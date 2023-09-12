"""Constants for the Mill online component."""
import logging

from homeassistant.const import Platform
from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntityDescription
from homeassistant.components.sensor import SensorDeviceClass, SensorEntityDescription

_LOGGER = logging.getLogger(__name__)

DOMAIN = "mill"

ICON = 'mdi:recycler'

HOST = "api.mill.com"
URL = f"https://{HOST}/app/v1"

PLATFORMS = [
    Platform.SENSOR,
    Platform.BINARY_SENSOR
]
SENSORS: dict[str, SensorEntityDescription] = {
    "Status": SensorEntityDescription(
        name="Status",
        icon="mdi:list-status",
        key="data.attributes.status"),
    "Bucket": SensorEntityDescription(
        name="Bucket",
        icon="mdi:delete-variant",
        key="data.attributes.bucketFullness"),
    "Cycle": SensorEntityDescription(      
        name="Cycle",
        icon="mdi:dots-horizontal-circle",
        key="data.attributes.dgoCycle.reported")
}
BINARY_SENSORS = {
    "Locked": BinarySensorEntityDescription(
        name="Locked",
        icon="mdi:lock",
        key="data.attributes.isLocked"),
    "Bucket Missing": BinarySensorEntityDescription(      
        name="Bucket Missing",
        icon="mdi:delete-variant",
        key="data.attributes.bucketMissing"),
    "Child Lock": BinarySensorEntityDescription(      
        name="Child Lock",
        icon="mdi:lock",
        key="data.attributes.childLockEnabled.reported")
}
