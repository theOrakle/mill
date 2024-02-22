"""Binary sensor platform for mill."""
from __future__ import annotations

from homeassistant.const import EntityCategory
from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)

from .const import DOMAIN
from .coordinator import MillDataUpdateCoordinator
from .entity import MillEntity

ENTITY_DESCRIPTIONS = (
    BinarySensorEntityDescription(
        key="lidLockState",
        name="Lid Locked",
        device_class=BinarySensorDeviceClass.LOCK,
    ),
    BinarySensorEntityDescription(
        key="lidOpenState",
        name="Lid Open",
        device_class=BinarySensorDeviceClass.DOOR,
    ),
    BinarySensorEntityDescription(
        key="bucketMissing",
        name="Bucket Missing",
        device_class=BinarySensorDeviceClass.PROBLEM,
    ),
    BinarySensorEntityDescription(
        key="childLockEnabled",
        name="Child Lock",
        device_class=BinarySensorDeviceClass.LOCK,
    ),
    BinarySensorEntityDescription(
        key="online",
        name="Online",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
)


async def async_setup_entry(hass, entry, async_add_devices):
    """Set up the binary_sensor platform."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_devices(
        MillBinarySensor(
            coordinator=coordinator,
            entity_description=entity_description,
            device=device,
        )
        for entity_description in ENTITY_DESCRIPTIONS
        for device in coordinator.data
    )


class MillBinarySensor(MillEntity, BinarySensorEntity):
    """mill binary_sensor class."""

    def __init__(
        self,
        coordinator: MillDataUpdateCoordinator,
        entity_description: BinarySensorEntityDescription,
        device,
    ) -> None:
        """Initialize the binary_sensor class."""
        super().__init__(coordinator,entity_description,device)
        self.entity_description = entity_description
        self.device = device

    @property
    def is_on(self) -> bool:
        """Return true if the binary_sensor is on."""
        desc = self.entity_description
        value = self.coordinator.data[self.device].get(desc.key)
        if isinstance(value, dict):
            value = value.get('reported')
        if self.entity_description.device_class == BinarySensorDeviceClass.LOCK:
            value = not(value)
        return value
