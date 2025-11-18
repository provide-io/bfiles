# `bfiles` Refinement and Standardization Plan

Date: 2025-06-27

This document outlines the plan to further refine the `bfiles` utility, focusing on standardization, addressing items from `docs/TODO.md`, and improving overall quality and robustness.

## I. Goals

1.  **Enhance Test Coverage & Reliability**: Bring test coverage above 90% and resolve any outstanding test issues (XFAILs).
2.  **Complete Core Documentation**: Generate detailed reference documentation.
3.  **Standardize CLI Behavior**: Ensure CLI behavior is consistent and intuitive, especially regarding output.
4.  **Improve Configurability**: Make aspects like the tokenizer configurable.
5.  **Maintain Code Quality**: Uphold and improve code structure and conventions.

## II. Detailed Plan Items

This plan corresponds to tasks in `docs/TODO.md` and items identified in the Maturity Report.

### 1. Testing and Quality Enhancement (Ref: `docs/TODO.md` - Testing & Quality)

*   **Action**: Increase test coverage from ~82.44% to >90%.
    *   **Details**:
        *   Analyze coverage reports (`pytest --cov=src/bfiles`) to identify specific modules and lines needing more tests.
        *   Focus on `src/bfiles/output.py` (currently low coverage).
        *   Add tests for more branches/edge cases in `src/bfiles/core.py` (e.g., error conditions during symlink resolution, complex chunking scenarios, OS errors during walk).
        *   Improve coverage for `src/bfiles/exclusions.py` (e.g., error conditions in `_load_gitignore_specs`, complex pattern interactions).
        *   Ensure `src/bfiles/logger.py` and `src/bfiles/config.py` edge cases are covered.
    *   **Priority**: High
    *   **Status**: 🚧 (In Progress / Needs Action)

*   **Action**: Resolve XFAIL (expected failure) tests.
    *   **Details**:
        *   `tests/test_exclusions.py::test_unreadable_gitignore_file`: Investigate why capturing the specific `logger.warning` is problematic. Explore alternative ways to assert the expected behavior or error handling, perhaps by checking `exclusion_manager.get_error_count()` or mocking specific OS calls if necessary.
        *   `tests/test_output.py::test_display_summary_table_shows_excluded`: Debug `capsys`/`stdout` capture issues for this specific test scenario. Ensure consistent output capturing across all test environments.
    *   **Priority**: Medium
    *   **Status**: 🚧 (Needs Action)

### 2. Documentation (`docs/TODO.md` - Documentation)

*   **Action**: Create detailed Markdown documentation (`docs/reference.md`).
    *   **Details**: This document should cover:
        *   **Installation**: Standard installation, and installation with optional dependencies (`gitignore`, `rich`).
        *   **Usage**:
            *   Basic bundling examples.
            *   Detailed explanation of all CLI options with examples.
            *   Advanced usage scenarios (e.g., complex include/exclude combinations, symlink handling).
        *   **Exclusion Logic**:
            *   Deep dive into precedence rules (.gitignore, include, exclude).
            *   Syntax for different pattern types (glob, regex, literal string).
            *   How default exclusions work and how to override them.
        *   **Chunking**:
            *   Detailed explanation of `--chunk-size` and `--chunk-overlap`.
            *   How token counting works (mentioning `tiktoken` and `cl100k_base`).
            *   Impact of chunking on the bundle format.
        *   **Bundle File Format**:
            *   Reiterate the structure from `docs/specs.txt` (Preamble, Header, File Entries, Footer).
            *   Detailed breakdown of the `### FILE ... ###` metadata line and its fields (op codes, size, tokens, cs, mime, mod, chunk_tokens, etc.).
            *   Explanation of `<<< BOF <<<` and `>>> EOF >>>` delimiters.
        *   **API Usage (if applicable as a library)**: If `bfiles` is intended to be used programmatically, document the main functions/classes (`BfilesConfig`, `bundle_files`, `list_potential_files`).
        *   **Troubleshooting**: Common issues and solutions.
    *   **Priority**: High (as per user request)
    *   **Status**: 🚧 (Needs Action)

*   **Action**: Create an "Examples Gallery" in the documentation.
    *   **Details**: A separate page or section in `docs/reference.md` showcasing various practical use cases and command combinations.
    *   **Priority**: Medium
    *   **Status**: 💡 (Idea / Not Started)

### 3. CLI Enhancements (`docs/TODO.md` - CLI Enhancements)

