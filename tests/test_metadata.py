#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""TODO: Add module docstring."""

import hashlib  # For hash checks
from pathlib import Path

import pytest

from bfiles.config import BfilesConfig
from bfiles.metadata import BundleSummary, FileMetadata  # Corrected import
from bfiles.utils import compute_file_hash, get_file_subtype


def test_filemetadata_from_path_basic_file(default_config_no_output: BfilesConfig, tmp_path: Path):
    config = default_config_no_output
    config.root_dir = tmp_path  # Point config to tmp_path for this test

    test_file = tmp_path / "regular.txt"
    content = "Hello Metadata!"
    test_file.write_text(content)

    meta = FileMetadata.from_path(test_file, config)

    assert meta.path == test_file.resolve()
    assert meta.size == len(content.encode())
    assert meta.file_type == "plain"  # Based on .txt from get_file_subtype
    assert meta.checksum == hashlib.sha256(content.encode()).hexdigest()
    assert meta.operation == "included"  # Default for non-empty


def test_filemetadata_from_path_empty_file(default_config_no_output: BfilesConfig, tmp_path: Path):
    config = default_config_no_output
    config.root_dir = tmp_path
    empty_file = tmp_path / "empty.dat"
    empty_file.touch()

    meta = FileMetadata.from_path(empty_file, config)

    assert meta.path == empty_file.resolve()
    assert meta.size == 0
    assert meta.file_type is None  # Empty files have no type in this version
    assert meta.checksum is None  # Empty files have no checksum
    assert meta.operation == "empty"


def test_filemetadata_from_path_symlink_not_followed(
    default_config_no_output: BfilesConfig, tmp_path: Path
):
    config = default_config_no_output
    config.root_dir = tmp_path
    config.follow_symlinks = False  # Explicitly set for clarity

    target_file = tmp_path / "target.txt"
    target_file.write_text("symlink target content")
    link_file = tmp_path / "link.lnk"
    link_file.symlink_to("target.txt")  # Relative link

    meta = FileMetadata.from_path(link_file, config)  # Path to link itself

    # FileMetadata.from_path always stats the target of a symlink when encountered.
    # BfilesConfig.follow_symlinks affects collection, not this direct call.
    assert meta.path == target_file.resolve()  # meta.path is resolved target
    assert meta.size == target_file.stat().st_size  # meta.size is target's size

    assert meta.checksum == compute_file_hash(target_file, config.hash_algorithm)
    assert meta.file_type == get_file_subtype(target_file)
    assert meta.token_count is not None  # Assuming target content is tokenizable
    assert meta.operation == "included"  # Target is included


def test_filemetadata_from_path_symlink_followed(
    default_config_no_output: BfilesConfig, tmp_path: Path
):
    config = default_config_no_output
    config.root_dir = tmp_path
    config.follow_symlinks = True  # Enable following

    target_file = tmp_path / "target_follow.txt"
    target_content = "followed target content"
    target_file.write_text(target_content)
    link_file = tmp_path / "link_follow.lnk"
    link_file.symlink_to("target_follow.txt")

    meta = FileMetadata.from_path(link_file, config)  # Path to link, but it's followed

    assert meta.path == target_file.resolve()  # Path should be the target's
    assert meta.size == len(target_content.encode())
    assert meta.checksum == hashlib.sha256(target_content.encode()).hexdigest()
    assert meta.operation == "included"


def test_filemetadata_from_path_file_not_found(
    default_config_no_output: BfilesConfig, tmp_path: Path
):
    config = default_config_no_output
    config.root_dir = tmp_path
    non_existent_file = tmp_path / "ghost.txt"

    with pytest.raises(ValueError, match="File not found"):
        FileMetadata.from_path(non_existent_file, config)


def test_bundlesummary_initialization():  # Added test for BundleSummary
    summary = BundleSummary()
    assert summary.total_files_discovered == 0
    assert summary.files_added_to_bundle == 0
    assert summary.total_excluded_count == 0
    assert summary.total_bundle_size_bytes == 0


# 🐝📁🔚
