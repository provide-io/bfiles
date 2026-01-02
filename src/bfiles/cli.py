#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#


import datetime
from pathlib import Path
import sys
from typing import Literal

import click
from provide.foundation import logger
from provide.foundation.cli.decorators import output_options
from provide.foundation.console import perr, pout
from provide.foundation.context import CLIContext

from bfiles.config import BfilesConfig, ExcludePattern, _get_default_exclude_patterns
from bfiles.core import bundle_files, list_potential_files
from bfiles.exclusions import ExclusionManager
from bfiles.unbundler import Unbundler

LogLevel = Literal["debug", "info", "warn", "warning", "error", "critical"]

LOG_LEVEL_CHOICES = ["debug", "info", "warn", "warning", "error", "critical"]
HASH_ALGO_CHOICES = ["sha256", "sha1", "md5", "sha512"]

try:
    from importlib.metadata import version

    __version__ = version("bfiles")
except ImportError:
    __version__ = "unknown"


# Main CLI group
@click.group(context_settings={"help_option_names": ["-h", "--help"]})
@click.version_option(version=__version__, package_name="bfiles", message="%(package)s version %(version)s")
def cli() -> None:
    """
    bfiles: A utility to bundle multiple files into a single text archive

    and unbundle them back.
    """


@cli.command(name="bundle", context_settings={"help_option_names": ["-h", "--help"]})
@click.option(
    "--root-dir",
    "-d",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, readable=True, path_type=Path),
    default=".",
    show_default=True,
    help="Root directory to scan for files.",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(dir_okay=False, writable=True, path_type=Path),
    default=None,
    help="Output file path for the bundle. [default: bfiles-YYYYMMDD-HHMMSS.txt in root-dir]",
)
@click.option(
    "--include",
    "-i",
    multiple=True,
    type=str,
    help=("Inclusion pattern (glob/literal). Overrides excludes except .gitignore. Use multiple times."),
)
@click.option(
    "--exclude",
    "-e",
    multiple=True,
    type=str,
    help="Exclusion pattern (regex/glob/literal, ends with / for dir). Use multiple times.",
)
@click.option(
    "--show-excluded",
    is_flag=True,
    default=False,
    help="Show excluded files/dirs (incl. .gitignore) in a table after processing.",
)
@click.option(
    "--exclusion-report",
    type=click.Path(dir_okay=False, writable=True, path_type=Path),
    default=None,
    help="Generate a text report of excluded items (incl. .gitignore) to this file.",
)
@click.option(
    "--log-level",
    "-l",
    type=click.Choice(LOG_LEVEL_CHOICES, case_sensitive=False),
    default="warning",
    show_default=True,
    help="Set the logging level.",
)
@click.option(
    "--encoding",
    type=str,
    default="utf-8",
    show_default=True,
    help="Encoding to use when reading files.",
)
@click.option(
    "--hash-algo",
    type=click.Choice(HASH_ALGO_CHOICES, case_sensitive=False),
    default="sha256",
    show_default=True,
    help="Hashing algorithm for file checksums.",
)
@click.option(
    "--no-gitignore",
    is_flag=True,
    default=False,
    help="Disable automatic loading and processing of .gitignore files.",
)
@click.option(
    "--follow-symlinks",
    is_flag=True,
    default=False,
    help="Follow symbolic links during directory scan.",
)
@click.option(
    "--max-files",
    "-m",
    type=int,
    default=None,
    help="Maximum number of files to include in the bundle.",
)
@click.option(
    "--list-files-only",
    is_flag=True,
    default=False,
    help="List files that would be included (after exclusions) and exit.",
)
@click.option(
    "--add-comment",
    type=str,
    default=None,
    help="Add a custom comment line to the bundle header.",
)
@click.option(
    "--chunk-size",
    type=int,
    default=None,
    help="Maximum tokens per chunk. No chunking if None. Requires tiktoken.",
    show_default=True,
)
@click.option("--chunk-overlap", type=int, default=0, help="Token overlap between chunks.", show_default=True)
@click.option(
    "--allow-unsafe",
    is_flag=True,
    default=False,
    help="Allow files with terminal-breaking control characters (ESC, NUL, BEL, etc.).",
)
@click.option(
    "--sanitize-unsafe",
    is_flag=True,
    default=False,
    help="Sanitize dangerous control characters to visible representations ([ESC], [NUL], etc.).",
)
@click.option(
    "--progress/--no-progress",
    default=True,
    help="Show real-time progress during file operations.",
)
@output_options
@click.pass_context
def main(  # noqa: C901
    ctx: click.Context,
    root_dir: Path,
    output: Path | None,
    include: tuple[str, ...],
    exclude: tuple[str, ...],
    show_excluded: bool,
    exclusion_report: Path | None,
    log_level: LogLevel,
    encoding: str,
    hash_algo: str,
    no_gitignore: bool,
    follow_symlinks: bool,
    max_files: int | None,
    list_files_only: bool,
    add_comment: str | None,
    chunk_size: int | None,
    chunk_overlap: int,
    allow_unsafe: bool,
    sanitize_unsafe: bool,
    progress: bool,
    json_output: bool | None,
    no_color: bool,
    no_emoji: bool,
) -> None:
    """Bundles files from a root directory into a single text archive."""
    # Create CLI context for JSON output support
    if not hasattr(ctx, "obj") or ctx.obj is None:
        ctx.obj = CLIContext()
    cli_context = ctx.obj
    if json_output is not None:
        cli_context.json_output = json_output
    if no_color:
        cli_context.no_color = no_color
    if no_emoji:
        cli_context.no_emoji = no_emoji

    # Note: Foundation logger level is set via FOUNDATION_LOG_LEVEL env var
    logger.info("bfiles bundle command started", log_level=log_level)

    if output is None and not list_files_only:
        timestamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        output_file_path = root_dir.resolve() / f"bf-{timestamp}.txt"
    elif output is not None:
        output_file_path = output.resolve()
    else:
        output_file_path = None

    logger.debug(
        "cli.bundle.arguments",
        root_dir=str(root_dir),
        output=str(output_file_path) if output_file_path else None,
        include=list(include),
        exclude=list(exclude),
        show_excluded=show_excluded,
        log_level=log_level,
        encoding=encoding,
        hash_algo=hash_algo,
        exclusion_report=str(exclusion_report) if exclusion_report else None,
        no_gitignore=no_gitignore,
        follow_symlinks=follow_symlinks,
        max_files=max_files,
        list_files_only=list_files_only,
        add_comment=add_comment,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        allow_unsafe=allow_unsafe,
        sanitize_unsafe=sanitize_unsafe,
        progress=progress,
    )

    exclusion_manager_instance: ExclusionManager | None = None

    try:
        user_exclude_patterns: list[ExcludePattern] = list(exclude)
        all_exclude_patterns: list[ExcludePattern] = _get_default_exclude_patterns() + user_exclude_patterns
        user_include_patterns: list[str] = list(include)

        config = BfilesConfig(
            root_dir=root_dir.resolve(),
            output_file=output_file_path,
            include_patterns=user_include_patterns,
            exclude_patterns=all_exclude_patterns,
            show_excluded=show_excluded,
            use_gitignore=not no_gitignore,
            follow_symlinks=follow_symlinks,
            max_files=max_files,
            encoding=encoding,
            hash_algorithm=hash_algo,
            list_files_only=list_files_only,
            header_comment=add_comment,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            allow_unsafe=allow_unsafe,
            sanitize_unsafe=sanitize_unsafe,
            show_progress=progress,
        )
        logger.debug(f"Effective configuration: {config}")

        try:
            exclusion_manager_instance = ExclusionManager(config)
            if config.use_gitignore:
                logger.info(".gitignore handling enabled.")
            else:
                logger.info(".gitignore handling disabled by config or flag.")
            exclusion_manager_instance.validate_config_patterns()
        except ImportError as e:  # pragma: no cover
            if "pathspec" in str(e) and config.use_gitignore:
                logger.critical(
                    "dependency.pathspec.missing",
                    error=str(e),
                    resolution=("Install via `pip install bfiles[gitignore]` to enable .gitignore support."),
                    exc_info=False,
                )
                perr(f"Error: {e}. 'pathspec' library is required for .gitignore support.")
                perr("You can disable .gitignore handling with the --no-gitignore flag.")
                perr("Or install with: pip install bfiles[gitignore]")
                raise SystemExit(2) from None
            else:
                raise

        if config.list_files_only:
            logger.info("Listing files only. Bundle will not be generated.")
            list_potential_files(config, exclusion_manager_instance, cli_context=cli_context)
            logger.info("File listing process completed.")
        else:
            if config.output_file is None:  # pragma: no cover
                logger.critical("Error: Output file path is required for bundling but was not determined.")
                perr("Error: Output file path could not be determined.")
                raise SystemExit(1)

            logger.info(f"Starting bundling process. Output to: {config.output_file}")
            bundle_files(config=config, exclusion_manager=exclusion_manager_instance, cli_context=cli_context)
            logger.info(f"Bfiles process completed successfully. Bundle saved to: {config.output_file}")
            # Display success message to user
            pout(f"Bundle created: {config.output_file}", ctx=cli_context)

        if exclusion_report and exclusion_manager_instance:  # pragma: no cover
            logger.info(f"Generating exclusion report to: {exclusion_report}")
            exclusion_manager_instance.generate_exclusion_report(exclusion_report)
        elif exclusion_report and not exclusion_manager_instance:  # pragma: no cover
            logger.error("Cannot generate exclusion report, ExclusionManager not available.")

    except ImportError as e:  # pragma: no cover
        logger.critical(f"Import error: {e}", exc_info=True)
        perr(f"Error: An import failed - {e}")
        raise SystemExit(1) from None
    except ValueError as e:  # pragma: no cover
        logger.critical(f"Configuration or Value error: {e}", exc_info=False)
        perr(f"Error: {e}")
        raise SystemExit(1) from None
    except OSError as e:  # pragma: no cover
        logger.critical(f"File system error: {e}", exc_info=False)
        perr(f"Error: {e}")
        raise SystemExit(1) from None
    except Exception as e:  # pragma: no cover
        logger.critical(f"An unexpected error occurred: {e}", exc_info=True)
        perr(f"An unexpected error occurred: {e}")
        raise SystemExit(1) from None


