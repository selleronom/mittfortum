"""Test coordinator module."""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import UpdateFailed

from custom_components.mittfortum.api.client import FortumAPIClient
from custom_components.mittfortum.coordinator import MittFortumDataCoordinator
from custom_components.mittfortum.exceptions import AuthenticationError, MittFortumError
from custom_components.mittfortum.models import ConsumptionData


@pytest.fixture
def mock_hass():
    """Create a mock Home Assistant instance."""
    return Mock(spec=HomeAssistant)


@pytest.fixture
def mock_api_client():
    """Create a mock API client."""
    client = AsyncMock(spec=FortumAPIClient)
    client.get_consumption_data.return_value = [
        ConsumptionData(value=150.5, unit="kWh", date_time=datetime.now(), cost=25.50)
    ]
    return client


@pytest.fixture
def coordinator(mock_hass, mock_api_client):
    """Create a coordinator instance."""
    return MittFortumDataCoordinator(
        hass=mock_hass,
        api_client=mock_api_client,
        update_interval=timedelta(minutes=15),
    )


class TestMittFortumDataCoordinator:
    """Test MittFortum data coordinator."""

    async def test_init(self, coordinator, mock_hass, mock_api_client):
        """Test coordinator initialization."""
        assert coordinator.hass == mock_hass
        assert coordinator.api_client == mock_api_client
        assert coordinator.name == "MittFortum"
        assert coordinator.update_interval == timedelta(minutes=15)

    async def test_async_update_data_success(self, coordinator, mock_api_client):
        """Test successful data update."""
        data = await coordinator._async_update_data()

        assert len(data) == 1
        assert data[0].value == 150.5
        assert data[0].unit == "kWh"
        assert data[0].cost == 25.50
        mock_api_client.get_consumption_data.assert_called_once()

    async def test_async_update_data_authentication_error(
        self, coordinator, mock_api_client
    ):
        """Test data update with authentication error."""
        mock_api_client.get_consumption_data.side_effect = AuthenticationError(
            "Auth failed"
        )

        with pytest.raises(UpdateFailed) as exc_info:
            await coordinator._async_update_data()

        assert "Authentication failed" in str(exc_info.value)

    async def test_async_update_data_api_error(self, coordinator, mock_api_client):
        """Test data update with API error."""
        mock_api_client.get_consumption_data.side_effect = MittFortumError("API error")

        with pytest.raises(UpdateFailed) as exc_info:
            await coordinator._async_update_data()

        assert "Failed to fetch data" in str(exc_info.value)

    async def test_async_update_data_unexpected_error(
        self, coordinator, mock_api_client
    ):
        """Test data update with unexpected error."""
        mock_api_client.get_consumption_data.side_effect = Exception("Unexpected error")

        with pytest.raises(UpdateFailed) as exc_info:
            await coordinator._async_update_data()

        assert "Unexpected error" in str(exc_info.value)

    async def test_async_update_data_empty_response(self, coordinator, mock_api_client):
        """Test data update with empty response."""
        mock_api_client.get_consumption_data.return_value = []

        data = await coordinator._async_update_data()
        assert data == []

    async def test_async_update_data_none_response(self, coordinator, mock_api_client):
        """Test data update with None response."""
        mock_api_client.get_consumption_data.return_value = None

        data = await coordinator._async_update_data()
        assert data == []
