"""Mill API Client."""
from __future__ import annotations

import asyncio
import socket

import aiohttp
import async_timeout
import websockets
import json

HOST = "api.mill.com"
URL = f"https://{HOST}/app/v1"
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
        creds = {
            "email":    self._username,
            "password": self._password
        }
        async with async_timeout.timeout(10):
            response = await self._session.request(
                method="post", 
                url=f"{URL}/tokens",
                json=creds
            )
        if response.status in (401, 403):
            raise MillApiClientAuthenticationError(
                "Invalid credentials",
            )
        results=await response.json()
        auth = {"Authorization": "Bearer " + results.get('token')}
        results = await self._api_wrapper(
            method="get", 
            url=f"{URL}/session_init?refresh_token=true",
            headers=auth
        )
        LOGGER.debug(results)
        self.token = results["data"]["attributes"]["authToken"]
        self.userId = results["data"]["attributes"]["userId"]
        self.devices = results["data"]["attributes"]["deviceIds"]

    async def async_get_data(self) -> any:
        """Get data from the API."""
        data = {}
        await self.async_load_devices()
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
                raise MillApiClientCommunicationError(
                    "Error fetching information",
                ) from Exception
            data[device] = json.loads(results)["data"]["attributes"]
            LOGGER.debug(data)
        return data

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