# Actual unbundle function
def _unbundle_files(
    bundle_file: Path,
    output_dir_cli: Path | None,  # Renamed to avoid confusion with Unbundler's internal var
    force: bool,
    list_only: bool,
    dry_run: bool,
    log_level: LogLevel,
    show_progress: bool,
    cli_context: CLIContext | None = None,
) -> None:
    # Note: Foundation logger level is set via FOUNDATION_LOG_LEVEL env var
    logger.info(f"bfiles unbundle command started for '{bundle_file}'", log_level=log_level)

    # The Unbundler class itself handles the logic for default output directory
    # if output_dir_base is None. So, we pass the CLI's output_dir directly.
    # If output_dir_cli is None here, Unbundler will create a default directory.

    try:
        unbundler_instance = Unbundler(
            bundle_file_path=bundle_file,
            output_dir_base=output_dir_cli,  # Pass the CLI option value
            force_overwrite=force,
            list_only=list_only,
            dry_run=dry_run,
            show_progress=show_progress,
            cli_context=cli_context,
        )
        if unbundler_instance.extract():
            logger.info("Unbundling process completed successfully.")
        else:
            logger.error("Unbundling process encountered errors.")
            raise SystemExit(1)
    except FileNotFoundError:
        logger.critical(f"Error: Bundle file '{bundle_file}' not found.", exc_info=False)
        perr(f"Error: Bundle file '{bundle_file}' not found.")
        raise SystemExit(1) from None
    except Exception as e:  # pragma: no cover
        logger.critical(f"An unexpected error occurred during unbundling: {e}", exc_info=True)
        perr(f"An unexpected error occurred: {e}")
        raise SystemExit(1) from None


