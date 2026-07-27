"""Data update coordinator for the Moj Elektro integration."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .api import MojElektroApiClient, MojElektroApiError
from .const import (
    CONF_METER_ID,
    CONF_SCAN_INTERVAL_HOURS,
    DEFAULT_SCAN_INTERVAL_HOURS,
    DOMAIN,
    HISTORY_DAYS,
)
from .statistics import async_import_daily_statistics

_LOGGER = logging.getLogger(__name__)


def _parse_dt(value: str | None) -> datetime | None:
    """Parse an API ISO timestamp into an aware datetime."""
    if not value:
        return None
    return dt_util.parse_datetime(value)


def _to_float(value: Any) -> float | None:
    """Coerce an API value (often a string) to float, or ``None``."""
    try:
        return float(str(value).strip())
    except (TypeError, ValueError):
        return None


class MojElektroDataUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Fetch daily meter readings and derive per-day consumption."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        client: MojElektroApiClient,
    ) -> None:
        """Initialise the coordinator from a config entry."""
        self.entry = entry
        self.client = client
        self.meter_id: str = entry.data[CONF_METER_ID]
        hours = entry.options.get(
            CONF_SCAN_INTERVAL_HOURS, DEFAULT_SCAN_INTERVAL_HOURS
        )
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(hours=hours),
        )

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch the trailing window and compute daily consumption."""
        today = dt_util.now().date()
        start = (today - timedelta(days=HISTORY_DAYS)).strftime("%Y-%m-%d")
        end = today.strftime("%Y-%m-%d")

        try:
            readings = await self.client.async_get_daily_readings(
                self.meter_id, start, end
            )
        except MojElektroApiError as err:
            raise UpdateFailed(str(err)) from err

        days = self._compute_daily(readings)

        if days:
            await async_import_daily_statistics(self.hass, self.meter_id, days)

        return {"days": days, "latest": days[-1] if days else None}

    @staticmethod
    def _compute_daily(readings: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Turn cumulative register readings into per-day consumption rows.

        Each row: ``start`` (aware datetime of the day the energy was used),
        ``consumption`` (kWh for that day) and ``cumulative`` (register value at
        the end of the day, used as the statistics ``sum``).
        """
        points: list[tuple[datetime, float]] = []
        for reading in readings:
            ts = _parse_dt(reading.get("timestamp"))
            value = _to_float(reading.get("value"))
            if ts is not None and value is not None:
                points.append((ts, value))
        points.sort(key=lambda p: p[0])

        days: list[dict[str, Any]] = []
        for (prev_ts, prev_val), (_cur_ts, cur_val) in zip(points, points[1:]):
            consumption = round(cur_val - prev_val, 3)
            days.append(
                {
                    "start": prev_ts,
                    "date": prev_ts.date().isoformat(),
                    "consumption": consumption,
                    "cumulative": cur_val,
                }
            )
        return days
