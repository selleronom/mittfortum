"""Sensor module contains the FortumSensor class for energy consumption."""
from datetime import timedelta
import logging

from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, entry, async_add_entities) -> None:
    """Set up the Fortum sensor entry.

    Args:
        hass: Home Assistant instance.
        entry: Config entry.
        async_add_entities: Function to add entities.

    Returns:
        None
    """
    api = hass.data[DOMAIN][entry.entry_id]
    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name="sensor",
        update_method=api.get_data,
        update_interval=timedelta(minutes=30),
    )
    await coordinator.async_config_entry_first_refresh()
    async_add_entities([FortumSensor(coordinator, entry, "kWh")])


class FortumSensor(CoordinatorEntity, SensorEntity):
    """Class representing the Fortum energy consumption sensor."""

    def __init__(self, coordinator, entry, unit_of_measurement) -> None:
        """Initialize the FortumSensor class."""
        super().__init__(coordinator)
        self._entry = entry
        self._unit_of_measurement = unit_of_measurement

    @property
    def unique_id(self) -> str:
        """Return the unique ID of the sensor."""
        return self._entry.entry_id

    @property
    def name(self) -> str:
        """Return the name of the sensor."""
        return "Fortum Energy Consumption"

    @property
    def state(self) -> int | None:
        """Return the state of the sensor."""
        # The coordinator's data is the response from your API
        data = self.coordinator.data
        if data:
            # Extract the value from the first item in the response
            return data[0]["value"]
        else:
            return None

    @property
    def device_state_attributes(self):
        """Return the state attributes."""
        data = self.coordinator.data
        if data:
            return {
                "temperature": data[0]["temp"],
                "date": data[0]["dateTime"],
            }
        else:
            return {}

    @property
    def unit_of_measurement(self) -> str:
        """Return the unit of measurement."""
        return self._unit_of_measurement

    @property
    def device_class(self) -> str:
        """Return the class of this device, from component DEVICE_CLASSES."""
        return "energy"

    @property
    def state_class(self) -> str:
        """Return the state class of this device."""
        return "total"
