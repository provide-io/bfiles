# Contributing to bfiles

Thank you for your interest in contributing to bfiles! This document provides guidelines for contributing to the project.

## Getting Started

### Prerequisites

- Python 3.11 or higher
- `uv` package manager

### Development Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/provide-io/bfiles.git
   cd bfiles
   ```

2. Set up the development environment:
   ```bash
   uv sync
   ```

This will create a virtual environment and install all development dependencies.

## Development Workflow

### Running Tests

```bash
# Run all tests (excluding slow/integration by default)
uv run pytest

# Run with coverage (minimum 80% required)
uv run pytest --cov=bfiles --cov-report=term-missing

# Run specific test file
uv run pytest tests/test_unbundler.py -v

# Run slow or integration tests
uv run pytest -m slow
uv run pytest -m integration

# Run all tests including slow/integration
uv run pytest -m ""

# Or using wrknv
we run test
```

### Code Quality

Before submitting a pull request, ensure your code passes all quality checks:

```bash
# Format code
uv run ruff format src/ tests/

# Lint code
uv run ruff check src/ tests/

# Auto-fix lint issues (safe fixes only)
uv run ruff check --fix src/ tests/

# Type checking
uv run mypy src/

# Or using wrknv
we run format
we run lint
we run typecheck
```

### Code Style

- Follow PEP 8 guidelines (enforced by `ruff`)
- Use modern Python 3.11+ type hints (e.g., `list[str]` not `List[str]`)
- Use absolute imports, never relative imports
- Add comprehensive type hints to all functions and methods
- Write docstrings for public APIs
- Use `from __future__ import annotations` for unquoted types

### Logging and Output

**IMPORTANT**: Use the correct output method for each context:

- **Application logging**: Use `provide.foundation.logger` for internal logging
  ```python
  from provide.foundation import logger
  logger.debug("Processing file", path=file_path)
  ```

- **User-facing output**: Use `pout()` and `perr()` from Foundation
  ```python
  from provide.foundation.console.output import pout, perr
  pout("✅ Bundle created successfully")
  perr("❌ Failed to process file")
  ```

- **Never use**: `print()` statements or raw `structlog` directly

## Project Structure

```
bfiles/
├── src/bfiles/
│   ├── cli.py              # Command-line interface (bundle, unbundle commands)
│   ├── config.py           # Configuration classes and pattern matching
│   ├── bundler.py          # File discovery, filtering, and bundle generation
│   ├── unbundler.py        # Bundle parsing and file extraction
│   ├── chunker.py          # Token-based file splitting with tiktoken
│   ├── extractor.py        # File content extraction
│   ├── metadata_writer.py  # Bundle metadata generation
│   ├── parser.py           # Bundle file parsing
│   ├── progress.py         # Progress indicators
│   ├── output.py           # Terminal output formatting
│   └── utils.py            # Utility functions
├── tests/                  # Test suite
│   ├── conftest.py        # Pytest fixtures
│   ├── test_bundler.py    # Bundler tests
│   ├── test_unbundler.py  # Unbundler tests
│   ├── test_chunker.py    # Chunker tests
│   └── ...
├── docs/                   # Documentation
│   ├── reference.md       # Complete reference manual
│   ├── specs.txt          # Bundle format specification
│   ├── bfiles.1           # Man page
│   └── MATURITY_REPORT.md # Code maturity assessment
└── pyproject.toml         # Project configuration
```

## Adding New Features

### Adding a New CLI Command

1. Add the command to `src/bfiles/cli.py`:
   ```python
   @cli.command()
   @click.option(...)
   def your_command(...):
       """Command description."""
       pass
   ```

2. Implement the logic in the appropriate module
3. Add tests in `tests/test_cli.py`
4. Update `docs/reference.md` with usage examples

### Adding New Bundler Options

1. Add the configuration field to `BfilesConfig` in `src/bfiles/config.py`
2. Implement the feature in `src/bfiles/bundler.py`
3. Add CLI option in `src/bfiles/cli.py`
4. Add tests in `tests/test_bundler.py`
5. Update documentation

### Modifying the Bundle Format

**IMPORTANT**: Bundle format changes require careful coordination:

1. Update the format specification in `docs/specs.txt`
2. Modify the writer logic in `src/bfiles/bundler.py`
3. Modify the parser logic in `src/bfiles/unbundler.py`
4. Add comprehensive tests for both reading and writing
5. Consider backward compatibility for existing bundles
6. Update all documentation and examples

## Testing Guidelines

### Writing Tests

- Place tests in the `tests/` directory
- Name test files with `test_` prefix (e.g., `test_bundler.py`)
- Use descriptive test names that explain what is being tested
- Include both positive and negative test cases
- Add edge case tests
- Use pytest markers: `unit`, `integration`, `slow`, `fast`, `benchmark`

### Test Structure

```python
def test_feature_name_scenario():
    """Test description explaining what this test validates."""
    # Arrange
    config = BfilesConfig(
        root_dir="/path/to/test/dir",
        exclude_patterns=["*.log"]
    )

    # Act
    result = bundle_files(config)

    # Assert
    assert result.success
    assert len(result.files) > 0
