"""
Schema Generator for Conduit Pipeline Elements

This module automatically generates a JSON schema for Conduit pipeline YAML/JSON configurations
by introspecting the Python classes and their type hints, docstrings, and signatures.

Environment Variables:
- CONDUIT_SEARCH_PATHS: Comma-separated list of additional search paths for pipeline elements
- CONDUIT_SCHEMA_PATH: Full path for output schema file (overrides default location)
"""

import inspect
import json
import sys
import os
from pathlib import Path
from typing import get_type_hints, get_origin, get_args, Any, Iterator, Generator
from dataclasses import is_dataclass, fields, MISSING
import dataclasses
import importlib
import pkgutil

from .pipelineElement import PipelineElement
from . import elements

def get_pipeline_elements_from_path(search_path, prefix="conduit"):
    """Discover PipelineElement classes from a specific module path"""
    elements_dict = {}
    
    try:
        # Add the search path to sys.path temporarily
        search_path = Path(search_path).resolve()
        if str(search_path) not in sys.path:
            sys.path.insert(0, str(search_path))
        
        # Try to import the module at this path
        for item in search_path.rglob("*.py"):
            if item.name.startswith("__"):
                continue
                
            # Convert file path to module name
            rel_path = item.relative_to(search_path)
            module_parts = list(rel_path.parts[:-1]) + [rel_path.stem]
            module_name = ".".join(module_parts)
            
            if not module_name:
                continue
                
            try:
                module = importlib.import_module(module_name)
                
                # Find all classes that are subclasses of PipelineElement
                for name, obj in inspect.getmembers(module, inspect.isclass):
                    if (hasattr(obj, '__bases__') and 
                        any('PipelineElement' in str(base) for base in obj.__mro__) and
                        'PipelineElement' not in str(obj) and
                        obj.__module__ == module_name):
                        
                        # Create element ID with specified prefix
                        element_id = f"{prefix}.{name}"
                        elements_dict[element_id] = obj
                        
            except (ImportError, AttributeError, ValueError) as e:
                # Skip modules that can't be imported or don't have valid classes
                continue
                
    except Exception as e:
        print(f"Warning: Could not search path {search_path}: {e}")
    
    return elements_dict

def get_all_pipeline_elements():
    """Discover all PipelineElement classes from built-in and configured search paths"""
    elements_dict = {}
    
    # Always include built-in conduit elements
    elements_module = elements
    
    # Walk through all modules in the elements package
    for importer, modname, ispkg in pkgutil.iter_modules(elements_module.__path__, 
                                                          elements_module.__name__ + "."):
        try:
            module = importlib.import_module(modname)
            
            # Find all classes that are subclasses of PipelineElement
            for name, obj in inspect.getmembers(module, inspect.isclass):
                if (issubclass(obj, PipelineElement) and 
                    obj != PipelineElement and 
                    obj.__module__ == modname):
                    
                    # Create the conduit.ElementName ID format
                    element_id = f"conduit.{name}"
                    elements_dict[element_id] = obj
                    
        except ImportError as e:
            print(f"Warning: Could not import {modname}: {e}")
            continue
    
    # Check for additional search paths from environment variable
    search_paths_env = os.getenv('CONDUIT_SEARCH_PATHS')
    if search_paths_env:
        print(f"Using additional search paths from CONDUIT_SEARCH_PATHS: {search_paths_env}")
        search_paths = [path.strip() for path in search_paths_env.split(',') if path.strip()]
        
        for i, search_path in enumerate(search_paths):
            # Use custom prefix for additional paths
            prefix = f"custom{i+1}"
            custom_elements = get_pipeline_elements_from_path(search_path, prefix)
            elements_dict.update(custom_elements)
    
    return elements_dict

def get_constructor_parameters(cls):
    """Extract constructor parameters and their types"""
    try:
        # Check if the class has its own __init__ method (not inherited from base class)
        if '__init__' not in cls.__dict__:
            # This class doesn't define its own __init__, so it has no specific parameters
            return {}
            
        signature = inspect.signature(cls.__init__)
        type_hints = get_type_hints(cls.__init__)
        
        params = {}
        for param_name, param in signature.parameters.items():
            if param_name in ['self', 'args', 'kwargs']:
                continue
                
            param_info = {
                'name': param_name,
                'required': param.default == param.empty
            }
            
            # Get type information
            if param_name in type_hints:
                param_type = type_hints[param_name]
                param_info['type'] = python_type_to_json_schema_type(param_type)
            else:
                # Infer type from default value if available
                if param.default != param.empty:
                    if isinstance(param.default, bool):
                        param_info['type'] = {'type': 'boolean'}
                    elif isinstance(param.default, int):
                        param_info['type'] = {'type': 'integer'}
                    elif isinstance(param.default, float):
                        param_info['type'] = {'type': 'number'}
                    elif isinstance(param.default, str):
                        param_info['type'] = {'type': 'string'}
                    elif isinstance(param.default, list):
                        param_info['type'] = {'type': 'array'}
                    else:
                        param_info['type'] = {'type': 'string'}
                else:
                    param_info['type'] = {'type': 'string'}
            
            # Get default value
            if param.default != param.empty:
                param_info['default'] = param.default
                
            params[param_name] = param_info
            
        return params
    except Exception as e:
        print(f"Warning: Could not get parameters for {cls.__name__}: {e}")
        return {}

