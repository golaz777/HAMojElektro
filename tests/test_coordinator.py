"""Tests for the coordinator's cumulative-to-daily maths."""

from __future__ import annotations

from custom_components.moj_elektro.coordinator import (
    MojElektroDataUpdateCoordinator as C,
)

from .conftest import daily_readings


def test_compute_daily_diffs_consecutive_readings():
    """Per-day consumption is the difference between consecutive registers."""
    readings = daily_readings("2026-07-01", [100.0, 105.5, 108.0, 111.25])
    days = C._compute_daily(readings)

    assert len(days) == 3
    assert [d["consumption"] for d in days] == [5.5, 2.5, 3.25]
    # Each row is attributed to the day the energy was used (the earlier reading).
    assert [d["date"] for d in days] == ["2026-07-01", "2026-07-02", "2026-07-03"]
    # ``cumulative`` is the register value at the end of the day (later reading).
    assert [d["cumulative"] for d in days] == [105.5, 108.0, 111.25]


def test_compute_daily_sorts_and_skips_bad_rows():
    """Out-of-order readings are sorted; unparseable rows are dropped."""
    readings = daily_readings("2026-07-01", [100.0, 102.0, 107.0])
    readings.reverse()
    readings.append({"timestamp": None, "value": "x"})  # dropped
    readings.append({"timestamp": "2026-07-04T00:00:00+02:00", "value": None})  # dropped

    days = C._compute_daily(readings)
    assert [d["consumption"] for d in days] == [2.0, 5.0]


def test_compute_daily_empty():
    """No readings yields no days."""
    assert C._compute_daily([]) == []
