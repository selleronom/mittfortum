"""Unit tests for OAuth2AuthClient."""

from unittest.mock import AsyncMock, patch

import pytest

from custom_components.mittfortum.api.auth import OAuth2AuthClient
from custom_components.mittfortum.exceptions import AuthenticationError


class TestOAuth2AuthClient:
    """Test OAuth2AuthClient."""

    def test_init(self, mock_hass):
        """Test initialization."""
        client = OAuth2AuthClient(
            hass=mock_hass,
            username="test@example.com",
            password="test_password",
        )

        assert client._username == "test@example.com"
        assert client._password == "test_password"
        assert client._hass == mock_hass

    def test_is_token_expired_no_expiry(self, mock_hass):
        """Test token expiry check with no expiry set."""
        client = OAuth2AuthClient(
            hass=mock_hass,
            username="test@example.com",
            password="test_password",
        )

        assert client.is_token_expired() is True

    @patch("time.time", return_value=1000)
    def test_is_token_expired_not_expired(self, mock_time, mock_hass):
        """Test token expiry check when token is not expired."""
        client = OAuth2AuthClient(
            hass=mock_hass,
            username="test@example.com",
            password="test_password",
        )
        client._token_expiry = 2000

        assert client.is_token_expired() is False

    @patch("time.time", return_value=2000)
    def test_is_token_expired_expired(self, mock_time, mock_hass):
        """Test token expiry check when token is expired."""
        client = OAuth2AuthClient(
            hass=mock_hass,
            username="test@example.com",
            password="test_password",
        )
        client._token_expiry = 1000

        assert client.is_token_expired() is True

    @pytest.mark.asyncio
    async def test_authenticate_success(self, mock_hass, sample_auth_tokens):
        """Test successful authentication."""
        # Set up mock_hass.data for get_async_client
        mock_hass.data = {}

        client = OAuth2AuthClient(
            hass=mock_hass,
            username="test@example.com",
            password="test_password",
        )

        with (
            patch(
                "custom_components.mittfortum.api.auth.get_async_client"
            ) as mock_get_client,
            patch.object(client, "_initialize_fortum_session") as mock_init_session,
            patch.object(client, "_initiate_oauth_signin") as mock_oauth_signin,
            patch.object(client, "_perform_sso_authentication") as mock_sso_auth,
            patch.object(client, "_complete_oauth_authorization") as mock_complete_auth,
            patch.object(client, "_verify_session_established") as mock_verify_session,
        ):
            # Mock the async context manager for the client
            mock_client = AsyncMock()
            mock_client.cookies.jar = []  # Empty cookie jar
            mock_get_client.return_value.__aenter__.return_value = mock_client

            # Set up method return values
            mock_init_session.return_value = "csrf_token_123"
            mock_oauth_signin.return_value = "https://oauth.url"
            mock_sso_auth.return_value = None
            mock_complete_auth.return_value = None
            mock_verify_session.return_value = {
                "user": {
                    "accessToken": "test_access_token",
                    "idToken": "test_id_token",
                    "expires": "2024-12-31T23:59:59Z",
                }
            }

            result = await client.authenticate()

            assert result.access_token == "test_access_token"
            assert result.id_token == "test_id_token"
            assert client._tokens.access_token == "test_access_token"

    @pytest.mark.asyncio
    async def test_authenticate_failure(self, mock_hass):
        """Test authentication failure."""
        # Set up mock_hass.data for get_async_client
        mock_hass.data = {}

        client = OAuth2AuthClient(
            hass=mock_hass,
            username="test@example.com",
            password="test_password",
        )

        with patch.object(
            client, "_initialize_fortum_session", side_effect=Exception("Test error")
        ):
            with pytest.raises(AuthenticationError):
                await client.authenticate()
