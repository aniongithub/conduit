from dataclasses import dataclass
import os
from typing import Generator, Iterator, Optional
from ..pipelineElement import PipelineElement

@dataclass
class FileInfoInput:
    """Input specification for FileInfo element
    
    All fields are optional - if not provided, will use defaults from constructor.
    This allows global configuration via constructor with per-datum overrides.
    """
    filename: Optional[str] = None

@dataclass
class FileInfoOutput:
    name: str
    size: int
    last_modified: int
    created: int
    is_dir: bool
    is_file: bool

class FileInfo(PipelineElement):
    def __init__(self, filename: Optional[str] = None):
        """Initialize FileInfo element
        
        Args:
            filename: Default filename to analyze (can be overridden per-datum)
        """
        super().__init__()  # Automatically captures all constructor parameters
        
    def process(self, input: Iterator[FileInfoInput]) -> Generator[FileInfoOutput, None, None]:
        for file_input in input:
            # Apply constructor defaults to None fields
            file_input = self.apply_defaults(file_input)
            
            if file_input.filename is None:
                raise ValueError("Filename is required (either from constructor or per-datum)")
            
            stat = os.stat(file_input.filename)
            yield FileInfoOutput(
                name = file_input.filename,
                size = stat.st_size,
                last_modified = stat.st_mtime,
                created = stat.st_ctime,
                is_dir = os.path.isdir(file_input.filename),
                is_file = os.path.isfile(file_input.filename)
            )