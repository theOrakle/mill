"""Select platform for mill."""
from __future__ import annotations

from homeassistant.components.select import SelectEntity, SelectEntityDescription

from .const import DOMAIN, LOGGER
from .coordinator import MillDataUpdateCoordinator
from .entity import MillEntity

ENTITY_DESCRIPTIONS = (
    SelectEntityDescription(
        key="lidLockSetting",
        name="Lid Lock Setting",
        icon="mdi:lock-outline",
        options=["AlwaysLocked", "AlwaysUnlocked", "LockedWhenHot"],
    ),
)


async def async_setup_entry(hass, entry, async_add_devices):
    """Set up the select platform."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    entities = []
    
    for device in coordinator.data:
        for entity_description in ENTITY_DESCRIPTIONS:
            # Only add lid lock setting if the device supports it
            if coordinator.data[device].get(entity_description.key) is not None:
                entities.append(
                    MillSelect(
                        coordinator=coordinator,
                        entity_description=entity_description,
                        device=device
                    )
                )
    
    async_add_devices(entities)


class MillSelect(MillEntity, SelectEntity):
    """Mill Select class."""

    def __init__(
        self,
        coordinator: MillDataUpdateCoordinator,
        entity_description: SelectEntityDescription,
        device,
    ) -> None:
        """Initialize the select class."""
        super().__init__(coordinator, entity_description, device)
        self.entity_description = entity_description
        self.device = device
        self._attr_options = entity_description.options

    @property
    def current_option(self) -> str | None:
        """Return the selected entity option."""
        desc = self.entity_description
        lid_lock_data = self.coordinator.data[self.device].get(desc.key)
        
        if isinstance(lid_lock_data, dict):
            desired = lid_lock_data.get('desired')
            reported = lid_lock_data.get('reported')
            # Use desired state if it differs from reported and is not None
            if desired != reported and desired is not None:
                current_setting = desired
            else:
                current_setting = reported
        else:
            current_setting = lid_lock_data
        
        # Make sure the current setting is in our options list
        if current_setting in self._attr_options:
            return current_setting
        else:
            LOGGER.warning(f"Unknown lid lock setting: {current_setting}")
            return None

    async def async_select_option(self, option: str) -> None:
        """Change the selected option."""
        if option not in self._attr_options:
            LOGGER.error(f"Invalid option: {option}. Valid options: {self._attr_options}")
            return
            
        await self.coordinator.client.async_set_lock(self.device, option)
        await self.coordinator.async_request_refresh()

        async def delayed_refresh():
            import asyncio
            await asyncio.sleep(5)  # Wait 5 seconds
            await self.coordinator.async_request_refresh()
            await asyncio.sleep(10)  # Wait another 10 seconds
            await self.coordinator.async_request_refresh()
        
        # Run delayed refreshes in background
        self.coordinator.hass.async_create_task(delayed_refresh())
