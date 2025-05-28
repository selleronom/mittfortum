"""Test cost sensors."""

from datetime import datetime
from unittest.mock import Mock

import pytest
from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass

from custom_components.mittfortum.device import MittFortumDevice
from custom_components.mittfortum.models import ConsumptionData
from custom_components.mittfortum.sensors.cost import MittFortumCostSensor


@pytest.fixture
def mock_coordinator():
    """Create a mock coordinator."""
    coordinator = Mock()
    coordinator.data = [
        ConsumptionData(value=150.5, unit="kWh", date_time=datetime.now(), cost=25.50),
        ConsumptionData(value=200.0, unit="kWh", date_time=datetime.now(), cost=30.00),
    ]
    coordinator.last_update_success = True
    return coordinator


@pytest.fixture
def mock_device():
    """Create a mock device."""
    device = Mock(spec=MittFortumDevice)
    device.device_info = {
        "identifiers": {("mittfortum", "123456")},
        "name": "Mittfortum Energy Meter",
        "manufacturer": "Fortum",
        "model": "Energy Meter",
    }
    return device


class TestMittFortumCostSensor:
    """Test MittFortum cost sensor."""

    @pytest.fixture
    def sensor(self, mock_coordinator, mock_device):
        """Create cost sensor."""
        return MittFortumCostSensor(
            coordinator=mock_coordinator,
            device=mock_device,
        )

    def test_sensor_properties(self, sensor):
        """Test sensor properties."""
        assert sensor.name == "Total Cost"
        assert sensor.device_class == SensorDeviceClass.MONETARY
        assert sensor.state_class == SensorStateClass.TOTAL
        assert sensor.native_unit_of_measurement == "SEK"

    def test_native_value_with_data(self, sensor, mock_coordinator):
        """Test native value when data is available."""
        # Should sum all cost values
        assert sensor.native_value == 55.50  # 25.50 + 30.00

    def test_native_value_no_data(self, sensor, mock_coordinator):
        """Test native value when no data is available."""
        mock_coordinator.data = None
        assert sensor.native_value is None

    def test_native_value_empty_data(self, sensor, mock_coordinator):
        """Test native value when data is empty."""
        mock_coordinator.data = []
        assert sensor.native_value == 0

    def test_native_value_with_none_costs(self, sensor, mock_coordinator):
        """Test native value when some costs are None."""
        mock_coordinator.data = [
            ConsumptionData(
                value=150.5, unit="kWh", date_time=datetime.now(), cost=25.50
            ),
            ConsumptionData(
                value=200.0, unit="kWh", date_time=datetime.now(), cost=None
            ),
        ]
        assert sensor.native_value == 25.50

    def test_available_with_data(self, sensor, mock_coordinator):
        """Test availability when data is present."""
        assert sensor.available is True

    def test_available_no_data(self, sensor, mock_coordinator):
        """Test availability when no data is present."""
        mock_coordinator.data = None
        assert sensor.available is False
