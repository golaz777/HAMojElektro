"""Tests for building Energy Dashboard statistics rows."""

from __future__ import annotations

from datetime import datetime

from custom_components.moj_elektro.const import statistic_id
from custom_components.moj_elektro.statistics import _hour_start, _running_rows


def test_statistic_id_is_slugified():
    """Meter ids with hyphens/uppercase become valid external statistic ids."""
    from homeassistant.components.recorder.statistics import valid_statistic_id

    sid = statistic_id("3-8110057")
    assert sid == "moj_elektro:3_8110057_energy_consumption"
    assert valid_statistic_id(sid)


def _period(iso: str, value: float) -> dict:
    return {"start": datetime.fromisoformat(iso), "value": value}


def test_running_rows_from_zero_hour_aligned_utc():
    """A fresh series starts at its own first value (no odometer spike), monotonic."""
    periods = [
        _period("2026-07-01T00:00:00+02:00", 5.5),
        _period("2026-07-02T00:00:00+02:00", 2.5),
    ]
    rows, running = _running_rows(periods, 0.0, None)

    assert len(rows) == 2
    # First point's sum is its own daily consumption, NOT a lifetime odometer.
    assert rows[0]["state"] == 5.5
    assert rows[0]["sum"] == 5.5
    # Running sum stays monotonic.
    assert rows[1]["state"] == 2.5
    assert rows[1]["sum"] == 8.0
    assert running == 8.0
    # 00:00 +02:00 -> 22:00 UTC previous day, minutes zeroed.
    assert rows[0]["start"].utcoffset().total_seconds() == 0
    assert rows[0]["start"].minute == 0 and rows[0]["start"].second == 0


def test_running_rows_continues_and_skips_stored():
    """Periods at/before the last stored one are skipped; sum continues from seed."""
    last_start = _hour_start(datetime.fromisoformat("2026-07-01T00:00:00+02:00"))
    periods = [
        _period("2026-07-01T00:00:00+02:00", 5.5),  # <= last_start -> skipped
        _period("2026-07-02T00:00:00+02:00", 2.5),
    ]
    rows, running = _running_rows(periods, 100.0, last_start)

    assert len(rows) == 1
    assert rows[0]["state"] == 2.5
    assert rows[0]["sum"] == 102.5
    assert running == 102.5


def test_running_rows_empty():
    rows, running = _running_rows([], 0.0, None)
    assert rows == []
    assert running == 0.0
