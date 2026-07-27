"""Sensor platform for the Moj Elektro integration."""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import UnitOfEnergy
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import MojElektroConfigEntry
from .coordinator import MojElektroDataUpdateCoordinator
from .entity import MojElektroEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: MojElektroConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Moj Elektro sensors from a config entry."""
    coordinator = entry.runtime_data
    async_add_entities([MojElektroDailyConsumptionSensor(coordinator)])


class MojElektroDailyConsumptionSensor(MojElektroEntity, SensorEntity):
    """Consumption for the last completed day (kWh).

    The Energy Dashboard uses the imported long-term statistics
    (``mojelektro:<meter>_energy_consumption``); this sensor is a convenient
    at-a-glance / automation value for the most recent day.
    """

    _attr_translation_key = "daily_consumption"
    _attr_icon = "mdi:transmission-tower-import"
    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
    _attr_state_class = SensorStateClass.TOTAL

    def __init__(self, coordinator: MojElektroDataUpdateCoordinator) -> None:
        """Initialise the daily-consumption sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.meter_id}_daily_consumption"

    @property
    def _latest(self) -> dict[str, Any] | None:
        return self.coordinator.data.get("latest")

    @property
    def native_value(self) -> float | None:
        """Return the last completed day's consumption in kWh."""
        latest = self._latest
        return latest["consumption"] if latest else None

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Expose the reading date and cumulative register value."""
        latest = self._latest
        if not latest:
            return None
        return {
            "date": latest["date"],
            "cumulative_kwh": latest["cumulative"],
            "meter_id": self.coordinator.meter_id,
        }
