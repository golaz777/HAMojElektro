"""Tests for building Energy Dashboard statistics rows."""

from __future__ import annotations

from datetime import datetime

from custom_components.moj_elektro.const import statistic_id
from custom_components.moj_elektro.statistics import build_statistics


def test_statistic_id_is_slugified():
    """Meter ids with hyphens/uppercase become valid external statistic ids."""
    from homeassistant.components.recorder.statistics import valid_statistic_id

    sid = statistic_id("3-8110057")
    assert sid == "moj_elektro:3_8110057_energy_consumption"
    assert valid_statistic_id(sid)


def _day(iso: str, consumption: float, cumulative: float) -> dict:
    return {
        "start": datetime.fromisoformat(iso),
        "consumption": consumption,
        "cumulative": cumulative,
    }


def test_build_statistics_hour_aligned_utc():
    """Rows are hour-aligned, in UTC, carrying state and cumulative sum."""
    days = [
        _day("2026-07-01T00:00:00+02:00", 5.5, 105.5),
        _day("2026-07-02T00:00:00+02:00", 2.5, 108.0),
    ]
    rows = build_statistics(days)

    assert len(rows) == 2
    first = rows[0]
    assert first["state"] == 5.5
    assert first["sum"] == 105.5
    # 00:00 +02:00 -> 22:00 UTC previous day, minutes zeroed.
    assert first["start"].utcoffset().total_seconds() == 0
    assert first["start"].minute == 0 and first["start"].second == 0


def test_build_statistics_empty():
    assert build_statistics([]) == []
