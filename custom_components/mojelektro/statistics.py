"""Long-term statistics import for the Energy Dashboard.

Moj Elektro delivers daily consumption with a ~24h delay. A normal sensor would
be timestamped at fetch time, misplacing yesterday's usage on today. Instead we
push external statistics keyed on the API's own reading timestamps, so the Energy
Dashboard shows each day's consumption on the correct day.

The meter's cumulative register is used as the statistics ``sum``: re-importing
overlapping days with the same cumulative values is idempotent and self-correcting.
"""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.recorder.models import StatisticData, StatisticMetaData
from homeassistant.components.recorder.statistics import async_add_external_statistics
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util

from .const import ENERGY_UNIT, STAT_SOURCE, statistic_id

_LOGGER = logging.getLogger(__name__)


def build_statistics(days: list[dict[str, Any]]) -> list[StatisticData]:
    """Build hour-aligned :class:`StatisticData` rows from daily readings.

    ``days`` is the coordinator's per-day list, each item holding an aware
    ``start`` datetime, the day's ``consumption`` and the ``cumulative`` register
    reading. Rows are aligned to the start of the hour (statistics requirement)
    and expressed in UTC.
    """
    rows: list[StatisticData] = []
    for day in days:
        start = dt_util.as_utc(day["start"]).replace(
            minute=0, second=0, microsecond=0
        )
        rows.append(
            StatisticData(
                start=start,
                state=day["consumption"],
                sum=day["cumulative"],
            )
        )
    return rows


async def async_import_daily_statistics(
    hass: HomeAssistant, meter_id: str, days: list[dict[str, Any]]
) -> None:
    """Push daily consumption into the Energy Dashboard as external statistics."""
    rows = build_statistics(days)
    if not rows:
        return

    metadata = StatisticMetaData(
        has_mean=False,
        has_sum=True,
        name=f"Moj Elektro {meter_id} consumption",
        source=STAT_SOURCE,
        statistic_id=statistic_id(meter_id),
        unit_of_measurement=ENERGY_UNIT,
    )
    async_add_external_statistics(hass, metadata, rows)
    _LOGGER.debug("Imported %d daily statistic rows for %s", len(rows), meter_id)
