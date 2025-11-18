# bfiles Reference Manual

`bfiles` is a command-line utility designed to bundle multiple files into a single text-based archive and, conversely, to unbundle these archives back into their original directory structure. It's particularly useful for packaging text-based projects, source code, or configuration files for sharing, analysis, or input to Large Language Models (LLMs).

## Table of Contents

1.  [Installation](#installation)
2.  [Commands](#commands)
    *   [Global Options](#global-options)
    *   [bundle](#bundle)
        *   [Synopsis](#bundle-synopsis)
        *   [Options](#bundle-options)
        *   [Examples](#bundle-examples)
    *   [unbundle](#unbundle)
        *   [Synopsis](#unbundle-synopsis)
        *   [Arguments](#unbundle-arguments)
        *   [Options](#unbundle-options)
        *   [Examples](#unbundle-examples)
3.  [Bundle File Format](#bundle-file-format)
    *   [Overall Structure](#overall-structure)
    *   [Preamble](#preamble)
    *   [Bundle Header](#bundle-header)
    *   [File Entry](#file-entry)
        *   [Metadata Line](#metadata-line)
        *   [Content Delimiters](#content-delimiters)
        *   [File Content](#file-content)
    *   [Bundle Footer (Summary)](#bundle-footer-summary)
4.  [Exclusion and Inclusion Logic](#exclusion-and-inclusion-logic)
    *   [Precedence Rules](#precedence-rules)
    *   [Pattern Types](#pattern-types)
    *   [Default Exclusions](#default-exclusions)
5.  [Chunking](#chunking)
    *   [Overview](#chunking-overview)
    *   [Tokenization](#tokenization)
    *   [Overlap Handling](#overlap-handling)
6.  [API Usage (Python Library)](#api-usage-python-library)
7.  [Troubleshooting](#troubleshooting)

## 1. Installation

Install `bfiles` using pip:

```bash
pip install bfiles
```

To include optional dependencies for enhanced terminal UI (using Rich library) and .gitignore processing (using pathspec):

```bash
pip install bfiles[tui,gitignore]
```

Or, for development, clone the repository and install with all development dependencies:

```bash
git clone <repository_url>
cd bfiles
pip install -e ".[dev,tui,gitignore]"
```

## 2. Commands

`bfiles` operates through two main subcommands: `bundle` and `unbundle`.

### Global Options

These options apply to the `bfiles` command itself:

*   `--version`: Shows the version of `bfiles` and exits.
*   `-h, --help`: Shows the main help message and exits.

### `bundle`

The `bundle` command is used to create a bfiles archive.

#### Bundle Synopsis

```bash
bfiles bundle [OPTIONS]
```

#### Bundle Options

*   `-d DIRECTORY, --root-dir DIRECTORY`
    *   Root directory to scan for files.
    *   Default: `.` (current directory).
*   `-o FILEPATH, --output FILEPATH`
    *   Output file path for the bundle.
    *   Default: `bfiles-YYYYMMDD-HHMMSS.txt` in the root directory.
*   `-i PATTERN, --include PATTERN`
    *   Inclusion pattern (glob/literal). Overrides excludes except `.gitignore`.
    *   Can be specified multiple times.
*   `-e PATTERN, --exclude PATTERN`
    *   Exclusion pattern (regex/glob/literal). A pattern ending with `/` implies a directory.
    *   Can be specified multiple times.
*   `--show-excluded`
    *   Show excluded files and directories (including those from `.gitignore`) in a summary table after processing.
*   `--exclusion-report FILEPATH`
    *   Generate a text report of all excluded items (including those from `.gitignore`) to the specified file.
*   `-l LEVEL, --log-level LEVEL`
    *   Set the logging level.
    *   Choices: `debug`, `info`, `warn`, `warning`, `error`, `critical`.
    *   Default: `warning`.
*   `--encoding ENCODING_STRING`
    *   Encoding to use when reading files for bundling.
    *   Default: `utf-8`.
*   `--hash-algo ALGORITHM`
    *   Hashing algorithm for file checksums.
    *   Choices: `sha256`, `sha1`, `md5`, `sha512`.
    *   Default: `sha256`.
*   `--no-gitignore`
    *   Disable automatic loading and processing of `.gitignore` files.
*   `--follow-symlinks`
    *   Follow symbolic links during directory scan.
*   `-m NUMBER, --max-files NUMBER`
    *   Maximum number of files to include in the bundle. No limit by default.
*   `--list-files-only`
    *   List files that would be included (after all exclusions) and then exit without creating a bundle.
*   `--add-comment STRING`
    *   Add a custom comment line to the bundle header.
*   `--chunk-size TOKENS`
    *   Maximum number of tokens per chunk. If not specified or set to 0, chunking is disabled. Requires the `tiktoken` library.
    *   Default: `None` (no chunking).
*   `--chunk-overlap TOKENS`
    *   Number of tokens to overlap between consecutive chunks.
    *   Default: `0`.

#### Bundle Examples

1.  **Basic Bundling**: Bundle all files in the current directory and its subdirectories into `my_archive.bfiles`.
    ```bash
    bfiles bundle -o my_archive.bfiles
    ```

2.  **Specific Root Directory**: Bundle files from `./src`.
    ```bash
    bfiles bundle -d ./src -o src_bundle.txt
    ```

3.  **Include/Exclude Patterns**: Bundle only Python files, excluding the `tests` directory and hidden files.
    ```bash
    bfiles bundle -i "*.py" -e "tests/" -e ".*" -o python_code.bfiles
    ```

4.  **Disable .gitignore**: Bundle all files, ignoring any `.gitignore` rules.
    ```bash
    bfiles bundle --no-gitignore -o full_project.txt
    ```

5.  **File Chunking**: Bundle files, splitting large files into chunks of approximately 1500 tokens with a 100-token overlap.
    ```bash
    bfiles bundle --chunk-size 1500 --chunk-overlap 100 -o chunked_large_files.bfiles
    ```

6.  **List Files**: Preview which files would be included from `my_project/` without actually creating a bundle.
    ```bash
    bfiles bundle -d my_project/ --list-files-only
    ```

### `unbundle`

The `unbundle` command extracts files from a bfiles archive.

#### Unbundle Synopsis

```bash
bfiles unbundle BUNDLE_FILE [OPTIONS]
```

#### Unbundle Arguments

*   `BUNDLE_FILE` (Positional Argument)
    *   The path to the bfiles bundle file that needs to be extracted. This argument is required.

#### Unbundle Options

*   `--output-dir DIRECTORY, -o DIRECTORY`
    *   Directory to extract files into.
    *   Default: If not specified, a new directory is created in the same location as the `BUNDLE_FILE`. This new directory is named after the bundle file (e.g., if `my_bundle.txt` is unbundled, output is to `my_bundle_unbundled/`).
*   `--force, -f`
    *   If specified, existing files in the output directory will be overwritten without prompting. Use with caution.
*   `--list-only, --ls`
    *   Lists the contents of the bundle (file paths, sizes, chunk info) without extracting any files.
*   `--dry-run, -n`
    *   Shows what files would be extracted and where they would be placed, but does not actually write any files to the disk. This is useful for previewing the unbundle operation.
*   `--log-level LEVEL, -l LEVEL`
    *   Set the logging level for the unbundle operation.
    *   Choices: `debug`, `info`, `warn`, `warning`, `error`, `critical`.
    *   Default: `warning`.

#### Unbundle Examples

1.  **Basic Unbundling**: Extract `my_archive.bfiles` to a new directory `my_archive_unbundled/`.
    ```bash
    bfiles unbundle my_archive.bfiles
    ```

2.  **Extract to Specific Directory**: Extract `project_backup.txt` into an existing directory named `restored_project/`.
    ```bash
    bfiles unbundle project_backup.txt -o restored_project/
    ```

3.  **Force Overwrite**: Extract `data.bfiles`, overwriting any existing files in the `output_data/` directory.
    ```bash
    bfiles unbundle data.bfiles -o output_data/ -f
    ```

4.  **List Contents**: Show the files contained within `source_code.bfiles` without extracting them.
    ```bash
    bfiles unbundle source_code.bfiles --list-only
    ```
    Alternatively, using the short form:
    ```bash
    bfiles unbundle source_code.bfiles --ls
    ```

5.  **Dry Run**: Preview the extraction of `config_bundle.txt` into `configs_new/`.
    ```bash
    bfiles unbundle config_bundle.txt -o configs_new/ -n
    ```

## 3. Bundle File Format

The bfiles bundle is a plain text file, typically UTF-8 encoded. It has a human-readable, line-oriented structure.

### Overall Structure

1.  **Optional Preamble** (2 lines): Informational message for users opening the file directly.
2.  **Bundle Header**: Contains metadata about the bundle itself and the bundling configuration.
3.  **File Entries**: Zero or more entries, each representing an original file or a chunk of a file.
4.  **Bundle Footer (Summary)**: Provides summary statistics of the bundling process.

### Preamble

The first two lines are typically:
```
Attention: The following text is a 'bfiles' bundle, containing multiple delimited files with metadata.
Parse and analyze the content between '<<< BOF <<<' and '>>> EOF >>>' for each '### FILE...' entry.
```
Followed by a blank line.

### Bundle Header

*   Starts with a line: `--- START OF BFILE <bundle_name.txt> ---`
    *   `<bundle_name.txt>` is the name of the output bundle file.
*   `bfiles bundle generated on: <ISO8601_datetime>`: Timestamp of bundle creation.
*   `Config: hash=<algo>, gitignore=<yes/no>, followlinks=<yes/no>`: Key configuration parameters used during bundling.
*   `Comment: <optional_user_comment>`: An optional comment provided by the user via `--add-comment`.
*   Ends with a line: `---`
*   Followed by a blank line.

### File Entry

Each file entry consists of a metadata line, a BOF marker, the file content, and an EOF marker.

#### Metadata Line

*   **Format**: `### FILE <N>: <relative_path>[(Chunk <C>/<T>)] | <key1>=<value1>; <key2>=<value2>; ... ###`
*   Components:
    *   `### FILE <N>:`: Marker indicating a file entry, where `<N>` is the sequential number of the file *content block* being written to the bundle (errors/duplicates might get file_num=0 if they don't have content blocks).
    *   `<relative_path>`: The path of the original file, relative to the bundler's root directory. Uses POSIX-style forward slashes (`/`).
    *   `(Chunk <C>/<T>)`: Optional. If present, indicates this entry is chunk `<C>` of `<T>` total chunks for the original file.
    *   `|`: Separator.
    *   `<key>=<value>` pairs: Semicolon-separated metadata items. Common keys include:
        *   `size`: Size of the *original full file* in bytes (e.g., `1024B`).
        *   `tokens`: Estimated token count of the *original full file content* (e.g., `250`). Uses `tiktoken` with `cl100k_base` by default.
        *   `op`: Single-character operation code indicating the status of this file/chunk:
            *   `+`: Included (content follows).
            *   `0`: Empty file (content section is empty or a single newline).
            *   `d`: Duplicate of another file already included by content (content may not follow).
            *   `C`: Chunked file (this entry is one of several chunks; `op` on original metadata).
            *   `!`: Error processing this file (content may be missing or indicative of an issue).
            *   `x`: Excluded (typically not written to bundle unless for reporting, not a standard content op code).
            *   `-`: Skipped (e.g., due to `--max-files`, typically not written).
        *   `cs`: Checksum of the *original full file content*. Format: `<algo>:<hex_digest_prefix>...` (e.g., `sha256:abcdef123...`).
        *   `type`: Guessed MIME subtype (e.g., `plain`, `x-python`).
        *   `mod`: Last modified timestamp in ISO8601 format (e.g., `2023-10-27T10:30:00`).
        *   `original`: If `op=d`, this indicates the relative path of the first file included with this content.
        *   `chunk_tokens`: (For chunks only) Token count of *this specific chunk's* content.
        *   `overlap_prev`: (For chunks C2 onwards) Byte length of the content at the beginning of this chunk that is an overlap from the end of the previous chunk.
*   Ends with `###`.

#### Content Delimiters

*   `<<< BOF <<<`: Marks the beginning of the file/chunk content. Always on its own line following the Metadata Line.
*   `>>> EOF >>>`: Marks the end of the file/chunk content. Always on its own line following the content.

#### File Content

*   The raw textual content of the original file or chunk is stored between the BOF and EOF markers.
*   The bundler attempts to read files as UTF-8; if that fails, it may attempt a latin-1 fallback. Null bytes (`\x00`) are typically stripped.
*   The bundler ensures content is followed by at least one newline before the `>>> EOF >>>` marker, unless the file is empty. For empty files, the line after `<<< BOF <<<` is empty, followed by `>>> EOF >>>`.

A blank line usually follows each complete file entry (after `>>> EOF >>>`) for readability.

### Bundle Footer (Summary)

*   Starts with a line: `### BUNDLE SUMMARY ###`
*   Contains multiple lines detailing counts of included files, total size, tokens, duplicates, exclusions, errors, processing time, etc.
*   Ends with a line: `--- END OF BFILE <bundle_name.txt> ---`

## 4. Exclusion and Inclusion Logic

`bfiles bundle` uses a set of rules to determine which files and directories are included in the bundle.

### Precedence Rules

1.  **`.gitignore` Files**: If not disabled (`--no-gitignore`), rules from `.gitignore` files are processed first. Matching files/directories are always excluded, and this exclusion cannot be overridden by include patterns.
2.  **`--include` Patterns**: Files matching any `--include` pattern are marked for inclusion. These patterns override subsequent `--exclude` patterns.
3.  **`--exclude` Patterns (User-defined and Defaults)**: Files matching any of these patterns are excluded, unless they were already explicitly included by an `--include` pattern (and not excluded by `.gitignore`).
    *   User-defined `--exclude` patterns are processed.
    *   Default exclusion patterns (see below) are then applied.

### Pattern Types

*   **Glob Patterns**: Standard file globbing (e.g., `*.py`, `docs/**/*.md`). Handled by `fnmatch`.
*   **String Literals**:
    *   Absolute paths (e.g., `/path/to/exact/file.txt`) are matched exactly.
    *   Relative paths (e.g., `path/to/file.txt`, `dir/`) are resolved relative to the `--root-dir` and matched exactly. A trailing `/` indicates a directory.
*   **Regular Expressions (Regex)**: If a pattern is not identified as a glob or a path literal, it's treated as a Python regex and compiled with `re.compile()`. It's matched against the full absolute path string of files/directories.

### Default Exclusions

`bfiles` comes with a list of default exclusion patterns to avoid bundling common unwanted items. These typically include:
*   Hidden files and directories (e.g., `.*`)
*   Python bytecode files (`.pyc`, `.pyo`)
*   Version control directories (`.git/`, `.svn/`, etc.)
*   Virtual environment directories (`.venv/`, `venv/`)
*   Environment files (`.env`)
*   Common build/distribution directories (`build/`, `dist/`, `bin/`, `obj/`)
*   Node.js modules (`node_modules/`)
*   Python cache (`__pycache__/`)
*   Log files (`*.log`)
*   Temporary files (`*.tmp`, `*.swp`)
*   `bfiles`' own output files (`*bfiles*.txt`, `*.bf.txt`)

## 5. Chunking

### Chunking Overview

For very large files, `bfiles bundle` can split the file content into smaller "chunks". This is useful when the bundle is intended for systems with input size limitations, such as LLMs.

*   Enabled by specifying `--chunk-size TOKENS`.
*   Each chunk is written as a separate File Entry in the bundle.
*   The metadata line for a chunk will indicate its sequence (e.g., `(Chunk 1/3)`).
*   The `op` code in the metadata for chunks will reflect the original file's operation (e.g., `C` if the original was `included` and then chunked).
*   The `tokens` field in a chunk's metadata refers to the token count of the original full file, while `chunk_tokens` refers to the token count of that specific chunk's content.

### Tokenization

*   Token counting and splitting are performed using the `tiktoken` library.
*   By default, the `cl100k_base` encoding (commonly used by OpenAI models) is used for tokenization.
*   Files suspected of being binary (e.g., containing null bytes) are typically not tokenized or chunked.

### Overlap Handling

*   The `--chunk-overlap TOKENS` option allows specifying a number of tokens that should be repeated at the end of one chunk and the beginning of the next. This can help preserve context across chunk boundaries.
*   When overlap is used, the bundler records the byte length of this overlapping segment in the metadata of the *subsequent* chunk using the `overlap_prev=<bytes>` field. The byte length is determined by decoding the overlapping tokens and then encoding that specific string to bytes.
*   The `bfiles unbundle` command uses this `overlap_prev` metadata to intelligently reassemble chunks:
    *   It verifies that the byte sequence at the end of the previously assembled content (logical content, excluding bundle formatting newlines) matches the byte sequence at the beginning of the current chunk's raw content (up to `overlap_prev` bytes).
    *   If they match, only the non-overlapping part of the current chunk is appended.
    *   If they do not match, a warning is logged, and the unbundler typically appends the full content of the current chunk as a fallback to ensure data is not lost, though the reassembly might not be perfect at the seam.

## 6. API Usage (Python Library)

While `bfiles` is primarily a CLI tool, its core components can be used programmatically.

```python
from bfiles import BfilesConfig, bundle_files, logger
from bfiles.exclusions import ExclusionManager
from bfiles.unbundler import Unbundler
from pathlib import Path

# Example: Bundling
logger.set_log_level("info")
config = BfilesConfig(
    root_dir=Path("./my_project"),
    output_file=Path("./my_project_bundle.txt"),
    include_patterns=["*.py"],
    exclude_patterns=["tests/"],
    chunk_size=1000,
    chunk_overlap=50
)
exclusion_mgr = ExclusionManager(config)
bundle_files(config, exclusion_mgr)
print(f"Bundle created at {config.output_file}")

# Example: Unbundling
unbundler = Unbundler(
    bundle_file_path=Path("./my_project_bundle.txt"),
    output_dir_base=Path("./my_project_restored"), # Can be None for default dir
    force_overwrite=True
)
if unbundler.extract():
    print("Unbundling successful.")
else:
    print("Unbundling failed.")
```

Key classes and functions:
*   `bfiles.config.BfilesConfig`: Configuration dataclass for bundling.
*   `bfiles.exclusions.ExclusionManager`: Manages include/exclude logic for bundling.
*   `bfiles.core.bundle_files()`: Main function to perform bundling.
*   `bfiles.core.list_potential_files()`: Function to list files that would be bundled.
*   `bfiles.unbundler.Unbundler`: Class to perform unbundling. Takes `bundle_file_path`, optional `output_dir_base`, and flags.
*   `bfiles.unbundler.BundleParser`: Class to parse bundle files (used internally by `Unbundler`).
*   `bfiles.logger.logger`: Singleton logger instance, configurable via `logger.set_log_level()`.

## 7. Troubleshooting

*   **Permission Errors**: Ensure `bfiles` has read access to the root directory and its contents (for bundling) and write access to the output directory (for bundling and unbundling).
*   **`pathspec` Missing for `.gitignore`**: If `.gitignore` processing is enabled (default for `bundle` command) and `pathspec` is not installed, `bfiles bundle` will exit with an error. Install with `pip install bfiles[gitignore]` or `pip install pathspec`. Alternatively, use `--no-gitignore`.
*   **`tiktoken` Missing for Chunking**: If `--chunk-size` is used for bundling and `tiktoken` is not installed, an error will occur. Install with `pip install bfiles` (as it's a core dependency) or `pip install tiktoken`.
*   **Encoding Issues**: If files are not `utf-8` (or the specified `--encoding` for bundling), the bundler attempts a `latin-1` fallback. If that also fails, the file might be skipped or cause an error. Content with null bytes might have them stripped. Bundles are typically UTF-8.
*   **Log Levels**: Use `--log-level debug` for detailed diagnostic output for both `bundle` and `unbundle` commands if you encounter unexpected behavior.
*   **Overlap Mismatches during Unbundling**: If the unbundler logs warnings about "Overlap mismatch", it means the content of the chunks does not perfectly align as expected. This could indicate a corrupted bundle or a bug in the bundler/unbundler's overlap calculation for specific edge cases. The unbundler will attempt to append the full chunk content as a fallback.
*   **Path Traversal during Unbundling**: The unbundler attempts to sanitize paths to prevent extraction outside the target output directory. If such an attempt is detected from a malformed bundle, it will be logged and the offending file skipped.
```
