#
# SPDX-FileCopyrightText: Copyright (c) provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Error types for bfiles operations."""

from provide.foundation import FoundationError


class BundleError(FoundationError):
    """Base error for all bundling operations."""


class ExclusionError(BundleError):
    """Error during exclusion pattern matching or filtering."""


class PatternCompilationError(ExclusionError):
    """Failed to compile exclusion pattern (regex, glob, etc.)."""


class GitignoreParseError(ExclusionError):
    """Failed to parse or apply .gitignore patterns."""


class MetadataError(BundleError):
    """Error during file metadata generation."""


class ChecksumError(MetadataError):
    """Failed to calculate file checksum."""


class TokenCountError(MetadataError):
    """Failed to count tokens in file content."""


class UnbundleError(BundleError):
    """Error during bundle extraction."""


class BundleParseError(UnbundleError):
    """Failed to parse bundle file format."""


class ChunkReassemblyError(UnbundleError):
    """Failed to reassemble chunked file."""


class ChecksumVerificationError(UnbundleError):
    """Checksum verification failed during extraction."""


class ChunkingError(BundleError):
    """Error during file chunking operations."""


class TokenizationError(ChunkingError):
    """Failed to tokenize file content for chunking."""


class ChunkSizeError(ChunkingError):
    """Invalid chunk size or overlap configuration."""


class ConfigurationError(BundleError):
    """Error in bfiles configuration."""


class InvalidPathError(ConfigurationError):
    """Invalid or unsafe file path."""


class FileReadError(BundleError):
    """Failed to read file content."""


class EncodingError(FileReadError):
    """Failed to decode file with supported encodings."""


class FileWriteError(BundleError):
    """Failed to write bundle or extracted file."""


class FileCollectionError(BundleError):
    """Error during file collection phase."""


class SymlinkError(FileCollectionError):
    """Error handling symbolic links."""


class DirectoryTraversalError(FileCollectionError):
    """Error traversing directory structure."""


# 🐝📁🔚
