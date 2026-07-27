"""The Moj Elektro integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import MojElektroApiClient
from .const import CONF_TOKEN
from .coordinator import MojElektroDataUpdateCoordinator
from .frontend_registration import async_register_frontend

PLATFORMS: list[Platform] = [Platform.SENSOR]

type MojElektroConfigEntry = ConfigEntry[MojElektroDataUpdateCoordinator]


async def async_setup_entry(
    hass: HomeAssistant, entry: MojElektroConfigEntry
) -> bool:
    """Set up Moj Elektro from a config entry."""
    await async_register_frontend(hass)
    session = async_get_clientsession(hass)
    client = MojElektroApiClient(session, entry.data[CONF_TOKEN])
    coordinator = MojElektroDataUpdateCoordinator(hass, entry, client)

    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    return True


async def async_unload_entry(
    hass: HomeAssistant, entry: MojElektroConfigEntry
) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def _async_update_listener(
    hass: HomeAssistant, entry: MojElektroConfigEntry
) -> None:
    """Reload the entry when options (scan interval) change."""
    await hass.config_entries.async_reload(entry.entry_id)
