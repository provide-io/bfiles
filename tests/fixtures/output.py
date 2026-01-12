#
# SPDX-FileCopyrightText: Copyright (c) provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#


import datetime
from pathlib import Path
import shutil

import pytest

from bfiles.config import BfilesConfig
from bfiles.metadata import FileMetadata

FIXTURES_DIR = Path(__file__).parent
FILES_DIR = FIXTURES_DIR / "files"


@pytest.fixture
def output_project_root(tmp_path: Path) -> Path:
    """
    Creates a minimal root directory needed for output config/metadata tests.

    Copies the 'core_project' structure as it contains needed files.
    """
    source_dir = FILES_DIR / "core_project"  # Reuse core structure for simplicity
    dest_dir = tmp_path / "output_proj_root"
    shutil.copytree(source_dir, dest_dir, dirs_exist_ok=True)
    return dest_dir


@pytest.fixture
def sample_metadata(output_project_root: Path) -> list[FileMetadata]:
    """Creates a list of sample FileMetadata objects relative to output_project_root."""
    now = datetime.datetime.now(datetime.UTC)
    root = output_project_root  # Use the copied directory root

    # Ensure paths exist for FileMetadata creation (even if empty/dummy)
    (root / "file1.py").touch()  # Was file1.txt in core, change ext for test
    (root / "sub").mkdir(exist_ok=True)
    (root / "sub" / "file2.txt").touch()
    (root / "excluded.log").touch()
    (root / "empty.dat").touch()
    (root / "duplicate_target.src").write_text("content output")  # Make content different
    (root / "duplicate_link.src").write_text("content output")  # Duplicate content
    (root / "skipped.cfg").touch()
    (root / "error.bin").touch()  # File for simulating error state
    (root / "chunked_file.txt").touch()  # File for chunking info test

    # Create metadata pointing to files within the output_project_root fixture
    return [
        FileMetadata(
            path=(root / "file1.py").resolve(),
            size=100,
            modified=now,
            file_type="x-python",
            checksum="abcoutput",
            operation="included",
            token_count=50,
        ),
        FileMetadata(
            path=(root / "sub" / "file2.txt").resolve(),
            size=200,
            modified=now,
            file_type="plain",
            checksum="defoutput",
            operation="included",
            token_count=100,
        ),
        FileMetadata(
            path=(root / "excluded.log").resolve(),
            size=50,
            modified=now,
            file_type="plain",
            checksum="ghioutput",
            operation="excluded",
            token_count=20,
        ),
        FileMetadata(
            path=(root / "empty.dat").resolve(),
            size=0,
            modified=now,
            file_type=None,
            checksum=None,
            operation="empty",
            token_count=0,
        ),
        FileMetadata(
            path=(root / "duplicate_link.src").resolve(),
            size=14,
            modified=now,
            file_type="plain",
            checksum="jkloutput",
            operation="duplicate",
            original=(root / "duplicate_target.src").resolve(),
            token_count=7,
        ),
        FileMetadata(
            path=(root / "skipped.cfg").resolve(),
            size=30,
            modified=now,
            file_type="plain",
            checksum="mnooutput",
            operation="skipped",
            token_count=15,
        ),
        FileMetadata(
            path=(root / "error.bin").resolve(),
            size=-1,
            modified=now,
            file_type=None,
            checksum=None,
            operation="error",
            token_count=None,
        ),
        FileMetadata(
            path=(root / "chunked_file.txt").resolve(),
            size=500,
            modified=now,
            file_type="plain",
            checksum="chunkoutput",
            operation="included",
            token_count=250,
            total_chunks=3,
        ),  # Chunked file example
    ]


@pytest.fixture
def output_config_show(output_project_root: Path, tmp_path: Path) -> BfilesConfig:
    """Config with show_excluded=True, using the output_project_root."""
    return BfilesConfig(
        root_dir=output_project_root, output_file=tmp_path / "out_show.txt", show_excluded=True
    )


@pytest.fixture
def output_config_hide(output_project_root: Path, tmp_path: Path) -> BfilesConfig:
    """Config with show_excluded=False (default), using the output_project_root."""
    return BfilesConfig(
        root_dir=output_project_root,
        output_file=tmp_path / "out_hide.txt",
        show_excluded=False,  # Default, but explicit here
    )


# 🐝📁🔚
