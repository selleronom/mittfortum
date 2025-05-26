"""Energy consumption sensor for MittFortum."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import UnitOfEnergy

from ..const import ENERGY_SENSOR_KEY

if TYPE_CHECKING:
    from ..coordinator import MittFortumDataCoordinator
    from ..device import MittFortumDevice

from ..entity import MittFortumEntity


class MittFortumEnergySensor(MittFortumEntity, SensorEntity):
    """Energy consumption sensor for MittFortum."""

    def __init__(
        self,
        coordinator: MittFortumDataCoordinator,
        device: MittFortumDevice,
    ) -> None:
        """Initialize energy sensor."""
        super().__init__(
            coordinator=coordinator,
            device=device,
            entity_key=ENERGY_SENSOR_KEY,
            name="Energy Consumption",
        )

    @property
    def native_value(self) -> float | None:
        """Return the state of the sensor."""
        if self.coordinator.data is None:
            return None
        if not self.coordinator.data:  # Empty list
            return 0

        return sum(item.value for item in self.coordinator.data)

    @property
    def native_unit_of_measurement(self) -> str:
        """Return the unit of measurement."""
        return UnitOfEnergy.KILO_WATT_HOUR

    @property
    def device_class(self) -> SensorDeviceClass:
        """Return the device class."""
        return SensorDeviceClass.ENERGY

    @property
    def state_class(self) -> SensorStateClass:
        """Return the state class."""
        return SensorStateClass.TOTAL

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return additional state attributes."""
        if not self.coordinator.data:
            return None

        data = self.coordinator.data
        return {
            "total_records": len(data),
            "latest_date": data[-1].date_time.isoformat() if data else None,
            "unit": data[0].unit if data else None,
        }
