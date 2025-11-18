# `bfiles` Development TODO

This document tracks the development status of `bfiles`.

## Core Functionality
- [✅] File bundling into a single text file
- [✅] Metadata inclusion (path, size, mod time, type, hash)
- [✅] `.gitignore` support
- [✅] Custom include patterns (glob, literal)
- [✅] Custom exclude patterns (regex, glob, literal)
- [✅] Default exclusion patterns
- [✅] Duplicate file detection and handling (by content hash)
- [✅] Symbolic link handling (`--follow-symlinks`)
- [✅] Output to specified file
- [✅] Output to default file if `-o` is omitted
- [✅] Verbose logging (`--log-level`)
- [✅] Quiet mode (covered by log levels, e.g. critical)
- [✅] File chunking based on token count (`--chunk-size`, `--chunk-overlap`)
- [✅] Token counting using `tiktoken`
- [✅] Configurable encoding for reading files
- [✅] Configurable hash algorithm

## CLI Enhancements
- [✅] `--list-files-only` option
- [✅] `--show-excluded` option for console summary
- [✅] `--exclusion-report` to generate a file detailing exclusions
- [✅] `--add-comment` for custom bundle header comment
- [✅] `--version` option
- [✅] `--help` option
- [🚧] Output to stdout when output file is `-` or when piped (current behavior might create default file; needs verification/refinement for explicit stdout pipe)
- [💡] Interactive mode for selecting files (low priority)
- [💡] Option to specify output encoding for the bundle file

## Testing & Quality
- [✅] Basic unit tests for core logic
- [✅] CLI interaction tests
- [🚧] Achieve >90% test coverage (currently ~82.44%)
    - [✅] `test_cli_exclusion_report` failure regarding `os.walk` is resolved (test now passes).
    - [🚧] Investigate and fix 2 XFAIL tests (`test_unreadable_gitignore_file`, `test_display_summary_table_shows_excluded`).
- [✅] Linting and formatting (Ruff)
- [✅] Type checking (Mypy)
- [✅] CI setup (GitHub Actions or similar - *external to this agent's work*)

## Documentation
- [✅] README.md with basic usage and features
- [✅] Comprehensive Man Page (`docs/bfiles.1`) - Updated for unbundle.
- [✅] Detailed Markdown documentation (`docs/reference.md`) - Created, includes unbundle.
- [✅] This TODO.md file (updated)
- [✅] Maturity Report (`docs/MATURITY_REPORT.md`)
- [💡] Examples gallery in documentation

## Core Unbundling Functionality
- [✅] CLI for unbundling (`bfiles unbundle`)
- [✅] Bundle parsing (header, file entries, content)
- [✅] File and directory reconstruction
- [✅] Chunk reassembly with intelligent overlap verification
- [✅] Options: `--output-dir`, `--force`, `--list-only`, `--dry-run`
- [✅] Logging for unbundle process
- [✅] Unit tests for unbundler (parser, extractor, overlap logic)

## Potential Future Features
- [💡] Support for pre-processing hooks (e.g., run a command on files before bundling)
- [💡] Support for different bundle formats (e.g., JSON, XML)
- [💡] Compression of bundled output
- [💡] Integration with other tools (e.g., as a library)
- [💡] Option to specify tokenizer for chunking beyond `cl100k_base` (e.g., via `BfilesConfig`)
- [💡] `--max-total-size-bytes` limit for bundle content (similar to `--max-files`)
- [🚧] Unbundling: Add checksum verification for extracted files (post-extraction optional step).

**Legend:**
- ✅: Completed
- 🚧: In Progress / Partially Implemented / Needs Action
- 💡: Idea / Not Started / Future consideration
- ❌: Blocked / Issue identified (currently no items are ❌)
