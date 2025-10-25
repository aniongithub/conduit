from typing import Generator, Iterator, Optional
from dataclasses import dataclass
from ..pipelineElement import PipelineElement

import urllib.request
import urllib.parse
import os
from pathlib import Path
import hashlib

@dataclass  
class DownloadInput:
    """Input specification for DownloadFile element
    
    All fields are optional - if not provided, will use defaults from constructor.
    This allows global configuration via constructor with per-datum overrides.
    """
    url: Optional[str] = None
    filename: Optional[str] = None
    output_dir: Optional[str] = None
    overwrite: Optional[bool] = None
    create_dirs: Optional[bool] = None

class DownloadFile(PipelineElement):
    """
    Download files from URLs with configurable output directory and filename handling.
    
    Supports custom output directories, filename templates, and automatic filename
    generation from URLs or content hashing.
    """
    
    def __init__(
        self,
        url: Optional[str] = None,
        filename: Optional[str] = None,
        output_dir: str = "./downloads",
        overwrite: bool = False,
        create_dirs: bool = True
    ):
        """
        Initialize DownloadFile element.
        
        Args:
            url: Default URL to download (can be overridden per-datum)
            filename: Default filename (can be overridden per-datum)
            output_dir: Directory to save downloaded files (supports env vars)
            overwrite: Whether to overwrite existing files
            create_dirs: Whether to create output directory if it doesn't exist
        """
        super().__init__()  # Automatically captures all constructor parameters
    
    def _get_filename_from_url(self, url: str) -> str:
        """Extract filename from URL or generate one."""
        parsed = urllib.parse.urlparse(url)
        path = parsed.path
        
        # Get filename from URL path
        if path and not path.endswith('/'):
            filename = os.path.basename(path)
            if filename and '.' in filename:
                return filename
        
        # Generate filename from URL hash if no good filename found
        url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
        return f"download_{url_hash}"
    
    def process(self, input: Iterator[DownloadInput]) -> Generator[str, None, None]:
        """Process each input by downloading files with optional custom filename."""
        for download_request in input:
            # Apply constructor defaults to None fields
            download_request = self.apply_defaults(download_request)
            
            url = download_request.url
            filename = download_request.filename
            
            # URL is required (either from constructor or per-datum)
            if not url or not url.startswith(('http://', 'https://')):
                raise ValueError(f"Invalid or missing URL: {url}")
                
            # Use per-datum or constructor default output directory
            output_directory = download_request.output_dir
            
            # Create output directory if needed
            if download_request.create_dirs:
                Path(output_directory).mkdir(parents=True, exist_ok=True)
            
            # Use provided filename or auto-generate from URL
            if filename:
                final_filename = filename
            else:
                final_filename = self._get_filename_from_url(url)
            
            # Construct full file path
            file_path = os.path.join(output_directory, final_filename)
            
            # Check if file exists and handle overwrite logic
            if os.path.exists(file_path) and not download_request.overwrite:
                # Add counter to filename to avoid conflicts
                base, ext = os.path.splitext(file_path)
                counter = 1
                while os.path.exists(f"{base}_{counter}{ext}"):
                    counter += 1
                file_path = f"{base}_{counter}{ext}"
            
            # Download the file
            with urllib.request.urlopen(url) as response:
                with open(file_path, 'wb') as f:
                    while True:
                        chunk = response.read(8192)
                        if not chunk:
                            break
                        f.write(chunk)
            
            yield file_path
