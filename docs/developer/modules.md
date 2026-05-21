# Module Documentation

Detailed documentation for each module in the Token Telemetry system.

## Overview

This document provides comprehensive documentation for each module, including:
- Purpose and responsibilities
- Key classes and functions
- Usage examples
- Internal details

## Module Index

| Module | Purpose | Key Classes/Functions |
|--------|---------|----------------------|
| [`config.py`](config.md) | Configuration management | `Config`, `load_config()` |
| [`database.py`](database.md) | Database operations | `Database`, `get_database()` |
| [`cost_calculator.py`](cost_calculator.md) | Cost computation | `CostCalculator`, `calculate_cost()` |
| [`models.py`](models.md) | Data models | `CallRecord`, `SummaryStats` |
| [`proxy.py`](proxy.md) | HTTP proxy server | `ProxyServer`, `TelemetryHandler` |
| [`reporter.py`](reporter.md) | Summary generation | `Reporter`, `generate_summary()` |
| [`cli.py`](cli.md) | CLI interface | `main()`, `parse_args()` |
| [`__init__.py`](init.md) | Package initialization | Lazy imports |

---

## config.py - Configuration Management

### Purpose

Handles loading, merging, and validating configuration from multiple sources with hierarchical priority.

### Key Classes

#### `Config`

Main configuration dataclass containing all configuration values.

**Attributes:**

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| `proxy` | ProxyConfig | ProxyConfig() | Proxy server configuration |
| `mistral` | MistralConfig | MistralConfig() | Mistral API configuration |
| `database` | DatabaseConfig | DatabaseConfig() | Database configuration |
| `logging` | LoggingConfig | LoggingConfig() | Logging configuration |
| `pricing` | Dict[str, Dict[str, float]] | {} | Pricing configuration |

**Sub-classes:**

```python
@dataclass
class ProxyConfig:
    host: str = "localhost"
    port: int = 8000

@dataclass
class MistralConfig:
    base_url: str = "https://api.mistral.ai"

@dataclass
class DatabaseConfig:
    path: str = "telemetry.db"

@dataclass
class LoggingConfig:
    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    file: str = "telemetry.log"
```

### Key Functions

#### `load_config(config_path: Optional[str] = None) -> Config`

Load configuration from files and environment variables.

**Parameters:**
- `config_path`: Optional path to a specific configuration file. If None, checks for `config/local.yaml`.

**Returns:**
- `Config` object with all configuration values loaded and merged.

**Priority Order:**
1. Environment Variables
2. User Configuration File (specified or `config/local.yaml`)
3. Default Configuration File (`config/default_config.yaml`)
4. Package Defaults

**Example:**
```python
from token_telemetry.config import load_config

# Load default configuration
config = load_config()
print(config.proxy.port)  # 8000

# Load custom configuration
config = load_config(config_path="config/production.yaml")
```

#### `get_config_path() -> Optional[Path]`

Get the path to the user's configuration file.

**Returns:**
- Path to configuration file, or None if not found.

**Search Order:**
1. `config/local.yaml`
2. `config.yaml` (current directory)

### Internal Functions

#### `_load_yaml_file(path: Path) -> Dict[str, Any]`

Load a YAML configuration file.

**Requires:** PyYAML package

#### `_load_json_file(path: Path) -> Dict[str, Any]`

Load a JSON configuration file.

#### `_merge_configs(base: Dict, override: Dict) -> Dict`

Recursively merge two configuration dictionaries.

**Behavior:**
- Nested dictionaries are merged recursively
- Other values are overridden
- Base dictionary is not modified

#### `_load_env_config() -> Dict[str, Any]`

Load configuration from environment variables.

**Environment Variable Mappings:**

| Environment Variable | Config Path | Type |
|---------------------|-------------|------|
| `TELEMETRY_PROXY_HOST` | `proxy.host` | str |
| `TELEMETRY_PROXY_PORT` | `proxy.port` | int |
| `MISTRAL_BASE_URL` | `mistral.base_url` | str |
| `TELEMETRY_DB_PATH` | `database.path` | str |

**Note:** These environment variables configure the **Token Telemetry proxy server**. To configure **Vibe CLI** to use the proxy, you must edit Vibe CLI's configuration (see user documentation for details).

#### `_parse_pricing_config(pricing_data: Dict) -> Dict[str, Dict[str, float]]`

Parse pricing configuration into standardized format.

