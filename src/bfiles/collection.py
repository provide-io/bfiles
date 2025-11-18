#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""File collection for bundling operations."""

import os
from pathlib import Path
from typing import TYPE_CHECKING

from provide.foundation import logger
from provide.foundation.resilience import retry

from bfiles.config import BfilesConfig
from bfiles.errors import DirectoryTraversalError, FileCollectionError
from bfiles.exclusions import ExclusionManager

if TYPE_CHECKING:
    from bfiles.progress import ProgressReporter


class FileCollector:
    """Collects files from directory tree with exclusion filtering."""

    def __init__(
        self,
        config: BfilesConfig,
        exclusion_manager: ExclusionManager,
        progress_reporter: "ProgressReporter | None" = None,
    ) -> None:
        self.config = config
        self.exclusion_manager = exclusion_manager
        self.progress_reporter = progress_reporter

    @retry(max_attempts=3)
    def collect(self) -> tuple[list[Path], int, int]:
        """Collect and filter files from root directory.

        Returns:
            Tuple of (sorted_unique_paths, processed_dirs_count, processed_links_count)
        """
        logger.info(
            "file.collect.start",
            root_dir=str(self.config.root_dir),
        )

        candidate_paths: list[Path] = []
        processed_dirs_count = 0
        processed_links_count = 0
        skipped_scan_count = 0

        for root_str, dirs, files in os.walk(
            self.config.root_dir,
            topdown=True,
            followlinks=self.config.follow_symlinks,
            onerror=self._handle_walk_error,
        ):
            current_dir = Path(root_str)
            processed_dirs_count += 1
            logger.debug("file.scan.directory", path=str(current_dir))

            dirs[:] = self._filter_directories(current_dir, dirs)

            for file_name in files:
                try:
                    file_path, is_link = self._process_file(current_dir, file_name)
                    if is_link:
                        processed_links_count += 1
                    if file_path:
                        candidate_paths.append(file_path)
                        logger.debug("file.found.candidate", path=str(file_path))
                        if self.progress_reporter:
                            self.progress_reporter.file_progress(
                                file_path, "found", root_dir=self.config.root_dir
                            )
                except (OSError, FileCollectionError) as e:
                    logger.warning("file.process.error", path=file_name, error=str(e))
                    skipped_scan_count += 1
                    self.exclusion_manager.add_excluded_item(current_dir / file_name, "error")
                    if self.progress_reporter:
                        self.progress_reporter.file_progress(
                            current_dir / file_name, "error", root_dir=self.config.root_dir
                        )

        logger.info(
            "file.collect.complete",
            candidate_count=len(candidate_paths),
            dirs_processed=processed_dirs_count,
            links_processed=processed_links_count,
            skipped=skipped_scan_count,
        )

        return self._deduplicate_and_sort(candidate_paths)

    def _handle_walk_error(self, error: OSError) -> None:
        """Handle os.walk errors."""
        logger.warning("file.walk.error", error=str(error))

    def _filter_directories(self, current_dir: Path, dirs: list[str]) -> list[str]:
        """Filter directories for descent based on exclusion rules.

        Args:
            current_dir: Current directory being processed
            dirs: List of subdirectory names

        Returns:
            Filtered list of directories to descend into
        """
        filtered_dirs = []

        for dir_name in dirs:
            dir_path = current_dir / dir_name
            try:
                resolved_dir = dir_path.resolve()
            except OSError as e:
                logger.warning("file.directory.resolve_error", path=str(dir_path), error=str(e))
                self.exclusion_manager.add_excluded_item(dir_path, "error")
                continue

            exclusion_reason = self.exclusion_manager.is_excluded(resolved_dir)
            if exclusion_reason:
                logger.info(
                    "exclusion.directory.matched",
                    path=str(dir_path),
                    reason=exclusion_reason,
                )
            else:
                logger.debug("exclusion.directory.passed", path=str(resolved_dir))
                filtered_dirs.append(dir_name)

        return filtered_dirs

    def _process_file(self, current_dir: Path, file_name: str) -> tuple[Path | None, bool]:
        """Process single file and determine if it should be included.

        Args:
            current_dir: Directory containing the file
            file_name: Name of the file

        Returns:
            Tuple of (resolved_file_path or None, is_symlink)

        Raises:
            FileCollectionError: If file processing fails
        """
        file_path = current_dir / file_name
        is_symlink = file_path.is_symlink()

        try:
            resolved_path = file_path.resolve()
        except OSError as e:
            raise FileCollectionError(f"Cannot resolve file path {file_path}: {e}") from e

        exclusion_reason = self.exclusion_manager.is_excluded(resolved_path)
        if exclusion_reason:
            logger.debug(
                "exclusion.file.matched",
                path=str(file_path),
                reason=exclusion_reason,
            )
            return None, is_symlink

        if is_symlink:
            return self._handle_symlink(file_path, resolved_path), is_symlink

        if file_path.is_file():
            return resolved_path, is_symlink

        logger.debug("file.not_regular", path=str(file_path))
        return None, is_symlink

    def _handle_symlink(self, original_path: Path, resolved_path: Path) -> Path | None:
        """Handle symbolic link based on configuration.

        Args:
            original_path: Original symlink path
            resolved_path: Resolved target path

        Returns:
            Resolved path if link should be followed, None otherwise

        Raises:
            SymlinkError: If symlink handling fails
        """
        if not self.config.follow_symlinks:
            logger.debug("file.symlink.skipped", path=str(original_path))
            return None

        if not resolved_path.is_file():
            logger.debug(
                "file.symlink.non_file_target",
                path=str(original_path),
                target=str(resolved_path),
            )
            return None

        logger.debug(
            "file.symlink.followed",
            path=str(original_path),
            target=str(resolved_path),
        )
        return resolved_path

    def _deduplicate_and_sort(self, candidate_paths: list[Path]) -> tuple[list[Path], int, int]:
        """Remove duplicates and sort paths.

        Args:
            candidate_paths: List of candidate file paths

        Returns:
            Tuple of (sorted_unique_paths, 0, 0) for backward compatibility
        """
        unique_paths = set(candidate_paths)

        def get_sort_key(p: Path) -> str:
            try:
                return p.relative_to(self.config.root_dir).as_posix()
            except ValueError:
                return p.as_posix()

        try:
            sorted_paths = sorted(unique_paths, key=get_sort_key)
            logger.debug("file.sorted.success", count=len(sorted_paths))

            duplicates_removed = len(candidate_paths) - len(sorted_paths)
            if duplicates_removed > 0:
                logger.debug("file.duplicates.removed", count=duplicates_removed)
        except Exception as e:
            logger.error("file.sort.error", error=str(e))
            raise DirectoryTraversalError(f"Failed to sort candidate paths: {e}") from e
        else:
            return sorted_paths, 0, 0


# 🐝📁🔚
