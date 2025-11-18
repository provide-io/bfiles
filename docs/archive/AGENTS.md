# Repository Guidelines

## Project Structure & Module Organization
- Source lives in `src/bfiles`, split by concern (`bundler.py`, `unbundler.py`, `config.py`, etc.) with the CLI entry point in `cli.py`.
- Tests reside in `tests`, mirroring the package layout and drawing shared fixtures from `tests/fixtures`.
- Reference material, specs, and plans are in `docs/`; keep CLI-visible documentation in sync with changes to `docs/reference.md` and `docs/bfiles.1`.

## Build, Test, and Development Commands
- Create an isolated environment before contributing: `python3 -m venv .venv && source .venv/bin/activate`.
- Install with development extras for tooling and test support: `pip install -e ".[dev]"`.
- Run the full suite (with required coverage) via `pytest --cov=src/bfiles`; use `-k` to focus on a failing path.
- Lint, format, and type-check prior to submitting: `ruff check src tests`, `ruff format src tests`, and `mypy src`.

## Coding Style & Naming Conventions
- Follow the Ruff configuration (`line-length = 100`, double quotes, space indentation); rely on `ruff format` to enforce layout.
- Keep modules and packages snake_case, classes PascalCase, and constants UPPER_SNAKE_CASE to match existing modules.
- All new code should be type-annotated and attr-friendly; prefer `attrs.define` patterns already present in the core modules.
- When adding CLI options, surface them through `click` in `cli.py` and document defaults in `config.py`.

## Testing Guidelines
- Pytest is configured with `--cov-fail-under=85`; maintain or raise coverage when touching critical paths.
- Place new test files under `tests/test_<topic>.py` and mirror helper data in `tests/fixtures`.
- Use parametrized tests for glob/exclusion logic to stay consistent with existing suites, and capture CLI behavior with the provided `CliRunner` fixtures.

## Commit & Pull Request Guidelines
- Recent history favors Conventional Commit headers (`Feat:`, `Fix:`, `Docs:`); keep subjects imperative and ≤72 characters.
- Include context in the body (problem, approach, follow-up) and reference related issues using GitHub keywords.
- For pull requests, provide a short summary, note test/lint runs, attach CLI transcripts or bundle samples when UX changes, and request review before merging.
