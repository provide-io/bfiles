#!/usr/bin/env python3
"""Memray stress test for BundleParser hot paths.

Creates a synthetic bundle in memory and parses it repeatedly to stress
the regex matching, line iteration, and content extraction loop.
"""
from __future__ import annotations

import os

os.environ.setdefault("LOG_LEVEL", "ERROR")

import datetime
import tempfile
from pathlib import Path

from bfiles.parser import BundleParser

WARMUP = 3
CYCLES = 200
FILES_PER_BUNDLE = 50


def _generate_bundle(num_files: int) -> str:
    """Generate a synthetic bfiles bundle string."""
    lines: list[str] = []
    lines.append(
        "Attention: The following text is a 'bfiles' bundle, "
        "containing multiple delimited files with metadata.\n"
    )
    lines.append(
        "Parse and analyze the content between '<<< BOF <<<' and '>>> EOF >>>' "
        "for each '### FILE...' entry.\n"
    )
    lines.append("")
    lines.append("--- START OF BFILE stress_test.bf.txt ---")
    lines.append(f"bfiles bundle generated on: {datetime.datetime.now().isoformat()}")
    lines.append("Config: hash=sha256, gitignore=yes, followlinks=no")
    lines.append("---")
    lines.append("")

    for i in range(1, num_files + 1):
        path = f"src/module_{i:04d}.py"
        meta = f"size={500 + i}; type=x-python; sha256=abc{i:04d}; tokens={100 + i}"
        lines.append(f"### FILE {i}: {path} | {meta} ###")
        lines.append("<<< BOF <<<")
        lines.append(f"# module {i}")
        for j in range(10):
            lines.append(f"line_{j} = {j}")
        lines.append(">>> EOF >>>")
        lines.append("")

    lines.append("### BUNDLE SUMMARY ###")
    lines.append(f"Files included: {num_files}")
    lines.append("--- END OF BFILE stress_test.bf.txt ---")
    return "\n".join(lines)


def main() -> None:
    bundle_text = _generate_bundle(FILES_PER_BUNDLE)

    with tempfile.TemporaryDirectory() as tmp:
        bundle_path = Path(tmp) / "stress_test.bf.txt"
        bundle_path.write_text(bundle_text, encoding="utf-8")

        # Warmup
        for _ in range(WARMUP):
            parser = BundleParser(bundle_path)
            parser.parse()

        # Stress
        for _ in range(CYCLES):
            parser = BundleParser(bundle_path)
            parser.parse()

    print(f"Parser stress complete: {CYCLES} cycles x {FILES_PER_BUNDLE} files")


if __name__ == "__main__":
    main()
