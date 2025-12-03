#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#


from pathlib import Path
import shutil

import pytest

FIXTURES_DIR = Path(__file__).parent
FILES_DIR = FIXTURES_DIR / "files"


@pytest.fixture
def gitignore_project_dir(tmp_path: Path) -> Path:
    """
    Creates a directory structure with nested .gitignore files for exclusion tests

    by copying static files.
    """
    source_dir = FILES_DIR / "gitignore_project"
    dest_dir = tmp_path / "gitignore_proj_setup"  # Name inside tmp_path
    shutil.copytree(source_dir, dest_dir, dirs_exist_ok=True)
    return dest_dir


@pytest.fixture
def include_exclude_project_dir(tmp_path: Path) -> Path:
    """
    Creates a directory structure for testing include/exclude precedence

    by copying static files.
    """
    source_dir = FILES_DIR / "include_exclude_project"
    dest_dir = tmp_path / "include_exclude_proj_setup"  # Name inside tmp_path
    shutil.copytree(source_dir, dest_dir, dirs_exist_ok=True)
    return dest_dir


# 🐝📁🔚
