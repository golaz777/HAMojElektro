"""Tests for the coordinator's derived series (intervals, blocks, peak)."""

from __future__ import annotations

from datetime import datetime, timedelta

from custom_components.moj_elektro.coordinator import (
    MojElektroDataUpdateCoordinator as C,
)


def _intervals(day: str, start_hour: int, values: list[float]) -> list[dict]:
    """15-min readings timestamped at interval END (+02:00), one per value."""
    base = datetime.fromisoformat(f"{day}T{start_hour:02d}:00:00+02:00")
    return [
        {
            "timestamp": (base + timedelta(minutes=15 * (i + 1))).isoformat(),
            "value": str(v),
        }
        for i, v in enumerate(values)
    ]


def test_hourly_from_intervals_buckets_by_hour():
    """Eight 15-min readings roll up into two hourly buckets."""
    readings = _intervals("2026-07-06", 10, [1.0] * 8)
    hourly = C._hourly_from_intervals(readings)

    assert [row["value"] for row in hourly] == [4.0, 4.0]
    assert sum(row["value"] for row in hourly) == 8.0
    # Buckets are hour-aligned and one hour apart.
    assert (hourly[1]["start"] - hourly[0]["start"]) == timedelta(hours=1)
    assert hourly[0]["start"].minute == 0


def test_blocks_by_day_sum_matches_total():
    """Per-block daily sums add up to the day's total energy."""
    readings = _intervals("2026-07-06", 9, [0.5] * 12)  # 09:00–12:00, total 6.0
    _by_block, latest = C._blocks_by_day(readings)

    assert round(sum(v for v in latest.values() if v is not None), 3) == 6.0


def test_monthly_peak_is_max_in_current_month(freezer):
    """Monthly peak ignores other months and returns the max power."""
    freezer.move_to("2026-07-15 12:00:00")
    readings = _intervals("2026-07-10", 8, [2.0, 5.0, 3.0])
    readings += _intervals("2026-06-30", 8, [9.0])  # different month, excluded

    assert C._monthly_peak(readings) == 5.0


def test_monthly_peak_empty():
    assert C._monthly_peak([]) is None
