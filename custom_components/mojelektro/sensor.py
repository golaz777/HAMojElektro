"""Sensor platform for the Moj Elektro integration."""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import EntityCategory, UnitOfEnergy, UnitOfPower
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import MojElektroConfigEntry
from .const import (
    FEATURE_BLOCKS,
    FEATURE_HELPERS,
    MEASUREMENTS,
    NUM_BLOCKS,
    Measurement,
)
from .coordinator import MojElektroDataUpdateCoordinator
from .entity import MojElektroEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: MojElektroConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Moj Elektro sensors from a config entry."""
    coordinator = entry.runtime_data
    features = coordinator.features
    entities: list[SensorEntity] = []

    # One energy sensor per enabled daily register measurement.
    for meas in MEASUREMENTS:
        if meas.period != "daily":
            continue
        if meas.feature is None or meas.feature in features:
            entities.append(MojElektroRegisterSensor(coordinator, meas))

    if FEATURE_BLOCKS in features:
        for block in range(1, NUM_BLOCKS + 1):
            entities.append(MojElektroBlockSensor(coordinator, block))

    if FEATURE_HELPERS in features:
        entities.append(MojElektroCurrentBlockSensor(coordinator))
        entities.append(MojElektroMonthlyPeakSensor(coordinator))
        for block in range(1, NUM_BLOCKS + 1):
            entities.append(MojElektroAgreedPowerSensor(coordinator, block))

    async_add_entities(entities)


class MojElektroRegisterSensor(MojElektroEntity, SensorEntity):
    """Daily consumption/export for one register (kWh)."""

    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
    _attr_state_class = SensorStateClass.TOTAL

    def __init__(
        self, coordinator: MojElektroDataUpdateCoordinator, meas: Measurement
    ) -> None:
        """Initialise a register sensor from its measurement description."""
        super().__init__(coordinator)
        self._meas = meas
        self._attr_unique_id = f"{coordinator.meter_id}_{meas.key}"
        if meas.key == "daily_consumption":
            # Preserve the v0.1.x entity (name + translation).
            self._attr_translation_key = "daily_consumption"
        else:
            self._attr_name = meas.name
        self._attr_icon = (
            "mdi:transmission-tower-export"
            if "export" in meas.key
            else "mdi:transmission-tower-import"
        )

    @property
    def _latest(self) -> dict[str, Any] | None:
        return self.coordinator.data.get("registers", {}).get(self._meas.key, {}).get(
            "latest"
        )

    @property
    def native_value(self) -> float | None:
        """Return the last completed day's value in kWh."""
        latest = self._latest
        return latest["consumption"] if latest else None

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Expose the reading date and cumulative register value."""
        latest = self._latest
        if not latest:
            return None
        return {"date": latest["date"], "cumulative_kwh": latest["cumulative"]}


class MojElektroBlockSensor(MojElektroEntity, SensorEntity):
    """Daily consumption within one network time-block (kWh)."""

    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
    _attr_state_class = SensorStateClass.TOTAL
    _attr_icon = "mdi:calendar-clock"

    def __init__(
        self, coordinator: MojElektroDataUpdateCoordinator, block: int
    ) -> None:
        """Initialise a per-block daily sensor."""
        super().__init__(coordinator)
        self._block = block
        self._attr_name = f"Daily consumption block {block}"
        self._attr_unique_id = f"{coordinator.meter_id}_blok_{block}"

    @property
    def native_value(self) -> float | None:
        """Return the last completed day's consumption for this block."""
        return self.coordinator.data.get("blocks", {}).get("latest", {}).get(
            self._block
        )


class MojElektroCurrentBlockSensor(MojElektroEntity, SensorEntity):
    """The network time-block (1-5) that is active right now."""

    _attr_translation_key = "current_tariff_block"
    _attr_icon = "mdi:transmission-tower"

    def __init__(self, coordinator: MojElektroDataUpdateCoordinator) -> None:
        """Initialise the current-block sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.meter_id}_current_tariff_block"

    @property
    def native_value(self) -> int | None:
        """Return the active block, or ``None`` if unknown."""
        block = self.coordinator.data.get("current_block")
        return block or None


class MojElektroMonthlyPeakSensor(MojElektroEntity, SensorEntity):
    """Highest 15-minute power (kW) so far this month."""

    _attr_translation_key = "monthly_peak_power"
    _attr_device_class = SensorDeviceClass.POWER
    _attr_native_unit_of_measurement = UnitOfPower.KILO_WATT
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:flash"

    def __init__(self, coordinator: MojElektroDataUpdateCoordinator) -> None:
        """Initialise the monthly-peak-power sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.meter_id}_monthly_peak_power"

    @property
    def native_value(self) -> float | None:
        """Return the monthly peak power in kW."""
        return self.coordinator.data.get("monthly_peak_power")


class MojElektroAgreedPowerSensor(MojElektroEntity, SensorEntity):
    """Contracted (agreed) power for one time-block (kW)."""

    _attr_device_class = SensorDeviceClass.POWER
    _attr_native_unit_of_measurement = UnitOfPower.KILO_WATT
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = "mdi:transmission-tower"

    def __init__(
        self, coordinator: MojElektroDataUpdateCoordinator, block: int
    ) -> None:
        """Initialise a per-block agreed-power sensor."""
        super().__init__(coordinator)
        self._block = block
        self._attr_name = f"Agreed power block {block}"
        self._attr_unique_id = f"{coordinator.meter_id}_agreed_power_blok_{block}"

    @property
    def native_value(self) -> float | None:
        """Return the contracted power for this block in kW."""
        return self.coordinator.data.get("agreed_power", {}).get(self._block)
