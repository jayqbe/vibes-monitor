# Example Configurations

This directory contains sample configuration files for different use cases of Token Telemetry.

## Configuration Files

| File | Description | Use Case |
|------|-------------|----------|
| [basic.yaml](basic.yaml) | Minimal configuration | Quick start, local development |
| [production.yaml](production.yaml) | Production-ready configuration | Production deployments |
| [development.yaml](development.yaml) | Development configuration | Local development with debugging |
| [multi-model.yaml](multi-model.yaml) | Multiple models with custom pricing | Testing different models |
| [custom-pricing.yaml](custom-pricing.yaml) | Custom pricing configuration | Non-standard pricing |
| [environment-variables.md](environment-variables.md) | Environment variable examples | Container/Orchestration |
| [docker-compose.yml](docker-compose.yml) | Docker Compose (future) | Containerized deployment |

## Quick Start

### 1. Copy a configuration file

```bash
# For basic usage
cp docs/examples/basic.yaml config/local.yaml

# For production
cp docs/examples/production.yaml config/local.yaml
```

### 2. Start the proxy

```bash
python -m token_telemetry.cli proxy
```

### 3. Configure Vibe CLI

Vibe CLI does NOT use `VIBE_API_ENDPOINT`. Configure Vibe CLI to use the proxy:

**Method A: Global config**
```bash
nano ~/.vibe/config.toml
# Change api_base from "https://api.mistral.ai/v1" to "http://localhost:8000/v1"
```

**Method B: Environment variable**
```bash
export VIBE_PROVIDERS='[{"name": "mistral", "api_base": "http://localhost:8000/v1", "api_key_env_var": "MISTRAL_API_KEY", "backend": "mistral"}]'
vibe
```

**Method C: Project config**
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

## Configuration Types

### YAML Configuration

All example files use YAML format, which is the recommended format for Token Telemetry.

### JSON Configuration

You can also use JSON format. See [json-example.json](json-example.json) for an example.

### Environment Variables

See [environment-variables.md](environment-variables.md) for environment variable examples.

## Creating Custom Configurations

Use the examples as a starting point and modify them for your needs:

```yaml
# Start with a base example
# cp docs/examples/basic.yaml config/local.yaml

# Then customize
proxy:
  port: 9000  # Change from default 8000

database:
  path: /var/lib/token_telemetry/telemetry.db

pricing:
  my-custom-model:
    input: 0.50
    output: 1.00
```

## See Also

- [Configuration Reference](../user/configuration.md) - Complete configuration documentation
- [Usage Guide](../user/usage.md) - How to use Token Telemetry
- [Installation Guide](../user/installation.md) - Installation instructions