**Input:** Raw pricing data from config file
**Output:** Normalized pricing with `input` and `output` keys

**Example:**
```python
# Input
{"mistral-medium": {"input": 0.25, "output": 0.75}}

# Output
{"mistral-medium": {"input": 0.25, "output": 0.75}}
```

### Usage Examples

```python
from token_telemetry.config import load_config, Config, ProxyConfig

# Load configuration
config = load_config()

# Access values
print(f"Proxy will run on {config.proxy.host}:{config.proxy.port}")
print(f"Mistral API endpoint: {config.mistral.base_url}")
print(f"Database path: {config.database.path}")

# Modify configuration
config.proxy.port = 9000
config.pricing["my-model"] = {"input": 0.50, "output": 1.00}

# Create config programmatically
config = Config(
    proxy=ProxyConfig(host="0.0.0.0", port=8080),
    database=DatabaseConfig(path="/var/lib/telemetry.db"),
)
```

---

## database.py - Database Access Layer

### Purpose

Provides SQLite database operations for storing and retrieving telemetry data with thread-safe connection handling.

### Key Classes

#### `Database`

SQLite database manager for telemetry data.

**Attributes:**
- `db_path`: Path to the SQLite database file
- `_lock`: Threading lock for initialization
- `_initialized`: Initialization flag

**Database Schema:**
```sql
CREATE TABLE IF NOT EXISTS calls (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    model TEXT NOT NULL,
    endpoint TEXT NOT NULL,
    origin TEXT NOT NULL,
    request_tokens INTEGER NOT NULL DEFAULT 0,
    response_tokens INTEGER NOT NULL DEFAULT 0,
    processing_time REAL NOT NULL DEFAULT 0.0,
    status_code INTEGER NOT NULL DEFAULT 0,
    cost REAL NOT NULL DEFAULT 0.0
);

CREATE INDEX idx_calls_timestamp ON calls(timestamp);
CREATE INDEX idx_calls_model ON calls(model);
CREATE INDEX idx_calls_origin ON calls(origin);
```

**Methods:**

##### `__init__(db_path: str = "telemetry.db")`

Initialize the database manager.

**Parameters:**
- `db_path`: Path to the SQLite database file

**Behavior:**
- Ensures parent directory exists
- Initializes thread-local storage

##### `insert_record(record: CallRecord) -> int`

Insert a telemetry record into the database.

**Parameters:**
- `record`: CallRecord object to insert

**Returns:**
- ID of the inserted record

**Example:**
```python
from token_telemetry.database import Database
from token_telemetry.models import CallRecord

db = Database("telemetry.db")
record = CallRecord(
    timestamp="2026-05-19T14:30:45",
    model="mistral-medium",
    endpoint="/v1/chat/completions",
    origin="user",
    request_tokens=1000,
    response_tokens=500,
    processing_time=1.234,
    status_code=200,
    cost=0.001125,
)
record_id = db.insert_record(record)
```

##### `get_record(record_id: int) -> Optional[CallRecord]`

Get a single telemetry record by ID.

**Parameters:**
- `record_id`: ID of the record to retrieve

**Returns:**
- CallRecord object or None if not found

##### `get_records(limit: Optional[int] = None, offset: int = 0, model: Optional[str] = None, origin: Optional[str] = None, start_date: Optional[str] = None, end_date: Optional[str] = None) -> List[CallRecord]`

Get multiple telemetry records with optional filtering.

**Parameters:**
- `limit`: Maximum number of records to return
- `offset`: Offset for pagination
- `model`: Filter by model name
- `origin`: Filter by origin
- `start_date`: Filter by start date (ISO format)
- `end_date`: Filter by end date (ISO format)

**Returns:**
- List of CallRecord objects

**Example:**
```python
# Get all records for mistral-medium
records = db.get_records(model="mistral-medium")

# Get last 10 records
records = db.get_records(limit=10)

# Get records from last week
from datetime import datetime, timedelta
start = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%dT00:00:00")
records = db.get_records(start_date=start)
```

##### `get_summary_stats(model: Optional[str] = None, origin: Optional[str] = None, start_date: Optional[str] = None, end_date: Optional[str] = None) -> SummaryStats`

Get aggregated summary statistics.

**Parameters:** Same as `get_records()`

**Returns:**
- SummaryStats object with:
  - `total_calls`: Total number of calls
  - `total_request_tokens`: Sum of all request tokens
  - `total_response_tokens`: Sum of all response tokens
  - `total_cost`: Sum of all costs
  - `by_model`: Statistics grouped by model
  - `by_origin`: Statistics grouped by origin

