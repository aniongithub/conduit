from typing import Generator, Iterator, Any, Optional, List
from dataclasses import dataclass
from ..pipelineElement import PipelineElement
from collections import defaultdict

@dataclass
class GroupByInput:
    """Input specification for GroupBy element
    
    All fields are optional - if not provided, will use defaults from constructor.
    This allows global configuration via constructor with per-datum overrides.
    """
    input: Any
    key: Optional[str] = None
    value: Optional[str] = None

@dataclass 
class GroupByOutput:
    """Output from GroupBy element"""
    key: str
    values: List[Any]

class GroupBy(PipelineElement):
    """
    GroupBy pipeline element for grouping items by a specified key.
    
    Collects all input items and groups them by the specified key expression,
    then outputs grouped results as dictionaries with 'key' and 'values' fields.
    """
    
    def __init__(self, key: str, value: Optional[str] = None):
        """
        Initialize GroupBy element.
        
        Args:
            key: Expression to group by (supports Python expressions like "input.department", "input['field']")
            value: Optional expression to extract as values (if None, uses entire input)
        """
        super().__init__()  # Automatically captures all constructor parameters
    
    def process(self, input: Iterator[GroupByInput]) -> Generator[GroupByOutput, None, None]:
        """Process all input items and group them by the specified key expression."""
        # Collect all items first (GroupBy requires materializing the iterator)
        items = list(input)
        
        # Create a dummy GroupByInput to get defaults, then apply them
        dummy_input = GroupByInput(input=None)
        defaults = self.apply_defaults(dummy_input)
        
        # Group items by key
        groups = defaultdict(list)
        
        for group_input in items:
            # Apply constructor defaults to None fields
            group_input = self.apply_defaults(group_input)
            
            # Extract grouping key using eval
            try:
                group_key = eval(group_input.key, {"__builtins__": {}}, {"input": group_input.input})
            except Exception as e:
                group_key = f"error: {str(e)}"
            
            # Extract value (or use entire input if no value expression specified)
            if group_input.value:
                try:
                    group_value = eval(group_input.value, {"__builtins__": {}}, {"input": group_input.input})
                except Exception:
                    group_value = group_input.input
            else:
                group_value = group_input.input
            
            # Convert group key to string for consistent grouping
            group_key_str = str(group_key) if group_key is not None else "null"
            
            groups[group_key_str].append(group_value)
        
        # Output grouped results - one group per yield as GroupByOutput dataclass
        for group_key, group_values in groups.items():
            yield GroupByOutput(key=group_key, values=group_values)