*   **Action**: Refine output to stdout.
    *   **Details**: Verify and ensure that `bfiles --output -` or `bfiles ... | other_command` correctly writes the bundle content to `sys.stdout` without creating a default file. Update `cli.py` logic if necessary. Add tests for this specific behavior.
    *   **Priority**: Medium
    *   **Status**: 🚧 (Needs Verification/Refinement)

*   **Action**: Consider adding an option to specify output encoding for the bundle file.
    *   **Details**: While the spec implies UTF-8, allowing user control over output encoding could be useful in some contexts. This would involve adding a CLI option and updating `core.py` where the bundle is written.
    *   **Priority**: Low
    *   **Status**: 💡 (Idea / Not Started)

### 4. Configurability & Feature Refinements (Ref: Maturity Report & `docs/TODO.md`)

*   **Action**: Allow configuration of the tokenizer.
    *   **Details**:
        *   Add a `tokenizer_name` (or similar) field to `BfilesConfig`.
        *   Add a corresponding CLI option (e.g., `--tokenizer`).
        *   Update `FileMetadata.from_path()` and `core.py`'s `_write_file_or_chunks_to_buffer()` to use the configured tokenizer instead of the hardcoded `cl100k_base`.
        *   Ensure graceful error handling if an invalid tokenizer name is provided.
    *   **Priority**: Medium
    *   **Status**: 💡 (Idea / Not Started)

*   **Action**: Add `--max-total-size-bytes` limit.
    *   **Details**: Implement functionality to stop bundling if the total size of *content* being added to the bundle exceeds a specified byte limit. This would be similar to `--max-files` but based on cumulative size.
    *   **Priority**: Low
    *   **Status**: 💡 (Idea / Not Started)

### 5. Codebase Standardization and Minor Refinements

*   **Naming Conventions**:
    *   **Review**: Ensure all internal functions, variables, and class members consistently follow PEP 8 (snake_case for functions/variables, PascalCase for classes).
    *   **Action**: Perform a codebase sweep. Most of it is good, but a final check is worthwhile.
*   **Docstring Consistency**:
    *   **Review**: Ensure all public modules, classes, functions, and methods have comprehensive docstrings. Check for consistent formatting (e.g., Sphinx style or Google style).
    *   **Action**: Fill in any missing docstrings, especially for helper functions in `config.py` or `core.py` if they are complex enough to warrant it.
*   **Error Message Clarity**:
    *   **Review**: Check logged error messages and user-facing CLI errors for clarity, consistency, and actionability.
    *   **Action**: Refine messages where necessary to provide better guidance to the user.
*   **`BundleSummary` Usage**:
    *   **Review**: The `BundleSummary` class in `metadata.py` is defined but doesn't appear to be actively used or populated in `core.py`. The summary text is generated directly from individual counts.
    *   **Action**: Decide whether to fully integrate `BundleSummary` by populating it during `bundle_files` and using it to generate the summary text, or remove/simplify it if the current approach is preferred. Integrating it could make summary generation cleaner. (Low Priority Refactor)

### 6. Future: Unbundling Functionality (`docs/TODO.md` - Potential Future Features & `docs/specs.txt`)

*   **Action**: Design and implement unbundling functionality.
    *   **Details**: Based on `docs/specs.txt` (Section 5: Unbundling Process and Section 7.2: Unbundling Errors). This would be a significant new feature.
        *   New CLI command (e.g., `bfiles unbundle <bundle_file> -o <output_dir>`).
        *   Parser for the bfiles bundle format.
        *   Logic for file/directory creation.
        *   Chunk reassembly.
        *   Error handling for malformed bundles or write errors.
        *   Security considerations (path traversal).
    *   **Priority**: Future (Major Feature)
    *   **Status**: 💡 (Idea / Not Started)

## III. Timeline and Next Steps

1.  **Immediate**: Create `docs/reference.md` (Plan Item II.2.Action).
2.  **Short Term**:
    *   Address CLI stdout behavior (Plan Item II.3.Action).
    *   Begin work on increasing test coverage (Plan Item II.1.Action).
3.  **Medium Term**:
    *   Resolve XFAIL tests (Plan Item II.1.Action).
    *   Implement configurable tokenizer (Plan Item II.4.Action).
    *   Codebase standardization review (Plan Item II.5).
4.  **Long Term/Future**:
    *   Consider other `💡` items from `docs/TODO.md` based on user feedback/priority.
    *   Design and implement unbundling functionality.

This plan will be updated as tasks are completed or new requirements emerge.
