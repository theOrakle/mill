import pydash
from homeassistant.helpers.entity import Entity, DeviceInfo
from .const import DOMAIN, _LOGGER, BINARY_SENSORS

async def async_setup_entry(hass, config, async_add_entities) -> None:
    coordinator = hass.data[DOMAIN][config.entry_id]
    entities = []
    for device in coordinator.devices:
        for field in BINARY_SENSORS:
            entities.append(MySensor(coordinator, device, field, BINARY_SENSORS[field]))
    async_add_entities(entities)

class MySensor(Entity):
    def __init__(self,coordinator,device,idx,entity):
        self.coordinator = coordinator
        self.device = device 
        self.idx = idx
        self.path = entity.key
        self._name = entity.name
        self._icon = entity.icon
        self._state = None
        self._attributes = {}
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self.device)},
            manufacturer=DOMAIN,
            model="Base",
            sw_version=pydash.get(self.coordinator.results[self.device],"data.attributes.firmwareVersion"),
            hw_version=pydash.get(self.coordinator.results[self.device],"data.attributes.oscarVersion"),
            name=self.device)

    @property
    def unique_id(self):
        return f"{DOMAIN}_{self.device}_{self._name}"

    @property
    def name(self):
        return self._name

    @property
    def icon(self):
        return self._icon

    @property
    def state(self):
        return self._state

    @property
    def state_attributes(self):
        return self._attributes

    async def async_update(self) -> None:
        self._state = pydash.get(self.coordinator.results[self.device],self.path) 
