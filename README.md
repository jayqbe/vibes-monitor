# Token Telemetry for Vibe CLI

A **standalone token telemetry system** that runs as a proxy wrapper around Vibe CLI to track API calls, measure token usage, compute costs based on Mistral AI's pricing model, and generate text-based summaries with category breakdowns.

## Features

- **Real-time API Call Tracking**: Log every API call made by Vibe CLI
- **Token Usage Measurement**: Count input/output tokens per API call
- **Cost Calculation**: Compute costs based on Mistral AI's pricing model
- **Text-Based Reporting**: Generate summaries with breakdowns by model, origin, and time period
- **Local Storage**: SQLite database for persistent telemetry data
- **Configurable**: External configuration for pricing, ports, and endpoints

## Quick Start

### Prerequisites

- Python 3.11+
- Vibe CLI installed

### Installation

```bash
# Clone the repository
git clone https://github.com/jayqbe/vibes-monitor.git
cd vibes-monitor

# Install in development mode
pip install -e ".[dev]"

# Or install just the package
pip install -e .
```

### Basic Usage

1. **Start the proxy server**:
   ```bash
   python -m token_telemetry.proxy
   # or
   telemetry-proxy
   ```

2. **Configure Vibe CLI to use the proxy** (choose one method):

   **Method A: Global config** (persistent for all projects):
   ```bash
   # Edit ~/.vibe/config.toml and change the Mistral provider's api_base
   # From: api_base = "https://api.mistral.ai/v1"
   # To:   api_base = "http://localhost:8000/v1"
   nano ~/.vibe/config.toml
   ```

   **Method B: Environment variable** (temporary, current session only):
   ```bash
   export VIBE_PROVIDERS='[{"name": "mistral", "api_base": "http://localhost:8000/v1", "api_key_env_var": "MISTRAL_API_KEY", "backend": "mistral"}]'
   vibe
   ```

   **Method C: Project-specific config** (isolated to current project):
   ```bash
   mkdir -p .vibe
   cat > .vibe/config.toml << 'EOF'
   [[providers]]
   name = "mistral"
   api_base = "http://localhost:8000/v1"
   api_key_env_var = "MISTRAL_API_KEY"
   backend = "mistral"
   EOF
   vibe
   ```

3. **Generate a summary report**:
   ```bash
   python -m token_telemetry.reporter
   # or
   telemetry-report
   ```

   > **⚠️ Important:** Vibe CLI does NOT use the `VIBE_API_ENDPOINT` environment variable. You must use one of the three methods above to configure Vibe CLI to send requests through the proxy.

### Configuration

Create a `config/local.yaml` file:

```yaml
# Proxy settings
proxy:
  port: 8000
  host: localhost

# Mistral API settings
mistral:
  base_url: https://api.mistral.ai

# Database settings
database:
  path: telemetry.db

# Pricing configuration (can also be in separate file)
pricing:
  mistral-tiny:
    input: 0.25
    output: 0.75
  mistral-medium:
    input: 0.25
    output: 0.75
  mistral-large:
    input: 0.25
    output: 0.75
```

Or use environment variables:

```bash
# Proxy configuration
export TELEMETRY_PROXY_PORT=8000
export TELEMETRY_PROXY_HOST=localhost

# Mistral API endpoint
export MISTRAL_BASE_URL=https://api.mistral.ai

# Database
export TELEMETRY_DB_PATH=telemetry.db
```

## Example Output

```
## Token Telemetry Summary (2026-05-19)

- **Total API Calls**: 42
- **Total Tokens**: 32,450 (Input: 12,000, Output: 20,450)
- **Total Cost**: $0.0243

### Breakdown by Model
- mistral-medium: 20 calls, 15,000 tokens (Input: 5,000, Output: 10,000), $0.01125
- mistral-large: 22 calls, 17,450 tokens (Input: 7,000, Output: 10,450), $0.01308

### Breakdown by Origin
- user: 30 calls, 25,000 tokens (Input: 10,000, Output: 15,000), $0.01875
- agent: 12 calls, 7,450 tokens (Input: 2,000, Output: 5,450), $0.00562
```

## Project Structure

```
token-telemetry/
├── src/
│   └── token_telemetry/
│       ├── __init__.py
│       ├── config.py           # Configuration management
│       ├── database.py         # Database access layer
│       ├── cost_calculator.py  # Cost computation
│       ├── proxy.py            # HTTP proxy server
│       ├── models.py           # Data models
│       ├── reporter.py         # Summary generation
│       └── cli.py              # Command-line interface
├── tests/
│   ├── unit/
│   ├── integration/
│   └── edge_cases/
├── config/
│   ├── default_config.yaml
│   └── default_pricing.yaml
├── docs/
│   ├── user/
│   └── developer/
├── scripts/
├── pyproject.toml
├── requirements.txt
└── README.md
```

## Architecture

```
Vibe CLI → Proxy Wrapper → Mistral API
                 ↓
         Telemetry Logger → SQLite Database
                 ↓
         Cost Calculator
                 ↓
         Reporter → Text Summaries
```

The proxy wrapper intercepts all API calls from Vibe CLI, logs telemetry data (timestamp, model, tokens, processing time, status), calculates costs, and stores everything in a local SQLite database. The reporter module then generates human-readable summaries.

## Telemetry Data Model

Each API call is logged with the following metadata:

| Field | Type | Description |
|-------|------|-------------|
| `timestamp` | TEXT | ISO 8601 timestamp |
| `model` | TEXT | Model name (e.g., mistral-medium) |
| `endpoint` | TEXT | API endpoint URL |
| `origin` | TEXT | Call initiator (user/agent/sub-agent) |
| `request_tokens` | INTEGER | Tokens in the request |
| `response_tokens` | INTEGER | Tokens in the response |
| `processing_time` | REAL | Time taken (seconds) |
| `status_code` | INTEGER | HTTP status code |
| `cost` | REAL | Calculated cost (USD) |

## Cost Model

By default, uses Mistral AI's pricing:

- **Input tokens**: $0.25 per 1M tokens
- **Output tokens**: $0.75 per 1M tokens

Pricing is configurable per model via configuration files or environment variables.

## Development

See [CONTRIBUTING.md](CONTRIBUTING.md) for development guidelines.

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src/token_telemetry --cov-report=html

# Run specific test file
pytest tests/unit/test_database.py
```

### Code Quality

This project uses:
- **black** for code formatting
- **isort** for import sorting
- **flake8** for linting
- **mypy** for type checking
- **pytest** for testing

Pre-commit hooks are configured for automatic formatting and linting.

## License

MIT License - see LICENSE file for details.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for contribution guidelines.
