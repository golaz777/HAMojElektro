"""Register the bundled Lovelace card with the Home Assistant frontend."""

from __future__ import annotations

import logging
from pathlib import Path

from homeassistant.components.frontend import add_extra_js_url
from homeassistant.components.http import StaticPathConfig
from homeassistant.core import HomeAssistant

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

FRONTEND_URL = "/moj_elektro/moj_elektro-cards.js"
_BUNDLE = Path(__file__).parent / "frontend" / "moj_elektro-cards.js"
_REGISTERED_KEY = f"{DOMAIN}_frontend_registered"


async def async_register_frontend(hass: HomeAssistant) -> None:
    """Serve the card bundle and add it as an extra JS module (once per hass).

    Best-effort: registering the dashboard card must never fail integration
    setup, so any problem (frontend/http not ready) is logged and swallowed.
    """
    if hass.data.get(_REGISTERED_KEY):
        return
    http = getattr(hass, "http", None)
    if http is None:
        return
    try:
        await http.async_register_static_paths(
            [StaticPathConfig(FRONTEND_URL, str(_BUNDLE), False)]
        )
        add_extra_js_url(hass, FRONTEND_URL)
    except Exception as err:  # noqa: BLE001 - card is optional, never break setup
        _LOGGER.debug("Could not register Moj Elektro frontend card: %s", err)
        return
    hass.data[_REGISTERED_KEY] = True
