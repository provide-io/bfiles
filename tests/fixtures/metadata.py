#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#


from pathlib import Path

import pytest

from bfiles.config import BfilesConfig
from bfiles.metadata_writer import MetadataWriter


@pytest.fixture
def writer_config(tmp_path: Path) -> BfilesConfig:
    """Basic config for writer tests (needs a root and output)."""
    root = tmp_path / "writer_root"
    root.mkdir(exist_ok=True)
    return BfilesConfig(root_dir=root, output_file=tmp_path / "dummy_writer_out.txt")


@pytest.fixture
def metadata_writer(writer_config: BfilesConfig) -> MetadataWriter:
    """Provides a MetadataWriter instance based on writer_config."""
    return MetadataWriter(writer_config)


# 🐝📁🔚
