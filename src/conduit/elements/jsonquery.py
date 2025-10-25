from typing import Generator, Iterator, Any, Union, Dict, List, Optional
from dataclasses import dataclass
from ..pipelineElement import PipelineElement
import json

@dataclass
class JsonQueryInput:
    """Input specification for JsonQuery element
    
    All fields are optional - if not provided, will use defaults from constructor.
    This allows global configuration via constructor with per-datum overrides.
    """
    input: Any
    query: Optional[str] = None

class JsonQuery(PipelineElement):
    """
    JSON Query pipeline element using jq-style syntax for JSON transformation.
    
    Supports extracting values, arrays, and objects from JSON data with simple
    dot notation and array indexing.
    """
    
    def __init__(self, query: str = "."):
        """
        Initialize JSON Query element.
        
        Args:
            query: Default jq-style query string (e.g., ".results", ".data[0].name", ".users[]")
        """
        super().__init__()  # Automatically captures all constructor parameters
    
    def _parse_query(self, query: str) -> List[str]:
        """Parse a jq-style query into a list of operations."""
        if query == ".":
            return []
        
        # Remove leading dot if present
        if query.startswith("."):
            query = query[1:]
        
        # Split by dots, but handle array notation
        parts = []
        current_part = ""
        bracket_count = 0
        
        for char in query:
            if char == "[":
                bracket_count += 1
                current_part += char
            elif char == "]":
                bracket_count -= 1
                current_part += char
            elif char == "." and bracket_count == 0:
                if current_part:
                    parts.append(current_part)
                current_part = ""
            else:
                current_part += char
        
        if current_part:
            parts.append(current_part)
        
        return parts
    
    def _apply_operation(self, data: Any, operation: str) -> Any:
        """Apply a single query operation to data."""
        if operation == "":
            return data
        
        # Handle array operations
        if operation.endswith("[]"):
            # Extract all elements from array
            field = operation[:-2]
            if field:
                # First get the field, then extract array elements
                if isinstance(data, dict) and field in data:
                    array_data = data[field]
                elif hasattr(data, field):
                    array_data = getattr(data, field)
                else:
                    raise ValueError(f"Field '{field}' not found in data")
            else:
                array_data = data
            
            if isinstance(array_data, list):
                return array_data  # Will be flattened later
            else:
                raise ValueError(f"Cannot iterate over non-array: {type(array_data)}")
        
        # Handle array indexing [n]
        if "[" in operation and "]" in operation:
            bracket_start = operation.find("[")
            bracket_end = operation.find("]")
            field = operation[:bracket_start] if bracket_start > 0 else ""
            index_str = operation[bracket_start + 1:bracket_end]
            
            # Get the array data
            if field:
                if isinstance(data, dict) and field in data:
                    array_data = data[field]
                elif hasattr(data, field):
                    array_data = getattr(data, field)
                else:
                    raise ValueError(f"Field '{field}' not found in data")
            else:
                array_data = data
            
            # Apply index
            if index_str.isdigit():
                index = int(index_str)
                if isinstance(array_data, list):
                    if -len(array_data) <= index < len(array_data):
                        return array_data[index]
                    else:
                        raise ValueError(f"Array index {index} out of range")
                else:
                    raise ValueError(f"Cannot index non-array: {type(array_data)}")
            else:
                raise ValueError(f"Invalid array index: {index_str}")
        
        # Handle regular field access
        if isinstance(data, dict):
            if operation in data:
                return data[operation]
            else:
                raise ValueError(f"Field '{operation}' not found in data")
        elif hasattr(data, operation):
            # Handle dataclass or object attribute access
            return getattr(data, operation)
        else:
            raise ValueError(f"Field '{operation}' not found in data")
    
    def _execute_query(self, data: Any, query: str) -> Any:
        """Execute a complete jq-style query on data."""
        operations = self._parse_query(query)
        current_data = data
        
        for operation in operations:
            current_data = self._apply_operation(current_data, operation)
        
        return current_data
    
    def _flatten_if_needed(self, result: Any) -> Iterator[Any]:
        """
        Flatten result based on type:
        - Arrays: yield each element separately
        - Dicts: yield each key-value pair as a tuple
        - Single values: yield the value itself
        """
        if isinstance(result, list):
            # Arrays: yield each element
            for item in result:
                yield item
        elif isinstance(result, dict):
            # Dicts: yield each key-value pair as a tuple
            for key, value in result.items():
                yield (key, value)
        else:
            # Single values: yield as-is
            yield result
    
    def process(self, input: Iterator[JsonQueryInput]) -> Generator[Any, None, None]:
        """Process each input item by applying the JSON query."""
        for json_input in input:
            # Apply constructor defaults to None fields
            json_input = self.apply_defaults(json_input)
            
            # Normalize query
            query = json_input.query.strip() if json_input.query else "."
            if not query:
                query = "."
            
            try:
                # Convert input to JSON-like structure if it's a string
                item = json_input.input
                if isinstance(item, str):
                    try:
                        data = json.loads(item)
                    except json.JSONDecodeError:
                        # If it's not valid JSON, treat as string literal
                        data = item
                else:
                    data = item
                
                # Execute the query
                result = self._execute_query(data, query)
                
                # Handle special case for array extraction with []
                if query.endswith("[]"):
                    # For array extraction, we want to yield each element separately
                    if isinstance(result, list):
                        for element in result:
                            yield element
                    else:
                        yield result
                else:
                    # For other queries, apply flattening logic
                    for flattened_result in self._flatten_if_needed(result):
                        yield flattened_result
            
            except Exception as e:
                # Yield error information for debugging
                yield {
                    "error": f"JSON query failed: {str(e)}",
                    "query": query,
                    "input": json_input.input
                }