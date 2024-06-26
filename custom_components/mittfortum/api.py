"""Module for interacting with the Fortum service API."""

import json
import logging
from datetime import datetime

import httpx
from httpx import HTTPStatusError

_LOGGER = logging.getLogger(__name__)


class FortumAPI:
    """API client for interacting with the Fortum service."""

    LOGIN_URL = "https://sso.fortum.com/am/oauth2/access_token"
    DATA_URL = "https://retail-lisa-eu-prd-energyflux.herokuapp.com/api/consumption/customer/{customer_id}/meteringPoint/{metering_point}"

    def __init__(
        self,
        refresh_token,
        customer_id,
        metering_point,
        street_address,
        city,
    ) -> None:
        self.refresh_token = refresh_token
        self.customer_id = customer_id
        self.metering_point = metering_point
        self.street_address = street_address
        self.city = city
        self.session_token = None

    async def login(self):
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        payload = {
            "grant_type": "refresh_token",
            "refresh_token": self.refresh_token,
            "client_id": "swedenmypagesprod",
        }
        response = None
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.LOGIN_URL, data=payload, headers=headers
                )
            response.raise_for_status()
            self.session_token = response.json().get("access_token")
            self.refresh_token = response.json().get("refresh_token")

            return self.session_token is not None
        except httpx.HTTPStatusError as e:
            _LOGGER.error(f"Failed to login: {e}")
            return False
        except json.JSONDecodeError:
            if response is not None:
                _LOGGER.error(f"Failed to parse response as JSON: {response.content}")
            else:
                _LOGGER.error(
                    "Failed to parse response as JSON, but no response was received"
                )
            return False

    async def get_total_consumption(self):
        return await self._get_data(
            self.customer_id,
            self.metering_point,
            "yearly",
            self.street_address,
            self.city,
        )

    async def _post(self, url, data):
        headers = {
            "X-Auth-System": "FR-CIAM",
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.session_token}",
        }
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(url, headers=headers, json=data)
            if response.status_code == 403:
                _LOGGER.info("Session expired, renewing login")
                if not await self.login():
                    raise Exception("Failed to renew login")
                headers = {"Authorization": f"Bearer {self.session_token}"}
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
        self,
        customer_id,
        metering_point,
        resolution,
        street_address,
        city,
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
