"""DataUpdateCoordinator for mill."""
from __future__ import annotations

from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)

from .api import (
    MillApiClient,
    MillApiClientAuthenticationError,
    MillApiClientError,
)
from .const import DOMAIN, LOGGER

type MillConfigEntry = ConfigEntry[MillDataUpdateCoordinator]


# https://developers.home-assistant.io/docs/integration_fetching_data#coordinated-single-api-poll-for-data-for-all-entities
class MillDataUpdateCoordinator(DataUpdateCoordinator[dict[str, dict]]):
    """Class to manage fetching data from the API."""

    config_entry: MillConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: MillConfigEntry,
        client: MillApiClient,
    ) -> None:
        """Initialize."""
        self.client = client
        super().__init__(
            hass,
            LOGGER,
            config_entry=config_entry,
            name=DOMAIN,
            update_interval=timedelta(minutes=5),
        )

    async def _async_update_data(self) -> dict[str, dict]:
        """Update data via library."""
        try:
            return await self.client.async_get_data()
        except MillApiClientAuthenticationError as exception:
            raise ConfigEntryAuthFailed(exception) from exception
        except MillApiClientError as exception:
            raise UpdateFailed(exception) from exception
