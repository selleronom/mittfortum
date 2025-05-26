"""Data models for the MittFortum integration."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass
class EnergyDataPoint:
    """Represents an energy data point."""

    value: float
    type: str

    @classmethod
    def from_api_response(cls, data: dict[str, Any]) -> EnergyDataPoint:
        """Create instance from API response data."""
        return cls(
            value=float(data["value"]),
            type=data["type"],
        )


@dataclass
class CostDataPoint:
    """Represents a cost data point."""

    total: float
    value: float
    type: str

    @classmethod
    def from_api_response(cls, data: dict[str, Any]) -> CostDataPoint:
        """Create instance from API response data."""
        return cls(
            total=float(data["total"]),
            value=float(data["value"]),
            type=data["type"],
        )


@dataclass
class Price:
    """Represents price information."""

    total: float
    value: float
    vat_amount: float
    vat_percentage: float

    @classmethod
    def from_api_response(cls, data: dict[str, Any]) -> Price:
        """Create instance from API response data."""
        return cls(
            total=float(data["total"]),
            value=float(data["value"]),
            vat_amount=float(data["vatAmount"]),
            vat_percentage=float(data["vatPercentage"]),
        )


@dataclass
class TemperatureReading:
    """Represents temperature reading."""

    temperature: float

    @classmethod
    def from_api_response(cls, data: dict[str, Any]) -> TemperatureReading:
        """Create instance from API response data."""
        return cls(
            temperature=float(data["temperature"]),
        )


@dataclass
class TimeSeriesDataPoint:
    """Represents a time series data point."""

    at_utc: datetime
    energy: list[EnergyDataPoint]
    cost: list[CostDataPoint] | None
    price: Price | None
    temperature_reading: TemperatureReading | None

    @classmethod
    def from_api_response(cls, data: dict[str, Any]) -> TimeSeriesDataPoint:
        """Create instance from API response data."""
        energy_points = [EnergyDataPoint.from_api_response(e) for e in data["energy"]]

        cost_points = None
        if data.get("cost"):
            cost_points = [CostDataPoint.from_api_response(c) for c in data["cost"]]

        price = None
        if data.get("price"):
            price = Price.from_api_response(data["price"])

        temperature = None
        if data.get("temperatureReading"):
            temperature = TemperatureReading.from_api_response(
                data["temperatureReading"]
            )

        return cls(
            at_utc=datetime.fromisoformat(data["atUTC"].replace("Z", "+00:00")),
            energy=energy_points,
            cost=cost_points,
            price=price,
            temperature_reading=temperature,
        )

    @property
    def total_energy(self) -> float:
        """Get total energy value."""
        return sum(point.value for point in self.energy if point.type == "ENERGY")

    @property
    def total_cost(self) -> float:
        """Get total cost value."""
        if not self.cost:
            return 0.0
        return sum(point.total for point in self.cost)


@dataclass
class TimeSeries:
    """Represents time series data."""

    delivery_site_category: str
    measurement_unit: str
    metering_point_no: str
    price_unit: str
    cost_unit: str
    temperature_unit: str
    series: list[TimeSeriesDataPoint]

    @classmethod
    def from_api_response(cls, data: dict[str, Any]) -> TimeSeries:
        """Create instance from API response data."""
        series_points = [
            TimeSeriesDataPoint.from_api_response(s) for s in data["series"]
        ]

        return cls(
            delivery_site_category=data["deliverySiteCategory"],
            measurement_unit=data["measurementUnit"],
            metering_point_no=data["meteringPointNo"],
            price_unit=data["priceUnit"],
            cost_unit=data["costUnit"],
            temperature_unit=data["temperatureUnit"],
            series=series_points,
        )

    @property
    def total_energy_consumption(self) -> float:
        """Get total energy consumption across all data points."""
        return sum(point.total_energy for point in self.series)

    @property
    def total_cost(self) -> float:
        """Get total cost across all data points."""
        return sum(point.total_cost for point in self.series)

    @property
    def latest_data_point(self) -> TimeSeriesDataPoint | None:
        """Get the latest data point with energy data."""
        for point in reversed(self.series):
            if point.energy and any(e.value > 0 for e in point.energy):
                return point
        return None


@dataclass
class ConsumptionData:
    """Legacy model for backward compatibility."""

    date_time: datetime
    value: float
    cost: float | None = None
    unit: str = "kWh"

    @classmethod
    def from_time_series(cls, time_series: TimeSeries) -> list[ConsumptionData]:
        """Create consumption data list from time series."""
        consumption_data = []

        for point in time_series.series:
            if point.energy and any(e.value > 0 for e in point.energy):
                consumption_data.append(
                    cls(
                        date_time=point.at_utc,
                        value=point.total_energy,
                        cost=point.total_cost if point.cost else None,
                        unit=time_series.measurement_unit,
                    )
                )

        return consumption_data

    @classmethod
    def from_api_response(cls, data: dict[str, Any]) -> ConsumptionData:
        """Create instance from legacy API response data."""
        return cls(
            date_time=datetime.fromisoformat(data["dateTime"]),
            value=float(data["value"]),
            cost=float(data.get("cost", 0)) if data.get("cost") is not None else None,
            unit=data.get("unit", "kWh"),
        )


@dataclass
class CustomerDetails:
    """Represents customer details."""

    customer_id: str
    postal_address: str
    post_office: str
    name: str | None = None

    @classmethod
    def from_api_response(cls, data: dict[str, Any]) -> CustomerDetails:
        """Create instance from API response data."""
        # Handle session endpoint format
        if "user" in data:
            user_data = data["user"]
            return cls(
                customer_id=user_data["customerId"],
                postal_address=user_data.get("postalAddress", ""),
                post_office=user_data.get("postOffice", ""),
                name=user_data.get("name"),
            )

        # Handle legacy/direct format
        return cls(
            customer_id=data["customerId"],
            postal_address=data["postalAddress"],
            post_office=data["postOffice"],
            name=data.get("name"),
        )


@dataclass
class MeteringPoint:
    """Represents a metering point."""

    metering_point_no: str
    address: str | None = None

    @classmethod
    def from_api_response(cls, data: dict[str, Any]) -> MeteringPoint:
        """Create instance from API response data."""
        return cls(
            metering_point_no=data["meteringPointNo"],
            address=data.get("address"),
        )


@dataclass
class AuthTokens:
    """Represents OAuth2 authentication tokens."""

    access_token: str
    refresh_token: str
    id_token: str
    expires_in: int
    token_type: str = "Bearer"

    @classmethod
    def from_api_response(cls, data: dict[str, Any]) -> AuthTokens:
        """Create instance from API response data."""
        return cls(
            access_token=data["access_token"],
            refresh_token=data["refresh_token"],
            id_token=data["id_token"],
            expires_in=int(data["expires_in"]),
            token_type=data.get("token_type", "Bearer"),
        )
