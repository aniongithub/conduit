# Creating Custom Pipeline Elements

This guide shows you how to create your own pipeline elements to extend Conduit's functionality.

## Basic Element Structure

Every pipeline element follows this pattern:

```python
from dataclasses import dataclass
from typing import Generator, Iterator, Optional
from conduit import PipelineElement

@dataclass
class MyElementInput:
    """Input specification for MyElement
    
    All fields should be Optional and will use constructor defaults if not provided.
    """
    value: Optional[str] = None
    multiplier: Optional[int] = None

class MyElement(PipelineElement):
    """A custom element that processes strings"""
    
    def __init__(self, default_multiplier: int = 1):
        super().__init__()  # Captures constructor parameters as defaults
    
    def process(self, input: Iterator[MyElementInput]) -> Generator[str, None, None]:
        for item in input:
            # Apply constructor defaults to None fields
            item = self.apply_defaults(item)
            
            # Process the item
            result = item.value * item.multiplier
            yield result
```

## Key Concepts

### 1. Input Dataclass
- Define a dataclass for typed input validation
- All fields should be `Optional` with `None` defaults
- Use clear field names and add docstrings

### 2. Constructor Defaults
- Use `super().__init__()` to capture constructor parameters
- These become defaults for input fields with `None` values
- Constructor parameters should match input dataclass fields

### 3. The `apply_defaults()` Method
- Merges constructor defaults with per-item input data
- Call this on each input item before processing
- Ensures consistent behavior between constructor and input data

### 4. Lazy Processing
- Use `yield` instead of `return` for memory efficiency
- Process one item at a time in generators
- Don't materialize large lists unless necessary

## Example: Text Processor

```python
from dataclasses import dataclass
from typing import Generator, Iterator, Optional
import re

@dataclass
class TextProcessorInput:
    """Input for text processing operations"""
    text: Optional[str] = None
    operation: Optional[str] = None  # "upper", "lower", "title", "clean"
    pattern: Optional[str] = None    # For regex operations

class TextProcessor(PipelineElement):
    """Process text with various operations"""
    
    def __init__(self, default_operation: str = "clean", default_pattern: str = r"[^\w\s]"):
        super().__init__()
    
    def process(self, input: Iterator[TextProcessorInput]) -> Generator[str, None, None]:
        for item in input:
            item = self.apply_defaults(item)
            
            text = item.text
            if not text:
                continue
                
            if item.operation == "upper":
                result = text.upper()
            elif item.operation == "lower":
                result = text.lower()
            elif item.operation == "title":
                result = text.title()
            elif item.operation == "clean":
                result = re.sub(item.pattern, "", text)
            else:
                result = text
                
            yield result
```

### Usage:
```yaml
# Constructor-level defaults
- id: my_package.TextProcessor
  default_operation: "upper"

# Per-item configuration
- id: conduit.Input
  data:
    - text: "Hello World!"
      operation: "lower"
    - text: "Another text"
      # Uses constructor default: "upper"

- id: my_package.TextProcessor
```

## Example: HTTP Client

```python
from dataclasses import dataclass
from typing import Generator, Iterator, Optional, Dict, Any
import requests

@dataclass 
class HttpClientInput:
    """Input for HTTP requests"""
    url: Optional[str] = None
    method: Optional[str] = None
    headers: Optional[Dict[str, str]] = None
    params: Optional[Dict[str, Any]] = None
    json_data: Optional[Dict[str, Any]] = None

class HttpClient(PipelineElement):
    """Make HTTP requests with flexible configuration"""
    
    def __init__(self, default_method: str = "GET", default_timeout: int = 30):
        super().__init__()
        self.timeout = default_timeout
    
    def process(self, input: Iterator[HttpClientInput]) -> Generator[Dict[str, Any], None, None]:
        for item in input:
            item = self.apply_defaults(item)
            
            try:
                response = requests.request(
                    method=item.method,
                    url=item.url,
                    headers=item.headers or {},
                    params=item.params or {},
                    json=item.json_data,
                    timeout=self.timeout
                )
                response.raise_for_status()
                
                yield {
                    "status_code": response.status_code,
                    "data": response.json() if response.headers.get("content-type", "").startswith("application/json") else response.text,
                    "headers": dict(response.headers)
                }
            except Exception as e:
                self.logger.error(f"HTTP request failed: {e}")
                if self.stop_on_error:
                    raise
```

