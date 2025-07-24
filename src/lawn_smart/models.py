import datetime
import logging
from decimal import Decimal
from typing import Annotated, Self

from attrmagic import ClassBase, SimpleDict, SimpleListRoot
from pydantic import Field

logger = logging.getLogger(__name__)

MINS_IN_HOUR = Decimal("60")
ZERO_DECIMAL = Decimal("0")


class Zone(ClassBase):
    """Represents a zone in the lawn smart system."""

    name: str
    vegetation_kc: Annotated[
        Decimal, Field(gt=0, le=1, description="Crop coefficient for vegetation")
    ]
    precipitation_rate: Annotated[Decimal, Field(gt=0, description="Precipitation rate [in/hr]")]
    soil_available_water: Annotated[
        Decimal, Field(ge=0, description="Available water in the soil [inches/foot]")
    ]
    root_depth: Annotated[Decimal, Field(gt=0, description="Root depth [feet]")]
    allowed_depletion: Annotated[
        Decimal, Field(gt=0, le=1, description="Allowed depletion of available water in the soil")
    ]
    efficiency: Annotated[Decimal, Field(gt=0, le=1, description="Irrigation system efficiency")]
    infiltration_rate: Annotated[Decimal, Field(gt=0, description="Infiltration rate [in/hr]")]
    max_cycle_duration: Annotated[
        Decimal, Field(gt=0, description="Maximum cycle duration to avoid runoff [minutes]")
    ]
    soak_minutes: Annotated[int, Field(gt=0, description="Soak time between cycles [minutes]")]

    @property
    def total_available_water(self) -> Decimal:
        """Calculate total available water in the soil."""
        return self.soil_available_water * self.root_depth

    @property
    def max_depletion(self) -> Decimal:
        """Calculate maximum allowed depletion of available water."""
        return self.total_available_water * self.allowed_depletion

    def generate_schedule(self, weather: list["WeatherDay"]) -> "WateringEvents":
        """
        Generate a watering schedule for this zone based on weather data.

        Args:
            weather (list[WeatherDay]): List of weather data for the zone.

        Returns:
            list[WateringEvent]: A list of watering events for the zone.
        """

        depletion = Decimal("0")
        schedule: WateringEvents = WateringEvents.empty()

        cycle_duration_hr = self.max_cycle_duration / MINS_IN_HOUR

        for day in weather:
            etc = day.eto * self.vegetation_kc
            effective_rainfall = day.forecast_rainfall * self.efficiency
            depletion += etc - effective_rainfall
            depletion = max(depletion, ZERO_DECIMAL)

            if depletion >= self.max_depletion:
                cycles = WateringCycles.generate(
                    depletion=depletion,
                    zone=self,
                    cycle_duration_hr=cycle_duration_hr,
                )

                total_water_applied = cycles.total_depth(self)
                depletion -= total_water_applied

                schedule.append(
                    WateringEvent(
                        date=day.date,
                        cycles=cycles,
                        soak_minutes=self.soak_minutes if len(cycles) > 1 else None,
                    )
                )
                depletion = max(depletion, ZERO_DECIMAL)

        return schedule


class Yard(SimpleDict[str, Zone]):
    """A collection of zones in the lawn smart system."""

    @classmethod
    def from_list(cls, zones: list[Zone]) -> Self:
        """Create a Yard instance from a list of zones."""
        return cls(root={zone.name: zone for zone in zones})

    def add_zone(self, zone: Zone) -> None:
        """Add a zone to the yard."""
        self.root[zone.name] = zone

    def generate_schedules(self, weather: list["WeatherDay"]) -> dict[str, "WateringEvents"]:
        """
        Generate watering schedules for all zones in the yard based on weather data.

        Args:
            weather (list[WeatherDay]): List of weather data.

        Returns:
            dict[str, list[WateringEvent]]: A dictionary mapping zone names to their watering schedules.
        """
        return {zone.name: zone.generate_schedule(weather) for zone in self.root.values()}


class WeatherDay(ClassBase):
    """Represents a weather day in the lawn smart system."""

    date: datetime.date
    eto: Annotated[Decimal, Field(ge=0, description="Reference evapotranspiration [inches]")]
    forecast_rainfall: Annotated[Decimal, Field(ge=0, description="Forecast rainfall [inches]")]


class WateringCycle(ClassBase):
    """Represents a watering cycle for a zone."""

    duration_minutes: Annotated[
        Decimal, Field(ge=0, description="Duration of the watering cycle [minutes]")
    ]


class WateringCycles(SimpleListRoot[WateringCycle]):
    """A collection of watering cycles."""

    @property
    def total_duration(self) -> Decimal:
        """Calculate the total duration of all cycles in minutes."""
        simple_total = sum(cycle.duration_minutes for cycle in self)
        return Decimal("0") if not isinstance(simple_total, Decimal) else simple_total

    def total_depth(self, zone: Zone) -> Decimal:
        """Calculate the total depth of water applied in inches."""
        msg = f"Total duration for depth calculation: {self.total_duration} minutes"
        logger.debug(msg)
        return self.total_duration / MINS_IN_HOUR * zone.precipitation_rate * zone.efficiency

    @classmethod
    def generate(cls, depletion: Decimal, cycle_duration_hr: Decimal, zone: Zone) -> Self:
        water_needed_inches = depletion / zone.efficiency

        max_cycle_depth = zone.infiltration_rate * cycle_duration_hr

        cycles: list[WateringCycle] = []
        remaining = water_needed_inches

        while remaining > 0:
            cycle_depth = min(remaining, max_cycle_depth)

            cycle_duration_minutes = (cycle_depth / zone.precipitation_rate) * MINS_IN_HOUR
            cycles.append(WateringCycle(duration_minutes=round(cycle_duration_minutes, 1)))

            remaining -= cycle_depth

        return cls(root=cycles)


class WateringEvent(ClassBase):
    """Represents a watering event for a zone."""

    date: datetime.date
    cycles: WateringCycles
    soak_minutes: Annotated[
        int | None, Field(gt=0, description="Soak time between cycles [minutes]")
    ] = None


class WateringEvents(SimpleListRoot[WateringEvent]):
    """A collection of watering events."""
