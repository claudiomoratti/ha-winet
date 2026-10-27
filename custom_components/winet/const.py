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
AUTOMATION_MODE_NAMES = {
    0: "disabled",
    1: "temperature_thresholds",
    2: "weekly_schedule",
    3: "thresholds_in_schedule",
}
OPERATING_PHASE_NAMES = {
    0: "off",
    1: "waiting_flame",
    2: "waiting_flame",
    3: "ignition",
    4: "work",
    5: "standby",
    6: "final_cleaning",
    7: "brazier_cleaning",
    8: "alarm",
    9: "alarm_memory",
}
WIFI_STATUS_NAMES = {
    0: "idle",
    1: "connecting",
    2: "wrong_password",
    3: "access_point_not_found",
    4: "connection_failed",
    5: "connected",
    255: "not_in_station_mode",
}
CLOUD_STATUS_NAMES = {
    0: "idle",
    1: "paused",
    2: "connected",
    3: "disconnected",
}