**Example:**
```python
from token_telemetry.database import Database

db = Database("telemetry.db")
stats = db.get_summary_stats()

print(f"Total calls: {stats.total_calls}")
print(f"Total cost: ${stats.total_cost:.6f}")

# Get stats for specific model
stats = db.get_summary_stats(model="mistral-medium")
```

##### `get_records_by_date(date: str) -> List[CallRecord]`

Get all records for a specific date.

**Parameters:**
- `date`: Date in ISO format (YYYY-MM-DD)

##### `get_records_by_week(year: int, week: int) -> List[CallRecord]`

Get all records for a specific week.

**Parameters:**
- `year`: Year number
- `week`: Week number (1-53)

##### `get_records_by_month(year: int, month: int) -> List[CallRecord]`

Get all records for a specific month.

**Parameters:**
- `year`: Year number
- `month`: Month number (1-12)

##### `delete_records(model: Optional[str] = None, origin: Optional[str] = None, start_date: Optional[str] = None, end_date: Optional[str] = None) -> int`

Delete records matching the specified criteria.

**Returns:**
- Number of records deleted

##### `clear_all() -> int`

Clear all records from the database.

**Returns:**
- Number of records deleted

##### `get_total_count() -> int`

Get the total number of records in the database.

##### `vacuum() -> None`

Run VACUUM to optimize the database.

### Thread Safety

The Database class uses:
- **Thread-local connection storage**: Each thread has its own connection
- **Per-database connection**: Connections are keyed by database path
- **WAL mode**: Enabled for better concurrency
- **Threading lock**: Used for initialization only

**Safe for:**
- Multiple threads reading and writing
- Concurrent access from proxy handler threads

### Context Managers

##### `@contextmanager get_cursor()`

Context manager for getting a database cursor.

**Yields:**
- SQLite cursor object

**Behavior:**
- Automatically commits on success
- Rolls back on exception
- Closes cursor on exit

**Example:**
```python
with db.get_cursor() as cursor:
    cursor.execute("SELECT * FROM calls WHERE model = ?", ("mistral-medium",))
    rows = cursor.fetchall()
# Cursor automatically closed, transaction committed
```

### Global Functions

#### `get_database(db_path: Optional[str] = None) -> Database`

Get or create a global database instance.

**Parameters:**
- `db_path`: Optional path to the database file

**Returns:**
- Database instance

**Example:**
```python
from token_telemetry.database import get_database

db = get_database()  # Uses default path
# or
db = get_database("/custom/path/telemetry.db")
```

#### `reset_database() -> None`

Reset the global database instance.

---

## cost_calculator.py - Cost Calculation Engine

### Purpose

Computes API call costs based on token usage and model-specific pricing.

### Key Classes

#### `CostCalculator`

Cost calculator that computes API call costs.

**Attributes:**
- `pricing`: Dictionary containing pricing configuration

**Default Pricing:**
```python
DEFAULT_PRICING = {
    "default": {"input": 0.25, "output": 0.75},
    "mistral-tiny": {"input": 0.25, "output": 0.75},
    "mistral-small": {"input": 0.25, "output": 0.75},
    "mistral-medium": {"input": 0.25, "output": 0.75},
    "mistral-large": {"input": 0.25, "output": 0.75},
    "codestral-latest": {"input": 0.25, "output": 0.75},
}
```

**Methods:**

##### `__init__(pricing_config: Optional[Dict] = None)`

Initialize the cost calculator.

**Parameters:**
- `pricing_config`: Optional pricing configuration dictionary. If None, uses default pricing.

**Behavior:**
- Deep copies the pricing configuration
- Ensures default pricing is present
- Fills in missing keys (input/output) with defaults

##### `calculate_cost(model: str, input_tokens: int = 0, output_tokens: int = 0) -> float`

Calculate the cost for an API call.

**Parameters:**
- `model`: The model name
- `input_tokens`: Number of input (prompt) tokens
- `output_tokens`: Number of output (completion) tokens

**Returns:**
- Cost in USD

**Raises:**
- `ValueError`: If token counts are negative

**Formula:**
```python
cost = (input_tokens / 1_000_000) * input_rate + (output_tokens / 1_000_000) * output_rate
```

