"""Unit tests for OAuth2AuthClient."""

from unittest.mock import AsyncMock, Mock, patch

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

    async def test_refresh_access_token_session_based(
        self, mock_hass, sample_auth_tokens
    ):
        """Test refresh access token with session-based token calls authenticate."""
        # Set up mock_hass.data for get_async_client
        mock_hass.data = {}

        client = OAuth2AuthClient(
            hass=mock_hass,
            username="test@example.com",
            password="test_password",
        )

        # Set up session-based tokens
        session_tokens = sample_auth_tokens
        session_tokens.refresh_token = "session_based"
        client._tokens = session_tokens

        # Mock authenticate method
        with patch.object(
            client, "authenticate", return_value=sample_auth_tokens
        ) as mock_auth:
            result = await client.refresh_access_token()

            mock_auth.assert_called_once()
            assert result == sample_auth_tokens

    async def test_refresh_access_token_no_refresh_token(self, mock_hass):
        """Test refresh access token without refresh token raises error."""
        client = OAuth2AuthClient(
            hass=mock_hass,
            username="test@example.com",
            password="test_password",
        )

        with pytest.raises(AuthenticationError, match="No refresh token available"):
            await client.refresh_access_token()

    async def test_refresh_access_token_real_oauth_token(
        self, mock_hass, sample_auth_tokens
    ):
        """Test refresh access token with real OAuth2 token."""
        # Set up mock_hass.data for get_async_client
        mock_hass.data = {}

        client = OAuth2AuthClient(
            hass=mock_hass,
            username="test@example.com",
            password="test_password",
        )

        # Set up real OAuth tokens
        real_tokens = sample_auth_tokens
        real_tokens.refresh_token = "real_refresh_token"
        client._tokens = real_tokens

        # Mock the HTTP client and response
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json = Mock(
            return_value={
                "access_token": "new_access_token",
                "refresh_token": "new_refresh_token",
                "token_type": "Bearer",
                "expires_in": 3600,
                "id_token": "new_id_token",
            }
        )

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response

        with patch(
            "custom_components.mittfortum.api.auth.get_async_client"
        ) as mock_get_client:
            mock_get_client.return_value.__aenter__.return_value = mock_client

            result = await client.refresh_access_token()

            # Verify the token exchange call was made
            mock_client.post.assert_called_once()
            call_args = mock_client.post.call_args
            assert call_args[1]["data"]["grant_type"] == "refresh_token"
            assert call_args[1]["data"]["refresh_token"] == "real_refresh_token"

            # Verify tokens were updated
            assert result.access_token == "new_access_token"
            assert result.refresh_token == "new_refresh_token"

    async def test_session_propagation_delay(self, mock_hass):
        """Test that session verification includes delay for server propagation."""
        client = OAuth2AuthClient(
            hass=mock_hass,
            username="test@example.com",
            password="test_password",
        )

        # Mock session data response
        mock_session_data = {
            "user": {
                "id": "test_user",
                "accessToken": "test_access_token",
                "customerId": "12345",
            }
        }

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_session_data

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response

        with patch(
            "custom_components.mittfortum.api.auth.get_async_client"
        ) as mock_get_client:
            mock_get_client.return_value.__aenter__.return_value = mock_client
            mock_get_client.return_value.__aexit__.return_value = None

            # Mock asyncio.sleep to verify it's called
            with patch(
                "custom_components.mittfortum.api.auth.asyncio.sleep"
            ) as mock_sleep:
                mock_sleep.return_value = None

                # Call _verify_session_established
                result = await client._verify_session_established(mock_client)

                # Verify the delay was added (now 0.3s for better propagation)
                mock_sleep.assert_called_once_with(0.3)

                # Verify session data was returned correctly
                assert result == mock_session_data
                assert result["user"]["id"] == "test_user"
