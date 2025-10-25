from typing import Generator, Iterator, Any, Union, Optional
from dataclasses import dataclass
from ..pipelineElement import PipelineElement

@dataclass
class ExtractInput:
    """Input specification for Extract element
    
    All fields are optional - if not provided, will use defaults from constructor.
    This allows global configuration via constructor with per-datum overrides.
    """
    input: Any
    path: Optional[str] = None

class Extract(PipelineElement):
    """
    Extract specific elements from tuples or objects using index or attribute access.
    
    Useful for extracting data from Fork outputs or other structured data.
    """
    
    def __init__(self, path: str):
        """
        Initialize Extract element.
        
        Args:
            path: Default path to extract (e.g., "0", "1", "name", "0.name", etc.)
        """
        super().__init__()  # Automatically captures all constructor parameters
    
    def _extract_value(self, obj: Any, path: str) -> Any:
        """Extract value from object using dot notation path."""
        parts = path.split('.')
        current = obj
        
        for part in parts:
            if part.isdigit():
                # Numeric index for tuples/lists
                index = int(part)
                if isinstance(current, (tuple, list)):
                    current = current[index]
                else:
                    raise ValueError(f"Cannot index non-sequence type {type(current)} with {part}")
            else:
                # Attribute access for objects/dicts
                if hasattr(current, part):
                    current = getattr(current, part)
                elif isinstance(current, dict) and part in current:
                    current = current[part]
                else:
                    raise ValueError(f"Cannot access '{part}' on {type(current)}")
        
        return current
    
    def process(self, input: Iterator[ExtractInput]) -> Generator[Any, None, None]:
        """Process each input by extracting the specified path."""
        for extract_input in input:
            # Apply constructor defaults to None fields
            extract_input = self.apply_defaults(extract_input)
            
            try:
                result = self._extract_value(extract_input.input, extract_input.path)
                yield result
            except Exception as e:
                raise ValueError(f"Failed to extract path '{extract_input.path}' from {type(extract_input.input)}: {e}")