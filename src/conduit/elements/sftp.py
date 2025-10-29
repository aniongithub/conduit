"""SFTP listing and download elements for Conduit.

This module provides two focused, composable PipelineElements:
- SftpList: performs server-side listing and yields metadata dicts for files.
- SftpDownload: downloads files given a remote path (string) or metadata dict
  produced by SftpList.

Design: keep elements single-responsibility and data-driven so pipelines may
list -> filter -> download without convenience/combined behaviors.
"""

import io
import os
from dataclasses import dataclass
from typing import Iterator, Optional, List, Union, Dict, Any
from pathlib import Path

try:
    import paramiko
    PARAMIKO_AVAILABLE = True
except ImportError:
    PARAMIKO_AVAILABLE = False

from ..pipelineElement import PipelineElement


@dataclass
class SftpListInput:
    """Input for SftpList element.

    Each input item instructs the element what to list. All auth/connection
    info should be provided when the element is instantiated (constructor
    args) to keep inputs data-focused (only remote paths + listing options).
    """
    remote_path: str
    glob_pattern: Optional[str] = None
    recursive: bool = False
    list_dirs: bool = False


@dataclass
class SftpList(PipelineElement):
    """List files on an SFTP server and emit metadata dictionaries.

    Yields metadata dicts with at least the `remote_path` and `filename` keys.
    Does NOT download file content.
    """

    def __init__(self,
                 hostname: str,
                 username: str,
                 password: Optional[str] = None,
                 private_key_path: Optional[str] = None,
                 port: int = 22,
                 timeout: int = 30,
                 # By default do not consult the local SSH agent or look for
                 # keys in standard locations. That prevents GUI/keyring
                 # unlock prompts for encrypted keys when password auth is
                 # provided. Set True to re-enable agent/lookups.
                 allow_agent: bool = False,
                 look_for_keys: bool = False):
        super().__init__()

        if not PARAMIKO_AVAILABLE:
            raise ImportError("paramiko is required for SFTP functionality. Install with: pip install paramiko")

        self.hostname = hostname
        self.username = username
        self.password = password
        self.private_key_path = private_key_path
        self.port = port
        self.timeout = timeout
        self.allow_agent = allow_agent
        self.look_for_keys = look_for_keys

        if not self.password and not self.private_key_path:
            raise ValueError("Either password or private_key_path must be provided")

    # --- shared helpers ---
    def _create_sftp_client(self):
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        connect_kwargs: Dict[str, Any] = {
            'hostname': self.hostname,
            'port': self.port,
            'username': self.username,
            'timeout': self.timeout,
        }

        if self.password:
            connect_kwargs['password'] = self.password

        if self.private_key_path:
            if os.path.exists(self.private_key_path):
                # try to load supported key types
                for key_class in (paramiko.RSAKey, paramiko.DSSKey, paramiko.ECDSAKey, getattr(paramiko, 'Ed25519Key', None)):
                    if key_class is None:
                        continue
                    try:
                        private_key = key_class.from_private_key_file(self.private_key_path)
                        connect_kwargs['pkey'] = private_key
                        break
                    except paramiko.PasswordRequiredException:
                        if self.password:
                            private_key = key_class.from_private_key_file(self.private_key_path, password=self.password)
                            connect_kwargs['pkey'] = private_key
                            break
                    except Exception:
                        continue
            else:
                raise FileNotFoundError(f"Private key file not found: {self.private_key_path}")

        # Explicitly control whether Paramiko should consult the SSH agent or
        # search for keys in the user's ~/.ssh. Default is False to avoid
        # triggering desktop keyring/passphrase dialogs unexpectedly.
        ssh.connect(allow_agent=self.allow_agent, look_for_keys=self.look_for_keys, **connect_kwargs)
        sftp = ssh.open_sftp()
        return ssh, sftp

    def _list_directory(self, sftp, remote_path: str, glob_pattern: Optional[str] = None, recursive: bool = False, list_dirs: bool = False) -> List[Dict[str, Any]]:
        import fnmatch
        from datetime import datetime, timezone

        results: List[Dict[str, Any]] = []

        def _scan(dir_path: str, depth: int = 0):
            try:
                for attr in sftp.listdir_attr(dir_path):
                    if attr.filename.startswith('.'):
                        continue

                    item_path = f"{dir_path.rstrip('/')}/{attr.filename}"
                    is_dir = attr.st_mode and (attr.st_mode & 0o040000) != 0

                    if is_dir:
                        if list_dirs and (not glob_pattern or fnmatch.fnmatch(attr.filename, glob_pattern)):
                            results.append({
                                'filename': attr.filename,
                                'remote_path': item_path,
                                'size': None,
                                'is_directory': True,
                                'mtime': datetime.fromtimestamp(attr.st_mtime, tz=timezone.utc).isoformat() if attr.st_mtime else None,
                                'depth': depth,
                                'attrs': attr.__dict__ if hasattr(attr, '__dict__') else None,
                            })
                        if recursive:
                            _scan(item_path, depth + 1)
                    else:
                        if not glob_pattern or fnmatch.fnmatch(attr.filename, glob_pattern):
                            results.append({
                                'filename': attr.filename,
                                'remote_path': item_path,
                                'size': attr.st_size,
                                'is_directory': False,
                                'mtime': datetime.fromtimestamp(attr.st_mtime, tz=timezone.utc).isoformat() if attr.st_mtime else None,
                                'depth': depth,
                                'attrs': attr.__dict__ if hasattr(attr, '__dict__') else None,
                            })
            except FileNotFoundError:
                # directory may vanish between listing calls
                return

        _scan(remote_path)
        return results

    # --- main processing ---
    def process(self, input: Iterator[SftpListInput]) -> Iterator[Dict[str, Any]]:
        ssh = None
        sftp = None
        try:
            ssh, sftp = self._create_sftp_client()

            for item in input:
                try:
                    # determine whether path is file or dir
                    try:
                        stat = sftp.stat(item.remote_path)
                        is_dir = (stat.st_mode & 0o040000) != 0
                    except FileNotFoundError:
                        self.logger.error(f"Remote path not found: {item.remote_path}")
                        continue

                    if not is_dir:
                        # single file -> emit metadata
                        yield {
                            'filename': Path(item.remote_path).name,
                            'remote_path': item.remote_path,
                            'size': stat.st_size,
                            'is_directory': False,
                            'mtime': None,
                            'attrs': None,
                        }
                    else:
                        # directory -> list
                        entries = self._list_directory(sftp, item.remote_path, item.glob_pattern, item.recursive, item.list_dirs)
                        for e in entries:
                            yield e

                except Exception as e:
                    self.logger.error(f"Error listing {item.remote_path}: {e}")
                    continue

        finally:
            if sftp:
                try:
                    sftp.close()
                except Exception:
                    pass
            if ssh:
                try:
                    ssh.close()
                except Exception:
                    pass


