# Configuration Reference

Complete reference for configuring Token Telemetry.

## Configuration Overview

Token Telemetry uses a hierarchical configuration system with the following priority (higher overrides lower):

```
1. Environment Variables (highest priority)
2. User Configuration File (config/local.yaml)
3. Default Configuration File (config/default_config.yaml)
4. Package Defaults (lowest priority)
```

## Configuration Files

### File Locations

| File | Purpose | Required |
|------|---------|----------|
| `config/default_config.yaml` | Package defaults | Yes (included) |
| `config/default_pricing.yaml` | Default pricing | Yes (included) |
| `config/local.yaml` | User overrides | No |

### File Formats

Supported configuration file formats:
- **YAML** (`.yaml`, `.yml`) - Recommended
- **JSON** (`.json`)

## Default Configuration

### config/default_config.yaml

```yaml
# Token Telemetry Default Configuration
# This file contains the default configuration values.
# Users can override these by creating a config/local.yaml file or using environment variables.

# Proxy server configuration
proxy:
  host: localhost
  port: 8000

# Mistral API configuration
mistral:
  base_url: "https://api.mistral.ai"

# Database configuration
database:
  path: "telemetry.db"

# Logging configuration
logging:
  level: INFO
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
  file: "telemetry.log"
```

### config/default_pricing.yaml

```yaml
# Token Telemetry Default Pricing Configuration
# Pricing is per 1M tokens (0.25 per 1M input tokens, 0.75 per 1M output tokens)
# Based on Mistral AI pricing as of May 2026

# Mistral AI Models
mistral-tiny:
  input: 0.25
  output: 0.75

mistral-small:
  input: 0.25
  output: 0.75

mistral-medium:
  input: 0.25
  output: 0.75

mistral-large:
  input: 0.25
  output: 0.75

# Codestral (code-specific model)
codestral-latest:
  input: 0.25
  output: 0.75

# Default pricing for unknown models (can be overridden)
default:
  input: 0.25
  output: 0.75
```

## Creating User Configuration

Create `config/local.yaml` to override defaults:

```yaml
# My custom configuration
proxy:
  port: 9000
  host: 0.0.0.0

mistral:
  base_url: "https://api.mistral.ai"

database:
  path: "/path/to/my/telemetry.db"

logging:
  level: DEBUG
  file: "/var/log/token_telemetry.log"

# Custom pricing for specific models
pricing:
  mistral-medium:
    input: 0.20
    output: 0.70
  custom-model:
    input: 0.50
    output: 1.00
```

## Configuration Options

### Proxy Configuration

| Option | Type | Default | Description | Environment Variable |
|--------|------|---------|-------------|---------------------|
| `proxy.host` | string | `localhost` | Host to bind the proxy server to | `TELEMETRY_PROXY_HOST` |
| `proxy.port` | integer | `8000` | Port to listen on | `TELEMETRY_PROXY_PORT` |

**Examples:**

```yaml
proxy:
  host: 0.0.0.0  # Allow external connections
  port: 8080    # Use port 8080
```

### Mistral API Configuration

| Option | Type | Default | Description | Environment Variable |
|--------|------|---------|-------------|---------------------|
| `mistral.base_url` | string | `https://api.mistral.ai` | Base URL for Mistral API | `MISTRAL_BASE_URL` |

**Note:** `VIBE_API_ENDPOINT` is **NOT** used for proxy configuration. It is only used by Vibe CLI to locate the proxy server. The proxy forwards all requests to `mistral.base_url`.

**Examples:**

```yaml
mistral:
  base_url: "https://api.mistral.ai/v1"
```

### Database Configuration

| Option | Type | Default | Description | Environment Variable |
|--------|------|---------|-------------|---------------------|
| `database.path` | string | `telemetry.db` | Path to SQLite database file | `TELEMETRY_DB_PATH` |

**Examples:**

```yaml
database:
  path: "/home/user/telemetry/telemetry.db"
```

**Note:** The directory must exist; the database file will be created automatically.

### Logging Configuration

