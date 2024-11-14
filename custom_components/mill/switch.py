"""Switch platform for mill."""
from __future__ import annotations

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription, SwitchDeviceClass

from .const import DOMAIN, LOGGER
from .coordinator import MillDataUpdateCoordinator
from .entity import MillEntity

ENTITY_DESCRIPTIONS = (
    SwitchEntityDescription(
        key="dgoCycle",
        name="Dry and Grind",
        device_class=SwitchDeviceClass.SWITCH,
    ),
)


async def async_setup_entry(hass, entry, async_add_devices):
    """Set up the switch platform."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_devices(
        MillSwitch(
            coordinator=coordinator,
            entity_description=entity_description,
            device=device
        )
        for entity_description in ENTITY_DESCRIPTIONS
        for device in coordinator.data
    )


class MillSwitch(MillEntity, SwitchEntity):
    """mill Switch class."""

    def __init__(
        self,
        coordinator: MillDataUpdateCoordinator,
        entity_description: SwitchEntityDescription,
        device,
    ) -> None:
        """Initialize the switch class."""
        super().__init__(coordinator,entity_description,device)
        self.entity_description = entity_description
        self.device = device

    @property
    def is_on(self) -> bool:
        """Return true if the mill is on."""
        desc = self.entity_description
        desire = self.coordinator.data[self.device].get(desc.key)['desired']
        report = self.coordinator.data[self.device].get(desc.key)['reported']
        if desire != report and desire != None:
            state = desire
        else:
            state = report
        return state == 'DryGrind'

    async def async_turn_off(self, **kwargs):
        """Turn the mill off."""
        state = 'Idle'
        await self.coordinator.client.async_set_cycle(self.device, state) 
        await self.coordinator.async_request_refresh()

    async def async_turn_on(self, **kwargs):
        """Turn the mill on."""
        state = 'DryGrind'
        await self.coordinator.client.async_set_cycle(self.device, state)
        await self.coordinator.async_request_refresh()
