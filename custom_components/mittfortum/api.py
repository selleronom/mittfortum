"""Module for interacting with the Fortum service API."""

import json
import logging
import time
from datetime import datetime

import httpx
from httpx import HTTPStatusError
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from seleniumwire import webdriver

_LOGGER = logging.getLogger(__name__)


class FortumAPI:
    """API client for interacting with the Fortum service."""

    LOGIN_URL = "https://www.mittfortum.se/"
    DATA_URL = "https://retail-lisa-eu-prd-energyflux.herokuapp.com/api/consumption/customer/{customer_id}/meteringPoint/{metering_point}"

    def __init__(
        self,
        username,
        password,
        customer_id,
        metering_point,
        street_address,
        city,
    ) -> None:
        self.username = username
        self.password = password
        self.customer_id = customer_id
        self.metering_point = metering_point
        self.street_address = street_address
        self.city = city
        self.session_token = None

    async def login(self):
        options = Options()
        options.add_argument(argument="--headless")

        driver = webdriver.Chrome(options=options)
        driver.get(url=self.LOGIN_URL)

        wait = WebDriverWait(driver=driver, timeout=10)

        username_field = wait.until(
            method=EC.presence_of_element_located(
                locator=(By.ID, "floatingLabelInput34")
            )
        )
        password_field = wait.until(
            method=EC.presence_of_element_located(
                locator=(By.ID, "floatingLabelInput39")
            )
        )

        username_field.send_keys(self.username)
        password_field.send_keys(self.password)
        password_field.send_keys(Keys.RETURN)

        session_token = None
        start_time = time.time()

        while True:
            for request in driver.requests:
                if "access_token" in request.path and request.response:
                    body = json.loads(s=request.response.body)
                    session_token = body.get("access_token")
                    break
            if session_token or time.time() - start_time > 30:
                break
            time.sleep(1)

        if session_token:
            return self.session_token is not None
        else:
            _LOGGER.error("Access Token not found")

        driver.quit()

    async def get_total_consumption(self):
        return await self._get_data(
            self.customer_id,
            self.metering_point,
            "yearly",
            self.street_address,
            self.city,
        )

    async def _post(self, url, data):
        headers = {"Authorization": f"Bearer {self.session_token}"}
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
