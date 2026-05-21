# Token Telemetry User Documentation

Welcome to the Token Telemetry user documentation! This directory contains comprehensive guides for installing, configuring, and using Token Telemetry with Vibe CLI.

## Documentation Structure

| Document | Description |
|----------|-------------|
| [Installation Guide](installation.md) | How to install Token Telemetry on various platforms |
| [Usage Guide](usage.md) | How to use Token Telemetry with Vibe CLI |
| [Configuration Reference](configuration.md) | Complete reference for all configuration options |
| [Troubleshooting](troubleshooting.md) | Common issues and solutions |

## Getting Started

New users should follow this order:

1. **[Installation Guide](installation.md)** - Install Token Telemetry
2. **[Usage Guide](usage.md)** - Learn how to use it with Vibe CLI
3. **[Configuration Reference](configuration.md)** - Customize your setup
4. **[Troubleshooting](troubleshooting.md)** - Solve common problems

## Quick Start

For the impatient:

```bash
# Install
pip install -e .

# Start proxy
python -m token_telemetry.cli proxy

# Configure Vibe CLI (in another terminal)
# Method B: Environment variable
export VIBE_PROVIDERS='[{"name": "mistral", "api_base": "http://localhost:8000/v1", "api_key_env_var": "MISTRAL_API_KEY", "backend": "mistral"}]'
vibe

# Generate report
python -m token_telemetry.cli report
```

## Support

- Check [Troubleshooting](troubleshooting.md) for common issues
- Review the [Functional Specification](../../FUNCTIONAL_SPECIFICATION.md) for technical details
- See [CONTRIBUTING](../../CONTRIBUTING.md) if you want to contribute

## Developer Documentation

For developers and contributors, see the [Developer Documentation](../developer/README.md).