@dataclass
class SftpDownload(PipelineElement):
    """Download files from SFTP given remote paths or metadata dicts.

    Accepts inputs that are either a string (remote path) or a metadata dict
    containing at least `remote_path` (as produced by SftpList).
    """

    def __init__(self,
                 hostname: str,
                 username: str,
                 password: Optional[str] = None,
                 private_key_path: Optional[str] = None,
                 port: int = 22,
                 timeout: int = 30,
                 download_mode: str = "memory",
                 local_dir: Optional[str] = None,
                 # Controls whether Paramiko consults the local SSH agent or
                 # looks for keys in ~/.ssh. Defaults to False to avoid
                 # triggering GUI/passphrase prompts during automated runs.
                 allow_agent: bool = False,
                 look_for_keys: bool = False):
        super().__init__()

        if not PARAMIKO_AVAILABLE:
            raise ImportError("paramiko is required for SFTP functionality. Install with: pip install paramiko")

        self.hostname = hostname
        self.username = username
        self.password = password
        self.private_key_path = private_key_path
        self.port = port
        self.timeout = timeout
        self.download_mode = download_mode
        self.local_dir = local_dir
        self.allow_agent = allow_agent
        self.look_for_keys = look_for_keys

        if self.download_mode == 'local' and not self.local_dir:
            raise ValueError("local_dir must be specified when download_mode='local'")

        if not self.password and not self.private_key_path:
            raise ValueError("Either password or private_key_path must be provided")

    def _create_sftp_client(self):
        # reuse same helper logic as SftpList but keep duplicated to avoid coupling
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        connect_kwargs: Dict[str, Any] = {
            'hostname': self.hostname,
            'port': self.port,
            'username': self.username,
            'timeout': self.timeout,
        }

        if self.password:
            connect_kwargs['password'] = self.password

        if self.private_key_path:
            if os.path.exists(self.private_key_path):
                for key_class in (paramiko.RSAKey, paramiko.DSSKey, paramiko.ECDSAKey, getattr(paramiko, 'Ed25519Key', None)):
                    if key_class is None:
                        continue
                    try:
                        private_key = key_class.from_private_key_file(self.private_key_path)
                        connect_kwargs['pkey'] = private_key
                        break
                    except paramiko.PasswordRequiredException:
                        if self.password:
                            private_key = key_class.from_private_key_file(self.private_key_path, password=self.password)
                            connect_kwargs['pkey'] = private_key
                            break
                    except Exception:
                        continue
            else:
                raise FileNotFoundError(f"Private key file not found: {self.private_key_path}")

        ssh.connect(allow_agent=self.allow_agent, look_for_keys=self.look_for_keys, **connect_kwargs)
        sftp = ssh.open_sftp()
        return ssh, sftp

    def _download_file(self, sftp, remote_path: str, local_filename: Optional[str] = None) -> Dict[str, Any]:
        try:
            stat = sftp.stat(remote_path)
            size = stat.st_size

            filename = local_filename or Path(remote_path).name

            if self.download_mode == 'memory':
                bio = io.BytesIO()
                sftp.getfo(remote_path, bio)
                bio.seek(0)
                return {
                    'filename': filename,
                    'remote_path': remote_path,
                    'file_obj': bio,
                    'size': size,
                    'mode': 'memory',
                }

            if self.download_mode == 'temp':
                import tempfile
                tmp = tempfile.NamedTemporaryFile(delete=False, prefix=f"sftp_{filename}_")
                sftp.getfo(remote_path, tmp)
                tmp.close()
                return {
                    'filename': filename,
                    'remote_path': remote_path,
                    'local_path': tmp.name,
                    'size': size,
                    'mode': 'temp',
                }

            if self.download_mode == 'local':
                local_path = Path(self.local_dir) / filename
                local_path.parent.mkdir(parents=True, exist_ok=True)
                sftp.get(remote_path, str(local_path))
                return {
                    'filename': filename,
                    'remote_path': remote_path,
                    'local_path': str(local_path),
                    'size': size,
                    'mode': 'local',
                }

            raise ValueError(f"Unknown download_mode: {self.download_mode}")

        except Exception as e:
            raise RuntimeError(f"Failed to download {remote_path}: {e}")

    def process(self, input: Iterator[Any]) -> Iterator[Dict[str, Any]]:
        """Accept either string paths or metadata dicts from upstream elements.
        
        Uses Iterator[Any] instead of Union[str, Dict] to avoid pipeline
        type-conversion issues with Union types. Runtime isinstance checks
        handle both input forms.
        """
        ssh = None
        sftp = None
        try:
            ssh, sftp = self._create_sftp_client()

            for item in input:
                try:
                    if isinstance(item, str):
                        remote_path = item
                        local_filename = None
                    elif isinstance(item, dict):
                        remote_path = item.get('remote_path') or item.get('path')
                        if not remote_path:
                            self.logger.error(f"Input dict missing 'remote_path': {item}")
                            continue
                        local_filename = item.get('filename')
                    else:
                        self.logger.error(f"Unsupported input type for SftpDownload: {type(item)}")
                        continue

                    result = self._download_file(sftp, remote_path, local_filename)
                    # preserve some metadata from input if present
                    if isinstance(item, dict):
                        for key in ('mtime', 'depth', 'attrs'):
                            if key in item:
                                result[key] = item[key]

                    yield result

                except Exception as e:
                    # emit an error record in the stream instead of raising
                    self.logger.error(f"Download failed for {item}: {e}")
                    yield {'error': True, 'remote_path': item if isinstance(item, str) else item.get('remote_path'), 'message': str(e)}

        finally:
            if sftp:
                try:
                    sftp.close()
                except Exception:
                    pass
            if ssh:
                try:
                    ssh.close()
                except Exception:
                    pass