#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Tests for Unbundler chunk overlap and reassembly."""

from pathlib import Path

from bfiles.unbundler import Unbundler

# --- Unbundler Chunk Overlap Tests ---


def test_unbundler_chunk_overlap_match(tmp_path: Path, content_bundle_overlap_match_str: str):
    # This test uses the original content_bundle_overlap_match_str fixture which is a bit complex.
    # The more precise test is the one below using content_for_overlap_test.
    # We can keep this as a broader test if the fixture is well-defined or simplify/remove it.
    # For now, let's focus on the clear ASCII one.
    # So, I'll use the content_for_overlap_test directly here.

    output_dir = tmp_path / "output_overlap_match"

    content_for_overlap_test = """--- START OF BFILE overlap_exact.txt ---
---
### FILE 1: data.txt (Chunk 1/3) | op=C ###
<<< BOF <<<
AAAAAAAAAABBBBBBBBBB
>>> EOF >>>

### FILE 2: data.txt (Chunk 2/3) | op=C; overlap_prev=10 ###
<<< BOF <<<
BBBBBBBBBBCCCCCCCCCC
>>> EOF >>>

### FILE 3: data.txt (Chunk 3/3) | op=C; overlap_prev=10 ###
<<< BOF <<<
CCCCCCCCCCDDDDDDDDDD
>>> EOF >>>
"""
    bundle_path = tmp_path / "overlap_exact.bfiles"
    bundle_path.write_text(content_for_overlap_test, encoding="utf-8")

    unbundler = Unbundler(bundle_path, output_dir_base=output_dir)
    assert unbundler.extract() is True
    reassembled_file = output_dir / "data.txt"
    assert reassembled_file.exists()
    assert reassembled_file.read_text(encoding="utf-8") == "AAAAAAAAAABBBBBBBBBB\nCCCCCCCCCC\nDDDDDDDDDD\n"


def test_unbundler_chunk_overlap_mismatch(tmp_path: Path, content_bundle_overlap_mismatch_str: str):
    """Test chunk reassembly when overlap bytes don't match (falls back to full concatenation)."""
    bundle_file_path = tmp_path / "overlap_mismatch.bfiles"
    bundle_file_path.write_text(content_bundle_overlap_mismatch_str, encoding="utf-8")
    output_dir = tmp_path / "output_overlap_mismatch"
    unbundler = Unbundler(bundle_file_path, output_dir_base=output_dir)

    # Should complete extraction (logs warning internally about mismatch)
    assert unbundler.extract() is True

    reassembled_file = output_dir / "mismatch.txt"
    assert reassembled_file.exists()
    # Expect full concatenation due to mismatch (fallback behavior)
    expected_content = "This is the first part.\nXXXXXThis is the second part.\n"
    assert reassembled_file.read_text(encoding="utf-8") == expected_content


def test_unbundler_chunk_overlap_content_too_short(
    tmp_path: Path, content_bundle_overlap_short_chunk_str: str
):
    """Test chunk reassembly when chunk content is shorter than declared overlap."""
    bundle_file_path = tmp_path / "overlap_short.bfiles"
    bundle_file_path.write_text(content_bundle_overlap_short_chunk_str, encoding="utf-8")
    output_dir = tmp_path / "output_overlap_short"
    unbundler = Unbundler(bundle_file_path, output_dir_base=output_dir)

    # Should complete extraction (logs warning internally about size mismatch)
    assert unbundler.extract() is True

    reassembled_file = output_dir / "short_chunk.txt"
    assert reassembled_file.exists()
    # Expect full concatenation when chunk is too short for overlap
    expected_content = "This is a long first part to establish overlap bytes.\nshort\n"
    assert reassembled_file.read_text(encoding="utf-8") == expected_content


def test_unbundler_chunk_zero_overlap(tmp_path: Path, content_bundle_zero_overlap_str: str, caplog):
    bundle_file_path = tmp_path / "zero_overlap.bfiles"
    bundle_file_path.write_text(content_bundle_zero_overlap_str, encoding="utf-8")
    output_dir = tmp_path / "output_zero_overlap"
    unbundler = Unbundler(bundle_file_path, output_dir_base=output_dir)
    assert unbundler.extract() is True

    reassembled_file = output_dir / "zero.txt"
    assert reassembled_file.exists()
    expected_content = "First part.\nSecond part.\n"
    assert reassembled_file.read_text() == expected_content
    # No warning should be logged for overlap_prev=0
    assert "Overlap mismatch" not in caplog.text
    assert "Content shorter than overlap_bytes_prev" not in caplog.text


# 🐝📁🔚
