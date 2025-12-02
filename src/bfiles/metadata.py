#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#


import datetime
from pathlib import Path

import attrs
from provide.foundation import logger
import tiktoken

from bfiles.config import BfilesConfig
from bfiles.utils import compute_file_hash, get_file_subtype

# Define valid operation choices for validation
_VALID_OPERATIONS = frozenset({"included", "skipped", "empty", "duplicate", "excluded", "error"})


@attrs.define(kw_only=True, slots=True, frozen=False)  # Allow mutation for simplicity here
class FileMetadata:
    """
    Represents metadata for a single file using attrs.

    Attributes:
        path: Absolute path to the file.
        size: File size in bytes.
        modified: Last modification time.
        file_type: Guessed MIME subtype (e.g., 'x-python', 'plain').
        checksum: File content hash (e.g., SHA256 hex digest).
        operation: Status of the file in the bundling process.
        original: Path to the original file if this one is a duplicate.
    """

    path: Path = attrs.field(validator=attrs.validators.instance_of(Path))
    size: int = attrs.field(validator=attrs.validators.instance_of(int))
    modified: datetime.datetime = attrs.field(
        validator=attrs.validators.instance_of(datetime.datetime)
    )
    file_type: str | None = attrs.field(default=None)
    checksum: str | None = attrs.field(default=None)
    operation: str = attrs.field(
        default="included", validator=attrs.validators.in_(_VALID_OPERATIONS)
    )
    original: Path | None = attrs.field(
        default=None, validator=attrs.validators.optional(attrs.validators.instance_of(Path))
    )
    token_count: int | None = attrs.field(default=None, kw_only=True)
    chunk_num: int | None = attrs.field(default=None, kw_only=True)
    total_chunks: int | None = attrs.field(default=None, kw_only=True)
    overlap_bytes_prev: int | None = attrs.field(
        default=None, kw_only=True
    )  # For chunks after the first

    @classmethod
    def from_path(cls, file_path: Path, config: BfilesConfig) -> "FileMetadata":
        """
        Factory method to create FileMetadata from a file path.

        Args:
            file_path: Path to the file.
            config: The BfilesConfig instance.

        Returns:
            A FileMetadata instance.

        Raises:
            ValueError: If the file is not found or inaccessible.
        """
        try:
            # Resolve the path first. If file_path is a symlink, resolved_path points to the target.
            # If file_path is a regular file, resolved_path is file_path.
            resolved_path = file_path.resolve()

            stat_result = resolved_path.stat()  # Stat the actual file/target
            file_size = stat_result.st_size
            modified = datetime.datetime.fromtimestamp(stat_result.st_mtime)

            if file_size > 0:
                # Compute type and hash from the resolved path (content source)
                file_type = get_file_subtype(resolved_path)
                checksum = compute_file_hash(resolved_path, algorithm=config.hash_algorithm)
            else:
                file_type = None
                checksum = None

            # Determine initial operation based on size
            operation = "empty" if file_size == 0 else "included"

            # Token counting
            token_count: int | None = None
            if operation == "included":  # Only count tokens for non-empty, included files initially
                try:
                    # Heuristic: skip token counting for files with null bytes (likely binary)
                    # Read from resolved_path
                    with resolved_path.open("rb") as fb:
                        chunk = fb.read(1024)  # Read first 1KB
                        if b"\x00" in chunk:
                            logger.debug(
                                f"Null byte found in {resolved_path}, "
                                "skipping token count (likely binary)."
                            )
                            token_count = None
                        else:
                            # Proceed with text reading for tokenization
                            file_content = resolved_path.read_text(
                                encoding=config.encoding, errors="replace"
                            )
                            try:
                                enc = tiktoken.get_encoding(
                                    "cl100k_base"
                                )  # Or config.tokenizer_encoding
                                token_count = len(enc.encode(file_content))
                            except UnicodeDecodeError:  # pragma: no cover
                                # Should be caught by errors='replace'
                                logger.warning(
                                    f"UnicodeDecodeError for {resolved_path} "
                                    "during tokenization attempt. Token count N/A."
                                )
                                token_count = None
                            except Exception as e_tok:  # pragma: no cover
                                # Catch InvalidEncodingName or other errors
                                logger.warning(f"Error tokenizing {resolved_path}: {e_tok}")
                                token_count = None
                except OSError as e_os:  # pragma: no cover
                    logger.warning(
                        f"OS error reading {resolved_path} for token counting: "
                        f"{e_os}. Token count N/A."
                    )
                    token_count = None
                except Exception as e_gen:  # pragma: no cover
                    logger.error(
                        f"Unexpected error during token counting prep for {resolved_path}: {e_gen}",
                        exc_info=True,
                    )
                    token_count = None

            return cls(
                path=resolved_path,  # Store the resolved path
                size=file_size,
                modified=modified,
                file_type=file_type,
                checksum=checksum,
                operation=operation,
                token_count=token_count,
            )
        except FileNotFoundError as e:  # pragma: no cover
            logger.error(f"File not found: {file_path} - {e}")
            raise ValueError(f"File not found: {file_path}") from e
        except OSError as e:  # pragma: no cover
            logger.error(f"OS error accessing {file_path}: {e}")
            raise ValueError(f"Cannot access file {file_path}: {e}") from e

    def get_operation_code(self) -> str:
        """
        Get the single-character code corresponding to the operation name.

        Returns:
            Single-character operation code ('+', 'x', 'd', '0', '-').
        """
        operation_codes = {
            "included": "+",
            "skipped": "-",
            "empty": "0",
            "duplicate": "d",
            "excluded": "x",
            "error": "!",
        }
        return operation_codes.get(self.operation, "?")


@attrs.define(kw_only=True, slots=True)
class BundleSummary:
    """Holds summary statistics about the bundling process."""

    total_files_discovered: int = 0
    total_files_processed: int = 0
    files_considered_for_bundle: int = 0
    files_added_to_bundle: int = 0
    total_content_bytes_in_bundle: int = 0
    duplicate_files_skipped: int = 0
    empty_files_skipped: int = 0
    symlinks_found: int = 0
    symlinks_followed: int = 0
    symlinks_ignored: int = 0
    symlinks_skipped_as_duplicate_target: int = 0
    excluded_by_config_pattern: int = 0
    excluded_by_gitignore: int = 0
    excluded_by_default_pattern: int = 0
    included_by_config_pattern: int = 0
    max_files_limit_hit: bool = False
    max_files_limit_value: int | None = None  # Allow None
    files_skipped_due_to_max_files: int = 0
    max_size_limit_hit: bool = False
    max_size_limit_value: int | None = None  # Allow None
    files_skipped_due_to_max_size: int = 0
    encoding_fallbacks_used: int = 0
    content_read_errors: int = 0
    stat_errors: int = 0
    other_processing_errors: int = 0
    output_file_path: Path | None = None
    bundle_header_size_bytes: int = 0
    bundle_footer_size_bytes: int = 0

    @property
    def total_excluded_count(self) -> int:
        return (
            self.excluded_by_config_pattern
            + self.excluded_by_gitignore
            + self.excluded_by_default_pattern
        )

    @property
    def total_bundle_size_bytes(self) -> int:
        return (
            self.bundle_header_size_bytes
            + self.total_content_bytes_in_bundle
            + self.bundle_footer_size_bytes
        )


# 🐝📁🔚
