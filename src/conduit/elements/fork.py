from logging import Logger
from ..pipelineElement import PipelineElement
from ..pipeline import Pipeline
from typing import Any, Generator, Iterator, Dict, List, Type
from ..common import loads
from dataclasses import dataclass

import json

@dataclass
class ForkInput:
    """Input specification for Fork element
    
    paths: Dict of named pipeline paths to execute in parallel.
           Each key becomes a field name in the output dict.
           Each value is a list of pipeline elements to execute.
    """
    paths: Dict[str, List[Dict[str, Any]]]

class Fork(PipelineElement):
    def __init__(self, paths: Dict[str, List[Dict[str, Any]]] = None):
        self._paths = {}
        if paths:
            self.paths = paths

    @property 
    def paths(self):
        return self._paths
    
    @paths.setter
    def paths(self, paths: Dict[str, List]):
        self._paths = {}
        for field_name, pipeline_data in paths.items():
            pipeline_data = loads(json.dumps(pipeline_data))
            if not isinstance(pipeline_data, list):
                pipeline_data = [pipeline_data]
            p = Pipeline(pipeline_data)
            self._paths[field_name] = p

    def process(self, input: Iterator[Any]) -> Generator[Dict[str, Any], None, None]:
        # Process each input item through all fork paths before moving to next item
        # This ensures item-wise synchronization and maintains laziness
        for item in input:
            # Process this single item through all paths immediately
            result = {}
            
            for path_name, pipeline in self._paths.items():
                # Each path processes exactly this one item
                path_results = list(pipeline.process(iter([item])))
                
                # We expect exactly one result per input item per path
                if path_results:
                    result[path_name] = path_results[0]
                else:
                    result[path_name] = None
            
            # Yield combined result for this item immediately
            yield result

    def outputs(self) -> Generator[Type, None, None]:
        for field_name, pipeline in self._paths.items():
            yield pipeline.inputs()
    