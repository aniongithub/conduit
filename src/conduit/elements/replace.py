from typing import Generator, Iterator, Any, Optional
from dataclasses import dataclass
from ..pipelineElement import PipelineElement
from ..template_renderer import get_template_renderer
import re

@dataclass
class ReplaceInput:
    """Input specification for Replace element
    
    All fields are optional - if not provided, will use defaults from constructor.
    This allows global configuration via constructor with per-datum overrides.
    """
    text: Any
    replacement: Optional[str] = None
    pattern: Optional[str] = None
    flags: Optional[int] = None

class Replace(PipelineElement):
    """
    Replace pipeline element for pattern-based text substitution.
    
    Supports regex-based find and replace operations with template 
    rendering for dynamic patterns and replacements.
    """
    
    def __init__(
        self,
        pattern: str = r".*",
        replacement: str = "",
        flags: int = 0
    ):
        """
        Initialize Replace element.
        
        Args:
            pattern: Default regular expression pattern to find (supports Jinja2 templates)
            replacement: Default replacement string (supports Jinja2 templates)
            flags: Default regex flags (re.IGNORECASE, re.MULTILINE, etc.)
        """
        super().__init__()  # Automatically captures all constructor parameters
    
    def process(self, input: Iterator[ReplaceInput]) -> Generator[str, None, None]:
        """Process each input item by applying replace operations."""
        renderer = get_template_renderer()
        
        for replace_input in input:
            # Apply constructor defaults to None fields
            replace_input = self.apply_defaults(replace_input)
            
            try:
                # Get text and replacement from input
                text = replace_input.text
                replacement = replace_input.replacement
                
                # Create context for template rendering
                context = {"input": replace_input}
                
                # Render pattern template
                rendered_pattern = renderer.render_template(replace_input.pattern, context)
                
                # Render replacement template
                rendered_replacement = renderer.render_template(replacement, context)
                
                # Compile regex pattern
                regex = re.compile(rendered_pattern, replace_input.flags)
                
                # Perform substitution
                result = regex.sub(rendered_replacement, text)
                yield result
            
            except re.error as e:
                # Handle regex compilation or execution errors
                yield {
                    "error": f"Regex error: {str(e)}",
                    "pattern": replace_input.pattern,
                    "input": replace_input
                }
            
            except Exception as e:
                # Handle other errors
                yield {
                    "error": f"Replace operation failed: {str(e)}",
                    "input": replace_input
                }