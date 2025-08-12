from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import datetime as dt


def calculate_sprint_periods(
    start_date: dt.datetime,
    end_date: dt.datetime,
) -> list[tuple[dt.datetime, dt.datetime, str]]:
    """Generate 14-day sprint periods with labels."""
    periods = []
    current_start = start_date

    while current_start < end_date:
        current_end = min(current_start + timedelta(days=14), end_date)
        label = f"{current_start.strftime('%Y-%m-%d')}"
        periods.append((current_start, current_end, label))
        current_start = current_end

    return periods


def get_sprint_for_date(
    date: dt.datetime,
    sprint_periods: list[tuple[dt.datetime, dt.datetime, str]],
) -> str:
    """Return sprint label for a given date."""
    for start, end, label in sprint_periods:
        if start <= date <= end:
            return label
    return "Unknown"
