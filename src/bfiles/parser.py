#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Bundle parsing for extraction operations."""

from pathlib import Path
import re
from typing import NamedTuple

from provide.foundation import logger

from bfiles.errors import BundleParseError


class ParsedFileEntry(NamedTuple):
    """Represents a single file entry parsed from the bundle."""

    relative_path: str
    metadata_str: str
    metadata_dict: dict[str, str]
    content: str
    is_chunk: bool = False
    chunk_num: int | None = None
    total_chunks: int | None = None
    file_num_in_bundle: int | None = None


class ParsedBundleHeader(NamedTuple):
    """Represents the parsed bundle header information."""

    original_bundle_name: str | None = None
    generation_datetime: str | None = None
    config_options: dict[str, str] = {}  # noqa: RUF012
    comment: str | None = None
    raw_header_lines: tuple[str, ...] = ()


class BundleParser:
    """Parses a bfiles bundle file, extracting its header, file entries, and content."""

    _FILE_META_LINE_RE = re.compile(
        r"^###\s+FILE\s+(?P<num>\d+):\s*(?P<path>.+?)\s*"
        r"(?:\(Chunk\s+(?P<chunk_num>\d+)/(?P<total_chunks>\d+)\))?\s*\|\s*(?P<meta_str>.+?)\s*###$"
    )
    _BUNDLE_START_RE = re.compile(r"^--- START OF BFILE (.+) ---$")
    _BUNDLE_END_RE = re.compile(r"^--- END OF BFILE (.+) ---$")
    _BUNDLE_SUMMARY_START_RE = re.compile(r"^### BUNDLE SUMMARY ###$")
    _CONFIG_LINE_RE = re.compile(r"^Config:\s*(.+)$")
    _COMMENT_LINE_RE = re.compile(r"^Comment:\s*(.+)$")
    _GENERATED_ON_RE = re.compile(r"^bfiles bundle generated on:\s*(.+)$")

    def __init__(self, bundle_file_path: Path) -> None:
        self.bundle_file_path = bundle_file_path
        self.header: ParsedBundleHeader | None = None
        self.file_entries: list[ParsedFileEntry] = []
        self.footer_lines: list[str] = []
        self._lines: list[str] = []
        self._current_line_idx: int = 0

    def _read_lines(self) -> None:
        """Read all lines from the bundle file.

        Raises:
            BundleParseError: If file cannot be read
        """
        logger.info("parse.read.start", path=str(self.bundle_file_path))

        try:
            try:
                with self.bundle_file_path.open("r", encoding="utf-8") as f:
                    self._lines = f.readlines()
                logger.debug("parse.read.success", encoding="utf-8")
            except UnicodeDecodeError:
                logger.warning(
                    "parse.read.fallback",
                    path=str(self.bundle_file_path),
                    fallback_encoding="latin-1",
                )
                with self.bundle_file_path.open("r", encoding="latin-1") as f:
                    self._lines = f.readlines()
                logger.debug("parse.read.success", encoding="latin-1")
        except FileNotFoundError as e:
            logger.error("parse.read.not_found", path=str(self.bundle_file_path))
            raise BundleParseError(f"Bundle file not found: {self.bundle_file_path}") from e
        except OSError as e:
            logger.error("parse.read.error", path=str(self.bundle_file_path), error=str(e))
            raise BundleParseError(f"Error reading bundle file: {e}") from e

    def _parse_metadata_kv_str(self, meta_kv_str: str) -> dict[str, str]:
        """Parse 'key1=value1; key2=value2' into a dict."""
        metadata: dict[str, str] = {}
        if not meta_kv_str:
            return metadata

        pairs = meta_kv_str.split(";")
        for pair in pairs:
            if "=" in pair:
                key, value = pair.split("=", 1)
                metadata[key.strip()] = value.strip()
            elif pair.strip():
                metadata[pair.strip()] = ""

        return metadata

    def _parse_header(self) -> bool:  # noqa: C901
        """Parse the bundle header section.

        Returns:
            True if successful, False otherwise
        """
        logger.debug("parse.header.start")

        raw_header_lines: list[str] = []
        original_bundle_name: str | None = None
        generation_datetime: str | None = None
        config_options: dict[str, str] = {}
        comment: str | None = None

        if self._current_line_idx < len(self._lines) and self._lines[self._current_line_idx].startswith(
            "Attention:"
        ):
            self._current_line_idx += 1

        if self._current_line_idx < len(self._lines) and self._lines[self._current_line_idx].startswith(
            "Parse and analyze"
        ):
            self._current_line_idx += 1

        if self._current_line_idx < len(self._lines) and not self._lines[self._current_line_idx].strip():
            self._current_line_idx += 1

        if self._current_line_idx >= len(self._lines):
            logger.error("parse.header.no_start_marker")
            return False

        start_match = self._BUNDLE_START_RE.match(self._lines[self._current_line_idx].strip())
        if not start_match:
            logger.error(
                "parse.header.invalid_start",
                line=self._lines[self._current_line_idx][:50],
            )
            return False

        original_bundle_name = start_match.group(1)
        raw_header_lines.append(self._lines[self._current_line_idx])
        self._current_line_idx += 1

        while self._current_line_idx < len(self._lines):
            line = self._lines[self._current_line_idx].strip()
            raw_header_lines.append(self._lines[self._current_line_idx])

            if line == "---":
                self._current_line_idx += 1
                if (
                    self._current_line_idx < len(self._lines)
                    and not self._lines[self._current_line_idx].strip()
                ):
                    self._current_line_idx += 1
                else:
                    logger.warning("parse.header.no_blank_line_after")

                self.header = ParsedBundleHeader(
                    original_bundle_name=original_bundle_name,
                    generation_datetime=generation_datetime,
                    config_options=config_options,
                    comment=comment,
                    raw_header_lines=raw_header_lines,
                )
                logger.debug("parse.header.success")
                return True

            gen_match = self._GENERATED_ON_RE.match(line)
            if gen_match:
                generation_datetime = gen_match.group(1)
            else:
                config_match = self._CONFIG_LINE_RE.match(line)
                if config_match:
                    configs = config_match.group(1).split(",")
                    for c_item in configs:
                        if "=" in c_item:
                            key, val = c_item.split("=", 1)
                            config_options[key.strip()] = val.strip()
                else:
                    comment_match = self._COMMENT_LINE_RE.match(line)
                    if comment_match:
                        comment = comment_match.group(1)

            self._current_line_idx += 1

        logger.error("parse.header.unexpected_end")
        return False

    def parse(self) -> bool:  # noqa: C901
        """Parse the entire bundle file.

        Returns:
            True on success, False on critical parsing errors

        Raises:
            BundleParseError: If parsing fails
        """
        logger.info("parse.bundle.start", path=str(self.bundle_file_path))

        self._read_lines()
        if not self._lines:
            return False

        if not self._parse_header():
            logger.error("parse.bundle.header_failed")
            return False

        logger.info(
            "parse.bundle.header_success",
            original_name=(self.header.original_bundle_name if self.header else "N/A"),
        )

        while self._current_line_idx < len(self._lines):
            line = self._lines[self._current_line_idx].strip()

            if not line:
                self._current_line_idx += 1
                continue

            if self._BUNDLE_SUMMARY_START_RE.match(line) or self._BUNDLE_END_RE.match(line):
                break

            meta_match = self._FILE_META_LINE_RE.match(line)
            if not meta_match:
                logger.error(
                    "parse.entry.malformed",
                    line_num=self._current_line_idx + 1,
                    line=line[:100],
                )
                return False

            groups = meta_match.groupdict()
            file_num = int(groups["num"])
            relative_path = groups["path"].strip()
            meta_kv_str = groups["meta_str"]
            is_chunk = bool(groups["chunk_num"])
            chunk_num = int(groups["chunk_num"]) if is_chunk else None
            total_chunks = int(groups["total_chunks"]) if is_chunk else None

            self._current_line_idx += 1

            if (
                self._current_line_idx >= len(self._lines)
                or self._lines[self._current_line_idx].strip() != "<<< BOF <<<"
            ):
                logger.error(
                    "parse.entry.missing_bof",
                    path=relative_path,
                    line_num=self._current_line_idx + 1,
                )
                return False
            self._current_line_idx += 1

            content_lines: list[str] = []
            while self._current_line_idx < len(self._lines):
                content_line_raw = self._lines[self._current_line_idx]
                if content_line_raw.strip() == ">>> EOF >>>":
                    break
                content_lines.append(content_line_raw)
                self._current_line_idx += 1
            else:
                logger.error("parse.entry.missing_eof", path=relative_path)
                return False

            self._current_line_idx += 1

            if self._current_line_idx < len(self._lines) and not self._lines[self._current_line_idx].strip():
                self._current_line_idx += 1

            content = "".join(content_lines)
            metadata_dict = self._parse_metadata_kv_str(meta_kv_str)

            self.file_entries.append(
                ParsedFileEntry(
                    relative_path=relative_path,
                    metadata_str=meta_kv_str,
                    metadata_dict=metadata_dict,
                    content=content,
                    is_chunk=is_chunk,
                    chunk_num=chunk_num,
                    total_chunks=total_chunks,
                    file_num_in_bundle=file_num,
                )
            )

            chunk_info = f" (Chunk {chunk_num}/{total_chunks})" if is_chunk else ""
            logger.debug("parse.entry.success", path=f"{relative_path}{chunk_info}")

        if self._current_line_idx < len(self._lines):
            line = self._lines[self._current_line_idx].strip()
            if self._BUNDLE_SUMMARY_START_RE.match(line):
                self._parse_footer()
            elif self._BUNDLE_END_RE.match(line):
                self.footer_lines.append(self._lines[self._current_line_idx])
                self._current_line_idx += 1
            else:
                logger.warning(
                    "parse.bundle.unexpected_content",
                    line_num=self._current_line_idx + 1,
                    line=line[:100],
                )

        logger.info("parse.bundle.success", entry_count=len(self.file_entries))
        return True

    def _parse_footer(self) -> None:
        """Parse and store footer lines if present."""
        logger.debug("parse.footer.start")

        while self._current_line_idx < len(self._lines):
            line_raw = self._lines[self._current_line_idx]
            self.footer_lines.append(line_raw)
            self._current_line_idx += 1
            if self._BUNDLE_END_RE.match(line_raw.strip()):
                break
        else:
            logger.warning("parse.footer.no_end_marker")


# 🐝📁🔚
