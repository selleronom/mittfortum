"""Main API client for MittFortum."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any

from homeassistant.helpers.httpx_client import get_async_client

from ..const import SESSION_URL
from ..exceptions import APIError, InvalidResponseError, UnexpectedStatusCodeError
from ..models import ConsumptionData, CustomerDetails, MeteringPoint, TimeSeries
from .endpoints import APIEndpoints

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

    from .auth import OAuth2AuthClient

_LOGGER = logging.getLogger(__name__)


class FortumAPIClient:
    """Main API client for Fortum tRPC services."""

    def __init__(self, hass: HomeAssistant, auth_client: OAuth2AuthClient) -> None:
        """Initialize API client."""
        self._hass = hass
        self._auth_client = auth_client

    async def get_customer_id(self) -> str:
        """Extract customer ID from session data or ID token."""
        # For session-based authentication, get customer ID from session data
        session_data = self._auth_client.session_data
        if session_data and "user" in session_data:
            user_data = session_data["user"]
            customer_id = user_data.get("customerId")
            if customer_id:
                return customer_id

        # Fall back to JWT token extraction for token-based authentication
        id_token = self._auth_client.id_token
        if not id_token:
            raise APIError("No ID token or session data available")

        # Skip JWT decoding for session-based dummy tokens
        if id_token == "session_based":
            raise APIError("Customer ID not found in session data")

        try:
            import jwt

            payload = jwt.decode(id_token, options={"verify_signature": False})
            return payload["customerid"][0]["crmid"]
        except (KeyError, IndexError, ValueError) as exc:
            raise APIError(f"Failed to extract customer ID: {exc}") from exc

    async def get_customer_details(self) -> CustomerDetails:
        """Fetch customer details using session endpoint."""
        response = await self._get(SESSION_URL)

        try:
            json_data = response.json()
            return CustomerDetails.from_api_response(json_data)
        except (ValueError, KeyError) as exc:
            raise InvalidResponseError(
                f"Invalid customer details response: {exc}"
            ) from exc

    async def get_metering_points(self) -> list[MeteringPoint]:
        """Fetch metering points from session endpoint."""
        response = await self._get(SESSION_URL)

        try:
            json_data = response.json()

            # Extract delivery sites from session response
            if "user" in json_data and "deliverySites" in json_data["user"]:
                delivery_sites = json_data["user"]["deliverySites"]
                return [
                    MeteringPoint.from_api_response(site) for site in delivery_sites
                ]
            else:
                return []
        except (ValueError, KeyError, TypeError) as exc:
            raise InvalidResponseError(
                f"Invalid metering points response: {exc}"
            ) from exc

    async def get_time_series_data(
        self,
        metering_point_nos: list[str],
        from_date: datetime | None = None,
        to_date: datetime | None = None,
        resolution: str = "MONTH",
    ) -> list[TimeSeries]:
        """Fetch time series data using tRPC endpoint with automatic retry logic."""
        # Default to last 3 months if no dates provided
        if not from_date:
            from_date = datetime.now().replace(day=1) - timedelta(days=90)
        if not to_date:
            to_date = datetime.now()

        # Try with the requested date range first
        try:
            return await self._fetch_time_series_data(
                metering_point_nos, from_date, to_date, resolution
            )
        except APIError as exc:
            if "Server error" in str(exc) or "reducing date range" in str(exc):
                _LOGGER.warning(
                    "Server error with requested date range, trying with last 30 days"
                )
                # Fallback to last 30 days
                fallback_from = datetime.now() - timedelta(days=30)
                fallback_to = datetime.now()
                try:
                    return await self._fetch_time_series_data(
                        metering_point_nos, fallback_from, fallback_to, resolution
                    )
                except APIError:
                    _LOGGER.warning(
                        "Server error with 30-day range, trying with last 7 days"
                    )
                    # Final fallback to last 7 days
                    final_from = datetime.now() - timedelta(days=7)
                    final_to = datetime.now()
                    return await self._fetch_time_series_data(
                        metering_point_nos, final_from, final_to, resolution
                    )
            else:
                raise

    async def _fetch_time_series_data(
        self,
        metering_point_nos: list[str],
        from_date: datetime,
        to_date: datetime,
        resolution: str,
    ) -> list[TimeSeries]:
        """Internal method to fetch time series data."""
        url = APIEndpoints.get_time_series_url(
            metering_point_nos=metering_point_nos,
            from_date=from_date,
            to_date=to_date,
            resolution=resolution,
        )

        _LOGGER.debug(
            "Fetching time series data from %s to %s with resolution %s",
            from_date.isoformat(),
            to_date.isoformat(),
            resolution,
        )

        response = await self._get(url)

        try:
            data = await self._parse_trpc_response(response)

            if isinstance(data, list):
                return [TimeSeries.from_api_response(item) for item in data]
            else:
                # Single time series
                return [TimeSeries.from_api_response(data)]

        except (ValueError, KeyError, TypeError) as exc:
            raise InvalidResponseError(f"Invalid time series response: {exc}") from exc

    async def get_consumption_data(
        self,
        metering_point_nos: list[str] | None = None,
        from_date: datetime | None = None,
        to_date: datetime | None = None,
        resolution: str = "MONTH",
    ) -> list[ConsumptionData]:
        """Fetch consumption data and convert to legacy format."""
        if not metering_point_nos:
            # Get all metering points for the customer
            metering_points = await self.get_metering_points()
            if not metering_points:
                raise APIError("No metering points found for customer")
            metering_point_nos = [mp.metering_point_no for mp in metering_points]

        time_series_list = await self.get_time_series_data(
            metering_point_nos=metering_point_nos,
            from_date=from_date,
            to_date=to_date,
            resolution=resolution,
        )

        # Convert time series to consumption data
        consumption_data = []
        for time_series in time_series_list:
            consumption_data.extend(ConsumptionData.from_time_series(time_series))

        return consumption_data

    async def get_total_consumption(self) -> list[ConsumptionData]:
        """Get total consumption data for the customer."""
        return await self.get_consumption_data()

    async def _get(self, url: str, retry_count: int = 0) -> Any:
        """Perform authenticated GET request with retry logic for token expiration."""
        # Limit retry attempts to prevent infinite loops
        if retry_count > 1:
            raise APIError(f"Maximum retry attempts ({retry_count}) exceeded for {url}")

        await self._ensure_valid_token()

        async with get_async_client(self._hass) as client:
            # Add session cookies if available
            if self._auth_client.session_cookies:
                for name, value in self._auth_client.session_cookies.items():
                    client.cookies[name] = value
                _LOGGER.debug(
                    "Added %d session cookies to request",
                    len(self._auth_client.session_cookies),
                )

            try:
                # Build headers fresh for each attempt to include updated tokens
                headers = {
                    "Accept": "application/json",
                    "User-Agent": (
                        "Mozilla/5.0 (X11; Linux x86_64; rv:138.0) "
                        "Gecko/20100101 Firefox/138.0"
                    ),
                    "Content-Type": "application/json",
                    "Referer": "https://www.fortum.com/se/el/inloggad/el",
                }

                # Only add Authorization header for non-session endpoints
                # if we have an access token
                if (
                    "/api/trpc/" not in url
                    and "/api/auth/session" not in url
                    and self._auth_client.access_token
                    and self._auth_client.access_token != "session_based"
                ):
                    headers["Authorization"] = (
                        f"Bearer {self._auth_client.access_token}"
                    )

                _LOGGER.debug("Making GET request to: %s (retry: %d)", url, retry_count)
                _LOGGER.debug(
                    "Request headers: %s",
                    {k: v for k, v in headers.items() if k != "Authorization"},
                )
                response = await client.get(url, headers=headers)
                return await self._handle_response(response)
            except APIError as exc:
                # Check if this is a token expiration that was just refreshed
                if str(exc) == "Token expired - retry required" and retry_count == 0:
                    _LOGGER.info("Token was refreshed, retrying request to %s", url)
                    # Retry the request once with the refreshed token
                    return await self._get(url, retry_count + 1)
                elif "Authentication failed" in str(exc):
                    # If authentication completely failed, don't retry
                    _LOGGER.error("Authentication failed, cannot retry: %s", exc)
                    raise
                else:
                    # Re-raise APIError without wrapping it
                    _LOGGER.debug("API error (no retry): %s", exc)
                    raise
            except Exception as exc:
                _LOGGER.exception("GET request failed for %s", url)
                raise APIError("GET request failed") from exc

    async def _parse_trpc_response(self, response: Any) -> dict[str, Any]:
        """Parse tRPC response format."""
        try:
            json_data = response.json()

            # tRPC response format: [{"result": {"data": {"json": actual_data}}}]
            if isinstance(json_data, list) and len(json_data) > 0:
                result = json_data[0]
                if "result" in result and "data" in result["result"]:
                    return result["result"]["data"]["json"]

            # Fallback to direct parsing if format is different
            if isinstance(json_data, dict):
                return json_data
            else:
                # If it's a list, return first item or empty dict
                return json_data[0] if json_data else {}

        except (ValueError, KeyError, IndexError) as exc:
            raise InvalidResponseError(f"Failed to parse tRPC response: {exc}") from exc

    async def _handle_response(self, response) -> Any:
        """Handle API response with error checking."""
        _LOGGER.debug("Response status: %s", response.status_code)

        if response.status_code == 401:
            # Token expired, try to refresh
            _LOGGER.info("Token expired, attempting refresh")
            try:
                await self._auth_client.refresh_access_token()
                _LOGGER.debug("Token refresh successful, signaling retry")
                raise APIError("Token expired - retry required")
            except Exception as refresh_exc:
                _LOGGER.error("Token refresh failed: %s", refresh_exc)
                # If refresh fails, we need to re-authenticate
                raise APIError(
                    "Authentication failed - re-authentication required"
                ) from refresh_exc

        if response.status_code == 403:
            # Forbidden, might need re-authentication
            _LOGGER.warning("Access forbidden, may need re-authentication")
            raise APIError("Access forbidden - authentication may be required")

        if response.status_code == 500:
            # Server error - check if it's a tRPC error with specific format
            try:
                error_data = response.json()
                if isinstance(error_data, list) and len(error_data) > 0:
                    error_item = error_data[0]
                    if "error" in error_item:
                        error_details = error_item["error"]
                        if "json" in error_details:
                            json_error = error_details["json"]
                            error_msg = json_error.get("message", "Unknown error")
                            error_code = json_error.get("code", "Unknown")
                            _LOGGER.error(
                                "Server error (tRPC): %s (code: %s)",
                                error_msg,
                                error_code,
                            )
                            # For INTERNAL_SERVER_ERROR, try with reduced date range
                            if error_msg == "INTERNAL_SERVER_ERROR":
                                raise APIError(
                                    "Server error - try reducing date range "
                                    "or changing resolution"
                                )
                            else:
                                raise APIError(f"Server error: {error_msg}")
            except (ValueError, KeyError):
                pass  # Fall through to generic handling

            _LOGGER.error("Server error (500): %s", response.text)
            raise APIError("Server internal error - try again later")

        if response.status_code != 200:
            _LOGGER.error(
                "Unexpected status code: %s, response: %s",
                response.status_code,
                response.text,
            )
            raise UnexpectedStatusCodeError(
                f"Unexpected status code {response.status_code}: {response.text}"
            )

        if not response.text:
            raise InvalidResponseError("Empty response from API")

        return response

    async def _ensure_valid_token(self) -> None:
        """Ensure we have a valid access token."""
        if self._auth_client.is_token_expired():
            # Check if we have a real OAuth2 refresh token or session-based token
            if (
                self._auth_client.refresh_token
                and self._auth_client.refresh_token != "session_based"
            ):
                await self._auth_client.refresh_access_token()
            else:
                # For session-based auth or no refresh token, re-authenticate
                await self._auth_client.authenticate()

    async def test_connection(self) -> dict[str, Any]:
        """Test API connection and return status information."""
        try:
            # Test session endpoint first
            session_response = await self._get(SESSION_URL)
            session_data = session_response.json()

            # Check if we have user data
            user_data = session_data.get("user", {})
            if not user_data:
                return {
                    "success": False,
                    "error": "No user data in session - authentication may have failed",
                    "session_status": "invalid",
                }

            # Extract metering points
            metering_points = []
            if "deliverySites" in user_data:
                for site in user_data["deliverySites"]:
                    if (
                        "consumption" in site
                        and "meteringPointNo" in site["consumption"]
                    ):
                        metering_points.append(site["consumption"]["meteringPointNo"])

            if not metering_points:
                return {
                    "success": False,
                    "error": "No metering points found in session data",
                    "session_status": "valid",
                    "user_id": user_data.get("id"),
                }

            # Test a simple tRPC call with minimal data
            try:
                # Try last 24 hours with hourly resolution (minimal request)
                test_from = datetime.now() - timedelta(hours=24)
                test_to = datetime.now()

                test_series = await self._fetch_time_series_data(
                    [metering_points[0]], test_from, test_to, "HOUR"
                )

                return {
                    "success": True,
                    "session_status": "valid",
                    "user_id": user_data.get("id"),
                    "metering_points": metering_points,
                    "api_test": "passed",
                    "test_data_points": len(test_series),
                }

            except Exception as api_exc:
                return {
                    "success": False,
                    "error": f"API test failed: {api_exc}",
                    "session_status": "valid",
                    "user_id": user_data.get("id"),
                    "metering_points": metering_points,
                    "api_test": "failed",
                }

        except Exception as exc:
            return {
                "success": False,
                "error": f"Connection test failed: {exc}",
                "session_status": "unknown",
            }
