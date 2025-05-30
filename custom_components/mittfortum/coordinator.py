"""Data update coordinator for MittFortum integration."""

from __future__ import annotations

import logging
from datetime import timedelta  # noqa: TC003
from typing import TYPE_CHECKING

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DEFAULT_UPDATE_INTERVAL
from .exceptions import APIError
from .models import ConsumptionData

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

    from .api import FortumAPIClient

_LOGGER = logging.getLogger(__name__)


class MittFortumDataCoordinator(DataUpdateCoordinator[list[ConsumptionData]]):
    """Data update coordinator for MittFortum."""

    def __init__(
        self,
        hass: HomeAssistant,
        api_client: FortumAPIClient,
        update_interval: timedelta = DEFAULT_UPDATE_INTERVAL,
    ) -> None:
        """Initialize coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name="MittFortum",
            update_interval=update_interval,
        )
        self.api_client = api_client

    async def _async_update_data(self) -> list[ConsumptionData]:
        """Fetch data from API."""
        try:
            _LOGGER.debug("Fetching consumption data from API")
            data = await self.api_client.get_total_consumption()
            if data is None:
                data = []
            _LOGGER.debug("Successfully fetched %d consumption records", len(data))
        except APIError as exc:
            # For authentication errors, provide more specific error message
            if (
                "Token expired" in str(exc)
                or "Access forbidden" in str(exc)
                or "Authentication failed" in str(exc)
            ):
                _LOGGER.warning(
                    "Authentication error during data update: %s. "
                    "This may be temporary due to session propagation.",
                    exc,
                )
                raise UpdateFailed(f"Authentication error: {exc}") from exc
            else:
                _LOGGER.exception("API error during data update")
                raise UpdateFailed(f"API error: {exc}") from exc
        except Exception as exc:
            _LOGGER.exception("Unexpected error during data update")
            raise UpdateFailed(f"Unexpected error: {exc}") from exc
        else:
            return data
