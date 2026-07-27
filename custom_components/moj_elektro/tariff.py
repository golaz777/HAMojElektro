"""Slovenian network-tariff time-block schedule (blok 1-5).

Pure, dependency-free functions (no Home Assistant imports) so they are easy to
unit test. The schedule and holiday handling are ported from
``frlequ/homeassistant-mojelektro``.

The active block depends on the season (high season = Nov-Feb), whether the day
is a weekend/holiday, and the hour of day.
"""

from __future__ import annotations

from datetime import date, datetime

HIGH_SEASON_MONTHS = frozenset({11, 12, 1, 2})

# (hour_start, hour_end, high_season_pair, low_season_pair).
# Each pair is (workday_or_weekend_block_a, block_b); selection below.
_SCHEDULE: tuple[tuple[int, int, tuple[int, int], tuple[int, int]], ...] = (
    (0, 5, (3, 4), (5, 4)),
    (6, 6, (2, 3), (4, 3)),
    (7, 13, (1, 2), (3, 2)),
    (14, 15, (2, 3), (4, 3)),
    (16, 19, (1, 2), (3, 2)),
    (20, 21, (2, 3), (4, 3)),
    (22, 23, (3, 4), (5, 4)),
)

# Fixed Slovenian public holidays as (month, day).
_FIXED_HOLIDAYS = frozenset(
    {
        (1, 1),
        (1, 2),
        (2, 8),
        (4, 27),
        (5, 1),
        (5, 2),
        (6, 25),
        (8, 15),
        (10, 31),
        (11, 1),
        (12, 25),
        (12, 26),
    }
)


def _easter_sunday(year: int) -> date:
    """Return Easter Sunday for ``year`` (anonymous Gregorian algorithm)."""
    a = year % 19
    b = year // 100
    c = year % 100
    d = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i = c // 4
    k = c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month = (h + l - 7 * m + 114) // 31
    day = ((h + l - 7 * m + 114) % 31) + 1
    return date(year, month, day)


def is_weekend_or_holiday(when: datetime | date) -> bool:
    """True if ``when`` is a Saturday/Sunday or a Slovenian public holiday.

    Easter Saturday and Easter Monday are included for the given year.
    """
    d = when.date() if isinstance(when, datetime) else when
    if d.weekday() >= 5:  # Saturday=5, Sunday=6
        return True
    easter = _easter_sunday(d.year)
    from datetime import timedelta

    easter_dates = {
        (easter - timedelta(days=1)).timetuple()[1:3],  # Easter Saturday
        (easter + timedelta(days=1)).timetuple()[1:3],  # Easter Monday
    }
    return (d.month, d.day) in _FIXED_HOLIDAYS or (d.month, d.day) in easter_dates


def block_for(when: datetime) -> int:
    """Return the active network-tariff block (1-5) for ``when``.

    ``when`` is treated as the instant to classify; when bucketing 15-minute
    interval readings (timestamped at the interval *end*), pass the interval
    start (end minus 15 minutes).
    """
    month = when.month
    hour = when.hour
    is_high = month in HIGH_SEASON_MONTHS
    weekend = is_weekend_or_holiday(when)

    for start, end, high_pair, low_pair in _SCHEDULE:
        if start <= hour <= end:
            if is_high and not weekend:
                return high_pair[0]
            if not is_high and weekend:
                return low_pair[0]
            return high_pair[1] if is_high else low_pair[1]
    return 0


def current_block(now: datetime) -> int:
    """Return the block active right now."""
    return block_for(now)
