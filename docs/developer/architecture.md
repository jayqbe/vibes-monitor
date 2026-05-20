# Architecture Overview

This document provides a comprehensive overview of the Token Telemetry system architecture, components, and data flow.

## System Overview

Token Telemetry is a **proxy-based telemetry system** that intercepts API calls from Vibe CLI, logs metadata, calculates costs, and generates text-based summaries. The system is designed to be:

- **Non-invasive**: No modifications required to Vibe CLI
- **Lightweight**: Minimal overhead on API calls
- **Extensible**: Easy to add new models, metrics, or report formats
- **Portable**: Works in any environment with Python 3.11+

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Token Telemetry System                  │
├─────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐ │
│  │   Vibe CLI   │───▶│  Proxy      │───▶│ Mistral API  │ │
│  │              │    │  Server     │    │              │ │
│  └──────────────┘    └──────┬───────┘    └──────────────┘ │
│                              │                             │
│                              ▼                             │
│                    ┌─────────────────┐                     │
│                    │  Telemetry     │                     │
│                    │  Logger        │                     │
│                    └────────┬────────┘                     │
│                             │                               │
│                    ┌────────▼────────┐                     │
│                    │  SQLite        │                     │
│                    │  Database      │                     │
│                    └────────┬────────┘                     │
│                             │                               │
│                    ┌────────▼────────┐                     │
│                    │  Cost          │                     │
│                    │  Calculator    │                     │
│                    └────────┬────────┘                     │
│                             │                               │
│                    ┌────────▼────────┐                     │
│                    │  Reporter       │                     │
│                    │  (CLI)          │                     │
│                    └─────────────────┘                     │
│                                                                 │
└─────────────────────────────────────────────────────────────┘
```

## Component Details

### 1. Proxy Server (`proxy.py`)

**Purpose**: Intercepts HTTP requests from Vibe CLI, forwards them to Mistral API, and captures response data.

**Key Features**:
- HTTP/1.1 server using Python's `http.server`
- Request/response interception and forwarding
- Header extraction for metadata (model, origin)
- Token count extraction from API responses
- Non-blocking telemetry logging
- Graceful error handling

**Request Flow**:
```
Vibe CLI Request → Proxy Handler → Forward to Mistral API → Receive Response → Log Telemetry → Return Response to Vibe CLI
```

**Supported HTTP Methods**:
- `POST` - Main API call method (chat completions)
- `GET` - For list/read operations
- `PUT`, `DELETE`, `PATCH` - Treated as POST for simplicity

### 2. Telemetry Logger & Database (`database.py`)

**Purpose**: Persistent storage of telemetry data in SQLite database.

**Database Schema**:
```sql
CREATE TABLE calls (
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

-- Indexes for query performance
CREATE INDEX idx_calls_timestamp ON calls(timestamp);
CREATE INDEX idx_calls_model ON calls(model);
CREATE INDEX idx_calls_origin ON calls(origin);
```

**Key Features**:
- Thread-safe connection handling with thread-local storage
- WAL (Write-Ahead Logging) mode for better concurrency
- CRUD operations for telemetry records
- Summary statistics aggregation
- Time-based queries (by date, week, month)
- Context manager for safe cursor handling

**Connection Strategy**:
- Per-database thread-local connection storage
- Lazy initialization on first use
- Automatic schema creation
- Connection pooling via thread-local storage

### 3. Cost Calculator (`cost_calculator.py`)

**Purpose**: Computes API call costs based on token usage and model-specific pricing.

**Pricing Model**:
```
Cost = (input_tokens / 1,000,000) * input_rate + (output_tokens / 1,000,000) * output_rate
```

**Key Features**:
- Configurable pricing per model
- Fallback to default pricing for unknown models
- Runtime pricing updates (add, update, remove models)
- Deep copy protection against mutable default issues
- Input validation (non-negative token counts)

**Default Pricing** (Mistral AI as of May 2026):
- Input tokens: $0.25 per 1M tokens
- Output tokens: $0.75 per 1M tokens

### 4. Reporter (`reporter.py`)

**Purpose**: Generates text-based summaries from telemetry data.

**Output Formats**:
- Markdown text summaries (default)
- Detailed record tables
- JSON export (via `export_to_dict()`)

**Summary Types**:
- **All data**: Complete history
- **Daily**: Current day's data
- **Weekly**: Current week's data (Monday-Sunday)
- **Monthly**: Current month's data
- **Custom date range**: Arbitrary date range

**Key Features**:
- Aggregated statistics by model and origin
- Filter support (by model, origin, date range)
- Time period calculations
- Formatted markdown output
- Database record count display

### 5. Configuration Management (`config.py`)

**Purpose**: Hierarchical configuration system supporting files, environment variables, and defaults.

**Configuration Priority** (highest to lowest):
1. Environment Variables
2. User Configuration File (`config/local.yaml`)
3. Default Configuration File (`config/default_config.yaml`)
4. Package Defaults

**Supported Formats**:
- YAML (`.yaml`, `.yml`) - Recommended
- JSON (`.json`)

**Key Features**:
- Recursive configuration merging
- Environment variable parsing with type conversion
- Configuration validation
- Pricing configuration parsing
- Configurable paths for all components

### 6. CLI Interface (`cli.py`)

**Purpose**: Command-line interface for starting the proxy and generating reports.

**Subcommands**:
- `proxy` - Start the telemetry proxy server
- `report` - Generate a telemetry summary report

**Key Features**:
- Argument parsing with `argparse`
- Configuration file support
- Command-line argument overrides
- Help text generation
- Error handling

### 7. Data Models (`models.py`)

**Purpose**: Defines the core data structures used throughout the system.

**Models**:

#### CallRecord
Represents a single API call telemetry record.

| Field | Type | Description |
|-------|------|-------------|
| `timestamp` | str | ISO 8601 timestamp |
| `model` | str | Model name |
| `endpoint` | str | API endpoint URL |
| `origin` | str | Call initiator (user/agent/sub-agent) |
| `request_tokens` | int | Tokens in request |
| `response_tokens` | int | Tokens in response |
| `processing_time` | float | Time taken (seconds) |
| `status_code` | int | HTTP status code |
| `cost` | float | Calculated cost (USD) |

**Methods**:
- `total_tokens()` - Sum of request + response tokens
- `to_dict()` - Convert to dictionary
- `from_dict(data)` - Create from dictionary

#### SummaryStats
Aggregated statistics for reporting.

| Field | Type | Description |
|-------|------|-------------|
| `total_calls` | int | Total number of API calls |
| `total_request_tokens` | int | Sum of all request tokens |
| `total_response_tokens` | int | Sum of all response tokens |
| `total_cost` | float | Sum of all costs |
| `by_model` | dict | Statistics grouped by model |
| `by_origin` | dict | Statistics grouped by origin |

**Properties**:
- `total_tokens` - Read-only sum of request + response tokens

## Data Flow

### Request Flow

```
┌──────────┐     ┌──────────┐     ┌──────────┐
│  Vibe    │────▶│  Proxy   │────▶│ Mistral │
│  CLI     │     │  Server  │     │  API    │
└──────────┘     └──────────┘     └──────────┘
                      │
                      ▼
┌─────────────────────────────────────────┐
│              Telemetry Logging            │
│  ┌─────────────────────────────────────┐ │
│  │ 1. Extract model from headers/path   │ │
│  │ 2. Extract origin from headers       │ │
│  │ 3. Forward request to Mistral API   │ │
│  │ 4. Measure processing time           │ │
│  │ 5. Extract token counts from response│ │
│  │ 6. Calculate cost                    │ │
│  │ 7. Create CallRecord                 │ │
│  │ 8. Insert into database              │ │
│  └─────────────────────────────────────┘ │
└─────────────────────────────────────────┘
                      │
                      ▼
              ┌────────────┐
              │  Database  │
              │  (SQLite)  │
              └────────────┘
```

### Cost Calculation Flow

```
┌──────────────┐
│ API Response │
│ usage:        │
│   input_tokens: 1000 │
│   output_tokens: 2000 │
└───────┬───────┘
        │
        ▼
┌──────────────┐
│ CostCalculator│
│ model_pricing = │
│   input: 0.25 │
│   output: 0.75│
└───────┬───────┘
        │
        ▼
┌──────────────┐
│ Calculation:  │
│ (1000/1M)*0.25 + │
│ (2000/1M)*0.75 = │
│ $0.001750    │
└───────┬───────┘
        │
        ▼
┌──────────────┐
│ CallRecord   │
│ cost: 0.001750│
└──────────────┘
```

### Reporting Flow

```
┌──────────────┐
│  User Query  │
│  (filters,   │
│   time period)│
└───────┬───────┘
        │
        ▼
┌──────────────┐
│  Database    │
│  Query       │
└───────┬───────┘
        │
        ▼
┌──────────────┐
│ SummaryStats │
│ aggregation   │
└───────┬───────┘
        │
        ▼
┌──────────────┐
│  Reporter    │
│  format_summary()│
└───────┬───────┘
        │
        ▼
┌──────────────┐
│ Markdown     │
│ Output       │
└──────────────┘
```

## Package Structure

```
token-telemetry/
├── config/
│   ├── default_config.yaml     # Default configuration
│   └── default_pricing.yaml    # Default pricing configuration
├── docs/
│   ├── user/                   # User documentation (DOC-001)
│   │   ├── installation.md
│   │   ├── usage.md
│   │   ├── configuration.md
│   │   └── troubleshooting.md
│   └── developer/              # Developer documentation (DOC-002)
│       ├── architecture.md
│       ├── modules.md
│       ├── api_reference.md
│       └── contributing.md
├── src/
│   └── token_telemetry/
│       ├── __init__.py        # Package initialization with lazy imports
│       ├── config.py          # Configuration management
│       ├── database.py        # SQLite database operations
│       ├── cost_calculator.py  # Cost computation logic
│       ├── models.py          # Data models
│       ├── proxy.py           # HTTP proxy server
│       ├── reporter.py        # Summary generation
│       └── cli.py             # Command-line interface
├── tests/
│   ├── unit/                  # Unit tests
│   │   ├── test_config.py
│   │   ├── test_database.py
│   │   ├── test_cost_calculator.py
│   │   └── test_models.py
│   ├── integration/            # Integration tests
│   │   └── test_integration.py
│   └── edge_cases/             # Edge case tests
│       └── test_edge_cases.py
├── pyproject.toml              # Project configuration
├── requirements.txt            # Production dependencies
├── requirements-dev.txt        # Development dependencies
└── README.md
```

## Design Decisions

### Why SQLite?

- **Pros**:
  - Zero configuration (file-based)
  - ACID-compliant
  - Good performance for single-writer, multiple-reader scenarios
  - Built into Python (no external dependencies)
  - Portable (single file)

- **Cons**:
  - Limited concurrency (though WAL mode helps)
  - Not suitable for distributed systems
  - No user management

- **Mitigation**: For high-concurrency environments, consider PostgreSQL (future enhancement)

### Why HTTP Server from Standard Library?

- **Pros**:
  - No external dependencies
  - Simple and reliable
  - Good enough for local development and moderate traffic

- **Cons**:
  - Single-threaded (though each request spawns a thread)
  - Not async (though for proxy use case, this is acceptable)

- **Mitigation**: For production deployments, consider using aiohttp or FastAPI (future enhancement)

### Why Thread-Local Connections?

- **Pros**:
  - Avoids connection overhead for each request
  - Handles concurrent requests safely
  - Simple implementation

- **Cons**:
  - Memory usage grows with number of threads
  - Connections not automatically closed

- **Mitigation**: WAL mode provides good concurrency; connection cleanup on long-running processes is a known limitation

### Why Hierarchical Configuration?

- **Pros**:
  - Flexible (files, env vars, defaults)
  - Priority system is intuitive
  - Easy to override for testing

- **Cons**:
  - Slight complexity in implementation
  - Merging logic can be confusing

- **Mitigation**: Clear documentation and examples

## Thread Safety

The system is designed to be thread-safe:

1. **Database**:
   - Thread-local connection storage
   - SQLite WAL mode for concurrent access
   - Per-database connection isolation

2. **Cost Calculator**:
   - Immutable pricing configuration after initialization
   - Thread-safe operations (read-only after init)

3. **Proxy Server**:
   - HTTPServer handles each request in a separate thread
   - Shared state is read-only or properly synchronized

4. **Reporter**:
   - Read-only database queries
   - No shared mutable state

## Performance Considerations

### Proxy Overhead

- **Request Processing**: ~1-5ms per request (typical)
- **Database Insert**: ~1-2ms per record
- **Cost Calculation**: <1ms per call
- **Total Overhead**: ~2-10ms per request

**Note**: Actual overhead depends on hardware, database size, and network conditions.

### Database Performance

| Operation | Complexity | Typical Time |
|-----------|------------|--------------|
| Insert | O(1) | 1-2ms |
| Query (no filters) | O(n) | 1-5ms |
| Query (with index) | O(log n) | 1-3ms |
| Summary (all data) | O(n) | 5-20ms |
| Summary (filtered) | O(n) | 5-20ms |

**Optimizations**:
- Indexes on timestamp, model, and origin
- WAL mode for concurrent writes
- Connection pooling via thread-local storage

### Memory Usage

| Component | Memory |
|-----------|--------|
| Proxy Server | ~10-20MB |
| Database Connection | ~1-2MB per thread |
| In-memory Data | Minimal (only config) |

**Note**: Memory usage scales with number of concurrent threads, not with database size.

## Extensibility

The system is designed for easy extension:

### Adding New Models

```python
# In your code
from token_telemetry.cost_calculator import CostCalculator

calculator = CostCalculator()
calculator.add_model("my-new-model", input_rate=0.50, output_rate=1.00)
```

### Adding New Metrics

1. Add field to `CallRecord` model
2. Add column to database schema
3. Update proxy to extract the metric
4. Update reporter to include it in summaries

### Adding New Report Formats

```python
# In reporter.py
class JSONReporter(Reporter):
    def generate_json_report(self, filters=None):
        data = self.export_to_dict(filters)
        return json.dumps(data, indent=2)
```

### Adding New API Providers

1. Create a new provider class
2. Implement request forwarding logic
3. Implement response parsing for token counts
4. Update proxy to route based on endpoint

## Limitations

### Current Limitations

1. **No HTTPS Support**: Proxy only supports HTTP. Use Nginx or similar for SSL termination.
2. **No Authentication**: Anyone with network access can use the proxy.
3. **SQLite Concurrency**: Limited to ~100 concurrent writes.
4. **Single Process**: Only one proxy instance can use a database file.
5. **No Persistent Connections**: Each request creates a new connection to Mistral API.

### Known Issues

1. **Deprecation Warnings**: `datetime.utcnow()` is deprecated in Python 3.13
2. **Resource Warnings**: Unclosed SQLite connections in tests
3. **Thread-Local Cleanup**: Connections persist for life of thread

See [IMPLEMENTATION_STATUS.md](../../IMPLEMENTATION_STATUS.md) for details.

## Future Enhancements

| Enhancement | Priority | Complexity |
|-------------|----------|------------|
| HTTPS Support | High | Medium |
| PostgreSQL Backend | Medium | High |
| Async Proxy (aiohttp) | Medium | High |
| REST API for Reports | Medium | Medium |
| Web Dashboard | Low | High |
| Authentication | Medium | Medium |
| Rate Limiting | Low | Medium |
| Prometheus Metrics | Medium | Medium |
| Distributed Tracing | Low | High |

## See Also

- [Module Documentation](modules.md) - Detailed module documentation
- [API Reference](api_reference.md) - Complete API reference
- [Contribution Guidelines](contributing.md) - How to contribute
- [Functional Specification](../../FUNCTIONAL_SPECIFICATION.md) - Requirements
- [Technical Design](../../TECHNICAL_DESIGN.md) - Detailed design
