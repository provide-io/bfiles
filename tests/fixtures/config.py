#
# SPDX-FileCopyrightText: Copyright (c) provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#


import pytest

from bfiles.config import BfilesConfig


@pytest.fixture
def default_config_no_output() -> BfilesConfig:
    """Provides a BfilesConfig instance with default values (output_file=None)."""
    # Assuming default root_dir='.' is acceptable here, or adjust as needed
    return BfilesConfig(output_file=None)


# You could add other config-specific fixtures here if needed,
# like configs with specific validation requirements.

# 🐝📁🔚
