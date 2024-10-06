"""Module for interacting with the Fortum service API."""

from datetime import datetime
import json
import logging

from httpx import HTTPStatusError

from homeassistant.helpers.httpx_client import get_async_client

from .oauth2_client import OAuth2Client

_LOGGER = logging.getLogger(__name__)


class FortumAPI:
    """API client for interacting with the Fortum service."""

    DATA_URL = "https://retail-lisa-eu-prd-energyflux.herokuapp.com/api/consumption/customer/{customer_id}/meteringPoint/{metering_point}"

    def __init__(
        self,
        oauth_client: OAuth2Client,
        customer_id: str,
        metering_point: str,
        street_address: str,
        city: str,
        HomeAssistant=None,
    ) -> None:
        self.oauth_client = oauth_client
        self.customer_id = customer_id
        self.metering_point = metering_point
        self.street_address = street_address
        self.city = city
        self.hass = HomeAssistant

    async def get_total_consumption(self):
        return await self._get_data(
            self.customer_id,
            self.metering_point,
            "yearly",
            self.street_address,
            self.city,
        )

    async def _post(self, url, data):
        if self.oauth_client.is_token_expired():
            await self.oauth_client.refresh_access_token()

        headers = {
            "X-Auth-System": "FR-CIAM",
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.oauth_client.session_token}",
        }
        try:
            async with get_async_client(self.hass) as client:
                response = await client.post(url, headers=headers, json=data)
            if response.status_code == 403:
                _LOGGER.info("Session expired, renewing login")
                if not await self.oauth_client.login():
                    raise Exception("Failed to renew login")
                headers["Authorization"] = f"Bearer {self.oauth_client.session_token}"
                response = await client.post(url, headers=headers, json=data)
            elif response.status_code != 200:
                _LOGGER.error(
                    "Unexpected status code %s from API", response.status_code
                )
                raise UnexpectedStatusCode(
                    f"Unexpected status code {response.status_code} from API"
                )
            return response
        except HTTPStatusError as e:
            _LOGGER.error(f"Failed to post data: {e}")
            return None

    async def _get_data(
        self, customer_id, metering_point, resolution, street_address, city
    ):
        current_year = datetime.now().year
        from_date = str(current_year - 4) + "-01-01"
        to_date = str(current_year) + "-12-31"

        url = self.DATA_URL.format(
            customer_id=customer_id, metering_point=metering_point
        )
        data = {
            "from": from_date,
            "to": to_date,
            "resolution": resolution,
            "postalAddress": street_address,
            "postOffice": city,
        }
        response = await self._post(url, data)
        if response is None or not response.text:
            _LOGGER.error("Empty response from API")
            raise InvalidResponse("Empty response from API")
        try:
            return response.json()
        except json.JSONDecodeError as e:
            _LOGGER.error(f"Invalid JSON in response: {response.text}")
            raise InvalidResponse("Invalid JSON in response") from e


class APIError(Exception):
    """Raised when there's an error related to the API."""


class InvalidResponse(APIError):
    """Raised when the API response is invalid."""


class UnexpectedStatusCode(APIError):
    """Raised when the API response has an unexpected status code."""


class LoginError(Exception):
    """Exception raised for errors in the login process."""

    def __init__(self, message="Failed to log in to MittFortum") -> None:
        self.message = message
        super().__init__(self.message)


class ConfigurationError(Exception):
    """Exception raised for errors in the configuration process."""

    def __init__(self, message="Invalid configuration for MittFortum") -> None:
        self.message = message
        super().__init__(self.message)
