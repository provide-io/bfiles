#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#


import mimetypes
from pathlib import Path

from provide.foundation import logger
from provide.foundation.crypto import hash_file
from provide.foundation.errors import ResourceError, ValidationError

# Initialize mimetypes database if not already done
# Add common types that might be missing or guessed incorrectly
mimetypes.init()
mimetypes.add_type("text/markdown", ".md")
mimetypes.add_type("text/x-python", ".py")
mimetypes.add_type("application/x-sh", ".sh")
mimetypes.add_type("text/x-yaml", ".yaml")
mimetypes.add_type("text/x-yaml", ".yml")
mimetypes.add_type("application/toml", ".toml")
mimetypes.add_type("text/rust", ".rs")
mimetypes.add_type("text/x-go", ".go")
mimetypes.add_type("text/plain", "Dockerfile")  # Treat Dockerfiles as plain text
mimetypes.add_type("text/plain", "Makefile")  # Treat Makefiles as plain text

# Fallbacks if mimetypes.guess_type returns None
# Focus on common text/code types
_MIME_TYPE_FALLBACKS: dict[str, str] = {
    ".js": "text/javascript",
    ".ts": "text/typescript",
    ".java": "text/x-java-source",
    ".c": "text/x-c",
    ".h": "text/x-c",
    ".cpp": "text/x-c++src",
    ".hpp": "text/x-c++src",
    ".cs": "text/x-csharp",
    ".rb": "text/x-ruby",
    ".php": "text/x-php",
    ".json": "application/json",
    ".xml": "application/xml",
    ".html": "text/html",
    ".css": "text/css",
    ".ini": "text/plain",
    ".cfg": "text/plain",
    ".txt": "text/plain",
    "makefile": "text/plain",
    "dockerfile": "text/plain",
    # Add more as identified
}


def compute_file_hash(file_path: Path, algorithm: str = "sha256", buffer_size: int = 65536) -> str:
    """
    Compute the checksum of a file using the specified algorithm.

    Note: This is a wrapper around foundation.crypto.hash_file() for backward compatibility.
    The buffer_size parameter is maintained for API compatibility but mapped to chunk_size.

    Args:
        file_path: Path to the file.
        algorithm: Hashing algorithm name (e.g., 'sha256', 'md5').
        buffer_size: Size of chunks to read from the file (mapped to chunk_size).

    Returns:
        Hex digest of the file hash.

    Raises:
        ValueError: If the algorithm is not supported.
        OSError: If the file cannot be opened or read.
    """
    try:
        return hash_file(file_path, algorithm=algorithm, chunk_size=buffer_size)
    except ValidationError as e:
        logger.error(f"Unsupported hash algorithm '{algorithm}' requested for {file_path}.")
        raise ValueError(f"Unsupported hash algorithm: {algorithm}") from e
    except ResourceError as e:  # pragma: no cover
        logger.error(f"Failed to read file for hashing {file_path}: {e}")
        raise OSError(f"Cannot read file: {file_path}") from e


def get_mime_type(file_path: Path) -> str | None:
    """
    Guess the full MIME type of a file using mimetypes and fallbacks.

    Args:
        file_path: Path to the file.

    Returns:
        Guessed MIME type string (e.g., 'text/x-python') or None if unknown.
    """
    mime_type: str | None = None
    # Use filename for guess_type as it handles names like Makefile better
    mime_type, _ = mimetypes.guess_type(file_path.name, strict=False)

    if mime_type:
        logger.debug(f"Guessed MIME type for {file_path.name} via mimetypes: {mime_type}")
        return mime_type

    # Fallback based on file extension (lowercase)
    ext_fallback = _MIME_TYPE_FALLBACKS.get(file_path.suffix.lower())
    if ext_fallback:
        logger.debug(f"Guessed MIME type for {file_path.name} via fallback: {ext_fallback}")
        return ext_fallback

    # Fallback based on filename (lowercase) if no extension match
    name_fallback = _MIME_TYPE_FALLBACKS.get(file_path.name.lower())
    if name_fallback:  # pragma: no cover
        logger.debug(f"Guessed MIME type for {file_path.name} via filename fallback: {name_fallback}")
        return name_fallback

    # If no type found after checks
    logger.debug(f"Could not determine MIME type for {file_path.name}.")
    return None


def get_file_subtype(file_path: Path) -> str | None:
    """
    Get the MIME subtype (part after '/') of a file, or None if unknown.

    Args:
        file_path: Path to the file.

    Returns:
        MIME subtype string (e.g., 'x-python', 'plain', 'json') or None.
    """
    full_mime_type = get_mime_type(file_path)

    if full_mime_type and "/" in full_mime_type:
        # Return the part after the last '/'
        return full_mime_type.split("/")[-1]
    elif full_mime_type:  # pragma: no cover
        # Handle cases like 'text' without subtype? Should be rare.
        # Return the full type if no slash? Or treat as 'plain'? Let's return it.
        logger.warning(f"MIME type '{full_mime_type}' for {file_path.name} lacks a subtype separator '/'.")
        return full_mime_type  # Return the full string if no '/'
    else:
        # Truly unknown type
        return None


