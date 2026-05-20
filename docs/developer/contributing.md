# Contribution Guidelines

This document provides guidelines for contributing to the Token Telemetry project as a developer.

## Getting Started

### Prerequisites

- Python 3.11+
- Git
- pip and virtualenv (recommended)
- Familiarity with Python development

### Development Setup

```bash
# 1. Fork the repository on GitHub
# 2. Clone your fork locally
git clone https://github.com/jayqbe/vibes-monitor.git
cd vibes-monitor

# 3. Create a virtual environment (recommended)
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# 4. Install development dependencies
pip install -e ".[dev]"

# 5. Install pre-commit hooks
pip install pre-commit
pre-commit install

# 6. Run tests to ensure everything works
pytest
```

## Project Structure

```
token-telemetry/
├── config/                      # Configuration files
│   ├── default_config.yaml      # Default configuration
│   └── default_pricing.yaml     # Default pricing configuration
├── docs/                        # Documentation
│   ├── user/                    # User documentation (DOC-001)
│   │   ├── installation.md
│   │   ├── usage.md
│   │   ├── configuration.md
│   │   └── troubleshooting.md
│   └── developer/               # Developer documentation (DOC-002)
│       ├── architecture.md
│       ├── modules.md
│       ├── api_reference.md
│       └── contributing.md
├── src/
│   └── token_telemetry/          # Main package
│       ├── __init__.py         # Package initialization
│       ├── config.py           # Configuration management
│       ├── database.py         # Database operations
│       ├── cost_calculator.py  # Cost computation
│       ├── models.py           # Data models
│       ├── proxy.py            # HTTP proxy server
│       ├── reporter.py         # Summary generation
│       └── cli.py              # Command-line interface
├── tests/                       # Tests
│   ├── unit/                   # Unit tests
│   │   ├── test_config.py
│   │   ├── test_database.py
│   │   ├── test_cost_calculator.py
│   │   └── test_models.py
│   ├── integration/             # Integration tests
│   │   └── test_integration.py
│   └── edge_cases/              # Edge case tests
│       └── test_edge_cases.py
├── .gitignore
├── pyproject.toml               # Project configuration
├── requirements.txt             # Production dependencies
├── requirements-dev.txt         # Development dependencies
└── README.md
```

## Development Workflow

### 1. Create a Feature Branch

```bash
# Create branch from main
git checkout main
git pull origin main
git checkout -b feat/your-feature-name
```

**Branch Naming Conventions:**
- `feat/` - New feature
- `fix/` - Bug fix
- `docs/` - Documentation changes
- `refactor/` - Code refactoring
- `test/` - Test-related changes
- `chore/` - Maintenance tasks

### 2. Make Changes

