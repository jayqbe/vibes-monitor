# Environment Variable Examples

This document provides examples of using environment variables to configure Token Telemetry.

## Overview

Token Telemetry supports configuration via environment variables with the following priority:

```
1. Environment Variables (highest priority)
2. User Configuration File (config/local.yaml)
3. Default Configuration File (config/default_config.yaml)
4. Package Defaults (lowest priority)
```

## Supported Environment Variables

| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| `TELEMETRY_PROXY_HOST` | Proxy server host | `localhost` | `0.0.0.0` |
| `TELEMETRY_PROXY_PORT` | Proxy server port | `8000` | `9000` |
| `MISTRAL_BASE_URL` | Mistral API endpoint | `https://api.mistral.ai` | `https://custom.endpoint` |
| `VIBE_API_ENDPOINT` | **For Vibe CLI only** - tells Vibe CLI where the proxy is | None | `http://localhost:8000` |
| `TELEMETRY_DB_PATH` | Database file path | `telemetry.db` | `/var/lib/token_telemetry/telemetry.db` |

**Note:** `VIBE_API_ENDPOINT` is **NOT** used by the proxy server. It is only read by Vibe CLI to locate the proxy. The proxy forwards requests to `MISTRAL_BASE_URL` (or the default `https://api.mistral.ai`).

## Usage Examples

### Example 1: Basic Configuration

```bash
# Set environment variables
export TELEMETRY_PROXY_HOST=localhost
export TELEMETRY_PROXY_PORT=8000
export MISTRAL_BASE_URL=https://api.mistral.ai
export TELEMETRY_DB_PATH=telemetry.db

# Start the proxy
python -m token_telemetry.cli proxy
```

### Example 2: Production Configuration

```bash
# Production settings
export TELEMETRY_PROXY_HOST=0.0.0.0
export TELEMETRY_PROXY_PORT=8080
export MISTRAL_BASE_URL=https://api.mistral.ai
export TELEMETRY_DB_PATH=/var/lib/token_telemetry/telemetry.db

# Start the proxy
python -m token_telemetry.cli proxy
```

### Example 3: Vibe CLI Integration

```bash
# In terminal 1: Start the proxy
export TELEMETRY_PROXY_PORT=8000
python -m token_telemetry.cli proxy

# In terminal 2: Use Vibe CLI with proxy
export VIBE_API_ENDPOINT=http://localhost:8000
vibe
```

### Example 4: Different Port

```bash
# Use port 9000 instead of default 8000
export TELEMETRY_PROXY_PORT=9000

# Start proxy
python -m token_telemetry.cli proxy

# Vibe CLI must use the same port
export VIBE_API_ENDPOINT=http://localhost:9000
vibe
```

### Example 5: Custom Database Location

```bash
# Use a custom database location
export TELEMETRY_DB_PATH=/path/to/my/telemetry.db

# Start proxy
python -m token_telemetry.cli proxy
```

### Example 6: Remote Mistral API

```bash
# Point to a custom Mistral API endpoint
export MISTRAL_BASE_URL=https://custom.mistral.endpoint

# Start proxy
python -m token_telemetry.cli proxy
```

**Note:** Do NOT use `VIBE_API_ENDPOINT` to set a custom Mistral API endpoint. `VIBE_API_ENDPOINT` is only for Vibe CLI to find the proxy server. Use `MISTRAL_BASE_URL` to configure where the proxy forwards requests.

## Docker Examples

### Example 1: Docker Run with Environment Variables

```bash
docker run \
  -e TELEMETRY_PROXY_HOST=0.0.0.0 \
  -e TELEMETRY_PROXY_PORT=8000 \
  -e MISTRAL_BASE_URL=https://api.mistral.ai \
  -e TELEMETRY_DB_PATH=/data/telemetry.db \
  -v /path/to/data:/data \
  -p 8000:8000 \
  token-telemetry
```

### Example 2: Docker Compose

```yaml
# docker-compose.yml
version: '3.8'

services:
  token-telemetry:
    image: token-telemetry
    environment:
      - TELEMETRY_PROXY_HOST=0.0.0.0
      - TELEMETRY_PROXY_PORT=8000
      - MISTRAL_BASE_URL=https://api.mistral.ai
      - TELEMETRY_DB_PATH=/data/telemetry.db
    volumes:
      - ./data:/data
    ports:
      - "8000:8000"
    restart: unless-stopped
```

Start with:
```bash
docker-compose up -d
```

## Kubernetes Examples

### Example 1: Kubernetes Deployment

```yaml
# deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: token-telemetry
spec:
  replicas: 1
  selector:
    matchLabels:
      app: token-telemetry
  template:
    metadata:
      labels:
        app: token-telemetry
    spec:
      containers:
      - name: token-telemetry
        image: token-telemetry
        env:
        - name: TELEMETRY_PROXY_HOST
          value: "0.0.0.0"
        - name: TELEMETRY_PROXY_PORT
          value: "8000"
        - name: MISTRAL_BASE_URL
          value: "https://api.mistral.ai"
        - name: TELEMETRY_DB_PATH
          value: "/data/telemetry.db"
        volumeMounts:
        - name: data
          mountPath: /data
        ports:
        - containerPort: 8000
      volumes:
      - name: data
        persistentVolumeClaim:
          claimName: token-telemetry-data
```

