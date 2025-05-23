"""Sensor platform for mill."""
from __future__ import annotations

from homeassistant.components.sensor import SensorEntity, SensorEntityDescription, SensorDeviceClass
from dateutil import parser

from .const import DOMAIN
from .coordinator import MillDataUpdateCoordinator
from .entity import MillEntity

ENTITY_DESCRIPTIONS = (
    SensorEntityDescription(
        key="massInBucket",
        name="Mass In Bucket",
        icon="mdi:list-status",
        device_class=SensorDeviceClass.WEIGHT,
        native_unit_of_measurement="kg",
    ),
    SensorEntityDescription(
        key="massAddedSinceBucketEmpty",
        name="Mass Added Since Bucket Empty",
        icon="mdi:pail-plus",
        device_class=SensorDeviceClass.WEIGHT,
        native_unit_of_measurement="kg",
    ),
    SensorEntityDescription(
        key="bucketFullness",
        name="Bucket Fullness",
        icon="mdi:delete-variant",
    ),
    SensorEntityDescription(
        key="grinderState",
        name="Grinder State",
        icon="mdi:hydro-power",
    ),
    SensorEntityDescription(
        key="currentCycleEndTime",
        name="Cycle End Time",
        icon="mdi:clock",
        device_class=SensorDeviceClass.TIMESTAMP,
    ),
)


async def async_setup_entry(hass, entry, async_add_devices):
    """Set up the sensor platform."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_devices(
        MillSensor(
            coordinator=coordinator,
            entity_description=entity_description,
            device=device
        )
        for entity_description in ENTITY_DESCRIPTIONS
        for device in coordinator.data
    )


class MillSensor(MillEntity, SensorEntity):
    """mill Sensor class."""

    def __init__(
        self,
        coordinator: MillDataUpdateCoordinator,
        entity_description: SensorEntityDescription,
        device,
    ) -> None:
        """Initialize the sensor class."""
        super().__init__(coordinator,entity_description,device)
        self.entity_description = entity_description
        self.device = device

    @property
    def native_value(self) -> str:
        """Return the native value of the sensor."""
        desc = self.entity_description
        if self.entity_description.device_class == SensorDeviceClass.TIMESTAMP:
          str_val = self.coordinator.data[self.device].get(desc.key)
          if str_val:
            value = parser.isoparse(str_val)
          else:
            value = None
        else:
          value = self.coordinator.data[self.device].get(desc.key)
        if isinstance(value, dict):
            value = value.get('reported')
        return value
