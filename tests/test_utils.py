#
# SPDX-FileCopyrightText: Copyright (c) provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#


import hashlib
from pathlib import Path
import sys

import pytest

from bfiles.utils import (
    compute_file_hash,  # Corrected import
    get_file_subtype,
    get_mime_type,
    is_utf8_file,
)


def test_compute_file_hash_sha256_success_sync(tmp_path: Path):
    file_content = b"Hello, bfiles sync!"
    test_file = tmp_path / "test_sync_sha256.txt"
    test_file.write_bytes(file_content)
    expected_hash = hashlib.sha256(file_content).hexdigest()
    actual_hash = compute_file_hash(test_file, algorithm="sha256")
    assert actual_hash == expected_hash


def test_compute_file_hash_md5_success_sync(tmp_path: Path):
    file_content = b"Another sync test file content."
    test_file = tmp_path / "test_sync_md5.dat"
    test_file.write_bytes(file_content)
    expected_hash = hashlib.md5(file_content).hexdigest()
    actual_hash = compute_file_hash(test_file, algorithm="md5")
    assert actual_hash == expected_hash


def test_compute_file_hash_empty_file_sync(tmp_path: Path):
    test_file = tmp_path / "empty_sync.txt"
    test_file.touch()
    expected_sha256_empty = hashlib.sha256(b"").hexdigest()
    actual_hash = compute_file_hash(test_file, algorithm="sha256")
    assert actual_hash == expected_sha256_empty


def test_compute_file_hash_file_not_found_sync(tmp_path: Path):
    non_existent_file = tmp_path / "not_a_file_sync.txt"
    with pytest.raises(OSError):  # compute_file_hash re-raises OSError
        compute_file_hash(non_existent_file)


def test_compute_file_hash_unsupported_algorithm_sync(tmp_path: Path):
    test_file = tmp_path / "test_algo_sync.txt"
    test_file.write_text("content")
    with pytest.raises(ValueError, match="Unsupported hash algorithm"):
        compute_file_hash(test_file, algorithm="invalid-algo-sync-123")


@pytest.mark.parametrize(
    "filename, expected_mime, expected_subtype",
    [
        ("test_mime.txt", "text/plain", "plain"),
        ("script_mime.py", "text/x-python", "x-python"),
        ("document_mime.md", "text/markdown", "markdown"),
        ("archive_mime.zip", "application/zip", "zip"),
        ("setup_mime.cfg", "text/plain", "plain"),
        ("Makefile", "text/plain", "plain"),  # Based on updated utils.py
        ("Dockerfile", "text/plain", "plain"),  # Based on updated utils.py
        ("image_mime.jpeg", "image/jpeg", "jpeg"),
        ("no_extension_file_mime", None, None),
        (".hiddenfile_mime", None, None),
        ("data_mime.json", "application/json", "json"),
        ("style_mime.css", "text/css", "css"),
        ("archive_mime.tar.gz", "application/x-tar", "x-tar"),  # mimetypes usually knows this
        ("unknown_mime.xyz", "chemical/x-xyz", "x-xyz"),  # If system mimetypes knows it
        ("really_unknown.unknownextension", None, None),
    ],
)
def test_get_mime_and_subtype_sync(
    tmp_path: Path, filename: str, expected_mime: str | None, expected_subtype: str | None
):
    test_file = tmp_path / filename
    test_file.touch()
    actual_mime = get_mime_type(test_file)
    actual_subtype = get_file_subtype(test_file)
    if (
        filename == "unknown_mime.xyz" and actual_mime is not None and expected_mime is None
    ):  # pragma: no cover
        pytest.skip(f"System provided unexpected MIME type for .xyz: {actual_mime}")
    elif (
        filename == "unknown_mime.xyz" and actual_mime is None and expected_mime is not None
    ):  # pragma: no cover
        message = f"System did not provide expected MIME type for .xyz: expected {expected_mime}, got None"
        pytest.fail(message)
    assert actual_mime == expected_mime
    assert actual_subtype == expected_subtype


def test_get_mime_type_non_existent_file_sync(tmp_path: Path):
    non_existent_py = tmp_path / "fake_sync.py"
    assert get_mime_type(non_existent_py) == "text/x-python"
    assert get_file_subtype(non_existent_py) == "x-python"


@pytest.mark.skipif(sys.platform == "win32", reason="Encoding tests might behave differently on Windows")
def test_is_utf8_file_valid_utf8_sync(tmp_path: Path):
    valid_utf8_content = "This is valid UTF-8 text with éàçü sync."
    test_file = tmp_path / "valid_utf8_sync.txt"
    test_file.write_text(valid_utf8_content, encoding="utf-8")
    assert is_utf8_file(test_file) is True


@pytest.mark.skipif(sys.platform == "win32", reason="Encoding tests might behave differently on Windows")
def test_is_utf8_file_invalid_utf8_sync(tmp_path: Path):
    invalid_utf8_bytes = b"This contains invalid sync \xff bytes."
    test_file = tmp_path / "invalid_utf8_sync.txt"
    test_file.write_bytes(invalid_utf8_bytes)
    assert is_utf8_file(test_file) is False


def test_is_utf8_file_empty_sync(tmp_path: Path):
    test_file = tmp_path / "empty_for_utf8_sync.txt"
    test_file.touch()
    assert is_utf8_file(test_file) is True


def test_is_utf8_file_not_found_sync(tmp_path: Path):
    non_existent_file = tmp_path / "not_here_for_utf8_sync.txt"
    assert is_utf8_file(non_existent_file) is False


# 🐝📁🔚
