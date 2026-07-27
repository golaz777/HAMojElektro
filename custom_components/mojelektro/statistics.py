"""Long-term statistics import for the Energy Dashboard.

Moj Elektro delivers data with a ~24h delay. A normal sensor would be timestamped
at fetch time, misplacing yesterday's usage on today. Instead we push external
statistics keyed on the API's own reading timestamps, so the Energy Dashboard
shows each period on the correct day/hour.

Two flavours:

- **Register series** (import/export daily registers): the meter's cumulative
  register is used as the statistics ``sum``. Re-importing overlapping days with
  the same cumulative values is idempotent and self-correcting.
- **Computed series** (time-blocks, and 15-min energy aggregated to hourly): there
  is no register, so the running ``sum`` is seeded from the last stored statistic
  (:func:`get_last_statistics`) and continued, keeping sums monotonic and stable.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from homeassistant.components.recorder import get_instance
from homeassistant.components.recorder.models import StatisticData, StatisticMetaData
from homeassistant.components.recorder.statistics import (
    async_add_external_statistics,
    get_last_statistics,
)
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util

from .const import ENERGY_UNIT, STAT_SOURCE, statistic_id_for

_LOGGER = logging.getLogger(__name__)


def _hour_start(value: datetime) -> datetime:
    """Return ``value`` in UTC, aligned to the start of the hour."""
    return dt_util.as_utc(value).replace(minute=0, second=0, microsecond=0)


def build_statistics(days: list[dict[str, Any]]) -> list[StatisticData]:
    """Build hour-aligned register rows (``state`` + cumulative ``sum``)."""
    return [
        StatisticData(
            start=_hour_start(day["start"]),
            state=day["consumption"],
            sum=day["cumulative"],
        )
        for day in days
    ]


def _metadata(meter_id: str, key: str, name: str) -> StatisticMetaData:
    return StatisticMetaData(
        has_mean=False,
        has_sum=True,
        name=f"Moj Elektro {meter_id} {name}",
        source=STAT_SOURCE,
        statistic_id=statistic_id_for(meter_id, key),
        unit_of_measurement=ENERGY_UNIT,
    )


async def async_import_registers(
    hass: HomeAssistant,
    meter_id: str,
    key: str,
    days: list[dict[str, Any]],
    name: str | None = None,
) -> None:
    """Import a cumulative-register series (idempotent via the register sum)."""
    rows = build_statistics(days)
    if not rows:
        return
    metadata = _metadata(meter_id, key, name or key)
    async_add_external_statistics(hass, metadata, rows)
    _LOGGER.debug("Imported %d register rows for %s/%s", len(rows), meter_id, key)


async def async_import_computed(
    hass: HomeAssistant,
    meter_id: str,
    key: str,
    periods: list[dict[str, Any]],
    name: str | None = None,
) -> None:
    """Import a computed series, continuing the running sum from stored stats.

    ``periods`` is ``[{start, value}]``. Only periods after the last stored one
    are appended, so repeated refreshes of the trailing window do not double-count.
    """
    if not periods:
        return

    sid = statistic_id_for(meter_id, key)
    last = await get_instance(hass).async_add_executor_job(
        get_last_statistics, hass, 1, sid, True, {"start", "sum"}
    )
    running = 0.0
    last_start: datetime | None = None
    if last.get(sid):
        prev = last[sid][0]
        running = float(prev.get("sum") or 0.0)
        last_start = dt_util.utc_from_timestamp(prev["start"])

    rows: list[StatisticData] = []
    for period in periods:
        start = _hour_start(period["start"])
        if last_start is not None and start <= last_start:
            continue
        running += period["value"]
        rows.append(StatisticData(start=start, state=period["value"], sum=running))

    if rows:
        metadata = _metadata(meter_id, key, name or key)
        async_add_external_statistics(hass, metadata, rows)
        _LOGGER.debug("Imported %d computed rows for %s/%s", len(rows), meter_id, key)
