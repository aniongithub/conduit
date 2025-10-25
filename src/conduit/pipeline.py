from logging import Logger
from typing import Any, Generator, Iterator, List, Tuple, TypeVar, get_origin, get_args
import uuid

from .pipelineElement import PipelineElement
from pydantic import BaseModel
import os
from .common import loadjson, loadyaml, instantiate, logger
import networkx as nx

import inspect
from dataclasses import is_dataclass, fields
from typing import get_type_hints

from dataclasses import is_dataclass, fields

InputType = TypeVar("InputType", bound=BaseModel)
OutputType = TypeVar("OutputType", bound=BaseModel)

class Pipeline(PipelineElement):
    def __init__(self, elements: List[dict], stop_on_error: bool = True):
        self.elements = []
        self.logger = logger()
        self.stop_on_error = stop_on_error
        try:
            logger().push()
            for e in elements:
                logger().info(f"Creating element {e['id']}")
                self.elements.append(PipelineElement.create(**e))
        except Exception as ex:
            self.logger.error(f"Error creating element {e['id']}", exc_info = ex)
            raise
        finally:
            self.logger.pop()
        
    def process(self, input: Iterator[InputType]) -> Generator[OutputType, None, None]:
        def get_dict(obj):
            if isinstance(obj, dict):
                return obj
            elif isinstance(obj, tuple): # Tuples are treated differently
                d = {}
                for i in range(len(obj)):
                    d[f"_{i}"] = obj[i]
                return d
            elif hasattr(obj, "__dict__"):
                return obj.__dict__
            else:
                # For non-dict types, wrap in a dict with 'input' key
                # This handles the case where previous element outputs a simple value
                # that needs to be converted to a dataclass with an 'input' field
                return {"input": obj}

        def get_typename(obj):
            return f"{obj.__module__}.{obj.__qualname__}"
        
        def get_id(obj):
            return get_typename(type(obj))
        
        def get_parameter_types(func):
            # Get the signature of the function
            signature = inspect.signature(func)
            
            # Get the type hints of the function
            type_hints = get_type_hints(func)
            
            # Extract the parameter types
            parameter_types = {}
            for param in signature.parameters.values():
                param_name = param.name
                param_type = type_hints.get(param_name, None)
                parameter_types[param_name] = param_type
            
            return parameter_types
        
        def flatten(iterable):
            for item in iterable:
                if isinstance(item, list) and not isinstance(item, (str, bytes)):
                    yield from flatten(item)
                else:
                    yield item        
        
        def is_simple_type(obj):
            simple_types = (int, float, str, bool, bytes, type(None))
            return isinstance(obj, simple_types)
        
        def is_input(obj, input_arg_type):
            if is_simple_type(obj) and type(obj) == input_arg_type:
                return True

            input_is_iterator = get_origin(input_arg_type) == get_origin(Iterator[object])
            if not input_is_iterator:
                return False
            
            # Direct match, just pass it through
            input_is_input_arg_type = input_is_iterator and type(obj) == input_arg_type.__args__[0]
            return input_is_input_arg_type
               
        def is_assignable_to_input(obj, input_arg_type):
            # At this point we need to ensure that input_arg_type and obj are dataclasses
            input_is_dataclass = hasattr(input_arg_type, "__dataclass_fields__")
            obj_is_dataclass = is_dataclass(obj)
            if not input_is_dataclass or not obj_is_dataclass:
                return False
            
            input_is_assignable = set(fields(input_arg_type)).issubset(set(fields(obj)))
            return input_is_assignable

        # Process the pipeline by converting current_data to a list between stages
        # This breaks true laziness but avoids generator conflicts for now
        current_data = list(input)

        for e in self.elements:
            try:
                logger().push()
                logger().debug(f"*** Processing element {get_id(e)} ***")
                param_types = get_parameter_types(e.process)
                if "input" not in param_types:
                    raise AttributeError(f"Element of type {e.__class__} does not have an 'input' parameter. Signature is {inspect.signature(e.process)}")
                arg_type = param_types["input"].__args__[0]
                
                if arg_type == None.__class__:
                    current_data = list(e.process(current_data))
                elif arg_type == Any:
                    current_data = list(e.process(current_data))
                else:
                    # Process items one at a time and collect results
                    next_data = []
                    for d in flatten(current_data):
                        logger().debug(f"Converting data item (type: {type(d)}) to {arg_type}")
                        
                        # Convert single item
                        converted_item = None
                        if is_input(d, arg_type):
                            logger().debug(f"Direct input match")
                            converted_item = d
                        elif is_assignable_to_input(d, arg_type):
                            logger().debug(f"Assignable input - creating instance via field copying")
                            input_instance = instantiate(get_typename(arg_type))
                            for field in fields(arg_type):
                                setattr(input_instance, field.name, getattr(d, field.name))
                            converted_item = input_instance
                        else:
                            logger().debug(f"Using get_dict conversion: {get_dict(d)}")
                            # Check if target type is a dataclass - if so, instantiate directly
                            if is_dataclass(arg_type):
                                logger().debug(f"Creating dataclass instance directly: {arg_type}")
                                input_data = get_dict(d)
                                
                                # Only pass fields that exist in the dataclass
                                valid_fields = {field.name for field in fields(arg_type)}
                                filtered_data = {k: v for k, v in input_data.items() if k in valid_fields}
                                
                                logger().debug(f"Filtered data for dataclass: {filtered_data}")
                                
                                # If no fields matched, pass the entire object as 'input' if that field exists
                                if not filtered_data and 'input' in valid_fields:
                                    logger().debug(f"No field matches, passing entire object as 'input' field")
                                    filtered_data = {'input': d}
                                
                                converted_item = arg_type(**filtered_data)
                            else:
                                converted_item = instantiate(get_typename(arg_type), **get_dict(d))
                        
                        # Process single converted item and collect results
                        element_results = list(e.process(iter([converted_item])))
                        next_data.extend(element_results)
                    
                    current_data = next_data
                    
            except Exception as ex:
                element_id = get_id(e)
                logger().error(f"Error processing element {element_id}: {str(ex)}", exc_info=ex)
                
                if self.stop_on_error:
                    logger().error(f"Pipeline stopped due to error in element {element_id}")
                    raise
                else:
                    logger().warning(f"Continuing pipeline despite error in element {element_id}")
                    # Continue with empty data to avoid breaking downstream elements
                    current_data = iter([])
            finally:
                logger().debug(f"*** Finished processing element {get_id(e)} ***")
                logger().pop()

        # Final output
        yield from iter(current_data)

    def run(self, input: dict = {}) -> Any:
        data = self.process([input])
        output = None
        for d in data:
            output = d
            
        return output
    
    # add getitem

    def __getitem__(self, key):
        return self.elements[key]
    def __len__(self):
        return len(self.elements)
    
    @staticmethod
    def from_config(pipeline_filename: str, logger: Logger = None, expand_env: bool = False, stop_on_error: bool = True) -> 'Pipeline':
        if os.path.splitext(pipeline_filename)[1] == ".json":
            pipeline_data = loadjson(pipeline_filename, expand_env)
        ext = os.path.splitext(pipeline_filename)[1]
        if ext == ".yaml" or ext == ".yml":
            pipeline_data = loadyaml(pipeline_filename, expand_env)
        
        result = Pipeline(pipeline_data, stop_on_error=stop_on_error)
        result.logger = logger
        return result

    def to_graph(self, pipeline: 'Pipeline' = None)-> nx.DiGraph:
        def get_typename(obj):
            return f"{obj.__module__}.{obj.__qualname__}"
        
        def populate(graph: nx.DiGraph, element: PipelineElement, parents: List[PipelineElement] = []) -> List[PipelineElement]:
            if get_typename(type(element)) == 'conduit.pipeline.Pipeline':
                for element in element.elements:
                    parents = populate(graph, element, parents) # This is wrong, we aren't iterating over the elements
                return parents
            
            if get_typename(type(element)) == 'conduit.elements.fork.Fork':
                graph.add_node(element)
                for parent in parents:
                    graph.add_edge(parent, element)
                parents = []
                for p in element.paths:
                    parents += populate(graph, p, [ element ])
                return parents

            graph.add_node(element)
            for parent in parents:
                graph.add_edge(parent, element)
            return [ element ]

        if pipeline is None:
            pipeline = self
        graph = nx.DiGraph()

        parents = []
        for e in pipeline.elements:
            for p in parents:
                graph.add_edge(p, e)
            parents = populate(graph, e, parents)

        return graph