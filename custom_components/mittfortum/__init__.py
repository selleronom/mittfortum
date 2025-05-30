"""The MittFortum integration."""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.exceptions import ConfigEntryNotReady

from .api import FortumAPIClient, OAuth2AuthClient

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant
from .const import DOMAIN, PLATFORMS
from .coordinator import MittFortumDataCoordinator
from .device import MittFortumDevice
from .exceptions import AuthenticationError, MittFortumError

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up MittFortum from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    # Get credentials from config entry
    username = entry.data[CONF_USERNAME]
    password = entry.data[CONF_PASSWORD]

    try:
        # Initialize authentication client
        auth_client = OAuth2AuthClient(
            hass=hass,
            username=username,
            password=password,
        )

        # Perform initial authentication
        await auth_client.authenticate()

        # Create API client
        api_client = FortumAPIClient(hass, auth_client)

        # Get customer ID for device creation
        customer_id = await api_client.get_customer_id()
        device = MittFortumDevice(customer_id)

        # Create data coordinator
        coordinator = MittFortumDataCoordinator(hass, api_client)

        # Perform initial data fetch with retry for session propagation issues
        max_retries = 3
        for attempt in range(max_retries):
            try:
                await coordinator.async_config_entry_first_refresh()
                break
            except ConfigEntryNotReady as exc:
                if (
                    "Authentication error" in str(exc)
                    and "Token expired" in str(exc)
                    and attempt < max_retries - 1
                ):
                    _LOGGER.warning(
                        "Initial authentication failed (attempt %d/%d), "
                        "retrying after delay due to potential session "
                        "propagation issue: %s",
                        attempt + 1,
                        max_retries,
                        exc,
                    )
                    # Add delay to allow session propagation
                    await asyncio.sleep(1.0 * (attempt + 1))
                    continue
                else:
                    # Re-raise the exception if it's not a retry-able auth error
                    # or we've exhausted retries
                    raise

        # Store coordinator and device for platforms
        hass.data[DOMAIN][entry.entry_id] = {
            "coordinator": coordinator,
            "device": device,
            "api_client": api_client,
        }

        # Forward setup to platforms
        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    except AuthenticationError:
        _LOGGER.exception("Authentication failed for MittFortum")
        return False
    except MittFortumError:
        _LOGGER.exception("Setup failed for MittFortum")
        return False
    except Exception:
        _LOGGER.exception("Unexpected error setting up MittFortum")
        return False
    else:
        return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
