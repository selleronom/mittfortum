"""Config flow for MittFortum integration."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from homeassistant import config_entries
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
import voluptuous as vol

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

from .api import FortumAPIClient, OAuth2AuthClient
from .const import DOMAIN
from .exceptions import AuthenticationError, MittFortumError

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_USERNAME): str,
        vol.Required(CONF_PASSWORD): str,
    }
)


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect."""
    try:
        # Test authentication
        auth_client = OAuth2AuthClient(
            hass=hass,
            username=data[CONF_USERNAME],
            password=data[CONF_PASSWORD],
        )

        await auth_client.authenticate()

        # Test API connection
        api_client = FortumAPIClient(hass, auth_client)
        await api_client.get_customer_id()

        return {"title": f"MittFortum ({data[CONF_USERNAME]})"}

    except AuthenticationError as exc:
        _LOGGER.exception("Authentication failed")
        raise InvalidAuth from exc
    except MittFortumError as exc:
        _LOGGER.exception("API connection failed")
        raise CannotConnect from exc
    except Exception as exc:
        _LOGGER.exception("Unexpected error during validation")
        raise CannotConnect from exc


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for MittFortum."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                info = await validate_input(self.hass, user_input)

                # Check if already configured
                await self.async_set_unique_id(user_input[CONF_USERNAME])
                self._abort_if_unique_id_configured()

                return self.async_create_entry(title=info["title"], data=user_input)

            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )


class CannotConnect(Exception):
    """Error to indicate we cannot connect."""


class InvalidAuth(Exception):
    """Error to indicate there is invalid auth."""
