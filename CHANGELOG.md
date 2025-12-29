# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.3.0] - 2025-12-28

### Added
- Initial public release
- File bundling for LLM processing
- Unbundling with integrity verification
- Token-based chunking with tiktoken integration
- Pattern matching with pathspec (.gitignore support)
- Rich terminal output for user feedback
- Comprehensive CLI (`bf` and `bfiles` commands)

### Technical Details
- Python 3.11+ required
- Dependencies: provide-foundation, tiktoken, pathspec, rich
- Development tools: ruff, mypy, pytest
- UV-based development workflow
