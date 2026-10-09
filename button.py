"""Plateforme Button."""
from homeassistant.components.button import ButtonEntity
from . import DOMAIN


async def async_setup_entry(hass, entry, async_add_entities):
    data_handler = hass.data[DOMAIN][entry.entry_id]
    button = KnxNotifierResetButton(data_handler, entry)
    data_handler.entities.append(button)
    async_add_entities([button])


class KnxNotifierResetButton(ButtonEntity):

    def __init__(self, data_handler, entry):
        self._handler = data_handler
        self._attr_name = f"{entry.title} Reset Alarme"
        self._attr_unique_id = f"{entry.entry_id}_reset_button"
        self._attr_icon = "mdi:restart"

    async def async_press(self):
        self._handler.reset_alarm()