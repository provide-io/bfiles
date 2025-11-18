#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""TODO: Add module docstring."""

from pathlib import Path
import re

import pytest

from bfiles.config import (
    DEFAULT_ENCODING,
    DEFAULT_HASH_ALGORITHM,
    DEFAULT_METADATA_TEMPLATE,
    BfilesConfig,
    ExcludePattern,
    _get_default_exclude_patterns,
)
from bfiles.errors import InvalidPathError


def test_config_defaults_no_output(default_config_no_output: BfilesConfig):
    config = default_config_no_output
    assert config.output_file is None
    assert config.encoding == DEFAULT_ENCODING
    assert config.hash_algorithm == DEFAULT_HASH_ALGORITHM
    assert config.metadata_template == DEFAULT_METADATA_TEMPLATE
    assert config.show_excluded is False
    assert config.max_files is None
    assert config.use_gitignore is True
    assert config.list_files_only is False

    expected_excludes = set(_get_default_exclude_patterns())
    assert set(config.exclude_patterns) == expected_excludes


def test_config_defaults_with_output(tmp_path: Path):
    output_path = tmp_path / "default_out.txt"
    config = BfilesConfig(output_file=output_path, root_dir=tmp_path)

    assert isinstance(config.output_file, Path)
    assert config.output_file == output_path.resolve()
    assert config.encoding == DEFAULT_ENCODING
    assert config.hash_algorithm == DEFAULT_HASH_ALGORITHM
    assert config.use_gitignore is True

    expected_excludes = set(_get_default_exclude_patterns())
    expected_excludes.add(str(output_path.resolve()))
    assert set(config.exclude_patterns) == expected_excludes


def test_config_overrides(tmp_path: Path):
    output_path = tmp_path / "my_bundle.bfile"
    custom_excludes: list[ExcludePattern] = ["*.log", r"\.tmp$", re.compile("__pycache__")]
    config = BfilesConfig(
        root_dir=tmp_path,
        output_file=output_path,
        encoding="latin-1",
        hash_algorithm="md5",
        exclude_patterns=list(custom_excludes),
        metadata_template="FILE: {file_path} | {metadata}",
        show_excluded=True,
        max_files=100,
        use_gitignore=False,
    )

    assert isinstance(config.output_file, Path)
    assert config.output_file == output_path.resolve()
    assert config.encoding == "latin-1"
    assert config.hash_algorithm == "md5"
    assert config.metadata_template == "FILE: {file_path} | {metadata}"
    assert config.show_excluded is True
    assert config.max_files == 100
    assert config.use_gitignore is False

    expected_final_patterns = set(custom_excludes)
    expected_final_patterns.add(str(output_path.resolve()))
    assert set(config.exclude_patterns) == expected_final_patterns


def test_config_output_file_path_conversion(tmp_path: Path):
    output_path_obj = tmp_path / "string_path.txt"
    expected_resolved_path = output_path_obj.resolve()
    config = BfilesConfig(output_file=output_path_obj, root_dir=tmp_path)
    assert isinstance(config.output_file, Path)
    assert config.output_file == expected_resolved_path


def test_config_invalid_max_files_type():
    with pytest.raises(TypeError):
        BfilesConfig(max_files="not-an-int", output_file=Path("dummy.txt"))  # type: ignore


def test_config_invalid_exclude_pattern_type():
    with pytest.raises(TypeError):
        BfilesConfig(exclude_patterns=[".log", 123], output_file=Path("dummy.txt"))  # type: ignore


def test_config_invalid_exclude_patterns_container():
    with pytest.raises(TypeError):
        BfilesConfig(exclude_patterns=(".log", "*.tmp"), output_file=Path("dummy.txt"))  # type: ignore


def test_config_invalid_output_file_type():
    with pytest.raises(TypeError, match="Cannot convert value"):
        BfilesConfig(output_file=123)  # type: ignore


def test_config_root_dir_not_found():
    with pytest.raises(InvalidPathError, match=r"Root directory .* not found"):
        BfilesConfig(root_dir="non_existent_directory_xyz_sync", output_file=None)


def test_config_root_dir_is_file(tmp_path: Path):
    file_path = tmp_path / "i_am_a_file_sync.txt"
    file_path.touch()
    with pytest.raises(InvalidPathError, match=r"Root path .* is not a directory"):
        BfilesConfig(root_dir=file_path, output_file=None)


def test_config_post_init_adds_output_file_exclusion(tmp_path: Path):
    output_path = tmp_path / "specific_bundle_sync.txt"
    initial_excludes = ["*.log", ".git/"]
    config = BfilesConfig(
        root_dir=tmp_path, output_file=output_path, exclude_patterns=list(initial_excludes)
    )
    expected_final_excludes = set(initial_excludes)
    expected_final_excludes.add(str(output_path.resolve()))
    assert set(config.exclude_patterns) == expected_final_excludes


def test_config_post_init_skips_add_if_literal_match(tmp_path: Path):
    output_path = tmp_path / "bundle_v2_sync.txt"
    resolved_output_str = str(output_path.resolve())
    initial_excludes = ["*.log", resolved_output_str]
    config = BfilesConfig(
        root_dir=tmp_path, output_file=output_path, exclude_patterns=list(initial_excludes)
    )
    assert resolved_output_str in config.exclude_patterns or any(
        isinstance(p, str)
        and Path(p).resolve(strict=False) == Path(resolved_output_str).resolve(strict=False)
        for p in config.exclude_patterns
    )


def test_config_post_init_handles_none_output_file():
    initial_excludes = ["*.log", ".git/"]
    config = BfilesConfig(output_file=None, exclude_patterns=list(initial_excludes))
    assert set(config.exclude_patterns) == set(initial_excludes)


# 🐝📁🔚
