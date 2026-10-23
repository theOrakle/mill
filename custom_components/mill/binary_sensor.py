"""Binary sensor platform for mill."""
from __future__ import annotations

from homeassistant.const import EntityCategory
from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)

from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import MillConfigEntry, MillDataUpdateCoordinator
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
        key="online",
        name="Online",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: MillConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the binary_sensor platform."""
    coordinator = entry.runtime_data
    async_add_entities(
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

    @property
    def is_on(self) -> bool:
        """Return true if the binary_sensor is on."""
        desc = self.entity_description
        value = self.coordinator.data.get(self.device, {}).get(desc.key)
        if isinstance(value, dict):
            value = value.get("reported")
        if value is None:
            return False
        if self.entity_description.device_class == BinarySensorDeviceClass.LOCK:
            value = not bool(value)
        return bool(value)
