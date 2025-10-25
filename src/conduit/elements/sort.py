from dataclasses import dataclass
from typing import Iterator, List, Any, Optional, Generator
from ..pipelineElement import PipelineElement
from ..common import logger

@dataclass
class SortInput:
    """Input specification for Sort element"""
    input: Any
    key: Optional[str] = None
    reverse: Optional[bool] = None

class Sort(PipelineElement):
    """
    Sort element that sorts all input items based on a key expression.
    
    This is an eager element that collects all items before sorting and outputting them.
    The key expression is evaluated for each item to determine sort order.
    
    Example configurations:
    - Sort by string representation: key: "str(input)"
    - Sort by numeric field: key: "input.size" 
    - Sort by nested field: key: "input.stats.level"
    - Sort by expression: key: "len(input.name)"
    - Reverse sort: reverse: true
    """
    
    def __init__(self, key: str = "str(input)", reverse: bool = False):
        """
        Initialize Sort element with configuration.
        
        Args:
            key: Expression to evaluate for sort key (default: "str(input)")
            reverse: Sort in descending order if True (default: False)
        """
        super().__init__()  # Automatically captures all constructor parameters
    
    def process(self, input: Iterator[SortInput]) -> Generator[Any, None, None]:
        """Process all input items and sort them by the specified key expression."""
        try:
            logger().push()
            logger().debug("Sort: Starting processing")
            
            # Collect all items first (Sort requires materializing the iterator)
            items = list(input)
            logger().debug(f"Sort: Collected {len(items)} items to sort")
            
            if not items:
                logger().debug("Sort: No items to sort")
                return
            
            # Create a dummy SortInput to get defaults, then apply them
            dummy_input = SortInput(input=None)
            defaults = self.apply_defaults(dummy_input)
            
            # Apply defaults to all items and collect actual data to sort
            sort_data = []
            for sort_input in items:
                # Apply constructor defaults to None fields
                sort_input = self.apply_defaults(sort_input)
                sort_data.append(sort_input)
            
            logger().debug(f"Sort: Using key expression '{defaults.key}', reverse={defaults.reverse}")
            
            # Sort items based on the key expression
            def get_sort_key(sort_input):
                """Evaluate the key expression for an item"""
                try:
                    # Create a local context for evaluation
                    context = {"input": sort_input.input}
                    result = eval(sort_input.key, {"__builtins__": {}}, context)
                    logger().debug(f"Sort: Key for item {sort_input.input} -> {result}")
                    return result
                except Exception as e:
                    logger().warning(f"Sort: Error evaluating key '{sort_input.key}' for item {sort_input.input}: {e}")
                    # Fallback to string representation
                    return str(sort_input.input)
            
            # Sort and yield the actual data items (not the SortInput wrappers)
            sorted_items = sorted(sort_data, key=get_sort_key, reverse=defaults.reverse)
            logger().debug(f"Sort: Sorted {len(sorted_items)} items")
            
            for sort_input in sorted_items:
                yield sort_input.input
                
        except Exception as e:
            logger().error(f"Sort: Error during processing: {e}", exc_info=e)
            raise
        finally:
            logger().debug("Sort: Finished processing") 
            logger().pop()