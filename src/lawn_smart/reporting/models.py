import datetime as dt
import logging
from decimal import Decimal
from typing import Self

from attrmagic import ClassBase

from lawn_smart.models import ZERO_DECIMAL, WateringEvent, WeatherDay, Zone

logging.basicConfig(level=logging.DEBUG)


class DailyMoistureReport(ClassBase):
    date: dt.date
    etc: Decimal
    forecast_rainfall: Decimal
    effective_rainfall: Decimal
    depletion_start: Decimal
    depletion_end: Decimal
    water_added_inches: Decimal
    watering_event: WateringEvent | None = None

    @classmethod
    def from_day_and_event(cls, day: WeatherDay, event: WateringEvent | None, zone: Zone) -> Self:
        date = day.date
        etc = day.eto * zone.vegetation_kc
        forecast_rainfall = day.forecast_rainfall
        effective_rainfall = forecast_rainfall * zone.efficiency

        depletion_start = etc - effective_rainfall

        water_added_inches = event.cycles.total_depth(zone) if event is not None else ZERO_DECIMAL

        depletion_end = depletion_start - water_added_inches

        return cls(
            date=date,
            etc=etc,
            forecast_rainfall=forecast_rainfall,
            effective_rainfall=effective_rainfall,
            depletion_start=depletion_start,
            depletion_end=depletion_end,
            water_added_inches=water_added_inches,
            watering_event=event,
        )


if __name__ == "__main__":
    # example usage
    from rich.console import Console
    from rich.table import Table

    console = Console()

    today = dt.date.today()
    console.log(f"[bold magenta]Generating daily moisture report for {today:%B %d, %Y}[/]")
    weather = [
        WeatherDay(
            date=today + dt.timedelta(days=i), eto=Decimal("0.18"), forecast_rainfall=ZERO_DECIMAL
        )
        for i in range(7)
    ]

    zone = Zone(
        name="Front Lawn",
        vegetation_kc=Decimal("0.8"),
        precipitation_rate=Decimal("1.0"),
        soil_available_water=Decimal("1.2"),
        root_depth=Decimal("0.5"),
        allowed_depletion=Decimal("0.5"),
        efficiency=Decimal("0.7"),
        infiltration_rate=Decimal("0.25"),
        max_cycle_duration=Decimal("30"),
        soak_minutes=30,
    )

    events = zone.generate_schedule(weather)
    reports: list[DailyMoistureReport] = []
    for day in weather:
        event = next((e for e in events if e.date == day.date), None)
        reports.append(DailyMoistureReport.from_day_and_event(day, event, zone))

    table = Table(title=f"{zone.name.title()} Daily Moisture Report")
    table.add_column("Date", justify="center")
    table.add_column("ETc (inches)", justify="right")
    table.add_column("Forecast Rainfall (inches)", justify="right")
    table.add_column("Effective Rainfall (inches)", justify="right")
    table.add_column("Depletion Start (inches)", justify="right")
    table.add_column("Depletion End (inches)", justify="right")
    table.add_column("Water Added (inches)", justify="right")
    table.add_column("Cycle Count", justify="center")

    for report in reports:
        table.add_row(
            str(report.date),
            f"{report.etc:.2f}",
            f"{report.forecast_rainfall:.2f}",
            f"{report.effective_rainfall:.2f}",
            f"{report.depletion_start:.2f}",
            f"{report.depletion_end:.2f}",
            f"{report.water_added_inches:.2f}",
            str(len(report.watering_event.cycles)) if report.watering_event is not None else "0",
            style="dim" if report.watering_event is None else "bold green",
        )

    console.print(table)