**Example:**
```python
from token_telemetry.cost_calculator import CostCalculator

calculator = CostCalculator()
cost = calculator.calculate_cost("mistral-medium", 1000, 2000)
# cost = (1000/1M)*0.25 + (2000/1M)*0.75 = 0.000250 + 0.001500 = 0.001750
```

##### `get_pricing_for_model(model: str) -> Dict[str, float]`

Get the pricing configuration for a specific model.

**Parameters:**
- `model`: The model name

**Returns:**
- Dictionary with 'input' and 'output' rates

**Behavior:**
- Falls back to default pricing if model not found
- Logs warning if model not found

##### `get_all_models() -> List[str]`

Get a list of all configured models.

**Returns:**
- List of model names

##### `add_model(model: str, input_rate: float = 0.25, output_rate: float = 0.75) -> None`

Add a new model with custom pricing.

**Parameters:**
- `model`: Model name
- `input_rate`: Input token rate per 1M tokens
- `output_rate`: Output token rate per 1M tokens

**Example:**
```python
calculator.add_model("my-custom-model", input_rate=0.50, output_rate=1.00)
```

##### `update_model(model: str, input_rate: Optional[float] = None, output_rate: Optional[float] = None) -> None`

Update pricing for an existing model.

**Parameters:**
- `model`: Model name
- `input_rate`: New input token rate (optional)
- `output_rate`: New output token rate (optional)

**Behavior:**
- Adds model if it doesn't exist
- Updates only specified rates

##### `remove_model(model: str) -> None`

Remove a model from the pricing configuration.

**Parameters:**
- `model`: Model name to remove

**Behavior:**
- Does not remove 'default' model
- Logs info message

### Global Functions

#### `get_cost_calculator(pricing_config: Optional[Dict] = None) -> CostCalculator`

Get or create a global cost calculator instance.

**Parameters:**
- `pricing_config`: Optional pricing configuration

**Returns:**
- CostCalculator instance

#### `calculate_cost(model: str, input_tokens: int = 0, output_tokens: int = 0, pricing_config: Optional[Dict] = None) -> float`

Convenience function to calculate cost for an API call.

**Parameters:**
- `model`: The model name
- `input_tokens`: Number of input tokens
- `output_tokens`: Number of output tokens
- `pricing_config`: Optional pricing configuration

**Returns:**
- Cost in USD

**Example:**
```python
from token_telemetry.cost_calculator import calculate_cost

cost = calculate_cost("mistral-medium", 1000, 2000)
```

#### `reset_cost_calculator() -> None`

Reset the global cost calculator instance.

### Usage Examples

```python
from token_telemetry.cost_calculator import CostCalculator, calculate_cost

# Method 1: Using the class
calculator = CostCalculator()
cost = calculator.calculate_cost("mistral-medium", 1000, 2000)

# Method 2: Using the convenience function
cost = calculate_cost("mistral-medium", 1000, 2000)

# Custom pricing
custom_pricing = {
    "my-model": {"input": 0.50, "output": 1.00},
    "default": {"input": 0.25, "output": 0.75},
}
calculator = CostCalculator(custom_pricing)
cost = calculator.calculate_cost("my-model", 1000, 2000)

# Add a new model at runtime
calculator.add_model("new-model", input_rate=0.30, output_rate=0.90)
```

---

## models.py - Data Models

### Purpose

Defines the data structures used throughout the telemetry system.

### Key Classes

#### `CallRecord`

Represents a single API call telemetry record.

**Attributes:**

| Attribute | Type | Description |
|-----------|------|-------------|
| `timestamp` | str | ISO 8601 formatted timestamp |
| `model` | str | Name of the model used |
| `endpoint` | str | API endpoint URL |
| `origin` | str | Call initiator (user, agent, sub-agent) |
| `request_tokens` | int | Number of tokens in the request |
| `response_tokens` | int | Number of tokens in the response |
| `processing_time` | float | Time taken to process the request (seconds) |
| `status_code` | int | HTTP status code |
| `cost` | float | Calculated cost for the call (USD) |

**Methods:**

##### `total_tokens() -> int`

Calculate total tokens (request + response).

**Returns:**
- Sum of request_tokens and response_tokens

##### `to_dict() -> Dict`

Convert to dictionary representation.

**Returns:**
- Dictionary with all attributes

##### `@classmethod from_dict(data: Dict) -> CallRecord`

Create CallRecord from dictionary.

**Parameters:**
- `data`: Dictionary with attribute values

**Returns:**
- CallRecord instance

