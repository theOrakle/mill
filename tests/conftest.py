"""Shared fixtures for the Mill tests."""
from __future__ import annotations

from collections.abc import Generator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.const import CONF_PASSWORD, CONF_TOKEN, CONF_USERNAME
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.mill.const import DOMAIN

pytest_plugins = "pytest_homeassistant_custom_component"

DEVICE = "DEVICE1"

DEVICE_DATA = {
    "firmwareVersion": "comms:rls-v01.10.12-a61078b;control:rls-v01.10.12-a61078b",
    "oscarVersion": 2,
    "massInBucket": {"reported": 1.5},
    "massAddedSinceBucketEmpty": {"reported": 0.4},
    "bucketFullness": {"reported": "Low"},
    "grinderState": {"reported": "Normal"},
    "currentCycleEndTime": "2026-10-20T12:00:00Z",
    "dgoCycle": {"reported": "Idle", "desired": "Idle"},
    "lidLockSetting": {"reported": "LockedWhenHot", "desired": "LockedWhenHot"},
    "lidLockState": {"reported": True},
    "lidOpenState": {"reported": False},
    "bucketMissing": {"reported": False},
    "online": {"reported": True},
    "impactEnergyTotalKwh": 188.89,
    "impactEnergyCurrentMonthKwh": 3.36,
}


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Allow Home Assistant to load the custom integration under test."""


@pytest.fixture
def mock_config_entry() -> MockConfigEntry:
    """Return a Mill config entry."""
    return MockConfigEntry(
        domain=DOMAIN,
        title="user@example.com",
        unique_id="user@example.com",
        data={
            CONF_USERNAME: "user@example.com",
            CONF_PASSWORD: "secret",
            CONF_TOKEN: "TOKEN",
        },
    )


@pytest.fixture
def mock_client() -> Generator[MagicMock]:
    """Patch the Mill API client everywhere it is constructed."""
    with (
        patch("custom_components.mill.MillApiClient", autospec=True) as client_cls,
        patch("custom_components.mill.config_flow.MillApiClient", new=client_cls),
    ):
        client = client_cls.return_value
        client._token = "NEWTOKEN"
        client.async_get_data = AsyncMock(return_value={DEVICE: dict(DEVICE_DATA)})
        client.async_set_cycle = AsyncMock()
        client.async_set_lock = AsyncMock()
        yield client
