"""Constants for the Mill online component."""
import logging

from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntityDescription
from homeassistant.components.sensor import SensorDeviceClass, SensorEntityDescription

_LOGGER = logging.getLogger(__name__)

DOMAIN = "mill"

COORDINATOR = "coordinator"

# In Seconds
UPDATE_FREQ = 30

HOST = "api.mill.com"
URL = f"https://{HOST}/app/v1"

SENSORS: dict[str, SensorEntityDescription] = {
    "mib": SensorEntityDescription(
        name="Mass In Bucket",
        icon="mdi:list-status",
        key="data.attributes.massInBucket"),
    "masbe": SensorEntityDescription(
        name="Mass Added Since Bucket Empty",
        icon="mdi:pail-plus",
        key="data.attributes.massAddedSinceBucketEmpty"),
    "bf": SensorEntityDescription(
        name="Bucket Fullness",
        icon="mdi:delete-variant",
        key="data.attributes.bucketFullness"),
    "cr": SensorEntityDescription(      
        name="Cycle",
        icon="mdi:dots-horizontal-circle",
        key="data.attributes.dgoCycle.reported")
}
BINARY_SENSORS = {
    "ll": BinarySensorEntityDescription(
        name="Lid Locked",
        icon="mdi:lock",
        key="data.attributes.lidLockState"),
    "lo": BinarySensorEntityDescription(
        name="Lid Open",
        icon="mdi:delete-empty",
        key="data.attributes.lidOpenState"),
    "bm": BinarySensorEntityDescription(      
        name="Bucket Missing",
        icon="mdi:pail-off",
        key="data.attributes.bucketMissing"),
    "cl": BinarySensorEntityDescription(      
        name="Child Lock",
        icon="mdi:lock",
        key="data.attributes.childLockEnabled.reported")
}
