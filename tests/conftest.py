"""Test configuration and fixtures."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from homeassistant.core import HomeAssistant

from custom_components.mittfortum.api import FortumAPIClient, OAuth2AuthClient
from custom_components.mittfortum.models import (
    AuthTokens,
    ConsumptionData,
    CustomerDetails,
)


@pytest.fixture
def mock_hass():
    """Mock Home Assistant instance."""
    hass = MagicMock(spec=HomeAssistant)
    hass.data = {}
    hass.states = MagicMock()
    hass.config_entries = MagicMock()
    hass.config_entries._entries = {}
    hass.config_entries.async_setup = AsyncMock(return_value=True)
    hass.config_entries.async_unload = AsyncMock(return_value=True)
    hass.async_block_till_done = AsyncMock()
    return hass


@pytest.fixture
def mock_auth_client():
    """Mock OAuth2AuthClient."""
    client = AsyncMock(spec=OAuth2AuthClient)
    client.access_token = "test_access_token"
    client.refresh_token = "test_refresh_token"
    client.id_token = "test_id_token"
    client.is_token_expired.return_value = False
    return client


@pytest.fixture
def mock_api_client(mock_hass, mock_auth_client):
    """Mock FortumAPIClient."""
    return AsyncMock(spec=FortumAPIClient)


@pytest.fixture
def sample_auth_tokens():
    """Sample authentication tokens."""
    return AuthTokens(
        access_token="test_access_token",
        refresh_token="test_refresh_token",
        id_token="test_id_token",
        expires_in=3600,
    )


@pytest.fixture
def sample_consumption_data():
    """Sample consumption data."""
    from datetime import datetime

    return [
        ConsumptionData(
            date_time=datetime(2024, 1, 1),
            value=100.5,
            cost=150.75,
            unit="kWh",
        ),
        ConsumptionData(
            date_time=datetime(2024, 1, 2),
            value=95.2,
            cost=142.80,
            unit="kWh",
        ),
    ]


@pytest.fixture
def sample_customer_details():
    """Sample customer details."""
    return CustomerDetails(
        customer_id="test_customer_123",
        postal_address="Test Street 123",
        post_office="Test City",
        name="Test Customer",
    )
