"""UI setup, options and address reconfiguration for WiNet."""

from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_HOST
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import InvalidDevice, WinetClient, WinetError, normalize_host
from .const import (
    CONF_AIR_DIVISOR,
    CONF_DUAL_FAN,
    CONF_HYDRO,
    CONF_INTERVAL,
    CONF_MAX_POWER,
    CONF_READ_ONLY,
    DEFAULTS,
    DOMAIN,
)


def settings_schema(current):
    values = DEFAULTS | dict(current)
    return vol.Schema(
        {
            vol.Required(CONF_AIR_DIVISOR, default=values[CONF_AIR_DIVISOR]): vol.In([1, 2]),
            vol.Required(CONF_MAX_POWER, default=values[CONF_MAX_POWER]): vol.In([5, 9]),
            vol.Required(CONF_HYDRO, default=values[CONF_HYDRO]): bool,
            vol.Required(CONF_DUAL_FAN, default=values[CONF_DUAL_FAN]): bool,
            vol.Required(CONF_READ_ONLY, default=values[CONF_READ_ONLY]): bool,
            vol.Required(CONF_INTERVAL, default=values[CONF_INTERVAL]): vol.All(
                vol.Coerce(int), vol.Range(min=10, max=300)
            ),
        }
    )


class WinetConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Set up a stove with a stable MAC identity."""

    VERSION = 1

    async def _validate(self, user_input):
        host = normalize_host(user_input[CONF_HOST])
        client = WinetClient(async_get_clientsession(self.hass), host)
        identity = await client.identify()
        await client.read()
        return host, identity

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            try:
                host, identity = await self._validate(user_input)
            except ValueError:
                errors[CONF_HOST] = "invalid_host"
            except InvalidDevice:
                errors["base"] = "unsupported_device"
            except WinetError:
                errors["base"] = "cannot_connect"
            else:
                await self.async_set_unique_id(identity["mac"])
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title="WiNet Stove",
                    data={CONF_HOST: host},
                    options={key: user_input[key] for key in DEFAULTS},
                )
        schema = settings_schema(user_input or {}).extend({vol.Required(CONF_HOST): str})
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    async def async_step_reconfigure(self, user_input=None):
        entry = self._get_reconfigure_entry()
        errors = {}
        if user_input is not None:
            try:
                host, identity = await self._validate(user_input)
            except ValueError:
                errors[CONF_HOST] = "invalid_host"
            except InvalidDevice:
                errors["base"] = "unsupported_device"
            except WinetError:
                errors["base"] = "cannot_connect"
            else:
                if identity["mac"] != entry.unique_id:
                    errors["base"] = "wrong_device"
                else:
                    return self.async_update_reload_and_abort(entry, data_updates={CONF_HOST: host})
        return self.async_show_form(
            step_id="reconfigure",
            data_schema=vol.Schema({vol.Required(CONF_HOST, default=entry.data[CONF_HOST]): str}),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return WinetOptionsFlow()


class WinetOptionsFlow(config_entries.OptionsFlow):
    async def async_step_init(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)
        return self.async_show_form(
            step_id="init", data_schema=settings_schema(self.config_entry.options)
        )
