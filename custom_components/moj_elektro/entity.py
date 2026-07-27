"""Shared base entity for the Moj Elektro integration."""

from __future__ import annotations

from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import MojElektroDataUpdateCoordinator


class MojElektroEntity(CoordinatorEntity[MojElektroDataUpdateCoordinator]):
    """Base entity binding all Moj Elektro entities to one device."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: MojElektroDataUpdateCoordinator) -> None:
        """Initialise the shared device info."""
        super().__init__(coordinator)
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.meter_id)},
            name="Moj Elektro",
            manufacturer="Informatika d.o.o.",
            model="Moj Elektro metering point",
        )