def get_dataclass_input_schema(cls):
    """Generate schema for dataclass input types"""
    try:
        signature = inspect.signature(cls.process)
        type_hints = get_type_hints(cls.process)
        
        if 'input' not in type_hints:
            return None
            
        input_type = type_hints['input']
        
        # Extract the Iterator inner type
        if get_origin(input_type) is not None:
            args = get_args(input_type)
            if args:
                inner_type = args[0]
                if is_dataclass(inner_type):
                    return generate_dataclass_schema(inner_type)
        
        return None
    except Exception as e:
        print(f"Warning: Could not get input schema for {cls.__name__}: {e}")
        return None

def generate_dataclass_schema(dataclass_type):
    """Generate JSON schema for a dataclass"""
    if not is_dataclass(dataclass_type):
        return None
        
    schema = {
        'type': 'object',
        'properties': {},
        'required': []
    }
    
    for field in fields(dataclass_type):
        field_schema = python_type_to_json_schema_type(field.type)
        
        # Add description from docstring if available
        if hasattr(dataclass_type, field.name):
            attr = getattr(dataclass_type, field.name)
            if hasattr(attr, '__doc__') and attr.__doc__:
                field_schema['description'] = attr.__doc__.strip()
        
        schema['properties'][field.name] = field_schema
        
        # Check if field has default value
        if field.default == field.default_factory == dataclass_type.__dataclass_fields__[field.name].default:
            continue  # Has default, not required
        else:
            schema['required'].append(field.name)
    
    return schema

def python_type_to_json_schema_type(python_type):
    """Convert Python type hints to JSON schema types"""
    # Handle None type
    if python_type is type(None):
        return {'type': 'null'}
    
    # Handle basic types
    if python_type == str:
        return {'type': 'string'}
    elif python_type == int:
        return {'type': 'integer'}
    elif python_type == float:
        return {'type': 'number'}
    elif python_type == bool:
        return {'type': 'boolean'}
    elif python_type == list:
        return {'type': 'array'}
    elif python_type == dict:
        return {'type': 'object'}
    
    # Handle generic types
    origin = get_origin(python_type)
    args = get_args(python_type)
    
    if origin is list:
        if args:
            return {
                'type': 'array',
                'items': python_type_to_json_schema_type(args[0])
            }
        return {'type': 'array'}
    elif origin is dict:
        return {'type': 'object'}
    elif origin is type(Iterator) or origin is type(Generator):
        # For Iterator/Generator types, we don't need to specify the schema
        return {'type': 'string', 'description': f'Iterator/Generator type'}
    
    # Handle Union types (including Optional)
    if origin is type(None) or str(python_type).startswith('typing.Union') or str(python_type).startswith('typing.Optional'):
        if args:
            # Check if this is Optional[T] (Union[T, None])
            if len(args) == 2 and type(None) in args:
                non_none_type = args[0] if args[1] is type(None) else args[1]
                return python_type_to_json_schema_type(non_none_type)
            else:
                # Multiple types union - use anyOf
                return {
                    'anyOf': [python_type_to_json_schema_type(arg) for arg in args if arg is not type(None)]
                }
    
    # Handle string representations of types that might not be imported
    type_str = str(python_type)
    if 'str' in type_str:
        return {'type': 'string'}
    elif 'int' in type_str:
        return {'type': 'integer'}
    elif 'float' in type_str:
        return {'type': 'number'}
    elif 'bool' in type_str:
        return {'type': 'boolean'}
    elif 'List' in type_str or 'list' in type_str:
        return {'type': 'array'}
    
    # Default fallback
    return {'type': 'string', 'description': f'Type: {python_type}'}

def extract_class_docstring(cls):
    """Extract and clean class docstring"""
    if cls.__doc__:
        lines = cls.__doc__.strip().split('\n')
        # Take the first non-empty line as description
        for line in lines:
            line = line.strip()
            if line:
                return line
    return f"{cls.__name__} pipeline element"



