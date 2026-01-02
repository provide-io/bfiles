# bfiles

A modular file bundling utility for LLM processing - bundle multiple files into a single text archive and unbundle them back.

## Features

- 📦 **Bundle files** into human-readable text archives
- 🔄 **Unbundle archives** back to original directory structure
- 🎯 Respect `.gitignore` patterns
- 🔍 Custom include/exclude patterns (glob, regex, literal)
- 🔐 File integrity verification (checksums)
- 🧩 **File chunking** for large files (token-based)
- 📊 Rich terminal output with statistics
- 🚀 LLM-friendly output format

## Quick Start

### Bundle files

```bash
# Bundle current directory
bfiles bundle

# Bundle specific directory
bfiles bundle --root-dir /path/to/project

# Custom output location
bfiles bundle --output my-bundle.txt

# With exclusions
bfiles bundle --exclude "*.log" --exclude "temp/"

# With inclusions (overrides excludes)
bfiles bundle --include "*.py" --include "*.md"
```

### Unbundle files

```bash
# Extract bundle to current directory
bfiles unbundle my-bundle.txt

# Extract to specific directory
bfiles unbundle my-bundle.txt --output-dir /path/to/destination

# Dry run (show what would be extracted)
bfiles unbundle my-bundle.txt --dry-run
```

### File Chunking

For large files that exceed LLM context windows:

```bash
# Chunk files larger than 4000 tokens
bfiles bundle --chunk-size 4000

# With 100-token overlap between chunks
bfiles bundle --chunk-size 4000 --chunk-overlap 100
```

## Documentation

- [docs/reference.md](https://github.com/provide-io/bfiles/blob/main/docs/reference.md) - Complete reference manual
- [docs/bfiles.1](https://github.com/provide-io/bfiles/blob/main/docs/bfiles.1) - Man page
- [docs/specs.txt](https://github.com/provide-io/bfiles/blob/main/docs/specs.txt) - Bundle format specification
- [docs/MATURITY_REPORT.md](https://github.com/provide-io/bfiles/blob/main/docs/MATURITY_REPORT.md) - Code maturity assessment

## Development

### Setup

```bash
# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install with dev dependencies
uv pip install -e ".[dev]"
```

### Run Tests

```bash
# All tests
pytest tests/ -v

# With coverage
pytest tests/ --cov=src/bfiles --cov-report=term-missing

# Specific test file
pytest tests/test_unbundler.py -v
```

### Lint and Format

```bash
# Check code
ruff check src tests

# Format code
ruff format src tests

# Type check
mypy src
```

## Contributing
See [CLAUDE.md](https://github.com/provide-io/bfiles/blob/main/CLAUDE.md) for contribution guidance.

## License

Apache License 2.0 - See LICENSE file for details.

## Installation

```bash
uv pip install -e .
```

For development:

```bash
uv pip install -e ".[dev]"
```

## Command Reference

See `man bfiles` or `docs/reference.md` for complete documentation.

### Global Options

- `--version` - Show version and exit
- `-h, --help` - Show help message

### Bundle Options

- `-d, --root-dir PATH` - Root directory to scan (default: `.`)
- `-o, --output PATH` - Output bundle file path
- `-i, --include PATTERN` - Include pattern (can be repeated)
- `-e, --exclude PATTERN` - Exclude pattern (can be repeated)
- `--show-excluded` - Display excluded files in summary
- `--exclusion-report PATH` - Generate exclusion report file
- `--chunk-size TOKENS` - Maximum tokens per chunk
- `--chunk-overlap TOKENS` - Token overlap between chunks
- `-l, --log-level LEVEL` - Logging level (DEBUG, INFO, WARNING, ERROR)

### Unbundle Options

- `-o, --output-dir PATH` - Destination directory (default: `.`)
- `-f, --force` - Overwrite existing files
- `--dry-run` - Show what would be extracted without doing it
- `--verify-checksums` - Verify file integrity (default: true)
- `-l, --log-level LEVEL` - Logging level

## Bundle File Format

Bundles are text files with this structure:

```
--- START OF BFILE bundle-name ---
bfiles bundle generated on: 2025-10-26 11:30:00
Config: root=/path/to/project | encoding=utf-8 | ...

### FILE 1: src/main.py | size=1234 | hash=abc123... | type=text/python ###
--- BOF src/main.py ---
[file contents]
--- EOF src/main.py ---

### FILE 2: README.md | size=567 | hash=def456... | type=text/markdown ###
--- BOF README.md ---
[file contents]
--- EOF README.md ---

### BUNDLE SUMMARY ###
Files: 2 | Total Size: 1.8 KB | Duplicates: 0 | Empty: 0
--- END OF BFILE bundle-name ---
```

See `docs/specs.txt` for complete format specification.

## Configuration

Default exclusions:

- Hidden files/directories (`.*`)
- Python bytecode (`.pyc`, `.pyo`, `__pycache__/`)
- Virtual environments (`.venv/`, `venv/`)
- Git directory (`.git/`)
- Build artifacts (`build/`, `dist/`, `node_modules/`)
- Environment files (`.env`)
- Log files (`*.log`)
- Temporary files (`*.tmp`, `*.swp`)
- Previous bundles (`*bfiles*.txt`, `*.bf.txt`)

## Python API

```python
from bfiles import BfilesConfig, bundle_files

# Create configuration
config = BfilesConfig(
    root_dir="/path/to/project",
    output_file="my-bundle.txt",
    exclude_patterns=["*.log", "temp/"],
    chunk_size=4000,
    chunk_overlap=100
)

# Bundle files
bundle_files(config)
```

## Dependencies

- Python >= 3.10
- attrs >= 23.1.0 - Configuration and data classes
- click >= 8.1.7 - CLI framework
- pathspec >= 0.12.1 - .gitignore pattern matching
- rich >= 14.0.0 - Enhanced terminal output
- structlog >= 25.3.0 - Structured logging
- tiktoken >= 0.7.0 - Token counting

## Project Info

- Homepage: https://bfiles.provide.io/
- Repository: https://github.com/provide-io/bfiles
- Issues: https://github.com/provide-io/bfiles/issues

## CLI Alias

After installation, `bfiles` is available as both:
- `bfiles` - Full command name
- `bf` - Short alias

```bash
bf bundle
bf unbundle my-bundle.txt
```

---

**Note**: The unbundler feature is comprehensive but may have edge cases. Please report any issues you encounter when unbundling files.

Copyright (c) Provide.io LLC.
