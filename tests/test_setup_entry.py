"""End-to-end setup test with a mocked API and a real recorder."""

from __future__ import annotations

from datetime import datetime, timedelta

from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.moj_elektro.const import (
    ALL_FEATURES,
    API_BASE_URL,
    CONF_FEATURES,
    CONF_METER_ID,
    CONF_SCAN_INTERVAL_HOURS,
    CONF_TOKEN,
    DOMAIN,
    READINGTYPE_15MIN_A_PLUS,
    READINGTYPE_15MIN_POWER_PLUS,
    READINGTYPE_DAILY,
)

METER_ID = "3-8110057"


def _daily_block():
    base = datetime.fromisoformat("2026-07-01T00:00:00+02:00")
    readings = [
        {"timestamp": (base + timedelta(days=i)).isoformat(), "value": str(100.0 + 5 * i)}
        for i in range(3)
    ]
    return {"readingType": READINGTYPE_DAILY, "intervalReadings": readings}


def _interval_block(reading_type: str, value: float):
    base = datetime.fromisoformat("2026-07-02T10:00:00+02:00")
    readings = [
        {"timestamp": (base + timedelta(minutes=15 * (i + 1))).isoformat(), "value": str(value)}
        for i in range(4)
    ]
    return {"readingType": reading_type, "intervalReadings": readings}


async def test_setup_entry_populates_sensor(
    recorder_mock, hass: HomeAssistant, aioclient_mock
) -> None:
    """A full refresh sets up the entry and populates the daily sensor."""
    aioclient_mock.get(
        f"{API_BASE_URL}/meter-readings",
        json={
            "intervalBlocks": [
                _daily_block(),
                _interval_block(READINGTYPE_15MIN_A_PLUS, 0.5),
                _interval_block(READINGTYPE_15MIN_POWER_PLUS, 4.2),
            ]
        },
    )
    aioclient_mock.get(
        f"{API_BASE_URL}/merilno-mesto/{METER_ID}",
        json={"merilneTocke": [{"gsrn": "111", "vrsta": "OMTO"}]},
    )
    aioclient_mock.get(
        f"{API_BASE_URL}/merilna-tocka/111",
        json={
            "dogovorjeneMoci": [
                {
                    "veljavnost": True,
                    "datumOd": "2020-01-01T00:00:00+01:00",
                    "datumDo": "2035-01-01T00:00:00+01:00",
                    "casovniBlok1": "7.0",
                    "casovniBlok2": "7.0",
                    "casovniBlok3": "10.0",
                    "casovniBlok4": "10.0",
                    "casovniBlok5": "3.0",
                }
            ]
        },
    )

    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_TOKEN: "tok", CONF_METER_ID: METER_ID},
        options={CONF_SCAN_INTERVAL_HOURS: 12, CONF_FEATURES: ALL_FEATURES},
        unique_id=METER_ID,
    )
    entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    state = hass.states.get("sensor.moj_elektro_daily_consumption")
    assert state is not None
    assert float(state.state) == 5.0  # 110 - 105 (last two daily registers)

    peak = hass.states.get("sensor.moj_elektro_monthly_peak_power")
    assert peak is not None
