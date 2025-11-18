#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""TODO: Add module docstring."""

from pathlib import Path
import shutil

from click.testing import CliRunner
import pytest

FIXTURES_DIR = Path(__file__).parent
FILES_DIR = FIXTURES_DIR / "files"


@pytest.fixture(scope="module")
def runner() -> CliRunner:
    """Provides a Click CliRunner instance."""
    return CliRunner()


@pytest.fixture
def cli_project_dir(tmp_path: Path) -> Path:
    """
    Creates a sample project directory structure for CLI tests

    by copying static files.
    """
    source_dir = FILES_DIR / "cli_project"
    dest_dir = tmp_path / "sample_proj_cli"  # Keep consistent with copy dest name

    # Copy the base structure
    shutil.copytree(
        source_dir, dest_dir, dirs_exist_ok=True, symlinks=True
    )  # Copy symlinks if possible

    # Explicitly create symlink within the *destination* directory
    link_path = dest_dir / "link_to_readme"
    target_name = "README.md"  # Relative link target within dest_dir
    target_path = dest_dir / target_name

    # Remove the file if it was copied, we need a symlink here
    if link_path.exists():
        link_path.unlink()

    if target_path.exists():
        # Check if target exists before creating link
        try:
            link_path.symlink_to(target_name)  # Create relative link
        except OSError as e:  # pragma: no cover
            pytest.skip(f"Could not create symlink 'link_to_readme': {e}")

    return dest_dir


# 🐝📁🔚
