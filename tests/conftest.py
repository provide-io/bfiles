#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Configuration for pytest."""

import pytest

pytest_plugins = [
    "tests.fixtures.cli",
    "tests.fixtures.config",
    "tests.fixtures.core",
    "tests.fixtures.exclusions",
    "tests.fixtures.metadata",
    "tests.fixtures.output",
]

# --- Bundle Test Fixtures ---


@pytest.fixture
def content_dummy_bundle_valid_str() -> str:
    return "\n".join(
        [
            "Attention: The following text is a 'bfiles' bundle...",
            "Parse and analyze the content between '<<< BOF <<<' and...",
            "",
            "--- START OF BFILE dummy_bundle.txt ---",
            "bfiles bundle generated on: 2024-01-01T12:00:00Z",
            "Config: hash=sha256, gitignore=yes, followlinks=no",
            "Comment: This is a valid test bundle.",
            "---",
            "",
            "### FILE 1: file1.txt | size=12B; op=+; cs=abc... ###",
            "<<< BOF <<<",
            "Hello World!",
            ">>> EOF >>>",
            "",
            "### FILE 2: path/to/file2.py | size=20B; op=+; cs=def... ###",
            "<<< BOF <<<",
            "def main():",
            "    pass",
            ">>> EOF >>>",
            "",
            "### FILE 3: empty.txt | size=0B; op=0; cs=... ###",
            "<<< BOF <<<",
            "",
            ">>> EOF >>>",
            "",
            ("### FILE 4: chunked_file.dat (Chunk 1/2) | size=30B; op=C; cs=xyz...; chunk_tokens=10 ###"),
            "<<< BOF <<<",
            "Part one of data.",
            ">>> EOF >>>",
            "",
            (
                "### FILE 5: chunked_file.dat (Chunk 2/2) | size=30B; op=C; cs=xyz...; "
                "chunk_tokens=10; overlap_prev=6 ###"
            ),
            "<<< BOF <<<",
            " data.Part two of data.",
            ">>> EOF >>>",
            "",
            "### BUNDLE SUMMARY ###",
            "- Included Files: 4",
            "--- END OF BFILE dummy_bundle.txt ---",
            "",
        ]
    )


@pytest.fixture
def content_malformed_bundle_missing_eof_str() -> str:
    return """--- START OF BFILE malformed.txt ---
---
### FILE 1: bad.txt | size=5B; op=+ ###
<<< BOF <<<
Oops
"""  # Missing >>> EOF >>>


@pytest.fixture
def content_malformed_bundle_bad_meta_str() -> str:
    return """--- START OF BFILE malformed.txt ---
---
### FILE BAD-LINE path/to/file.txt | meta ###
<<< BOF <<<
Content
>>> EOF >>>
"""


@pytest.fixture
def content_bundle_with_unsafe_paths_str() -> str:
    return """--- START OF BFILE unsafe.txt ---
---
### FILE 1: ../../../etc/passwd | size=10B; op=+ ###
<<< BOF <<<
#fake
>>> EOF >>>

### FILE 2: normal_dir/../../../../root_file.txt | size=10B; op=+ ###
<<< BOF <<<
#fake2
>>> EOF >>>

### FILE 3: /abs/path/file.txt | size=10B; op=+ ###
<<< BOF <<<
#fake3
>>> EOF >>>

### FILE 4: good/file.txt | size=10B; op=+ ###
<<< BOF <<<
Good one
>>> EOF >>>
"""


@pytest.fixture
def content_bundle_overlap_match_str() -> str:
    return """--- START OF BFILE overlap_match.txt ---
---
### FILE 1: overlap_file.txt (Chunk 1/3) | op=C; chunk_tokens=10 ###
<<< BOF <<<
This is the first part. Overlap
>>> EOF >>>

### FILE 2: overlap_file.txt (Chunk 2/3) | op=C; chunk_tokens=10; overlap_prev=8 ###
<<< BOF <<<
 Overlap and this is the second. MoreOverlap
>>> EOF >>>

### FILE 3: overlap_file.txt (Chunk 3/3) | op=C; chunk_tokens=10; overlap_prev=12 ###
<<< BOF <<<
 MoreOverlap and this is the end.
>>> EOF >>>
"""


@pytest.fixture
def content_bundle_overlap_mismatch_str() -> str:
    return """--- START OF BFILE overlap_mismatch.txt ---
---
### FILE 1: mismatch.txt (Chunk 1/2) | op=C ###
<<< BOF <<<
This is the first part.
>>> EOF >>>

### FILE 2: mismatch.txt (Chunk 2/2) | op=C; overlap_prev=5 ###
<<< BOF <<<
XXXXXThis is the second part.
>>> EOF >>>
"""  # Previous 5 bytes are "part.\n", current starts with "XXXXX"


@pytest.fixture
def content_bundle_overlap_short_chunk_str() -> str:
    return """--- START OF BFILE short_chunk_overlap.txt ---
---
### FILE 1: short_chunk.txt (Chunk 1/2) | op=C ###
<<< BOF <<<
This is a long first part to establish overlap bytes.
>>> EOF >>>

### FILE 2: short_chunk.txt (Chunk 2/2) | op=C; overlap_prev=10 ###
<<< BOF <<<
short
>>> EOF >>>
"""  # Chunk 2 content "short\n" (6 bytes) is shorter than overlap_prev=10


@pytest.fixture
def content_bundle_zero_overlap_str() -> str:
    # Bundler with chunk_overlap=0 would not produce overlap_prev.
    # This test simulates if overlap_prev=0 was somehow in metadata.
    return """--- START OF BFILE zero_overlap.txt ---
---
### FILE 1: zero.txt (Chunk 1/2) | op=C ###
<<< BOF <<<
First part.
>>> EOF >>>

### FILE 2: zero.txt (Chunk 2/2) | op=C; overlap_prev=0 ###
<<< BOF <<<
Second part.
>>> EOF >>>
"""


# 🐝📁🔚
