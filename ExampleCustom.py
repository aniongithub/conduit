from conduit.pipelineElement import PipelineElement
from typing import Iterator, Any
from dataclasses import dataclass

@dataclass
class ExampleCustomInput:
    message: str = "Hello from custom element!"

class ExampleCustom(PipelineElement):
    """Example custom pipeline element for demonstration"""
    
    def __init__(self, prefix: str = "[CUSTOM]"):
        super().__init__()
        self.prefix = prefix
    
    def process(self, input: Iterator[ExampleCustomInput]) -> Iterator[dict]:
        for item in input:
            yield {
                "custom_message": f"{self.prefix} {item.message}",
                "element_type": "custom",
                "original_input": item.__dict__
            }