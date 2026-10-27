"""Measured values retain nulls; no invented zero readings."""

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.const import SIGNAL_STRENGTH_DECIBELS_MILLIWATT, UnitOfTemperature
from homeassistant.helpers.entity import EntityCategory

from .const import (
    AUTOMATION_MODE_NAMES,
    CLOUD_STATUS_NAMES,
    CONF_AIR_DIVISOR,
    CONF_DUAL_FAN,
    CONF_HYDRO,
    OPERATING_PHASE_NAMES,
    STATUS_NAMES,
    WIFI_STATUS_NAMES,
)
from .entity import WinetEntity


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = entry.runtime_data
    keys = ["status", "description", "air", "gasflue", "rpm_extractor"]
    if coordinator.settings[CONF_HYDRO]:
        keys += ["water"]
    if coordinator.settings[CONF_DUAL_FAN]:
        keys += [
            "operating_phase",
            "alarm_code",
            "wifi_signal",
            "wifi_rssi",
            "wifi_status",
            "cloud_status",
            "last_disconnect_reason",
            "last_cloud_error",
            "fan_profile",
            "automation_mode",
        ]
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
        elif key == "operating_phase":
            self._attr_device_class = SensorDeviceClass.ENUM
            self._attr_options = [*dict.fromkeys(OPERATING_PHASE_NAMES.values()), "unrecognized"]
            self._attr_icon = "mdi:fire"
        elif key == "wifi_status":
            self._attr_device_class = SensorDeviceClass.ENUM
            self._attr_options = [*WIFI_STATUS_NAMES.values(), "unrecognized"]
            self._attr_entity_category = EntityCategory.DIAGNOSTIC
            self._attr_icon = "mdi:wifi-cog"
        elif key == "cloud_status":
            self._attr_device_class = SensorDeviceClass.ENUM
            self._attr_options = [*CLOUD_STATUS_NAMES.values(), "unrecognized"]
            self._attr_entity_category = EntityCategory.DIAGNOSTIC
            self._attr_icon = "mdi:cloud-check"
        elif key == "wifi_rssi":
            self._attr_device_class = SensorDeviceClass.SIGNAL_STRENGTH
            self._attr_native_unit_of_measurement = SIGNAL_STRENGTH_DECIBELS_MILLIWATT
            self._attr_state_class = SensorStateClass.MEASUREMENT
            self._attr_entity_category = EntityCategory.DIAGNOSTIC
        elif key == "wifi_signal":
            self._attr_entity_category = EntityCategory.DIAGNOSTIC
            self._attr_icon = "mdi:wifi"
        elif key in ("alarm_code", "last_disconnect_reason", "last_cloud_error"):
            self._attr_entity_category = EntityCategory.DIAGNOSTIC
            self._attr_icon = "mdi:alert-circle-outline"
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
        if self.key == "operating_phase":
            return OPERATING_PHASE_NAMES.get(value, "unrecognized")
        if self.key == "wifi_status":
            return WIFI_STATUS_NAMES.get(value, "unrecognized")
        if self.key == "cloud_status":
            return CLOUD_STATUS_NAMES.get(value, "unrecognized")
        if self.key == "air" and value is not None:
            return value / self.coordinator.settings[CONF_AIR_DIVISOR]
        return value

    @property
    def extra_state_attributes(self):
        raw_keys = {
            "status": "raw_status",
            "operating_phase": "raw_phase",
            "wifi_status": "raw_status",
            "cloud_status": "raw_status",
        }
        if attribute := raw_keys.get(self.key):
            return {attribute: getattr(self.coordinator.data, self.key)}
        return None
