#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Tests for Unbundler path sanitization and security."""

from pathlib import Path

import pytest

from bfiles.errors import BundleParseError
from bfiles.unbundler import Unbundler

# --- Unbundler Security Tests ---


def test_unbundler_path_sanitization(tmp_path: Path, content_bundle_with_unsafe_paths_str: str):
    """Test that unsafe paths are rejected and not extracted."""
    bundle_file_path = tmp_path / "unsafe_paths.bfiles"
    bundle_file_path.write_text(content_bundle_with_unsafe_paths_str, encoding="utf-8")
    output_dir = tmp_path / "output_sanitize"
    unbundler = Unbundler(bundle_file_path, output_dir_base=output_dir)

    # Should complete extraction but skip unsafe paths (logs warnings internally)
    assert unbundler.extract() is True

    # Unsafe paths should NOT be created
    assert not (output_dir / "../../../etc/passwd").exists()
    assert not (output_dir / "normal_dir/../../../../root_file.txt").exists()
    assert not (output_dir / "/abs/path/file.txt").exists()
    assert not Path("/abs/path/file.txt").exists()

    # The good file should be extracted
    assert (output_dir / "good/file.txt").exists()
    assert (output_dir / "good/file.txt").read_text() == "Good one\n"


def test_unbundler_non_existent_bundle(tmp_path: Path):
    """Test that unbundler raises error for non-existent bundle files."""
    unbundler = Unbundler(tmp_path / "no_such_bundle.bfiles", output_dir_base=tmp_path / "out")
    # Parser now raises BundleParseError (wrapping FileNotFoundError)
    with pytest.raises(BundleParseError, match="Bundle file not found"):
        unbundler.extract()


# 🐝📁🔚
