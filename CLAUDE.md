# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

`bfiles` is a modular file bundling utility for LLM processing. It bundles multiple files into a single human-readable text archive with metadata, and can unbundle them back to their original directory structure.

## Development Commands

### Environment Setup
```bash
# Install dependencies
uv sync

# Activate environment
source .venv/bin/activate
```

### Testing
```bash
# Run all tests (excluding slow/integration by default)
uv run pytest

# Run with coverage
uv run pytest --cov=bfiles --cov-report=term-missing

# Run specific test file
uv run pytest tests/test_unbundler.py -v

# Run slow or integration tests
uv run pytest -m slow
uv run pytest -m integration

# Run all tests including slow/integration
uv run pytest -m ""
```

### Code Quality
```bash
# Format code
uv run ruff format src/ tests/

# Lint code
uv run ruff check src/ tests/

# Auto-fix lint issues (safe fixes only)
uv run ruff check --fix src/ tests/

# Type checking
uv run mypy src/
```

After editing Python files, run:
```bash
ruff format <file>
ruff check --fix <file>
mypy <file>
```

## Architecture

### Core Components

1. **CLI** (`src/bfiles/cli.py`)
   - Entry points: `bf` and `bfiles` commands
   - Commands: `bundle`, `unbundle`

2. **Configuration** (`src/bfiles/config.py`)
   - `BfilesConfig` - attrs-based configuration class
   - Pattern matching (glob, regex, literal)
   - Default exclusions (gitignore-like patterns)

3. **Bundler** (`src/bfiles/bundler.py`)
   - File discovery and filtering
   - Metadata extraction (size, hash, type)
   - Bundle file generation

4. **Unbundler** (`src/bfiles/unbundler.py`)
   - Bundle parsing
   - File extraction
   - Checksum verification

5. **Chunker** (`src/bfiles/chunker.py`)
   - Token-based file splitting
   - Overlap management
   - tiktoken integration

### Key Design Patterns

- **Attrs for Data Classes**: Uses `@attrs.define` throughout
- **Foundation Logging**: Uses `provide.foundation` logger, never raw structlog
- **Modern Type Hints**: Python 3.11+ syntax (`list[str]`, not `List[str]`)
- **Absolute Imports**: No relative imports
- **Pathspec**: Uses pathspec library for .gitignore pattern matching

### Bundle Format

```
--- START OF BFILE bundle-name ---
bfiles bundle generated on: TIMESTAMP
Config: root=PATH | encoding=utf-8 | ...

### FILE 1: path/to/file | size=N | hash=HASH | type=MIME ###
--- BOF path/to/file ---
[contents]
--- EOF path/to/file ---

### BUNDLE SUMMARY ###
Files: N | Total Size: X KB | ...
--- END OF BFILE bundle-name ---
```

## Testing Strategy

- **80% coverage minimum** (enforced via `--cov-fail-under=80`)
- **Markers**: `unit`, `integration`, `slow`, `fast`, `benchmark`
- **Async support**: Uses pytest-asyncio in auto mode
- **Foundation testkit**: Uses provide-testkit for fixtures

## Important Notes

- Uses `provide-foundation[all]` for logging - never use print() or raw structlog
- Output and error messages use `pout()` and `perr()` from Foundation
- Token counting via tiktoken for LLM context window management
- Rich terminal output for user feedback
- File integrity verification via checksums

## Python API

```python
from bfiles import BfilesConfig, bundle_files

config = BfilesConfig(
    root_dir="/path/to/project",
    output_file="bundle.txt",
    exclude_patterns=["*.log"],
    chunk_size=4000,
    chunk_overlap=100
)

bundle_files(config)
```

## Code Style

- Line length: 111 characters
- Comprehensive ruff rules (E, F, W, I, UP, ANN, B, C90, SIM, PTH, RUF)
- No inline defaults - use constants or config modules
- No backward compatibility or migration logic
