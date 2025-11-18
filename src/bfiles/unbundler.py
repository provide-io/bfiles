#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Unbundle orchestration for extracting files from bundles."""

from pathlib import Path

from provide.foundation import logger
from provide.foundation.console import pout
from provide.foundation.context import CLIContext

from bfiles.extractor import FileExtractor
from bfiles.parser import BundleParser, ParsedFileEntry
from bfiles.progress import ProgressReporter


class Unbundler:
    """Orchestrates extraction of files from a parsed bfiles bundle."""

    def __init__(
        self,
        bundle_file_path: Path,
        output_dir_base: Path | None,
        force_overwrite: bool = False,
        list_only: bool = False,
        dry_run: bool = False,
        show_progress: bool = False,
        cli_context: CLIContext | None = None,
    ) -> None:
        self.bundle_file_path = bundle_file_path
        self.parser = BundleParser(bundle_file_path)
        self.force_overwrite = force_overwrite
        self.list_only = list_only
        self.dry_run = dry_run
        self.show_progress = show_progress
        self.cli_context = cli_context

        self._target_output_root: Path | None = None
        self._output_dir_base = output_dir_base if output_dir_base else Path.cwd()
        self.progress = ProgressReporter(enabled=show_progress, cli_context=cli_context)

    def _prepare_output_directory(self) -> bool:
        """Determine and prepare the final output directory.

        Returns:
            True if successful, False otherwise
        """
        logger.info("unbundle.prepare_output.start")

        bundle_name_stem = self._get_bundle_name_stem()

        if self._output_dir_base == Path.cwd():
            default_dir_name = bundle_name_stem + "_unbundled"
            potential_output_dir = self.bundle_file_path.parent / default_dir_name
            self._target_output_root = potential_output_dir.resolve()
            logger.info(
                "unbundle.output.default",
                path=str(self._target_output_root),
            )
        else:
            self._target_output_root = self._output_dir_base.resolve()
            logger.info(
                "unbundle.output.specified",
                path=str(self._target_output_root),
            )

        if self.list_only or self.dry_run:
            logger.info(
                "unbundle.output.info_only",
                path=str(self._target_output_root),
            )
            return True

        try:
            if not self._target_output_root.exists():
                logger.info(
                    "unbundle.output.creating",
                    path=str(self._target_output_root),
                )
                self._target_output_root.mkdir(parents=True, exist_ok=True)
            elif not self._target_output_root.is_dir():
                logger.error(
                    "unbundle.output.not_directory",
                    path=str(self._target_output_root),
                )
                return False
        except OSError as e:
            logger.error(
                "unbundle.output.creation_failed",
                path=str(self._target_output_root),
                error=str(e),
            )
            return False
        else:
            return True

    def _get_bundle_name_stem(self) -> str:
        """Get bundle name stem for default output directory."""
        if self.parser.header and self.parser.header.original_bundle_name:
            header_name = self.parser.header.original_bundle_name
            for ext in [".bfiles", ".txt"]:
                if header_name.endswith(ext):
                    return header_name[: -len(ext)]
            return header_name

        for ext in [".bfiles", ".txt"]:
            if self.bundle_file_path.name.endswith(ext):
                return self.bundle_file_path.name[: -len(ext)]

        return self.bundle_file_path.stem

    def extract(self) -> bool:
        """Parse bundle and extract files.

        Returns:
            True on success, False otherwise
        """
        logger.info("unbundle.start", bundle=str(self.bundle_file_path))

        if not self.parser.parse():
            logger.error("unbundle.parse_failed", bundle=str(self.bundle_file_path))
            return False

        if not self._prepare_output_directory():
            return False

        if not self._target_output_root:
            logger.error("unbundle.no_output_root")
            return False

        grouped_files = self._group_file_entries()

        if self.list_only:
            return self._list_contents(grouped_files)

        extractor = FileExtractor(
            self._target_output_root,
            self.force_overwrite,
            self.dry_run,
            progress_reporter=self.progress,
        )

        self.progress.operation_start("Extracting files")
        result = self._extract_files(extractor, grouped_files)
        self.progress.operation_end("File extraction", len(grouped_files))
        return result

    def _group_file_entries(self) -> dict[str, list[ParsedFileEntry]]:
        """Group file entries by path, handling chunks."""
        grouped: dict[str, list[ParsedFileEntry]] = {}
        for entry in self.parser.file_entries:
            grouped.setdefault(entry.relative_path, []).append(entry)
        return grouped

    def _list_contents(self, grouped_files: dict[str, list[ParsedFileEntry]]) -> bool:
        """List bundle contents without extraction."""
        # JSON output mode
        if self.cli_context and self.cli_context.json_output:
            files_list = []
            for rel_path, entries in grouped_files.items():
                entries.sort(
                    key=lambda e: (
                        e.is_chunk,
                        e.chunk_num if e.chunk_num is not None else -1,
                    )
                )
                entry_data: dict[str, str | int | bool | None] = {
                    "path": rel_path,
                    "operation": entries[0].metadata_dict.get("op", "?"),
                    "size": entries[0].metadata_dict.get("size"),
                    "is_chunked": entries[0].is_chunk,
                }
                if entries[0].is_chunk and entries[0].total_chunks:
                    entry_data["chunks"] = entries[0].total_chunks
                files_list.append(entry_data)

            output_data = {
                "bundle_file": str(self.bundle_file_path),
                "file_count": len(grouped_files),
                "files": files_list,
            }
            if self.parser.header:
                output_data["header"] = {
                    "original_name": self.parser.header.original_bundle_name,
                    "generated": self.parser.header.generation_datetime,
                    "comment": self.parser.header.comment,
                }
            pout(output_data, json_key="unbundle_list", ctx=self.cli_context)
        else:
            # Text output mode
            pout(f"Contents of bundle: {self.bundle_file_path}")

            if self.parser.header:
                pout(f"  Original Bundle Name: {self.parser.header.original_bundle_name or 'N/A'}")
                pout(f"  Generated: {self.parser.header.generation_datetime or 'N/A'}")
                if self.parser.header.comment:
                    pout(f"  Comment: {self.parser.header.comment}")

            for rel_path, entries in grouped_files.items():
                entries.sort(
                    key=lambda e: (
                        e.is_chunk,
                        e.chunk_num if e.chunk_num is not None else -1,
                    )
                )

                chunk_info = ""
                if entries[0].is_chunk and entries[0].total_chunks:
                    chunk_info = f" ({entries[0].total_chunks} chunks)"

                op_code = entries[0].metadata_dict.get("op", "?")
                size = entries[0].metadata_dict.get("size", "N/A")
                pout(f"  [{op_code}] {rel_path}{chunk_info} (Size: {size})")

            pout(f"\nListed {len(grouped_files)} unique file paths from bundle.")

        logger.info("unbundle.list.complete", file_count=len(grouped_files))
        return True

    def _extract_files(
        self, extractor: FileExtractor, grouped_files: dict[str, list[ParsedFileEntry]]
    ) -> bool:
        """Extract all files using the extractor."""
        file_extraction_counter = 0

        for rel_path_str, entries in grouped_files.items():
            entries.sort(
                key=lambda e: (
                    e.is_chunk,
                    e.chunk_num if e.chunk_num is not None else -1,
                )
            )

            # Validate and resolve path using Foundation security
            target_abs_path = extractor.validate_and_resolve_path(rel_path_str)
            if not target_abs_path:
                logger.warning(
                    "unbundle.skip.unsafe_path",
                    path=rel_path_str,
                )
                continue

            try:
                content = extractor.determine_content(entries, rel_path_str)
                is_empty = extractor.is_empty_file(entries[0])

                if extractor.extract_file(target_abs_path, content, is_empty):
                    file_extraction_counter += 1

            except Exception as e:
                logger.error(
                    "unbundle.extract_error",
                    path=rel_path_str,
                    error=str(e),
                )
                continue

        # Output summary
        if self.cli_context and self.cli_context.json_output:
            summary_data = {
                "output_directory": str(self._target_output_root),
                "total_files": len(grouped_files),
                "extracted_files": file_extraction_counter,
                "dry_run": self.dry_run,
            }
            pout(summary_data, json_key="unbundle_summary", ctx=self.cli_context)
        elif self.dry_run:
            pout(f"\nDry run complete. Would process {len(grouped_files)} unique file paths.")
        else:
            message = (
                "\nExtraction complete. "
                f"Extracted {file_extraction_counter} files to {self._target_output_root}"
            )
            pout(message)

        if self.dry_run:
            logger.info(
                "unbundle.dry_run.complete",
                would_process=len(grouped_files),
            )
        else:
            logger.info(
                "unbundle.complete",
                extracted_count=file_extraction_counter,
                output_root=str(self._target_output_root),
            )

        return True


# 🐝📁🔚
