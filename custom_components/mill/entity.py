"""MillEntity class."""
from __future__ import annotations

from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, VERSION
from .coordinator import MillDataUpdateCoordinator

class MillEntity(CoordinatorEntity):
    """MillEntity class."""

    def __init__(
        self, 
        coordinator: MillDataUpdateCoordinator,
        entity_description,
        device,
    ) -> None:
        """Initialize."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{DOMAIN}_{device}_{entity_description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, device)},
            name=device,
            model=f"Integration {VERSION}",
            manufacturer=DOMAIN.capitalize(),
            sw_version=coordinator.data[device].get("firmwareVersion"),
            hw_version=coordinator.data[device].get("oscarVersion"),
        )
