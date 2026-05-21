# Usage Guide

Learn how to use Token Telemetry to track Vibe CLI API calls and monitor token usage.

## Quick Start

### 1. Start the Proxy Server

```bash
python -m token_telemetry.cli proxy
```

This starts the telemetry proxy on `localhost:8000`.

### 2. Configure Vibe CLI to Use Proxy

**Vibe CLI does NOT use `VIBE_API_ENDPOINT`.** You must configure Vibe CLI to send requests through the proxy using one of these methods:

**Method A: Global config** (persistent for all projects):
```bash
# Edit ~/.vibe/config.toml and change the Mistral provider's api_base
nano ~/.vibe/config.toml
```
Find the `[[providers]]` section with `name = "mistral"` and change:
```toml
# From:
api_base = "https://api.mistral.ai/v1"

# To:
api_base = "http://localhost:8000/v1"
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

Now all Vibe CLI API calls will be intercepted and logged.

### 3. Generate a Report

After using Vibe CLI, generate a summary:

```bash
python -m token_telemetry.cli report
```

## Command Reference

### Proxy Command

Start the telemetry proxy server that intercepts and logs API calls.

```bash
# Basic usage
python -m token_telemetry.cli proxy

# Custom port
python -m token_telemetry.cli proxy --port 9000

# Custom host
python -m token_telemetry.cli proxy --host 0.0.0.0

# Custom configuration file
python -m token_telemetry.cli proxy --config config/local.yaml

# Verbose logging
python -m token_telemetry.cli proxy --verbose
```

**Options:**
- `-p, --port PORT` - Port to run the proxy server on (default: 8000)
- `-H, --host HOST` - Host to bind to (default: localhost)
- `-c, --config PATH` - Path to configuration file
- `-v, --verbose` - Enable debug logging

### Report Command

Generate summary reports from logged telemetry data.

```bash
# Basic usage - show all data
python -m token_telemetry.cli report

# Filter by model
python -m token_telemetry.cli report --model mistral-medium

# Filter by origin
python -m token_telemetry.cli report --origin user

# Time period filters
python -m token_telemetry.cli report --period daily
python -m token_telemetry.cli report --period weekly
python -m token_telemetry.cli report --period monthly

# Custom date range
python -m token_telemetry.cli report --start-date 2026-05-19 --end-date 2026-05-20

# Combined filters
python -m token_telemetry.cli report --model mistral-large --origin agent --period weekly

# Save to file
python -m token_telemetry.cli report --output report.md

# Verbose logging
python -m token_telemetry.cli report --verbose
```

**Options:**
- `-c, --config PATH` - Path to configuration file
- `--model MODEL` - Filter by model name
- `--origin ORIGIN` - Filter by origin (user, agent, sub-agent)
- `--period {daily,weekly,monthly,all}` - Time period for summary (default: all)
- `--start-date DATE` - Start date for custom period (YYYY-MM-DD)
- `--end-date DATE` - End date for custom period (YYYY-MM-DD)
- `-o, --output PATH` - Output file path (default: stdout)
- `-v, --verbose` - Enable debug logging

## Direct Module Usage

You can also run modules directly without the CLI:

### Start Proxy

```bash
python -m token_telemetry.proxy
```

### Generate Report

```bash
python -m token_telemetry.reporter
```

### With Configuration

```bash
python -m token_telemetry.proxy --config config/local.yaml
python -m token_telemetry.reporter --config config/local.yaml
```

## Example Workflow

### Scenario 1: Track a Vibe CLI Session

```bash
# Terminal 1: Start the proxy
python -m token_telemetry.cli proxy

# Terminal 2: Use Vibe CLI with proxy (using Method B)
export VIBE_PROVIDERS='[{"name": "mistral", "api_base": "http://localhost:8000/v1", "api_key_env_var": "MISTRAL_API_KEY", "backend": "mistral"}]'
vibe
# ... use Vibe CLI as normal ...

# Terminal 3: Generate report after session
python -m token_telemetry.cli report
```

### Scenario 2: Monitor Specific Model Usage

```bash
# Generate report for mistral-large only
python -m token_telemetry.cli report --model mistral-large

# Generate weekly report for agent-originated calls
python -m token_telemetry.cli report --origin agent --period weekly
```

### Scenario 3: Daily Monitoring

```bash
# Start proxy in background
python -m token_telemetry.cli proxy &

# At end of day, generate daily report
python -m token_telemetry.cli report --period daily --output daily_report.md
```

### Scenario 4: Multi-User Tracking

```bash
# User 1 session (using Method B)
export VIBE_PROVIDERS='[{"name": "mistral", "api_base": "http://localhost:8000/v1", "api_key_env_var": "MISTRAL_API_KEY", "backend": "mistral"}]'
vibe --message "Hello from user1"

# User 2 session (direct curl with origin header)
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "X-Telemetry-Origin: agent" \
  -H "Content-Type: application/json" \
  -d '{"model": "mistral-medium", "messages": [...]}'

# View breakdown by origin
python -m token_telemetry.cli report
```

## Understanding the Output

### Summary Report Format

```
## Token Telemetry Summary (Daily)

- **Total API Calls**: 42
- **Total Tokens**: 32,450 (Input: 12,000, Output: 20,450)
- **Total Cost**: $0.024300

