#
# SPDX-FileCopyrightText: Copyright (c) provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#


from pathlib import Path
import shutil

import pytest

from bfiles.config import BfilesConfig
from bfiles.exclusions import ExclusionManager

FIXTURES_DIR = Path(__file__).parent
FILES_DIR = FIXTURES_DIR / "files"


@pytest.fixture
def core_project_dir(tmp_path: Path) -> Path:
    """
    Creates a basic directory structure for core logic tests

    by copying static files.
    """
    source_dir = FILES_DIR / "core_project"
    dest_dir = tmp_path / "core_proj_setup"  # Name inside tmp_path

    # Copy the base structure
    shutil.copytree(source_dir, dest_dir, dirs_exist_ok=True, symlinks=True)

    # Explicitly create directory symlink within the *destination* directory
    link_path = dest_dir / "link_to_dir"
    target_dir_name = "link_target"  # Relative path to target dir
    target_path = dest_dir / target_dir_name

    if not link_path.exists() and target_path.is_dir():
        try:
            link_path.symlink_to(target_dir_name, target_is_directory=True)
        except OSError as e:  # pragma: no cover
            pytest.skip(f"Could not create symlink 'link_to_dir': {e}")

    return dest_dir


@pytest.fixture
def basic_config(core_project_dir: Path, tmp_path: Path) -> BfilesConfig:
    """Basic config pointing to the core_project_dir."""
    output = tmp_path / "bundle_core_test.txt"
    # Note: Default excludes (like .*) from BfilesConfig will apply here.
    return BfilesConfig(root_dir=core_project_dir, output_file=output)


@pytest.fixture
def exclusion_manager(basic_config: BfilesConfig) -> ExclusionManager:
    """Basic ExclusionManager instance based on basic_config."""
    # Ensure config has been processed if needed before manager init
    return ExclusionManager(basic_config)


# 🐝📁🔚
