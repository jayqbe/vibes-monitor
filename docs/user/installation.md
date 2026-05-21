# Installation Guide

This guide covers all installation options for Token Telemetry.

## Prerequisites

| Requirement | Version | Notes |
|-------------|---------|-------|
| Python | 3.11+ | Required for all installation methods |
| pip | Latest | Python package manager |
| Git | Latest | Only required for source installation |

## Quick Installation

### Method 1: Install from Source (Recommended for Development)

```bash
# Clone the repository
git clone https://github.com/jayqbe/vibes-monitor.git
cd vibes-monitor

# Install in development mode (editable)
pip install -e ".[dev]"
```

The development installation includes all dependencies plus development tools (testing, linting, formatting).

### Method 2: Install Package Only

```bash
# Clone the repository
git clone https://github.com/jayqbe/vibes-monitor.git
cd vibes-monitor

# Install only production dependencies
pip install -e .
```

### Method 3: Direct pip Install (Future)

Once published to PyPI:

```bash
pip install token-telemetry
```

## Verification

Verify your installation by running:

```bash
# Check if the package can be imported
python -c "import token_telemetry; print(token_telemetry.__version__)"

# Check CLI commands are available
python -m token_telemetry.cli --help
```

Expected output:
```
usage: token-telemetry [-h] {proxy,report} ...

Token Telemetry for Vibe CLI - Track API calls and compute costs

positional arguments:
  {proxy,report}
    proxy       Start the telemetry proxy server
    report      Generate a telemetry summary report
```

## Installing Dependencies Manually

### Production Dependencies

The core package requires:

```bash
pip install requests pyyaml
```

### Development Dependencies

For development and testing:

```bash
pip install -r requirements-dev.txt
```

Or individually:

```bash
# Testing
pip install pytest pytest-cov pytest-mock

# Formatting & Linting
pip install black isort flake8 mypy
```

## Setting Up Vibe CLI Integration

### Method 1: Global Configuration (Recommended)

Edit your global Vibe CLI configuration to route all requests through the proxy:

```bash
# Edit the global config file
nano ~/.vibe/config.toml
```

Find the `[[providers]]` section with `name = "mistral"` and change the `api_base`:

```toml
# From:
api_base = "https://api.mistral.ai/v1"

# To:
api_base = "http://localhost:8000/v1"
```

Save the file. All future Vibe CLI sessions will now use the proxy.

### Method 2: Temporary Environment Variable

For testing purposes, use the environment variable:

```bash
# In one terminal, start the proxy
python -m token_telemetry.cli proxy

# In another terminal, use Vibe CLI with proxy
export VIBE_PROVIDERS='[{"name": "mistral", "api_base": "http://localhost:8000/v1", "api_key_env_var": "MISTRAL_API_KEY", "backend": "mistral"}]'
vibe
```

> **Note:** Vibe CLI does NOT use `VIBE_API_ENDPOINT`. You must use `VIBE_PROVIDERS` or edit the config file.

### Method 3: Project-Specific Configuration

For project-specific tracking, create a local Vibe CLI config:

```bash
mkdir -p .vibe
cat > .vibe/config.toml << 'EOF'
[[providers]]
name = "mistral"
api_base = "http://localhost:8000/v1"
api_key_env_var = "MISTRAL_API_KEY"
backend = "mistral"
EOF
```

This configuration only affects Vibe CLI when run from this directory.

## Platform-Specific Notes

### macOS

```bash
# Install Python via Homebrew
brew install python

# Install Git
brew install git
```

### Linux (Ubuntu/Debian)

```bash
# Install Python and pip
sudo apt update
sudo apt install python3 python3-pip python3-venv git

# Use Python 3 explicitly
python3 -m pip install -e .
```

### Windows

```powershell
# Install Python from https://www.python.org/downloads/
# Open Command Prompt as Administrator
python -m pip install -e ".[dev]"
```

## Virtual Environment Setup

Recommended for development:

```bash
# Create virtual environment
python -m venv .venv

# Activate it
# On macOS/Linux:
source .venv/bin/activate

# On Windows:
.venv\Scripts\activate

# Install dependencies
pip install -e ".[dev]"

# Deactivate when done
deactivate
```

## Docker Installation (Optional)

A Dockerfile is planned for future releases. For now, use the source installation method.

## Troubleshooting Installation

See [Troubleshooting](troubleshooting.md) for common installation issues.

## Next Steps

Once installed, proceed to:
- [Usage Guide](usage.md) - Learn how to use Token Telemetry
- [Configuration Reference](configuration.md) - Customize your setup
