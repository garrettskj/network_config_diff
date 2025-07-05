"""Configuration diff module for comparing network device configurations."""

import difflib
from collections.abc import Iterator

from logzero import logger


class ConfigDiffer:
    """Handles configuration comparison and diff generation."""

    def __init__(self) -> None:
        """Initialize configuration differ."""
        logger.info("ConfigDiffer initialized")

    def generate_unified_diff(
        self, config1: str, config2: str, device1_name: str, device2_name: str
    ) -> Iterator[str]:
        """
        Generate unified diff between two configurations.

        Args:
            config1: First configuration string
            config2: Second configuration string
            device1_name: Name/identifier for first device
            device2_name: Name/identifier for second device

        Returns:
            Iterator of diff lines
        """
        logger.debug(f"Generating unified diff between {device1_name} and {device2_name}")
        logger.debug(f"Config1 size: {len(config1)} chars, Config2 size: {len(config2)} chars")

        return difflib.unified_diff(
            config1.splitlines(keepends=True),
            config2.splitlines(keepends=True),
            fromfile=f"{device1_name} Configuration",
            tofile=f"{device2_name} Configuration",
            lineterm="",
        )

    def generate_diff_html(
        self, config1: str, config2: str, device1_name: str, device2_name: str
    ) -> str:
        """
        Generate HTML diff between two configurations with color coding.

        Args:
            config1: First configuration string
            config2: Second configuration string
            device1_name: Name/identifier for first device
            device2_name: Name/identifier for second device

        Returns:
            HTML string containing color-coded diff
        """
        logger.info(f"Generating HTML diff between {device1_name} and {device2_name}")

        diff_lines = self.generate_unified_diff(
            config1, config2, device1_name, device2_name
        )

        html_diff: list[str] = []
        line_count = 0

        for line in diff_lines:
            line_count += 1
            if line.startswith("+++") or line.startswith("---"):
                html_diff.append(
                    f'<div class="diff-header">{self._escape_html(line)}</div>'
                )
            elif line.startswith("@@"):
                html_diff.append(
                    f'<div class="diff-info">{self._escape_html(line)}</div>'
                )
            elif line.startswith("+"):
                html_diff.append(
                    f'<div class="diff-added">{self._escape_html(line)}</div>'
                )
            elif line.startswith("-"):
                html_diff.append(
                    f'<div class="diff-removed">{self._escape_html(line)}</div>'
                )
            else:
                html_diff.append(
                    f'<div class="diff-context">{self._escape_html(line)}</div>'
                )

        result = "".join(html_diff)
        logger.info(f"HTML diff generation complete: {line_count} diff lines, {len(result)} chars output")
        return result

    def generate_side_by_side_diff(
        self, config1: str, config2: str, device1_name: str, device2_name: str
    ) -> str:
        """
        Generate side-by-side HTML diff between two configurations.

        Args:
            config1: First configuration string
            config2: Second configuration string
            device1_name: Name/identifier for first device
            device2_name: Name/identifier for second device

        Returns:
            HTML string containing side-by-side diff
        """
        html_differ = difflib.HtmlDiff()
        return html_differ.make_file(
            config1.splitlines(),
            config2.splitlines(),
            fromdesc=f"{device1_name} Configuration",
            todesc=f"{device2_name} Configuration",
        )

    def get_diff_statistics(self, config1: str, config2: str) -> dict:
        """
        Get statistics about the differences between two configurations.

        Args:
            config1: First configuration string
            config2: Second configuration string

        Returns:
            Dictionary containing diff statistics
        """
        logger.debug("Calculating diff statistics")

        diff_lines = list(
            self.generate_unified_diff(config1, config2, "Device1", "Device2")
        )

        added_lines = sum(
            1
            for line in diff_lines
            if line.startswith("+") and not line.startswith("+++")
        )
        removed_lines = sum(
            1
            for line in diff_lines
            if line.startswith("-") and not line.startswith("---")
        )

        stats = {
            "added_lines": added_lines,
            "removed_lines": removed_lines,
            "total_changes": added_lines + removed_lines,
            "has_differences": added_lines + removed_lines > 0,
        }

        logger.info(f"Diff statistics calculated: {stats}")
        return stats

    def _escape_html(self, text: str) -> str:
        """
        Escape HTML special characters in text.

        Args:
            text: Text to escape

        Returns:
            HTML-escaped text
        """
        return (
            text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&#x27;")
        )
