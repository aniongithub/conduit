#!/usr/bin/env python3
"""
Schema Generator for Conduit Pipeline Elements

This script automatically generates a JSON schema for Conduit pipeline YAML/JSON configurations
by introspecting the Python classes and their type hints, docstrings, and signatures.
"""

import inspect
import json
import sys
import os
from pathlib import Path
from typing import get_type_hints, get_origin, get_args, Any, Iterator, Generator
from dataclasses import is_dataclass, fields
import importlib
import pkgutil

# Add src to path so we can import conduit
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from conduit.pipelineElement import PipelineElement
import conduit.elements

def get_all_pipeline_elements():
    """Discover all PipelineElement classes in the conduit.elements module"""
    elements = {}
    
    # Get the conduit.elements module
    elements_module = conduit.elements
    
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
                    elements[element_id] = obj
                    
        except ImportError as e:
            print(f"Warning: Could not import {modname}: {e}")
            continue
    
    return elements

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

def get_common_properties_for_element(element_class):
    """Get common properties that elements typically accept via setattr"""
    common_props = {}
    
    # Special handling for specific element types
    if element_class.__name__ == 'Input':
        common_props.update({
            'pattern': {
                'type': 'string',
                'description': "Glob pattern for file matching (e.g., '**/*.py')"
            },
            'root_dir': {
                'type': 'string', 
                'description': "Root directory for search operations",
                'default': '.'
            },
            'recursive': {
                'type': 'boolean',
                'description': "Enable recursive directory traversal",
                'default': False
            },
            'max': {
                'type': 'integer',
                'description': "Maximum number of results",
                'minimum': 1
            },
            'count': {
                'type': 'integer', 
                'description': "Number of items to generate",
                'minimum': 1
            }
        })
    elif element_class.__name__ == 'Glob':
        common_props.update({
            'max': {
                'type': 'integer',
                'description': "Maximum number of results",
                'minimum': 1
            }
        })
    
    return common_props

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
    
    # Add constructor parameters
    params = get_constructor_parameters(element_class)
    for param_name, param_info in params.items():
        param_schema = param_info.get('type', {'type': 'string'})
        
        # Add better descriptions and handle specific parameter types
        if param_name == 'format':
            param_schema['description'] = "Format string (supports {input} and function calls)"
        elif param_name == 'pattern':
            param_schema['description'] = "Glob pattern for file matching (e.g., '**/*.py')"
        elif param_name == 'root_dir':
            param_schema['description'] = "Root directory for search operations"
        elif param_name == 'recursive':
            param_schema['description'] = "Enable recursive directory traversal"
        elif param_name == 'command':
            param_schema['description'] = "Shell command to execute"
        elif param_name == 'arguments':
            param_schema['description'] = "Command line arguments (supports format strings)"
        elif param_name == 'working_directory':
            param_schema['description'] = "Working directory for command execution"
        elif param_name == 'capture_output':
            param_schema['description'] = "Capture and return command output"
        elif param_name == 'timeout':
            param_schema['description'] = "Command timeout in seconds (-1 for no timeout)"
        elif param_name == 'expression':
            param_schema['description'] = "Python expression to evaluate (has access to 'input' variable)"
        else:
            param_schema['description'] = f"Parameter: {param_name}"
        
        if 'default' in param_info:
            param_schema['default'] = param_info['default']
        
        schema['properties'][param_name] = param_schema
        
        if param_info['required']:
            schema['required'].append(param_name)
    
    # Add common properties that can be set via setattr
    common_props = get_common_properties_for_element(element_class)
    for prop_name, prop_schema in common_props.items():
        if prop_name not in schema['properties']:
            schema['properties'][prop_name] = prop_schema
    
    # Special handling for Fork element
    if element_class.__name__ == 'Fork':
        schema['properties']['paths'] = {
            'type': 'array',
            'description': 'Array of pipeline paths to execute in parallel',
            'items': {
                'type': 'array',
                'items': {'$ref': '#/definitions/PipelineElement'}
            },
            'minItems': 1
        }
        if 'paths' not in schema['required']:
            schema['required'].append('paths')
    
    # Allow additional properties for elements that use setattr pattern
    if len(params) == 0 or element_class.__name__ in ['Input', 'Glob', 'FileInfo']:
        schema['additionalProperties'] = True
    else:
        schema['additionalProperties'] = False
    
    return schema

def generate_full_schema():
    """Generate the complete JSON schema for Conduit pipelines"""
    elements = get_all_pipeline_elements()
    
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
                        'enum': list(elements.keys())
                    }
                },
                'allOf': []
            }
        }
    }
    
    # Generate conditional schemas for each element type
    for element_id, element_class in elements.items():
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

def main():
    """Main function to generate and save the schema"""
    print("Generating Conduit pipeline schema...")
    
    # Discover all pipeline elements
    elements = get_all_pipeline_elements()
    print(f"Found {len(elements)} pipeline elements:")
    for element_id in sorted(elements.keys()):
        print(f"  - {element_id}")
    
    # Generate schema
    schema = generate_full_schema()
    
    # Ensure schema directory exists
    schema_dir = Path(__file__).parent.parent / "schema"
    schema_dir.mkdir(exist_ok=True)
    
    # Write schema to file
    schema_file = schema_dir / "pipeline-schema.json"
    with open(schema_file, 'w', encoding='utf-8') as f:
        json.dump(schema, f, indent=2, sort_keys=True)
    
    print(f"\nSchema generated successfully: {schema_file}")
    print(f"Schema contains {len(schema['definitions']['PipelineElement']['allOf'])} element definitions")

if __name__ == '__main__':
    main()