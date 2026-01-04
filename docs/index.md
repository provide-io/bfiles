# bfiles

!!! warning "Pre-release"
    This documentation covers a pre-release. APIs and features may change, and some documented items are exploratory and may change or be removed.


A modular file bundling utility for LLM processing - bundle multiple files into a single text archive and unbundle them back.

## Features

- **Bundle files** into human-readable text archives
- **Unbundle archives** back to original directory structure
- Respect `.gitignore` patterns
- Custom include/exclude patterns (glob, regex, literal)
- File integrity verification (checksums)
- **File chunking** for large files (token-based)
- Rich terminal output with statistics
- LLM-friendly output format

## Quick Start

### Bundle files

```bash
# Bundle current directory
bfiles bundle

# Bundle specific directory
bfiles bundle --root-dir /path/to/project

# Custom output location
bfiles bundle --output my-bundle.txt
```

### Unbundle files

```bash
# Extract bundle to current directory
bfiles unbundle my-bundle.txt

# Extract to specific directory
bfiles unbundle my-bundle.txt --output-dir /path/to/destination
```

## Python API

```python
from bfiles import BfilesConfig, bundle_files

config = BfilesConfig(
    root_dir="/path/to/project",
    output_file="my-bundle.txt",
    exclude_patterns=["*.log", "temp/"],
    chunk_size=4000,
    chunk_overlap=100
)

bundle_files(config)
```

## CLI Alias

After installation, `bfiles` is available as both:

- `bfiles` - Full command name
- `bf` - Short alias

See the [Reference](reference.md) for complete documentation.
