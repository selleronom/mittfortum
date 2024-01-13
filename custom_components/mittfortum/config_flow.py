"""Config flow for MittFortum integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError

from .api import FortumAPI  # Import the API class
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


class PlaceholderHub:
    """Placeholder class to make tests pass.

    TODO Remove this placeholder class and replace with things from your PyPI package.
    """

    def __init__(self, host: str) -> None:
        """Initialize."""
        self.host = host

    async def authenticate(self, username: str, password: str) -> bool:
        """Test if we can authenticate with the host."""
        return True


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect.

    Data has the keys from STEP_USER_DATA_SCHEMA with values provided by the user.
    """
    try:
        api = FortumAPI(
            data[CONF_USERNAME],
            data[CONF_PASSWORD],
            data["customer_id"],
            data["metering_point"],
            data["street_address"],
            data["city"],
        )
    except Exception as e:
        _LOGGER.error("Failed to create API: %s", e)
        raise CannotConnect(f"Failed to create API: {e}") from e

    try:
        if not await api.login():
            raise InvalidAuth
    except Exception as e:
        _LOGGER.error("Failed to login: %s", e)
        raise CannotConnect(f"Failed to login: {e}") from e

    return {"title": data[CONF_USERNAME]}


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
