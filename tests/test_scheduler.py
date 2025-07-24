import datetime
from decimal import Decimal

import pytest

from lawn_smart.models import WateringEvent, WateringEvents, WeatherDay, Yard, Zone


@pytest.fixture
def simple_weather() -> list[WeatherDay]:
    """7 days of dry weather with constant ETo."""
    today = datetime.date.today()
    return [
        WeatherDay(
            date=today + datetime.timedelta(days=day),
            eto=Decimal("0.18"),
            forecast_rainfall=Decimal("0"),
        )
        for day in range(7)
    ]


@pytest.fixture
def clay_zone() -> Zone:
    """A zone with low infiltration, likely to need multiple cycles."""
    return Zone(
        name="Clay Lawn",
        vegetation_kc=Decimal("0.8"),
        precipitation_rate=Decimal("1.0"),
        soil_available_water=Decimal("1.2"),
        root_depth=Decimal("0.5"),
        allowed_depletion=Decimal("0.5"),
        efficiency=Decimal("0.7"),
        infiltration_rate=Decimal("0.25"),
        max_cycle_duration=Decimal("30"),
        soak_minutes=10,
    )


@pytest.fixture
def sandy_zone() -> Zone:
    """A zone with sandy soil, allowing for quick drainage."""
    return Zone(
        name="Sandy Lawn",
        vegetation_kc=Decimal("0.8"),
        precipitation_rate=Decimal("1.0"),
        soil_available_water=Decimal("1.2"),
        root_depth=Decimal("0.5"),
        allowed_depletion=Decimal("0.5"),
        efficiency=Decimal("0.7"),
        infiltration_rate=Decimal("1"),
        max_cycle_duration=Decimal("30"),
        soak_minutes=10,
    )


def test_generate_schedule_for_zone_creates_events(
    simple_weather: list[WeatherDay], clay_zone: Zone
) -> None:
    """Test that the schedule is created with multiple cycles for clay soil."""

    schedule = clay_zone.generate_schedule(simple_weather)

    assert isinstance(schedule, WateringEvents)

    assert len(schedule) >= 1


def test_cycles_do_not_exceed_infiltration(
    clay_zone: Zone, simple_weather: list[WeatherDay]
) -> None:
    """Test that cycles do not exceed the infiltration rate."""

    schedule = clay_zone.generate_schedule(simple_weather)

    max_depth = clay_zone.infiltration_rate * (clay_zone.max_cycle_duration / Decimal("60"))

    for event in schedule:
        for cycle in event.cycles:
            applied_depth = (cycle.duration_minutes / Decimal("60")) * clay_zone.precipitation_rate
            assert applied_depth <= max_depth


def test_generate_schedules_multiple_zones(
    simple_weather: list[WeatherDay], clay_zone: Zone, sandy_zone: Zone
) -> None:
    """Test that schedules can be generated for multiple zones."""

    yard = Yard.from_list([clay_zone, sandy_zone])
    schedules = yard.generate_schedules(simple_weather)

    assert set(schedules.keys()) == {clay_zone.name, sandy_zone.name}

    for events in schedules.values():
        assert all(isinstance(event, WateringEvent) for event in events)


def test_real_rainfall_reduces_or_skips_watering(
    simple_weather: list[WeatherDay], clay_zone: Zone
) -> None:
    """Test that real rainfall reduces or skips watering."""

    rainy_weather = simple_weather.copy()
    rainy_weather[2] = rainy_weather[2].model_copy(update={"forecast_rainfall": Decimal("1")})

    schedule = clay_zone.generate_schedule(rainy_weather)

    dry_schedule = clay_zone.generate_schedule(simple_weather)

    assert len(schedule) < len(dry_schedule)
