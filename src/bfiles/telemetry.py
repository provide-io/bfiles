#
# SPDX-FileCopyrightText: Copyright (c) provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Telemetry configuration for bfiles operations."""

from provide.foundation.eventsets.types import EventMapping, EventSet, FieldMapping

EVENT_SET = EventSet(
    name="bfiles",
    description="File bundling and unbundling event enrichment",
    mappings=[
        EventMapping(
            name="bfiles_domain",
            visual_markers={
                "unbundle": "📂",
                "exclusion": "🚫",
                "metadata": "📋",
                "default": "❓",
            },
            default_key="default",
        ),
        EventMapping(
            name="bfiles_action",
            visual_markers={
                "collect": "📂",
                "filter": "🔍",
                "write": "✍️",
                "chunk": "🔪",
                "verify": "🔐",
                "check": "🔎",
                "pattern": "🎯",
                "hash": "🔐",
                "tokens": "🔢",
                "complete": "🏁",
                "default": "❓",
            },
            default_key="default",
        ),
        EventMapping(
            name="bfiles_status",
            visual_markers={
                "start": "🚀",
                "failure": "❌",
                "skipped": "⏭️",
                "matched": "🎯",
                "passed": "✓",
                "calculated": "🔢",
                "counted": "📊",
                "encoding_fallback": "⚠️",
                "complete": "🎉",
                "default": "➡️",
            },
            default_key="default",
        ),
    ],
    field_mappings=[
        FieldMapping(
            log_key="bfiles.domain",
            event_set_name="bfiles",
            description="Bfiles operation domain",
        ),
        FieldMapping(
            log_key="bfiles.action",
            event_set_name="bfiles",
            description="Bfiles action being performed",
        ),
        FieldMapping(
            log_key="bfiles.status",
            event_set_name="bfiles",
            description="Bfiles operation status",
        ),
        FieldMapping(
            log_key="file_count",
            event_set_name="bfiles",
            description="Number of files processed",
            value_type="integer",
        ),
        FieldMapping(
            log_key="bundle_size",
            event_set_name="bfiles",
            description="Bundle size in bytes",
            value_type="integer",
        ),
        FieldMapping(
            log_key="chunk_count",
            event_set_name="bfiles",
            description="Number of chunks",
            value_type="integer",
        ),
        FieldMapping(
            log_key="excluded_count",
            event_set_name="bfiles",
            description="Number of excluded files",
            value_type="integer",
        ),
        FieldMapping(
            log_key="pattern",
            event_set_name="bfiles",
            description="Exclusion pattern",
            value_type="string",
        ),
        FieldMapping(
            log_key="file_path",
            event_set_name="bfiles",
            description="File path being processed",
            value_type="string",
        ),
    ],
    priority=90,
)

# 🐝📁🔚
