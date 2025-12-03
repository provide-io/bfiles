#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#


import datetime
from pathlib import Path

from bfiles.config import BfilesConfig
from bfiles.metadata import FileMetadata
from bfiles.metadata_writer import MetadataWriter


def test_format_metadata_included(metadata_writer: MetadataWriter, writer_config: BfilesConfig):
    now = datetime.datetime(2024, 5, 2, 10, 30, 0, tzinfo=datetime.UTC)
    p = (writer_config.root_dir / "src/module_sync.py").resolve()
    meta = FileMetadata(
        path=p,
        size=1024,
        modified=now,
        file_type="x-python",
        checksum="a1b2c3d4e5f6a7b8sync",
        operation="included",
    )
    line = metadata_writer.format_metadata(file_num=5, metadata=meta, root_dir=writer_config.root_dir)

    assert line.startswith("### FILE 5: src/module_sync.py |")
    assert "checksum=a1b2c3d4e5f6..." in line
    assert f"modified={now.isoformat(timespec='seconds')}" in line
    assert "op=+" in line
    assert "size=1024" in line
    assert "type=x-python" in line
    assert "original=" not in line


def test_format_metadata_duplicate(metadata_writer: MetadataWriter, writer_config: BfilesConfig):
    now = datetime.datetime(2024, 5, 2, 10, 31, 0, tzinfo=datetime.UTC)
    p_orig = (writer_config.root_dir / "original_sync.txt").resolve()
    p_dup = (writer_config.root_dir / "subdir/duplicate_sync.txt").resolve()
    meta = FileMetadata(
        path=p_dup,
        size=500,
        modified=now,
        file_type="plain",
        checksum="fedcba987654sync",
        operation="duplicate",
        original=p_orig,
    )
    line = metadata_writer.format_metadata(file_num=0, metadata=meta, root_dir=writer_config.root_dir)

    assert line.startswith("### FILE 0: subdir/duplicate_sync.txt |")
    assert "checksum=fedcba987654..." in line
    assert f"modified={now.isoformat(timespec='seconds')}" in line
    assert "op=d" in line
    assert "size=500" in line
    assert "type=plain" in line
    assert "original=original_sync.txt" in line


def test_format_metadata_empty(metadata_writer: MetadataWriter, writer_config: BfilesConfig):
    now = datetime.datetime(2024, 5, 2, 10, 32, 0, tzinfo=datetime.UTC)
    p = (writer_config.root_dir / "empty_sync").resolve()
    meta = FileMetadata(path=p, size=0, modified=now, operation="empty")
    line = metadata_writer.format_metadata(file_num=0, metadata=meta, root_dir=writer_config.root_dir)

    assert line.startswith("### FILE 0: empty_sync |")
    assert "checksum=" not in line
    assert f"modified={now.isoformat(timespec='seconds')}" in line
    assert "op=0" in line
    assert "size=0" in line
    assert "type=" not in line


def test_format_metadata_excluded(metadata_writer: MetadataWriter, writer_config: BfilesConfig):
    now = datetime.datetime(2024, 5, 2, 10, 33, 0, tzinfo=datetime.UTC)
    p = (writer_config.root_dir / ".git/config_sync").resolve()
    meta = FileMetadata(path=p, size=123, modified=now, operation="excluded")
    line = metadata_writer.format_metadata(file_num=0, metadata=meta, root_dir=writer_config.root_dir)

    assert line.startswith("### FILE 0: .git/config_sync |")
    assert f"modified={now.isoformat(timespec='seconds')}" in line
    assert "op=x" in line
    assert "size=123" in line


def test_format_metadata_path_outside_root(metadata_writer: MetadataWriter, tmp_path: Path):
    root_dir = tmp_path / "project_root_sync"
    root_dir.mkdir()
    outside_file = tmp_path / "outside_file_sync.txt"
    outside_file.touch()

    config = BfilesConfig(root_dir=root_dir, output_file=tmp_path / "out_sync.txt")
    writer = MetadataWriter(config)

    now = datetime.datetime(2024, 5, 2, 10, 35, 0, tzinfo=datetime.UTC)
    meta = FileMetadata(
        path=outside_file.resolve(), size=10, modified=now, operation="included", checksum="123sync"
    )
    line = writer.format_metadata(file_num=1, metadata=meta, root_dir=root_dir)

    assert f"### FILE 1: {outside_file.resolve()!s} |" in line
    assert "op=+" in line


# 🐝📁🔚
