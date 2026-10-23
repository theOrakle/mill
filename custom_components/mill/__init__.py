"""Custom integration to integrate mill with Home Assistant.

For more details about this integration, please refer to
https://github.com/theOrakle/mill
"""
from __future__ import annotations

from homeassistant.const import CONF_PASSWORD, CONF_TOKEN, CONF_USERNAME, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import MillApiClient
from .coordinator import MillConfigEntry, MillDataUpdateCoordinator

PLATFORMS: list[Platform] = [
    Platform.BINARY_SENSOR,
    Platform.SELECT,
    Platform.SENSOR,
    Platform.SWITCH,
]


# https://developers.home-assistant.io/docs/config_entries_index/#setting-up-an-entry
async def async_setup_entry(hass: HomeAssistant, entry: MillConfigEntry) -> bool:
    """Set up this integration using UI."""
    coordinator = MillDataUpdateCoordinator(
        hass,
        entry,
        MillApiClient(
            username=entry.data[CONF_USERNAME],
            password=entry.data[CONF_PASSWORD],
            session=async_get_clientsession(hass),
            token=entry.data.get(CONF_TOKEN),
        ),
    )
    # Raises ConfigEntryNotReady (retry) or ConfigEntryAuthFailed (reauth).
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: MillConfigEntry) -> bool:
    """Handle removal of an entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