# is_utf8_file function might be less critical now with 'replace' error handling,
# but kept here if explicit checks are ever needed.
def is_utf8_file(file_path: Path, sample_size: int = 1024) -> bool:
    """
    Quickly check if the beginning of a file seems decodable as UTF-8.

    Args:
        file_path: Path to the file.
        sample_size: How many bytes to read from the start of the file.

    Returns:
        True if the sample decodes as UTF-8 'strict', False otherwise or on error.
    """
    try:
        with file_path.open("rb") as f:
            sample = f.read(sample_size)
            sample.decode("utf-8", errors="strict")  # Try decoding with strict errors
    except UnicodeDecodeError:  # pragma: no cover
        logger.debug(f"File start does not decode as strict UTF-8: {file_path}")
        return False
    except FileNotFoundError:  # pragma: no cover
        logger.error(f"File not found during UTF-8 check: {file_path}")
        return False
    except OSError as e:  # pragma: no cover
        logger.error(f"OS error during UTF-8 check for {file_path}: {e}")
        return False
    except Exception as e:  # pragma: no cover
        logger.error(f"Unexpected error during UTF-8 check for {file_path}: {e}", exc_info=True)
        return False
    else:
        return True


# ASCII control character names for sanitization
_CONTROL_CHAR_NAMES: dict[int, str] = {
    0x00: "NUL",
    0x01: "SOH",
    0x02: "STX",
    0x03: "ETX",
    0x04: "EOT",
    0x05: "ENQ",
    0x06: "ACK",
    0x07: "BEL",
    0x08: "BS",
    0x09: "TAB",  # Safe whitespace - won't be replaced
    0x0A: "LF",  # Safe whitespace - won't be replaced
    0x0B: "VT",  # Safe whitespace - won't be replaced
    0x0C: "FF",  # Safe whitespace - won't be replaced
    0x0D: "CR",  # Safe whitespace - won't be replaced
    0x0E: "SO",
    0x0F: "SI",
    0x10: "DLE",
    0x11: "DC1",
    0x12: "DC2",
    0x13: "DC3",
    0x14: "DC4",
    0x15: "NAK",
    0x16: "SYN",
    0x17: "ETB",
    0x18: "CAN",
    0x19: "EM",
    0x1A: "SUB",
    0x1B: "ESC",
    0x1C: "FS",
    0x1D: "GS",
    0x1E: "RS",
    0x1F: "US",
}

# Safe whitespace characters that are allowed in file content
_SAFE_WHITESPACE = {0x09, 0x0A, 0x0B, 0x0C, 0x0D}  # \t, \n, \v, \f, \r


def has_dangerous_chars(content: str) -> tuple[bool, list[tuple[int, str]]]:
    r"""Check if content contains dangerous control characters that can break terminals.

    Dangerous characters are control chars 0x00-0x1F except safe whitespace (\t, \n, \r, \f, \v).

    Args:
        content: String content to check

    Returns:
        Tuple of (is_dangerous, [(position, hex_representation), ...])
        - is_dangerous: True if dangerous chars found
        - list: List of (position, "0xNN") for first 10 dangerous chars found

    Examples:
        >>> has_dangerous_chars("hello\\x00world")
        (True, [(5, '0x00')])

        >>> has_dangerous_chars("hello\\nworld")  # \\n is safe
        (False, [])

        >>> has_dangerous_chars("test\\x1b[31mred\\x1b[0m")  # ESC sequences
        (True, [(4, '0x1b'), (10, '0x1b')])
    """
    dangerous_positions: list[tuple[int, str]] = []

    for pos, char in enumerate(content):
        char_code = ord(char)

        # Check if it's a control character (0x00-0x1F)
        # Skip safe whitespace
        if 0x00 <= char_code <= 0x1F and char_code not in _SAFE_WHITESPACE:
            dangerous_positions.append((pos, f"0x{char_code:02x}"))

            # Limit to first 10 for performance
            if len(dangerous_positions) >= 10:
                break

    is_dangerous = len(dangerous_positions) > 0
    return is_dangerous, dangerous_positions


def sanitize_dangerous_chars(content: str) -> str:
    r"""Replace dangerous control characters with visible safe representations.

    Converts control chars (0x00-0x1F except safe whitespace) to [NAME] format.
    Preserves safe whitespace: \\t, \\n, \\r, \\f, \\v

    Args:
        content: String content to sanitize

    Returns:
        Sanitized string with control chars replaced by [NAME] markers

    Examples:
        >>> sanitize_dangerous_chars("hello\\x00world")
        'hello[NUL]world'

        >>> sanitize_dangerous_chars("test\\x1b[31mred\\x1b[0m")
        'test[ESC][31mred[ESC][0m'

        >>> sanitize_dangerous_chars("hello\\nworld")  # \\n preserved
        'hello\\nworld'

        >>> sanitize_dangerous_chars("tab\\there")  # \\t preserved
        'tab\\there'
    """
    result = []

    for char in content:
        char_code = ord(char)

        # Check if it's a control character (0x00-0x1F)
        if 0x00 <= char_code <= 0x1F:
            # Preserve safe whitespace
            if char_code in _SAFE_WHITESPACE:
                result.append(char)
            else:
                # Replace with visible name
                name = _CONTROL_CHAR_NAMES.get(char_code, f"0x{char_code:02X}")
                result.append(f"[{name}]")
        else:
            # Normal character, keep as-is
            result.append(char)

    return "".join(result)


# 🐝📁🔚
