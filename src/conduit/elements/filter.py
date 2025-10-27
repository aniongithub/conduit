from dataclasses import dataclass
from typing import Any, Iterator, Generator
from ..pipelineElement import PipelineElement
from ..common import logger


class DotDict(dict):
    """Dictionary wrapper that allows dot notation access to nested dictionaries"""
    
    def __getattr__(self, key):
        try:
            value = self[key]
            # Recursively convert nested dicts to DotDict for continued dot notation
            if isinstance(value, dict):
                return DotDict(value)
            elif isinstance(value, list):
                # Convert list items that are dicts to DotDict
                return [DotDict(item) if isinstance(item, dict) else item for item in value]
            return value
        except KeyError:
            raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{key}'")


@dataclass
class FilterInput:
    """Input specification for Filter element
    
    Args:
        input: The data item to evaluate
        condition: Expression to evaluate (dynamic parameter)
    """
    input: Any
    condition: str = None


@dataclass  
class FilterOutput:
    """Output specification for Filter element
    
    Args:
        output: The filtered data item (only items that pass the condition)
    """
    output: Any


class Filter(PipelineElement):
    """Filter pipeline element that keeps items when condition evaluates to True
    
    Uses Python's built-in eval for expression evaluation. Items are available as 'item' in the condition.
    Dictionary keys can be accessed using dot notation for cleaner syntax.
    
    Args:
        condition: Expression to evaluate (default "True" keeps all items)
        
    Examples:
        Filter(condition="item.weight > 500")  # Keep heavy Pokemon
        Filter(condition="len(item.abilities) >= 2")  # Keep Pokemon with 2+ abilities
        Filter(condition="any(t.type.name == 'grass' for t in item.types)")  # Keep grass types
    """
    
    def __init__(self, condition: str = "True"):
        super().__init__()  # Capture constructor parameters
    
    def process(self, input: Iterator[FilterInput]) -> Generator[Any, None, None]:
        """Process input items, yielding only those that pass the filter condition
        
        Args:
            input: Iterator of FilterInput items
            
        Yields:
            Any: Raw items where condition evaluated to True (not wrapped in FilterOutput)
        """
        for item in input:
            # Apply defaults to get the actual condition (could be dynamic)
            item = self.apply_defaults(item)
            
            try:
                # Debug logging to see what we're evaluating
                logger().debug(f"Filter evaluating condition: '{item.condition}'")
                logger().debug(f"Filter input data type: {type(item.input)}")
                
                # Convert input to DotDict for dot notation access
                dot_item = DotDict(item.input) if isinstance(item.input, dict) else item.input
                
                # Create evaluation context with built-in functions and the item
                eval_context = {
                    'item': dot_item,
                    'any': any,
                    'all': all,
                    'len': len,
                    '__builtins__': {}  # Restrict access to built-ins for security
                }
                
                # Evaluate the condition using built-in eval
                result = eval(item.condition, eval_context)
                logger().debug(f"Filter condition result: {result}")
                
                if result:
                    logger().debug(f"Filter KEEPING item (condition was True)")
                    # Yield the raw data, not wrapped in FilterOutput
                    yield item.input
                else:
                    logger().debug(f"Filter SKIPPING item (condition was False)")
                # Items that don't pass the condition are silently skipped
            except Exception as e:
                logger().warning(f"Filter evaluation error for condition '{item.condition}': {e}")
                # Skip items that cause evaluation errors