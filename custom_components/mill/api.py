"""Mill API Client."""
from __future__ import annotations

import asyncio
import socket
import inspect

import aiohttp
import async_timeout
import websockets
import json

HOST = "api.mill.com"
AUTH_URL = f"https://{HOST}/app/v1"
CLOUD_URL = f"https://cloud.{HOST}/v1"

from .const import LOGGER

class MillApiClientError(Exception):
    """Exception to indicate a general API error."""


class MillApiClientCommunicationError(
    MillApiClientError
):
    """Exception to indicate a communication error."""


class MillApiClientAuthenticationError(
    MillApiClientError
):
    """Exception to indicate an authentication error."""


class MillApiClient:
    """Mill API Client."""

    def __init__(
        self,
        username: str,
        password: str,
        session: aiohttp.ClientSession,
        token: str,
    ) -> None:
        """Mill API Client."""
        self._username = username
        self._password = password
        self._session = session
        self._token = token
        self.devices = []

    async def async_load_devices(self) -> any:
        """Get token from the API."""
        if self.devices:
            LOGGER.debug("Exiting device load")
            return
        await self.async_update_token()
        auth = {"Authorization": "Bearer " + self._token}
        results = await self._api_wrapper(
            method="get", 
            url=f"{CLOUD_URL}/session_init?refresh_token=true",
            headers=auth
        )
        LOGGER.debug(results)
        self._token = results["authToken"]
        self.userId = results["userId"]
        self.devices = [d['device_id'] for d in results["devices"]]

    async def async_get_data(self) -> any:
        """Get data from the API."""
        data = {}
        await self.async_load_devices()
        url = f"wss://websocket.cloud.{HOST}/"
        for device in self.devices:
            headers = {
                'Host':                 HOST,
                'Upgrade':              'websocket',
                'Origin':               f'https://websocket.cloud.{HOST}',
                'deviceId':             device,
                'Authorization':        self._token,
                'Connection':           'Upgrade'
            }
            try:
                connect_args = {
                    "uri": url,
                    "headers": headers
                }
            
                sig = inspect.signature(websockets.connect).parameters
                if "extra_headers" in sig:
                    connect_args["extra_headers"] = connect_args.pop("headers")
                else:
                    connect_args["additional_headers"] = connect_args.pop("headers")
            
                async with websockets.connect(**connect_args) as ws:
                    results = await ws.recv()
            except Exception:
                raise MillApiClientCommunicationError(
                    "Error fetching information",
                ) from Exception
            data[device] = json.loads(results)
            LOGGER.debug(data)
        return data


    async def async_update_token(self):
        creds = {
            "email":    self._username,
            "password": self._password
        }
        async with async_timeout.timeout(10):
            response = await self._session.request(
                method="post",
                url=f"{AUTH_URL}/tokens",
                json=creds
            )
        if response.status in (401, 403):
            raise MillApiClientAuthenticationError(
                "Invalid credentials",
            )
        results=await response.json()
        self._token = results.get('token')


    async def async_set_lock(self, device, setting: str):
        """Set the lid lock setting.
        
        Valid settings: 'AlwaysLocked', 'AlwaysUnlocked', 'LockedWhenHot'
        """
        valid_settings = ['AlwaysLocked', 'AlwaysUnlocked', 'LockedWhenHot']
        if setting not in valid_settings:
            raise ValueError(f"Invalid lid lock setting: {setting}. Must be one of {valid_settings}")
            
        await self.async_update_token()
        auth = {"Authorization": "Bearer " + self._token}
        results = await self._api_wrapper(
            method="post", 
            url=f"{CLOUD_URL}/device_settings/{device}",
            data={"settings": {"lidLockSetting": setting}},
            headers=auth
        )
        LOGGER.debug(f"Lid lock setting set to {setting}: {results}")


    async def async_set_cycle(self, device, cycle_state):
        """Set the cycle."""
        await self.async_update_token()
        auth = {"Authorization": "Bearer " + self._token}
        results = await self._api_wrapper(
            method="post", 
            url=f"{CLOUD_URL}/device_settings/{device}",
            data={"settings":{"dgoCycle": cycle_state}},
            headers=auth
        )
        LOGGER.debug(results)


    async def _api_wrapper(
        self,
        method: str,
        url: str,
        data: dict | None = None,
        headers: dict | None = None,
    ) -> any:
        """Get information from the API."""
        try:
            async with async_timeout.timeout(10):
                response = await self._session.request(
                    method=method,
                    url=url,
                    headers=headers,
                    json=data,
                )
                if response.status in (401, 403):
                    raise MillApiClientAuthenticationError(
                        "Invalid credentials",
                    )
                response.raise_for_status()
                return await response.json()

        except asyncio.TimeoutError as exception:
            raise MillApiClientCommunicationError(
                "Timeout error fetching information",
            ) from exception
        except (aiohttp.ClientError, socket.gaierror) as exception:
            raise MillApiClientCommunicationError(
                "Error fetching information",
            ) from exception
        except Exception as exception:  # pylint: disable=broad-except
            raise MillApiClientError(
                "Something really wrong happened!"
            ) from exception
