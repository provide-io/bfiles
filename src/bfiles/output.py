#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#


from collections.abc import Sequence  # Use Sequence for generic iterable type hint
import datetime
import os
from pathlib import Path
import sys
import time

# Conditionally import TypeAlias for older Python versions if needed
from typing import TypeAlias

# Avoid circular import, only import for type hint if needed
from provide.foundation import logger
from provide.foundation.console.output import pout

from bfiles.config import BfilesConfig  # Import for type hint
from bfiles.metadata import FileMetadata  # Import the attrs class

# Try importing Rich for enhanced console output
try:
    from rich.console import Console
    from rich.table import Table

    RICH_AVAILABLE = True
except ImportError:  # pragma: no cover
    RICH_AVAILABLE = False
    # Define dummy types for type hinting when Rich is not available
    Console: TypeAlias = type(None)  # type: ignore
    Table: TypeAlias = type(None)  # type: ignore


def truncate_path(path: Path, max_len: int = 60) -> str:
    """Truncates a path string for display if it exceeds max_len, using a middle ellipsis."""
    path_str = str(path).replace(os.path.sep, "/")  # Use POSIX separators
    if len(path_str) <= max_len:
        return path_str

    ellipsis = "..."
    if max_len < len(ellipsis) + 2:  # Need at least one char on each side
        # Return tail portion if max_len is extremely small
        return (
            ellipsis + path_str[-(max_len - len(ellipsis)) :]
            if (max_len - len(ellipsis)) > 0
            else ellipsis[:max_len]
        )

    # Calculate how many chars to keep total (excluding ellipsis)
    keep_len = max_len - len(ellipsis)
    # Keep roughly half on each side, leaning towards keeping more of the end
    end_len = (keep_len + 1) // 2
    start_len = keep_len - end_len  # The remaining part

    # Ensure lengths are non-negative (should be covered by initial check)
    start_len = max(0, start_len)
    end_len = max(0, end_len)  # Ensure end_len is also non-negative

    # Prevent overlap issue if string is just slightly longer than max_len
    if start_len + end_len >= len(path_str):  # pragma: no cover
        return path_str  # Should not happen with logic above, but safe fallback

    return f"{path_str[:start_len]}{ellipsis}{path_str[-end_len:]}"


def display_summary_table(  # noqa: C901
    all_processed_metadata: Sequence[FileMetadata],
    config: BfilesConfig,  # Accept config to check show_excluded
    force_plain_text: bool = False,
) -> None:
    """
    Displays a summary table of processed files using Rich, or basic text fallback.

    By default, it hides files that were simply 'excluded'. Use the
    --show-excluded flag (via config.show_excluded) to include them.
    """
    if not all_processed_metadata:  # pragma: no cover
        logger.info("No files were processed or recorded for the summary table.")
        return

    # --- Filter metadata based on config.show_excluded ---
    if not config.show_excluded:
        # Default: Filter out items whose *only* status is 'excluded'
        metadata_to_display = [meta for meta in all_processed_metadata if meta.operation != "excluded"]
    else:
        # If --show-excluded is True, display everything
        metadata_to_display = list(all_processed_metadata)  # Ensure it's a list for consistency

    if not metadata_to_display:  # pragma: no cover
        if not config.show_excluded:
            pout("\n(No included, duplicate, empty, skipped, or error files to display)")
            pout("(Use --show-excluded to see items excluded by rules)")
        return

    table_title = "Bfiles Bundle Content Summary"
    if config.show_excluded:
        table_title = "Bfiles Full Processed Summary"
    table_title = f"{table_title} ({len(metadata_to_display)} items)"

    if RICH_AVAILABLE and not force_plain_text:
        console = Console(file=sys.stdout)
        table = Table(
            title=table_title,
            show_header=True,
            header_style="bold cyan",
            show_lines=False,
            row_styles=["none", "dim"],
            caption="Op: + Incl, x Excl, d Dup, 0 Empty, - Skip, ! Err",
        )
        table.add_column("Op", style="bold", width=3, justify="center")
        table.add_column("#", style="dim", width=5, justify="right")
        table.add_column("Path", style="green", no_wrap=False, min_width=30, max_width=60, ratio=3)
        table.add_column("Size", style="magenta", width=10, justify="right")
        table.add_column("Type", style="yellow", width=15, overflow="fold")
        table.add_column("Checksum", style="dim", width=15)
        table.add_column("Modified", style="blue", width=18, justify="center")
        table.add_column("Info", style="white", ratio=2, overflow="fold", min_width=20)

        file_counter = 0
        for entry in metadata_to_display:
            if entry.operation == "included":
                file_counter += 1

            (
                op_code_display_rich,
                _,
                num_display,
                path_display,
                size_display,
                type_display,
                checksum_display,
                mod_display,
                info_display_rich,
                _,
                row_style,
            ) = _prepare_display_row_data(entry, config, file_counter, force_plain_text)

            table.add_row(
                op_code_display_rich,
                num_display,
                path_display,
                size_display,
                type_display,
                checksum_display,
                mod_display,
                info_display_rich,
                style=row_style,
            )

        console.print(table)
        return

    logger.debug("using_plain_text_output")
    pout(f"\n{table_title}")
    header_fmt = "{:<3} | {:<4} | {:<55} | {:>10} | {:<15} | {:<14} | {:<18} | {}"
    pout(header_fmt.format("Op", "#", "Path", "Size", "Type", "Checksum", "Modified", "Info"))
    pout("-" * 150)

    file_counter = 0
    for entry in metadata_to_display:
        if entry.operation == "included":
            file_counter += 1

        (
            _,
            op_code_plain,
            num_display,
            path_display,
            _size_display_raw,
            type_display,
            checksum_display,
            mod_display,
            _,
            info_display_plain,
            _,
        ) = _prepare_display_row_data(entry, config, file_counter, force_plain_text)

        size_display_plain = str(entry.size) if entry.size >= 0 else "N/A"

        pout(
            header_fmt.format(
                op_code_plain,
                num_display,
                path_display,
                size_display_plain,
                type_display,
                checksum_display,
                mod_display,
                info_display_plain,
            )
        )

    pout("-" * 150)
    pout("Op: + Incl, x Excl, d Dup, 0 Empty, - Skip, ! Err")


