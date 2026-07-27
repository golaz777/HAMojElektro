"""Data update coordinator for the Moj Elektro integration."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from . import statistics as stats
from . import tariff
from .api import MojElektroApiClient, MojElektroApiError
from .const import (
    ALL_FEATURES,
    CONF_FEATURES,
    CONF_METER_ID,
    CONF_SCAN_INTERVAL_HOURS,
    DEFAULT_SCAN_INTERVAL_HOURS,
    DOMAIN,
    FEATURE_BLOCKS,
    FEATURE_HELPERS,
    FEATURE_INTERVALS,
    HISTORY_DAYS,
    MEASUREMENTS,
    NUM_BLOCKS,
    READINGTYPE_15MIN_A_PLUS,
    READINGTYPE_15MIN_POWER_PLUS,
    Measurement,
)

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
    """Fetch meter readings and derive per-day / per-block consumption."""

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

    @property
    def features(self) -> list[str]:
        """Enabled feature groups (defaults to all)."""
        return self.entry.options.get(CONF_FEATURES, ALL_FEATURES)

    def _enabled_measurements(self) -> list[Measurement]:
        """Measurements whose feature group is enabled (or always-on)."""
        feats = self.features
        return [m for m in MEASUREMENTS if m.feature is None or m.feature in feats]

    def _reading_types(self) -> list[str]:
        """Distinct reading types to request for the enabled features."""
        types = {m.reading_type for m in self._enabled_measurements()}
        if FEATURE_BLOCKS in self.features:
            types.add(READINGTYPE_15MIN_A_PLUS)
        if FEATURE_HELPERS in self.features:
            types.add(READINGTYPE_15MIN_POWER_PLUS)
        return list(types)

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch the trailing window and compute all derived series."""
        today = dt_util.now().date()
        start = (today - timedelta(days=HISTORY_DAYS)).strftime("%Y-%m-%d")
        end = today.strftime("%Y-%m-%d")

        try:
            readings = await self.client.async_get_meter_readings(
                self.meter_id, start, end, self._reading_types()
            )
        except MojElektroApiError as err:
            raise UpdateFailed(str(err)) from err

        data: dict[str, Any] = {"registers": {}}

        # Daily cumulative registers -> per-day consumption + statistics.
        for meas in self._enabled_measurements():
            if meas.period != "daily":
                continue
            days = self._compute_daily(readings.get(meas.reading_type, []))
            data["registers"][meas.key] = {
                "days": days,
                "latest": days[-1] if days else None,
            }
            if meas.statistic and days:
                await stats.async_import_registers(
                    self.hass, self.meter_id, meas.key, days
                )

        # 15-minute interval energy -> hourly statistics (computed sums).
        if FEATURE_INTERVALS in self.features:
            for meas in self._enabled_measurements():
                if meas.period != "15min" or not meas.statistic:
                    continue
                hourly = self._hourly_from_intervals(
                    readings.get(meas.reading_type, [])
                )
                if hourly:
                    await stats.async_import_computed(
                        self.hass, self.meter_id, meas.key, hourly
                    )

        # Network time-blocks (blok 1-5), computed from 15-min A+.
        if FEATURE_BLOCKS in self.features:
            block_days, block_latest = self._blocks_by_day(
                readings.get(READINGTYPE_15MIN_A_PLUS, [])
            )
            data["blocks"] = {"latest": block_latest}
            for block, periods in block_days.items():
                if periods:
                    await stats.async_import_computed(
                        self.hass, self.meter_id, f"blok_{block}", periods
                    )

        # Helper values (no statistics).
        if FEATURE_HELPERS in self.features:
            data["monthly_peak_power"] = self._monthly_peak(
                readings.get(READINGTYPE_15MIN_POWER_PLUS, [])
            )
            data["current_block"] = tariff.current_block(dt_util.now())
            data["agreed_power"] = await self._async_agreed_power()

        return data

    # -- daily registers ----------------------------------------------------

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

    # -- 15-minute intervals ------------------------------------------------

    @staticmethod
    def _interval_points(readings: list[dict[str, Any]]) -> list[tuple[datetime, float]]:
        """Parse interval readings into sorted (local interval-start, value) pairs.

        API interval readings are timestamped at the interval *end*; the energy
        belongs to the 15 minutes before it, so the start is ``timestamp - 15m``.
        """
        points: list[tuple[datetime, float]] = []
        for reading in readings:
            ts = _parse_dt(reading.get("timestamp"))
            value = _to_float(reading.get("value"))
            if ts is not None and value is not None:
                start = dt_util.as_local(ts) - timedelta(minutes=15)
                points.append((start, value))
        points.sort(key=lambda p: p[0])
        return points

    @classmethod
    def _hourly_from_intervals(
        cls, readings: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Aggregate 15-minute energy into hourly buckets (statistics resolution)."""
        buckets: dict[datetime, float] = {}
        for start, value in cls._interval_points(readings):
            hour = start.replace(minute=0, second=0, microsecond=0)
            buckets[hour] = buckets.get(hour, 0.0) + value
        return [
            {"start": hour, "value": round(total, 3)}
            for hour, total in sorted(buckets.items())
        ]

    # -- time blocks --------------------------------------------------------

    @classmethod
    def _blocks_by_day(
        cls, readings: list[dict[str, Any]]
    ) -> tuple[dict[int, list[dict[str, Any]]], dict[int, float | None]]:
        """Sum 15-minute A+ energy into (day, block) buckets.

        Returns ``({block: [{start(day), consumption}]}, {block: latest_value})``.
        """
        sums: dict[tuple[Any, int], float] = {}
        for start, value in cls._interval_points(readings):
            block = tariff.block_for(start)
            if block == 0:
                continue
            day = start.replace(hour=0, minute=0, second=0, microsecond=0)
            sums[(day, block)] = sums.get((day, block), 0.0) + value

        by_block: dict[int, list[dict[str, Any]]] = {
            b: [] for b in range(1, NUM_BLOCKS + 1)
        }
        for (day, block), total in sorted(sums.items(), key=lambda kv: kv[0][0]):
            by_block[block].append({"start": day, "value": round(total, 3)})

        latest: dict[int, float | None] = {}
        for block, periods in by_block.items():
            latest[block] = periods[-1]["value"] if periods else None
        return by_block, latest

    # -- helper values ------------------------------------------------------

    @classmethod
    def _monthly_peak(cls, readings: list[dict[str, Any]]) -> float | None:
        """Return the highest 15-minute power (kW) in the current month."""
        now = dt_util.now()
        peak: float | None = None
        for start, value in cls._interval_points(readings):
            if start.year == now.year and start.month == now.month:
                peak = value if peak is None else max(peak, value)
        return None if peak is None else round(peak, 3)

    async def _async_agreed_power(self) -> dict[int, float | None]:
        """Return contracted power (kW) per block from the OMTO metering point.

        Best-effort: a lookup failure logs and returns an empty mapping rather
        than failing the whole refresh.
        """
        result: dict[int, float | None] = {}
        try:
            points = await self.client.async_get_metering_points(self.meter_id)
            gsrn = next(
                (p.get("gsrn") for p in points if p.get("vrsta") == "OMTO"), None
            )
            if not gsrn:
                return result
            detail = await self.client.async_get_metering_point_detail(gsrn)
        except MojElektroApiError as err:
            _LOGGER.debug("Agreed-power lookup failed: %s", err)
            return result

        now = dt_util.now().replace(tzinfo=None)
        for moc in detail.get("dogovorjeneMoci") or []:
            if not moc.get("veljavnost"):
                continue
            od = _parse_dt(moc.get("datumOd"))
            do = _parse_dt(moc.get("datumDo"))
            od = od.replace(tzinfo=None) if od else None
            do = do.replace(tzinfo=None) if do else None
            if od and do and od <= now <= do:
                for b in range(1, NUM_BLOCKS + 1):
                    result[b] = _to_float(moc.get(f"casovniBlok{b}"))
                break
        return result