def generate_element_schema(element_id, element_class):
    """Generate JSON schema for a single pipeline element"""
    schema = {
        'type': 'object',
        'description': extract_class_docstring(element_class),
        'properties': {
            'id': {
                'type': 'string',
                'const': element_id,
                'description': f'Pipeline element type: {element_class.__name__}'
            }
        },
        'required': ['id']
    }
    
    # Add constructor parameters (element-level configuration)
    params = get_constructor_parameters(element_class)
    for param_name, param_info in params.items():
        param_schema = param_info.get('type', {'type': 'string'})
        
        if 'default' in param_info:
            param_schema['default'] = param_info['default']
        
        schema['properties'][param_name] = param_schema
        
        if param_info['required']:
            schema['required'].append(param_name)
    
    # Look for dataclass input (per-datum configuration)
    # Check if element has an input dataclass (e.g., CliElementInput for CliElement)
    input_class_name = f"{element_class.__name__}Input"
    module = importlib.import_module(element_class.__module__)
    
    if hasattr(module, input_class_name):
        input_class = getattr(module, input_class_name)
        if is_dataclass(input_class):
            print(f"Found input dataclass: {input_class_name}")
            
            # Generate schema for the dataclass and merge properties
            for field in fields(input_class):
                # Only process fields that have None default (they're optional overrides)
                if field.default is not None:
                    continue
                    
                field_schema = python_type_to_json_schema_type(field.type)
                
                # Add description from field docstring if available
                if field.metadata and 'description' in field.metadata:
                    field_schema['description'] = field.metadata['description']
                
                # If this field exists in constructor params, use constructor default
                if field.name in params and 'default' in params[field.name]:
                    field_schema['default'] = params[field.name]['default']
                
                # Merge with constructor property (dataclass extends constructor)
                schema['properties'][field.name] = field_schema
                
                # Dataclass fields with MISSING default are optional overrides
                # Don't add them to required list unless constructor requires them
    
    # Elements should define their properties through constructor + dataclass pattern
    schema['additionalProperties'] = False
    
    return schema

def generate_full_schema():
    """Generate the complete JSON schema for Conduit pipelines"""
    elements_dict = get_all_pipeline_elements()
    
    # Base schema structure
    schema = {
        '$schema': 'http://json-schema.org/draft-07/schema#',
        '$id': 'https://github.com/text2motion/conduit/schema/pipeline-schema.json',
        'title': 'Conduit Pipeline Configuration',
        'description': 'Schema for Conduit data pipeline YAML/JSON configurations',
        'type': 'array',
        'items': {'$ref': '#/definitions/PipelineElement'},
        'definitions': {
            'PipelineElement': {
                'type': 'object',
                'required': ['id'],
                'properties': {
                    'id': {
                        'type': 'string',
                        'description': 'Fully qualified class name of the pipeline element',
                        'enum': list(elements_dict.keys())
                    }
                },
                'allOf': []
            }
        }
    }
    
    # Generate conditional schemas for each element type
    for element_id, element_class in elements_dict.items():
        element_schema = generate_element_schema(element_id, element_class)
        
        conditional_schema = {
            'if': {
                'properties': {
                    'id': {'const': element_id}
                }
            },
            'then': {
                'properties': element_schema['properties'],
                'required': element_schema.get('required', ['id']),
                'additionalProperties': element_schema.get('additionalProperties', False)
            }
        }
        
        schema['definitions']['PipelineElement']['allOf'].append(conditional_schema)
    
    return schema

def get_schema_output_path():
    """Get the schema output path from environment variable or default location"""
    # Check for custom schema path from environment variable
    custom_path = os.getenv('CONDUIT_SCHEMA_PATH')
    if custom_path:
        print(f"Using custom schema path from CONDUIT_SCHEMA_PATH: {custom_path}")
        return Path(custom_path)
    
    # Default: put schema in conduit package directory: {install_location}/conduit/schema
    import conduit
    conduit_path = Path(conduit.__file__).parent
    
    # Whether editable install or regular install, put schema inside the conduit package
    schema_dir = conduit_path / "schema"
    schema_dir.mkdir(exist_ok=True)
    return schema_dir / "pipeline-schema.json"

def main():
    """Main function to generate and save the schema"""
    print("Generating Conduit pipeline schema...")
    
    # Show configuration
    search_paths_env = os.getenv('CONDUIT_SEARCH_PATHS')
    custom_path = os.getenv('CONDUIT_SCHEMA_PATH')
    if search_paths_env or custom_path:
        print("Configuration:")
        if search_paths_env:
            print(f"  Additional search paths: {search_paths_env}")
        if custom_path:
            print(f"  Custom output path: {custom_path}")
    
    # Discover all pipeline elements
    elements_dict = get_all_pipeline_elements()
    print(f"Found {len(elements_dict)} pipeline elements:")
    for element_id in sorted(elements_dict.keys()):
        print(f"  - {element_id}")
    
    # Generate schema
    schema = generate_full_schema()
    
    # Get output path
    schema_file = get_schema_output_path()
    
    # Ensure directory exists
    schema_file.parent.mkdir(parents=True, exist_ok=True)
    
    # Write schema to file
    with open(schema_file, 'w', encoding='utf-8') as f:
        json.dump(schema, f, indent=2, sort_keys=True)
    
    print(f"\nSchema generated successfully: {schema_file}")
    print(f"Schema contains {len(schema['definitions']['PipelineElement']['allOf'])} element definitions")

if __name__ == '__main__':
    main()