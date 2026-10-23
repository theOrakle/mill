"""Switch platform for mill."""
from __future__ import annotations

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription, SwitchDeviceClass

from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import MillConfigEntry, MillDataUpdateCoordinator
from .entity import MillEntity

ENTITY_DESCRIPTIONS = (
    SwitchEntityDescription(
        key="dgoCycle",
        name="Dry and Grind",
        device_class=SwitchDeviceClass.SWITCH,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: MillConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the switch platform."""
    coordinator = entry.runtime_data
    async_add_entities(
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

    @property
    def is_on(self) -> bool:
        """Return true if the mill is on."""
        desc = self.entity_description
        state_data = self.coordinator.data.get(self.device, {}).get(desc.key, {})
        if isinstance(state_data, dict):
            desire = state_data.get("desired")
            report = state_data.get("reported")
        else:
            desire = None
            report = state_data
        if desire != report and desire is not None:
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
