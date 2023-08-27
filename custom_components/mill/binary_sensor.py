import websockets
import aiohttp
import json
import pydash
from homeassistant.helpers.entity import Entity, DeviceInfo
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from .const import DOMAIN, HOST, URL, _LOGGER, BINARY_SENSORS

async def async_setup_entry(hass, config, async_add_entities) -> None:
    creds = {
        "email":    config.data[CONF_USERNAME],
        "password": config.data[CONF_PASSWORD]
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(URL+"/tokens",data=creds) as r:
            results = await r.json()
    if r.status == 201:
        auth = {"Authorization": "Bearer " + results.get('token')}
        async with aiohttp.ClientSession() as session:
            async with session.get(URL+"/session_init?refresh_token=true",headers=auth) as r:
                results = await r.json()
        token = results.get('data')['attributes']['authToken']
    devices = results.get('data')['attributes']['deviceIds']

    entities = []
    for device in devices:
        for field in BINARY_SENSORS:
            entities.append(MillBinarySensor(hass, token, device, field))

    async_add_entities(entities)

class MillBinarySensor(Entity):

    def parse_results(self,results):
        self._state = pydash.get(results,BINARY_SENSORS[self.field])
        self._attributes = {}

    def __init__(self,hass,token,device,field):
        self.token = token
        self.device = device
        self.field = field
        self._state = None
        self._attributes = {}
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, device)},
            manufacturer=DOMAIN,
            model="1",
            name=device)

    @property
    def unique_id(self):
        return f"{DOMAIN}_{self.device}_{self.name}"

    @property
    def name(self):
        return f"{DOMAIN}_{self.field}"

    @property
    def icon(self):
        return 'mdi:recycle'

    @property
    def state(self):
        return self._state

    @property
    def state_attributes(self):
        return self._attributes

    async def async_update(self) -> None:
        url = f"wss://{HOST}/app/v1/websocket/device"
        headers = {
            'Host':                 HOST,
            'Upgrade':              'websocket',
            'Origin':               f'https://{HOST}',
            'X-Device-Id':          self.device,
            'X-Authorization':      self.token,
            'Connection':           'Upgrade'
        }

        try:
            async with websockets.connect(extra_headers=headers,uri=url) as ws:
                results = await ws.recv()
                #if results.status_code != 200:
                #    self.refresh_token()
                #results = await ws.recv()
        except:
            _LOGGER.error("Failed to communicate to the API")

        self.parse_results(json.loads(results))
