from dataclasses import dataclass
from typing import Generator, Iterator, Optional, Union
from ..pipelineElement import PipelineElement

import random

@dataclass
class RandomInput:
    """Input specification for Random element
    
    All fields are optional - if not provided, will use defaults from constructor.
    This allows global configuration via constructor with per-datum overrides.
    """
    seed: Optional[int] = None
    min: Optional[Union[float, int]] = None
    max: Optional[Union[float, int]] = None
    type: Optional[str] = None  # "float" or "int"

class Random(PipelineElement):
    """Generate random values (float or integer)
    
    For each input, generates one random value within the specified range.
    Type can be "float" or "int" to control output type.
    """
    
    def __init__(
        self, 
        seed: Optional[int] = None, 
        min: Union[float, int] = 0, 
        max: Union[float, int] = 1.0,
        type: str = "float"
    ):
        """Initialize Random element
        
        Args:
            seed: Default random seed for reproducible results
            min: Default minimum value for random number
            max: Default maximum value for random number
            type: Default type of random number ("float" or "int")
        """
        super().__init__()  # Automatically captures all constructor parameters
    
    def process(self, input: Iterator[RandomInput]) -> Generator[Union[float, int], None, None]:
        for random_input in input:
            # Apply constructor defaults to None fields
            random_input = self.apply_defaults(random_input)
            
            if random_input.seed is not None:
                random.seed(random_input.seed)
            
            if random_input.type == "int":
                yield random.randint(int(random_input.min), int(random_input.max))
            else:  # default to float
                yield random.uniform(float(random_input.min), float(random_input.max))
