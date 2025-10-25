from typing import Generator, Iterator, Any
from ..pipelineElement import PipelineElement

class Empty(PipelineElement):
    """Generate empty data
    
    This element ignores its input and yields a single empty dict.
    Useful for providing default/empty input to other elements.
    """
    
    def process(self, input: Iterator[Any]) -> Generator[dict, None, None]:
        for _ in input:
            yield {}    