#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Tests for Unbundler extraction, modes, and force operations."""

from pathlib import Path

from bfiles.unbundler import Unbundler

# --- Unbundler Extraction and Mode Tests ---


def test_unbundler_extract_simple(tmp_path: Path, content_dummy_bundle_valid_str: str):
    bundle_file_path = tmp_path / "dummy_valid_extract.bfiles"
    bundle_file_path.write_text(content_dummy_bundle_valid_str, encoding="utf-8")
    output_dir = tmp_path / "output_extract"
    unbundler = Unbundler(bundle_file_path, output_dir_base=output_dir)

    assert unbundler.extract() is True

    file1 = output_dir / "file1.txt"
    assert file1.exists()
    assert file1.read_text(encoding="utf-8") == "Hello World!\n"

    file2 = output_dir / "path/to/file2.py"
    assert file2.exists()
    assert file2.read_text(encoding="utf-8") == "def main():\n    pass\n"

    empty_file = output_dir / "empty.txt"
    assert empty_file.exists()
    assert empty_file.read_text(encoding="utf-8") == ""  # Expect empty after processing

    chunked_file = output_dir / "chunked_file.dat"
    assert chunked_file.exists()
    assert chunked_file.read_text(encoding="utf-8") == "Part one of data.\nPart two of data.\n"


def test_unbundler_list_only(tmp_path: Path, content_dummy_bundle_valid_str: str, capsys):
    bundle_file_path = tmp_path / "dummy_valid_list.bfiles"
    bundle_file_path.write_text(content_dummy_bundle_valid_str, encoding="utf-8")
    output_dir = tmp_path / "output_list"  # Should not be created
    unbundler = Unbundler(bundle_file_path, output_dir_base=output_dir, list_only=True)

    assert unbundler.extract() is True
    assert not output_dir.exists()

    captured = capsys.readouterr()
    assert "Contents of bundle:" in captured.out
    assert "[+] file1.txt" in captured.out
    assert "[+] path/to/file2.py" in captured.out
    assert "[0] empty.txt" in captured.out
    assert "[C] chunked_file.dat (2 chunks)" in captured.out  # op might be C for chunked file itself


def test_unbundler_dry_run(tmp_path: Path, content_dummy_bundle_valid_str: str, capsys):
    bundle_file_path = tmp_path / "dummy_valid_dryrun.bfiles"
    bundle_file_path.write_text(content_dummy_bundle_valid_str, encoding="utf-8")
    output_dir = tmp_path / "output_dryrun"  # Should not be created, but files "would be" placed here
    unbundler = Unbundler(bundle_file_path, output_dir_base=output_dir, dry_run=True)

    assert unbundler.extract() is True
    assert not output_dir.exists()  # Check no real dirs/files created

    captured = capsys.readouterr()
    # Dry run just prints summary, not individual files
    assert "Dry run complete" in captured.out
    # Should process 4 unique file paths (file1.txt, path/to/file2.py, empty.txt, chunked_file.dat)
    assert "4 unique file paths" in captured.out


def test_unbundler_force_overwrite(tmp_path: Path, content_dummy_bundle_valid_str: str):
    bundle_file_path = tmp_path / "dummy_valid_force.bfiles"
    bundle_file_path.write_text(content_dummy_bundle_valid_str, encoding="utf-8")
    output_dir = tmp_path / "output_force"
    output_dir.mkdir()

    # Create a pre-existing file
    pre_existing_file = output_dir / "file1.txt"
    pre_existing_file.write_text("Old content", encoding="utf-8")

    # First, run without force (should skip)
    unbundler_no_force = Unbundler(bundle_file_path, output_dir_base=output_dir, force_overwrite=False)
    assert unbundler_no_force.extract() is True
    assert pre_existing_file.read_text(encoding="utf-8") == "Old content"  # Not overwritten

    # Now, run with force (should overwrite)
    unbundler_force = Unbundler(bundle_file_path, output_dir_base=output_dir, force_overwrite=True)
    assert unbundler_force.extract() is True
    assert pre_existing_file.read_text(encoding="utf-8") == "Hello World!\n"  # Overwritten


def test_unbundler_default_output_dir(tmp_path: Path, content_dummy_bundle_valid_str: str, monkeypatch):
    # To test default output dir creation, we need to ensure the Unbundler's
    # _output_dir_base is effectively None or CWD initially.
    # The CLI passes None if -o is not used.
    # Let's simulate the Unbundler being called with output_dir_base=None

    # Change CWD for this test to isolate default dir creation
    test_run_dir = tmp_path / "test_run_cwd"
    test_run_dir.mkdir()
    monkeypatch.chdir(test_run_dir)

    # Create bundle in this new CWD
    bundle_in_cwd_path = test_run_dir / "dummy_default_dir.bfiles"
    bundle_in_cwd_path.write_text(content_dummy_bundle_valid_str, encoding="utf-8")

    unbundler = Unbundler(bundle_in_cwd_path, output_dir_base=None)  # Simulate no -o from CLI
    assert unbundler.extract() is True

    # Default dir uses bundle_name_stem from *header* if available, then "_unbundled"
    # Header has "dummy_bundle.txt", so stem is "dummy_bundle"
    expected_default_dir = test_run_dir / "dummy_bundle_unbundled"
    assert expected_default_dir.exists()
    assert expected_default_dir.is_dir()
    assert (expected_default_dir / "file1.txt").exists()


# 🐝📁🔚
