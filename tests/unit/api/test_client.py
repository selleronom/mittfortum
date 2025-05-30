"""Unit tests for FortumAPIClient."""

from unittest.mock import AsyncMock, Mock, patch

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

    async def test_trpc_endpoints_exclude_auth_headers(
        self, mock_hass, mock_auth_client
    ):
        """Test that tRPC endpoints do NOT receive Authorization headers."""
        from unittest.mock import AsyncMock, MagicMock

        mock_auth_client.access_token = "test_access_token_123"
        mock_auth_client.session_cookies = {"sessionid": "test_session"}
        mock_auth_client.is_token_expired.return_value = False

        client = FortumAPIClient(mock_hass, mock_auth_client)

        # Test tRPC endpoint
        trpc_url = (
            "https://www.fortum.com/se/el/api/trpc/loggedIn.timeSeries.listTimeSeries"
        )

        with patch(
            "custom_components.mittfortum.api.client.get_async_client"
        ) as mock_get_client:
            # Create a properly configured mock client
            mock_client = AsyncMock()

            # Mock the response with concrete values
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.text = '{"test": "data"}'  # Non-empty text
            mock_response.json.return_value = [
                {"result": {"data": {"json": {"test": "data"}}}}
            ]

            mock_client.get.return_value = mock_response
            mock_client.cookies = MagicMock()

            # Configure the context manager
            mock_get_client.return_value.__aenter__.return_value = mock_client
            mock_get_client.return_value.__aexit__.return_value = None

            # Make the request
            await client._get(trpc_url)

            # Verify the call was made
            assert mock_client.get.called
            call_args = mock_client.get.call_args

            # Check that Authorization header was NOT included
            headers = call_args[1]["headers"]
            assert "Authorization" not in headers

    async def test_non_trpc_endpoints_include_auth_headers(
        self, mock_hass, mock_auth_client
    ):
        """Test that non-tRPC endpoints DO receive Authorization headers."""
        from unittest.mock import AsyncMock, MagicMock

        mock_auth_client.access_token = "test_access_token_123"
        mock_auth_client.session_cookies = {"sessionid": "test_session"}
        mock_auth_client.is_token_expired.return_value = False

        client = FortumAPIClient(mock_hass, mock_auth_client)

        # Test non-tRPC endpoint
        api_url = "https://www.fortum.com/se/el/api/some-other-endpoint"

        with patch(
            "custom_components.mittfortum.api.client.get_async_client"
        ) as mock_get_client:
            # Create a properly configured mock client
            mock_client = AsyncMock()

            # Mock the response with concrete values
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.text = '{"test": "data"}'  # Non-empty text
            mock_response.json.return_value = {"test": "data"}

            mock_client.get.return_value = mock_response
            mock_client.cookies = MagicMock()

            # Configure the context manager
            mock_get_client.return_value.__aenter__.return_value = mock_client
            mock_get_client.return_value.__aexit__.return_value = None

            # Make the request
            await client._get(api_url)

            # Verify the call was made
            assert mock_client.get.called
            call_args = mock_client.get.call_args

            # Check that Authorization header was included
            headers = call_args[1]["headers"]
            assert "Authorization" in headers
            assert headers["Authorization"] == "Bearer test_access_token_123"

    async def test_session_endpoints_exclude_auth_headers(
        self, mock_hass, mock_auth_client
    ):
        """Test that session endpoints do NOT receive Authorization headers."""
        from unittest.mock import AsyncMock, MagicMock

        mock_auth_client.access_token = "test_access_token_123"
        mock_auth_client.session_cookies = {"sessionid": "test_session"}
        mock_auth_client.is_token_expired.return_value = False

        client = FortumAPIClient(mock_hass, mock_auth_client)

        # Test session endpoint
        session_url = "https://www.fortum.com/se/el/api/auth/session"

        with patch(
            "custom_components.mittfortum.api.client.get_async_client"
        ) as mock_get_client:
            # Create a properly configured mock client
            mock_client = AsyncMock()

            # Mock the response with concrete values
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.text = '{"user": {"test": "data"}}'  # Non-empty text
            mock_response.json.return_value = {"user": {"test": "data"}}

            mock_client.get.return_value = mock_response
            mock_client.cookies = MagicMock()

            # Configure the context manager
            mock_get_client.return_value.__aenter__.return_value = mock_client
            mock_get_client.return_value.__aexit__.return_value = None

            # Make the request
            await client._get(session_url)

            # Verify the call was made
            assert mock_client.get.called
            call_args = mock_client.get.call_args

            # Check that Authorization header was NOT included
            headers = call_args[1]["headers"]
            assert "Authorization" not in headers

    async def test_trpc_endpoint_no_auth_header(self, mock_hass, mock_auth_client):
        """Test that tRPC endpoints do NOT receive Authorization headers."""
        mock_auth_client.access_token = "test_access_token_123"
        mock_auth_client.session_cookies = {"sessionid": "test_session"}
        mock_auth_client.is_token_expired.return_value = False

        client = FortumAPIClient(mock_hass, mock_auth_client)

        # tRPC endpoint URL
        trpc_url = (
            "https://www.fortum.com/se/el/api/trpc/"
            "loggedIn.timeSeries.listTimeSeries?batch=1&input="
            "%7B%220%22%3A%7B%22json%22%3A%7B%22meteringPointNo%22%3A%5B%22123%22%5D%7D%7D%7D"
        )

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = '{"test": "data"}'
        mock_response.json.return_value = [
            {"result": {"data": {"json": {"test": "data"}}}}
        ]

        with patch(
            "custom_components.mittfortum.api.client.get_async_client"
        ) as mock_get_client:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client.cookies = {}

            mock_get_client.return_value.__aenter__.return_value = mock_client
            mock_get_client.return_value.__aexit__.return_value = None

            result = await client._get(trpc_url)

            # Verify Authorization header was NOT included
            call_args = mock_client.get.call_args
            headers = call_args[1]["headers"]
            assert "Authorization" not in headers

            # Verify we got the expected result
            assert result == mock_response

    async def test_non_trpc_endpoint_gets_auth_header(
        self, mock_hass, mock_auth_client
    ):
        """Test that non-tRPC endpoints DO receive Authorization headers."""
        mock_auth_client.access_token = "test_access_token_123"
        mock_auth_client.session_cookies = {"sessionid": "test_session"}
        mock_auth_client.is_token_expired.return_value = False

        client = FortumAPIClient(mock_hass, mock_auth_client)

        # Non-tRPC API endpoint
        api_url = "https://www.fortum.com/se/el/api/some-other-endpoint"

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = '{"test": "data"}'
        mock_response.json.return_value = {"test": "data"}

        with patch(
            "custom_components.mittfortum.api.client.get_async_client"
        ) as mock_get_client:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client.cookies = {}

            mock_get_client.return_value.__aenter__.return_value = mock_client
            mock_get_client.return_value.__aexit__.return_value = None

            await client._get(api_url)

            # Verify Authorization header was included
            call_args = mock_client.get.call_args
            headers = call_args[1]["headers"]
            assert "Authorization" in headers
            assert headers["Authorization"] == "Bearer test_access_token_123"

    async def test_retry_logic_prevents_infinite_loop(
        self, mock_hass, mock_auth_client
    ):
        """Test that retry logic allows exactly 1 retry and prevents infinite loops."""
        mock_auth_client.access_token = "test_access_token_123"
        mock_auth_client.session_cookies = {"sessionid": "test_session"}
        mock_auth_client.is_token_expired.return_value = False
        mock_auth_client.refresh_access_token = AsyncMock()

        client = FortumAPIClient(mock_hass, mock_auth_client)

        call_count = 0

        # Mock the _handle_response method to always raise TOKEN_EXPIRED_RETRY_MSG
        async def mock_handle_response(response):
            nonlocal call_count
            call_count += 1
            # Always simulate token expiry to test retry logic
            raise APIError("Token expired - retry required")

        with patch.object(client, "_handle_response", side_effect=mock_handle_response):
            with patch(
                "homeassistant.helpers.httpx_client.get_async_client"
            ) as mock_get_client:
                mock_client = AsyncMock()
                mock_client.cookies = {}
                mock_get_client.return_value.__aenter__.return_value = mock_client
                mock_get_client.return_value.__aexit__.return_value = None

                # This should fail after exactly 2 attempts (original + 1 retry)
                with pytest.raises(APIError, match="Token expired - retry required"):
                    await client._get("https://www.fortum.com/se/el/api/test")

                # Verify exactly 2 calls were made (no infinite loop)
                assert call_count == 2
