#
# SPDX-FileCopyrightText: Copyright (c) provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""File extraction from parsed bundles."""

from pathlib import Path
from typing import TYPE_CHECKING

from provide.foundation import logger
from provide.foundation.archive.security import is_safe_path
from provide.foundation.file import atomic_write

from bfiles.errors import ChunkReassemblyError, UnbundleError
from bfiles.parser import ParsedFileEntry

if TYPE_CHECKING:
    from bfiles.progress import ProgressReporter


class FileExtractor:
    """Extracts files from parsed bundle entries."""

    def __init__(
        self,
        output_root: Path,
        force_overwrite: bool = False,
        dry_run: bool = False,
        progress_reporter: "ProgressReporter | None" = None,
    ) -> None:
        self.output_root = output_root
        self.force_overwrite = force_overwrite
        self.dry_run = dry_run
        self.progress_reporter = progress_reporter

    def validate_and_resolve_path(self, relative_path_str: str) -> Path | None:
        """Validate and resolve a path for safe extraction.

        Uses Foundation's is_safe_path() for comprehensive security checks.

        Args:
            relative_path_str: Relative path string from bundle

        Returns:
            Absolute target path or None if unsafe
        """
        # Use Foundation's security validation
        if not is_safe_path(self.output_root, relative_path_str):
            logger.error(
                "extract.path.unsafe",
                path=relative_path_str,
                root=str(self.output_root),
            )
            return None

        # Path is safe, resolve it
        try:
            target_path = (self.output_root / relative_path_str).resolve()
        except Exception as e:
            logger.error(
                "extract.path.resolution_error",
                path=relative_path_str,
                error=str(e),
            )
            return None
        else:
            return target_path

    def reassemble_chunks(self, entries: list[ParsedFileEntry], rel_path: str) -> str:
        """Reassemble chunked file content with overlap handling.

        Args:
            entries: List of chunk entries (sorted by chunk_num)
            rel_path: Relative path for logging

        Returns:
            Reassembled content

        Raises:
            ChunkReassemblyError: If reassembly fails
        """
        if not all(e.is_chunk for e in entries):
            raise ChunkReassemblyError(f"Mixed chunked/non-chunked entries for {rel_path}")

        expected_total = entries[0].total_chunks
        if expected_total and len(entries) != expected_total:
            raise ChunkReassemblyError(
                f"Missing chunks for {rel_path}: expected {expected_total}, got {len(entries)}"
            )

        logger.info(
            "extract.reassemble.start",
            path=rel_path,
            chunk_count=len(entries),
        )

        reassembled_parts: list[str] = []
        current_assembled_bytes = b""

        for i, chunk_entry in enumerate(entries):
            chunk_bytes = chunk_entry.content.encode("utf-8")

            if i == 0:
                reassembled_parts.append(chunk_entry.content)
                current_assembled_bytes = chunk_bytes
            else:
                overlap_bytes_prev = self._get_overlap_bytes(chunk_entry)

                if overlap_bytes_prev > 0:
                    non_overlapping = self._handle_chunk_overlap(
                        current_assembled_bytes,
                        chunk_bytes,
                        overlap_bytes_prev,
                        chunk_entry.chunk_num or i + 1,
                        rel_path,
                    )
                    if non_overlapping:
                        reassembled_parts.append(non_overlapping)
                        current_assembled_bytes += non_overlapping.encode("utf-8")
                    else:
                        reassembled_parts.append(chunk_entry.content)
                        current_assembled_bytes += chunk_bytes
                else:
                    reassembled_parts.append(chunk_entry.content)
                    current_assembled_bytes += chunk_bytes

        final_content = "".join(reassembled_parts)
        logger.info(
            "extract.reassemble.complete",
            path=rel_path,
            size_bytes=len(final_content.encode("utf-8")),
        )

        return final_content

    def _get_overlap_bytes(self, chunk_entry: ParsedFileEntry) -> int:
        """Extract overlap bytes value from chunk metadata."""
        overlap_str = chunk_entry.metadata_dict.get("overlap_prev")
        if overlap_str and overlap_str.isdigit():
            return int(overlap_str)
        return 0

    def _handle_chunk_overlap(
        self,
        assembled_bytes: bytes,
        chunk_bytes: bytes,
        overlap_bytes: int,
        chunk_num: int,
        rel_path: str,
    ) -> str | None:
        """Handle chunk overlap validation and extraction.

        Returns:
            Non-overlapping portion as string, or None if overlap fails
        """
        if len(assembled_bytes) < overlap_bytes or len(chunk_bytes) < overlap_bytes:
            logger.warning(
                "extract.overlap.size_mismatch",
                path=rel_path,
                chunk_num=chunk_num,
                overlap_bytes=overlap_bytes,
            )
            return None

        assembled_str = assembled_bytes.decode("utf-8", "replace")
        logical_content = assembled_str[:-1] if assembled_str.endswith("\n") else assembled_str

        logical_bytes = logical_content.encode("utf-8", "replace")

        if len(logical_bytes) < overlap_bytes:
            logger.warning(
                "extract.overlap.logical_size_mismatch",
                path=rel_path,
                chunk_num=chunk_num,
            )
            return None

        prev_overlap = logical_bytes[-overlap_bytes:]
        curr_overlap = chunk_bytes[:overlap_bytes]

        if prev_overlap == curr_overlap:
            non_overlapping_bytes = chunk_bytes[overlap_bytes:]
            logger.debug(
                "extract.overlap.verified",
                path=rel_path,
                chunk_num=chunk_num,
                overlap_bytes=overlap_bytes,
            )
            return non_overlapping_bytes.decode("utf-8", errors="replace")
        else:
            logger.warning(
                "extract.overlap.content_mismatch",
                path=rel_path,
                chunk_num=chunk_num,
            )
            return None

    def extract_file(
        self,
        target_path: Path,
        content: str,
        is_empty: bool = False,
    ) -> bool:
        """Extract a single file to disk.

        Args:
            target_path: Absolute path to write file
            content: File content
            is_empty: Whether file should be treated as empty

        Returns:
            True if successful, False otherwise
        """
        if is_empty and content == "\n":
            content = ""

        if self.dry_run:
            action = "Would create"
            if target_path.exists():
                action = "Would overwrite" if self.force_overwrite else "Would skip (exists)"
            logger.info(
                "extract.dry_run",
                action=action,
                path=str(target_path),
                size_bytes=len(content),
            )
            return True

        if target_path.exists() and not self.force_overwrite:
            logger.info(
                "extract.skip.exists",
                path=str(target_path),
            )
            return False

        try:
            target_path.parent.mkdir(parents=True, exist_ok=True)

            data = content.encode("utf-8")
            atomic_write(target_path, data)

            logger.info(
                "extract.file.success",
                path=str(target_path),
                size_bytes=len(data),
            )
            if self.progress_reporter:
                self.progress_reporter.file_progress(target_path, "extracted", root_dir=self.output_root)
        except OSError as e:
            logger.error(
                "extract.file.os_error",
                path=str(target_path),
                error=str(e),
            )
            return False
        except Exception as e:
            logger.error(
                "extract.file.unexpected_error",
                path=str(target_path),
                error=str(e),
            )
            return False
        else:
            return True

    def determine_content(self, entries: list[ParsedFileEntry], rel_path: str) -> str:
        """Determine final content from entries (handles chunks or single file).

        Args:
            entries: List of file entries (may be chunks or single)
            rel_path: Relative path for logging

        Returns:
            Final file content

        Raises:
            UnbundleError: If content determination fails
        """
        if not entries:
            raise UnbundleError(f"No entries provided for {rel_path}")

        if entries[0].is_chunk:
            return self.reassemble_chunks(entries, rel_path)
        else:
            if len(entries) > 1:
                logger.warning(
                    "extract.multiple_non_chunked",
                    path=rel_path,
                    count=len(entries),
                )
            return entries[0].content

    def is_empty_file(self, entry: ParsedFileEntry) -> bool:
        """Check if file entry represents an empty file.

        Args:
            entry: File entry to check

        Returns:
            True if file is empty
        """
        return entry.metadata_dict.get("op") == "0" or entry.metadata_dict.get("size", "").upper() == "0B"


# 🐝📁🔚
