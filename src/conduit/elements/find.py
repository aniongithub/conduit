from typing import Generator, Iterator, Any, Optional, List
from dataclasses import dataclass
from ..pipelineElement import PipelineElement
from ..template_renderer import get_template_renderer
import re

@dataclass
class FindInput:
    """Input specification for Find element
    
    All fields are optional - if not provided, will use defaults from constructor.
    This allows global configuration via constructor with per-datum overrides.
    """
    text: Optional[str] = None
    pattern: Optional[str] = None
    operation: Optional[str] = None
    group: Optional[int] = None
    flags: Optional[int] = None
    output_all_groups: Optional[bool] = None

class Find(PipelineElement):
    """
    Find pipeline element for pattern matching and extraction.
    
    Supports pattern matching, searching, and extraction with optional 
    template rendering for dynamic patterns.
    """
    
    def __init__(
        self,
        text: Optional[str] = None,
        pattern: str = r".*",
        operation: str = "search",
        group: int = 0,
        flags: int = 0,
        output_all_groups: bool = False
    ):
        """
        Initialize Find element.
        
        Args:
            text: Default text to search (can be overridden per-datum)
            pattern: The regular expression pattern (supports Jinja2 templates)
            operation: Operation to perform - "match", "search", "findall", "extract"
            group: Which capture group to return (0 for full match, 1+ for specific groups)
            flags: Regex flags (re.IGNORECASE, re.MULTILINE, etc.)
            output_all_groups: If True, output all capture groups as a list
        """
        super().__init__()  # Automatically captures all constructor parameters
    
    def process(self, input: Iterator[FindInput]) -> Generator[Any, None, None]:
        """Process each input item by applying find operations."""
        renderer = get_template_renderer()
        
        for find_input in input:
            # Apply constructor defaults to None fields
            find_input = self.apply_defaults(find_input)
            
            # Validate operation
            valid_operations = ["match", "search", "findall", "extract"]
            if find_input.operation.lower() not in valid_operations:
                raise ValueError(f"Invalid operation '{find_input.operation}'. Valid operations: {valid_operations}")
            
            try:
                # Get text from input (required after applying defaults)
                text = find_input.text
                if text is None:
                    raise ValueError("Text is required (either from constructor or per-datum)")
                
                # Create context for template rendering
                context = {"input": find_input}
                
                # Render pattern template
                rendered_pattern = renderer.render_template(find_input.pattern, context)
                
                # Compile regex pattern
                regex = re.compile(rendered_pattern, find_input.flags)
                
                # Perform the requested operation
                if find_input.operation.lower() == "match":
                    match = regex.match(text)
                    if match:
                        if find_input.output_all_groups:
                            yield list(match.groups())
                        else:
                            yield match.group(find_input.group)
                    else:
                        yield None
                
                elif find_input.operation.lower() == "search":
                    match = regex.search(text)
                    if match:
                        if find_input.output_all_groups:
                            yield list(match.groups())
                        else:
                            yield match.group(find_input.group)
                    else:
                        yield None
                
                elif find_input.operation.lower() == "findall":
                    matches = regex.findall(text)
                    if matches:
                        # findall returns a list, so we yield each match separately
                        for match in matches:
                            if isinstance(match, tuple):
                                # Multiple groups - yield as list
                                yield list(match)
                            else:
                                # Single group or no groups
                                yield match
                    else:
                        yield None
                        
                elif find_input.operation.lower() == "extract":
                    # Extract specific group(s) from the match
                    match = regex.search(text)
                    if match:
                        if find_input.output_all_groups:
                            yield list(match.groups())
                        else:
                            yield match.group(find_input.group)
                    else:
                        yield None
            
            except re.error as e:
                # Handle regex compilation or execution errors
                yield {
                    "error": f"Regex error: {str(e)}",
                    "pattern": find_input.pattern,
                    "input": find_input
                }
            
            except Exception as e:
                # Handle other errors
                yield {
                    "error": f"Find operation failed: {str(e)}",
                    "operation": find_input.operation,
                    "input": find_input
                }