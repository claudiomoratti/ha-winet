"""Constants for WiNet local stove control."""

from homeassistant.const import Platform

DOMAIN = "winet"
PLATFORMS = [Platform.CLIMATE, Platform.NUMBER, Platform.SENSOR, Platform.BINARY_SENSOR]
CONF_AIR_DIVISOR = "air_divisor"
CONF_MAX_POWER = "max_power"
CONF_HYDRO = "hydro"
CONF_DUAL_FAN = "dual_fan"
DUAL_FAN_PROFILE = 27436
CONF_READ_ONLY = "read_only"
CONF_INTERVAL = "poll_interval"
DEFAULTS = {
    CONF_AIR_DIVISOR: 2,
    CONF_MAX_POWER: 5,
    CONF_HYDRO: False,
    CONF_DUAL_FAN: False,
    CONF_READ_ONLY: True,
    CONF_INTERVAL: 15,
}
STATUS_NAMES = {0: "off", 1: "on", 2: "final_cleaning", 3: "alarm", 4: "unmanaged"}
