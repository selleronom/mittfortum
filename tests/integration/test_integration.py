"""Integration tests for the MittFortum integration."""

from datetime import datetime
from unittest.mock import AsyncMock, patch

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
import pytest

from custom_components.mittfortum.const import DOMAIN
from custom_components.mittfortum.models import (
    ConsumptionData,
    CustomerDetails,
    MeteringPoint,
)


@pytest.fixture
def mock_config_entry():
    """Create a mock config entry."""
    return ConfigEntry(
        version=1,
        minor_version=1,
        domain=DOMAIN,
        title="MittFortum (test_user)",
        data={
            CONF_USERNAME: "test_user",
            CONF_PASSWORD: "test_password",
        },
        source="user",
        unique_id="test_user",
    )


@pytest.fixture
def mock_consumption_data():
    """Create mock consumption data."""
    return [
        ConsumptionData(
            value=150.5,
            unit="kWh",
            date_time=datetime(2025, 5, 25, 12, 0, 0),
            cost=25.50,
        ),
        ConsumptionData(
            value=200.0,
            unit="kWh",
            date_time=datetime(2025, 5, 25, 13, 0, 0),
            cost=30.00,
        ),
    ]


@pytest.fixture
def mock_customer_details():
    """Create mock customer details."""
    return CustomerDetails(
        customer_id="12345",
        name="Test User",
        postal_address="123 Test St",
        post_office="Test City",
    )


@pytest.fixture
def mock_metering_point():
    """Create mock metering point."""
    return MeteringPoint(metering_point_no="MP123456", address="123 Test Street")


class TestMittFortumIntegration:
    """Test the MittFortum integration end-to-end."""

    @patch("custom_components.mittfortum.api.auth.OAuth2AuthClient")
    @patch("custom_components.mittfortum.api.client.FortumAPIClient")
    async def test_integration_setup_and_sensors(
        self,
        mock_api_client_class,
        mock_auth_client_class,
        mock_hass,
        mock_config_entry,
        mock_consumption_data,
        mock_customer_details,
        mock_metering_point,
    ):
        """Test full integration setup and sensor creation."""
        # Setup mocks
        mock_auth_client = AsyncMock()
        mock_auth_client_class.return_value = mock_auth_client
        mock_api_client = AsyncMock()
        mock_api_client_class.return_value = mock_api_client
        mock_api_client.get_consumption_data.return_value = mock_consumption_data
        mock_api_client.get_customer_details.return_value = mock_customer_details
        mock_api_client.get_metering_points.return_value = [mock_metering_point]

        # Add config entry
        mock_hass.config_entries._entries[mock_config_entry.entry_id] = (
            mock_config_entry
        )
        mock_config_entry.add_to_hass(mock_hass)

        # Setup integration
        await mock_hass.config_entries.async_setup(mock_config_entry.entry_id)
        await mock_hass.async_block_till_done()

        # Verify integration is loaded
        assert DOMAIN in mock_hass.data
        assert mock_config_entry.entry_id in mock_hass.data[DOMAIN]

        # Verify sensors are created
        energy_entity_id = "sensor.main_meter_energy_consumption"
        cost_entity_id = "sensor.main_meter_total_cost"

        energy_state = mock_hass.states.get(energy_entity_id)
        cost_state = mock_hass.states.get(cost_entity_id)

        # Energy sensor should sum all consumption values
        assert energy_state is not None
        assert float(energy_state.state) == 350.5  # 150.5 + 200.0

        # Cost sensor should sum all cost values
        assert cost_state is not None
        assert float(cost_state.state) == 55.50  # 25.50 + 30.00

    @patch("custom_components.mittfortum.api.auth.OAuth2AuthClient")
    @patch("custom_components.mittfortum.api.client.FortumAPIClient")
    async def test_integration_unload(
        self,
        mock_api_client_class,
        mock_auth_client_class,
        mock_hass,
        mock_config_entry,
    ):
        """Test integration unload."""
        # Setup mocks
        mock_auth_client = AsyncMock()
        mock_auth_client_class.return_value = mock_auth_client

        mock_api_client = AsyncMock()
        mock_api_client_class.return_value = mock_api_client
        mock_api_client.get_consumption_data.return_value = []
        mock_api_client.get_customer_details.return_value = CustomerDetails(
            customer_id="12345",
            name="Test User",
            postal_address="123 Test St",
            post_office="Test City",
        )
        mock_api_client.get_metering_points.return_value = []

        # Add and setup config entry
        mock_hass.config_entries._entries[mock_config_entry.entry_id] = (
            mock_config_entry
        )
        mock_config_entry.add_to_hass(mock_hass)
        await mock_hass.config_entries.async_setup(mock_config_entry.entry_id)
        await mock_hass.async_block_till_done()

        # Verify integration is loaded
        assert DOMAIN in mock_hass.data

        # Unload integration
        await mock_hass.config_entries.async_unload(mock_config_entry.entry_id)
        await mock_hass.async_block_till_done()

        # Verify integration is unloaded
        assert mock_config_entry.entry_id not in mock_hass.data.get(DOMAIN, {})

    @patch("custom_components.mittfortum.api.auth.OAuth2AuthClient")
    @patch("custom_components.mittfortum.api.client.FortumAPIClient")
    async def test_integration_coordinator_update(
        self,
        mock_api_client_class,
        mock_auth_client_class,
        mock_hass,
        mock_config_entry,
        mock_consumption_data,
        mock_customer_details,
        mock_metering_point,
    ):
        """Test coordinator data updates."""
        # Setup mocks
        mock_auth_client = AsyncMock()
        mock_auth_client_class.return_value = mock_auth_client

        mock_api_client = AsyncMock()
        mock_api_client_class.return_value = mock_api_client
        mock_api_client.get_consumption_data.return_value = mock_consumption_data
        mock_api_client.get_customer_details.return_value = mock_customer_details
        mock_api_client.get_metering_points.return_value = [mock_metering_point]

        # Add and setup config entry
        mock_hass.config_entries._entries[mock_config_entry.entry_id] = (
            mock_config_entry
        )
        mock_config_entry.add_to_hass(mock_hass)
        await mock_hass.config_entries.async_setup(mock_config_entry.entry_id)
        await mock_hass.async_block_till_done()

        # Get coordinator
        coordinator = mock_hass.data[DOMAIN][mock_config_entry.entry_id]["coordinator"]

        # Trigger update
        await coordinator.async_request_refresh()
        await mock_hass.async_block_till_done()

        # Verify API was called
        mock_api_client.get_consumption_data.assert_called()

        # Verify coordinator has data
        assert coordinator.data == mock_consumption_data
