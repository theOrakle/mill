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
# Mill is moving accounts to a new login platform (issue #13). Established
# accounts still work on the legacy AUTH_URL login; newer ones may not.
NEW_AUTH_URL = "https://account.prod.platform.mill.com/v1/auth/token"
SESSION_INIT_URL = f"{CLOUD_URL}/session_init?refresh_token=true"
# A client error from a login step means "this login path can't authenticate
# this account" (wrong password, a newer/older account type, or the path having
# been retired) - the cue to try the other login. Rate limits (429), timeouts
# and 5xx are deliberately NOT in here: those are outages, not rejections.
_LOGIN_REJECTED = (400, 401, 403, 404, 410)
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
        self.userId: str | None = None
        # Which login last worked: "new" (account platform), "old" (legacy) or
        # None before the first successful login.
        self._flow: str | None = None

    async def async_load_devices(self) -> None:
        """Learn the account's devices and user id (legacy login only).

        The new login gets both from session_init as part of logging in, every
        poll, so there is nothing to do here for it.
        """
        if self.devices:
            LOGGER.debug("Exiting device load")
            return
        if self._flow != "old":
            return
        auth = {"Authorization": "Bearer " + self._token}
        results = await self._api_wrapper(
            method="get",
            url=SESSION_INIT_URL,
            headers=auth
        )
        LOGGER.debug(results)
        self.userId = results.get("userId")
        self.devices = [d["device_id"] for d in results.get("devices", []) if isinstance(d, dict) and d.get("device_id")]

    async def async_get_data(self) -> dict[str, dict]:
        """Get data from the API."""
        data: dict[str, dict] = {}
        had_error = False
        await self.async_update_token()
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
            max_attempts = 3
            results = None
            for attempt in range(1, max_attempts + 1):
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
                    break
                except Exception as exception:  # noqa: BLE001
                    LOGGER.debug(
                        "Websocket read failed for device %s (attempt %d/%d): %s",
                        device, attempt, max_attempts, exception,
                    )
                    if attempt < max_attempts:
                        await asyncio.sleep(2)
            if results is None:
                LOGGER.error("Websocket read failed for device %s after %d attempts", device, max_attempts)
                had_error = True
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
        """Log in and refresh self._token.

        Tries the login that worked last time first (the new platform login
        on the very first run) and falls back to the other one when this
        account is rejected by it. Network problems are not "rejections" and
        are raised straight away instead of flipping flows.
        """
        order = ("old", "new") if self._flow == "old" else ("new", "old")
        rejected: MillApiClientAuthenticationError | None = None
        for flow in order:
            try:
                if flow == "new":
                    await self._login_new()
                else:
                    await self._login_old()
            except MillApiClientAuthenticationError as exception:
                LOGGER.debug("Mill %s login was rejected: %s", flow, exception)
                rejected = exception
                continue
            if self._flow != flow:
                LOGGER.info(
                    "Mill: logged in with the %s",
                    "new account platform login" if flow == "new" else "legacy login",
                )
                self._flow = flow
            return
        raise rejected or MillApiClientAuthenticationError("Invalid credentials")

    async def _login_request(
        self,
        method: str,
        url: str,
        json_body: dict | None = None,
        headers: dict | None = None,
    ) -> tuple[int, object]:
        """One login-related request -> (status, parsed JSON or None).

        Only transport failures raise; the caller decides what a status means.
        """
        try:
            async with async_timeout.timeout(10):
                response = await self._session.request(
                    method=method, url=url, json=json_body, headers=headers
                )
                status = response.status
                try:
                    payload = await response.json(content_type=None)
                except ValueError:
                    payload = None
        except asyncio.TimeoutError as exception:
            raise MillApiClientCommunicationError(
                "Timeout error fetching information",
            ) from exception
        except (aiohttp.ClientError, socket.gaierror) as exception:
            raise MillApiClientCommunicationError(
                f"Error fetching information: {type(exception).__name__}",
            ) from exception
        return status, payload

    async def _login_old(self) -> None:
        """Legacy login: one request, returns a long-lived token."""
        status, payload = await self._login_request(
            "post",
            f"{AUTH_URL}/tokens",
            json_body={"email": self._username, "password": self._password},
        )
        if status in _LOGIN_REJECTED:
            raise MillApiClientAuthenticationError(f"Legacy login rejected ({status})")
        if not 200 <= status < 300 or not isinstance(payload, dict):
            raise MillApiClientCommunicationError(f"Legacy login failed ({status})")
        token = payload.get("token")
        if not token:
            raise MillApiClientAuthenticationError("No token returned in auth response")
        self._token = token

    async def _login_new(self) -> None:
        """New account-platform login.

        Logging in returns a short-lived (60 min) access token + refresh token.
        Mill's cloud API only trusts that pair after a session_init that also
        carries the refresh token in an `x-refresh-token` header, and its
        response holds the `authToken` the websocket and REST calls use - so
        session_init is part of every new-style login (which also keeps the
        device list fresh).
        """
        status, payload = await self._login_request(
            "post",
            NEW_AUTH_URL,
            json_body={"email": self._username, "password": self._password},
        )
        if status in _LOGIN_REJECTED:
            raise MillApiClientAuthenticationError(f"New login rejected ({status})")
        if not 200 <= status < 300 or not isinstance(payload, dict):
            raise MillApiClientCommunicationError(f"New login failed ({status})")
        access, refresh = payload.get("token"), payload.get("refreshToken")
        if not access or not refresh:
            raise MillApiClientAuthenticationError("New login returned no token")

        status, session = await self._login_request(
            "get",
            SESSION_INIT_URL,
            headers={"Authorization": f"Bearer {access}", "x-refresh-token": refresh},
        )
        if status in _LOGIN_REJECTED:
            raise MillApiClientAuthenticationError(f"New session rejected ({status})")
        if not 200 <= status < 300 or not isinstance(session, dict):
            raise MillApiClientCommunicationError(f"New session failed ({status})")
        auth_token = session.get("authToken")
        if not auth_token:
            raise MillApiClientAuthenticationError("New session returned no authToken")
        self._token = auth_token
        self.userId = session.get("userId") or self.userId
        devices = [
            d["device_id"]
            for d in session.get("devices", [])
            if isinstance(d, dict) and d.get("device_id")
        ]
        if devices:
            self.devices = devices


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
