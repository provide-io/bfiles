#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""TODO: Add module docstring."""

from __future__ import annotations

from pathlib import Path
import re

from click.testing import CliRunner

from bfiles.cli import main as bfiles_cli


def _run_cli(runner: CliRunner, args: list[str]) -> str:
    """Invoke the CLI and assert the command succeeds."""
    result = runner.invoke(bfiles_cli, args, catch_exceptions=False)
    assert result.exit_code == 0, f"CLI exited with code {result.exit_code}:\n{result.output}"
    return result.output


def test_bundle_creates_default_output(runner: CliRunner, cli_project_dir: Path) -> None:
    output_text = _run_cli(runner, ["-d", str(cli_project_dir)])

    generated_files = list(cli_project_dir.glob("bf-*.txt"))
    assert generated_files, "Expected default bundle file to be created"

    bundle_path = generated_files[0]
    content = bundle_path.read_text()
    assert "### BUNDLE SUMMARY ###" in content
    assert "### FILE" in content
    assert "Bundle created" in output_text or "Bundle created:" in output_text


def test_list_files_only_outputs_listing(runner: CliRunner, cli_project_dir: Path) -> None:
    output_text = _run_cli(runner, ["-d", str(cli_project_dir), "--list-files-only"])

    assert "Files that would be included" in output_text
    assert ".gitignore" not in output_text
    assert not list(cli_project_dir.glob("bf-*.txt"))


def test_custom_output_path(runner: CliRunner, cli_project_dir: Path, tmp_path: Path) -> None:
    target = tmp_path / "custom_bundle.bf"
    _run_cli(runner, ["-d", str(cli_project_dir), "-o", str(target)])

    assert target.is_file()
    assert "### BUNDLE SUMMARY ###" in target.read_text()


def test_include_exclude_without_gitignore(
    runner: CliRunner, cli_project_dir: Path, tmp_path: Path
) -> None:
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

    assert "Excluded Files" in output_text


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


def test_exclusion_report_file_created(
    runner: CliRunner, cli_project_dir: Path, tmp_path: Path
) -> None:
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
