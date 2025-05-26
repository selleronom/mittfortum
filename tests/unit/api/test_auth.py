"""Unit tests for OAuth2AuthClient."""

from unittest.mock import patch

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
            patch.object(client, "_fetch_openid_configuration") as mock_config,
            patch.object(client, "_initiate_session") as mock_session,
            patch.object(client, "_authenticate_user") as mock_auth,
            patch.object(client, "_get_user_session") as mock_user_session,
            patch.object(client, "_fetch_user_details") as mock_user_details,
            patch.object(client, "_validate_goto") as mock_goto,
            patch.object(client, "_follow_success_url") as mock_follow,
            patch.object(client, "_exchange_code_for_tokens") as mock_exchange,
        ):
            mock_config.return_value = {
                "authorization_endpoint": "https://test.com/auth"
            }
            mock_user_session.return_value = {"id": "user_123"}
            mock_goto.return_value = {"successURL": "https://test.com/success"}
            mock_follow.return_value = "auth_code_123"
            mock_exchange.return_value = sample_auth_tokens

            result = await client.authenticate()

            assert result == sample_auth_tokens
            assert client._tokens == sample_auth_tokens

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
            client, "_fetch_openid_configuration", side_effect=Exception("Test error")
        ):
            with pytest.raises(AuthenticationError):
                await client.authenticate()
