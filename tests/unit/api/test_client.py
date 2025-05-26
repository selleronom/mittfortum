"""Unit tests for FortumAPIClient."""

from unittest.mock import Mock, patch

import pytest

from custom_components.mittfortum.api.client import FortumAPIClient
from custom_components.mittfortum.exceptions import APIError
from custom_components.mittfortum.models import CustomerDetails


class TestFortumAPIClient:
    """Test FortumAPIClient."""

    def test_init(self, mock_hass, mock_auth_client):
        """Test initialization."""
        client = FortumAPIClient(mock_hass, mock_auth_client)

        assert client._hass == mock_hass
        assert client._auth_client == mock_auth_client

    @pytest.mark.asyncio
    async def test_get_customer_id_success(self, mock_hass, mock_auth_client):
        """Test successful customer ID extraction."""
        mock_auth_client.id_token = "test_token"

        client = FortumAPIClient(mock_hass, mock_auth_client)

        with patch("jwt.decode") as mock_decode:
            mock_decode.return_value = {"customerid": [{"crmid": "customer_123"}]}

            result = await client.get_customer_id()

            assert result == "customer_123"

    @pytest.mark.asyncio
    async def test_get_customer_id_no_token(self, mock_hass, mock_auth_client):
        """Test customer ID extraction with no token."""
        mock_auth_client.id_token = None
        mock_auth_client.session_data = None

        client = FortumAPIClient(mock_hass, mock_auth_client)

        with pytest.raises(APIError, match="No ID token or session data available"):
            await client.get_customer_id()

    @pytest.mark.asyncio
    async def test_get_customer_id_from_session(self, mock_hass, mock_auth_client):
        """Test customer ID extraction from session data."""
        mock_auth_client.session_data = {"user": {"customerId": "session_customer_123"}}
        mock_auth_client.id_token = "session_based"

        client = FortumAPIClient(mock_hass, mock_auth_client)

        result = await client.get_customer_id()

        assert result == "session_customer_123"

    @pytest.mark.asyncio
    async def test_get_customer_id_session_based_no_data(
        self, mock_hass, mock_auth_client
    ):
        """Test customer ID extraction with session-based token but no session data."""
        mock_auth_client.session_data = None
        mock_auth_client.id_token = "session_based"

        client = FortumAPIClient(mock_hass, mock_auth_client)

        with pytest.raises(APIError, match="Customer ID not found in session data"):
            await client.get_customer_id()

    @pytest.mark.asyncio
    async def test_get_customer_details_success(
        self, mock_hass, mock_auth_client, sample_customer_details
    ):
        """Test successful customer details fetch."""
        client = FortumAPIClient(mock_hass, mock_auth_client)

        # Mock response data from session endpoint
        mock_response = Mock()
        mock_response.json.return_value = {
            "user": {
                "customerId": "customer_123",
                "postalAddress": "Test Street 123",
                "postOffice": "Test City",
                "name": "Test Customer",
            }
        }

        with patch.object(client, "_get", return_value=mock_response):
            result = await client.get_customer_details()

            assert isinstance(result, CustomerDetails)
            assert result.customer_id == "customer_123"
            assert result.postal_address == "Test Street 123"

    @pytest.mark.asyncio
    async def test_get_total_consumption_success(
        self, mock_hass, mock_auth_client, sample_consumption_data
    ):
        """Test successful total consumption fetch."""
        client = FortumAPIClient(mock_hass, mock_auth_client)

        with patch.object(
            client, "get_consumption_data", return_value=sample_consumption_data
        ):
            result = await client.get_total_consumption()

            assert result == sample_consumption_data
            assert len(result) == 2

    @pytest.mark.asyncio
    async def test_get_total_consumption_no_metering_points(
        self, mock_hass, mock_auth_client
    ):
        """Test total consumption fetch with no metering points."""
        client = FortumAPIClient(mock_hass, mock_auth_client)

        with patch.object(client, "get_metering_points", return_value=[]):
            with pytest.raises(APIError, match="No metering points found"):
                await client.get_consumption_data()
