"""Config flow for MittFortum integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_USERNAME, CONF_PASSWORD
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError

from .api import FortumAPI  # Import the API class
from .oauth2_client import OAuth2Client
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_USERNAME): str,
        vol.Required(CONF_PASSWORD): str,
        vol.Required("customer_id"): str,
        vol.Required("metering_point"): str,
        vol.Required("street_address"): str,
        vol.Required("city"): str,
    }
)


from .oauth2_client import OAuth2Client


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect.

    Data has the keys from STEP_USER_DATA_SCHEMA with values provided by the user.
    """
    try:
        oauth_client = OAuth2Client(
            username=data[CONF_USERNAME], password=data[CONF_PASSWORD]
        )
        api = FortumAPI(
            oauth_client=oauth_client,
            customer_id=data["customer_id"],
            metering_point=data["metering_point"],
            street_address=data["street_address"],
            city=data["city"],
        )
    except Exception as e:
        _LOGGER.error("Failed to create API: %s", e)
        raise CannotConnect(f"Failed to create API: {e}") from e

    try:
        if not await oauth_client.login():
            raise InvalidAuth
    except Exception as e:
        _LOGGER.error("Failed to login: %s", e)
        raise CannotConnect(f"Failed to login: {e}") from e

    try:
        if not await api.get_total_consumption():
            raise InvalidAuth
    except Exception as e:
        _LOGGER.error("Failed to login: %s", e)
        raise CannotConnect(f"Failed to login: {e}") from e

    return {"title": data["customer_id"]}


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for MittFortum integration."""

    VERSION = 1

    async def async_step_user(self, user_input=None) -> FlowResult:
        """Handle a flow initialized by the user."""
        errors = {}
        if user_input is not None:
            try:
                info = await validate_input(self.hass, user_input)
                return self.async_create_entry(title=info["title"], data=user_input)
            except InvalidAuth:
                _LOGGER.error("Invalid authentication")
                errors["base"] = "invalid_auth"
            except CannotConnect as e:
                _LOGGER.error("Cannot connect: %s", e)
                errors["base"] = str(e)
            except Exception as e:  # for unexpected exceptions
                _LOGGER.error("Unexpected error: %s", e)
                errors["base"] = "unknown"
        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""