# Helper function to prepare row data for both Rich and plain text tables
def _prepare_display_row_data(  # noqa: C901
    meta: FileMetadata,
    config: BfilesConfig,
    file_counter: int,
    force_plain_text: bool,
) -> tuple[str, str, str, str, str, str, str, str, str, str, str]:
    """Prepares a tuple of strings for a single row in the summary table."""
    op_code_rich_prefix = ""
    op_code_plain = meta.get_operation_code()
    row_style = ""  # For Rich table, not directly used by plain text

    num_display = "-"
    if meta.operation == "included":
        op_code_rich_prefix = "[bold green]"
        num_display = str(file_counter)
    elif meta.operation == "excluded":
        op_code_rich_prefix = "[bold red]"
        row_style = "dim"
    elif meta.operation == "duplicate":
        op_code_rich_prefix = "[bold yellow]"
        row_style = "dim"
    elif meta.operation == "empty":
        op_code_rich_prefix = "[dim]"
        row_style = "dim"
    elif meta.operation == "skipped":
        op_code_rich_prefix = "[cyan]"
        row_style = "dim"
    elif meta.operation == "error":
        op_code_rich_prefix = "[bold bright_red]"
        num_display = "!"  # Keep '!' for plain text too
    else:  # pragma: no cover
        op_code_rich_prefix = "[dim]"
        op_code_plain = "?"  # Ensure plain op code is also '?'

    op_code_display_rich = f"{op_code_rich_prefix}{op_code_plain}[/]"

    try:
        rel_path_str = str(meta.path.relative_to(config.root_dir))
    except ValueError:
        rel_path_str = str(meta.path)
    except Exception as e:  # pragma: no cover
        logger.warning(f"Error getting relative path for {meta.path}: {e}. Using absolute.")
        rel_path_str = str(meta.path)
    path_display = truncate_path(Path(rel_path_str), max_len=55)

    size_display = (
        str(meta.size)
        if meta.size >= 0
        else ("N/A" if not RICH_AVAILABLE or force_plain_text else "[red]N/A[/]")
    )
    type_display = meta.file_type if meta.file_type else "-"
    checksum_display = (meta.checksum[:12] + "..") if meta.checksum else "-"

    mod_display = "-"
    if isinstance(meta.modified, datetime.datetime) and meta.modified.year > 1:
        mod_display = meta.modified.strftime("%Y-%m-%d %H:%M")

    info_display_plain = ""
    info_display_rich = ""  # Separate for Rich potentially
    if meta.operation == "duplicate" and meta.original:
        try:
            rel_orig_path_str = str(meta.original.relative_to(config.root_dir))
        except ValueError:  # pragma: no cover
            rel_orig_path_str = str(meta.original)
        except Exception as e:  # pragma: no cover
            logger.warning(f"Error getting relative path for original {meta.original}: {e}")
            rel_orig_path_str = str(meta.original)
        info_display_plain = f"Dup of: {truncate_path(Path(rel_orig_path_str), 15)}"
        info_display_rich = f"Dup of: {truncate_path(Path(rel_orig_path_str), 20)}"
    elif meta.operation == "excluded":
        info_display_plain = "Excluded"
        info_display_rich = "[red]Excluded[/]"
    elif meta.operation == "skipped":
        info_display_plain = "Skipped(Limit)"
        info_display_rich = "[cyan]Skipped (Limit)[/]"
    elif meta.operation == "error":
        info_display_plain = "Error"
        info_display_rich = "[red]Error[/]"

    if meta.total_chunks is not None and meta.total_chunks > 0:
        chunk_info_str = f"Chunked ({meta.total_chunks} parts)"
        if info_display_plain and info_display_plain not in ["Excluded", "Skipped(Limit)", "Error"]:
            info_display_plain += f"; {chunk_info_str}"
        elif not info_display_plain:
            info_display_plain = chunk_info_str

        if info_display_rich and info_display_rich not in [
            "[red]Excluded[/]",
            "[cyan]Skipped (Limit)[/]",
            "[red]Error[/]",
        ]:
            info_display_rich += f"; {chunk_info_str}"
        elif not info_display_rich:
            info_display_rich = chunk_info_str

    # For plain text we use op_code_plain; Rich uses op_code_display_rich.
    # Tuple positions align with both renderers' expectations.

    return (
        op_code_display_rich,  # For Rich
        op_code_plain,  # For Plain
        num_display,
        path_display,
        size_display,  # Rich can style this if it's "N/A"
        type_display,
        checksum_display,
        mod_display,
        info_display_rich,  # For Rich
        info_display_plain,  # For Plain
        row_style,  # For Rich
    )


