"""Tests for the Moj Elektro config flow."""

from __future__ import annotations

import pytest
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.mojelektro.const import (
    API_BASE_URL,
    CONF_METER_ID,
    CONF_TOKEN,
    DOMAIN,
)

LOCATION_ID = "0123456789"
MERILNO_MESTO_URL = f"{API_BASE_URL}/merilno-mesto/{LOCATION_ID}"


async def _start(hass: HomeAssistant):
    return await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )


async def test_full_flow_creates_entry(hass: HomeAssistant, aioclient_mock) -> None:
    """A valid token lists points and creates an entry for the chosen one."""
    aioclient_mock.get(
        MERILNO_MESTO_URL,
        json={"merilneTocke": [{"gsrn": "111", "vrsta": "OMTO"}]},
    )

    result = await _start(hass)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_TOKEN: "tok", "location_id": LOCATION_ID},
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "meter"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_METER_ID: "111"}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"] == {CONF_TOKEN: "tok", CONF_METER_ID: "111"}
    assert result["result"].unique_id == "111"


@pytest.mark.parametrize(
    ("status", "expected"),
    [(401, "invalid_auth"), (500, "cannot_connect")],
)
async def test_flow_errors(
    hass: HomeAssistant, aioclient_mock, status: int, expected: str
) -> None:
    """Auth vs connection failures surface distinct errors."""
    aioclient_mock.get(MERILNO_MESTO_URL, status=status)

    result = await _start(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_TOKEN: "bad", "location_id": LOCATION_ID},
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": expected}
