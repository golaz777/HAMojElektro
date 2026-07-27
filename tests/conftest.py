"""Shared pytest fixtures for the Moj Elektro tests."""

from __future__ import annotations

import pytest

pytest_plugins = ["pytest_homeassistant_custom_component"]


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable loading of the custom integration in all tests."""
    yield


def daily_readings(start_day: str, values: list[float]) -> list[dict]:
    """Build a list of cumulative-register readings, one per day.

    ``start_day`` is a ``YYYY-MM-DD`` date; each value is the cumulative register
    reading at 00:00 local of the corresponding day.
    """
    from datetime import datetime, timedelta

    base = datetime.fromisoformat(f"{start_day}T00:00:00+02:00")
    return [
        {
            "timestamp": (base + timedelta(days=i)).isoformat(),
            "value": str(v),
        }
        for i, v in enumerate(values)
    ]
