#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#


from pathlib import Path
import re
from typing import TypeAlias

import attrs
from provide.foundation import logger
from provide.foundation.config.base import BaseConfig, field

from bfiles.errors import ConfigurationError, InvalidPathError

ExcludePattern: TypeAlias = str | re.Pattern[str]
IncludePattern: TypeAlias = str

DEFAULT_ENCODING = "utf-8"
DEFAULT_HASH_ALGORITHM = "sha256"
DEFAULT_EXCLUDE_PATTERNS: list[ExcludePattern] = [
    ".*",
    r"\.py[co]$",
    ".git/",
    ".venv/",
    "venv/",
    r"(^|/)\.env$",
    "bin/",
    "obj/",
    "build/",
    "dist/",
    "node_modules/",
    "__pycache__/",
    "*.log",
    "*.tmp",
    "*.swp",
    "*bfiles*.txt",
    "*.bf.txt",
]
DEFAULT_METADATA_TEMPLATE = "### FILE {file_num}: {file_path} | {metadata} ###"


def _get_default_exclude_patterns() -> list[ExcludePattern]:
    return list(DEFAULT_EXCLUDE_PATTERNS)


def _convert_optional_path(value: str | Path | None) -> Path | None:
    if value is None:
        return None
    if isinstance(value, Path):
        return value
    try:
        return Path(value)
    except TypeError as e:
        raise TypeError(f"Cannot convert value of type {type(value)} to Path or None.") from e


@attrs.define(kw_only=True, slots=True)
class BfilesConfig(BaseConfig):
    root_dir: Path = field(  # noqa: RUF009
        default=Path(),
        converter=Path,
        validator=attrs.validators.instance_of(Path),
        description="Root directory to bundle",
        env_var="BFILES_ROOT_DIR",
    )
    output_file: Path | None = field(  # noqa: RUF009
        default=None,
        converter=_convert_optional_path,
        validator=attrs.validators.optional(attrs.validators.instance_of(Path)),
        description="Output bundle file path",
        env_var="BFILES_OUTPUT",
    )
    encoding: str = field(
        default=DEFAULT_ENCODING,
        description="File encoding to use",
        env_var="BFILES_ENCODING",
    )
    hash_algorithm: str = field(
        default=DEFAULT_HASH_ALGORITHM,
        validator=attrs.validators.instance_of(str),
        description="Hash algorithm for checksums",
        env_var="BFILES_HASH_ALGORITHM",
    )
    include_patterns: list[IncludePattern] = field(  # noqa: RUF009
        factory=list,
        validator=attrs.validators.deep_iterable(
            member_validator=attrs.validators.instance_of(str),
            iterable_validator=attrs.validators.instance_of(list),
        ),
        description="Patterns to explicitly include",
    )
    exclude_patterns: list[ExcludePattern] = field(  # noqa: RUF009
        factory=_get_default_exclude_patterns,
        validator=attrs.validators.deep_iterable(
            member_validator=attrs.validators.instance_of((str, re.Pattern)),
            iterable_validator=attrs.validators.instance_of(list),
        ),
        description="Patterns to exclude",
    )
    use_gitignore: bool = field(
        default=True,
        description="Use .gitignore patterns",
        env_var="BFILES_USE_GITIGNORE",
    )
    follow_symlinks: bool = field(
        default=False,
        description="Follow symbolic links",
        env_var="BFILES_FOLLOW_SYMLINKS",
    )
    max_files: int | None = field(
        default=None,
        validator=attrs.validators.optional(attrs.validators.instance_of(int)),
        description="Maximum files to bundle",
        env_var="BFILES_MAX_FILES",
    )
    list_files_only: bool = field(
        default=False,
        description="Only list files, don't bundle",
    )
    metadata_template: str = field(
        default=DEFAULT_METADATA_TEMPLATE,
        description="Template for file metadata headers",
    )
    show_excluded: bool = field(
        default=False,
        description="Show excluded files report",
    )
    header_comment: str | None = field(
        default=None,
        validator=attrs.validators.optional(attrs.validators.instance_of(str)),
        description="Custom header comment",
    )
    chunk_size: int | None = field(
        default=None,
        description="Token-based chunk size",
        env_var="BFILES_CHUNK_SIZE",
    )
    chunk_overlap: int = field(
        default=0,
        description="Token overlap between chunks",
        env_var="BFILES_CHUNK_OVERLAP",
    )
    allow_unsafe: bool = field(
        default=False,
        description="Allow inclusion of files with terminal-breaking control characters",
        env_var="BFILES_ALLOW_UNSAFE",
    )
    sanitize_unsafe: bool = field(
        default=False,
        description="Sanitize dangerous control characters before including files",
        env_var="BFILES_SANITIZE_UNSAFE",
    )
    show_progress: bool = field(
        default=False,
        description="Show real-time progress during file operations",
        env_var="BFILES_SHOW_PROGRESS",
    )

    def __attrs_post_init__(self) -> None:
        super().__attrs_post_init__()
        self.validate()

    def validate(self) -> None:
        try:
            self.root_dir = self.root_dir.resolve()
            if not self.root_dir.exists():
                raise InvalidPathError(f"Root directory '{self.root_dir}' not found.")
            if not self.root_dir.is_dir():
                raise InvalidPathError(f"Root path '{self.root_dir}' is not a directory.")
        except (OSError, FileNotFoundError) as e:
            raise ConfigurationError(f"Root directory issue: {e}") from e

        # Validate terminal safety flags are mutually exclusive
        if self.allow_unsafe and self.sanitize_unsafe:
            raise ConfigurationError(
                "Cannot use both --allow-unsafe and --sanitize-unsafe flags. "
                "Choose one: allow dangerous characters as-is, or sanitize them."
            )

        if self.output_file is not None:
            if not self.output_file.is_absolute():
                try:
                    self.output_file = self.output_file.resolve()
                except OSError as e:
                    logger.warning(
                        "file.resolve.warning",
                        path=str(self.output_file),
                        error=str(e),
                    )
            output_file_abs_str = str(self.output_file)
            already_excluded = any(
                (isinstance(p, str) and str(Path(p).resolve(strict=False)) == output_file_abs_str)
                or (isinstance(p, str) and p == output_file_abs_str)
                for p in self.exclude_patterns
            )
            if not already_excluded:
                self.exclude_patterns.append(output_file_abs_str)
                logger.debug("config.exclude.output_file", path=output_file_abs_str)
            else:
                logger.debug("config.exclude.already_covered", path=output_file_abs_str)
        else:
            logger.debug("config.output_file.none")
        logger.debug("config.initialized", config=str(self))


# 🐝📁🔚
