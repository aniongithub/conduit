from ..pipelineElement import PipelineElement
from typing import Any, Generator, Iterator, List, Tuple

class Identity(PipelineElement):
    def process(self, input: Iterator[Any]) -> Generator[Any, None, None]:
        for i in input:
            yield i