### Breakdown by Model
- **mistral-medium**: 20 calls, 15,000 tokens (Input: 5,000, Output: 10,000), $0.011250
- **mistral-large**: 22 calls, 17,450 tokens (Input: 7,000, Output: 10,450), $0.013080

### Breakdown by Origin
- **user**: 30 calls, 25,000 tokens (Input: 10,000, Output: 15,000), $0.018750
- **agent**: 12 calls, 7,450 tokens (Input: 2,000, Output: 5,450), $0.005625

*Database contains 42 total records*
```

### Field Descriptions

| Field | Description | Format |
|-------|-------------|--------|
| **Total API Calls** | Number of API calls logged | Integer |
| **Total Tokens** | Sum of all input + output tokens | Integer |
| **Input/Output Tokens** | Tokens in requests/responses | Integer |
| **Total Cost** | Total cost in USD | Decimal (6 places) |
| **Breakdown by Model** | Statistics grouped by model name | Per-model stats |
| **Breakdown by Origin** | Statistics grouped by call origin | Per-origin stats |

## Telemetry Metadata Tracked

Each API call logs the following metadata:

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `timestamp` | TEXT | ISO 8601 timestamp | `2026-05-19T14:30:45.123456` |
| `model` | TEXT | Model name | `mistral-medium` |
| `endpoint` | TEXT | API endpoint URL | `/v1/chat/completions` |
| `origin` | TEXT | Call initiator | `user`, `agent`, `sub-agent` |
| `request_tokens` | INTEGER | Tokens in request | `1000` |
| `response_tokens` | INTEGER | Tokens in response | `500` |
| `processing_time` | REAL | Time taken (seconds) | `1.234` |
| `status_code` | INTEGER | HTTP status code | `200` |
| `cost` | REAL | Calculated cost (USD) | `0.001125` |

## Cost Calculation

Costs are calculated using Mistral AI's pricing model:

- **Input tokens**: $0.25 per 1,000,000 tokens
- **Output tokens**: $0.75 per 1,000,000 tokens

**Formula:**
```
cost = (input_tokens / 1,000,000) * 0.25 + (output_tokens / 1,000,000) * 0.75
```

**Example:**
- 1,000 input tokens + 2,000 output tokens = $0.000250 + $0.001500 = $0.001750

See [Configuration Reference](configuration.md) for custom pricing.

## Using Custom Headers

The proxy extracts metadata from custom headers:

| Header | Purpose | Example |
|--------|---------|---------|
| `X-Telemetry-Model` | Override model detection | `X-Telemetry-Model: mistral-large` |
| `X-Telemetry-Origin` | Set call origin | `X-Telemetry-Origin: agent` |
| `X-Model` | Alternative model header | `X-Model: codestral-latest` |
| `X-Origin` | Alternative origin header | `X-Origin: sub-agent` |

**Example with curl:**

```bash
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "X-Telemetry-Model: mistral-large" \
  -H "X-Telemetry-Origin: my-agent" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -d '{"messages": [{"role": "user", "content": "Hello"}]}'
```

## Database Location

By default, telemetry data is stored in `telemetry.db` in the current directory.

You can change this via:
- Configuration file: `database.path`
- Environment variable: `TELEMETRY_DB_PATH`
- CLI argument: Not directly available, use config file

## Running Multiple Instances

For development or testing, you can run multiple proxy instances on different ports:

```bash
# Instance 1
python -m token_telemetry.cli proxy --port 8000 --config config/instance1.yaml

# Instance 2
python -m token_telemetry.cli proxy --port 8001 --config config/instance2.yaml
```

## Stopping the Proxy

Press `Ctrl+C` in the terminal where the proxy is running, or:

```bash
# Find the process ID
ps aux | grep token_telemetry

# Kill the process
kill <PID>
```

## Log Files

By default, logs are written to `telemetry.log` with the format:
```
2026-05-19 14:30:45 - token_telemetry.proxy - INFO - Starting proxy server on localhost:8000
```

Configure logging in your configuration file:

```yaml
logging:
  level: DEBUG  # DEBUG, INFO, WARNING, ERROR, CRITICAL
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
  file: "telemetry.log"
```

## Best Practices

### 1. Use Configuration Files

Create `config/local.yaml` for your custom settings instead of using CLI arguments every time.

### 2. Backup Your Database

The SQLite database contains all your telemetry history. Backup regularly:

```bash
cp telemetry.db telemetry.db.backup
```

### 3. Monitor Database Size

For long-term usage, the database can grow large. Consider:
- Regular exports to CSV/JSON
- Periodic cleanup of old data
- Separate databases for different projects

### 4. Use Different Origins

Set different origins for different users or agents to get detailed breakdowns:

```python
# In your application code
import os
os.environ['X-Telemetry-Origin'] = 'my-application'
```

### 5. Test Before Production Use

Test the proxy with a few API calls before using it in production:

```bash
# Make a test call
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model": "mistral-tiny", "messages": [{"role": "user", "content": "test"}]}'

# Check if it was logged
python -m token_telemetry.cli report
```

## See Also

- [Installation Guide](installation.md)
- [Configuration Reference](configuration.md)
- [Troubleshooting](troubleshooting.md)
