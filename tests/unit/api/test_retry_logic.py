"""Test retry logic for token refresh in API client."""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from custom_components.mittfortum.api.client import FortumAPIClient
from custom_components.mittfortum.exceptions import APIError


class TestRetryLogic:
    """Test retry logic for token expiration scenarios."""

    async def test_get_request_retry_on_token_expired(
        self, mock_hass, mock_auth_client
    ):
        """Test that _get retries request once when token expires."""
        client = FortumAPIClient(mock_hass, mock_auth_client)

        # Mock successful second request
        mock_response = Mock()
        mock_response.json.return_value = {"success": True}

        call_count = 0

        async def mock_handle_response(response):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                # First call fails with token expired
                raise APIError("Token expired - retry required")
            else:
                # Second call succeeds
                return mock_response

        with patch.object(client, "_ensure_valid_token", new_callable=AsyncMock):
            with patch.object(
                client, "_handle_response", side_effect=mock_handle_response
            ):
                with patch(
                    "custom_components.mittfortum.api.client.get_async_client"
                ) as mock_get_client:
                    mock_client = AsyncMock()
                    mock_get_client.return_value.__aenter__.return_value = mock_client
                    mock_client.get.return_value = mock_response

                    result = await client._get("https://example.com/api/test")

                    # Should succeed after retry
                    assert result == mock_response
                    # Should have been called twice (original + retry)
                    assert call_count == 2

    async def test_get_request_no_retry_after_first_retry(
        self, mock_hass, mock_auth_client
    ):
        """Test that _get doesn't retry infinitely."""
        client = FortumAPIClient(mock_hass, mock_auth_client)

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

                    # Should raise after one retry
                    with pytest.raises(
                        APIError, match="Token expired - retry required"
                    ):
                        await client._get("https://example.com/api/test")

    async def test_get_request_no_retry_on_other_api_errors(
        self, mock_hass, mock_auth_client
    ):
        """Test that _get doesn't retry on other API errors."""
        client = FortumAPIClient(mock_hass, mock_auth_client)

        call_count = 0

        async def mock_handle_response(response):
            nonlocal call_count
            call_count += 1
            # Fail with different error
            raise APIError("Server error")

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

                    # Should raise immediately without retry
                    with pytest.raises(APIError, match="Server error"):
                        await client._get("https://example.com/api/test")

                    # Should only be called once (no retry)
                    assert call_count == 1

    async def test_get_request_wraps_non_api_exceptions(
        self, mock_hass, mock_auth_client
    ):
        """Test that _get wraps non-APIError exceptions properly."""
        client = FortumAPIClient(mock_hass, mock_auth_client)

        with patch.object(client, "_ensure_valid_token", new_callable=AsyncMock):
            with patch(
                "custom_components.mittfortum.api.client.get_async_client"
            ) as mock_get_client:
                mock_client = AsyncMock()
                mock_get_client.return_value.__aenter__.return_value = mock_client
                mock_client.get.side_effect = Exception("Network error")

                # Should wrap in APIError
                with pytest.raises(APIError, match="GET request failed"):
                    await client._get("https://example.com/api/test")
