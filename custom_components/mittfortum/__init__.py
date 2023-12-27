"""The MittFortum integration."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME, Platform
from homeassistant.core import HomeAssistant

from .api import FortumAPI  # Import the API class
from .const import DOMAIN

PLATFORMS: list[Platform] = [Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up MittFortum from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    # Get the parameters from the config entry
    username = entry.data[CONF_USERNAME]
    password = entry.data[CONF_PASSWORD]
    customer_id = entry.data["customer_id"]
    metering_point = entry.data["metering_point"]
    resolution = entry.data["resolution"]
    street_address = entry.data["street_address"]
    city = entry.data["city"]

    # Create API instance
    api = FortumAPI(
        username,
        password,
        customer_id,
        metering_point,
        resolution,
        street_address,
        city,
    )

    # Validate the API connection (and authentication)
    await api.login()

    # Store an API object for your platforms to access
    hass.data[DOMAIN][entry.entry_id] = api

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
