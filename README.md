# conduit - A modern, modular data-driven data processor

**conduit** is a modular data pipeline framework designed for creating, processing, and transforming data for various purposes, like ML/AI or data analysis. Instead of writing brittle scripts that are buggy, hard to understand/modify, conduit allows users to compose pipelines from simple elements via `yaml` files. It removes the need for state machines and logic in data-processing scripts and makes them data-driven, externalizing and breaking down the steps needed to go from input to output, which can often be quite complex.

## Features

* **Data-driven** : By externalizing the composition stage of conventional data processing scripts, conduit effectively removes the need for a state machine in your data processing scripts which is typically the biggest source of bugs and code-rigidity.
* **Modular Design** : Build pipelines using composable `PipelineElement` components, including sources, transforms, sinks, and even sub-pipelines.
* **True Lazy Evaluation** : Efficiently handle large datasets with fully lazy, generator-based processing that maintains memory efficiency.
* **Type-Safe** : Use Python's `typing` and dataclasses to enforce schema validation and type safety.
* **Hierarchical Pipelines** : Combine multiple pipelines into larger workflows with ease using Fork elements.
* **Template System** : Secure Jinja2-based templating for dynamic configuration and formatting.
* **Environment Variables** : Built-in support for environment variable expansion with default values.
* **JSON Schema Generation** : Auto-generated JSON schema for IDE support and validation.
* **Extensible for ML/AI** : Tailored for dataset preparation, augmentation, and integration into ML workflows. It's easy to write custom PipelineElements, which can then seamlessly integrate with other elements instead of having to rewrite/integrate an entire script from scratch.

## Installation

To install conduit into your own environment, you can simply use `pip`

```bash
pip3 install git+https://github.com/text2motion/conduit.git
```

## Development

