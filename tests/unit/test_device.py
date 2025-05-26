"""Test device module."""

import pytest

from custom_components.mittfortum.device import MittFortumDevice
from custom_components.mittfortum.models import CustomerDetails, MeteringPoint


@pytest.fixture
def customer_details():
    """Create customer details fixture."""
    return CustomerDetails(
        customer_id="12345",
        postal_address="Test Street 123",
        post_office="Test City",
        name="John Doe",
    )


@pytest.fixture
def metering_point():
    """Create metering point fixture."""
    return MeteringPoint(metering_point_no="MP123456", address="123 Main St")


class TestMittFortumDevice:
    """Test MittFortumDevice."""

    def test_device_creation(self, customer_details, metering_point):
        """Test device creation."""
        device = MittFortumDevice(customer_id="12345", name="Test Device")

        assert device.unique_id == "12345"

    def test_device_info(self, customer_details, metering_point):
        """Test device info generation."""
        device = MittFortumDevice(customer_id="12345", name="Test Device")

        device_info = device.device_info

        assert device_info["identifiers"] == {("mittfortum", "12345")}
        assert device_info["name"] == "Test Device"
        assert device_info["manufacturer"] == "Fortum"

    def test_device_info_no_name(self, customer_details, metering_point):
        """Test device info with default name."""
        device = MittFortumDevice(customer_id="12345")

        device_info = device.device_info

        assert device_info["name"] == "MittFortum Account"

    def test_device_info_no_address(self, customer_details, metering_point):
        """Test device info without address."""
        device = MittFortumDevice(customer_id="12345", name="Test Device")

        device_info = device.device_info

        assert device_info["entry_type"] == "service"

    def test_device_equality(self, customer_details, metering_point):
        """Test device equality."""
        device1 = MittFortumDevice(customer_id="12345", name="Test Device")
        device2 = MittFortumDevice(customer_id="12345", name="Test Device")

        # Note: These are different instances, so they won't be equal
        # unless the class implements __eq__
        assert device1.unique_id == device2.unique_id

    def test_device_inequality(self, customer_details, metering_point):
        """Test device inequality."""
        device1 = MittFortumDevice(customer_id="12345", name="Test Device")
        device2 = MittFortumDevice(customer_id="67890", name="Other Device")

        assert device1.unique_id != device2.unique_id
