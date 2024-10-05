"""The MittFortum integration."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_USERNAME, CONF_PASSWORD, Platform
from homeassistant.core import HomeAssistant

from .api import ConfigurationError, FortumAPI, LoginError  # Import the API class
from .oauth2_client import OAuth2Client

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)
PLATFORMS: list[Platform] = [Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up MittFortum from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    # Get the parameters from the config entry
    username = entry.data[CONF_USERNAME]
    password = entry.data[CONF_PASSWORD]
    customer_id = entry.data["customer_id"]
    metering_point = entry.data["metering_point"]
    street_address = entry.data["street_address"]
    city = entry.data["city"]

    try:
        # Initialize OAuth2Client
        oauth_client = OAuth2Client(
            username=username,
            password=password,
            HomeAssistant=hass,
        )

        # Create API instance
        api = FortumAPI(
            oauth_client=oauth_client,
            customer_id=customer_id,
            metering_point=metering_point,
            street_address=street_address,
            city=city,
            HomeAssistant=hass,
        )

        # Perform login to obtain session token
        await oauth_client.login()

        # Validate the API connection (and authentication)
        await api.get_total_consumption()

    except LoginError as e:
        _LOGGER.error("Failed to log in to MittFortum: %s", e)
        return False
    except ConfigurationError as e:
        _LOGGER.error("Invalid configuration for MittFortum: %s", e)
        return False

    # Store an API object for your platforms to access
    hass.data[DOMAIN][entry.entry_id] = api

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