**Behavior:**
- Uses current timestamp if not provided
- Uses "unknown" for model if not provided
- Uses "unknown" for origin if not provided
- Uses 0 for numeric fields if not provided

**Example:**
```python
from token_telemetry.models import CallRecord

# Create from attributes
record = CallRecord(
    timestamp="2026-05-19T14:30:45.123456",
    model="mistral-medium",
    endpoint="/v1/chat/completions",
    origin="user",
    request_tokens=1000,
    response_tokens=500,
    processing_time=1.234,
    status_code=200,
    cost=0.001125,
)

# Create from dict
data = {
    "timestamp": "2026-05-19T14:30:45",
    "model": "mistral-medium",
    "endpoint": "/v1/chat/completions",
    "origin": "user",
    "request_tokens": 1000,
    "response_tokens": 500,
    "processing_time": 1.234,
    "status_code": 200,
    "cost": 0.001125,
}
record = CallRecord.from_dict(data)

# Convert to dict
record_dict = record.to_dict()

# Get total tokens
total = record.total_tokens()  # 1500
```

#### `SummaryStats`

Aggregated statistics for reporting.

**Attributes:**

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| `total_calls` | int | 0 | Total number of API calls |
| `total_request_tokens` | int | 0 | Sum of all request tokens |
| `total_response_tokens` | int | 0 | Sum of all response tokens |
| `total_cost` | float | 0.0 | Sum of all costs |
| `by_model` | dict | {} | Statistics grouped by model |
| `by_origin` | dict | {} | Statistics grouped by origin |

**Properties:**

##### `total_tokens -> int` (read-only)

Calculate total tokens across all calls.

**Returns:**
- Sum of total_request_tokens and total_response_tokens

**Example:**
```python
from token_telemetry.models import SummaryStats

stats = SummaryStats(
    total_calls=42,
    total_request_tokens=12000,
    total_response_tokens=20450,
    total_cost=0.0243,
    by_model={
        "mistral-medium": {
            "calls": 20,
            "request_tokens": 5000,
            "response_tokens": 10000,
            "cost": 0.01125,
        }
    },
    by_origin={
        "user": {
            "calls": 30,
            "request_tokens": 10000,
            "response_tokens": 15000,
            "cost": 0.01875,
        }
    },
)

print(f"Total tokens: {stats.total_tokens}")  # 32450
print(f"Total cost: ${stats.total_cost:.6f}")  # $0.024300
```

---

## proxy.py - HTTP Proxy Server

### Purpose

Implements the HTTP proxy server that intercepts API calls from Vibe CLI, forwards them to Mistral API, logs telemetry data, and returns responses.

### Key Classes

#### `TelemetryHandler`

HTTP request handler that intercepts API calls and logs telemetry.

**Inherits from:** `http.server.BaseHTTPRequestHandler`

**Class Attributes:**
- `database`: Shared Database instance
- `cost_calculator`: Shared CostCalculator instance
- `mistral_base_url`: Shared Mistral API base URL

**Instance Attributes:**
- `database`: Database instance (inherits from class or passed to constructor)
- `cost_calculator`: CostCalculator instance
- `mistral_base_url`: Mistral API base URL

**Methods:**

##### `__init__(self, *args, database=None, cost_calculator=None, mistral_base_url=None, **kwargs)`

Initialize the handler.

**Parameters:**
- `database`: Optional Database instance
- `cost_calculator`: Optional CostCalculator instance
- `mistral_base_url`: Optional Mistral API base URL

##### `log_message(self, format: str, *args)`

Override default logging to use our logger.

##### `_extract_model(self) -> str`

Extract the model name from the request.

**Checks in order:**
1. Custom headers: `X-Telemetry-Model`, `X-Model`
2. Path: looks for model names in the URL path
3. Default: "unknown"

**Returns:**
- Model name

##### `_extract_origin(self) -> str`

Extract the origin from the request.

**Checks in order:**
1. Custom headers: `X-Telemetry-Origin`, `X-Origin`
2. Default: "user"

**Returns:**
- Origin (lowercase)

##### `_extract_request_tokens(self) -> int`

Extract request token count from headers.

**Checks:**
- Header: `X-Telemetry-Request-Tokens`

**Returns:**
- Number of request tokens or 0

**Note:** Request tokens are typically extracted from the API response, not the request.

##### `_forward_request(self, request_data: Dict) -> requests.Response`

Forward the request to the Mistral API.