This is a devcontainer-enabled repository, please see [here](https://code.visualstudio.com/docs/devcontainers/tutorial) for pre-requisites and installation steps.

Now you can simple open the this repository in VS Code and choose "Reopen in Container" from the popup.

## Usage

To use conduit, you can invoke it using a terminal after installation like so:

```sh
conduit-cli path/to/pipeline.yaml
```

See `launch.json` for an example of debugging your workflows.

If you are using this repository, there is no need for any setup. Just press F5 and choose from any of the listed workflows from the `examples` folder.

## Example YAML Pipeline Configurations

### Simple File Processing Pipeline

```yaml
---
# Find all Python files and display file information
- id: conduit.Input
  data:
    - pattern: '**/*.py'
      root_dir: '.'
      recursive: true

- id: conduit.Glob
- id: conduit.FileInfo
- id: conduit.Console
  format: "{{input.name}} ........... {{input.size}} bytes"
```

This pipeline finds all Python files in the current directory and displays their names and sizes.

### Pokemon API Pipeline with Fork and Downloads

```yaml
---
# Download Pokemon images from the Pokemon API
- id: conduit.Input
  data:
    - url: "https://pokeapi.co/api/v2/pokemon?limit=${limit:-10}"
      method: "GET"

- id: conduit.RestApi
  response_format: "json"

- id: conduit.JsonQuery
  query: ".results[]"

# Fork to process data in parallel paths
- id: conduit.Fork
  paths:
    url:  # Get artwork URL
      - id: conduit.RestApi
        response_format: "json"
      - id: conduit.JsonQuery
        query: ".sprites.other.official-artwork.front_default"
    filename:  # Create filename from Pokemon name
      - id: conduit.JsonQuery
        query: ".name"
      - id: conduit.Format
        template: "{{input}}.png"

- id: conduit.DownloadFile
  output_dir: "${outputFolder:-./pokemon_images}"
  create_dirs: true
  overwrite: true

- id: conduit.Console
  format: "Downloaded Pokemon image: {{input}}"
```

This more complex pipeline demonstrates:

- Environment variable expansion with defaults (`${limit:-10}`)
- REST API calls and JSON processing
- Fork elements for parallel processing paths
- File downloading with dynamic filenames
- Template-based formatting

## Available Pipeline Elements

Conduit includes many built-in pipeline elements:

- **Data Sources**: `Input`, `RestApi`, `Random`, `Glob`
- **Transformations**: `Filter`, `Format`, `JsonQuery`, `Extract`, `Replace`
- **Flow Control**: `Fork`, `Iterate`, `Identity`, `Empty`
- **Output**: `Console`, `DownloadFile`
- **System**: `Cli`, `FileInfo`, `Find`, `Path`
- **Data Processing**: `Numpy`, `Eval`

## Creating Custom Pipeline Elements

It's easy to extend conduit with your own pipeline elements! Here's how to create a custom element:

```python
from dataclasses import dataclass
from typing import Generator, Iterator, Optional
from ..pipelineElement import PipelineElement
import random

@dataclass
class RandomInput:
    """Input specification for Random element
  
    All fields are optional and will use constructor defaults if not provided.
    """
    seed: Optional[int] = None
    min: Optional[float] = None
    max: Optional[float] = None
    type: Optional[str] = None  # "float" or "int"

class Random(PipelineElement):
    """Generate random values (float or integer)"""
  
    def __init__(self, seed: int = None, min: float = 0, max: float = 1.0, type: str = "float"):
        super().__init__()  # Captures constructor parameters as defaults
  
    def process(self, input: Iterator[RandomInput]) -> Generator[float, None, None]:
        for random_input in input:
            # Apply constructor defaults to None fields
            random_input = self.apply_defaults(random_input)
          
            if random_input.seed is not None:
                random.seed(random_input.seed)
          
            if random_input.type == "int":
                yield random.randint(int(random_input.min), int(random_input.max))
            else:
                yield random.uniform(random_input.min, random_input.max)
```

### Key Concepts for Custom Elements:

1. **Dataclass Input**: Define a dataclass for typed input with optional fields
2. **Constructor Defaults**: Use `super().__init__()` to capture constructor parameters
3. **apply_defaults()**: Merge constructor defaults with per-datum input
4. **Lazy Processing**: Use generators (`yield`) to maintain lazy evaluation
5. **Type Safety**: Proper type hints for IDE support and validation

### Example Usage:

```yaml
---
# Generate 5 random integers between 1 and 100
- id: conduit.Input
  data:
    - max: 100
      min: 1
      type: "int"

- id: conduit.Random
- id: conduit.Console
  format: "Random number: {{input}}"
```

This demonstrates:

- Constructor-level defaults (seed, type, range)
- Per-datum configuration overrides via Input data
- Template-based output formatting

## Advanced Features

### True Lazy Evaluation

Conduit now implements fully lazy evaluation - data flows through the pipeline one item at a time without materializing intermediate results. This enables:

- **Memory Efficiency**: Process datasets larger than available RAM
- **Streaming**: Results appear as soon as they're computed
- **Early Termination**: Stop processing when you have enough results

### Environment Variable Support

Use environment variables in your YAML configurations with default values:

```yaml
- id: conduit.RestApi
  url: "${API_URL:-https://api.example.com}"
  timeout: ${TIMEOUT:-30}
```

### Fork Elements for Parallel Processing

Fork elements allow you to process data through multiple parallel paths:

```yaml
- id: conduit.Fork
  paths:
    metadata:  # Extract metadata
      - id: conduit.JsonQuery
        query: ".metadata"
    content:   # Process content
      - id: conduit.JsonQuery
        query: ".content"
      - id: conduit.Format
        template: "Processed: {{input}}"
```

### Template System

All string fields support Jinja2 templating with built-in path filters:

```yaml
- id: conduit.Console
  format: "File: {{input.path | get_filename}} ({{input.size}} bytes)"
```

Available filters: `get_filename`, `get_extension`, `get_basename`, `get_dirname`, and more.
