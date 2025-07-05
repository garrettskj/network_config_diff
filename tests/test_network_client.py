"""Tests for network_client module."""

import shutil
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

from netmiko.exceptions import NetmikoAuthenticationException, NetmikoTimeoutException

from lib.network_client import NetworkClient


class TestNetworkClient:
    """Test cases for NetworkClient class."""

    def setup_method(self):
        """Set up test fixtures."""
        # Create temporary directory for testing storage
        self.temp_dir = tempfile.mkdtemp()
        self.client = NetworkClient(storage_dir=self.temp_dir)
        self.sample_device_params = {
            "device_type": "cisco_ios",
            "host": "192.168.1.1",
            "username": "admin",
            "password": "password",
            "timeout": 30,
        }

    def teardown_method(self):
        """Clean up test fixtures."""
        # Remove temporary directory
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_init_default_timeout(self):
        """Test NetworkClient initialization with default timeout."""
        temp_dir = tempfile.mkdtemp()
        try:
            client = NetworkClient(storage_dir=temp_dir)
            assert client.timeout == 30
            assert client.storage_dir == Path(temp_dir)
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_init_custom_timeout(self):
        """Test NetworkClient initialization with custom timeout."""
        temp_dir = tempfile.mkdtemp()
        try:
            client = NetworkClient(timeout=60, storage_dir=temp_dir)
            assert client.timeout == 60
            assert client.storage_dir == Path(temp_dir)
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    @patch("lib.network_client.ConnectHandler")
    def test_get_device_config_success(self, mock_connect_handler):
        """Test successful device configuration retrieval."""
        mock_connection = Mock()
        mock_connection.send_command.return_value = "! Sample config\nversion 15.1"
        mock_connect_handler.return_value = mock_connection

        config, error = self.client.get_device_config(self.sample_device_params)

        assert config == "! Sample config\nversion 15.1"
        assert error is None
        mock_connect_handler.assert_called_once_with(**self.sample_device_params)
        mock_connection.send_command.assert_called_once_with("show running-config")
        mock_connection.disconnect.assert_called_once()

        # Check that configuration was stored
        stored_files = list(Path(self.temp_dir).glob("*.cfg"))
        assert len(stored_files) == 1

        # Verify stored file contents
        with open(stored_files[0]) as f:
            content = f.read()
            assert "! Configuration retrieved from 192.168.1.1 (cisco_ios)" in content
            assert "! Sample config\nversion 15.1" in content

    @patch("lib.network_client.ConnectHandler")
    def test_get_device_config_auth_failure(self, mock_connect_handler):
        """Test device configuration retrieval with authentication failure."""
        mock_connect_handler.side_effect = NetmikoAuthenticationException("Auth failed")

        config, error = self.client.get_device_config(self.sample_device_params)

        assert config is None
        assert error == "Authentication failed"

    @patch("lib.network_client.ConnectHandler")
    def test_get_device_config_timeout(self, mock_connect_handler):
        """Test device configuration retrieval with timeout."""
        mock_connect_handler.side_effect = NetmikoTimeoutException("Timeout")

        config, error = self.client.get_device_config(self.sample_device_params)

        assert config is None
        assert error == "Connection timeout"

    @patch("lib.network_client.ConnectHandler")
    def test_get_device_config_generic_exception(self, mock_connect_handler):
        """Test device configuration retrieval with generic exception."""
        mock_connect_handler.side_effect = Exception("Generic error")

        config, error = self.client.get_device_config(self.sample_device_params)

        assert config is None
        assert error == "Generic error"

    @patch("lib.network_client.ConnectHandler")
    def test_get_device_config_connection_error_during_command(self, mock_connect_handler):
        """Test device configuration retrieval with error during command execution."""
        mock_connection = Mock()
        mock_connection.send_command.side_effect = Exception("Command failed")
        mock_connect_handler.return_value = mock_connection

        config, error = self.client.get_device_config(self.sample_device_params)

        assert config is None
        assert error == "Command failed"

    def test_validate_device_params_valid(self):
        """Test validation of valid device parameters."""
        valid_params = {
            "device_type": "cisco_ios",
            "host": "192.168.1.1",
            "username": "admin",
            "password": "password",
            "timeout": 30,
        }
        assert self.client.validate_device_params(valid_params) is True

    def test_validate_device_params_missing_required_field(self):
        """Test validation of device parameters with missing required field."""
        invalid_params = {
            "device_type": "cisco_ios",
            "host": "192.168.1.1",
            "username": "admin",
            # Missing password
            "timeout": 30,
        }
        assert self.client.validate_device_params(invalid_params) is False

    def test_validate_device_params_empty_required_field(self):
        """Test validation of device parameters with empty required field."""
        invalid_params = {
            "device_type": "cisco_ios",
            "host": "",  # Empty host
            "username": "admin",
            "password": "password",
            "timeout": 30,
        }
        assert self.client.validate_device_params(invalid_params) is False

    def test_validate_device_params_none_value(self):
        """Test validation of device parameters with None value."""
        invalid_params = {
            "device_type": "cisco_ios",
            "host": "192.168.1.1",
            "username": None,  # None username
            "password": "password",
            "timeout": 30,
        }
        assert self.client.validate_device_params(invalid_params) is False

    def test_create_device_params_with_default_timeout(self):
        """Test creating device parameters with default timeout."""
        params = self.client.create_device_params(
            device_type="cisco_ios",
            host="192.168.1.1",
            username="admin",
            password="password"
        )
        expected = {
            "device_type": "cisco_ios",
            "host": "192.168.1.1",
            "username": "admin",
            "password": "password",
            "timeout": 30,
        }
        assert params == expected

    def test_create_device_params_with_custom_timeout(self):
        """Test creating device parameters with custom timeout."""
        params = self.client.create_device_params(
            device_type="cisco_nxos",
            host="192.168.1.2",
            username="admin",
            password="password",
            timeout=60
        )
        expected = {
            "device_type": "cisco_nxos",
            "host": "192.168.1.2",
            "username": "admin",
            "password": "password",
            "timeout": 60,
        }
        assert params == expected

    def test_create_device_params_with_none_timeout(self):
        """Test creating device parameters with None timeout (should use default)."""
        params = self.client.create_device_params(
            device_type="juniper_junos",
            host="192.168.1.3",
            username="admin",
            password="password",
            timeout=None
        )
        expected = {
            "device_type": "juniper_junos",
            "host": "192.168.1.3",
            "username": "admin",
            "password": "password",
            "timeout": 30,
        }
        assert params == expected

    def test_store_config(self):
        """Test configuration storage functionality."""
        config_content = "! Test configuration\nversion 15.1\nhostname test-device"

        # Test storing configuration
        config_file = self.client._store_config("192.168.1.1", "cisco_ios", config_content)

        # Verify file was created
        assert config_file.exists()
        assert config_file.suffix == ".cfg"

        # Verify file contents
        with open(config_file) as f:
            content = f.read()
            assert "! Configuration retrieved from 192.168.1.1 (cisco_ios)" in content
            assert config_content in content

    def test_list_stored_configs(self):
        """Test listing stored configurations."""
        # Initially no configs
        configs = self.client.list_stored_configs()
        assert len(configs) == 0

        # Store some configurations
        self.client._store_config("192.168.1.1", "cisco_ios", "config1")
        self.client._store_config("192.168.1.2", "cisco_ios", "config2")
        self.client._store_config("10.0.0.1", "cisco_nxos", "config3")

        # List all configurations
        all_configs = self.client.list_stored_configs()
        assert len(all_configs) == 3

        # List configurations for specific host
        host_configs = self.client.list_stored_configs("192.168.1.1")
        assert len(host_configs) == 1
        assert "192_168_1_1" in str(host_configs[0])

    def test_list_stored_configs_nonexistent_directory(self):
        """Test listing configurations when storage directory doesn't exist."""
        # Create client and then delete the storage directory to simulate the scenario
        temp_dir = tempfile.mkdtemp()
        temp_client = NetworkClient(storage_dir=temp_dir)

        # Remove the directory after creation
        shutil.rmtree(temp_dir)

        # Now try to list configs - should handle missing directory gracefully
        configs = temp_client.list_stored_configs()
        assert len(configs) == 0

    def test_validate_config_content_valid(self):
        """Test configuration content validation with valid content."""
        valid_config = """! Valid Cisco configuration
version 15.1
hostname test-router
interface GigabitEthernet0/1
 ip address 192.168.1.1 255.255.255.0
 no shutdown
!
router ospf 1
 network 192.168.1.0 0.0.0.255 area 0
!"""

        assert self.client.validate_config_content(valid_config) is True

    def test_validate_config_content_invalid(self):
        """Test configuration content validation with invalid content."""
        invalid_configs = [
            "",  # Empty content
            "   ",  # Whitespace only
            "This is just plain text with no configuration indicators",
            "version 15.1",  # Only one indicator
        ]

        for invalid_config in invalid_configs:
            assert self.client.validate_config_content(invalid_config) is False

    def test_validate_config_content_minimal_valid(self):
        """Test configuration content validation with minimal valid content."""
        minimal_config = """hostname router1
interface eth0"""

        assert self.client.validate_config_content(minimal_config) is True

    def test_store_uploaded_config(self):
        """Test storing uploaded configuration files."""
        filename = "router-config.txt"
        content = "hostname test-router\ninterface eth0\nip address 192.168.1.1"
        device_name = "Test Router"

        # Store the configuration
        stored_file = self.client.store_uploaded_config(filename, content, device_name)

        # Verify file was created
        assert stored_file.exists()
        assert stored_file.suffix == ".cfg"
        assert "Test_Router_uploaded_" in stored_file.name

        # Verify file contents
        with open(stored_file) as f:
            stored_content = f.read()
            assert f"! Configuration uploaded from file: {filename}" in stored_content
            assert f"! Device name: {device_name}" in stored_content
            assert content in stored_content

    def test_store_uploaded_config_no_device_name(self):
        """Test storing uploaded configuration without device name."""
        filename = "switch-config.cfg"
        content = "hostname test-switch\nvlan 10"

        # Store without device name
        stored_file = self.client.store_uploaded_config(filename, content)

        # Verify file was created with filename-based naming
        assert stored_file.exists()
        assert "switch-config_uploaded_" in stored_file.name

        # Verify file contents
        with open(stored_file) as f:
            stored_content = f.read()
            assert f"! Configuration uploaded from file: {filename}" in stored_content
            assert "! Device name:" not in stored_content  # Should not have device name line
            assert content in stored_content

    def test_store_uploaded_config_special_characters(self):
        """Test storing uploaded configuration with special characters in names."""
        filename = "router config v2.1.txt"
        content = "hostname router-test"
        device_name = "Test Router: Version 2.1"

        # Store with special characters
        stored_file = self.client.store_uploaded_config(filename, content, device_name)

        # Verify special characters are handled
        assert stored_file.exists()
        assert "Test_Router__Version_2_1_uploaded_" in stored_file.name
