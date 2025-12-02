#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""TODO: Add module docstring."""

import logging
from pathlib import Path

import pytest

from bfiles.config import BfilesConfig
from bfiles.exclusions import ExclusionManager


def test_gitignore_basic_exclusions(gitignore_project_dir: Path, tmp_path: Path):
    config = BfilesConfig(
        root_dir=gitignore_project_dir, output_file=tmp_path / "out_sync.txt", use_gitignore=True
    )
    manager = ExclusionManager(config)
    assert manager.is_excluded(gitignore_project_dir / "main.py") is None
    assert manager.is_excluded(gitignore_project_dir / "data.log") == "gitignore"
    assert manager.is_excluded(gitignore_project_dir / "config.ini") == "gitignore"


def test_gitignore_nested_exclusions(gitignore_project_dir: Path, tmp_path: Path):
    config = BfilesConfig(
        root_dir=gitignore_project_dir, output_file=tmp_path / "out_sync.txt", use_gitignore=True
    )
    manager = ExclusionManager(config)
    assert manager.is_excluded(gitignore_project_dir / "sub" / "helper.py") is None
    assert manager.is_excluded(gitignore_project_dir / "sub" / "temp.tmp") == "gitignore"
    assert manager.is_excluded(gitignore_project_dir / "sub" / "sub_data.log") == "gitignore"
    assert manager.is_excluded(gitignore_project_dir / "sub" / "subsub" / "final.py") is None
    assert manager.is_excluded(gitignore_project_dir / "sub" / "subsub" / "deep_config.ini") == "gitignore"


def test_gitignore_disabled(gitignore_project_dir: Path, tmp_path: Path):
    config = BfilesConfig(
        root_dir=gitignore_project_dir, output_file=tmp_path / "out_sync.txt", use_gitignore=False
    )
    manager = ExclusionManager(config)
    assert manager.is_excluded(gitignore_project_dir / "data.log") == "glob"
    assert manager.is_excluded(gitignore_project_dir / "config.ini") is None
    assert manager.is_excluded(gitignore_project_dir / "sub" / "temp.tmp") == "glob"
    assert manager.is_excluded(gitignore_project_dir / "sub" / "helper.py") is None


def test_include_overrides_exclude(include_exclude_project_dir: Path, tmp_path: Path):
    config = BfilesConfig(
        root_dir=include_exclude_project_dir,
        output_file=tmp_path / "out_sync.txt",
        use_gitignore=True,
        include_patterns=["*.py", "*.bak"],
        exclude_patterns=["*.py", "*.txt", "*.bak"],
    )
    manager = ExclusionManager(config)
    assert manager.is_excluded(include_exclude_project_dir / "a.txt") == "glob"
    assert manager.is_excluded(include_exclude_project_dir / "b.py") is None
    assert manager.is_excluded(include_exclude_project_dir / "c.py.bak") is None
    assert manager.is_excluded(include_exclude_project_dir / "d.log") == "gitignore"


def test_gitignore_overrides_include(include_exclude_project_dir: Path, tmp_path: Path):
    config = BfilesConfig(
        root_dir=include_exclude_project_dir,
        output_file=tmp_path / "out_sync.txt",
        use_gitignore=True,
        include_patterns=["*.log"],
        exclude_patterns=["*.txt"],
    )
    manager = ExclusionManager(config)
    assert manager.is_excluded(include_exclude_project_dir / "a.txt") == "glob"
    assert manager.is_excluded(include_exclude_project_dir / "b.py") is None
    assert manager.is_excluded(include_exclude_project_dir / "d.log") == "gitignore"


def test_exclude_precedence_string_regex_glob(include_exclude_project_dir: Path, tmp_path: Path):
    file_to_test = include_exclude_project_dir / "b.py"
    resolved_path_str = str(file_to_test.resolve())
    config_str = BfilesConfig(
        root_dir=include_exclude_project_dir,
        output_file=tmp_path / "out_str_sync.txt",
        exclude_patterns=[resolved_path_str, r"\.py$", "*.py"],
    )
    manager_str = ExclusionManager(config_str)
    assert manager_str.is_excluded(file_to_test) == "string"
    config_re = BfilesConfig(
        root_dir=include_exclude_project_dir,
        output_file=tmp_path / "out_re_sync.txt",
        exclude_patterns=[r"\.py$", "*.py"],
    )
    manager_re = ExclusionManager(config_re)
    assert manager_re.is_excluded(file_to_test) == "regex"
    config_glob = BfilesConfig(
        root_dir=include_exclude_project_dir,
        output_file=tmp_path / "out_glob_sync.txt",
        exclude_patterns=["*.py"],
    )
    manager_glob = ExclusionManager(config_glob)
    assert manager_glob.is_excluded(file_to_test) == "glob"


@pytest.mark.xfail(
    reason=("Platform-specific logging makes capturing the unreadable .gitignore warning unreliable.")
)
def test_unreadable_gitignore_file(tmp_path: Path, caplog):  # Use standard caplog
    """Ensure unreadable .gitignore files emit a warning without crashing.

    The test manipulates permissions and inspects the exclusions logger output.
    """
    project_dir = tmp_path / "unreadable_gitignore_project"
    project_dir.mkdir()

    gitignore_path = project_dir / ".gitignore"
    gitignore_path.write_text("*.log\n")

    original_mode = gitignore_path.stat().st_mode
    unreadable_made = False
    try:
        gitignore_path.chmod(0o000)
        unreadable_made = True
    except OSError as e:  # pragma: no cover
        pytest.skip(f"Could not make .gitignore unreadable (chmod 000 failed): {e}")

    (project_dir / "app.log").touch()
    (project_dir / "app.py").touch()

    bundle_output_dir = tmp_path / "bundle_output"
    bundle_output_dir.mkdir()
    config = BfilesConfig(
        root_dir=project_dir,
        use_gitignore=True,
        output_file=bundle_output_dir / "bundle.out",
        # log_level was incorrectly added here, removed.
    )

    # Get the specific logger instance and set its level for the test
    bfiles_exclusions_logger = logging.getLogger("bfiles.exclusions")
    original_level = bfiles_exclusions_logger.level
    bfiles_exclusions_logger.setLevel(logging.DEBUG)  # Force level for direct logger

    # Also use caplog to capture from this specific logger at DEBUG level
    with caplog.at_level(logging.DEBUG, logger="bfiles.exclusions"):
        em = ExclusionManager(config)

    # Restore original level
    bfiles_exclusions_logger.setLevel(original_level)

    if unreadable_made:
        gitignore_path.chmod(original_mode)  # Restore permissions for cleanup

    found_warning = False
    expected_logger_name = "bfiles.exclusions"
    for record in caplog.records:
        if (
            record.name == expected_logger_name
            and record.levelname == "WARNING"
            and f"Error loading .gitignore file {gitignore_path}" in record.message
            and (
                "Permission denied" in record.message
                or "Errno 13" in record.message
                or "Errno 1" in record.message
            )
        ):
            found_warning = True
            break

    failure_message = (
        f"Expected WARNING log about unreadable .gitignore permissions. Actual logs:\n{caplog.text}"
    )
    assert found_warning, failure_message

    # Since .gitignore was unreadable, its rules should not apply.
    assert em.is_excluded(project_dir / "app.log") is None, (
        "Expected app.log to remain included when .gitignore rules cannot be read."
    )
    assert em.is_excluded(project_dir / "app.py") is None


# 🐝📁🔚
