#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Core orchestration for bundling and listing operations."""

from pathlib import Path
import time

from provide.foundation import logger
from provide.foundation.console import pout
from provide.foundation.context import CLIContext

from bfiles.bundler import Bundler
from bfiles.chunking import FileChunker
from bfiles.collection import FileCollector
from bfiles.config import BfilesConfig
from bfiles.exclusions import ExclusionManager
from bfiles.metadata_writer import MetadataWriter
from bfiles.progress import ProgressReporter
from bfiles.reader import FileReader


def bundle_files(
    config: BfilesConfig, exclusion_manager: ExclusionManager, cli_context: CLIContext | None = None
) -> ExclusionManager:
    """Bundle files into a single output file.

    Args:
        config: Configuration for bundling
        exclusion_manager: Manager for exclusion rules
        cli_context: Optional CLI context for JSON output

    Returns:
        Updated exclusion_manager with statistics
    """
    logger.info("bundle.start", root_dir=str(config.root_dir))
    start_time = time.monotonic()

    # Create progress reporter if enabled
    progress = ProgressReporter(enabled=config.show_progress, cli_context=cli_context)

    # Create components
    collector = FileCollector(config, exclusion_manager, progress_reporter=progress)
    reader = FileReader(config)
    chunker = FileChunker(config)
    metadata_writer = MetadataWriter(config)
    bundler = Bundler(config, reader, chunker, metadata_writer, exclusion_manager, progress_reporter=progress)

    # Collect files
    progress.operation_start("Collecting files")
    sorted_candidate_paths, _, _ = collector.collect()
    progress.operation_end("File collection", len(sorted_candidate_paths))

    # Bundle files
    progress.operation_start("Processing files")
    stats = bundler.bundle(sorted_candidate_paths)
    (
        included_files,
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
    ) = stats
    progress.operation_end("File processing", included_files)

    elapsed = time.monotonic() - start_time
    logger.info("bundle.complete", duration_seconds=elapsed)

    log_bundle_summary(
        config,
        exclusion_manager,
        included_files,
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
        cli_context=cli_context,
    )

    if config.show_excluded:
        logger.info("bundle.show_excluded.start")
        try:
            exclusion_manager.display_exclusions()  # type: ignore[no-untyped-call]
        except AttributeError:
            logger.error("bundle.exclusions.display_error", error="method not found")
        except Exception as e:
            logger.error("bundle.exclusions.display_error", error=str(e))

    return exclusion_manager


def list_potential_files(  # noqa: C901
    config: BfilesConfig, exclusion_manager: ExclusionManager, cli_context: CLIContext | None = None
) -> None:
    """List files that would be included in a bundle.

    Args:
        config: Configuration for listing
        exclusion_manager: Manager for exclusion rules
        cli_context: Optional CLI context for JSON output
    """
    logger.info("list.start", root_dir=str(config.root_dir))
    start_time = time.monotonic()

    # Create progress reporter if enabled
    progress = ProgressReporter(enabled=config.show_progress, cli_context=cli_context)

    # Collect files
    progress.operation_start("Collecting files")
    collector = FileCollector(config, exclusion_manager, progress_reporter=progress)
    sorted_candidate_paths, _, _ = collector.collect()
    progress.operation_end("File collection", len(sorted_candidate_paths))

    included_files: list[Path] = []
    processed_files = 0
    skipped_max_files = 0

    for file_path in sorted_candidate_paths:
        processed_files += 1
        exclusion_reason = exclusion_manager.exclusion_cache.get(file_path)

        if exclusion_reason and exclusion_reason not in ("error", "skipped"):
            logger.debug("list.file.excluded", path=str(file_path), reason=exclusion_reason)
            continue

        if config.max_files is not None and len(included_files) >= config.max_files:
            if skipped_max_files == 0:
                logger.info("list.limit.reached", max_files=config.max_files)
            skipped_max_files += 1
            exclusion_manager.add_excluded_item(file_path, "skipped")
            continue

        included_files.append(file_path)

    elapsed = time.monotonic() - start_time
    logger.info("list.complete", duration_seconds=elapsed)

    log_list_summary(len(included_files), processed_files, exclusion_manager, cli_context=cli_context)

    # Output file list as JSON or text
    if cli_context and cli_context.json_output:
        file_list = [
            str(path_obj.relative_to(config.root_dir))
            if path_obj.is_relative_to(config.root_dir)
            else str(path_obj)
            for path_obj in included_files
        ]
        pout({"files": file_list, "count": len(included_files)}, json_key="list", ctx=cli_context)
    elif not included_files:
        pout("\nNo files found matching the criteria.")
    else:
        pout("\n--- Files that would be included in bundle ---")
        for i, path_obj in enumerate(included_files, start=1):
            try:
                rel_path = path_obj.relative_to(config.root_dir)
                pout(f"{i:4d}: {rel_path.as_posix()}")
            except ValueError:
                pout(f"{i:4d}: {path_obj.as_posix()} (Absolute Path)")
            except Exception as e:
                pout(f"{i:4d}: Error displaying path {path_obj}: {e}")
        pout("--- End of list ---")

    if config.show_excluded:
        logger.info("list.show_excluded.start")
        try:
            exclusion_manager.display_exclusions()  # type: ignore[no-untyped-call]
        except AttributeError:
            logger.error("list.exclusions.display_error", error="method not found")
        except Exception as e:
            logger.error("list.exclusions.display_error", error=str(e))


