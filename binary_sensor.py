"""Plateforme Binary Sensor."""
from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from . import DOMAIN


async def async_setup_entry(hass, entry, async_add_entities):
    data_handler = hass.data[DOMAIN][entry.entry_id]
    sensor = KnxNotifierAlarmSensor(data_handler, entry)
    data_handler.entities.append(sensor)
    async_add_entities([sensor])


class KnxNotifierAlarmSensor(BinarySensorEntity):

    def __init__(self, data_handler, entry):
        self._handler = data_handler
        self._attr_name = f"{entry.title} Etat Alarme"
        self._attr_unique_id = f"{entry.entry_id}_alarm_sensor"
        self._attr_device_class = BinarySensorDeviceClass.PROBLEM

    @property
    def is_on(self) -> bool:
        return self._handler.in_alarm