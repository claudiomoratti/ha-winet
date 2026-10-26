"""WiNet local stove integration."""

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryError, ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import InvalidDevice, WinetClient, WinetError
from .const import CONF_DUAL_FAN, PLATFORMS
from .coordinator import WinetCoordinator


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Connect without writing any device settings."""
    client = WinetClient(
        async_get_clientsession(hass),
        entry.data[CONF_HOST],
        dual_fan=entry.options.get(CONF_DUAL_FAN, False),
    )
    try:
        identity = await client.identify()
    except InvalidDevice as err:
        raise ConfigEntryError(str(err)) from err
    except WinetError as err:
        raise ConfigEntryNotReady(str(err)) from err
    if identity["mac"] != entry.unique_id:
        raise ConfigEntryError("A different WiNet device is now using this address")
    coordinator = WinetCoordinator(hass, entry, client, identity)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))
    return True


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Apply options with a clean reload."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload entities and their coordinator listeners."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
