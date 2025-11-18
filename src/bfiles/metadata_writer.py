#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""TODO: Add module docstring."""

import datetime
import os
from pathlib import Path
from typing import TextIO  # For type hinting stream

import attrs
from provide.foundation import logger

# Avoid circular import, only import for type hint if needed
from bfiles.config import BfilesConfig  # Import for type hint
from bfiles.metadata import FileMetadata  # Import the attrs class


class MetadataWriter:
    """Handles formatting FileMetadata into a string line based on a template."""

    def __init__(self, config: BfilesConfig) -> None:
        """
        Initialize with the application configuration.

        Args:
            config: The BfilesConfig instance containing the template.
        """
        self.template: str = config.metadata_template
        # Store config if other settings might be needed later
        # self.config = config

    def format_metadata(  # noqa: C901
        self, file_num: int, metadata: FileMetadata, root_dir: Path
    ) -> str:
        """
        Format metadata for a file using the configured template.

        Args:
            file_num: The sequential number of the file being processed/included.
                      Can be a placeholder for non-included files.
            metadata: The FileMetadata object for the file.
            root_dir: The root directory used for the scan (for relative paths).

        Returns:
            The formatted metadata string line, ready for writing.
        """
        # --- Prepare components for the template ---

        # 1. Calculate relative path for display using the provided root_dir
        try:
            # Ensure metadata.path is absolute before making relative
            abs_meta_path = metadata.path.resolve()
            # Calculate relative path from the specified root_dir
            relative_path_display = str(abs_meta_path.relative_to(root_dir))
        except ValueError:  # pragma: no cover
            logger.warning(
                "metadata.relative_path_failed",
                path=str(metadata.path),
                root=str(root_dir),
            )
            relative_path_display = str(metadata.path)
        except Exception as e:  # pragma: no cover
            logger.error(
                "metadata.relative_path_error",
                path=str(metadata.path),
                error=str(e),
                exc_info=True,
            )
            relative_path_display = str(metadata.path)

        # 2. Create the dynamic "| key=value" metadata part
        exclude_keys_from_dict = {"path", "operation", "original"}

        metadata_items: list[str] = []
        meta_dict = attrs.asdict(
            metadata,
            filter=lambda attr, value: attr.name not in exclude_keys_from_dict and value is not None,
        )

        for key, value in meta_dict.items():
            if key == "modified" and isinstance(value, datetime.datetime):
                metadata_items.append(f"{key}={value.isoformat(timespec='seconds')}")
            elif key == "size":
                metadata_items.append(f"{key}={value}")
            elif key == "checksum":
                checksum_display = value[:12]  # Display first 12 chars
                metadata_items.append(f"{key}={checksum_display}...")
            elif key == "file_type":
                metadata_items.append(f"type={value}")
            elif key == "token_count":
                metadata_items.append(f"tokens={value}")
            elif key == "overlap_bytes_prev" and value is not None:  # Add overlap_bytes_prev if present
                metadata_items.append(f"overlap_prev={value}")

        # 3. Add operation code explicitly
        op_code = metadata.get_operation_code()
        metadata_items.append(f"op={op_code}")

        # 4. Add original path if it's a duplicate
        if metadata.operation == "duplicate" and metadata.original:
            try:
                # Show original path relative to root_dir as well
                rel_original_path = str(metadata.original.resolve().relative_to(root_dir))
                metadata_items.append(f"original={rel_original_path}")
            except ValueError:  # pragma: no cover
                metadata_items.append(f"original={metadata.original}")
            except Exception as e:  # pragma: no cover
                logger.warning(
                    "metadata.original_relative_failed",
                    original=str(metadata.original),
                    error=str(e),
                )
                metadata_items.append(f"original={metadata.original}")

        # 5. Combine metadata items into a single string, sorted alphabetically by key
        metadata_str = " | ".join(sorted(metadata_items))

        # --- Format the final line using the template ---
        try:
            # Use POSIX path separators for consistency in the output bundle
            posix_relative_path = relative_path_display.replace(os.path.sep, "/")

            # Add chunk info to the path string if available
            path_to_use_in_template = posix_relative_path
            if metadata.chunk_num is not None and metadata.total_chunks is not None:
                path_to_use_in_template += f" (Chunk {metadata.chunk_num}/{metadata.total_chunks})"

            return self.template.format(
                file_num=file_num,
                file_path=path_to_use_in_template,  # Use path with chunk info
                metadata=metadata_str,
            )
        except KeyError as e:  # pragma: no cover
            logger.error(
                "metadata.template.missing_key",
                missing=str(e),
                template=self.template,
            )
            fallback_template = "### FILE {file_num}: {file_path} | ErrorInTemplate=KeyError | {metadata} ###"
            posix_relative_path = relative_path_display.replace(os.path.sep, "/")
            return fallback_template.format(
                file_num=file_num, file_path=posix_relative_path, metadata=metadata_str
            )
        except Exception as e:  # pragma: no cover
            logger.error(
                "metadata.template.unexpected_error",
                error=str(e),
                exc_info=True,
            )
            posix_relative_path = relative_path_display.replace(os.path.sep, "/")
            return f"### FILE {file_num}: {posix_relative_path} | ErrorFormattingMetadata ###"

    # write_metadata_line method is less relevant if core.py writes directly
    def write_metadata_line(self, output_stream: TextIO, metadata_line: str) -> None:  # pragma: no cover
        """(Helper) Write a pre-formatted metadata line to the output stream."""
        try:
            output_stream.write(metadata_line + "\n")
        except Exception as e:
            logger.error(f"Failed to write metadata line directly: {e}")


# 🐝📁🔚
