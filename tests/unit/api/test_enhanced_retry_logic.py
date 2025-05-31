"""Test enhanced retry logic for session-based authentication."""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from custom_components.mittfortum.api.client import FortumAPIClient
from custom_components.mittfortum.exceptions import APIError


class TestEnhancedRetryLogic:
    """Test enhanced retry logic for session-based authentication."""

    async def test_session_based_auth_allows_multiple_retries(
        self, mock_hass, mock_auth_client
    ):
        """Test that session-based auth allows up to 3 retries."""
        client = FortumAPIClient(mock_hass, mock_auth_client)

        # Mock session-based authentication
        mock_auth_client.refresh_token = "session_based"

        call_count = 0

        async def mock_handle_response(response):
            nonlocal call_count
            call_count += 1
            if call_count <= 3:  # Fail first 3 attempts
                raise APIError("Token expired - retry required")
            else:
                # 4th attempt succeeds
                return {"success": True}

        with patch.object(client, "_ensure_valid_token", new_callable=AsyncMock):
            with patch.object(
                client, "_handle_response", side_effect=mock_handle_response
            ):
                with patch(
                    "custom_components.mittfortum.api.client.get_async_client"
                ) as mock_get_client:
                    mock_client = AsyncMock()
                    mock_get_client.return_value.__aenter__.return_value = mock_client
                    mock_client.get.return_value = Mock()

                    result = await client._get("https://example.com/api/test")

                    # Should succeed after 3 retries (4 total attempts)
                    assert result == {"success": True}
                    assert call_count == 4

    async def test_session_based_auth_exponential_backoff(
        self, mock_hass, mock_auth_client
    ):
        """Test that session-based auth uses exponential backoff delays."""
        client = FortumAPIClient(mock_hass, mock_auth_client)

        # Mock session-based authentication
        mock_auth_client.refresh_token = "session_based"

        with patch.object(client, "_ensure_valid_token", new_callable=AsyncMock):
            with patch.object(client, "_handle_response") as mock_handle_response:
                mock_handle_response.side_effect = [
                    APIError("Token expired - retry required"),
                    {"success": True},
                ]

                with patch(
                    "custom_components.mittfortum.api.client.get_async_client"
                ) as mock_get_client:
                    mock_client = AsyncMock()
                    mock_get_client.return_value.__aenter__.return_value = mock_client
                    mock_client.get.return_value = Mock()

                    with patch(
                        "custom_components.mittfortum.api.client.asyncio.sleep"
                    ) as mock_sleep:
                        result = await client._get("https://example.com/api/test")

                        # Should succeed after 1 retry
                        assert result == {"success": True}

                        # Verify exponential backoff was used (0.5s for first retry)
                        mock_sleep.assert_called_once_with(0.5)

    async def test_oauth_token_still_allows_only_one_retry(
        self, mock_hass, mock_auth_client
    ):
        """Test that OAuth tokens still only allow 1 retry."""
        client = FortumAPIClient(mock_hass, mock_auth_client)

        # Mock OAuth authentication (not session-based)
        mock_auth_client.refresh_token = "real_oauth_refresh_token"

        call_count = 0

        async def mock_handle_response(response):
            nonlocal call_count
            call_count += 1
            # Always fail with token expired
            raise APIError("Token expired - retry required")

        with patch.object(client, "_ensure_valid_token", new_callable=AsyncMock):
            with patch.object(
                client, "_handle_response", side_effect=mock_handle_response
            ):
                with patch(
                    "custom_components.mittfortum.api.client.get_async_client"
                ) as mock_get_client:
                    mock_client = AsyncMock()
                    mock_get_client.return_value.__aenter__.return_value = mock_client
                    mock_client.get.return_value = Mock()

                    # Should raise after 1 retry (2 total attempts)
                    with pytest.raises(
                        APIError, match="Token expired - retry required"
                    ):
                        await client._get("https://example.com/api/test")

                    # Should only be called twice (original + 1 retry)
                    assert call_count == 2

    async def test_session_based_auth_max_retries_exceeded(
        self, mock_hass, mock_auth_client
    ):
        """Test that session-based auth stops after max retries."""
        client = FortumAPIClient(mock_hass, mock_auth_client)

        # Mock session-based authentication
        mock_auth_client.refresh_token = "session_based"

        async def mock_handle_response(response):
            # Always fail with token expired
            raise APIError("Token expired - retry required")

        with patch.object(client, "_ensure_valid_token", new_callable=AsyncMock):
            with patch.object(
                client, "_handle_response", side_effect=mock_handle_response
            ):
                with patch(
                    "custom_components.mittfortum.api.client.get_async_client"
                ) as mock_get_client:
                    mock_client = AsyncMock()
                    mock_get_client.return_value.__aenter__.return_value = mock_client
                    mock_client.get.return_value = Mock()

                    # Should raise after 3 retries (4 total attempts)
                    with pytest.raises(
                        APIError, match="Token expired - retry required"
                    ):
                        await client._get("https://example.com/api/test")

    async def test_session_based_auth_different_delays_per_retry(
        self, mock_hass, mock_auth_client
    ):
        """Test that session-based auth uses increasing delays."""
        client = FortumAPIClient(mock_hass, mock_auth_client)

        # Mock session-based authentication
        mock_auth_client.refresh_token = "session_based"

        call_count = 0

        async def mock_handle_response(response):
            nonlocal call_count
            call_count += 1
            if call_count <= 2:  # Fail first 2 attempts
                raise APIError("Token expired - retry required")
            else:
                # 3rd attempt succeeds
                return {"success": True}

        with patch.object(client, "_ensure_valid_token", new_callable=AsyncMock):
            with patch.object(
                client, "_handle_response", side_effect=mock_handle_response
            ):
                with patch(
                    "custom_components.mittfortum.api.client.get_async_client"
                ) as mock_get_client:
                    mock_client = AsyncMock()
                    mock_get_client.return_value.__aenter__.return_value = mock_client
                    mock_client.get.return_value = Mock()

                    with patch(
                        "custom_components.mittfortum.api.client.asyncio.sleep"
                    ) as mock_sleep:
                        result = await client._get("https://example.com/api/test")

                        # Should succeed after 2 retries
                        assert result == {"success": True}

                        # Verify exponential backoff: 0.5s, then 1.0s
                        expected_calls = [0.5, 1.0]
                        actual_calls = [
                            call[0][0] for call in mock_sleep.call_args_list
                        ]
                        assert actual_calls == expected_calls
