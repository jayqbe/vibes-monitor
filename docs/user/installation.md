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

### Method 1: Environment Variable (Recommended)

Add to your shell configuration file (`~/.bashrc`, `~/.zshrc`, or `~/.profile`):

```bash
# For bash/zsh
export VIBE_API_ENDPOINT=http://localhost:8000
```

Then reload your shell:

```bash
source ~/.bashrc  # or source ~/.zshrc
```

### Method 2: Temporary Environment Variable

For testing purposes:

```bash
# In one terminal, start the proxy
export VIBE_API_ENDPOINT=http://localhost:8000
vibe

# In another terminal, start the telemetry proxy
python -m token_telemetry.cli proxy
```

### Method 3: Vibe CLI Configuration

If Vibe CLI supports configuration files, you can set the API endpoint there:

```yaml
# ~/.vibe/config.yaml (hypothetical)
api_endpoint: http://localhost:8000
```

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
