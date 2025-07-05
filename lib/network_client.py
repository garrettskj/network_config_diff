"""Network device client module for SSH connectivity and configuration retrieval."""

from datetime import datetime
from pathlib import Path
from typing import Any

from logzero import logger
from netmiko import ConnectHandler
from netmiko.exceptions import NetmikoAuthenticationException, NetmikoTimeoutException


class NetworkClient:
    """Client for connecting to network devices and retrieving configurations."""

    def __init__(self, timeout: int = 30, storage_dir: str = "stored_configs") -> None:
        """Initialize network client with default timeout and storage directory."""
        self.timeout = timeout
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(exist_ok=True)
        logger.info(f"NetworkClient initialized with timeout={timeout}s, storage_dir={storage_dir}")

    def get_device_config(
        self, device_params: dict[str, Any]
    ) -> tuple[str | None, str | None]:
        """
        Connect to network device and retrieve running configuration.

        Args:
            device_params: Dictionary containing device connection parameters
                - device_type: Type of device (e.g., 'cisco_ios')
                - host: Device IP address
                - username: SSH username
                - password: SSH password
                - timeout: Connection timeout (optional)

        Returns:
            Tuple of (config_string, error_message)
            - config_string: Device configuration if successful, None if failed
            - error_message: Error description if failed, None if successful
        """
        host = device_params.get("host", "unknown")
        device_type = device_params.get("device_type", "unknown")

        logger.info(f"Attempting to connect to device {host} (type: {device_type})")

        try:
            logger.debug(f"Creating SSH connection to {host}")
            
            # For legacy devices, we need to configure paramiko directly
            if device_type in ["cisco_ios", "cisco_asa"]:
                # Import paramiko to configure algorithms
                import paramiko
                
                # Configure paramiko to allow legacy algorithms
                transport = paramiko.Transport.from_config = staticmethod(lambda config: None)
                
                # Enable legacy key exchange algorithms
                paramiko.Transport._preferred_kex = (
                    'diffie-hellman-group14-sha1',
                    'diffie-hellman-group1-sha1',
                    'diffie-hellman-group-exchange-sha1',
                    'diffie-hellman-group-exchange-sha256',
                ) + paramiko.Transport._preferred_kex
                
                # Enable legacy server host key algorithms
                paramiko.Transport._preferred_keys = (
                    'ssh-rsa',
                    'ssh-dss',
                ) + paramiko.Transport._preferred_keys
                
                logger.debug(f"Configured legacy SSH algorithms for {device_type}")
            
            connection = ConnectHandler(**device_params)

            logger.info(f"Successfully connected to {host}, retrieving configuration")
            config: str = connection.send_command("show running-config")

            logger.debug(f"Disconnecting from {host}")
            connection.disconnect()

            # Store configuration to file
            config_file = self._store_config(host, device_type, config)
            logger.info(f"Configuration retrieved and stored to {config_file}")

            return config, None

        except NetmikoAuthenticationException as e:
            error_msg = "Authentication failed"
            logger.error(f"Authentication failed for {host}: {str(e)}")
            return None, error_msg

        except NetmikoTimeoutException as e:
            error_msg = "Connection timeout"
            logger.error(f"Connection timeout for {host}: {str(e)}")
            return None, error_msg

        except Exception as e:
            error_msg = str(e)
            logger.error(f"Unexpected error connecting to {host}: {error_msg}")
            return None, error_msg

    def _store_config(self, host: str, device_type: str, config: str) -> Path:
        """
        Store device configuration to file.
        
        Args:
            host: Device IP address or hostname
            device_type: Type of network device
            config: Configuration content to store
            
        Returns:
            Path to stored configuration file
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        # Sanitize hostname for filename
        safe_host = host.replace(".", "_").replace(":", "_")
        filename = f"{safe_host}_{device_type}_{timestamp}.cfg"
        config_file = self.storage_dir / filename

        logger.debug(f"Storing configuration to {config_file}")

        try:
            with open(config_file, 'w', encoding='utf-8') as f:
                f.write(f"! Configuration retrieved from {host} ({device_type})\n")
                f.write(f"! Retrieved on {datetime.now().isoformat()}\n")
                f.write("!\n")
                f.write(config)

            logger.debug(f"Successfully stored {len(config)} characters to {config_file}")
            return config_file

        except Exception as e:
            logger.error(f"Failed to store configuration to {config_file}: {str(e)}")
            raise

    def validate_device_params(self, device_params: dict[str, Any]) -> bool:
        """
        Validate that device parameters contain required fields.

        Args:
            device_params: Dictionary containing device connection parameters

        Returns:
            True if all required parameters are present, False otherwise
        """
        required_fields = ["device_type", "host", "username", "password"]
        logger.debug(f"Validating device parameters: {list(device_params.keys())}")

        valid = all(
            field in device_params and device_params[field] for field in required_fields
        )

        if not valid:
            missing_fields = [field for field in required_fields
                            if field not in device_params or not device_params[field]]
            logger.warning(f"Validation failed - missing required fields: {missing_fields}")
        else:
            logger.debug("Device parameters validation successful")

        return valid

    def create_device_params(
        self,
        device_type: str,
        host: str,
        username: str,
        password: str,
        timeout: int | None = None,
    ) -> dict[str, Any]:
        """
        Create device parameters dictionary with proper typing.

        Args:
            device_type: Type of network device
            host: Device IP address or hostname
            username: SSH username
            password: SSH password
            timeout: Connection timeout (uses instance default if not provided)

        Returns:
            Dictionary containing device connection parameters
        """
        actual_timeout = timeout or self.timeout
        logger.debug(f"Creating device parameters for {host} (type: {device_type}, timeout: {actual_timeout}s)")

        # Define default SSH algorithms for different device types
        ssh_config = self._get_ssh_config(device_type)

        params = {
            "device_type": device_type,
            "host": host,
            "username": username,
            "password": "***",  # Don't log the actual password
            "timeout": actual_timeout,
        }
        
        # Add SSH algorithm configurations if provided
        if ssh_config:
            params.update(ssh_config)
            logger.debug(f"Applied SSH config for {device_type}: {ssh_config}")
        
        logger.debug(f"Device parameters created: {params}")

        # Return actual parameters with real password
        actual_params = {
            "device_type": device_type,
            "host": host,
            "username": username,
            "password": password,
            "timeout": actual_timeout,
        }
        
        # Add SSH algorithm configurations if provided
        if ssh_config:
            actual_params.update(ssh_config)
        
        return actual_params

    def list_stored_configs(self, host: str | None = None) -> list[Path]:
        """
        List stored configuration files.
        
        Args:
            host: Optional host filter (if provided, only return configs for this host)
            
        Returns:
            List of configuration file paths
        """
        logger.debug(f"Listing stored configurations in {self.storage_dir}")

        if not self.storage_dir.exists():
            logger.warning(f"Storage directory {self.storage_dir} does not exist")
            return []

        pattern = "*.cfg"
        if host:
            safe_host = host.replace(".", "_").replace(":", "_")
            pattern = f"{safe_host}_*.cfg"

        config_files = list(self.storage_dir.glob(pattern))
        logger.info(f"Found {len(config_files)} stored configuration files")

        return sorted(config_files, key=lambda p: p.stat().st_mtime, reverse=True)

    def validate_config_content(self, content: str) -> bool:
        """
        Validate configuration file content.
        
        Args:
            content: Configuration content to validate
            
        Returns:
            True if content appears to be a valid configuration
        """
        if not content or not content.strip():
            logger.warning("Configuration content is empty")
            return False

        # Basic validation - look for common configuration patterns
        config_indicators = [
            "version",
            "hostname",
            "interface",
            "router",
            "access-list",
            "ip route",
            "vlan",
            "spanning-tree",
            "!",  # Comment marker common in Cisco configs
        ]

        content_lower = content.lower()
        found_indicators = sum(1 for indicator in config_indicators if indicator in content_lower)

        # Require at least 2 configuration indicators
        if found_indicators >= 2:
            logger.debug(f"Configuration validation passed ({found_indicators} indicators found)")
            return True
        else:
            logger.warning(f"Configuration validation failed (only {found_indicators} indicators found)")
            return False

    def store_uploaded_config(self, filename: str, content: str, device_name: str | None = None) -> Path:
        """
        Store uploaded configuration file with metadata.
        
        Args:
            filename: Original filename
            content: Configuration content
            device_name: Optional device name override
            
        Returns:
            Path to stored configuration file
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Use device name if provided, otherwise use filename without extension
        if device_name:
            safe_name = device_name.replace(".", "_").replace(":", "_").replace(" ", "_")
        else:
            safe_name = Path(filename).stem.replace(".", "_").replace(":", "_").replace(" ", "_")

        stored_filename = f"{safe_name}_uploaded_{timestamp}.cfg"
        config_file = self.storage_dir / stored_filename

        logger.debug(f"Storing uploaded configuration to {config_file}")

        try:
            with open(config_file, 'w', encoding='utf-8') as f:
                f.write(f"! Configuration uploaded from file: {filename}\n")
                if device_name:
                    f.write(f"! Device name: {device_name}\n")
                f.write(f"! Uploaded on {datetime.now().isoformat()}\n")
                f.write("!\n")
                f.write(content)

            logger.info(f"Successfully stored uploaded configuration: {len(content)} characters to {config_file}")
            return config_file

        except Exception as e:
            logger.error(f"Failed to store uploaded configuration to {config_file}: {str(e)}")
            raise

    def _get_ssh_config(self, device_type: str) -> dict[str, Any]:
        """
        Get SSH algorithm configuration for specific device types.
        
        Args:
            device_type: Type of network device
            
        Returns:
            Dictionary with SSH algorithm configurations
        """
        ssh_configs = {
            "cisco_ios": {
                "ssh_config_file": False,
                "use_keys": False,
                "key_file": None,
                "allow_agent": False,
                "system_host_keys": False,
                "alt_host_keys": False,
                "alt_key_file": "",
                "ssh_strict": False,
                "conn_timeout": 60,
            },
            "cisco_nxos": {
                "ssh_config_file": False,
                "use_keys": False,
                "key_file": None,
                "allow_agent": False,
                "system_host_keys": False,
                "alt_host_keys": False,
                "alt_key_file": "",
                "ssh_strict": False,
                "conn_timeout": 60,
            },
            "cisco_asa": {
                "ssh_config_file": False,
                "use_keys": False,
                "key_file": None,
                "allow_agent": False,
                "system_host_keys": False,
                "alt_host_keys": False,
                "alt_key_file": "",
                "ssh_strict": False,
                "conn_timeout": 60,
            },
            "juniper_junos": {
                "ssh_config_file": False,
                "use_keys": False,
                "key_file": None,
                "allow_agent": False,
                "system_host_keys": False,
                "alt_host_keys": False,
                "alt_key_file": "",
                "ssh_strict": False,
                "conn_timeout": 60,
            },
        }
        
        config = ssh_configs.get(device_type, {})
        
        # Add algorithm configurations for older/legacy devices
        if device_type in ["cisco_ios", "cisco_asa"]:
            config.update({
                "disabled_algorithms": {
                    "kex": [],
                    "server_host_key_algorithms": [],
                    "encryption": [],
                    "mac": [],
                    "compression": []
                },
                # Enable legacy algorithms for older devices
                "ssh_config_file": None,
                "use_keys": False,
                "allow_agent": False,
                "banner_timeout": 15,
                "auth_timeout": 60,
                "blocking_timeout": 20,
                "fast_cli": False,
                "global_delay_factor": 2
            })
        
        logger.debug(f"SSH config for {device_type}: {config}")
        return config