@cli.command(name="unbundle", context_settings={"help_option_names": ["-h", "--help"]})
@click.argument(
    "bundle_file",
    type=click.Path(exists=True, file_okay=True, dir_okay=False, readable=True, path_type=Path),
)
@click.option(
    "--output-dir",
    "-o",
    type=click.Path(file_okay=False, dir_okay=True, writable=True, path_type=Path),
    default=None,
    help=(
        "Directory to extract files into. "
        "[default: a new directory named after the bundle file in its location]"
    ),
)
@click.option(
    "--force",
    "-f",
    is_flag=True,
    default=False,
    help="Overwrite existing files in the output directory without prompting.",
)
@click.option(
    "--list-only",
    "--ls",
    is_flag=True,
    default=False,
    help="List the contents of the bundle without extracting any files.",
)
@click.option(
    "--dry-run",
    "-n",
    is_flag=True,
    default=False,
    help="Show what files would be extracted and where, but do not actually write any files.",
)
@click.option(
    "--log-level",
    "-l",
    type=click.Choice(LOG_LEVEL_CHOICES, case_sensitive=False),
    default="warning",
    show_default=True,
    help="Set the logging level for the unbundle operation.",
)
@click.option(
    "--progress/--no-progress",
    default=True,
    help="Show real-time progress during file extraction.",
)
@output_options
@click.pass_context
def unbundle_command(
    ctx: click.Context,
    bundle_file: Path,
    output_dir: Path | None,
    force: bool,
    list_only: bool,
    dry_run: bool,
    log_level: LogLevel,
    progress: bool,
    json_output: bool | None,
    no_color: bool,
    no_emoji: bool,
) -> None:
    """Extracts files from a bfiles bundle archive."""
    # Create CLI context for JSON output support
    if not hasattr(ctx, "obj") or ctx.obj is None:
        ctx.obj = CLIContext()
    cli_context = ctx.obj
    if json_output is not None:
        cli_context.json_output = json_output
    if no_color:
        cli_context.no_color = no_color
    if no_emoji:
        cli_context.no_emoji = no_emoji

    _unbundle_files(bundle_file, output_dir, force, list_only, dry_run, log_level, progress, cli_context)


if __name__ == "__main__":  # pragma: no cover
    cli()

# 🐝📁🔚
