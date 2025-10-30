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

## Network Elements

### conduit.SftpList
Lists files on an SFTP server and emits metadata for each file.

**Parameters:**
- `hostname` (str): SFTP server hostname
- `username` (str): Username for authentication
- `password` (str, optional): Password for authentication
- `private_key_path` (str, optional): Path to SSH private key file
- `port` (int): SFTP server port (default: 22)
- `timeout` (int): Connection timeout in seconds (default: 30)
- `allow_agent` (bool): Allow SSH agent for key authentication (default: false)
- `look_for_keys` (bool): Look for keys in ~/.ssh (default: false)

**Input:**
- `remote_path` (str): Path to list on the SFTP server
- `glob_pattern` (str, optional): Glob pattern to filter files (e.g., "*.csv")
- `recursive` (bool): Recursively list subdirectories (default: false)
- `list_dirs` (bool): Include directories in output (default: false)

**Output:**
Metadata dict for each file with keys:
- `filename` (str): Name of the file
- `remote_path` (str): Full remote path
- `size` (int): File size in bytes (None for directories)
- `is_directory` (bool): Whether the item is a directory
- `mtime` (str): Last modification time (ISO8601 format)
- `depth` (int): Directory depth (for recursive listings)
- `attrs` (dict): Raw server attributes

**Example:**
```yaml
- id: conduit.Input
  data:
    - remote_path: "/pub/data/"
      glob_pattern: "*.csv"
      recursive: true
- id: conduit.SftpList
  hostname: "sftp.example.com"
  username: "myuser"
  password: "mypass"
  port: 22
  timeout: 30
```

### conduit.SftpDownload
Downloads files from an SFTP server given remote paths or metadata from SftpList.

**Parameters:**
- `hostname` (str): SFTP server hostname
- `username` (str): Username for authentication
- `password` (str, optional): Password for authentication
- `private_key_path` (str, optional): Path to SSH private key file
- `port` (int): SFTP server port (default: 22)
- `timeout` (int): Connection timeout in seconds (default: 30)
- `download_mode` (str): How to handle downloaded files:
  - `"memory"`: Keep files in memory as BytesIO objects (default)
  - `"temp"`: Download to temporary files
  - `"local"`: Download to specified local directory
- `local_dir` (str, optional): Local directory for downloads (required if download_mode="local")
- `allow_agent` (bool): Allow SSH agent for key authentication (default: false)
- `look_for_keys` (bool): Look for keys in ~/.ssh (default: false)

**Input:**
Accepts either:
- A string containing the remote file path
- A dict with at least `remote_path` key (as produced by SftpList)

**Output:**
Dict with keys:
- `filename` (str): Name of the file
- `remote_path` (str): Remote path
- `file_obj` (BytesIO): File object (if mode="memory")
- `local_path` (str): Local file path (if mode="temp" or mode="local")
- `size` (int): File size in bytes
- `mode` (str): Download mode used
- Plus any metadata keys preserved from input (mtime, depth, attrs)

**Example - List then Download:**
```yaml
# Step 1: List files on SFTP server
- id: conduit.Input
  data:
    - remote_path: "/data/reports/"
      glob_pattern: "*.csv"
      recursive: true
- id: conduit.SftpList
  hostname: "sftp.example.com"
  username: "myuser"
  password: "mypass"

# Step 2: Filter by size (only files > 1KB)
- id: conduit.Filter
  condition: "not item.is_directory and (item.size or 0) > 1024"

# Step 3: Download selected files
- id: conduit.SftpDownload
  hostname: "sftp.example.com"
  username: "myuser"
  password: "mypass"
  download_mode: "local"
  local_dir: "./downloads"

# Step 4: Process downloaded files
- id: conduit.Console
  format: "Downloaded: {{input.filename}} ({{input.size}} bytes)"
```

**Authentication Notes:**
- Either `password` or `private_key_path` must be provided
- Set `allow_agent=true` to use SSH agent authentication
- Set `look_for_keys=true` to automatically search for keys in ~/.ssh
- By default, agent and key lookups are disabled to avoid GUI passphrase prompts during unattended runs

## Data Processing Elements

### conduit.CsvReader
Reads CSV files and yields each row as a dictionary.

**Parameters:**
- `delimiter` (str): Field delimiter character (default: ",")
- `quotechar` (str): Quote character for fields (default: '"')
- `encoding` (str): Text encoding (default: "utf-8")
- `skip_empty_rows` (bool): Skip rows with no data (default: true)
- `fieldnames` (list[str], optional): Custom field names for headerless CSV files

**Input:**
Accepts any of:
- A string containing a file path
- A file-like object (e.g., BytesIO from DownloadFile)
- A dict with one of these keys:
  - `file_obj`: File-like object
  - `local_path`: Path to local file
  - `remote_path`: Path to remote file
  - `path`: Generic path

**Output:**
Dict for each CSV row with field names as keys

**Example:**
```yaml
# Read CSV from downloaded file
- id: conduit.Input
  data:
    - url: "https://example.com/data.csv"

- id: conduit.DownloadFile
  output_dir: "/tmp"
  
- id: conduit.CsvReader
  delimiter: ","
  encoding: "utf-8"
  skip_empty_rows: true
  
- id: conduit.Console
  format: "{{input.name}}: {{input.email}}"
```

**Complete Example with Grouping:**
```yaml
# Download, parse, and group CSV data
- id: conduit.Input
  data:
    - url: "https://example.com/customers.csv"
      filename: "customers.csv"

- id: conduit.DownloadFile
  output_dir: "/tmp"

- id: conduit.CsvReader

- id: conduit.GroupBy
  key: "input['Country']"

- id: conduit.Console
  format: |
    === {{input.key}} ({{input.values|length}} customers) ===
    {% for customer in input.values %}
    - {{customer.Name}} ({{customer.Email}})
    {% endfor %}
```

**Notes:**
- Uses Python's built-in `csv.DictReader` for robust CSV parsing
- Automatically handles different input types (paths, file objects, dicts)
- Preserves metadata from previous elements when input is a dict
- Supports various text encodings for international data
- Works seamlessly with DownloadFile, SftpDownload, and other file sources

### conduit.GroupBy
Groups items by a key expression and outputs grouped results.

**Parameters:**
- `key` (str): Python expression to extract grouping key (use `input` variable)
- `value` (str, optional): Python expression to extract values (default: entire input)

**Input:**
Any data items to be grouped

**Output:**
Dict with keys:
- `key` (str): The grouping key
- `values` (list): List of items in this group

**Example:**
```yaml
# Group by category
- id: conduit.GroupBy
  key: "input['category']"
  
# Access nested fields
- id: conduit.GroupBy
  key: "input.user.country"
```

### conduit.Sort
Sorts items by a key expression.

**Parameters:**
- `key` (str): Python expression to extract sort key (use `input` variable)
- `reverse` (bool): Sort in descending order (default: false)

**Example:**
```yaml
- id: conduit.Sort
  key: "input['score']"
  reverse: true  # Highest scores first
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