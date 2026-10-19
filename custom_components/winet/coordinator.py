"""Shared polling and serialized, explicitly enabled writes."""

from __future__ import annotations

import asyncio
import logging
import math
from datetime import timedelta

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import StoveState, WinetClient, WinetError
from .const import (
    CONF_AIR_DIVISOR,
    CONF_HYDRO,
    CONF_INTERVAL,
    CONF_MAX_POWER,
    CONF_READ_ONLY,
    DEFAULTS,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


class WinetCoordinator(DataUpdateCoordinator[StoveState]):
    """One snapshot for all entities, refreshed after successful commands."""

    def __init__(self, hass: HomeAssistant, entry, client: WinetClient, identity: dict) -> None:
        self.client = client
        self.identity = identity
        self.settings = DEFAULTS | dict(entry.options)
        self._io_lock = asyncio.Lock()
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            config_entry=entry,
            update_interval=timedelta(seconds=self.settings[CONF_INTERVAL]),
            always_update=False,
        )

    async def _async_update_data(self) -> StoveState:
        try:
            async with self._io_lock:
                return await self.client.read()
        except WinetError as err:
            raise UpdateFailed(str(err)) from err

    async def async_command(self, path: str, value: float | int) -> None:
        """Validate first, send once, then read back; never assume final state."""
        if self.settings[CONF_READ_ONLY]:
            raise ServiceValidationError(
                "WiNet is in read-only mode. Enable commands in integration options."
            )
        if not self.last_update_success:
            raise HomeAssistantError("WiNet is unavailable")
        if (
            isinstance(value, bool)
            or not isinstance(value, (float, int))
            or not math.isfinite(value)
        ):
            raise ServiceValidationError("Invalid WiNet value")
        if path == "status":
            if value not in (0, 1):
                raise ServiceValidationError("Unsupported stove command")
        elif path == "power":
            if not 1 <= value <= self.settings[CONF_MAX_POWER] or value != int(value):
                raise ServiceValidationError("Power is outside the configured range")
        elif path == "temperature/air":
            if not 5 <= value <= 40 or not math.isclose(value * 2, round(value * 2)):
                raise ServiceValidationError("Air setpoint must be 5–40 °C in steps of 0.5 °C")
            value *= self.settings[CONF_AIR_DIVISOR]
        elif path == "temperature/water":
            if not self.settings[CONF_HYDRO] or not 40 <= value <= 80 or value != int(value):
                raise ServiceValidationError("Water setpoint requires hydro mode and 40–80 °C")
        else:
            raise ServiceValidationError("Unsupported WiNet command")
        try:
            async with self._io_lock:
                if path == "status" and value == 1:
                    # Check a fresh snapshot, not an old cached off state.
                    state = await self.client.read()
                    self.async_set_updated_data(state)
                    if state.status == 1:
                        return
                    if state.status != 0:
                        raise ServiceValidationError(
                            "Cannot start during cleaning, alarm or an unknown state"
                        )
                await self.client.command(path, value)
        except WinetError as err:
            # A timeout does not prove that a write was not applied. Do not retry.
            await self.async_request_refresh()
            raise HomeAssistantError(
                "WiNet command failed or its outcome is uncertain; check the stove state"
            ) from err
        await self.async_request_refresh()
        if not self.last_update_success:
            raise HomeAssistantError(
                "WiNet accepted the command, but reading back its state failed"
            )
