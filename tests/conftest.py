"""pytest configuration and fixtures."""

import os
import sys

import pytest

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture
def sample_configs():
    """Provide sample network device configurations for testing."""
    config1 = """! Device 1 Configuration
version 15.1
hostname device1
!
interface GigabitEthernet0/1
 ip address 192.168.1.1 255.255.255.0
 no shutdown
!
router ospf 1
 network 192.168.1.0 0.0.0.255 area 0
!
end"""

    config2 = """! Device 2 Configuration
version 15.1
hostname device2
!
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

    return {"config1": config1, "config2": config2}


@pytest.fixture
def sample_device_params():
    """Provide sample device parameters for testing."""
    return {
        "device1": {
            "device_type": "cisco_ios",
            "host": "192.168.1.1",
            "username": "admin",
            "password": "password",
            "timeout": 30,
        },
        "device2": {
            "device_type": "cisco_ios",
            "host": "192.168.1.2",
            "username": "admin",
            "password": "password",
            "timeout": 30,
        },
    }