## Example: Data Aggregator

```python
from dataclasses import dataclass
from typing import Generator, Iterator, Optional, List, Any
from collections import defaultdict

@dataclass
class AggregatorInput:
    """Input for data aggregation"""
    data: Optional[Any] = None
    group_by: Optional[str] = None
    operation: Optional[str] = None  # "sum", "count", "avg", "collect"

class Aggregator(PipelineElement):
    """Aggregate data by groups"""
    
    def __init__(self, default_operation: str = "collect"):
        super().__init__()
        self.groups = defaultdict(list)
    
    def process(self, input: Iterator[AggregatorInput]) -> Generator[Dict[str, Any], None, None]:
        # First pass: collect all data
        for item in input:
            item = self.apply_defaults(item)
            
            if item.group_by and hasattr(item.data, item.group_by):
                key = getattr(item.data, item.group_by)
            else:
                key = "default"
                
            self.groups[key].append(item.data)
        
        # Second pass: yield aggregated results
        for group, values in self.groups.items():
            if item.operation == "sum":
                result = sum(values)
            elif item.operation == "count":
                result = len(values)
            elif item.operation == "avg":
                result = sum(values) / len(values) if values else 0
            else:  # collect
                result = values
                
            yield {
                "group": group,
                "result": result,
                "count": len(values)
            }
```

## Element Registration

To make your elements available in pipelines, you need to register them:

### Option 1: Package Structure
```
my_conduit_elements/
├── __init__.py
├── text_processor.py
├── http_client.py
└── aggregator.py
```

In `__init__.py`:
```python
from .text_processor import TextProcessor
from .http_client import HttpClient  
from .aggregator import Aggregator

__all__ = ["TextProcessor", "HttpClient", "Aggregator"]
```

### Option 2: Entry Points (setup.py)
```python
setup(
    name="my-conduit-elements",
    entry_points={
        "conduit.elements": [
            "TextProcessor = my_conduit_elements:TextProcessor",
            "HttpClient = my_conduit_elements:HttpClient",
            "Aggregator = my_conduit_elements:Aggregator",
        ]
    }
)
```

## Best Practices

### 1. Error Handling
```python
def process(self, input: Iterator[MyInput]) -> Generator[Any, None, None]:
    for item in input:
        try:
            # Process item
            result = self.do_processing(item)
            yield result
        except Exception as e:
            self.logger.error(f"Processing failed: {e}")
            if self.stop_on_error:
                raise
            # Continue to next item
```

### 2. Logging
```python
def process(self, input: Iterator[MyInput]) -> Generator[Any, None, None]:
    for item in input:
        self.logger.debug(f"Processing item: {item}")
        # ... processing logic
        self.logger.info(f"Processed item successfully")
        yield result
```

### 3. Configuration Validation
```python
def __init__(self, required_param: str, optional_param: str = "default"):
    if not required_param:
        raise ValueError("required_param cannot be empty")
    super().__init__()
```

### 4. Resource Management
```python
def __init__(self, connection_string: str):
    super().__init__()
    self.connection = None

def process(self, input: Iterator[MyInput]) -> Generator[Any, None, None]:
    try:
        self.connection = create_connection(self.connection_string)
        for item in input:
            # Use self.connection
            yield result
    finally:
        if self.connection:
            self.connection.close()
```

## Testing Custom Elements

```python
import unittest
from my_elements import TextProcessor, TextProcessorInput

class TestTextProcessor(unittest.TestCase):
    def test_uppercase_operation(self):
        element = TextProcessor(default_operation="upper")
        input_data = [TextProcessorInput(text="hello world")]
        
        results = list(element.process(iter(input_data)))
        
        self.assertEqual(results[0], "HELLO WORLD")
        
    def test_per_item_override(self):
        element = TextProcessor(default_operation="upper")
        input_data = [TextProcessorInput(text="hello", operation="lower")]
        
        results = list(element.process(iter(input_data)))
        
        self.assertEqual(results[0], "hello")
```

## Integration with Conduit

Once your elements are installed, use them in pipelines:

```yaml
- id: conduit.Input
  data:
    - text: "Hello, World!"
      operation: "upper"

- id: my_package.TextProcessor
  default_operation: "clean"
  default_pattern: "[!,]"

- id: conduit.Console
  format: "Result: {{input}}"
```

Your custom elements integrate seamlessly with built-in elements and can be mixed and matched in any pipeline configuration!