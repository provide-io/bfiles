#
# SPDX-FileCopyrightText: Copyright (c) provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""bfiles: A modular file bundling utility for LLM processing.

Integrated with provide-foundation for enterprise-grade patterns.
"""

from provide.foundation import get_hub, logger
from provide.foundation.utils.versioning import get_version

from bfiles.bundler import Bundler
from bfiles.chunking import FileChunker
from bfiles.collection import FileCollector
from bfiles.config import BfilesConfig
from bfiles.core import bundle_files, list_potential_files
from bfiles.exclusions import ExclusionManager
from bfiles.extractor import FileExtractor
from bfiles.metadata import FileMetadata
from bfiles.metadata_writer import MetadataWriter
from bfiles.parser import BundleParser
from bfiles.reader import FileReader
from bfiles.unbundler import Unbundler

# Initialize the Foundation Hub (available for advanced usage)
_hub = get_hub()

# Log successful integration with Foundation
logger.debug(
    "bfiles.init",
    foundation_hub_available=True,
    components_available=["Bundler", "Parser", "Extractor", "Collector", "Reader"],
)

# Public API exports
__all__ = [
    # Configuration
    "BfilesConfig",
    "BundleParser",
    # Components (for advanced usage)
    "Bundler",
    "ExclusionManager",
    "FileChunker",
    "FileCollector",
    "FileExtractor",
    # Data structures
    "FileMetadata",
    "FileReader",
    "MetadataWriter",
    # Unbundling
    "Unbundler",
    # Core operations
    "bundle_files",
    # Foundation integration
    "get_hub",
    "list_potential_files",
]

__version__ = get_version("bfiles", caller_file=__file__)

# 🐝📁🔚