| Option | Type | Default | Description | Environment Variable |
|--------|------|---------|-------------|---------------------|
| `logging.level` | string | `INFO` | Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL) | N/A |
| `logging.format` | string | `%(asctime)s - %(name)s - %(levelname)s - %(message)s` | Log message format | N/A |
| `logging.file` | string | `telemetry.log` | Path to log file | N/A |

**Log Levels:**
- `DEBUG` - Most verbose, includes all debug messages
- `INFO` - Normal operation messages
- `WARNING` - Warning messages
- `ERROR` - Error messages only
- `CRITICAL` - Critical errors only

**Examples:**

```yaml
logging:
  level: DEBUG
  format: "[%(asctime)s] %(levelname)s in %(name)s: %(message)s"
  file: "/var/log/token_telemetry.log"
```

### Pricing Configuration

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `pricing.<model>.input` | float | `0.25` | Input token price per 1M tokens |
| `pricing.<model>.output` | float | `0.75` | Output token price per 1M tokens |
| `pricing.default` | dict | `{input: 0.25, output: 0.75}` | Fallback pricing for unknown models |

**Pricing is per 1,000,000 tokens.**

**Examples:**

```yaml
pricing:
  # Mistral models with custom pricing
  mistral-tiny:
    input: 0.15
    output: 0.50
  
  mistral-small:
    input: 0.20
    output: 0.60
  
  mistral-medium:
    input: 0.25
    output: 0.75
  
  mistral-large:
    input: 0.30
    output: 0.90
  
  # Custom models
  my-custom-model:
    input: 0.50
    output: 1.00
  
  # Default for any unknown models
  default:
    input: 0.25
    output: 0.75
```

**Adding New Models:**

```yaml
pricing:
  # Add support for a new model
  mistral-embed:
    input: 0.10
    output: 0.00  # Embedding models typically don't have output tokens
```

## Environment Variables

All configuration options can be set via environment variables:

| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| `TELEMETRY_PROXY_HOST` | Proxy server host | `localhost` | `export TELEMETRY_PROXY_HOST=0.0.0.0` |
| `TELEMETRY_PROXY_PORT` | Proxy server port | `8000` | `export TELEMETRY_PROXY_PORT=9000` |
| `MISTRAL_BASE_URL` | Mistral API endpoint | `https://api.mistral.ai` | `export MISTRAL_BASE_URL=https://custom.endpoint` |
| `VIBE_API_ENDPOINT` | **For Vibe CLI only** - tells Vibe CLI where the proxy is | None | `export VIBE_API_ENDPOINT=http://localhost:8000` |
| `TELEMETRY_DB_PATH` | Database file path | `telemetry.db` | `export TELEMETRY_DB_PATH=/path/to/db` |

**Priority:** Environment variables > config file > defaults. Note: `VIBE_API_ENDPOINT` is **NOT** used by the proxy server - it is only read by Vibe CLI.

### Using Environment Variables

```bash
# Set all environment variables
export TELEMETRY_PROXY_HOST=0.0.0.0
export TELEMETRY_PROXY_PORT=8080
export MISTRAL_BASE_URL=https://api.mistral.ai
export TELEMETRY_DB_PATH=/var/lib/token_telemetry/telemetry.db

# Start the proxy
python -m token_telemetry.cli proxy
```

### .env File (Optional)

Create a `.env` file in your project directory:

```bash
# .env
TELEMETRY_PROXY_HOST=0.0.0.0
TELEMETRY_PROXY_PORT=8080
MISTRAL_BASE_URL=https://api.mistral.ai
TELEMETRY_DB_PATH=./data/telemetry.db
```

Then load it before running:

```bash
# Using dotenv (install with: pip install python-dotenv)
from dotenv import load_dotenv
load_dotenv()

# Or source it in bash
set -a && source .env && set +a
python -m token_telemetry.cli proxy
```

## Complete Configuration Example

Here's a comprehensive example with all options:

