"""Tests for Mill setup, unload and entities."""
from __future__ import annotations

from unittest.mock import MagicMock

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.const import EntityCategory
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.mill.api import (
    MillApiClientAuthenticationError,
    MillApiClientCommunicationError,
)
from custom_components.mill.const import DOMAIN

from .conftest import DEVICE


async def test_setup_and_unload(
    hass: HomeAssistant, mock_client: MagicMock, mock_config_entry: MockConfigEntry
) -> None:
    """The entry loads, creates the device and entities, and unloads cleanly."""
    mock_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()
    assert mock_config_entry.state is ConfigEntryState.LOADED

    device = dr.async_get(hass).async_get_device_by_identifier(
        (DOMAIN, DEVICE), mock_config_entry.entry_id
    )
    assert device is not None
    assert device.manufacturer == "Mill"
    assert device.model == "Food Recycler"

    assert hass.states.get("switch.device1_dry_and_grind").state == "off"
    assert hass.states.get("binary_sensor.device1_lid_open").state == "off"
    assert hass.states.get("select.device1_lid_lock_setting").state == "LockedWhenHot"
    assert hass.states.get("sensor.device1_mass_in_bucket").state == "1.5"

    # The lid-lock setting is configuration, not a day-to-day control.
    lid_lock = er.async_get(hass).async_get("select.device1_lid_lock_setting")
    assert lid_lock.entity_category is EntityCategory.CONFIG

    assert await hass.config_entries.async_unload(mock_config_entry.entry_id)
    assert mock_config_entry.state is ConfigEntryState.NOT_LOADED


async def test_switch_and_select_call_api(
    hass: HomeAssistant, mock_client: MagicMock, mock_config_entry: MockConfigEntry
) -> None:
    """Controls forward to the API client."""
    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    await hass.services.async_call(
        "switch", "turn_on", {"entity_id": "switch.device1_dry_and_grind"}, blocking=True
    )
    mock_client.async_set_cycle.assert_awaited_once_with(DEVICE, "DryGrind")

    await hass.services.async_call(
        "select",
        "select_option",
        {"entity_id": "select.device1_lid_lock_setting", "option": "AlwaysLocked"},
        blocking=True,
    )
    mock_client.async_set_lock.assert_awaited_once_with(DEVICE, "AlwaysLocked")


async def test_setup_retries_when_mill_unreachable(
    hass: HomeAssistant, mock_client: MagicMock, mock_config_entry: MockConfigEntry
) -> None:
    """A connection failure at setup is retried, not a hard error."""
    mock_client.async_get_data.side_effect = MillApiClientCommunicationError("down")
    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    assert mock_config_entry.state is ConfigEntryState.SETUP_RETRY


async def test_setup_starts_reauth_on_rejected_credentials(
    hass: HomeAssistant, mock_client: MagicMock, mock_config_entry: MockConfigEntry
) -> None:
    """Rejected credentials start a re-authentication flow."""
    mock_client.async_get_data.side_effect = MillApiClientAuthenticationError("bad")
    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()
    assert mock_config_entry.state is ConfigEntryState.SETUP_ERROR
    flows = hass.config_entries.flow.async_progress_by_handler(DOMAIN)
    assert [f["context"]["source"] for f in flows] == ["reauth"]
