from logging import Logger
from typing import Generator, Iterator, Optional, Any
from dataclasses import dataclass
from ..utils import get_functions
from ..pipelineElement import PipelineElement
from ..template_renderer import get_template_renderer

@dataclass
class PathTransformInput:
    """Input specification for PathTransform element
    
    All fields are optional - if not provided, will use defaults from constructor.
    This allows global configuration via constructor with per-datum overrides.
    """
    input: Any
    format: Optional[str] = None

class PathTransform(PipelineElement):
    def __init__(self, format: str = "{{path}}"):
        """Initialize PathTransform element
        
        Args:
            format: Default template string for path transformation
        """
        super().__init__()  # Automatically captures all constructor parameters

    def process(self, input: Iterator[PathTransformInput]) -> Generator[str, None, None]:
        renderer = get_template_renderer()
        for path_input in input:
            # Apply constructor defaults to None fields
            path_input = self.apply_defaults(path_input)
            
            context = get_functions()
            context["path"] = path_input.input
            context["input"] = path_input.input
            yield renderer.render_template(path_input.format, context)