```yaml
# config/local.yaml

# Proxy settings
proxy:
  host: 0.0.0.0
  port: 8080

# Mistral API settings
mistral:
  base_url: "https://api.mistral.ai/v1"

# Database settings
database:
  path: "/home/user/telemetry/data/telemetry.db"

# Logging settings
logging:
  level: INFO
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
  file: "/home/user/telemetry/logs/telemetry.log"

# Custom pricing
pricing:
  # Standard Mistral models
  mistral-tiny:
    input: 0.25
    output: 0.75
  
  mistral-small:
    input: 0.25
    output: 0.75
  
  mistral-medium:
    input: 0.25
    output: 0.75
  
  mistral-large:
    input: 0.25
    output: 0.75
  
  codestral-latest:
    input: 0.25
    output: 0.75
  
  # Custom models
  my-company-model:
    input: 0.50
    output: 1.50
  
  # Embedding model (no output tokens)
  mistral-embed:
    input: 0.10
    output: 0.00
  
  # Default for unknown models
  default:
    input: 0.25
    output: 0.75
```

## Configuration Validation

The configuration system validates:

1. **Proxy Port**: Must be a valid port number (1-65535)
2. **Pricing Rates**: Must be non-negative numbers
3. **Log Level**: Must be a valid log level

Invalid configurations will log warnings and fall back to defaults.

## Multiple Configuration Files

You can load multiple configuration files by:

1. **Primary config file**: `config/local.yaml`
2. **Additional files**: Use the `--config` CLI argument

```bash
# Load config from a specific file
python -m token_telemetry.cli proxy --config /path/to/custom.yaml
```

## JSON Configuration Format

You can also use JSON for configuration:

```json
{
  "proxy": {
    "host": "localhost",
    "port": 8000
  },
  "mistral": {
    "base_url": "https://api.mistral.ai"
  },
  "database": {
    "path": "telemetry.db"
  },
  "logging": {
    "level": "INFO",
    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    "file": "telemetry.log"
  },
  "pricing": {
    "mistral-medium": {
      "input": 0.25,
      "output": 0.75
    }
  }
}
```

Load it with:

```bash
python -m token_telemetry.cli proxy --config config/local.json
```

## Configuration Precedence Examples

### Example 1: Environment Variable Overrides File

```yaml
# config/local.yaml
proxy:
  port: 8000
```

```bash
export TELEMETRY_PROXY_PORT=9000
python -m token_telemetry.cli proxy
# Result: Port 9000 (environment variable wins)
```

### Example 2: CLI Argument Overrides Everything

```yaml
# config/local.yaml
proxy:
  port: 8000
```

```bash
export TELEMETRY_PROXY_PORT=9000
python -m token_telemetry.cli proxy --port 8080
# Result: Port 8080 (CLI argument wins)
```

### Example 3: Partial Configuration

```yaml
# config/local.yaml
proxy:
  port: 8000
# No database configuration
```

```bash
# No environment variables set
python -m token_telemetry.cli proxy
# Result: Port 8000, database.path = "telemetry.db" (default)
```

## Programmatic Configuration

You can also load and modify configuration programmatically:

```python
from token_telemetry.config import load_config, Config

# Load configuration
config = load_config()

# Modify values
config.proxy.port = 9000
config.database.path = "/custom/path/telemetry.db"

# Use in your code
from token_telemetry.proxy import ProxyServer
server = ProxyServer(
    host=config.proxy.host,
    port=config.proxy.port,
    db_path=config.database.path,
)
```

## Configuration Schema

```
Config:
  ├── proxy: ProxyConfig
  │     ├── host: str = "localhost"
  │     └── port: int = 8000
  ├── mistral: MistralConfig
  │     └── base_url: str = "https://api.mistral.ai"
  ├── database: DatabaseConfig
  │     └── path: str = "telemetry.db"
  ├── logging: LoggingConfig
  │     ├── level: str = "INFO"
  │     ├── format: str = "..."
  │     └── file: str = "telemetry.log"
  └── pricing: Dict[str, Dict[str, float]]
        └── {model}: {input: float, output: float}
```

## See Also

- [Installation Guide](installation.md)
- [Usage Guide](usage.md)
- [Troubleshooting](troubleshooting.md)
