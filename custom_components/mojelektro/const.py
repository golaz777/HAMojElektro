"""Constants for the Moj Elektro integration."""

from __future__ import annotations

from typing import Final

from homeassistant.util import slugify

DOMAIN: Final = "mojelektro"

# Moj Elektro REST API (Informatika d.o.o.). Production environment.
API_BASE_URL: Final = "https://api.informatika.si/mojelektro/v1"

# Endpoint paths (relative to API_BASE_URL).
EP_MERILNO_MESTO: Final = "/merilno-mesto/{meter_id}"  # account metering points
EP_MERILNA_TOCKA: Final = "/merilna-tocka/{gsrn}"  # metering-point detail
EP_METER_READINGS: Final = "/meter-readings"  # ?usagePoint=&startTime=&endTime=&option=

# ReadingType for the daily cumulative active-energy register (A+, consumption).
# Values returned are cumulative meter register readings; the per-day consumption
# is the difference between two consecutive daily readings.
READINGTYPE_DAILY: Final = "32.0.4.1.1.2.12.0.0.0.0.0.0.0.0.3.72.0"

# Config entry data keys.
CONF_TOKEN: Final = "token"
CONF_METER_ID: Final = "meter_id"

# Options keys.
CONF_SCAN_INTERVAL_HOURS: Final = "scan_interval_hours"
DEFAULT_SCAN_INTERVAL_HOURS: Final = 12
MIN_SCAN_INTERVAL_HOURS: Final = 4
MAX_SCAN_INTERVAL_HOURS: Final = 24

# How far back to fetch on each refresh (days). One extra day is needed as the
# anchor for the first day's difference.
HISTORY_DAYS: Final = 35

# Long-term statistics live under the integration's own source (external stats).
STAT_SOURCE: Final = DOMAIN
ENERGY_UNIT: Final = "kWh"


def statistic_id(meter_id: str) -> str:
    """External statistic id for a metering point (``mojelektro:<meter>_...``).

    HA requires external statistic ids to match ``[a-z0-9_]`` with no leading/
    trailing or doubled underscores, so the metering-point id (which may contain
    hyphens/uppercase, e.g. ``3-8110057``) is slugified first.
    """
    return f"{DOMAIN}:{slugify(meter_id)}_energy_consumption"
