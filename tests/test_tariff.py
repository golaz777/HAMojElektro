"""Tests for the Slovenian time-block schedule."""

from __future__ import annotations

from datetime import datetime

from custom_components.mojelektro.tariff import (
    block_for,
    is_weekend_or_holiday,
)


def _dt(iso: str) -> datetime:
    return datetime.fromisoformat(iso)


def test_high_season_workday_blocks():
    """High season (Jan) workday: block 1 in the peak hours, 3 overnight."""
    # 2026-01-05 is a Monday.
    assert block_for(_dt("2026-01-05T10:00:00")) == 1  # 07-13 range
    assert block_for(_dt("2026-01-05T02:00:00")) == 3  # 00-05 range
    assert block_for(_dt("2026-01-05T21:00:00")) == 2  # 20-21 range


def test_low_season_workday_blocks():
    """Low season (July) workday is one block cheaper than high season."""
    # 2026-07-06 is a Monday.
    assert block_for(_dt("2026-07-06T10:00:00")) == 2
    assert block_for(_dt("2026-07-06T02:00:00")) == 4


def test_weekend_shifts_block():
    """Weekends are cheaper than the same hour on a workday."""
    # 2026-01-10 is a Saturday (high season).
    assert block_for(_dt("2026-01-10T10:00:00")) == 2
    # 2026-07-11 is a Saturday (low season).
    assert block_for(_dt("2026-07-11T10:00:00")) == 3


def test_holiday_counts_as_weekend():
    """A public holiday on a weekday is treated like a weekend."""
    # 2026-04-06 is Easter Monday (a Monday) -> weekend/holiday True.
    assert is_weekend_or_holiday(_dt("2026-04-06T10:00:00"))
    # New Year's Day 2026 (Thursday) is a fixed holiday.
    assert is_weekend_or_holiday(_dt("2026-01-01T10:00:00"))
    # A plain workday is not.
    assert not is_weekend_or_holiday(_dt("2026-07-06T10:00:00"))
