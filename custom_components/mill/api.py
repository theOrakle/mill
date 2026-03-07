"""Mill API Client."""
from __future__ import annotations

import asyncio
import inspect
import socket
from datetime import UTC, datetime

import aiohttp
import async_timeout
import json
import websockets

import homeassistant.util.ssl

from .const import LOGGER

HOST = "api.mill.com"
AUTH_URL = f"https://{HOST}/app/v1"
CLOUD_URL = f"https://cloud.{HOST}/v1"
WS_CONNECT_TIMEOUT = 10
WS_RECV_TIMEOUT = 10


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
        self.devices: list[str] = []

    async def async_load_devices(self) -> None:
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
        self.devices = [d["device_id"] for d in results["devices"] if isinstance(d, dict) and d.get("device_id")]

    async def async_get_data(self) -> dict[str, dict]:
        """Get data from the API."""
        data: dict[str, dict] = {}
        had_error = False
        await self.async_load_devices()
        impact_metrics = await self.async_get_impact_metrics()
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
                    "headers": headers,
                    "ssl": homeassistant.util.ssl.client_context(),
                    "open_timeout": WS_CONNECT_TIMEOUT,
                }

                sig = inspect.signature(websockets.connect).parameters
                if "extra_headers" in sig:
                    connect_args["extra_headers"] = connect_args.pop("headers")
                else:
                    connect_args["additional_headers"] = connect_args.pop("headers")

                async with websockets.connect(**connect_args) as ws:
                    async with async_timeout.timeout(WS_RECV_TIMEOUT):
                        results = await ws.recv()
            except Exception as exception:  # noqa: BLE001
                had_error = True
                LOGGER.debug("Websocket read failed for device %s: %s", device, exception)
                continue
            try:
                data[device] = json.loads(results)
            except json.JSONDecodeError:
                LOGGER.debug("Skipping non-JSON websocket payload for device %s", device)
                had_error = True
                continue
            # Impact values are user-level; copy onto each device payload for entity access.
            data[device].update(impact_metrics)
            LOGGER.debug(data)
        if not data and had_error:
            raise MillApiClientCommunicationError(
                "Error fetching information from websocket devices",
            )
        return data

    async def async_get_impact_metrics(self) -> dict[str, float | int | str | None]:
        """Fetch and summarize impact metrics (including energy usage)."""
        if not getattr(self, "userId", None):
            return {
                "impactEnergyTotalKwh": None,
                "impactEnergyCurrentMonthKwh": None,
                "impactEnergyMonths": 0,
                "impactEnergyLatestMonthDate": None,
            }
        await self.async_update_token()
        auth = {"Authorization": f"Bearer {self._token}"}
        response = await self._api_wrapper(
            method="get",
            url=f"{CLOUD_URL}/feature_data/{self.userId}",
            headers=auth,
        )
        impact = response.get("impact", {}) if isinstance(response, dict) else {}
        historical = (
            impact.get("historical_energy_use_data", {})
            if isinstance(impact, dict)
            else {}
        )
        by_month = (
            historical.get("by_month", [])
            if isinstance(historical, dict)
            else []
        )
        entries: list[dict] = [x for x in by_month if isinstance(x, dict)]
        total_kwh = 0.0
        now = datetime.now(UTC)
        current_month_kwh = 0.0
        latest_date: str | None = None

        for item in entries:
            try:
                kwh = float(item.get("kwh", 0.0) or 0.0)
            except (TypeError, ValueError):
                kwh = 0.0
            total_kwh += kwh

            date_value = item.get("date")
            parsed = _parse_date(date_value)
            if parsed:
                if parsed.year == now.year and parsed.month == now.month:
                    current_month_kwh += kwh
                if latest_date is None or parsed.date().isoformat() > latest_date:
                    latest_date = parsed.date().isoformat()

        return {
            "impactEnergyTotalKwh": round(total_kwh, 3),
            "impactEnergyCurrentMonthKwh": round(current_month_kwh, 3),
            "impactEnergyMonths": len(entries),
            "impactEnergyLatestMonthDate": latest_date,
        }

    async def async_update_token(self) -> None:
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
        response.raise_for_status()
        results = await response.json()
        self._token = results.get("token")


    async def async_set_lock(self, device: str, setting: str) -> None:
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


    async def async_set_cycle(self, device: str, cycle_state: str) -> None:
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
    ) -> dict:
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


def _parse_date(value: object) -> datetime | None:
    """Parse a YYYY-MM-DD date from Mill impact payload."""
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)
