from typing import Generator, Iterator, Any, Optional
from dataclasses import dataclass
from ..pipelineElement import PipelineElement
import json
import jq

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
    JSON Query pipeline element using native jq library for JSON transformation.
    
    Supports the full jq syntax for JSON queries and transformations.
    """
    
    def __init__(self, query: str = "."):
        """
        Initialize JSON Query element.
        
        Args:
            query: Default jq query string (e.g., ".results", ".data[0].name", ".users[]")
        """
        super().__init__()  # Automatically captures all constructor parameters
        # Pre-compile the default query for efficiency
        self._compiled_query = jq.compile(query)
        self._default_query = query
    
    def process(self, input: Iterator[JsonQueryInput]) -> Generator[Any, None, None]:
        """Process each input item by applying the jq query."""
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
                
                # Use compiled query if it matches, otherwise compile new one
                if query == self._default_query:
                    compiled_query = self._compiled_query
                else:
                    compiled_query = jq.compile(query)
                
                # Execute the query using the correct jq API
                program_with_input = compiled_query.input_value(data)
                
                # Use the built-in iter() function to iterate over results
                for result in iter(program_with_input):
                    yield result
            
            except Exception as e:
                # Yield error information for debugging
                yield {
                    "error": f"jq query failed: {str(e)}",
                    "query": query,
                    "input": json_input.input
                }