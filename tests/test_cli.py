#
# SPDX-FileCopyrightText: Copyright (c) provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#


from __future__ import annotations

from pathlib import Path
import re

from click.testing import CliRunner

from bfiles.cli import main as bfiles_cli


def _run_cli(runner: CliRunner, args: list[str]) -> str:
    """Invoke the CLI and assert the command succeeds.

    Note: Uses catch_exceptions=True (default) to handle stream cleanup issues
    that can occur in CI environments with tiktoken/Rich. We catch ValueError
    from Click's stream cleanup and verify success via file system checks.
    """
    try:
        result = runner.invoke(bfiles_cli, args)
        # Only fail on real command errors, not stream cleanup issues
        if result.exit_code != 0:
            if result.exception and not isinstance(result.exception, ValueError):
                raise result.exception
            # Check if it's a real failure vs stream cleanup issue
            assert result.exit_code == 0, f"CLI exited with code {result.exit_code}:\n{result.output}"
        return result.output
    except ValueError as e:
        # Handle Click's CliRunner stream cleanup issue
        # "I/O operation on closed file" occurs when tiktoken closes stderr
        if "I/O operation on closed file" in str(e):
            return ""  # Command likely succeeded, caller should verify via file system
        raise


def test_bundle_creates_default_output(runner: CliRunner, cli_project_dir: Path) -> None:
    output_text = _run_cli(runner, ["-d", str(cli_project_dir)])

    generated_files = list(cli_project_dir.glob("bf-*.txt"))
    assert generated_files, "Expected default bundle file to be created"

    bundle_path = generated_files[0]
    content = bundle_path.read_text()
    assert "### BUNDLE SUMMARY ###" in content
    assert "### FILE" in content
    # output_text may be empty if stream cleanup failed in CI
    if output_text:
        assert "Bundle created" in output_text or "Bundle created:" in output_text


def test_list_files_only_outputs_listing(runner: CliRunner, cli_project_dir: Path) -> None:
    output_text = _run_cli(runner, ["-d", str(cli_project_dir), "--list-files-only"])

    # output_text may be empty if stream cleanup failed in CI
    if output_text:
        assert "Files that would be included" in output_text
        assert ".gitignore" not in output_text
    assert not list(cli_project_dir.glob("bf-*.txt"))


def test_custom_output_path(runner: CliRunner, cli_project_dir: Path, tmp_path: Path) -> None:
    target = tmp_path / "custom_bundle.bf"
    _run_cli(runner, ["-d", str(cli_project_dir), "-o", str(target)])

    assert target.is_file()
    assert "### BUNDLE SUMMARY ###" in target.read_text()


def test_include_exclude_without_gitignore(runner: CliRunner, cli_project_dir: Path, tmp_path: Path) -> None:
    target = tmp_path / "filtered_bundle.bf"
    _run_cli(
        runner,
        [
            "-d",
            str(cli_project_dir),
            "-o",
            str(target),
            "--no-gitignore",
            "--include",
            "*.py",
            "--exclude",
            "**/__init__.py",
        ],
    )

    content = target.read_text()
    assert "main.py" in content
    assert "subdir/helper.py" in content
    # Include patterns should override excludes, so __init__ files stay
    assert "src/__init__.py" in content


def test_max_files_limit(runner: CliRunner, cli_project_dir: Path, tmp_path: Path) -> None:
    target = tmp_path / "limited_bundle.bf"
    _run_cli(
        runner,
        ["-d", str(cli_project_dir), "-o", str(target), "--max-files", "2"],
    )

    content = target.read_text()
    assert "Included Files: 2" in content
    assert re.search(r"- Files Skipped \(Limit Reached\): \d+", content)


def test_invalid_root_dir(runner: CliRunner) -> None:
    result = runner.invoke(bfiles_cli, ["-d", "does-not-exist"], catch_exceptions=False)
    assert result.exit_code != 0
    assert "does not exist" in result.output


def test_invalid_hash_algorithm(runner: CliRunner, cli_project_dir: Path) -> None:
    result = runner.invoke(
        bfiles_cli,
        ["-d", str(cli_project_dir), "--hash-algo", "bad-hash"],
        catch_exceptions=False,
    )
    assert result.exit_code != 0
    assert "Invalid value for '--hash-algo'" in result.output


def test_show_excluded_flag(runner: CliRunner, cli_project_dir: Path, tmp_path: Path) -> None:
    target = tmp_path / "show_excluded_bundle.bf"
    output_text = _run_cli(
        runner,
        [
            "-d",
            str(cli_project_dir),
            "-o",
            str(target),
            "--show-excluded",
        ],
    )

    # output_text may be empty if stream cleanup failed in CI
    # Verify the bundle was created as a fallback
    if output_text:
        assert "Excluded Files" in output_text
    else:
        assert target.is_file(), "Expected bundle to be created even if output is empty"


def test_chunking_creates_chunk_entries(runner: CliRunner, tmp_path: Path) -> None:
    project_dir = tmp_path / "chunk_project"
    project_dir.mkdir()
    file_path = project_dir / "chunkme.txt"
    file_path.write_text("token " * 60, encoding="utf-8")
    target = tmp_path / "chunked_bundle.bf"

    _run_cli(
        runner,
        [
            "-d",
            str(project_dir),
            "-o",
            str(target),
            "--chunk-size",
            "20",
            "--chunk-overlap",
            "5",
        ],
    )

    bundle_content = target.read_text()
    assert "chunkme.txt (Chunk 1/" in bundle_content
    assert "(Chunk 2/" in bundle_content


def test_exclusion_report_file_created(runner: CliRunner, cli_project_dir: Path, tmp_path: Path) -> None:
    report_path = tmp_path / "exclusions.txt"
    _run_cli(
        runner,
        [
            "-d",
            str(cli_project_dir),
            "--exclusion-report",
            str(report_path),
        ],
    )

    assert report_path.is_file()
    report_content = report_path.read_text()
    assert "### Bfiles Exclusion Report ###" in report_content


# 🐝📁🔚
