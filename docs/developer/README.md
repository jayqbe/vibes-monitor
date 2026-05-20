# Token Telemetry Developer Documentation

Welcome to the Token Telemetry developer documentation! This directory contains comprehensive guides for developers, contributors, and anyone interested in understanding the internals of Token Telemetry.

## Documentation Structure

| Document | Description |
|----------|-------------|
| [Architecture Overview](architecture.md) | High-level system architecture and data flow |
| [Module Documentation](modules.md) | Detailed documentation for each module |
| [API Reference](api_reference.md) | Complete API reference for all public interfaces |
| [Contribution Guidelines](contributing.md) | How to contribute to the project |

## Architecture

Token Telemetry follows a modular, layered architecture:

```
Vibe CLI → Proxy Wrapper → Mistral API
                 ↓
         Telemetry Logger → SQLite Database
                 ↓
         Cost Calculator
                 ↓
         Reporter → Text Summaries
```

See [Architecture Overview](architecture.md) for details.

## Modules

The system consists of the following core modules:

| Module | Purpose |
|--------|---------|
| `config.py` | Configuration management |
| `database.py` | SQLite database operations |
| `cost_calculator.py` | Cost computation logic |
| `models.py` | Data models (CallRecord, SummaryStats) |
| `proxy.py` | HTTP proxy server |
| `reporter.py` | Summary generation |
| `cli.py` | Command-line interface |

See [Module Documentation](modules.md) for details.

## Development Setup

```bash
# Clone the repository
git clone https://github.com/jayqbe/vibes-monitor.git
cd vibes-monitor

# Install in development mode
pip install -e ".[dev]"

# Install pre-commit hooks
pip install pre-commit
pre-commit install
```

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src/token_telemetry --cov-report=html

# Run specific test file
pytest tests/unit/test_database.py -v
```

## Code Quality

This project uses:
- **black** for code formatting
- **isort** for import sorting
- **flake8** for linting
- **mypy** for type checking

```bash
# Check all
black src/token_telemetry tests/ --check
isort src/token_telemetry tests/ --check
flake8 src/token_telemetry tests/
mypy src/token_telemetry
```

## User Documentation

For end-user documentation, see the [User Documentation](../user/README.md).
