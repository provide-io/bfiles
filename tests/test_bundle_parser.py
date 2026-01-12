#
# SPDX-FileCopyrightText: Copyright (c) provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Tests for BundleParser class."""

from pathlib import Path

import pytest

from bfiles.errors import BundleParseError
from bfiles.parser import BundleParser

# --- BundleParser Tests ---


def test_bundle_parser_valid_bundle(tmp_path: Path, content_dummy_bundle_valid_str: str):
    bundle_file_path = tmp_path / "test_bundle.bfiles"
    bundle_file_path.write_text(content_dummy_bundle_valid_str, encoding="utf-8")
    parser = BundleParser(bundle_file_path)
    assert parser.parse() is True

    assert parser.header is not None
    assert parser.header.original_bundle_name == "dummy_bundle.txt"
    assert parser.header.comment == "This is a valid test bundle."
    assert parser.header.config_options.get("hash") == "sha256"

    assert len(parser.file_entries) == 5

    entry1 = parser.file_entries[0]
    assert entry1.relative_path == "file1.txt"
    assert entry1.content == "Hello World!\n"
    assert entry1.metadata_dict.get("op") == "+"
    assert not entry1.is_chunk

    entry2 = parser.file_entries[1]
    assert entry2.relative_path == "path/to/file2.py"
    assert entry2.content == "def main():\n    pass\n"

    entry3 = parser.file_entries[2]  # empty.txt
    assert entry3.relative_path == "empty.txt"
    # The parser currently includes the newline if the bundle has BOF \n EOF for empty files
    assert entry3.content == "\n"
    assert entry3.metadata_dict.get("op") == "0"

    entry4 = parser.file_entries[3]  # chunked_file.dat part 1
    assert entry4.relative_path == "chunked_file.dat"
    assert entry4.is_chunk
    assert entry4.chunk_num == 1
    assert entry4.total_chunks == 2
    assert entry4.content == "Part one of data.\n"

    entry5 = parser.file_entries[4]  # chunked_file.dat part 2
    assert entry5.relative_path == "chunked_file.dat"
    assert entry5.is_chunk
    assert entry5.chunk_num == 2
    assert entry5.total_chunks == 2
    assert entry5.content == " data.Part two of data.\n"  # Parser reads the raw content from fixture

    assert parser.footer_lines is not None
    assert "--- END OF BFILE dummy_bundle.txt ---" in parser.footer_lines[-1]


def test_bundle_parser_malformed_missing_eof(tmp_path: Path, content_malformed_bundle_missing_eof_str: str):
    """Test that parser correctly handles bundles with missing EOF marker."""
    bundle_file_path = tmp_path / "malformed_missing_eof.bfiles"
    bundle_file_path.write_text(content_malformed_bundle_missing_eof_str, encoding="utf-8")
    parser = BundleParser(bundle_file_path)
    # Parser should return False for malformed bundles (logs error internally)
    assert parser.parse() is False


def test_bundle_parser_malformed_bad_meta(tmp_path: Path, content_malformed_bundle_bad_meta_str: str):
    """Test that parser correctly handles bundles with malformed metadata."""
    bundle_file_path = tmp_path / "malformed_meta.bfiles"
    bundle_file_path.write_text(content_malformed_bundle_bad_meta_str, encoding="utf-8")
    parser = BundleParser(bundle_file_path)
    # Parser should return False for malformed bundles (logs error internally)
    assert parser.parse() is False


def test_bundle_parser_file_not_found(tmp_path: Path):
    """Test that parser raises BundleParseError for non-existent files."""
    parser = BundleParser(tmp_path / "non_existent_bundle.bfiles")
    # Parser now raises BundleParseError (wrapping FileNotFoundError)
    with pytest.raises(BundleParseError, match="Bundle file not found"):
        parser.parse()


# 🐝📁🔚