def log_bundle_summary(
    config: BfilesConfig,
    exclusion_manager: ExclusionManager,
    included_files: int,
    total_size: int,
    duplicates: int,
    empty_files: int,
    io_errors: int,
    encoding_errors: int,
    skipped_max_files: int,
    unsafe_excluded: int,
    unsafe_sanitized: int,
    total_content_tokens: int,
    overall_bundle_tokens: int | None,
    cli_context: CLIContext | None = None,
) -> None:
    """Log bundle creation summary statistics.

    Args:
        config: Configuration used for bundling
        exclusion_manager: Manager with exclusion statistics
        included_files: Number of files included
        total_size: Total size in bytes
        duplicates: Number of duplicate files
        empty_files: Number of empty files
        io_errors: Number of IO errors
        encoding_errors: Number of encoding errors
        skipped_max_files: Number of files skipped due to max limit
        unsafe_excluded: Number of files excluded due to dangerous characters
        unsafe_sanitized: Number of files with sanitized dangerous characters
        total_content_tokens: Total content tokens
        overall_bundle_tokens: Overall bundle token count
        cli_context: Optional CLI context for JSON output
    """
    config_excluded_files = exclusion_manager.get_config_excluded_files_count()
    config_excluded_dirs = exclusion_manager.get_config_excluded_dirs_count()
    total_config_excluded = config_excluded_files + config_excluded_dirs

    total_system_errors = io_errors + exclusion_manager.get_error_count()
    skipped_by_limit = exclusion_manager.get_skipped_by_limit_count()

    tokens_str = str(overall_bundle_tokens) if overall_bundle_tokens is not None else "N/A"

    logger.info(
        "bundle.summary",
        included=included_files,
        size_bytes=total_size,
        content_tokens=total_content_tokens,
        bundle_tokens=tokens_str,
        duplicates=duplicates,
        config_excluded=total_config_excluded,
        config_excluded_files=config_excluded_files,
        config_excluded_dirs=config_excluded_dirs,
        empty=empty_files,
        skipped_limit=skipped_by_limit,
        errors=total_system_errors,
        encoding_errors=encoding_errors,
        unsafe_excluded=unsafe_excluded,
        unsafe_sanitized=unsafe_sanitized,
    )

    # Output JSON summary if requested
    if cli_context and cli_context.json_output:
        summary_data = {
            "included_files": included_files,
            "total_size_bytes": total_size,
            "content_tokens": total_content_tokens,
            "bundle_tokens": overall_bundle_tokens,
            "duplicates": duplicates,
            "empty_files": empty_files,
            "config_excluded_files": config_excluded_files,
            "config_excluded_dirs": config_excluded_dirs,
            "skipped_by_limit": skipped_by_limit,
            "io_errors": total_system_errors,
            "encoding_errors": encoding_errors,
            "unsafe_excluded": unsafe_excluded,
            "unsafe_sanitized": unsafe_sanitized,
            "output_file": str(config.output_file) if config.output_file else None,
        }
        pout(summary_data, json_key="bundle_summary", ctx=cli_context)


def log_list_summary(
    included_count: int,
    processed_count: int,
    exclusion_manager: ExclusionManager,
    cli_context: CLIContext | None = None,
) -> None:
    """Log file listing summary statistics.

    Args:
        included_count: Number of files that would be included
        processed_count: Number of files processed
        exclusion_manager: Manager with exclusion statistics
        cli_context: Optional CLI context for JSON output
    """
    config_excluded_files = exclusion_manager.get_config_excluded_files_count()
    config_excluded_dirs = exclusion_manager.get_config_excluded_dirs_count()
    total_config_excluded = config_excluded_files + config_excluded_dirs

    total_errors = exclusion_manager.get_error_count()
    skipped_by_limit = exclusion_manager.get_skipped_by_limit_count()

    logger.info(
        "list.summary",
        found=included_count,
        processed_scan=processed_count,
        config_excluded=total_config_excluded,
        config_excluded_files=config_excluded_files,
        config_excluded_dirs=config_excluded_dirs,
        skipped_limit=skipped_by_limit,
        scan_errors=total_errors,
    )

    # Output JSON summary if requested
    if cli_context and cli_context.json_output:
        summary_data = {
            "files_found": included_count,
            "files_processed": processed_count,
            "config_excluded_files": config_excluded_files,
            "config_excluded_dirs": config_excluded_dirs,
            "skipped_by_limit": skipped_by_limit,
            "scan_errors": total_errors,
        }
        pout(summary_data, json_key="list_summary", ctx=cli_context)


# 🐝📁🔚