### Example 2: Kubernetes Service

```yaml
# service.yaml
apiVersion: v1
kind: Service
metadata:
  name: token-telemetry
spec:
  selector:
    app: token-telemetry
  ports:
  - port: 8000
    targetPort: 8000
  type: ClusterIP
```

## Shell Script Examples

### Example 1: Start Script

```bash
#!/bin/bash
# start_telemetry.sh

# Set environment variables
export TELEMETRY_PROXY_HOST=localhost
export TELEMETRY_PROXY_PORT=8000
export MISTRAL_BASE_URL=https://api.mistral.ai
export TELEMETRY_DB_PATH=telemetry.db

# Start the proxy
python -m token_telemetry.cli proxy
```

Make executable:
```bash
chmod +x start_telemetry.sh
./start_telemetry.sh
```

### Example 2: Setup Script

```bash
#!/bin/bash
# setup_telemetry.sh

# Create directories
mkdir -p /var/lib/token_telemetry
mkdir -p /var/log/token_telemetry

# Set environment variables
export TELEMETRY_PROXY_HOST=0.0.0.0
export TELEMETRY_PROXY_PORT=8080
export MISTRAL_BASE_URL=https://api.mistral.ai
export TELEMETRY_DB_PATH=/var/lib/token_telemetry/telemetry.db

# Start the proxy in background
python -m token_telemetry.cli proxy &

# Store PID for later
echo $! > /tmp/token_telemetry.pid

echo "Token Telemetry started on port 8080"
echo "PID: $!"
```

### Example 3: Stop Script

```bash
#!/bin/bash
# stop_telemetry.sh

# Get PID from file
PID=$(cat /tmp/token_telemetry.pid)

# Kill the process
kill $PID

# Remove PID file
rm /tmp/token_telemetry.pid

echo "Token Telemetry stopped"
```

## .env File Example

Create a `.env` file in your project directory:

```bash
# .env
TELEMETRY_PROXY_HOST=localhost
TELEMETRY_PROXY_PORT=8000
MISTRAL_BASE_URL=https://api.mistral.ai
TELEMETRY_DB_PATH=telemetry.db
```

Load it before running:

```bash
# Using dotenv (install with: pip install python-dotenv)
from dotenv import load_dotenv
load_dotenv()

# Or source it in bash
set -a && source .env && set +a
python -m token_telemetry.cli proxy
```

## Multiple Environments

### Example: Development vs Production

```bash
# Development environment
export ENV=development
export TELEMETRY_PROXY_PORT=8000
export TELEMETRY_DB_PATH=telemetry_dev.db

# Production environment
export ENV=production
export TELEMETRY_PROXY_HOST=0.0.0.0
export TELEMETRY_PROXY_PORT=8080
export TELEMETRY_DB_PATH=/var/lib/token_telemetry/telemetry.db
```

Use a script to load the appropriate configuration:

```bash
#!/bin/bash
# start.sh

if [ "$ENV" = "production" ]; then
    export TELEMETRY_PROXY_HOST=0.0.0.0
    export TELEMETRY_PROXY_PORT=8080
    export TELEMETRY_DB_PATH=/var/lib/token_telemetry/telemetry.db
else
    export TELEMETRY_PROXY_HOST=localhost
    export TELEMETRY_PROXY_PORT=8000
    export TELEMETRY_DB_PATH=telemetry_dev.db
fi

python -m token_telemetry.cli proxy
```

## Environment Variable Precedence

### Example: Overriding Configuration

```yaml
# config/local.yaml
proxy:
  port: 8000
```

```bash
# Environment variable overrides the config file
export TELEMETRY_PROXY_PORT=9000
python -m token_telemetry.cli proxy
# Result: Port 9000 (environment variable wins)
```

### Example: CLI Argument Overrides Everything

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

## Checking Current Configuration

```bash
# Print current configuration
python -c "from token_telemetry.config import load_config; c = load_config(); print(c)"

# Or more detailed
python -c "from token_telemetry.config import load_config; import pprint; c = load_config(); pprint.pprint(c.__dict__)"
```

## Best Practices

1. **Use environment variables for secrets**: Never hardcode sensitive information
2. **Document your configuration**: Comment your environment variable settings
3. **Use different files for different environments**: `config/local.yaml`, `config/production.yaml`, etc.
4. **Set defaults in code**: Provide sensible defaults for optional configuration
5. **Validate configuration**: Check that required values are set before starting
6. **Use .env files for development**: But never commit them to version control

## See Also

- [Configuration Reference](../user/configuration.md) - Complete configuration documentation
- [Installation Guide](../user/installation.md) - Installation instructions
- [Usage Guide](../user/usage.md) - Usage examples
