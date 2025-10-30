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

- **🔧 Composable**: Mix and match built-in elements, or easily write your own
- **⚡ Streaming**: Memory-efficient, lazy processing of large datasets
- **🚀 Fast**: Get results as they're computed, not after everything finishes
- **🌐 API-Ready**: Built-in REST server for pipeline execution
- **🎯 Type-Safe**: Full IDE support with auto-completion and validation

## Quick Start

### Docker (Recommended)

The easiest way to try or deploy Conduit - no installation required!

### Quick Test

```bash
# Run a simple hello world pipeline
docker run --rm aniondocker/conduit:latest run examples/hello_world.yaml
```

### Run Examples

**Pokemon API downloader** - Fetches Pokemon data and downloads official artwork images

```bash
# Downloads pokemon images to ./pokemon_images (requires volume mount for file access)
docker run --rm -v $(pwd):/data -w /data aniondocker/conduit:latest run examples/pokemon_api.yaml

# Download 20 Pokemon instead of default 10
docker run --rm -v $(pwd):/data -w /data aniondocker/conduit:latest run examples/pokemon_api.yaml --args limit=20
```

**File processing** - Analyzes files in your directory and shows their sizes

```bash
# Analyzes *.py files in current directory (requires volume mount to access your files)
docker run --rm -v $(pwd):/data -w /data aniondocker/conduit:latest run examples/file_sizes.yaml
```

**Pokemon evolution chains** - Complex workflow showing parallel data fetching and processing

```bash
# Fetches Pokemon data and maps out evolution relationships
docker run --rm -v $(pwd):/data -w /data aniondocker/conduit:latest run examples/pokemon_evolution.yaml
```

**Data grouping** - Demonstrates grouping and aggregation of data sets

```bash
# Groups sample data by category and shows aggregated results
docker run --rm -v $(pwd):/data -w /data aniondocker/conduit:latest run examples/groupby_example.yaml
```

**Data sorting** - Shows how to sort data using custom keys

```bash
# Sorts sample data by different criteria
docker run --rm -v $(pwd):/data -w /data aniondocker/conduit:latest run examples/sort_example.yaml
```

**Pokemon filtering** - Filters Pokemon by specific criteria (type, stats, etc.)

```bash
# Filters Pokemon list based on criteria like type or generation
docker run --rm -v $(pwd):/data -w /data aniondocker/conduit:latest run examples/pokemon_filter.yaml
```

**SFTP file operations** - List and download files from SFTP servers (uses public test server)

```bash
# Lists files from test SFTP server, filters by size, and downloads
docker run --rm -v $(pwd):/data -w /data aniondocker/conduit:latest run examples/sftp_rebex_example.yaml
```

**CSV processing** - Download and process CSV files with grouping and aggregation

```bash
# Downloads CSV from Google Drive, groups by country, and displays results
docker run --rm aniondocker/conduit:latest run examples/csv_example.yaml
```

**Custom elements** - Demonstrates extending Conduit with user-defined processing elements

```bash
# Shows how custom elements work alongside built-in ones
docker run --rm -v $(pwd):/data -w /data aniondocker/conduit:latest run examples/custom_element_example.yaml

# Run your own pipeline files
docker run --rm -v $(pwd):/data -w /data aniondocker/conduit:latest run your-pipeline.yaml
```

### Run API Server

```bash
# Start the server (accessible on http://localhost:8000)
docker run --rm -p 8000:8000 aniondocker/conduit:latest serve --host 0.0.0.0

# Test the server
curl -X POST http://localhost:8000/run \
  -H "Content-Type: application/json" \
  -d '{"pipeline": [
    {"id": "conduit.Input", "data": [{"name": "Docker"}]},
    {"id": "conduit.Console", "format": "Hello from {{input.name}}!"}
  ]}'
```

### Custom Elements

Mount your custom elements directory to extend Conduit:

```bash
# Create your custom element
mkdir my-elements
cat > my-elements/MyCustom.py << 'EOF'
from conduit.pipelineElement import PipelineElement
from typing import Iterator
from dataclasses import dataclass

@dataclass  
class MyCustomInput:
    message: str = "Hello from my custom element!"

class MyCustom(PipelineElement):
    def process(self, input: Iterator[MyCustomInput]) -> Iterator[dict]:
        for item in input:
            yield {"custom_output": f"🚀 {item.message}"}
EOF

# Create package init file
echo "from .MyCustom import MyCustom" > my-elements/__init__.py

# Use your custom element
docker run --rm -v $(pwd)/my-elements:/elements aniondocker/conduit:latest run - << 'EOF'
- id: conduit.Input
  data: [{"message": "Docker + Custom Elements!"}]
- id: elements.MyCustom  
- id: conduit.Console
  format: "{{input.custom_output}}"
EOF
```

### Local Installation

If you prefer to install locally:

```bash
pip install git+https://github.com/aniongithub/conduit.git
```

Create `hello.yaml`:

```yaml
- id: conduit.Input
  data: [{message: "Hello, Conduit!"}]
- id: conduit.Console
  format: "{{input.message}}"
```

Run it:

```bash
conduit-cli run hello.yaml
# Output: Hello, Conduit!
```

Start the API server:

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

***Note**: This approach is not recommended, use docker or devcontainers for the most supported and easiest path*

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


| Category      | Elements                                   | Purpose                          |
| --------------- | -------------------------------------------- | ---------------------------------- |
| **Input**     | `Input`, `RestApi`, `Random`, `Glob`       | Data sources and generation      |
| **Transform** | `Filter`, `JsonQuery`, `Extract`, `Format` | Data processing and extraction   |
| **Data**      | `CsvReader`, `GroupBy`, `Sort`             | Data parsing and organization    |
| **Flow**      | `Fork`, `Iterate`, `Identity`, `Empty`     | Control flow and parallelization |
| **Output**    | `Console`, `DownloadFile`                  | Results and file operations      |
| **Network**   | `SftpList`, `SftpDownload`                 | SFTP file listing and transfer   |
| **System**    | `Cli`, `FileInfo`, `Find`, `Path`          | System integration               |

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
