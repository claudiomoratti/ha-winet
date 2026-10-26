"""Native thermostat entity. The stove retains control of combustion."""

from homeassistant.components.climate import ClimateEntity, ClimateEntityFeature, HVACMode
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.exceptions import ServiceValidationError

from .const import CONF_AIR_DIVISOR, CONF_DUAL_FAN, CONF_MAX_POWER
from .entity import WinetEntity


async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities([WinetClimate(entry.runtime_data)])


class WinetClimate(WinetEntity, ClimateEntity):
    _attr_name = None
    _attr_icon = "mdi:fire"
    _attr_translation_key = "stove"
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_min_temp = 5
    _attr_max_temp = 40
    _attr_target_temperature_step = 0.5
    _attr_hvac_modes = [HVACMode.OFF, HVACMode.HEAT]
    _attr_supported_features = (
        ClimateEntityFeature.TARGET_TEMPERATURE
        | ClimateEntityFeature.TURN_ON
        | ClimateEntityFeature.TURN_OFF
        | ClimateEntityFeature.PRESET_MODE
    )

    def __init__(self, coordinator):
        super().__init__(coordinator, "climate")
        self._power_presets = {
            f"power_{level}": level for level in range(1, coordinator.settings[CONF_MAX_POWER] + 1)
        }
        self._attr_preset_modes = list(self._power_presets)
        self._fan_pairs = {}
        if coordinator.settings[CONF_DUAL_FAN]:
            self._attr_supported_features |= ClimateEntityFeature.FAN_MODE
            self._fan_pairs = {
                f"fans_{first}_{second}": (first, second)
                for first in range(1, 5)
                for second in range(1, 5)
            }
            self._attr_fan_modes = list(self._fan_pairs)

    @property
    def fan_mode(self):
        """Represent both independent speeds in HA's single native fan selector."""
        state = self.coordinator.data
        mode = f"fans_{state.fan_1}_{state.fan_2}"
        return mode if mode in self._fan_pairs else None

    async def async_set_fan_mode(self, fan_mode):
        if fan_mode not in self._fan_pairs:
            raise ServiceValidationError("Unsupported fan combination")
        first, second = self._fan_pairs[fan_mode]
        await self.coordinator.async_set_fan_speeds(fan_1=first, fan_2=second)

    @property
    def preset_mode(self):
        """Use the shared device snapshot, including changes made outside HA."""
        return next(
            (
                preset
                for preset, level in self._power_presets.items()
                if level == self.coordinator.data.power
            ),
            None,
        )

    async def async_set_preset_mode(self, preset_mode):
        """Set only combustion power; preserve temperature and on/off state."""
        if preset_mode not in self._power_presets:
            raise ServiceValidationError("Unsupported power preset")
        await self.coordinator.async_command("power", self._power_presets[preset_mode])

    @property
    def current_temperature(self):
        value = self.coordinator.data.air
        return None if value is None else value / self.coordinator.settings[CONF_AIR_DIVISOR]

    @property
    def target_temperature(self):
        value = self.coordinator.data.set_air
        return None if value is None else value / self.coordinator.settings[CONF_AIR_DIVISOR]

    @property
    def hvac_mode(self):
        status = self.coordinator.data.status
        if status == 1:
            return HVACMode.HEAT
        if status in (0, 2):
            return HVACMode.OFF
        return None

    # hvac_action intentionally unset: status=1 does not distinguish ignition,
    # modulation, standby or established combustion across stove firmwares.

    async def async_set_temperature(self, **kwargs):
        if kwargs.get("hvac_mode") not in (None, self.hvac_mode):
            raise ServiceValidationError("Set HVAC mode in a separate action")
        if ATTR_TEMPERATURE not in kwargs:
            raise ServiceValidationError("Temperature is required")
        await self.coordinator.async_command("temperature/air", kwargs[ATTR_TEMPERATURE])

    async def async_set_hvac_mode(self, hvac_mode):
        if hvac_mode not in self.hvac_modes:
            raise ServiceValidationError("Unsupported HVAC mode")
        await self.coordinator.async_command("status", 1 if hvac_mode == HVACMode.HEAT else 0)

    async def async_turn_on(self):
        await self.async_set_hvac_mode(HVACMode.HEAT)

    async def async_turn_off(self):
        await self.async_set_hvac_mode(HVACMode.OFF)
