# Contributing to Token Telemetry

Thank you for your interest in contributing to Token Telemetry! This document provides guidelines for contributing to the project.

## Development Setup

### Prerequisites

- Python 3.11 or higher
- Git
- pip and virtualenv (recommended)

### Getting Started

1. **Fork the repository** on GitHub
2. **Clone your fork** locally:
   ```bash
   git clone https://github.com/jayqbe/vibes-monitor.git
   cd vibes-monitor
   ```

3. **Create a virtual environment** (recommended):
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

4. **Install development dependencies**:
   ```bash
   pip install -e ".[dev]"
   ```

5. **Install pre-commit hooks**:
   ```bash
   pip install pre-commit
   pre-commit install
   ```

6. **Run tests** to ensure everything works:
   ```bash
   pytest
   ```

## Project Structure

```
token-telemetry/
├── src/
│   └── token_telemetry/
│       ├── __init__.py      # Package initialization
│       ├── config.py        # Configuration management
│       ├── database.py      # SQLite database operations
│       ├── cost_calculator.py # Cost computation logic
│       ├── proxy.py         # HTTP proxy server
│       ├── models.py        # Data models (CallRecord, SummaryStats)
│       ├── reporter.py      # Summary generation
│       └── cli.py           # Command-line interface
├── tests/
│   ├── unit/               # Unit tests
│   │   ├── __init__.py
│   │   ├── test_config.py
│   │   ├── test_database.py
│   │   ├── test_cost_calculator.py
│   │   ├── test_proxy.py
│   │   └── test_reporter.py
│   ├── integration/         # Integration tests
│   │   └── test_end_to_end.py
│   └── edge_cases/          # Edge case tests
│       └── test_edge_cases.py
├── config/
│   ├── default_config.yaml # Default configuration
│   └── default_pricing.yaml # Default pricing configuration
├── docs/
│   ├── user/               # User documentation
│   └── developer/           # Developer documentation
├── scripts/
│   └── deploy.sh           # Deployment scripts
├── pyproject.toml          # Project configuration
├── requirements.txt        # Production dependencies
├── requirements-dev.txt    # Development dependencies
├── README.md
├── CONTRIBUTING.md
└── .gitignore
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

### Docstrings

- Use **Google-style docstrings** for all modules, classes, and public functions
- Include type information in docstrings
- Document parameters, return values, and exceptions raised

Example:
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
    """
    ...
```

### Naming Conventions

- **Modules**: lowercase_with_underscores.py
- **Classes**: PascalCase
- **Functions**: lowercase_with_underscores
- **Variables**: lowercase_with_underscores
- **Constants**: UPPERCASE_WITH_UNDERSCORES
- **Private members**: _leading_underscore (for internal use)

### Testing

- All new code must have corresponding unit tests
- Target: **90%+ code coverage** for all modules
- Use **pytest** for testing
- Use **pytest-mock** for mocking dependencies
- Test both happy paths and edge cases

#### Test File Structure

- Place tests in `tests/unit/`, `tests/integration/`, or `tests/edge_cases/`
- Name test files: `test_<module>.py`
- Name test functions: `test_<functionality>`
- Use fixtures for common test setup

Example:
```python
# tests/unit/test_cost_calculator.py
from token_telemetry.cost_calculator import calculate_cost


def test_calculate_cost_mistral_medium():
    """Test cost calculation for mistral-medium model."""
    cost = calculate_cost("mistral-medium", 1000, 2000)
    assert cost == 0.002  # (1000/1M * 0.25) + (2000/1M * 0.75)


def test_calculate_cost_zero_tokens():
    """Test cost calculation with zero tokens."""
    cost = calculate_cost("mistral-medium", 0, 0)
    assert cost == 0.0
```

## Commit Message Guidelines

- Use **conventional commits** format
- Messages should be clear and descriptive
- Reference issue numbers when applicable

### Commit Types

- `feat`: A new feature
- `fix`: A bug fix
- `docs`: Documentation only changes
- `style`: Changes that do not affect the meaning of the code (formatting)
- `refactor`: A code change that neither fixes a bug nor adds a feature
- `perf`: A code change that improves performance
- `test`: Adding missing tests
- `chore`: Changes to the build process or auxiliary tools

### Message Format

```
<type>(<scope>): <subject>

<body>

<footer>
```

Examples:
```
feat(cost-calculator): add support for custom pricing models

- Add configuration loading for custom model pricing
- Update calculate_cost to use configurable rates
- Add tests for custom pricing scenarios

Closes #123
```

```
fix(database): handle concurrent write operations safely

- Implement connection pooling for SQLite
- Use WAL mode for better concurrency
- Add retry logic for database operations

Fixes #456
```

## Pull Request Process

1. **Create a feature branch**: `git checkout -b feat/your-feature-name`
2. **Commit your changes**: Use meaningful commit messages
3. **Push to your fork**: `git push origin feat/your-feature-name`
4. **Create a Pull Request** on GitHub

### PR Requirements

Before submitting a PR:
- [ ] All tests pass: `pytest`
- [ ] Code passes linting: `flake8`
- [ ] Code is formatted: `black .`
- [ ] Type hints are valid: `mypy src/token_telemetry`
- [ ] Imports are sorted: `isort .`
- [ ] Test coverage is maintained or improved

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

## Code Review

- All PRs require at least **one approval** from a maintainer
- Reviewers will check:
  - Code quality and style
  - Test coverage
  - Documentation
  - Security considerations
  - Performance implications

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

## Contact

For questions or discussions, please open an issue on GitHub.

---

Thank you for contributing to Token Telemetry!
