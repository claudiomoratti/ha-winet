"""Measured values retain nulls; no invented zero readings."""

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.const import UnitOfTemperature
from homeassistant.helpers.entity import EntityCategory

from .const import (
    AUTOMATION_MODE_NAMES,
    CONF_AIR_DIVISOR,
    CONF_DUAL_FAN,
    CONF_HYDRO,
    STATUS_NAMES,
)
from .entity import WinetEntity


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = entry.runtime_data
    keys = ["status", "description", "air", "gasflue", "rpm_extractor"]
    if coordinator.settings[CONF_HYDRO]:
        keys += ["water"]
    if coordinator.settings[CONF_DUAL_FAN]:
        keys += ["wifi_signal", "fan_profile", "automation_mode"]
    async_add_entities(WinetSensor(coordinator, key) for key in keys)


class WinetSensor(WinetEntity, SensorEntity):
    def __init__(self, coordinator, key):
        super().__init__(coordinator, key)
        self.key = key
        self._attr_translation_key = key
        if key in ("air", "water", "gasflue"):
            self._attr_device_class = SensorDeviceClass.TEMPERATURE
            self._attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
            self._attr_state_class = SensorStateClass.MEASUREMENT
        elif key == "rpm_extractor":
            self._attr_native_unit_of_measurement = "rpm"
            self._attr_state_class = SensorStateClass.MEASUREMENT
            self._attr_icon = "mdi:fan"
        elif key == "status":
            self._attr_device_class = SensorDeviceClass.ENUM
            self._attr_options = [*STATUS_NAMES.values(), "unrecognized"]
        elif key == "automation_mode":
            self._attr_device_class = SensorDeviceClass.ENUM
            self._attr_options = [*AUTOMATION_MODE_NAMES.values(), "unrecognized"]
            self._attr_entity_category = EntityCategory.DIAGNOSTIC
            self._attr_icon = "mdi:calendar-clock"
        elif key == "wifi_signal":
            self._attr_entity_category = EntityCategory.DIAGNOSTIC
            self._attr_icon = "mdi:wifi"
        elif key == "fan_profile":
            self._attr_entity_category = EntityCategory.DIAGNOSTIC
            self._attr_icon = "mdi:tune-variant"

    @property
    def native_value(self):
        value = getattr(self.coordinator.data, self.key)
        if self.key == "status":
            return STATUS_NAMES.get(value, "unrecognized")
        if self.key == "automation_mode":
            return AUTOMATION_MODE_NAMES.get(value, "unrecognized")
        if self.key == "air" and value is not None:
            return value / self.coordinator.settings[CONF_AIR_DIVISOR]
        return value

    @property
    def extra_state_attributes(self):
        if self.key == "status":
            return {"raw_status": self.coordinator.data.status}
        return None
