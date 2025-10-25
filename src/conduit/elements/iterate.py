from dataclasses import dataclass
from ..pipelineElement import PipelineElement
from typing import Any, Generator, Iterator, Optional

@dataclass
class IterateInput:
    """Input specification for Iterate element
    
    All fields are optional - if not provided, will use defaults from constructor.
    This allows global configuration via constructor with per-datum overrides.
    """
    input: Any
    count: Optional[int] = None

class Iterate(PipelineElement):
    """Iterate/repeat input data a specified number of times
    
    Takes input data with a count and yields the input data that many times.
    Useful for generating multiple instances of the same data.
    """
    
    def __init__(self, count: int = 1):
        """Initialize Iterate element
        
        Args:
            count: Default number of times to repeat each input item
        """
        super().__init__()  # Automatically captures all constructor parameters
    
    def process(self, input: Iterator[IterateInput]) -> Generator[Any, None, None]:
        for iterate_input in input:
            # Apply constructor defaults to None fields
            iterate_input = self.apply_defaults(iterate_input)
            
            for i in range(iterate_input.count):
                yield iterate_input.input

