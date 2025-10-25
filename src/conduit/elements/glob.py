from dataclasses import dataclass
from ..pipelineElement import PipelineElement
from glob import glob
from typing import Generator, Iterator, List, Optional

@dataclass
class GlobInput:
    """Input specification for Glob element
    
    All fields are optional - if not provided, will use defaults from constructor.
    This allows global configuration via constructor with per-datum overrides.
    """
    pattern: Optional[str] = None
    root_dir: Optional[str] = None
    max: Optional[int] = None
    recursive: Optional[bool] = None

@dataclass
class GlobOutput:
    filename: str

class Glob(PipelineElement):
    def __init__(
        self,
        pattern: str = "*",
        root_dir: str = ".",
        max: Optional[int] = None,
        recursive: bool = False
    ):
        """Initialize Glob element
        
        Args:
            pattern: Default glob pattern to search for
            root_dir: Default root directory to search in
            max: Default maximum number of files to return (None for no limit)
            recursive: Default whether to search recursively
        """
        super().__init__()  # Automatically captures all constructor parameters
        
    def process(self, input: Iterator[GlobInput]) -> Generator[GlobOutput, None, None]:
        for glob_input in input:
            # Apply constructor defaults to None fields
            glob_input = self.apply_defaults(glob_input)
            
            files = glob(glob_input.pattern, root_dir=glob_input.root_dir, recursive=glob_input.recursive)
            if glob_input.max is not None:
                files = files[:glob_input.max]
            
            for f in files:
                yield GlobOutput(filename=f)
