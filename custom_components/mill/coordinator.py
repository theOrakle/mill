from __future__ import annotations

import websockets
import aiohttp
import json
import pydash
from datetime import timedelta
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator, 
    UpdateFailed
)
from homeassistant.const import CONF_USERNAME, CONF_PASSWORD, CONF_ACCESS_TOKEN, CONF_CLIENT_ID
from .const import DOMAIN, _LOGGER, UPDATE_FREQ, HOST, URL

class MillCoordinator(DataUpdateCoordinator):

    def __init__(self, hass, config):
        self.results = {}
        self.token = config.data[CONF_ACCESS_TOKEN]
        self.userid = config.data[CONF_CLIENT_ID]

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=UPDATE_FREQ)
        )

    async def _async_update_data(self):
        url = f"{URL}/users/{self.userid}"
        auth = {"Authorization": "Bearer " + self.token}
        async with aiohttp.ClientSession() as session:
            async with session.get(url,headers=auth) as r:
                results = await r.json()
                self.devices = pydash.get(results,"data.attributes.deviceIds")
        url = f"wss://{HOST}/app/v1/websocket/device"
        for device in self.devices:
            headers = {
                'Host':                 HOST,
                'Upgrade':              'websocket',
                'Origin':               f'https://{HOST}',
                'X-Device-Id':          device,
                'X-Authorization':      self.token,
                'Connection':           'Upgrade'
            }
            try:
                async with websockets.connect(extra_headers=headers,uri=url) as ws:
                    results = await ws.recv()
            except:
                _LOGGER.error("Failed to communicate to the API")
            self.results[device] = json.loads(results)