- Follow the [Code Style Guidelines](#code-style-guidelines)
- Add tests for new functionality
- Update documentation as needed
- Keep commits atomic and focused

### 3. Run Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src/token_telemetry --cov-report=html

# Run specific test file
pytest tests/unit/test_database.py -v

# Run specific test
pytest tests/unit/test_cost_calculator.py::TestCostCalculator::test_calculate_cost -v
```

### 4. Check Code Quality

```bash
# Formatting
black src/token_telemetry tests/ --check

# Import sorting
isort src/token_telemetry tests/ --check

# Linting
flake8 src/token_telemetry tests/

# Type checking
mypy src/token_telemetry

# Fix formatting issues
black src/token_telemetry tests/
isort src/token_telemetry tests/
```

### 5. Commit Your Changes

```bash
# Stage changes
git add .

# Commit with descriptive message
git commit -m "feat(cost-calculator): add support for custom pricing models

Closes #123"
```

**Commit Message Guidelines:**
- Use [conventional commits](https://www.conventionalcommits.org/) format
- Include scope in parentheses (e.g., `feat(database)`, `fix(proxy)`)
- Reference issue numbers when applicable
- Keep subject line under 50 characters
- Use imperative mood ("Add" not "Added")

### 6. Push and Create Pull Request

```bash
# Push to your fork
git push origin feat/your-feature-name

# Create Pull Request on GitHub
```

## Code Style Guidelines

### Python Style

- Follow [PEP 8](https://peps.python.org/pep-0008/) style guide
- Use **black** for code formatting (configured in pyproject.toml)
- Use **isort** for import sorting
- Maximum line length: 100 characters

### Type Hints

- Use type hints for all function parameters and return values
- Use `-> None` for functions that don't return a value
- Use `Optional[T]` for parameters that can be None
- Use `Dict`, `List`, `Tuple`, etc. from `typing` module for complex types

**Example:**
```python
def calculate_cost(
    model: str,
    input_tokens: int,
    output_tokens: int,
    pricing_config: Optional[Dict[str, Dict[str, float]]] = None,
) -> float:
    """Calculate cost for an API call."""
    ...
```

### Docstrings

- Use **Google-style docstrings** for all modules, classes, and public functions
- Include type information in docstrings
- Document parameters, return values, and exceptions raised

**Example:**
```python
def calculate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """
    Calculate the cost for an API call based on token usage and model.
    
    Args:
        model: The model name (e.g., 'mistral-medium')
        input_tokens: Number of tokens in the request
        output_tokens: Number of tokens in the response
    
    Returns:
        The calculated cost in USD
    
    Raises:
        ValueError: If model is not found in pricing configuration
        ValueError: If token counts are negative
    """
    ...
```

### Naming Conventions

| Type | Convention | Example |
|------|------------|---------|
| Modules | lowercase_with_underscores | `cost_calculator.py` |
| Classes | PascalCase | `CostCalculator` |
| Functions | lowercase_with_underscores | `calculate_cost()` |
| Variables | lowercase_with_underscores | `input_tokens` |
| Constants | UPPERCASE_WITH_UNDERSCORES | `DEFAULT_PRICING` |
| Private members | _leading_underscore | `_get_connection()` |
| Protected members | _leading_underscore | `_database` |

### Testing

- All new code must have corresponding unit tests
- Target: **90%+ code coverage** for all modules
- Use **pytest** for testing
- Use **pytest-mock** for mocking dependencies
- Test both happy paths and edge cases

**Test File Structure:**
```python
# tests/unit/test_cost_calculator.py

import pytest
from token_telemetry.cost_calculator import CostCalculator, calculate_cost


class TestCostCalculator:
    """Tests for CostCalculator class."""
    
    def test_calculate_cost_basic(self):
        """Test basic cost calculation."""
        calculator = CostCalculator()
        cost = calculator.calculate_cost("mistral-medium", 1000, 2000)
        assert cost == pytest.approx(0.001750)
    
    def test_calculate_cost_zero_tokens(self):
        """Test cost calculation with zero tokens."""
        calculator = CostCalculator()
        cost = calculator.calculate_cost("mistral-medium", 0, 0)
        assert cost == 0.0
    
    def test_calculate_cost_negative_tokens(self):
        """Test that negative tokens raise ValueError."""
        calculator = CostCalculator()
        with pytest.raises(ValueError):
            calculator.calculate_cost("mistral-medium", -1, 0)
    
    def test_add_model(self):
        """Test adding a new model."""
        calculator = CostCalculator()
        calculator.add_model("my-model", input_rate=0.50, output_rate=1.00)
        assert "my-model" in calculator.get_all_models()
        pricing = calculator.get_pricing_for_model("my-model")
        assert pricing["input"] == 0.50
        assert pricing["output"] == 1.00
```

## Code Review Process

### Before Submitting a PR

- [ ] All tests pass: `pytest`
- [ ] Code passes linting: `flake8`
- [ ] Code is formatted: `black .`
- [ ] Type hints are valid: `mypy src/token_telemetry`
- [ ] Imports are sorted: `isort .`
- [ ] Test coverage is maintained or improved
- [ ] Docstrings added/updated
- [ ] Type hints added/updated

### PR Template

```markdown
## Description

[Brief description of the changes]

## Related Issues

- Closes #[issue-number]
- Related to #[issue-number]

## Changes Made

- [ ] New feature
- [ ] Bug fix
- [ ] Documentation update
- [ ] Code refactoring
- [ ] Tests
- [ ] Other (describe)

## Testing

- [ ] All existing tests pass
- [ ] New tests added for new functionality
- [ ] Manual testing performed

## Checklist

- [ ] Code follows style guidelines
- [ ] Docstrings added/updated
- [ ] Type hints added/updated
- [ ] Tests added/updated
- [ ] Documentation updated (if applicable)
```

### Review Process

1. All PRs require at least **one approval** from a maintainer
2. Reviewers will check:
   - Code quality and style
   - Test coverage
   - Documentation
   - Security considerations
   - Performance implications
3. Address all review comments before merging

## Reporting Issues

When reporting issues:

- Use the GitHub issue tracker
- Include a clear description of the problem
- Provide steps to reproduce
- Include relevant logs or error messages
- Specify your Python version and OS

## Release Process

### Versioning

This project uses [Semantic Versioning](https://semver.org/):
- `MAJOR` version: Breaking changes
- `MINOR` version: New features (backward-compatible)
- `PATCH` version: Bug fixes (backward-compatible)

### Creating a Release

1. Update version in `pyproject.toml`
2. Update `CHANGELOG.md` with release notes
3. Create a Git tag: `git tag -a v0.1.0 -m "Release v0.1.0"`
4. Push the tag: `git push origin v0.1.0`
5. Build and upload to PyPI (if applicable)

## Additional Resources

- [Python Documentation](https://docs.python.org/3/)
- [pytest Documentation](https://docs.pytest.org/)
- [black Documentation](https://black.readthedocs.io/)
- [PEP 8 Style Guide](https://peps.python.org/pep-0008/)
- [Google Style Docstrings](https://google.github.io/styleguide/pyguide.html#38-comments-and-docstrings)

## Code of Conduct

By participating in this project, you agree to abide by the [Code of Conduct](../../CODE_OF_CONDUCT.md).

## Questions?

For questions or discussions, please open an issue on GitHub or contact the maintainers.

---

## Development Tips

### Debugging

```bash
# Run with debug logging
export LOG_LEVEL=DEBUG
python -m token_telemetry.cli proxy

# Or in code
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Profiling

```bash
# Install profiler
pip install cProfile

# Profile a module
python -m cProfile -o profile.prof -s cumulative python -m token_telemetry.proxy

# View results
python -c "import pstats; pstats.Stats('profile.prof').sort_stats('cumulative').print_stats(20)"
```

### Database Inspection

```bash
# View database contents
sqlite3 telemetry.db "SELECT * FROM calls LIMIT 10;"

# Get table info
sqlite3 telemetry.db ".schema calls"

# Count records
sqlite3 telemetry.db "SELECT COUNT(*) FROM calls;"

# Query by model
sqlite3 telemetry.db "SELECT * FROM calls WHERE model = 'mistral-medium';"
```

### Testing with Mock Data

```python
# In tests, use an in-memory database
from token_telemetry.database import Database
from token_telemetry.models import CallRecord

db = Database(":memory:")

# Insert test data
record = CallRecord(
    timestamp="2026-05-19T14:30:45",
    model="mistral-medium",
    endpoint="/v1/chat/completions",
    origin="user",
    request_tokens=1000,
    response_tokens=500,
    processing_time=1.234,
    status_code=200,
    cost=0.001125,
)
db.insert_record(record)

# Test queries
records = db.get_records()
stats = db.get_summary_stats()
```

## Documentation

### Updating Documentation

- User documentation: `docs/user/`
- Developer documentation: `docs/developer/`
- API reference: `docs/developer/api_reference.md`

**Documentation Guidelines:**
- Use Markdown format
- Keep examples simple and clear
- Include code examples that are tested and working
- Document all public APIs
- Use consistent formatting

### Building Documentation

Currently, documentation is in Markdown format and can be viewed directly on GitHub or with any Markdown viewer.

Future: Consider using MkDocs or Sphinx for HTML documentation generation.

## Maintenance Tasks

### Updating Dependencies

```bash
# Update a dependency
pip install --upgrade package-name

# Update requirements.txt
pip freeze > requirements.txt

# Or for development dependencies
pip install --upgrade --upgrade-strategy eager package-name
pip freeze > requirements-dev.txt
```

### Running Integration Tests

```bash
# Run all integration tests
pytest tests/integration/ -v

# Run with mocked Mistral API
# (Requires pytest-mock)
pytest tests/integration/test_integration.py -v
```

### Code Coverage

```bash
# Run tests with coverage
pytest --cov=src/token_telemetry --cov-report=html --cov-report=term

# View HTML report
open htmlcov/index.html

# Check coverage for specific file
pytest --cov=src/token_telemetry --cov-report=term tests/unit/test_database.py
```

## See Also

- [Architecture Overview](architecture.md) - System architecture
- [Module Documentation](modules.md) - Detailed module documentation
- [API Reference](api_reference.md) - Complete API reference
- [CONTRIBUTING.md](../../CONTRIBUTING.md) - General contribution guidelines
