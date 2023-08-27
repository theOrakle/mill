"""Constants for the Mill online component."""
import logging

from homeassistant.const import Platform

_LOGGER = logging.getLogger(__name__)

DOMAIN = "mill"

ICON = 'mdi:recycler'

HOST = "api.mill.com"
URL = f"https://{HOST}/app/v1"

PLATFORMS = [
    Platform.SENSOR,
    Platform.BINARY_SENSOR
]
SENSORS = {
    "Status"            :       "data.attributes.status",
    "Cycle"             :       "data.attributes.dgoCycle.reported"
}
BINARY_SENSORS = {
    "Locked"            :       "data.attributes.isLocked",
    "Bucket Missing"    :       "data.attributes.bucketMissing",
    "Child Lock"        :       "data.attributes.childLockEnabled.reported"
}
