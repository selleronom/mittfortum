"""Module for interacting with the Fortum service API."""
from datetime import datetime, timedelta
import json
import logging

from dateutil.relativedelta import relativedelta
import httpx

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError

_LOGGER = logging.getLogger(__name__)


class FortumAPI:
    """API client for interacting with the Fortum service."""

    def __init__(
        self,
        username,
        password,
        customer_id,
        metering_point,
        resolution,
        street_address,
        city,
    ) -> None:
        """Initialize a FortumAPI instance.

        Args:
            username (str): The username for authentication.
            password (str): The password for authentication.
            customer_id (str): The ID of the customer.
            metering_point (str): The ID of the metering point.
            resolution (str): The resolution of the data (e.g., "hourly", "daily").
            street_address (str): The postal address of the customer.
            city (str): The post office of the customer.
        """
        self.username = username
        self.password = password
        self.customer_id = customer_id
        self.metering_point = metering_point
        self.resolution = resolution
        self.street_address = street_address
        self.city = city
        self.session_token = None

    async def login(self):
        """Perform login to obtain a session token.

        Returns:
            bool: True if login is successful and a session token is obtained, False otherwise.
        """
        login_url = "https://retail-lisa-eu-auth.herokuapp.com/api/login"
        login_data = {"username": self.username, "password": self.password}
        async with httpx.AsyncClient() as client:
            response = await client.post(login_url, data=login_data)
        self.session_token = response.json().get("access_token")
        return self.session_token is not None

    async def get_data(self):
        """Retrieve consumption data for a specific customer and metering point.

        Returns:
            dict: The consumption data in JSON format.
        """
        return await self._get_data(
            self.customer_id,
            self.metering_point,
            self.resolution,
            self.street_address,
            self.city,
        )

    async def _get_data(
        self,
        customer_id,
        metering_point,
        resolution,
        street_address,
        city,
    ):
        """Retrieve consumption data for a specific customer and metering point.

        Args:
            customer_id (str): The ID of the customer.
            metering_point (str): The ID of the metering point.
            resolution (str): The resolution of the data (e.g., "hourly", "daily").
            street_address (str): The postal address of the customer.
            city (str): The post office of the customer.

        Returns:
            dict: The consumption data in JSON format.
        """

        now = datetime.now()

        if resolution.lower() == "hourly":
            from_date = (now - timedelta(hours=1)).isoformat()
        elif resolution.lower() == "daily":
            from_date = (now - timedelta(days=1)).isoformat()
        else:  # Monthly
            from_date = (now - relativedelta(months=1)).replace(day=1).isoformat()

        to_date = now.isoformat()

        url = f"https://retail-lisa-eu-prd-energyflux.herokuapp.com/api/consumption/customer/{customer_id}/meteringPoint/{metering_point}"
        headers = {"Authorization": f"Bearer {self.session_token}"}
        data = {
            "from": from_date,
            "to": to_date,
            "resolution": resolution,
            "postalAddress": street_address,
            "postOffice": city,
        }
        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=headers, json=data)
        if response.status_code != 200:
            _LOGGER.error("Unexpected status code %s from API", response.status_code)
            raise UnexpectedStatusCode(
                f"Unexpected status code {response.status_code} from API"
            )
        if not response.text:
            _LOGGER.error("Empty response from API")
            raise InvalidResponse("Empty response from API")
        try:
            return response.json()
        except json.JSONDecodeError as e:
            _LOGGER.error("Invalid JSON in response")
            raise InvalidResponse("Invalid JSON in response") from e


class APIError(Exception):
    """Raised when there's an error related to the API."""


class InvalidResponse(APIError):
    """Raised when the API response is invalid."""


class UnexpectedStatusCode(APIError):
    """Raised when the API response has an unexpected status code."""
