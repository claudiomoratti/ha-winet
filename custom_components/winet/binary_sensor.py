"""Alarm according to the conventional WiNet Stove status mapping."""

from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity

from .entity import WinetEntity


async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities([WinetAlarm(entry.runtime_data)])


class WinetAlarm(WinetEntity, BinarySensorEntity):
    _attr_device_class = BinarySensorDeviceClass.PROBLEM
    _attr_translation_key = "alarm"

    def __init__(self, coordinator):
        super().__init__(coordinator, "alarm")

    @property
    def is_on(self):
        status = self.coordinator.data.status
        return status == 3 if status in (0, 1, 2, 3) else None
