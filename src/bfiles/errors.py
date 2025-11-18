#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Error types for bfiles operations."""

from provide.foundation import FoundationError


class BundleError(FoundationError):
    """Base error for all bundling operations."""

    pass


class ExclusionError(BundleError):
    """Error during exclusion pattern matching or filtering."""

    pass


class PatternCompilationError(ExclusionError):
    """Failed to compile exclusion pattern (regex, glob, etc.)."""

    pass


class GitignoreParseError(ExclusionError):
    """Failed to parse or apply .gitignore patterns."""

    pass


class MetadataError(BundleError):
    """Error during file metadata generation."""

    pass


class ChecksumError(MetadataError):
    """Failed to calculate file checksum."""

    pass


class TokenCountError(MetadataError):
    """Failed to count tokens in file content."""

    pass


class UnbundleError(BundleError):
    """Error during bundle extraction."""

    pass


class BundleParseError(UnbundleError):
    """Failed to parse bundle file format."""

    pass


class ChunkReassemblyError(UnbundleError):
    """Failed to reassemble chunked file."""

    pass


class ChecksumVerificationError(UnbundleError):
    """Checksum verification failed during extraction."""

    pass


class ChunkingError(BundleError):
    """Error during file chunking operations."""

    pass


class TokenizationError(ChunkingError):
    """Failed to tokenize file content for chunking."""

    pass


class ChunkSizeError(ChunkingError):
    """Invalid chunk size or overlap configuration."""

    pass


class ConfigurationError(BundleError):
    """Error in bfiles configuration."""

    pass


class InvalidPathError(ConfigurationError):
    """Invalid or unsafe file path."""

    pass


class FileReadError(BundleError):
    """Failed to read file content."""

    pass


class EncodingError(FileReadError):
    """Failed to decode file with supported encodings."""

    pass


class FileWriteError(BundleError):
    """Failed to write bundle or extracted file."""

    pass


class FileCollectionError(BundleError):
    """Error during file collection phase."""

    pass


class SymlinkError(FileCollectionError):
    """Error handling symbolic links."""

    pass


class DirectoryTraversalError(FileCollectionError):
    """Error traversing directory structure."""

    pass


# 🐝📁🔚