**Parameters:**
- `request_data`: Dictionary containing method, url, headers, data

**Returns:**
- Response from the Mistral API

**Behavior:**
- Uses `requests` library
- Sets 30-second timeout
- Raises RequestException on failure

##### `_log_telemetry(self, request_data: Dict, response: requests.Response, processing_time: float) -> CallRecord`

Log telemetry data for this API call.

**Parameters:**
- `request_data`: Request information
- `response`: Response from Mistral API
- `processing_time`: Time taken for the request

**Returns:**
- CallRecord with the logged data

**Behavior:**
1. Extracts response data (status code, token counts)
2. Extracts model and origin from request_data
3. Calculates cost using cost_calculator
4. Creates CallRecord
5. Inserts into database (non-blocking, continues on failure)

**Token Extraction:**
- Tries to parse JSON response
- Looks for `usage.prompt_tokens` / `usage.completion_tokens` (OpenAI format)
- Falls back to `usage.input_tokens` / `usage.output_tokens`

##### `_build_response(self, response: requests.Response)`

Build and send the HTTP response to the client.

**Parameters:**
- `response`: Response from Mistral API

**Behavior:**
- Sends response status code
- Copies response headers (excluding Content-Length, Transfer-Encoding, Connection)
- Sends response body

##### `do_POST(self)`

Handle POST requests.

**Behavior:**
1. Reads request body
2. Extracts model and origin
3. Builds request data for forwarding
4. Forwards request to Mistral API
5. Measures processing time
6. Logs telemetry
7. Sends response back to client

##### `do_GET(self)`

Handle GET requests.

**Behavior:** Similar to POST but without request body.

##### `do_PUT(self)`, `do_DELETE(self)`, `do_PATCH(self)`

Handle other HTTP methods.

**Behavior:** Currently delegate to POST or GET for simplicity.

#### `ProxyServer`

HTTP Proxy Server for Token Telemetry.

**Attributes:**
- `host`: Host to bind to
- `port`: Port to listen on
- `mistral_base_url`: Base URL for Mistral API
- `db_path`: Path to SQLite database
- `pricing_config`: Pricing configuration for cost calculator
- `database`: Database instance
- `cost_calculator`: CostCalculator instance
- `server`: HTTPServer instance
- `_server_thread`: Server thread (if running in background)

**Methods:**

##### `__init__(self, host: str = "localhost", port: int = 8000, mistral_base_url: str = "https://api.mistral.ai", db_path: str = "telemetry.db", pricing_config: Optional[Dict] = None)`

Initialize the proxy server.

**Parameters:**
- `host`: Host to bind to
- `port`: Port to listen on
- `mistral_base_url`: Base URL for Mistral API
- `db_path`: Path to SQLite database
- `pricing_config`: Pricing configuration for cost calculator

**Behavior:**
- Creates database instance
- Creates cost calculator instance
- Initializes server to None

##### `start(self)`

Start the proxy server.

**Behavior:**
1. Configures TelemetryHandler class with instances
2. Creates HTTPServer
3. Starts serving forever
4. Handles KeyboardInterrupt gracefully

##### `start_in_thread(self)`

Start the proxy server in a background thread.

**Behavior:**
1. Configures TelemetryHandler class
2. Creates HTTPServer
3. Starts server in daemon thread
4. Server continues running in background

##### `stop(self)`

Stop the proxy server.

**Behavior:**
- Shuts down server
- Closes server
- Joins server thread (with timeout)

##### `is_running(self) -> bool`

Check if the server is running.

**Returns:**
- True if server is running, False otherwise

### Constants

#### `FORWARD_HEADERS`

Headers to forward to Mistral API:
- Authorization
- Content-Type
- Accept
- User-Agent
- X-Request-ID

#### `TELEMETRY_HEADERS`

Headers to extract for telemetry:
- X-Telemetry-Model
- X-Telemetry-Origin
- X-Model
- X-Origin

### Global Functions

#### `main()`

Main entry point for running the proxy server from command line.

**Behavior:**
- Loads configuration
- Creates and starts ProxyServer

### Usage Examples

