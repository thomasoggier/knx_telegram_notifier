"""Plateforme Switch."""
from homeassistant.components.switch import SwitchEntity
from homeassistant.helpers.restore_state import RestoreEntity
from . import DOMAIN


async def async_setup_entry(hass, entry, async_add_entities):
    data_handler = hass.data[DOMAIN][entry.entry_id]
    switch = KnxNotifierActiveSwitch(data_handler, entry)
    data_handler.entities.append(switch)
    async_add_entities([switch])


class KnxNotifierActiveSwitch(RestoreEntity, SwitchEntity):
    """Switch d'activation avec persistance native via RestoreEntity."""

    def __init__(self, data_handler, entry):
        self._handler = data_handler
        self._attr_name = f"{entry.title} Actif"
        self._attr_unique_id = f"{entry.entry_id}_active_switch"
        # On initialise par défaut à True (ou selon le handler)
        self._is_on = True

    async def async_added_to_hass(self) -> None:
        """Exécuté lorsque l'entité est ajoutée à Home Assistant : récupère l'ancien état."""
        await super().async_added_to_hass()
        
        # Récupération de l'état d'avant le redémarrage
        last_state = await self.async_get_last_state()
        if last_state is not None:
            self._is_on = (last_state.state == "on")
        else:
            self._is_on = self._handler.active

        # On synchronise immédiatement le gestionnaire central
        self._handler.active = self._is_on

    @property
    def is_on(self) -> bool:
        return self._handler.active

    async def async_turn_on(self, **kwargs):
        self._handler.active = True
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs):
        self._handler.active = False
        self.async_write_ha_state()