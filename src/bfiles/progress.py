#
# SPDX-FileCopyrightText: Copyright (c) provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Real-time progress reporting for file operations."""

from pathlib import Path
import time
from typing import Literal

from provide.foundation.console import pout
from provide.foundation.context import CLIContext

ProgressStatus = Literal[
    "found", "included", "excluded", "empty", "duplicate", "error", "extracted", "skipped"
]


class ProgressReporter:
    """Reports real-time progress during file operations.

    Uses Foundation's pout() for output. Automatically disabled in JSON mode.
    Respects no_color and no_emoji settings from CLIContext.
    """

    def __init__(self, enabled: bool = True, cli_context: CLIContext | None = None) -> None:
        """Initialize progress reporter.

        Args:
            enabled: Whether progress reporting is enabled
            cli_context: Optional CLI context (disables progress in JSON mode)
        """
        self.enabled = enabled
        self.cli_context = cli_context
        self.current_operation: str | None = None
        self.operation_start_time: float = 0.0

        # Disable progress in JSON mode
        if cli_context and cli_context.json_output:
            self.enabled = False

    def _should_output(self) -> bool:
        """Check if output should be produced."""
        return self.enabled and not (self.cli_context and self.cli_context.json_output)

    def _get_status_symbol(self, status: ProgressStatus) -> str:
        """Get colored symbol for status.

        Args:
            status: Progress status

        Returns:
            Colored symbol string
        """
        # Check if emojis are disabled
        no_emoji = self.cli_context and self.cli_context.no_emoji

        symbols = {
            "found": "✓" if not no_emoji else "+",
            "included": "✓" if not no_emoji else "+",
            "extracted": "✓" if not no_emoji else "+",
            "excluded": "⊗" if not no_emoji else "X",
            "empty": "○" if not no_emoji else "o",
            "duplicate": "≈" if not no_emoji else "=",
            "error": "✗" if not no_emoji else "!",
            "skipped": "⊝" if not no_emoji else "-",
        }

        return symbols.get(status, "?")

    def _get_status_color(self, status: ProgressStatus) -> str:
        """Get color for status.

        Args:
            status: Progress status

        Returns:
            Color name
        """
        colors = {
            "found": "green",
            "included": "green",
            "extracted": "green",
            "excluded": "yellow",
            "empty": "cyan",
            "duplicate": "cyan",
            "error": "red",
            "skipped": "yellow",
        }

        return colors.get(status, "white")

    def operation_start(self, operation_name: str) -> None:
        """Signal start of an operation phase.

        Args:
            operation_name: Name of the operation (e.g., "Collecting files")
        """
        if not self._should_output():
            return

        self.current_operation = operation_name
        self.operation_start_time = time.monotonic()

        pout(f"\n{operation_name}...", color="cyan", bold=True, ctx=self.cli_context)

    def operation_end(self, operation_name: str, count: int, elapsed: float | None = None) -> None:
        """Signal end of an operation phase with summary.

        Args:
            operation_name: Name of the operation
            count: Number of items processed
            elapsed: Optional elapsed time in seconds
        """
        if not self._should_output():
            return

        if elapsed is None and self.operation_start_time > 0:
            elapsed = time.monotonic() - self.operation_start_time

        elapsed_str = f" in {elapsed:.1f}s" if elapsed else ""
        pout(
            f"{operation_name} complete: {count} items{elapsed_str}",
            color="cyan",
            ctx=self.cli_context,
        )

        self.current_operation = None
        self.operation_start_time = 0.0

    def file_progress(
        self,
        file_path: Path,
        status: ProgressStatus,
        root_dir: Path | None = None,
        details: str | None = None,
    ) -> None:
        """Report progress for a single file.

        Args:
            file_path: Path to the file being processed
            status: Status of the operation
            root_dir: Optional root directory for relative path display
            details: Optional additional details to display
        """
        if not self._should_output():
            return

        # Get relative path if root_dir provided
        try:
            display_path = file_path.relative_to(root_dir) if root_dir else file_path
        except ValueError:
            display_path = file_path

        symbol = self._get_status_symbol(status)
        color = self._get_status_color(status)

        # Format message
        status_label = status.capitalize()
        details_str = f" ({details})" if details else ""
        message = f"  {symbol} {status_label}: {display_path.as_posix()}{details_str}"

        pout(message, color=color, ctx=self.cli_context)

    def simple_message(self, message: str, color: str = "white") -> None:
        """Output a simple progress message.

        Args:
            message: Message to display
            color: Color for the message
        """
        if not self._should_output():
            return

        pout(f"  {message}", color=color, ctx=self.cli_context)


# 🐝📁🔚