```python
from token_telemetry.proxy import ProxyServer, TelemetryHandler

# Method 1: Simple usage
server = ProxyServer()
server.start()

# Method 2: Custom configuration
server = ProxyServer(
    host="0.0.0.0",
    port=8080,
    mistral_base_url="https://api.mistral.ai",
    db_path="/var/lib/telemetry/telemetry.db",
)
server.start()

# Method 3: Run in background
server = ProxyServer(port=8080)
server.start_in_thread()
# ... do other work ...
server.stop()

# Method 4: Custom handler configuration
# Set class-level attributes before starting
TelemetryHandler.database = my_database
TelemetryHandler.cost_calculator = my_calculator
TelemetryHandler.mistral_base_url = "https://custom.endpoint"
server = ProxyServer()
server.start()
```

---

## reporter.py - Reporter Module

### Purpose

Generates text-based summaries from telemetry data with category breakdowns.

### Key Classes

#### `Reporter`

Generates text-based summaries from telemetry data.

**Attributes:**
- `database`: Database instance

**Methods:**

##### `__init__(self, db_path: str = "telemetry.db")`

Initialize the reporter.

**Parameters:**
- `db_path`: Path to the SQLite database

##### `generate_summary(self, filters: Optional[Dict] = None, time_period: str = "all") -> str`

Generate a text-based summary report.

**Parameters:**
- `filters`: Optional filters dictionary
  - `model`: Filter by model name
  - `origin`: Filter by origin
  - `start_date`: Start date (ISO format)
  - `end_date`: End date (ISO format)
- `time_period`: Time period for summary
  - `'all'`: All data
  - `'daily'`: Today's data
  - `'weekly'`: This week's data (Monday-Sunday)
  - `'monthly'`: This month's data

**Returns:**
- Formatted text summary

##### `_get_date_filters(self, time_period: str) -> Dict`

Get date filters based on time period.

**Parameters:**
- `time_period`: Time period string

**Returns:**
- Dictionary with start_date and/or end_date

##### `_format_summary(self, stats: SummaryStats, time_period: str = "all", filters: Optional[Dict] = None) -> str`

Format summary statistics into text.

**Parameters:**
- `stats`: Summary statistics
- `time_period`: Time period for the summary
- `filters`: Applied filters (for display)

**Returns:**
- Formatted text summary

**Format:**
```markdown
## Token Telemetry Summary ({time_period})

- **Total API Calls**: {total_calls}
- **Total Tokens**: {total_tokens} (Input: {input}, Output: {output})
- **Total Cost**: ${total_cost:.6f}

### Breakdown by Model
- **{model}**: {calls} calls, {tokens} tokens (Input: {input}, Output: {output}), ${cost:.6f}

### Breakdown by Origin
- **{origin}**: {calls} calls, {tokens} tokens (Input: {input}, Output: {output}), ${cost:.6f}

*Database contains {total_records} total records*
```

##### `generate_detailed_report(self, limit: int = 100, filters: Optional[Dict] = None) -> str`

Generate a detailed report with individual records.

**Parameters:**
- `limit`: Maximum number of records to include
- `filters`: Optional filters to apply

**Returns:**
- Formatted detailed report in markdown table format

##### `export_to_dict(self, filters: Optional[Dict] = None) -> Dict`

Export summary data as a dictionary (for JSON export).

**Parameters:**
- `filters`: Optional filters to apply

**Returns:**
- Dictionary containing:
  - `summary`: Aggregated statistics
  - `by_model`: Statistics by model
  - `by_origin`: Statistics by origin
  - `records`: List of individual records as dictionaries

### Global Functions

#### `generate_summary(db_path: str = "telemetry.db", filters: Optional[Dict] = None, time_period: str = "all") -> str`

Convenience function to generate a summary.

**Parameters:**
- `db_path`: Path to the SQLite database
- `filters`: Optional filters to apply
- `time_period`: Time period for summary

**Returns:**
- Formatted text summary

#### `main()`

Main entry point for running the reporter from command line.

**Behavior:**
- Parses command-line arguments
- Loads configuration
- Generates summary with specified filters
- Outputs to stdout or file

### Usage Examples

```python
from token_telemetry.reporter import Reporter, generate_summary

# Method 1: Using the class
reporter = Reporter("telemetry.db")
summary = reporter.generate_summary(time_period="daily")
print(summary)

# Method 2: Using the convenience function
summary = generate_summary(
    db_path="telemetry.db",
    filters={"model": "mistral-medium"},
    time_period="weekly"
)

# Method 3: Generate detailed report
reporter = Reporter()
detailed = reporter.generate_detailed_report(limit=50)

# Method 4: Export to JSON
reporter = Reporter()
data = reporter.export_to_dict(filters={"model": "mistral-large"})
import json
json.dumps(data, indent=2)

# Method 5: With filters
today_summary = reporter.generate_summary(
    filters={
        "model": "mistral-medium",
        "origin": "user",
        "start_date": "2026-05-19T00:00:00",
        "end_date": "2026-05-19T23:59:59"
    },
    time_period="all"
)
```

