from abc import ABC
from logging import Logger
from typing import Generator, Generic, Iterator, TypeVar
from pydantic import BaseModel
import inspect
from .common import instantiate, logger


InputType = TypeVar("InputType", bound=BaseModel)
OutputType = TypeVar("OutputType", bound=BaseModel)

class PipelineElement(ABC, Generic[InputType, OutputType]):
    def __init__(self):
        """Automatically capture constructor parameters from child class as defaults"""
        self._defaults = {}
        
        # Get the calling frame (child class constructor)
        frame = inspect.currentframe().f_back
        if frame:
            keys, _, _, values = inspect.getargvalues(frame)
            # Store all parameters except 'self' as defaults
            self._defaults = {k: v for k, v in values.items() if k != 'self'}
    
    def apply_defaults(self, dataclass_instance):
        """Apply constructor defaults to None fields in dataclass instance"""
        for field_name, default_value in self._defaults.items():
            # Skip special attributes like __class__
            if field_name.startswith('__'):
                continue
            if hasattr(dataclass_instance, field_name):
                current_value = getattr(dataclass_instance, field_name)
                if current_value is None:
                    setattr(dataclass_instance, field_name, default_value)
        return dataclass_instance

    def process(self, input: Iterator[InputType]) -> Generator[OutputType, None, None]:
        logger().error("process method not implemented")

    @staticmethod
    def create(**kwargs):
        element_id = kwargs["id"] if "id" in kwargs else None
        kwargs.pop("id", None)
        return instantiate(element_id, **kwargs)
    
    def inputs(self) -> Generator[InputType, None, None]:
        yield from [ InputType ]
    
    def outputs(self) -> Generator[OutputType, None, None]:
        yield from [ OutputType ]