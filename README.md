# Conduit

**Conduit** is a streaming data pipeline framework that lets you build complex data processing workflows using simple YAML configurations instead of brittle scripts.

## Why Conduit?

Replace this:
```python
# Fragile, hard-to-modify script
data = fetch_api_data()
filtered = [item for item in data if item['status'] == 'active']
processed = [transform(item) for item in filtered]
for item in processed:
    print(f"Result: {item}")
```

With this:
```yaml
- id: conduit.RestApi
  url: "https://api.example.com/data"
- id: conduit.Filter
  condition: "input.status == 'active'"
- id: conduit.Transform
  template: "{{input | process}}"
- id: conduit.Console
  format: "Result: {{input}}"
```

## Key Benefits

- **🔧 Composable**: Mix and match 25+ built-in elements
- **⚡ Streaming**: Memory-efficient, lazy processing of large datasets  
- **🚀 Fast**: Get results as they're computed, not after everything finishes
- **🌐 API-Ready**: Built-in REST server for pipeline execution
- **🎯 Type-Safe**: Full IDE support with auto-completion and validation

## Quick Start

### Installation
```bash
pip install git+https://github.com/aniongithub/conduit.git
```

### Your First Pipeline
Create `hello.yaml`:
```yaml
- id: conduit.Input
  data: [{message: "Hello, Conduit!"}]
- id: conduit.Console
  format: "{{input.message}}"
```

Run it:
```bash
conduit-cli hello.yaml
# Output: Hello, Conduit!
```

### API Server
Start the server:
```bash
conduit-cli serve --host 0.0.0.0 --port 8000
```

Execute pipelines via REST:
```bash
curl -X POST http://localhost:8000/run \
  -H "Content-Type: application/json" \
  -d '{"pipeline": [
    {"id": "conduit.Input", "data": [{"name": "World"}]},
    {"id": "conduit.Console", "format": "Hello, {{input.name}}!"}
  ]}'
```

## Examples

### Process Files
```yaml
# Find and analyze Python files
- id: conduit.Glob
  pattern: "**/*.py"
- id: conduit.FileInfo
- id: conduit.Console
  format: "{{input.name}}: {{input.size}} bytes"
```

### Fetch API Data
```yaml
# Get Pokemon data with custom limit
- id: conduit.RestApi
  url: "https://pokeapi.co/api/v2/pokemon?limit=${limit:-5}"
- id: conduit.JsonQuery
  query: ".results[].name"
- id: conduit.Console
  format: "Pokemon: {{input}}"
```

Run with arguments:
```bash
conduit-cli pokemon.yaml --args limit=10
```

### Complex Workflows
```yaml
# Parallel processing with Fork
- id: conduit.RestApi
  url: "https://api.example.com/data"
- id: conduit.Fork
  paths:
    summary:
      - id: conduit.JsonQuery
        query: ".metadata.title"
    details:
      - id: conduit.JsonQuery
        query: ".content"
      - id: conduit.Filter
        condition: "len(input) > 100"
- id: conduit.Console
  format: "{{input.summary}}: {{input.details[:50]}}..."
```

### Using the API with Arguments
```bash
# Convert YAML to API request with yq
yq eval '{"pipeline": ., "args": {"limit": "10"}}' examples/pokemon_evolution.yaml -o=json | \
curl -X POST http://localhost:8000/run -H "Content-Type: application/json" -d @-
```

## Built-in Elements

| Category | Elements | Purpose |
|----------|----------|---------|
| **Input** | `Input`, `RestApi`, `Random`, `Glob` | Data sources and generation |
| **Transform** | `Filter`, `JsonQuery`, `Extract`, `Format` | Data processing and extraction |
| **Flow** | `Fork`, `Iterate`, `Identity`, `Empty` | Control flow and parallelization |
| **Output** | `Console`, `Download` | Results and file operations |
| **System** | `Cli`, `FileInfo`, `Find`, `Path` | System integration |

> **Need more?** Check the [full element reference](docs/elements.md) or [create custom elements](docs/custom-elements.md)

## Development

### Dev Container Setup
This repository is meant for development with a VS Code dev container:
1. Install [Docker](https://docker.com) and [VS Code](https://code.visualstudio.com)
2. Install the [Dev Containers extension](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers)
3. Open repository and select "Reopen in Container"
4. Press F5 to run example pipelines or the server

### Creating Custom Elements
```python
from dataclasses import dataclass
from typing import Generator, Iterator
from conduit import PipelineElement

@dataclass
class MyInput:
    value: str

class MyElement(PipelineElement):
    def process(self, input: Iterator[MyInput]) -> Generator[str, None, None]:
        for item in input:
            yield f"Processed: {item.value}"
```

### REST API Response Format
```json
{
  "success": true,
  "results": ["item1", "item2", "item3"],
  "stdout": ["Console output line 1", "Console output line 2"],
  "stderr": [],
  "stats": {
    "duration": 1.23,
    "total_items_processed": 3,
    "throughput": 2.44,
    "element_metrics": [...]
  }
}
```

## Learn More

- 🔧 [Element Reference](docs/elements.md) - Complete element documentation
- 🚀 [Examples](examples/) - Real-world pipeline examples
- 🐛 [Issues](https://github.com/aniongithub/conduit/issues) - Bug reports and feature requests

## License

MIT License - see [LICENSE](LICENSE) for details.
