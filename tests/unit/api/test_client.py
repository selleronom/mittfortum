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

    async def test_get_customer_id_success(self, mock_hass, mock_auth_client):
        """Test successful customer ID extraction."""
        mock_auth_client.id_token = "test_token"

        client = FortumAPIClient(mock_hass, mock_auth_client)

        with patch("jwt.decode") as mock_decode:
            mock_decode.return_value = {"customerid": [{"crmid": "customer_123"}]}

            result = await client.get_customer_id()

            assert result == "customer_123"

    async def test_get_customer_id_no_token(self, mock_hass, mock_auth_client):
        """Test customer ID extraction with no token."""
        mock_auth_client.id_token = None
        mock_auth_client.session_data = None

        client = FortumAPIClient(mock_hass, mock_auth_client)

        with pytest.raises(APIError, match="No ID token or session data available"):
            await client.get_customer_id()

    async def test_get_customer_id_from_session(self, mock_hass, mock_auth_client):
        """Test customer ID extraction from session data."""
        mock_auth_client.session_data = {"user": {"customerId": "session_customer_123"}}
        mock_auth_client.id_token = "session_based"

        client = FortumAPIClient(mock_hass, mock_auth_client)

        result = await client.get_customer_id()

        assert result == "session_customer_123"

    async def test_get_customer_id_session_based_no_data(
        self, mock_hass, mock_auth_client
    ):
        """Test customer ID extraction with session-based token but no session data."""
        mock_auth_client.session_data = None
        mock_auth_client.id_token = "session_based"

        client = FortumAPIClient(mock_hass, mock_auth_client)

        with pytest.raises(APIError, match="Customer ID not found in session data"):
            await client.get_customer_id()

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

    async def test_get_total_consumption_no_metering_points(
        self, mock_hass, mock_auth_client
    ):
        """Test total consumption fetch with no metering points."""
        client = FortumAPIClient(mock_hass, mock_auth_client)

        with patch.object(client, "get_metering_points", return_value=[]):
            with pytest.raises(APIError, match="No metering points found"):
                await client.get_consumption_data()

    async def test_ensure_valid_token_session_based(self, mock_hass, mock_auth_client):
        """Test _ensure_valid_token with session-based token."""
        client = FortumAPIClient(mock_hass, mock_auth_client)

        # Mock token as expired and session-based
        mock_auth_client.is_token_expired.return_value = True
        mock_auth_client.refresh_token = "session_based"

        with patch.object(mock_auth_client, "authenticate") as mock_auth:
            await client._ensure_valid_token()
            mock_auth.assert_called_once()

    async def test_ensure_valid_token_real_refresh_token(
        self, mock_hass, mock_auth_client
    ):
        """Test _ensure_valid_token with real OAuth2 refresh token."""
        client = FortumAPIClient(mock_hass, mock_auth_client)

        # Mock token as expired with real refresh token
        mock_auth_client.is_token_expired.return_value = True
        mock_auth_client.refresh_token = "real_refresh_token"

        with patch.object(mock_auth_client, "refresh_access_token") as mock_refresh:
            await client._ensure_valid_token()
            mock_refresh.assert_called_once()

    async def test_ensure_valid_token_not_expired(self, mock_hass, mock_auth_client):
        """Test _ensure_valid_token with valid token."""
        client = FortumAPIClient(mock_hass, mock_auth_client)

        # Mock token as not expired
        mock_auth_client.is_token_expired.return_value = False

        with patch.object(mock_auth_client, "authenticate") as mock_auth:
            with patch.object(mock_auth_client, "refresh_access_token") as mock_refresh:
                await client._ensure_valid_token()
                mock_auth.assert_not_called()
                mock_refresh.assert_not_called()

    async def test_ensure_valid_token_no_refresh_token(
        self, mock_hass, mock_auth_client
    ):
        """Test _ensure_valid_token with no refresh token."""
        client = FortumAPIClient(mock_hass, mock_auth_client)

        # Mock token as expired with no refresh token
        mock_auth_client.is_token_expired.return_value = True
        mock_auth_client.refresh_token = None

        with patch.object(mock_auth_client, "authenticate") as mock_auth:
            await client._ensure_valid_token()
            mock_auth.assert_called_once()