---

## cli.py - Command-Line Interface

### Purpose

Provides the main entry point for running the proxy server and generating reports from the command line.

### Key Functions

#### `setup_logging(verbose: bool = False)`

Configure logging for the CLI.

**Parameters:**
- `verbose`: If True, set logging level to DEBUG

**Behavior:**
- Sets up stream handler to stdout
- Configures format: `%(asctime)s - %(name)s - %(levelname)s - %(message)s`

#### `start_proxy(args: argparse.Namespace)`

Start the telemetry proxy server.

**Parameters:**
- `args`: Parsed command-line arguments

**Behavior:**
1. Loads configuration
2. Overrides with command-line arguments
3. Creates and starts ProxyServer

#### `generate_report(args: argparse.Namespace)`

Generate and display a telemetry summary report.

**Parameters:**
- `args`: Parsed command-line arguments

**Behavior:**
1. Loads configuration
2. Creates Reporter instance
3. Applies filters from arguments
4. Generates summary
5. Outputs to stdout or file

#### `parse_args() -> argparse.Namespace`

Parse command-line arguments.

**Returns:**
- Parsed arguments namespace

**Subcommands:**
- `proxy`: Start the telemetry proxy server
- `report`: Generate a telemetry summary report

**Proxy Arguments:**
- `-p, --port`: Port to run the proxy server on (default: 8000)
- `-H, --host`: Host to run the proxy server on (default: localhost)
- `-c, --config`: Path to configuration file
- `-v, --verbose`: Enable verbose logging

**Report Arguments:**
- `-c, --config`: Path to configuration file
- `--model`: Filter by model name
- `--origin`: Filter by origin
- `--period`: Time period (daily, weekly, monthly, all)
- `--start-date`: Start date (YYYY-MM-DD)
- `--end-date`: End date (YYYY-MM-DD)
- `-o, --output`: Output file path
- `-v, --verbose`: Enable verbose logging

#### `main()`

Main entry point for the token-telemetry CLI.

**Behavior:**
- Parses arguments
- Sets up logging
- Routes to appropriate subcommand handler

### Usage Examples

```python
from token_telemetry.cli import main, parse_args

# Run the CLI
main()

# Or parse and handle arguments programmatically
args = parse_args()
if args.command == "proxy":
    from token_telemetry.cli import start_proxy
    start_proxy(args)
elif args.command == "report":
    from token_telemetry.cli import generate_report
    generate_report(args)
```

---

## __init__.py - Package Initialization

### Purpose

Package initialization with lazy imports to avoid circular dependencies.

### Key Features

- Lazy import of submodules
- Package metadata (`__version__`, `__author__`, `__description__`)
- Clean public API via `__all__`

### Lazy Import Mechanism

The `__getattr__` function dynamically imports modules when accessed:

```python
def __getattr__(name: str):
    _modules = {
        "Config": "token_telemetry.config",
        "load_config": "token_telemetry.config",
        "Database": "token_telemetry.database",
        "CostCalculator": "token_telemetry.cost_calculator",
        "calculate_cost": "token_telemetry.cost_calculator",
        "ProxyServer": "token_telemetry.proxy",
        "TelemetryHandler": "token_telemetry.proxy",
        "Reporter": "token_telemetry.reporter",
        "generate_summary": "token_telemetry.reporter",
        "CallRecord": "token_telemetry.models",
        "SummaryStats": "token_telemetry.models",
    }
    
    if name in _modules:
        module = __import__(_modules[name], fromlist=[name])
        return getattr(module, name)
    
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
```

### Public API

**`__all__` exports:**
- `__version__`
- `Config`
- `load_config`
- `Database`
- `CostCalculator`
- `calculate_cost`
- `ProxyServer`
- `TelemetryHandler`
- `Reporter`
- `generate_summary`
- `CallRecord`
- `SummaryStats`

### Usage Examples

```python
# Import specific classes
from token_telemetry import Database, CostCalculator, CallRecord

# Import functions
from token_telemetry import load_config, calculate_cost, generate_summary

# Check version
import token_telemetry
print(token_telemetry.__version__)
```
