"""MillEntity class."""
from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import EntityDescription
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import MillDataUpdateCoordinator


class MillEntity(CoordinatorEntity[MillDataUpdateCoordinator]):
    """Base class for Mill entities (one device per food recycler)."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: MillDataUpdateCoordinator,
        entity_description: EntityDescription,
        device: str,
    ) -> None:
        """Initialize."""
        super().__init__(coordinator)
        self.entity_description = entity_description
        self.device = device
        device_data = coordinator.data.get(device, {})
        self._attr_unique_id = f"{DOMAIN}_{device}_{entity_description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, device)},
            name=device,
            manufacturer="Mill",
            model="Food Recycler",
            sw_version=device_data.get("firmwareVersion"),
            hw_version=str(v) if (v := device_data.get("oscarVersion")) is not None else None,
        )