def generate_bundle_header(config: BfilesConfig) -> str:
    """Generates the main header for the bundle file."""
    from bfiles import __version__ as bfiles_version  # To get current version

    header_lines = [
        (
            "Attention: The following text is a 'bfiles' bundle, containing multiple "
            "delimited files with metadata."
        ),
        (
            "Parse and analyze the content between '<<< BOF <<<' and '>>> EOF >>>' for each "
            "'### FILE...' entry."
        ),
        "",
        "--- Bundle Configuration ---",
        f"# Root Directory: {config.root_dir.as_posix()}",
        f"# Follow Symlinks: {config.follow_symlinks}",
        f"# Max Files: {config.max_files if config.max_files is not None else 'Unlimited'}",
        (
            f"# Generated by bfiles v{bfiles_version} (Python utility) on "
            f"{datetime.datetime.now(datetime.UTC).isoformat()}"
        ),
    ]
    if hasattr(config, "header_comment") and config.header_comment:  # Check if attribute exists
        header_lines.append(f"# Comment: {config.header_comment}")
    header_lines.append("--- End of Bundle Configuration ---")
    header_lines.append("")
    return "\n".join(header_lines)


def generate_summary_text(
    config: BfilesConfig,  # Pass config for context
    included_files: int,
    total_size: int,
    duplicates: int,
    # Parameters matching the call from core.py:
    excluded_by_config_files: int,  # Renamed from excluded_files_total
    excluded_by_config_dirs: int,  # Renamed from excluded_dirs_total
    empty_files: int,
    io_errors: int,  # This is total_system_errors from core.py
    encoding_errors: int,
    skipped_by_limit: int,  # Renamed from skipped_max_files
    excluded_by_gitignore: int,  # Renamed from gitignore_excluded
    unsafe_excluded: int,  # Files excluded due to dangerous characters
    unsafe_sanitized: int,  # Files with sanitized dangerous characters
    total_token_count: int,
    overall_bundle_token_count: int | None,
    start_time: float,
) -> str:
    """Generate the summary section text for the bundle file footer."""
    elapsed = time.monotonic() - start_time

    # Total items excluded by configuration (non-gitignore)
    total_config_excluded_items = excluded_by_config_files + excluded_by_config_dirs

    gitignore_line = ""
    if config.use_gitignore and excluded_by_gitignore > 0:  # Only show if count > 0
        gitignore_line = f"- Items Excluded by .gitignore: {excluded_by_gitignore}\n"

    skipped_line = ""
    if skipped_by_limit > 0:  # Only show if files were skipped
        skipped_line = f"- Files Skipped (Limit Reached): {skipped_by_limit}\n"  # Renamed for clarity

    unsafe_excluded_line = ""
    if unsafe_excluded > 0:
        unsafe_excluded_line = f"- Files Excluded (Unsafe Control Characters): {unsafe_excluded}\n"

    unsafe_sanitized_line = ""
    if unsafe_sanitized > 0:
        unsafe_sanitized_line = f"- Files Sanitized (Control Characters Replaced): {unsafe_sanitized}\n"

    summary_lines = [
        "\n### BUNDLE SUMMARY ###",
        f"- Included Files: {included_files}",
        f"- Total Size (Included): {total_size} bytes",
        f"- Duplicate Files Skipped: {duplicates}",
        (
            "- Items Excluded by Config/Defaults: "
            f"{total_config_excluded_items} (Files: {excluded_by_config_files}, "
            f"Dirs: {excluded_by_config_dirs})"
        ),
        gitignore_line.strip(),
        unsafe_excluded_line.strip(),
        unsafe_sanitized_line.strip(),
        f"- Empty Files Found: {empty_files}",
        skipped_line.strip(),
        f"- System Errors Encountered: {io_errors}",  # Renamed for clarity
        f"- Encoding Errors (Fallback Attempted): {encoding_errors}",
    ]
    # Add token information
    if overall_bundle_token_count is not None:
        summary_lines.append(
            f"- Estimated Bundle Token Range: {total_token_count} - {overall_bundle_token_count}"
        )
    else:
        summary_lines.append(
            f"- Total Content Tokens (Included Files): {total_token_count} (Full bundle estimate N/A)"
        )

    summary_lines.extend([f"- Processing Time: {elapsed:.2f} seconds", "### END BUNDLE SUMMARY ###"])
    # Filter out empty lines (like the gitignore/skipped lines if count was 0)
    return "\n".join(line for line in summary_lines if line)


# 🐝📁🔚
