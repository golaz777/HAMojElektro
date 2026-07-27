"""Constants for the Moj Elektro integration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from homeassistant.util import slugify

DOMAIN: Final = "moj_elektro"

# Moj Elektro REST API (Informatika d.o.o.). Production environment.
API_BASE_URL: Final = "https://api.informatika.si/mojelektro/v1"

# Endpoint paths (relative to API_BASE_URL).
EP_MERILNO_MESTO: Final = "/merilno-mesto/{meter_id}"  # account metering points
EP_MERILNA_TOCKA: Final = "/merilna-tocka/{gsrn}"  # metering-point detail
EP_METER_READINGS: Final = "/meter-readings"  # ?usagePoint=&startTime=&endTime=&option=

# ReadingType for the daily cumulative active-energy register (A+, total, T0).
# Kept for back-compat; the primary Energy-Dashboard statistic derives from it.
READINGTYPE_DAILY: Final = "32.0.4.1.1.2.12.0.0.0.0.0.0.0.0.3.72.0"

# Config entry data keys.
CONF_TOKEN: Final = "token"
CONF_METER_ID: Final = "meter_id"

# Options keys.
CONF_SCAN_INTERVAL_HOURS: Final = "scan_interval_hours"
CONF_FEATURES: Final = "features"
DEFAULT_SCAN_INTERVAL_HOURS: Final = 12
MIN_SCAN_INTERVAL_HOURS: Final = 4
MAX_SCAN_INTERVAL_HOURS: Final = 24

# Feature groups the user can toggle in options.
FEATURE_EXPORT: Final = "export"  # A- production registers
FEATURE_TARIFF_SPLIT: Final = "tariff_split"  # VT/MT (T1/T2) daily split
FEATURE_BLOCKS: Final = "blocks"  # 5 network time-blocks (daily kWh)
FEATURE_INTERVALS: Final = "intervals"  # 15-min A+/A- -> hourly statistics
FEATURE_HELPERS: Final = "helpers"  # current block, agreed power, monthly peak
ALL_FEATURES: Final = [
    FEATURE_EXPORT,
    FEATURE_TARIFF_SPLIT,
    FEATURE_BLOCKS,
    FEATURE_INTERVALS,
    FEATURE_HELPERS,
]

# How far back to fetch on each refresh (days). One extra day is needed as the
# anchor for the first day's difference.
HISTORY_DAYS: Final = 35

STAT_SOURCE: Final = DOMAIN
ENERGY_UNIT: Final = "kWh"
POWER_UNIT: Final = "kW"

# Number of Slovenian network-tariff time blocks.
NUM_BLOCKS: Final = 5


@dataclass(frozen=True, kw_only=True)
class Measurement:
    """A single meter reading type mapped to a Home Assistant sensor/statistic.

    ``period`` is ``"daily"`` for cumulative registers (STANJE) or ``"15min"``
    for interval quantities (KOLICINA). ``key`` is used for the entity unique id
    and the external statistic id suffix. ``statistic`` marks series that should
    be imported into long-term statistics (Energy Dashboard).
    """

    key: str
    reading_type: str
    period: str
    name: str
    unit: str
    device_class: str  # "energy" | "power"
    feature: str | None  # None => always on
    statistic: bool = True


# Active-energy daily cumulative registers (kWh). A+ = import, A- = export.
_A_PLUS_T0 = READINGTYPE_DAILY
MEASUREMENTS: Final[tuple[Measurement, ...]] = (
    Measurement(
        key="daily_consumption",  # unchanged unique id from v0.1.x
        reading_type=_A_PLUS_T0,
        period="daily",
        name="Daily consumption",
        unit=ENERGY_UNIT,
        device_class="energy",
        feature=None,
    ),
    Measurement(
        key="daily_consumption_peak",
        reading_type="32.0.4.1.1.2.12.0.0.0.0.1.0.0.0.3.72.0",
        period="daily",
        name="Daily consumption peak",
        unit=ENERGY_UNIT,
        device_class="energy",
        feature=FEATURE_TARIFF_SPLIT,
    ),
    Measurement(
        key="daily_consumption_offpeak",
        reading_type="32.0.4.1.1.2.12.0.0.0.0.2.0.0.0.3.72.0",
        period="daily",
        name="Daily consumption off-peak",
        unit=ENERGY_UNIT,
        device_class="energy",
        feature=FEATURE_TARIFF_SPLIT,
    ),
    Measurement(
        key="daily_export",
        reading_type="32.0.4.1.19.2.12.0.0.0.0.0.0.0.0.3.72.0",
        period="daily",
        name="Daily export",
        unit=ENERGY_UNIT,
        device_class="energy",
        feature=FEATURE_EXPORT,
    ),
    Measurement(
        key="daily_export_peak",
        reading_type="32.0.4.1.19.2.12.0.0.0.0.1.0.0.0.3.72.0",
        period="daily",
        name="Daily export peak",
        unit=ENERGY_UNIT,
        device_class="energy",
        feature=FEATURE_EXPORT,
    ),
    Measurement(
        key="daily_export_offpeak",
        reading_type="32.0.4.1.19.2.12.0.0.0.0.2.0.0.0.3.72.0",
        period="daily",
        name="Daily export off-peak",
        unit=ENERGY_UNIT,
        device_class="energy",
        feature=FEATURE_EXPORT,
    ),
    # 15-minute interval energy (kWh per interval) -> hourly statistics.
    Measurement(
        key="import_15min",
        reading_type="32.0.2.4.1.2.12.0.0.0.0.0.0.0.0.3.72.0",
        period="15min",
        name="Import (15 min)",
        unit=ENERGY_UNIT,
        device_class="energy",
        feature=FEATURE_INTERVALS,
    ),
    Measurement(
        key="export_15min",
        reading_type="32.0.2.4.19.2.12.0.0.0.0.0.0.0.0.3.72.0",
        period="15min",
        name="Export (15 min)",
        unit=ENERGY_UNIT,
        device_class="energy",
        feature=FEATURE_INTERVALS,
    ),
)

# 15-minute active-power reading types (kW), used for the monthly peak and for
# bucketing energy into blocks. Not exposed as their own statistics.
READINGTYPE_15MIN_A_PLUS: Final = "32.0.2.4.1.2.12.0.0.0.0.0.0.0.0.3.72.0"
READINGTYPE_15MIN_POWER_PLUS: Final = "32.0.2.4.1.2.37.0.0.0.0.0.0.0.0.3.38.0"


def statistic_id(meter_id: str) -> str:
    """Back-compat statistic id for the primary daily consumption (A+ total).

    Unchanged since v0.1.1 so existing Energy Dashboard configuration keeps
    working. Equivalent to ``statistic_id_for(meter_id, "energy_consumption")``.
    """
    return f"{DOMAIN}:{slugify(meter_id)}_energy_consumption"


def statistic_id_for(meter_id: str, key: str) -> str:
    """External statistic id for a measurement ``key`` on a metering point.

    HA requires external statistic ids to match ``[a-z0-9_]`` with no leading/
    trailing or doubled underscores, so both parts are slugified.
    """
    if key == "daily_consumption":
        return statistic_id(meter_id)
    return f"{DOMAIN}:{slugify(meter_id)}_{slugify(key)}"