```

### Test Fixtures

Use the shared fixtures in `tests/conftest.py`:

```python
def test_with_fixture(tmp_path, sample_files):
    """Use pytest fixtures for common test setup."""
    # tmp_path provides a temporary directory
    # sample_files provides pre-configured test files
    pass
```

## Documentation

### Docstring Format

Use Google-style docstrings:

```python
def bundle_files(config: BfilesConfig) -> BundleResult:
    """Bundle files according to configuration.

    Args:
        config: Configuration object with bundling options

    Returns:
        BundleResult containing success status and metadata

    Raises:
        BfilesError: If bundling fails

    Example:
        >>> config = BfilesConfig(root_dir="./project")
        >>> result = bundle_files(config)
        >>> print(f"Bundled {result.file_count} files")
    """
```

### Updating Documentation

When adding new features or changing APIs:

1. Update relevant docstrings in the code
2. Update `README.md` for user-facing changes
3. Update `docs/reference.md` for command-line changes
4. Update the man page in `docs/bfiles.1` if needed
5. Update `docs/specs.txt` for bundle format changes

## Submitting Changes

### Pull Request Process

1. Create a feature branch from `main`:
   ```bash
   git checkout -b feature/your-feature-name main
   ```

2. Make your changes following the guidelines

3. Ensure all tests pass and code quality checks pass:
   ```bash
   uv run pytest
   uv run ruff format src/ tests/
   uv run ruff check src/ tests/
   uv run mypy src/
   ```

4. Commit your changes:
   ```bash
   git commit -m "Add feature: description of what was added"
   ```

5. Push to the branch:
   ```bash
   git push origin feature/your-feature-name
   ```

6. Open a Pull Request

7. Ensure your PR:
   - Has a clear title and description
   - References any related issues
   - Includes tests for new functionality
   - Maintains or improves code coverage (80% minimum)
   - Updates documentation as needed
   - Passes all CI checks

### Commit Message Guidelines

- Use present tense ("Add feature" not "Added feature")
- Use imperative mood ("Move cursor to..." not "Moves cursor to...")
- Limit first line to 72 characters
- Reference issues and pull requests when relevant

Examples:
- `Add chunk overlap support for better LLM context`
- `Fix unbundler handling of binary files`
- `Update documentation for pattern matching syntax`

## Code Review Process

All submissions require review. The maintainers will:

- Review code for quality, style, and correctness
- Ensure tests are comprehensive and passing
- Verify documentation is updated and accurate
- Check for breaking changes
- Ensure code coverage meets minimum threshold (80%)

## Getting Help

- Open an issue for bugs or feature requests
- Check existing issues and documentation first
- Refer to the documentation in the `docs/` directory

## Python API

If contributing to the Python API, ensure your changes work correctly:

```python
from bfiles import BfilesConfig, bundle_files

config = BfilesConfig(
    root_dir="/path/to/project",
    output_file="bundle.txt",
    exclude_patterns=["*.log"],
    chunk_size=4000,
    chunk_overlap=100
)

result = bundle_files(config)
```

## License

By contributing to bfiles, you agree that your contributions will be licensed under the Apache-2.0 License.
