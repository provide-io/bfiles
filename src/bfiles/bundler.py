#
# SPDX-FileCopyrightText: Copyright (c) provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Bundle creation and file aggregation."""

import datetime
import io
from pathlib import Path
import time
from typing import TYPE_CHECKING, TextIO

import attrs
from provide.foundation import logger
from provide.foundation.file import atomic_write
from provide.foundation.resilience import retry
import tiktoken

from bfiles.chunking import ChunkData, FileChunker
from bfiles.config import BfilesConfig
from bfiles.errors import BundleError
from bfiles.exclusions import ExclusionManager
from bfiles.metadata import FileMetadata
from bfiles.metadata_writer import MetadataWriter
from bfiles.output import generate_summary_text
from bfiles.reader import FileReader
from bfiles.utils import has_dangerous_chars, sanitize_dangerous_chars

if TYPE_CHECKING:
    from bfiles.progress import ProgressReporter


class Bundler:
    """Orchestrates file bundling with chunking support."""

    def __init__(
        self,
        config: BfilesConfig,
        file_reader: FileReader,
        file_chunker: FileChunker,
        metadata_writer: MetadataWriter,
        exclusion_manager: ExclusionManager,
        progress_reporter: "ProgressReporter | None" = None,
    ) -> None:
        self.config = config
        self.file_reader = file_reader
        self.file_chunker = file_chunker
        self.metadata_writer = metadata_writer
        self.exclusion_manager = exclusion_manager
        self.progress_reporter = progress_reporter

    @retry(max_attempts=2)
    def bundle(
        self, sorted_candidate_paths: list[Path]
    ) -> tuple[int, int, int, int, int, int, int, int, int, int, int | None]:
        """Create bundle file from candidate paths.

        Args:
            sorted_candidate_paths: Sorted list of file paths to bundle

        Returns:
            Tuple of (included_files, total_size, duplicates, empty_files,
                     io_errors, encoding_errors, skipped_max_files,
                     unsafe_excluded, unsafe_sanitized,
                     total_content_tokens, overall_bundle_tokens)

        Raises:
            BundleError: If bundle creation fails
        """
        if self.config.output_file is None:
            raise BundleError("Output file path cannot be None for bundling")

        logger.info(
            "bundle.create.start",
            output_file=str(self.config.output_file),
            candidate_count=len(sorted_candidate_paths),
        )

        start_time = time.monotonic()
        buffer = io.StringIO()

        self._write_header(buffer)

        stats = self._process_files(buffer, sorted_candidate_paths)

        footer = self._create_footer(stats, start_time)
        buffer.write(footer)

        self._write_to_disk(buffer.getvalue())

        elapsed = time.monotonic() - start_time
        logger.info("bundle.create.complete", duration_seconds=elapsed)

        return stats

    def _process_files(  # noqa: C901
        self, buffer: io.StringIO, file_paths: list[Path]
    ) -> tuple[int, int, int, int, int, int, int, int, int, int, int | None]:
        """Process all files and write to buffer.

        Returns:
            Tuple of statistics
        """
        included_count = 0
        total_size = 0
        duplicates = 0
        empty_files = 0
        io_errors = 0
        encoding_errors = 0
        skipped_max_files = 0
        unsafe_excluded = 0
        unsafe_sanitized = 0

        file_hash_map: dict[str, FileMetadata] = {}
        all_metadata: list[FileMetadata] = []

        for idx, file_path in enumerate(file_paths, start=1):
            logger.debug("bundle.process.file", path=str(file_path), index=idx)

            cached_exclusion = self.exclusion_manager.exclusion_cache.get(file_path)
            if cached_exclusion and cached_exclusion not in ("error", "skipped"):
                if self.config.show_excluded:
                    meta = self._create_exclusion_metadata(file_path, "excluded")
                    all_metadata.append(meta)
                if self.progress_reporter:
                    self.progress_reporter.file_progress(file_path, "excluded", root_dir=self.config.root_dir)
                continue

            if self.config.max_files and included_count >= self.config.max_files:
                if skipped_max_files == 0:
                    logger.info("bundle.limit.reached", max_files=self.config.max_files)
                skipped_max_files += 1
                self.exclusion_manager.add_excluded_item(file_path, "skipped")
                meta = self._create_exclusion_metadata(file_path, "skipped")
                all_metadata.append(meta)
                if self.progress_reporter:
                    self.progress_reporter.file_progress(
                        file_path,
                        "skipped",
                        root_dir=self.config.root_dir,
                        details="max_files limit",
                    )
                continue

            try:
                metadata = FileMetadata.from_path(file_path, self.config)
            except ValueError:
                io_errors += 1
                self.exclusion_manager.add_excluded_item(file_path, "error")
                meta = self._create_exclusion_metadata(file_path, "error")
                all_metadata.append(meta)
                if self.progress_reporter:
                    self.progress_reporter.file_progress(file_path, "error", root_dir=self.config.root_dir)
                continue

            all_metadata.append(metadata)

            if metadata.operation == "error":
                io_errors += 1
                formatted = self.metadata_writer.format_metadata(0, metadata, self.config.root_dir)
                buffer.write(formatted + "\n\n")
                if self.progress_reporter:
                    self.progress_reporter.file_progress(file_path, "error", root_dir=self.config.root_dir)
                continue

            if metadata.operation == "empty":
                empty_files += 1
                self._write_empty_file(buffer, metadata)
                if self.progress_reporter:
                    self.progress_reporter.file_progress(file_path, "empty", root_dir=self.config.root_dir)
                continue

            if metadata.checksum and metadata.checksum in file_hash_map:
                original = file_hash_map[metadata.checksum]
                metadata = attrs.evolve(metadata, operation="duplicate", original=original.path)
                all_metadata[-1] = metadata
                duplicates += 1
                formatted = self.metadata_writer.format_metadata(0, metadata, self.config.root_dir)
                buffer.write(formatted + "\n\n")
                if self.progress_reporter:
                    self.progress_reporter.file_progress(file_path, "duplicate", root_dir=self.config.root_dir)
                continue

            if metadata.operation == "included":
                if metadata.checksum:
                    file_hash_map[metadata.checksum] = metadata
                included_count += 1
                if metadata.size > 0:
                    total_size += metadata.size

                content, enc_err, enc_fail = self.file_reader.read(file_path)

                if enc_fail:
                    encoding_errors += 1
                    metadata = attrs.evolve(metadata, operation="error", token_count=None)
                    all_metadata[-1] = metadata

                # Terminal safety check: detect dangerous control characters
                if content:
                    is_dangerous, dangerous_positions = has_dangerous_chars(content)

                    if is_dangerous:
                        # Three modes: default (exclude), allow_unsafe (warn + include),
                        # sanitize_unsafe (sanitize + include)
                        if not self.config.allow_unsafe and not self.config.sanitize_unsafe:
                            # Default mode: Exclude file with warning
                            logger.warning(
                                "file.unsafe.excluded",
                                path=str(file_path),
                                dangerous_chars=len(dangerous_positions),
                                positions=dangerous_positions[:3],  # Show first 3 positions
                            )
                            unsafe_excluded += 1
                            included_count -= 1  # Decrement since we already counted it
                            if metadata.size > 0:
                                total_size -= metadata.size
                            metadata = attrs.evolve(metadata, operation="excluded")
                            all_metadata[-1] = metadata
                            self.exclusion_manager.add_excluded_item(file_path, "unsafe")
                            continue

                        elif self.config.allow_unsafe:
                            # Allow mode: Include with warning
                            logger.warning(
                                "file.unsafe.allowed",
                                path=str(file_path),
                                dangerous_chars=len(dangerous_positions),
                                positions=dangerous_positions[:3],
                            )

                        elif self.config.sanitize_unsafe:
                            # Sanitize mode: Replace dangerous chars with visible representations
                            logger.info(
                                "file.unsafe.sanitized",
                                path=str(file_path),
                                dangerous_chars=len(dangerous_positions),
                            )
                            content = sanitize_dangerous_chars(content)
                            unsafe_sanitized += 1

                should_chunk = self.file_chunker.should_chunk(
                    content, metadata.token_count, enc_err or enc_fail
                )

                if should_chunk and content:
                    self._write_chunked_file(buffer, content, metadata, file_path, included_count)
                else:
                    self._write_single_file(buffer, content, metadata, included_count)

                # Report progress for successfully included file
                if self.progress_reporter:
                    size_str = f"{metadata.size} bytes" if metadata.size else ""
                    self.progress_reporter.file_progress(
                        file_path, "included", root_dir=self.config.root_dir, details=size_str
                    )

        total_content_tokens = sum(
            m.token_count for m in all_metadata if m.token_count and m.operation == "included"
        )

        overall_tokens = self._estimate_overall_tokens(buffer.getvalue())

        return (
            included_count,
            total_size,
            duplicates,
            empty_files,
            io_errors,
            encoding_errors,
            skipped_max_files,
            unsafe_excluded,
            unsafe_sanitized,
            total_content_tokens,
            overall_tokens,
        )

    def _write_header(self, stream: TextIO) -> None:
        """Write bundle header."""
        stream.write(
            "Attention: The following text is a 'bfiles' bundle, "
            "containing multiple delimited files with metadata.\n"
        )
        stream.write(
            "Parse and analyze the content between '<<< BOF <<<' and '>>> EOF >>>' "
            "for each '### FILE...' entry.\n\n"
        )

        bfile_name = self.config.output_file.name if self.config.output_file else "unknown.txt"
        stream.write(f"--- START OF BFILE {bfile_name} ---\n")
        stream.write(f"bfiles bundle generated on: {datetime.datetime.now().isoformat()}\n")

        gitignore = "yes" if self.config.use_gitignore else "no"
        followlinks = "yes" if self.config.follow_symlinks else "no"
        stream.write(
            f"Config: hash={self.config.hash_algorithm}, gitignore={gitignore}, followlinks={followlinks}\n"
        )

        if self.config.header_comment:
            stream.write(f"Comment: {self.config.header_comment}\n")
        stream.write("---\n\n")

        logger.debug("bundle.header.written")

    def _create_footer(
        self,
        stats: tuple[int, int, int, int, int, int, int, int, int, int, int | None],
        start_time: float,
    ) -> str:
        """Create bundle footer with summary."""
        (
            included,
            total_size,
            duplicates,
            empty,
            io_errors,
            enc_errors,
            _skipped,
            unsafe_excluded,
            unsafe_sanitized,
            content_tokens,
            overall_tokens,
        ) = stats

        excluded_files = self.exclusion_manager.get_config_excluded_files_count()
        excluded_dirs = self.exclusion_manager.get_config_excluded_dirs_count()
        gitignore_excluded = self.exclusion_manager.get_gitignore_excluded_count()
        total_errors = io_errors + self.exclusion_manager.get_error_count()
        skipped_by_limit = self.exclusion_manager.get_skipped_by_limit_count()

        summary = generate_summary_text(
            config=self.config,
            included_files=included,
            total_size=total_size,
            duplicates=duplicates,
            excluded_by_config_files=excluded_files,
            excluded_by_config_dirs=excluded_dirs,
            empty_files=empty,
            io_errors=total_errors,
            encoding_errors=enc_errors,
            skipped_by_limit=skipped_by_limit,
            excluded_by_gitignore=gitignore_excluded,
            unsafe_excluded=unsafe_excluded,
            unsafe_sanitized=unsafe_sanitized,
            total_token_count=content_tokens,
            overall_bundle_token_count=overall_tokens,
            start_time=start_time,
        )

        bfile_name = self.config.output_file.name if self.config.output_file else "unknown.txt"
        return summary + f"\n\n--- END OF BFILE {bfile_name} ---\n"

    def _write_empty_file(self, buffer: io.StringIO, metadata: FileMetadata) -> None:
        """Write empty file entry."""
        formatted = self.metadata_writer.format_metadata(0, metadata, self.config.root_dir)
        buffer.write(formatted + "\n")
        buffer.write("<<< BOF <<<\n\n>>> EOF >>>\n\n")

    def _write_single_file(
        self,
        buffer: io.StringIO,
        content: str | None,
        metadata: FileMetadata,
        file_num: int,
    ) -> None:
        """Write single (non-chunked) file entry."""
        formatted = self.metadata_writer.format_metadata(file_num, metadata, self.config.root_dir)
        buffer.write(formatted + "\n")
        buffer.write("<<< BOF <<<\n")

        if content:
            buffer.write(content)
            if not content.endswith("\n") and metadata.operation != "empty":
                buffer.write("\n")

        buffer.write(">>> EOF >>>\n\n")

    def _write_chunked_file(
        self,
        buffer: io.StringIO,
        content: str,
        metadata: FileMetadata,
        file_path: Path,
        file_num: int,
    ) -> None:
        """Write chunked file entries."""
        chunks = self.file_chunker.chunk(content, file_path)

        encoder = tiktoken.get_encoding("cl100k_base")

        for chunk_data in chunks:
            chunk_metadata = self._create_chunk_metadata(metadata, chunk_data, encoder)

            formatted = self.metadata_writer.format_metadata(file_num, chunk_metadata, self.config.root_dir)
            buffer.write(formatted + "\n")
            buffer.write("<<< BOF <<<\n")

            try:
                chunk_content = encoder.decode(chunk_data.tokens)
                buffer.write(chunk_content)
                if not chunk_content.endswith("\n"):
                    buffer.write("\n")
            except Exception as e:
                logger.error(
                    "bundle.chunk.decode_error",
                    path=str(file_path),
                    chunk_num=chunk_data.chunk_num,
                    error=str(e),
                )

            buffer.write(">>> EOF >>>\n\n")

    def _create_chunk_metadata(
        self,
        original_metadata: FileMetadata,
        chunk_data: ChunkData,
        encoder: tiktoken.Encoding,
    ) -> FileMetadata:
        """Create metadata for a specific chunk."""
        return attrs.evolve(
            original_metadata,
            chunk_num=chunk_data.chunk_num,
            total_chunks=chunk_data.total_chunks,
            token_count=chunk_data.token_count,
            overlap_bytes_prev=chunk_data.overlap_bytes_prev,
        )

    def _create_exclusion_metadata(self, file_path: Path, operation: str) -> FileMetadata:
        """Create metadata for excluded/error files."""
        try:
            stat = file_path.lstat()
            mod_time = datetime.datetime.fromtimestamp(stat.st_mtime, tz=datetime.UTC)
            size = stat.st_size
        except OSError:
            mod_time = datetime.datetime.fromtimestamp(0, tz=datetime.UTC)
            size = -1

        return FileMetadata(
            path=file_path,
            size=size,
            modified=mod_time,
            operation=operation,
            token_count=None,
        )

    def _estimate_overall_tokens(self, content: str) -> int | None:
        """Estimate total bundle token count."""
        try:
            encoder = tiktoken.get_encoding("cl100k_base")
            return len(encoder.encode(content))
        except Exception as e:
            logger.warning(
                "bundle.tokens.estimation_failed",
                error=str(e),
            )
            return None

    def _write_to_disk(self, content: str) -> None:
        """Write bundle content to disk using atomic write."""
        if not self.config.output_file:
            raise BundleError("Output file path is None")

        try:
            data = content.encode(self.config.encoding, errors="replace")
            atomic_write(self.config.output_file, data)
            logger.info(
                "bundle.write.success",
                path=str(self.config.output_file),
                size_bytes=len(data),
            )
        except Exception as e:
            logger.error(
                "bundle.write.failure",
                path=str(self.config.output_file),
                error=str(e),
            )
            raise BundleError(f"Failed to write bundle: {e}") from e


# 🐝📁🔚
