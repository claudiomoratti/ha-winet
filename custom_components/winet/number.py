"""Native power and optional hydro setpoint controls."""

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.const import UnitOfTemperature

from .const import CONF_DUAL_FAN, CONF_HYDRO, CONF_MAX_POWER
from .entity import WinetEntity


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = entry.runtime_data
    entities = [WinetNumber(coordinator, "power")]
    if coordinator.settings[CONF_HYDRO]:
        entities.append(WinetNumber(coordinator, "set_water"))
    if coordinator.settings[CONF_DUAL_FAN]:
        entities.extend(WinetFanSpeed(coordinator, f"fan_{fan}") for fan in (1, 2))
    async_add_entities(entities)


class WinetNumber(WinetEntity, NumberEntity):
    _attr_mode = NumberMode.BOX
    _attr_native_step = 1

    def __init__(self, coordinator, key):
        super().__init__(coordinator, key)
        self.key = key
        self._attr_translation_key = key
        if key == "power":
            self._attr_native_min_value = 1
            self._attr_native_max_value = coordinator.settings[CONF_MAX_POWER]
            self._attr_icon = "mdi:fire"
        else:
            self._attr_native_min_value = 40
            self._attr_native_max_value = 80
            self._attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
            self._attr_icon = "mdi:water-thermometer"

    @property
    def native_value(self):
        return getattr(self.coordinator.data, self.key)

    async def async_set_native_value(self, value):
        path = "power" if self.key == "power" else "temperature/water"
        await self.coordinator.async_command(path, value)


class WinetFanSpeed(WinetEntity, NumberEntity):
    """An independent 1–4 speed, without inventing an off or automatic mode."""

    _attr_mode = NumberMode.SLIDER
    _attr_native_min_value = 1
    _attr_native_max_value = 4
    _attr_native_step = 1
    _attr_icon = "mdi:fan"

    def __init__(self, coordinator, key):
        super().__init__(coordinator, key)
        self.key = key
        self._attr_translation_key = key

    @property
    def available(self):
        return super().available and self.native_value is not None

    @property
    def native_value(self):
        return getattr(self.coordinator.data, self.key)

    async def async_set_native_value(self, value):
        await self.coordinator.async_set_fan_speeds(**{self.key: value})
