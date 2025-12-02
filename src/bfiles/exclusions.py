#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#


import contextlib
import datetime
import fnmatch
import os
from pathlib import Path
import re
from re import Pattern
from typing import Any, Literal, TypeAlias  # type: ignore[assignment]

try:
    import pathspec

    try:
        from pathspec import PathSpec
    except ImportError:  # pragma: no cover
        PathSpec: TypeAlias = Any  # type: ignore
except ImportError:  # pragma: no cover
    pathspec = None
    PathSpec: TypeAlias = Any  # type: ignore

from provide.foundation import logger
from provide.foundation.console import pout

from bfiles.config import BfilesConfig, ExcludePattern, IncludePattern

ExclusionReason: TypeAlias = (
    Literal["gitignore", "regex", "glob", "string", "skipped", "error", "unsafe"] | None
)
ExclusionOutcome: TypeAlias = Literal["included_by_rule", "excluded_by_rule", "no_match"]


class ExclusionManager:
    """Manage inclusion/exclusion decisions for bundle candidates.

    Precedence rules:
    1. .gitignore (if enabled) always excludes.
    2. --include patterns override subsequent --exclude patterns.
    3. --exclude patterns (user + defaults: string > regex > glob) apply last.
    """

    def __init__(self, config: BfilesConfig) -> None:
        if config.use_gitignore and pathspec is None:  # pragma: no cover
            raise ImportError("pathspec library not found, but use_gitignore is enabled.")

        self.config = config
        self.root_dir = config.root_dir  # Already resolved
        self._raw_exclude_patterns: list[ExcludePattern] = config.exclude_patterns
        self._include_patterns: list[IncludePattern] = config.include_patterns

        self._compiled_regexes: list[Pattern[str]] = []
        self._glob_patterns: list[str] = []
        self._string_literals: list[str] = []

        self._gitignore_specs: dict[Path, PathSpec] = {}
        self.exclusion_cache: dict[Path, ExclusionReason] = {}  # Key: resolved Path
        self.excluded_items: dict[Path, ExclusionReason] = {}  # Key: resolved Path

        # Counters for different exclusion/issue types
        self._gitignore_excluded_count: int = 0
        self._config_excluded_files_count: int = 0
        self._config_excluded_dirs_count: int = 0  # For dirs excluded by non-gitignore rules
        self._error_count: int = 0  # Files/dirs that caused errors during processing
        self._skipped_by_limit_count: int = 0  # Files skipped due to --max-files etc.

        self._compile_config_patterns()
        if self.config.use_gitignore:
            self._load_gitignore_specs()

    def _compile_config_patterns(self) -> None:  # noqa: C901
        self._compiled_regexes = []
        self._glob_patterns = []
        self._string_literals = []
        logger.debug(f"Compiling {len(self._raw_exclude_patterns)} raw exclude patterns.")

        for pattern in self._raw_exclude_patterns:
            if isinstance(pattern, re.Pattern):
                self._compiled_regexes.append(pattern)
                logger.debug(f"Loaded pre-compiled regex pattern: {pattern.pattern}")
            elif isinstance(pattern, str):
                is_glob = "*" in pattern or "?" in pattern or "[" in pattern
                is_regex_candidate = not is_glob

                if is_regex_candidate and not Path(pattern).is_absolute():
                    try:
                        compiled_regex = re.compile(pattern)
                        self._compiled_regexes.append(compiled_regex)
                        logger.debug(f"Compiled string as regex pattern: {pattern}")
                        continue
                    except re.error:
                        logger.debug(f"Pattern '{pattern}' is not a valid regex, trying as glob/literal.")
                        pass

                if is_glob:
                    self._glob_patterns.append(pattern)
                    logger.debug(f"Identified glob pattern: {pattern}")
                elif Path(pattern).is_absolute():
                    self._string_literals.append(str(Path(pattern).resolve(strict=False)))
                    logger.debug(f"Treating absolute path pattern as exact literal: {pattern}")
                elif not is_glob:
                    try:
                        resolved_path = (self.root_dir / pattern).resolve(strict=False)
                        self._string_literals.append(str(resolved_path))
                        logger.debug(
                            "exclude.literal.relative",
                            resolved=str(resolved_path),
                            pattern=pattern,
                        )
                    except OSError as e:  # pragma: no cover
                        logger.warning(
                            "exclude.literal.resolve_failed",
                            pattern=pattern,
                            error=str(e),
                        )
                    except Exception as e:  # pragma: no cover
                        logger.warning(
                            "exclude.literal.process_error",
                            pattern=pattern,
                            error=str(e),
                        )
            else:  # pragma: no cover
                logger.warning(f"Ignoring invalid config exclude pattern type: {type(pattern)} - {pattern}")

        logger.info(
            f"ExclusionManager patterns: {len(self._compiled_regexes)} regex, "
            f"{len(self._glob_patterns)} glob, {len(self._string_literals)} literal."
        )
        logger.info(f"Include patterns: {len(self._include_patterns)} glob/literal.")

    def _load_gitignore_specs(self) -> None:
        self._gitignore_specs = {}
        gitignore_count = 0
        if not self.root_dir.is_dir():  # pragma: no cover
            logger.warning(f"Root directory '{self.root_dir}' not found. Cannot load .gitignore files.")
            return

        logger.info(f"Searching for .gitignore files within '{self.root_dir}'...")
        for gitignore_path_obj in self.root_dir.rglob(".gitignore"):
            if (
                gitignore_path_obj.is_file()
                and ".git" not in gitignore_path_obj.relative_to(self.root_dir).parts
            ):
                gitignore_dir = gitignore_path_obj.parent.resolve()
                logger.debug(f"Found .gitignore: {gitignore_path_obj}")
                try:
                    with gitignore_path_obj.open("r", encoding="utf-8", errors="ignore") as f_in:
                        # Read lines, strip whitespace, filter out empty lines and comments
                        lines = [
                            line.strip() for line in f_in if line.strip() and not line.strip().startswith("#")
                        ]
                        if lines:
                            spec: PathSpec = pathspec.PathSpec.from_lines(
                                pathspec.patterns.GitWildMatchPattern, lines
                            )
                            if spec.patterns:  # Check if spec was successfully created with patterns
                                self._gitignore_specs[gitignore_dir] = spec
                                gitignore_count += 1
                                # Log the actual patterns that pathspec parsed
                                parsed_patterns_for_log = [
                                    p.pattern if hasattr(p, "pattern") else str(p) for p in spec.patterns
                                ]
                                logger.debug(
                                    "gitignore.patterns.loaded",
                                    pattern_count=len(spec.patterns),
                                    patterns=parsed_patterns_for_log,
                                    source=str(gitignore_path_obj),
                                    directory=str(gitignore_dir),
                                )
                            else:  # pragma: no cover
                                logger.debug(
                                    "gitignore.patterns.empty",
                                    source=str(gitignore_path_obj),
                                    lines=lines,
                                )
                        else:  # pragma: no cover
                            logger.debug(f"Skipping empty or comment-only .gitignore: {gitignore_path_obj}")
                except OSError as e:  # pragma: no cover
                    logger.error(f"Failed to read {gitignore_path_obj}: {e}")
                except Exception as e:  # pragma: no cover
                    logger.error(f"Failed to parse {gitignore_path_obj} using pathspec: {e}")
        logger.info(f"Loaded {gitignore_count} .gitignore files with patterns.")

    def validate_config_patterns(self) -> None:
        logger.info("Validating config regex patterns...")
        has_errors = False
        for pattern_config_item in self._raw_exclude_patterns:
            if isinstance(pattern_config_item, str):
                is_glob = (
                    "*" in pattern_config_item or "?" in pattern_config_item or "[" in pattern_config_item
                )
                is_literal_path = (
                    Path(pattern_config_item).is_absolute()
                    or str((self.root_dir / pattern_config_item).resolve(strict=False))
                    in self._string_literals
                )
                if not is_glob and not is_literal_path:
                    try:
                        re.compile(pattern_config_item)
                    except re.error as e:  # pragma: no cover
                        logger.error(
                            "exclude.regex.invalid",
                            pattern=pattern_config_item,
                            error=str(e),
                        )
                        has_errors = True
        if not has_errors:  # pragma: no cover
            logger.info("exclude.regex.validated")
        else:  # pragma: no cover
            logger.warning("exclude.regex.invalid_found")

    def is_excluded(self, path_to_check: Path) -> ExclusionReason:  # noqa: C901
        try:
            resolved_path = path_to_check.resolve()
            resolved_path_str = str(resolved_path)
        except OSError as e:  # pragma: no cover
            logger.error(
                "exclude.resolve_failed",
                path=str(path_to_check),
                error=str(e),
            )
            self.add_excluded_item(path_to_check, "error")
            return "error"

        if resolved_path in self.exclusion_cache:
            # Counters already updated when the item was first cached.
            return self.exclusion_cache[resolved_path]

        # 1. .gitignore check (highest precedence for exclusion)
        if self.config.use_gitignore and self._gitignore_specs and self._check_gitignore(resolved_path):
            logger.debug("exclude.gitignore", path=resolved_path_str)
            self.add_excluded_item(resolved_path, "gitignore")
            return "gitignore"

        # 2. --include patterns (highest precedence for inclusion, overrides config excludes)
        if self._include_patterns:
            for pattern_str in self._include_patterns:
                if fnmatch.fnmatch(resolved_path_str, pattern_str) or fnmatch.fnmatch(
                    resolved_path.name, pattern_str
                ):
                    logger.debug(
                        "exclude.include.override",
                        path=resolved_path_str,
                        pattern=pattern_str,
                    )
                    self.exclusion_cache[resolved_path] = None  # Mark as not excluded
                    # Do not add to self.excluded_items if included
                    return None  # Not excluded

        # 3. --exclude patterns (user + defaults: string > regex > glob)
        # String literals (these are already resolved absolute paths in _string_literals)
        if resolved_path_str in self._string_literals:
            logger.debug("exclude.string.literal", path=resolved_path_str)
            self.add_excluded_item(resolved_path, "string")
            return "string"

        # Regex patterns
        for pattern in self._compiled_regexes:
            if pattern.search(resolved_path_str):
                logger.debug(
                    "exclude.regex.match",
                    path=resolved_path_str,
                    pattern=pattern.pattern,
                )
                self.add_excluded_item(resolved_path, "regex")
                return "regex"

        # Glob patterns
        for pattern_str in self._glob_patterns:
            if fnmatch.fnmatch(resolved_path_str, pattern_str) or fnmatch.fnmatch(
                resolved_path.name, pattern_str
            ):
                logger.debug(
                    "exclude.glob.match",
                    path=resolved_path_str,
                    pattern=pattern_str,
                )
                self.add_excluded_item(resolved_path, "glob")
                return "glob"

        # 4. If no rules matched, it's included by default
        logger.debug("exclude.no_match", path=resolved_path_str)
        self.exclusion_cache[resolved_path] = None  # Not excluded
        return None

    def add_excluded_item(self, path: Path, reason: ExclusionReason) -> None:
        """
        Adds an item to the exclusion tracking and updates relevant counters.

        This method should be the primary way items are marked as excluded internally.
        """
        if reason is None:  # Should not happen if called for an actual exclusion
            return

        resolved_path = path  # Assuming path is already resolved if coming from is_excluded internal calls
        try:
            if not path.is_absolute():  # Resolve if not already
                resolved_path = path.resolve()
        except OSError:  # If path is invalid (e.g. during initial error marking)
            pass  # Keep original path for logging if resolve fails

        self.excluded_items[resolved_path] = reason
        self.exclusion_cache[resolved_path] = reason  # Also update cache

        is_dir = False
        with contextlib.suppress(OSError):  # Path might not exist or be accessible if it's an "error" reason
            is_dir = resolved_path.is_dir()

        if reason == "gitignore":
            self._gitignore_excluded_count += 1
        elif reason in ["string", "regex", "glob"]:
            if is_dir:
                self._config_excluded_dirs_count += 1
            else:
                self._config_excluded_files_count += 1
        elif reason == "error":
            self._error_count += 1
        elif reason == "skipped":  # For limits like max_files
            self._skipped_by_limit_count += 1
        # "excluded" as a generic reason might be from direct input, handle if necessary
        # For now, primarily focusing on reasons set by internal logic.

    def _check_gitignore(self, abs_path_to_check: Path) -> bool:
        if not abs_path_to_check.is_absolute():  # pragma: no cover
            logger.warning(
                "gitignore.check.non_absolute",
                path=str(abs_path_to_check),
            )
            return False

        current_dir_to_check_spec_for = abs_path_to_check.parent
        while self.root_dir <= current_dir_to_check_spec_for:
            if current_dir_to_check_spec_for in self._gitignore_specs:
                spec = self._gitignore_specs[current_dir_to_check_spec_for]
                try:
                    path_relative_to_gitignore_dir = abs_path_to_check.relative_to(
                        current_dir_to_check_spec_for
                    )
                    relative_path_str_for_spec = str(path_relative_to_gitignore_dir).replace(os.path.sep, "/")
                    relative_path_str_for_spec = str(path_relative_to_gitignore_dir).replace(os.path.sep, "/")
                    if spec.match_file(relative_path_str_for_spec):
                        return True
                except ValueError:  # pragma: no cover
                    logger.warning(
                        "gitignore.check.relative_failed",
                        path=str(abs_path_to_check),
                        base=str(current_dir_to_check_spec_for),
                    )
                except Exception as e:  # pragma: no cover
                    logger.error(
                        "gitignore.check.match_error",
                        path=str(abs_path_to_check),
                        base=str(current_dir_to_check_spec_for),
                        error=str(e),
                    )

            if current_dir_to_check_spec_for == self.root_dir:
                break
            if current_dir_to_check_spec_for.parent == current_dir_to_check_spec_for:
                break
            current_dir_to_check_spec_for = current_dir_to_check_spec_for.parent
        return False

    def get_gitignore_excluded_count(self) -> int:
        return self._gitignore_excluded_count

    def get_config_excluded_files_count(self) -> int:
        return self._config_excluded_files_count

    def get_config_excluded_dirs_count(self) -> int:
        return self._config_excluded_dirs_count

    def get_error_count(self) -> int:
        return self._error_count

    def get_skipped_by_limit_count(self) -> int:
        return self._skipped_by_limit_count

    def get_all_exclusions(self) -> dict[Path, ExclusionReason]:
        return dict(sorted(self.excluded_items.items()))

    def _prepare_excluded_item_display_data(
        self, path_obj: Path, reason: ExclusionReason | None
    ) -> tuple[str, str, str]:
        """Helper to format a single excluded item for display."""
        item_type = "N/A"
        try:
            if path_obj.is_symlink():
                item_type = "LINK"
            elif path_obj.is_dir():
                item_type = "DIR"
            elif path_obj.is_file():
                item_type = "FILE"
            else:
                item_type = "???"  # Should not happen for resolved paths
        except OSError:  # Path might not exist if error occurred early
            item_type = "ERR"

        try:
            display_path_str = str(path_obj.relative_to(self.root_dir))
        except ValueError:  # Path is outside root_dir or other error
            display_path_str = str(path_obj)

        # Use POSIX separators for display consistency
        display_path_str = display_path_str.replace(os.path.sep, "/")

        reason_str = str(reason) if reason else "Unknown"
        return item_type, display_path_str, reason_str

    def display_exclusions(self) -> None:  # pragma: no cover
        all_excluded = self.get_all_exclusions()
        if not all_excluded:
            try:
                from rich.console import Console

                console = Console()
                console.print("[i]No files or directories were excluded.[/i]")
            except ImportError:
                pout("No files or directories were excluded.")
            return

        try:
            from rich.console import Console
            from rich.table import Table

            from bfiles.output import truncate_path

            console = Console()
            table = Table(
                title="Excluded Files and Directories",
                show_lines=True,
                show_header=True,
                header_style="bold magenta",
            )
            table.add_column("Type", justify="center", style="dim", width=4)
            table.add_column("Path", justify="left", style="white", max_width=80)
            table.add_column("Reason", justify="left", style="yellow")

            console.print(f"[bold]Total Excluded Items: {len(all_excluded)}[/]")
            for path_obj, reason_val in all_excluded.items():
                item_type, display_path_str, reason_str = self._prepare_excluded_item_display_data(
                    path_obj, reason_val
                )
                display_path_truncated = truncate_path(
                    Path(display_path_str)
                )  # Path() needed if display_path_str is just str
                table.add_row(item_type, display_path_truncated, reason_str)
            console.print(table)
        except ImportError:
            logger.warning("Rich library not installed. Displaying exclusions as plain text.")
            pout("\n--- Excluded Files/Directories ---")
            pout(f"Total Excluded Items: {len(all_excluded)}")
            for path_obj, reason_val in all_excluded.items():
                item_type, display_path_str, reason_str = self._prepare_excluded_item_display_data(
                    path_obj, reason_val
                )
                # Truncate for plain text as well
                if len(display_path_str) > 80:
                    display_path_str = display_path_str[:38] + "..." + display_path_str[-39:]
                pout(f"- [{item_type}] {display_path_str}: {reason_str}")
            pout("--- End of Exclusions ---")

    def generate_exclusion_report(
        self, output_file: Path | str = "exclusion_report.txt"
    ) -> None:  # pragma: no cover
        output_path = Path(output_file)
        all_excluded = self.get_all_exclusions()
        try:
            with output_path.open("w", encoding="utf-8") as report:
                report.write("### Bfiles Exclusion Report ###\n")
                report.write(f"Generated: {datetime.datetime.now().isoformat()}\n")
                report.write(
                    f"Root Directory Scanned: {self.root_dir.as_posix()}\n"
                )  # Use as_posix for consistency
                report.write(f"Total Excluded Items: {len(all_excluded)}\n")
                if self.config.use_gitignore:
                    report.write(f"Items Excluded by .gitignore: {self.get_gitignore_excluded_count()}\n")
                # Add other counts for more detail
                report.write(f"Items Excluded by Config (Files): {self.get_config_excluded_files_count()}\n")
                report.write(f"Items Excluded by Config (Dirs): {self.get_config_excluded_dirs_count()}\n")
                report.write(f"Items Skipped by Limit: {self.get_skipped_by_limit_count()}\n")
                report.write(f"Errors during Scan/Exclusion: {self.get_error_count()}\n")

                report.write("\n--- Excluded Items (Sorted by Path) ---\n")
                if all_excluded:
                    for path_obj, reason_val in all_excluded.items():
                        item_type, display_path_str, reason_str = self._prepare_excluded_item_display_data(
                            path_obj, reason_val
                        )
                        report.write(f"- [{item_type}] {display_path_str}: {reason_str}\n")
                else:
                    report.write("None\n")
                report.write("\n--- End of Report ---")
            logger.info(f"Exclusion report generated successfully at: {output_path}")
        except OSError as e:
            logger.error(f"Failed to write exclusion report to {output_path}: {e}")
        except Exception as e:
            logger.error(f"An unexpected error occurred generating exclusion report: {e}", exc_info=True)


# 🐝📁🔚
