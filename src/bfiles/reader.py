#
# SPDX-FileCopyrightText: Copyright (c) provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""File reading with encoding detection and fallback."""

from pathlib import Path

from provide.foundation import logger
from provide.foundation.resilience import retry

from bfiles.config import BfilesConfig
from bfiles.errors import EncodingError, FileReadError


class FileReader:
    """Reads file content with encoding fallback and error handling."""

    def __init__(self, config: BfilesConfig) -> None:
        self.config = config

    @retry(max_attempts=2)
    def read(self, file_path: Path) -> tuple[str | None, bool, bool]:
        """Read file content with encoding fallback.

        Args:
            file_path: Path to file to read

        Returns:
            Tuple of (content_string|None, encoding_error_occurred, encoding_fallback_failed)
        """
        content: str | None = None
        encoding_error = False
        fallback_failed = False

        try:
            content = self._read_with_primary_encoding(file_path)
            logger.debug(
                "file.read.success",
                path=str(file_path),
                encoding=self.config.encoding,
            )
        except UnicodeDecodeError:
            encoding_error = True
            logger.info(
                "file.read.encoding_fallback",
                path=str(file_path),
                primary_encoding=self.config.encoding,
            )

            try:
                content = self._read_with_fallback_encoding(file_path)
                logger.info(
                    "file.read.fallback_success",
                    path=str(file_path),
                    fallback_encoding="latin-1",
                )
            except Exception as e:
                logger.error(
                    "file.read.fallback_failure",
                    path=str(file_path),
                    error=str(e),
                )
                fallback_failed = True
                content = None

        except FileNotFoundError:
            logger.error("file.read.not_found", path=str(file_path))
            content = None
            encoding_error = True
            fallback_failed = True

        except IsADirectoryError:
            logger.error("file.read.is_directory", path=str(file_path))
            content = None
            encoding_error = True
            fallback_failed = True

        except OSError as e:
            logger.error("file.read.os_error", path=str(file_path), error=str(e))
            content = None
            encoding_error = True
            fallback_failed = True

        except Exception as e:
            logger.error(
                "file.read.unexpected_error",
                path=str(file_path),
                error=str(e),
                exc_info=True,
            )
            content = None
            encoding_error = True
            fallback_failed = True

        if content is not None:
            content = self._clean_content(content, file_path)

        return content, encoding_error, fallback_failed

    def _read_with_primary_encoding(self, file_path: Path) -> str:
        """Read file with configured primary encoding.

        Args:
            file_path: Path to file to read

        Returns:
            File content as string

        Raises:
            UnicodeDecodeError: If file cannot be decoded with primary encoding
            FileReadError: If file cannot be read
        """
        try:
            return file_path.read_text(encoding=self.config.encoding)
        except UnicodeDecodeError:
            # Re-raise to allow fallback handling in read()
            raise
        except FileNotFoundError as e:
            raise FileReadError(f"File not found: {file_path}") from e
        except Exception as e:
            raise FileReadError(f"Failed to read {file_path}: {e}") from e

    def _read_with_fallback_encoding(self, file_path: Path) -> str:
        """Read file with latin-1 fallback encoding.

        Latin-1 (ISO-8859-1) can decode any byte sequence, making it a reliable fallback.

        Args:
            file_path: Path to file to read

        Returns:
            File content as string

        Raises:
            EncodingError: If fallback encoding fails
        """
        try:
            return file_path.read_text(encoding="latin-1")
        except Exception as e:
            raise EncodingError(f"Failed to read {file_path} with latin-1 fallback: {e}") from e

    def _clean_content(self, content: str, file_path: Path) -> str:
        """Clean file content by removing null bytes.

        Args:
            content: Raw file content
            file_path: Path for logging

        Returns:
            Cleaned content string
        """
        if "\x00" in content:
            content = content.replace("\x00", "")
            logger.debug("file.content.null_bytes_removed", path=str(file_path))

        return content


# 🐝📁🔚
