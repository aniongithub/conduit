from dataclasses import make_dataclass
from typing import Generator, Iterator, Any, List, Dict, Union
from ..pipelineElement import PipelineElement

class Input(PipelineElement):
    def __init__(self, data: List[Union[Dict[str, Any], Any]] = None):
        """Initialize Input element with data to yield
        
        Args:
            data: List of items to yield from this input element. 
                  Each item can be a dict (which gets converted to a dataclass) 
                  or any other type (yielded as-is).
        """
        self.data = data or []
    
    def process(self, input: Iterator[None]) -> Generator[Any, None, None]:
        for item in self.data:
            if isinstance(item, dict):
                # Create a dataclass from dict fields and values
                fields = {k: type(v) for k, v in item.items()}
                result = make_dataclass("InputData", fields)(**item)
                yield result
            else:
                # For non-dict items, yield as-is
                yield item

