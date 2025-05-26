"""Cost sensor for MittFortum."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)

from ..const import COST_SENSOR_KEY

if TYPE_CHECKING:
    from ..coordinator import MittFortumDataCoordinator
    from ..device import MittFortumDevice

from ..entity import MittFortumEntity


class MittFortumCostSensor(MittFortumEntity, SensorEntity):
    """Cost sensor for MittFortum."""

    def __init__(
        self,
        coordinator: MittFortumDataCoordinator,
        device: MittFortumDevice,
    ) -> None:
        """Initialize cost sensor."""
        super().__init__(
            coordinator=coordinator,
            device=device,
            entity_key=COST_SENSOR_KEY,
            name="Total Cost",
        )

    @property
    def native_value(self) -> float | None:
        """Return the state of the sensor."""
        if self.coordinator.data is None:
            return None
        if not self.coordinator.data:  # Empty list
            return 0

        return sum(item.cost for item in self.coordinator.data if item.cost is not None)

    @property
    def native_unit_of_measurement(self) -> str:
        """Return the unit of measurement."""
        return "SEK"

    @property
    def device_class(self) -> SensorDeviceClass:
        """Return the device class."""
        return SensorDeviceClass.MONETARY

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
        cost_data = [item for item in data if item.cost is not None]

        return {
            "total_records_with_cost": len(cost_data),
            "currency": "SEK",
            "latest_date": data[-1].date_time.isoformat() if data else None,
        }
