# Pipeline Elements Reference

This document provides a comprehensive reference for all built-in Conduit pipeline elements.

## Input Elements

### conduit.Input
Provides static data to start a pipeline.

**Parameters:**
- `data` (list): List of data items to inject into the pipeline

**Example:**
```yaml
- id: conduit.Input
  data:
    - name: "Alice"
      age: 30
    - name: "Bob" 
      age: 25
```

### conduit.RestApi
Fetches data from REST APIs.

**Parameters:**
- `url` (str): API endpoint URL
- `method` (str): HTTP method (GET, POST, PUT, DELETE)
- `headers` (dict): HTTP headers
- `response_format` (str): "json" or "text"
- `timeout` (int): Request timeout in seconds

**Example:**
```yaml
- id: conduit.RestApi
  url: "https://api.github.com/users/octocat"
  method: "GET"
  response_format: "json"
```

### conduit.Random
Generates random numbers.

**Parameters:**
- `type` (str): "int" or "float"
- `min` (float): Minimum value
- `max` (float): Maximum value
- `seed` (int): Random seed for reproducibility

**Example:**
```yaml
- id: conduit.Random
  type: "int"
  min: 1
  max: 100
```

### conduit.Glob
Finds files matching patterns.

**Parameters:**
- `pattern` (str): Glob pattern (e.g., "*.py", "**/*.json")
- `root_dir` (str): Directory to search from
- `recursive` (bool): Enable recursive search

**Example:**
```yaml
- id: conduit.Glob
  pattern: "**/*.yaml"
  root_dir: "./examples"
  recursive: true
```

## Transform Elements

### conduit.Filter
Filters items based on conditions.

**Parameters:**
- `condition` (str): Python expression to evaluate
- `keep_matching` (bool): Keep items that match (true) or don't match (false)

**Example:**
```yaml
- id: conduit.Filter
  condition: "input.age >= 18"
  keep_matching: true
```

### conduit.JsonQuery
Extracts data using jq-style queries.

**Parameters:**
- `query` (str): jq query expression

**Example:**
```yaml
- id: conduit.JsonQuery
  query: ".users[].name"
```

### conduit.Extract
Extracts data using regex patterns.

**Parameters:**
- `pattern` (str): Regular expression pattern
- `group` (int): Capture group to extract (default: 1)
- `all_matches` (bool): Return all matches or just the first

**Example:**
```yaml
- id: conduit.Extract
  pattern: "email: ([\\w.-]+@[\\w.-]+)"
  group: 1
```

### conduit.Format
Formats data using templates.

**Parameters:**
- `template` (str): Jinja2 template string

**Example:**
```yaml
- id: conduit.Format
  template: "Hello, {{input.name}}! You are {{input.age}} years old."
```

### conduit.Replace
Replaces text using regex patterns.

**Parameters:**
- `pattern` (str): Regular expression pattern
- `replacement` (str): Replacement string
- `count` (int): Maximum number of replacements (0 = all)

**Example:**
```yaml
- id: conduit.Replace
  pattern: "\\s+"
  replacement: "_"
```

## Flow Control Elements

### conduit.Fork
Splits data into parallel processing paths.

**Parameters:**
- `paths` (dict): Named paths with their element lists

**Example:**
```yaml
- id: conduit.Fork
  paths:
    metadata:
      - id: conduit.JsonQuery
        query: ".meta"
    content:
      - id: conduit.JsonQuery
        query: ".data"
      - id: conduit.Filter
        condition: "len(input) > 0"
```

### conduit.Iterate
Expands arrays into individual items.

**Parameters:**
- None (processes input arrays automatically)

**Example:**
```yaml
# Input: [1, 2, 3] → Output: 1, 2, 3 (as separate items)
- id: conduit.Iterate
```

### conduit.Identity
Passes data through unchanged (useful for debugging).

**Parameters:**
- None

**Example:**
```yaml
- id: conduit.Identity  # No-op for debugging
```

### conduit.Empty
Generates empty data (useful in Fork paths).

**Parameters:**
- None

**Example:**
```yaml
- id: conduit.Empty  # Outputs None
```

## Output Elements

### conduit.Console
Prints formatted output to stdout.

**Parameters:**
- `format` (str): Template string for output formatting

**Example:**
```yaml
- id: conduit.Console
  format: "Processing: {{input.filename}} ({{input.size}} bytes)"
```

### conduit.Download
Downloads files from URLs.

**Parameters:**
- `output_dir` (str): Directory to save files
- `filename` (str): Custom filename (optional)
- `create_dirs` (bool): Create directories if they don't exist
- `overwrite` (bool): Overwrite existing files

**Example:**
```yaml
- id: conduit.Download
  output_dir: "./downloads"
  create_dirs: true
  overwrite: false
```

## System Elements

### conduit.Cli
Executes command-line programs.

**Parameters:**
- `command` (str): Command to execute
- `args` (list): Command arguments
- `capture_output` (bool): Capture stdout/stderr
- `shell` (bool): Use shell for execution

**Example:**
```yaml
- id: conduit.Cli
  command: "ls"
  args: ["-la", "./"]
  capture_output: true
```

### conduit.FileInfo
Gets information about files.

**Parameters:**
- None (operates on file paths from input)

**Example:**
```yaml
- id: conduit.FileInfo
# Input: "/path/to/file.txt"
# Output: {name: "file.txt", size: 1024, path: "/path/to/file.txt", ...}
```

### conduit.Find 
Searches for files and directories.

**Parameters:**
- `path` (str): Search path
- `name` (str): Name pattern
- `type` (str): "f" (files), "d" (directories), or "both"
- `max_depth` (int): Maximum search depth

**Example:**
```yaml
- id: conduit.Find
  path: "./src"
  name: "*.py"
  type: "f"
  max_depth: 3
```

### conduit.Path
Manipulates file paths.

**Parameters:**
- `operation` (str): "dirname", "basename", "extension", "join", "absolute"
- `parts` (list): Path parts for join operation

**Example:**
```yaml
- id: conduit.Path
  operation: "basename"
# Input: "/path/to/file.txt" → Output: "file.txt"
```

## Data Processing Elements

### conduit.Numpy
Performs NumPy operations on arrays.

**Parameters:**
- `operation` (str): NumPy operation name
- `axis` (int): Operation axis
- `dtype` (str): Data type for conversion

**Example:**
```yaml
- id: conduit.Numpy
  operation: "mean"
  axis: 0
```

### conduit.Eval
Evaluates Python expressions safely.

**Parameters:**
- `expression` (str): Python expression to evaluate
- `globals` (dict): Global variables for evaluation

**Example:**
```yaml
- id: conduit.Eval
  expression: "input * 2 + 1"
```

## Common Patterns

### Environment Variables
All string parameters support environment variable expansion:
```yaml
- id: conduit.RestApi
  url: "${API_URL:-https://api.example.com}"
  timeout: ${TIMEOUT:-30}
```

### Template Filters
Format elements support built-in Jinja2 filters:
```yaml
- id: conduit.Format
  template: "{{input.path | get_filename}} is {{input.size | filesizeformat}}"
```

Available filters:
- `get_filename` - Extract filename from path
- `get_dirname` - Extract directory from path  
- `get_extension` - Extract file extension
- `filesizeformat` - Format bytes as human-readable size

### Error Handling
Use `stop_on_error` parameter to control pipeline behavior:
```yaml
# In pipeline configuration
stop_on_error: false  # Continue processing even if elements fail
```

## Custom Elements

See [custom-elements.md](custom-elements.md) for detailed instructions on creating your own pipeline elements.