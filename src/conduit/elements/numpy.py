from typing import Generator, Iterator, Optional
from dataclasses import dataclass
from ..pipelineElement import PipelineElement
import numpy as np
import os

@dataclass
class NumpyFileInput:
    """Input specification for NumpyFile element
    
    All fields are optional - if not provided, will use defaults from constructor.
    This allows global configuration via constructor with per-datum overrides.
    """
    filename: Optional[str] = None
    allow_pickle: Optional[bool] = None
    fix_imports: Optional[bool] = None

class NumpyFile(PipelineElement):
    def __init__(
        self, 
        filename: Optional[str] = None,
        allow_pickle: bool = False,
        fix_imports: bool = True
    ):
        """Initialize NumpyFile element
        
        Args:
            filename: Default numpy file to load (can be overridden per-datum)
            allow_pickle: Default setting for allowing pickle loading
            fix_imports: Default setting for fixing imports during loading
        """
        super().__init__()  # Automatically captures all constructor parameters
    
    def process(self, input: Iterator[NumpyFileInput]) -> Generator[np.ndarray, None, None]:
        for numpy_input in input:
            # Apply constructor defaults to None fields
            numpy_input = self.apply_defaults(numpy_input)
            
            if numpy_input.filename is None:
                raise ValueError("Filename is required (either from constructor or per-datum)")
            
            yield np.load(
                numpy_input.filename,
                allow_pickle=numpy_input.allow_pickle,
                fix_imports=numpy_input.fix_imports
            )