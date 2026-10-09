"""Plateforme Switch."""
from homeassistant.components.switch import SwitchEntity
from . import DOMAIN


async def async_setup_entry(hass, entry, async_add_entities):
    data_handler = hass.data[DOMAIN][entry.entry_id]
    switch = KnxNotifierActiveSwitch(data_handler, entry)
    data_handler.entities.append(switch)
    async_add_entities([switch])


class KnxNotifierActiveSwitch(SwitchEntity):

    def __init__(self, data_handler, entry):
        self._handler = data_handler
        self._attr_name = f"{entry.title} Actif"
        self._attr_unique_id = f"{entry.entry_id}_active_switch"

    @property
    def is_on(self) -> bool:
        return self._handler.active

    async def async_turn_on(self, **kwargs):
        self._handler.set_active(True)

    async def async_turn_off(self, **kwargs):
        self._handler.set_active(False)