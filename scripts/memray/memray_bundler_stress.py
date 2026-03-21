#!/usr/bin/env python3
"""Memray stress test for bundler hot paths.

Exercises FileMetadata.from_path (stat + hash + tiktoken), metadata
formatting, and the StringIO buffer write loop that dominates bundling.
"""
from __future__ import annotations

import os

os.environ.setdefault("LOG_LEVEL", "ERROR")

import datetime
import io
import tempfile
from pathlib import Path

from bfiles.config import BfilesConfig
from bfiles.metadata import FileMetadata
from bfiles.metadata_writer import MetadataWriter

WARMUP = 5
CYCLES = 500
FILES_PER_CYCLE = 20


def _create_sample_files(tmp_dir: Path, count: int) -> list[Path]:
    """Create sample text files for bundling."""
    paths: list[Path] = []
    for i in range(count):
        p = tmp_dir / f"sample_{i:04d}.py"
        p.write_text(f"# sample file {i}\n" + "x = 1\n" * 50, encoding="utf-8")
        paths.append(p)
    return paths


def main() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        sample_files = _create_sample_files(tmp_path, FILES_PER_CYCLE)

        config = BfilesConfig(
            root_dir=tmp_path,
            output_file=tmp_path / "out.bf.txt",
        )
        writer = MetadataWriter(config)

        # Warmup
        for _ in range(WARMUP):
            for fp in sample_files[:5]:
                meta = FileMetadata.from_path(fp, config)
                writer.format_metadata(1, meta, config.root_dir)

        # Stress: metadata creation + formatting in a tight loop
        for cycle in range(CYCLES):
            buf = io.StringIO()
            for idx, fp in enumerate(sample_files, start=1):
                meta = FileMetadata.from_path(fp, config)
                formatted = writer.format_metadata(idx, meta, config.root_dir)
                buf.write(formatted + "\n")
                buf.write("<<< BOF <<<\n")
                content = fp.read_text(encoding="utf-8")
                buf.write(content)
                buf.write("\n>>> EOF >>>\n\n")
            _ = buf.getvalue()

    print(f"Bundler stress complete: {CYCLES} cycles x {FILES_PER_CYCLE} files")


if __name__ == "__main__":
    main()
