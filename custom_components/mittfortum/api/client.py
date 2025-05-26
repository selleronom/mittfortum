"""Main API client for MittFortum."""

from __future__ import annotations

from datetime import datetime, timedelta
import logging
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
        """Fetch time series data using tRPC endpoint."""
        # Default to last 12 months if no dates provided
        if not from_date:
            from_date = datetime.now().replace(day=1) - timedelta(days=365)
        if not to_date:
            to_date = datetime.now()

        url = APIEndpoints.get_time_series_url(
            metering_point_nos=metering_point_nos,
            from_date=from_date,
            to_date=to_date,
            resolution=resolution,
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

    async def _get(self, url: str) -> Any:
        """Perform authenticated GET request."""
        await self._ensure_valid_token()

        # For tRPC endpoints, use session-based authentication (cookies)
        # For session endpoints, use session-based authentication (no explicit auth header)
        headers = {
            "Accept": "application/json",
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:138.0) Gecko/20100101 Firefox/138.0",
            "Content-Type": "application/json",
            "Referer": "https://www.fortum.com/se/el/inloggad/el",
        }

        # Only add Authorization header for non-session endpoints if we have an access token
        if (
            "/api/trpc/" not in url
            and "/api/auth/session" not in url
            and self._auth_client.access_token
            and self._auth_client.access_token != "session_based"
        ):
            headers["Authorization"] = f"Bearer {self._auth_client.access_token}"

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
                _LOGGER.debug("Making GET request to: %s", url)
                _LOGGER.debug(
                    "Request headers: %s",
                    {k: v for k, v in headers.items() if k != "Authorization"},
                )
                response = await client.get(url, headers=headers)
                return await self._handle_response(response)
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
            await self._auth_client.refresh_access_token()
            raise APIError("Token expired - retry required")

        if response.status_code == 403:
            # Forbidden, might need re-authentication
            _LOGGER.warning("Access forbidden, may need re-authentication")
            raise APIError("Access forbidden - authentication may be required")

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
            if self._auth_client.refresh_token:
                await self._auth_client.refresh_access_token()
            else:
                await self._auth_client.authenticate()
