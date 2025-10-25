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
        
    def _get_dict(self, obj):
        """Convert object to dictionary representation"""
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

    def _get_typename(self, obj):
        """Get typename string for an object"""
        return f"{obj.__module__}.{obj.__qualname__}"
    
    def _get_id(self, obj):
        """Get ID string for an object"""
        return self._get_typename(type(obj))
    
    def _get_parameter_types(self, func):
        """Get parameter types for a function"""
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
    
    def _flatten(self, iterable):
        """Flatten nested iterables"""
        for item in iterable:
            if isinstance(item, list) and not isinstance(item, (str, bytes)):
                yield from self._flatten(item)
            else:
                yield item        
    
    def _is_simple_type(self, obj):
        """Check if object is a simple type"""
        simple_types = (int, float, str, bool, bytes, type(None))
        return isinstance(obj, simple_types)
    
    def _is_input(self, obj, input_arg_type):
        """Check if object matches input argument type"""
        if self._is_simple_type(obj) and type(obj) == input_arg_type:
            return True

        input_is_iterator = get_origin(input_arg_type) == get_origin(Iterator[object])
        if not input_is_iterator:
            return False
        
        # Direct match, just pass it through
        input_is_input_arg_type = input_is_iterator and type(obj) == input_arg_type.__args__[0]
        return input_is_input_arg_type
           
    def _is_assignable_to_input(self, obj, input_arg_type):
        """Check if object can be assigned to input argument type"""
        # At this point we need to ensure that input_arg_type and obj are dataclasses
        input_is_dataclass = hasattr(input_arg_type, "__dataclass_fields__")
        obj_is_dataclass = is_dataclass(obj)
        if not input_is_dataclass or not obj_is_dataclass:
            return False
        
        input_is_assignable = set(fields(input_arg_type)).issubset(set(fields(obj)))
        return input_is_assignable

    def _convert_item_to_type(self, item, target_type):
        """Convert a single item to the target type"""
        logger().debug(f"Converting data item (type: {type(item)}) to {target_type}")
        
        # Direct match - no conversion needed
        if self._is_input(item, target_type):
            logger().debug(f"Direct input match")
            return item
        
        # Assignable dataclass - copy fields
        if self._is_assignable_to_input(item, target_type):
            logger().debug(f"Assignable input - creating instance via field copying")
            input_instance = instantiate(self._get_typename(target_type))
            for field in fields(target_type):
                setattr(input_instance, field.name, getattr(item, field.name))
            return input_instance
        
        # General conversion using dict representation
        logger().debug(f"Using get_dict conversion: {self._get_dict(item)}")
        if is_dataclass(target_type):
            logger().debug(f"Creating dataclass instance directly: {target_type}")
            input_data = self._get_dict(item)
            
            # Only pass fields that exist in the dataclass
            valid_fields = {field.name for field in fields(target_type)}
            filtered_data = {k: v for k, v in input_data.items() if k in valid_fields}
            
            logger().debug(f"Filtered data for dataclass: {filtered_data}")
            
            # If no fields matched, pass the entire object as 'input' if that field exists
            if not filtered_data and 'input' in valid_fields:
                logger().debug(f"No field matches, passing entire object as 'input' field")
                filtered_data = {'input': item}
            
            return target_type(**filtered_data)
        else:
            return instantiate(self._get_typename(target_type), **self._get_dict(item))

    def process(self, input: Iterator[InputType]) -> Generator[OutputType, None, None]:
        # Create a lazy generator chain - each element processes the output of the previous one
        def create_element_generator(element, input_stream):
            """Create a lazy generator for a single pipeline element"""
            try:
                logger().push()
                logger().debug(f"*** Processing element {self._get_id(element)} ***")
                param_types = self._get_parameter_types(element.process)
                if "input" not in param_types:
                    raise AttributeError(f"Element of type {element.__class__} does not have an 'input' parameter. Signature is {inspect.signature(element.process)}")
                arg_type = param_types["input"].__args__[0]
                
                def convert_items_generator():
                    """Create a generator that yields converted items on-demand"""
                    for item in self._flatten(input_stream):
                        try:
                            if arg_type == None.__class__ or arg_type == Any:
                                # For untyped elements, pass item directly
                                yield item
                            else:
                                # Convert item to expected type
                                converted_item = self._convert_item_to_type(item, arg_type)
                                yield converted_item
                        except Exception as item_ex:
                            element_id = self._get_id(element)
                            logger().error(f"Error converting item in element {element_id}: {str(item_ex)}", exc_info=item_ex)
                            
                            if self.stop_on_error:
                                raise
                            # Skip this item and continue with next
                            continue
                
                # Let the element decide how to consume the generator (lazy vs eager)
                yield from element.process(convert_items_generator())
                
            except Exception as ex:
                element_id = self._get_id(element)
                logger().error(f"Error in element {element_id}: {str(ex)}", exc_info=ex)
                
                if self.stop_on_error:
                    logger().error(f"Pipeline stopped due to error in element {element_id}")
                    raise
                else:
                    logger().warning(f"Continuing pipeline despite error in element {element_id}")
                    # Yield nothing for this element (effectively skipping it)
                    return
            finally:
                logger().debug(f"*** Finished processing element {self._get_id(element)} ***")
                logger().pop()

        # Chain all elements together lazily
        current_stream = input
        for element in self.elements:
            current_stream = create_element_generator(element, current_stream)
        
        # Final lazy output
        yield from current_stream

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