"""Device representation for MittFortum integration."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo

from .const import DOMAIN, MANUFACTURER, MODEL


class MittFortumDevice:
    """Representation of a MittFortum device."""

    def __init__(self, customer_id: str, name: str | None = None) -> None:
        """Initialize device."""
        self._customer_id = customer_id
        self._name = name or "MittFortum Account"

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._customer_id)},
            name=self._name,
            manufacturer=MANUFACTURER,
            model=MODEL,
            entry_type=DeviceEntryType.SERVICE,
        )

    @property
    def unique_id(self) -> str:
        """Return unique device ID."""
        return self._customer_id
