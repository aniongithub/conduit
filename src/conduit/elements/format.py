from typing import Generator, Iterator, Any, Optional
from dataclasses import dataclass
from ..pipelineElement import PipelineElement
from ..template_renderer import SafeTemplateRenderer

@dataclass
class FormatInput:
    """Input specification for Format element
    
    All fields are optional - if not provided, will use defaults from constructor.
    This allows global configuration via constructor with per-datum overrides.
    """
    input: Any
    template: Optional[str] = None

class Format(PipelineElement):
    """Format input data using Jinja2 templates
    
    This element applies a Jinja2 template to transform input data.
    Useful for string formatting, adding extensions, combining fields, etc.
    
    The template is configured as a property on the element, and each input
    data item flows through the template to produce the output.
    """
    
    def __init__(self, template: str = "{{input}}"):
        """Initialize Format element
        
        Args:
            template: Default Jinja2 template string to format the input data.
                     For dict inputs, each key becomes a template variable.
                     For non-dict inputs, the value is available as 'input'.
        """
        super().__init__()  # Automatically captures all constructor parameters
    
    def process(self, input: Iterator[FormatInput]) -> Generator[str, None, None]:
        renderer = SafeTemplateRenderer()
        
        for format_input in input:
            # Apply constructor defaults to None fields
            format_input = self.apply_defaults(format_input)
            
            item = format_input.input
            
            # Prepare template variables
            if isinstance(item, dict):
                # For dict inputs, each key becomes a template variable
                template_vars = item.copy()
                template_vars['input'] = item  # Also available as 'input'
            elif hasattr(item, '__dict__'):
                # For objects with attributes, make each attribute available as a template variable
                template_vars = item.__dict__.copy()
                template_vars['input'] = item  # Also available as 'input'
            else:
                # For simple values, available as 'input'
                template_vars = {'input': item}
            
            # Apply the template to format the data
            result = renderer.render_template(format_input.template, template_vars)
            yield result