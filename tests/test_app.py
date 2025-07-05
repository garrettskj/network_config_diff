"""Tests for Flask application."""

import json
from io import BytesIO
from pathlib import Path
from unittest.mock import patch

from app import app


class TestFlaskApp:
    """Test cases for Flask application."""

    def setup_method(self):
        """Set up test fixtures."""
        self.app = app
        self.app.config["TESTING"] = True
        self.client = self.app.test_client()

        # Sample form data
        self.sample_form_data = {
            "device1_type": "cisco_ios",
            "device1_ip": "192.168.1.1",
            "device1_username": "admin",
            "device1_password": "password",
            "device2_type": "cisco_ios",
            "device2_ip": "192.168.1.2",
            "device2_username": "admin",
            "device2_password": "password",
        }

    def test_index_route(self):
        """Test the index route."""
        response = self.client.get("/")
        assert response.status_code == 200
        assert b"Network Device Configuration Comparison" in response.data

    def test_diff_route(self):
        """Test the diff route."""
        response = self.client.get("/diff")
        assert response.status_code == 200
        assert b"Configuration Difference" in response.data

    @patch("app.network_client.get_device_config")
    @patch("app.config_differ.generate_diff_html")
    @patch("app.config_differ.get_diff_statistics")
    def test_compare_configs_success(self, mock_get_stats, mock_gen_diff, mock_get_config):
        """Test successful configuration comparison."""
        # Mock network client responses
        mock_get_config.side_effect = [
            ("config1 content", None),  # Device 1 success
            ("config2 content", None),  # Device 2 success
        ]

        # Mock diff generation
        mock_gen_diff.return_value = "<div>Mock diff HTML</div>"
        mock_get_stats.return_value = {
            "added_lines": 5,
            "removed_lines": 3,
            "total_changes": 8,
            "has_differences": True,
        }

        response = self.client.post("/compare", data=self.sample_form_data)

        assert response.status_code == 200
        data = json.loads(response.data)

        assert data["error"] is False
        assert data["diff_html"] == "<div>Mock diff HTML</div>"
        assert data["device1_name"] == "192.168.1.1"
        assert data["device2_name"] == "192.168.1.2"
        assert data["diff_stats"]["total_changes"] == 8

    @patch("app.network_client.get_device_config")
    def test_compare_configs_device1_error(self, mock_get_config):
        """Test configuration comparison with device 1 error."""
        mock_get_config.side_effect = [
            (None, "Authentication failed"),  # Device 1 error
            ("config2 content", None),        # Device 2 success
        ]

        response = self.client.post("/compare", data=self.sample_form_data)

        assert response.status_code == 200
        data = json.loads(response.data)

        assert data["error"] is True
        assert data["device1_error"] == "Authentication failed"
        assert data["device2_error"] is None

    @patch("app.network_client.get_device_config")
    def test_compare_configs_device2_error(self, mock_get_config):
        """Test configuration comparison with device 2 error."""
        mock_get_config.side_effect = [
            ("config1 content", None),     # Device 1 success
            (None, "Connection timeout"),  # Device 2 error
        ]

        response = self.client.post("/compare", data=self.sample_form_data)

        assert response.status_code == 200
        data = json.loads(response.data)

        assert data["error"] is True
        assert data["device1_error"] is None
        assert data["device2_error"] == "Connection timeout"

    @patch("app.network_client.get_device_config")
    def test_compare_configs_both_devices_error(self, mock_get_config):
        """Test configuration comparison with both devices error."""
        mock_get_config.side_effect = [
            (None, "Authentication failed"),  # Device 1 error
            (None, "Connection timeout"),     # Device 2 error
        ]

        response = self.client.post("/compare", data=self.sample_form_data)

        assert response.status_code == 200
        data = json.loads(response.data)

        assert data["error"] is True
        assert data["device1_error"] == "Authentication failed"
        assert data["device2_error"] == "Connection timeout"

    def test_compare_configs_missing_required_fields(self):
        """Test configuration comparison with missing required fields."""
        incomplete_data = {
            "device1_type": "cisco_ios",
            "device1_ip": "192.168.1.1",
            # Missing device1_username and device1_password
            "device2_type": "cisco_ios",
            "device2_ip": "192.168.1.2",
            "device2_username": "admin",
            "device2_password": "password",
        }

        response = self.client.post("/compare", data=incomplete_data)

        # Should return 200 with error details (app doesn't validate required fields, SSH connection fails)
        assert response.status_code == 200
        data = response.get_json()
        assert data["error"] is True
        assert data["device1_error"] == "Authentication failed"  # SSH fails due to missing credentials

    @patch("app.network_client.get_device_config")
    @patch("app.config_differ.generate_diff_html")
    @patch("app.config_differ.get_diff_statistics")
    def test_compare_configs_with_custom_device_types(self, mock_get_stats, mock_gen_diff, mock_get_config):
        """Test configuration comparison with custom device types."""
        custom_form_data = self.sample_form_data.copy()
        custom_form_data["device1_type"] = "cisco_nxos"
        custom_form_data["device2_type"] = "juniper_junos"

        mock_get_config.side_effect = [
            ("nxos config", None),
            ("junos config", None),
        ]
        mock_gen_diff.return_value = "<div>Custom diff</div>"
        mock_get_stats.return_value = {
            "added_lines": 2,
            "removed_lines": 1,
            "total_changes": 3,
            "has_differences": True,
        }

        response = self.client.post("/compare", data=custom_form_data)

        assert response.status_code == 200
        data = json.loads(response.data)

        assert data["error"] is False
        assert data["diff_html"] == "<div>Custom diff</div>"

    @patch("app.network_client.get_device_config")
    @patch("app.config_differ.generate_diff_html")
    @patch("app.config_differ.get_diff_statistics")
    def test_compare_configs_identical_configs(self, mock_get_stats, mock_gen_diff, mock_get_config):
        """Test configuration comparison with identical configurations."""
        identical_config = "version 15.1\nhostname device"

        mock_get_config.side_effect = [
            (identical_config, None),
            (identical_config, None),
        ]
        mock_gen_diff.return_value = ""  # Empty diff for identical configs
        mock_get_stats.return_value = {
            "added_lines": 0,
            "removed_lines": 0,
            "total_changes": 0,
            "has_differences": False,
        }

        response = self.client.post("/compare", data=self.sample_form_data)

        assert response.status_code == 200
        data = json.loads(response.data)

        assert data["error"] is False
        assert data["diff_html"] == ""
        assert data["diff_stats"]["has_differences"] is False

    def test_compare_configs_get_method_not_allowed(self):
        """Test that GET method is not allowed for compare route."""
        response = self.client.get("/compare")
        assert response.status_code == 405  # Method Not Allowed

    @patch("app.network_client.get_device_config")
    @patch("app.config_differ.generate_diff_html")
    @patch("app.config_differ.get_diff_statistics")
    def test_compare_configs_threading(self, mock_get_stats, mock_gen_diff, mock_get_config):
        """Test that configuration comparison works with threading."""
        mock_get_config.side_effect = [
            ("config1", None),
            ("config2", None),
        ]
        mock_gen_diff.return_value = "<div>Mock diff HTML</div>"
        mock_get_stats.return_value = {
            "added_lines": 2,
            "removed_lines": 1,
            "total_changes": 3,
            "has_differences": True,
        }

        response = self.client.post("/compare", data=self.sample_form_data)

        # Verify successful response
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["error"] is False

        # Verify that both devices were called
        assert mock_get_config.call_count == 2

    def test_app_configuration(self):
        """Test Flask application configuration."""
        assert self.app.config["TESTING"] is True
        assert self.app.name == "app"

    def test_404_error(self):
        """Test 404 error handling."""
        response = self.client.get("/nonexistent")
        assert response.status_code == 404

    @patch("app.network_client.validate_config_content")
    @patch("app.network_client.store_uploaded_config")
    @patch("app.config_differ.generate_diff_html")
    @patch("app.config_differ.get_diff_statistics")
    def test_compare_configs_file_upload_success(self, mock_get_stats, mock_gen_diff, mock_store_config, mock_validate):
        """Test successful configuration comparison with file uploads."""
        # Mock the validation and storage
        mock_validate.return_value = True
        mock_store_config.return_value = Path("/tmp/test_config.cfg")
        mock_gen_diff.return_value = "<div>Test diff</div>"
        mock_get_stats.return_value = {"added": 5, "removed": 3}

        # Create test configuration files
        config1 = b"hostname router1\ninterface eth0\nip address 192.168.1.1"
        config2 = b"hostname router2\ninterface eth0\nip address 192.168.1.2"

        file_data = {
            "device1_method": "file",
            "device2_method": "file",
            "device1_name": "Router 1",
            "device2_name": "Router 2",
        }

        # Use Flask's test client to simulate file upload
        file_data['device1_config'] = (BytesIO(config1), 'router1.cfg')
        file_data['device2_config'] = (BytesIO(config2), 'router2.cfg')

        response = self.client.post("/compare",
                                  data=file_data,
                                  content_type='multipart/form-data')

        assert response.status_code == 200
        data = response.get_json()
        assert data["error"] is False
        assert data["device1_name"] == "Router 1"
        assert data["device2_name"] == "Router 2"
        assert data["diff_html"] == "<div>Test diff</div>"
        assert data["diff_stats"] == {"added": 5, "removed": 3}

    def test_compare_configs_file_upload_missing_files(self):
        """Test file upload with missing files."""
        file_data = {
            "device1_method": "file",
            "device2_method": "file",
        }

        response = self.client.post("/compare",
                                  data=file_data,
                                  content_type='multipart/form-data')

        assert response.status_code == 200
        data = response.get_json()
        assert data["error"] is True
        assert data["device1_error"] == "Configuration file required"

    @patch("app.network_client.validate_config_content")
    def test_compare_configs_file_upload_invalid_content(self, mock_validate):
        """Test file upload with invalid configuration content."""
        mock_validate.return_value = False

        config1 = b"This is not a valid network configuration"
        config2 = b"hostname router2\ninterface eth0"

        file_data = {
            "device1_method": "file",
            "device2_method": "file",
        }

        file_data['device1_config'] = (BytesIO(config1), 'invalid.txt')
        file_data['device2_config'] = (BytesIO(config2), 'router2.cfg')

        response = self.client.post("/compare",
                                  data=file_data,
                                  content_type='multipart/form-data')

        assert response.status_code == 200
        data = response.get_json()
        assert data["error"] is True
        assert data["device1_error"] == "File does not appear to contain valid network configuration"

    @patch("app.network_client.get_device_config")
    @patch("app.network_client.validate_config_content")
    @patch("app.network_client.store_uploaded_config")
    @patch("app.config_differ.generate_diff_html")
    @patch("app.config_differ.get_diff_statistics")
    def test_compare_configs_mixed_methods(self, mock_get_stats, mock_gen_diff, mock_store_config, mock_validate, mock_get_config):
        """Test configuration comparison with SSH and file upload mixed."""
        # Mock SSH connection
        mock_get_config.return_value = ("hostname device1\ninterface eth0", None)

        # Mock file validation and storage
        mock_validate.return_value = True
        mock_store_config.return_value = Path("/tmp/test_config.cfg")
        mock_gen_diff.return_value = "<div>Mixed diff</div>"
        mock_get_stats.return_value = {"added": 2, "removed": 1}

        config2 = b"hostname device2\ninterface eth1"

        mixed_data = {
            "device1_method": "ssh",
            "device1_type": "cisco_ios",
            "device1_ip": "192.168.1.1",
            "device1_username": "admin",
            "device1_password": "password",
            "device2_method": "file",
            "device2_name": "Device 2",
        }

        mixed_data['device2_config'] = (BytesIO(config2), 'device2.cfg')

        response = self.client.post("/compare",
                                  data=mixed_data,
                                  content_type='multipart/form-data')

        assert response.status_code == 200
        data = response.get_json()
        assert data["error"] is False
        assert data["device1_name"] == "192.168.1.1"
        assert data["device2_name"] == "Device 2"
        assert data["diff_html"] == "<div>Mixed diff</div>"
