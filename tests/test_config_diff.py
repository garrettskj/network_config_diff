"""Tests for config_diff module."""

from lib.config_diff import ConfigDiffer


class TestConfigDiffer:
    """Test cases for ConfigDiffer class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.differ = ConfigDiffer()
        self.config1 = """! Device 1 Configuration
version 15.1
hostname device1
interface GigabitEthernet0/1
 ip address 192.168.1.1 255.255.255.0
 no shutdown
!
router ospf 1
 network 192.168.1.0 0.0.0.255 area 0
!
end"""

        self.config2 = """! Device 2 Configuration
version 15.1
hostname device2
interface GigabitEthernet0/1
 ip address 192.168.1.2 255.255.255.0
 no shutdown
!
interface GigabitEthernet0/2
 ip address 192.168.2.1 255.255.255.0
 no shutdown
!
router ospf 1
 network 192.168.1.0 0.0.0.255 area 0
 network 192.168.2.0 0.0.0.255 area 0
!
end"""

    def test_init(self):
        """Test ConfigDiffer initialization."""
        differ = ConfigDiffer()
        assert differ is not None

    def test_generate_unified_diff(self):
        """Test unified diff generation."""
        diff_lines = list(self.differ.generate_unified_diff(
            self.config1, self.config2, "device1", "device2"
        ))

        # Should have diff header lines
        assert any("device1 Configuration" in line for line in diff_lines)
        assert any("device2 Configuration" in line for line in diff_lines)

        # Should have changes
        assert any(line.startswith("-hostname device1") for line in diff_lines)
        assert any(line.startswith("+hostname device2") for line in diff_lines)

    def test_generate_unified_diff_identical_configs(self):
        """Test unified diff generation with identical configurations."""
        diff_lines = list(self.differ.generate_unified_diff(
            self.config1, self.config1, "device1", "device1"
        ))

        # Should have no diff lines for identical configs
        assert len(diff_lines) == 0

    def test_generate_diff_html(self):
        """Test HTML diff generation."""
        html_diff = self.differ.generate_diff_html(
            self.config1, self.config2, "device1", "device2"
        )

        # Should contain HTML diff elements
        assert 'class="diff-header"' in html_diff
        assert 'class="diff-added"' in html_diff
        assert 'class="diff-removed"' in html_diff

        # Should contain escaped content
        assert "device1 Configuration" in html_diff
        assert "device2 Configuration" in html_diff

    def test_generate_diff_html_identical_configs(self):
        """Test HTML diff generation with identical configurations."""
        html_diff = self.differ.generate_diff_html(
            self.config1, self.config1, "device1", "device1"
        )

        # Should be empty string for identical configs
        assert html_diff == ""

    def test_generate_diff_html_with_special_characters(self):
        """Test HTML diff generation with special HTML characters."""
        config_with_html = """! Configuration with <special> chars
version 15.1
hostname "device with quotes"
description This & that
!
end"""

        config_with_html_modified = """! Configuration with <special> chars
version 15.2
hostname "device with quotes"
description This & that
!
end"""

        html_diff = self.differ.generate_diff_html(
            config_with_html, config_with_html_modified, "device1", "device2"
        )

        # Should properly escape HTML characters
        assert "&lt;special&gt;" in html_diff
        assert "&quot;device with quotes&quot;" in html_diff
        assert "This &amp; that" in html_diff

    def test_generate_side_by_side_diff(self):
        """Test side-by-side HTML diff generation."""
        html_diff = self.differ.generate_side_by_side_diff(
            self.config1, self.config2, "device1", "device2"
        )

        # Should contain HTML table structure
        assert "<table" in html_diff
        assert "<tr>" in html_diff
        assert "<td" in html_diff

        # Should contain device names
        assert "device1 Configuration" in html_diff
        assert "device2 Configuration" in html_diff

    def test_get_diff_statistics(self):
        """Test diff statistics calculation."""
        stats = self.differ.get_diff_statistics(self.config1, self.config2)

        # Should have proper statistics structure
        assert "added_lines" in stats
        assert "removed_lines" in stats
        assert "total_changes" in stats
        assert "has_differences" in stats

        # Should detect differences
        assert stats["has_differences"] is True
        assert stats["total_changes"] > 0
        assert stats["added_lines"] > 0
        assert stats["removed_lines"] > 0

    def test_get_diff_statistics_identical_configs(self):
        """Test diff statistics with identical configurations."""
        stats = self.differ.get_diff_statistics(self.config1, self.config1)

        # Should show no differences
        assert stats["has_differences"] is False
        assert stats["total_changes"] == 0
        assert stats["added_lines"] == 0
        assert stats["removed_lines"] == 0

    def test_get_diff_statistics_only_additions(self):
        """Test diff statistics with only additions."""
        simple_config = "version 15.1\nhostname device1"
        extended_config = "version 15.1\nhostname device1\ninterface Gi0/1\n ip address 192.168.1.1 255.255.255.0"

        stats = self.differ.get_diff_statistics(simple_config, extended_config)

        # Should show differences with mostly additions
        assert stats["has_differences"] is True
        assert stats["added_lines"] >= stats["removed_lines"]
        assert stats["total_changes"] > 0

    def test_get_diff_statistics_only_removals(self):
        """Test diff statistics with only removals."""
        extended_config = "version 15.1\nhostname device1\ninterface Gi0/1\n ip address 192.168.1.1 255.255.255.0"
        simple_config = "version 15.1\nhostname device1"

        stats = self.differ.get_diff_statistics(extended_config, simple_config)

        # Should show differences with mostly removals
        assert stats["has_differences"] is True
        assert stats["removed_lines"] >= stats["added_lines"]
        assert stats["total_changes"] > 0

    def test_escape_html_basic_characters(self):
        """Test HTML escaping of basic characters."""
        text = "<div>Hello & goodbye</div>"
        escaped = self.differ._escape_html(text)

        expected = "&lt;div&gt;Hello &amp; goodbye&lt;/div&gt;"
        assert escaped == expected

    def test_escape_html_quotes(self):
        """Test HTML escaping of quotes."""
        text = 'description "This is a test" with \'single quotes\''
        escaped = self.differ._escape_html(text)

        expected = "description &quot;This is a test&quot; with &#x27;single quotes&#x27;"
        assert escaped == expected

    def test_escape_html_empty_string(self):
        """Test HTML escaping of empty string."""
        text = ""
        escaped = self.differ._escape_html(text)

        assert escaped == ""

    def test_escape_html_no_special_characters(self):
        """Test HTML escaping of text without special characters."""
        text = "This is normal text with numbers 123 and symbols @#$%"
        escaped = self.differ._escape_html(text)

        # Should remain unchanged
        assert escaped == text
