from dataclasses import dataclass
from logging import Logger
from .. import PipelineElement
from typing import Any, Generator, Iterator, Optional
from ..utils import get_functions
from ..template_renderer import get_template_renderer

@dataclass
class ConsoleInput:
    """Input specification for Console element
    
    input: The data item to print
    format: Optional format string for rendering the input (defaults to "{{input}}")
    """
    input: Optional[Any] = None
    format: Optional[str] = None

class Console(PipelineElement):
    def __init__(self, format: str = "{{input}}", input: Any = None):
        super().__init__()  # Capture constructor parameters if needed

    def process(self, input: Iterator[ConsoleInput]) -> Generator[Any, None, None]:
        renderer = get_template_renderer()
        for i in input:
            i = self.apply_defaults(i)
            # Fallback to default format if still None
            if i.format is None:
                i.format = "{{input}}"
            context = get_functions()
            context["input"] = i.input
            result = renderer.render_template(i.format, context)
            print(result)
            yield i.input  # Pass through the original input, not the ConsoleInput object