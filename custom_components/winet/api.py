"""Small async client for the WiNet local API. No automatic write retries."""

from __future__ import annotations

import asyncio
import ipaddress
import math
import re
from dataclasses import dataclass, replace
from typing import Any
from urllib.parse import urlencode

import aiohttp
from yarl import URL

from .const import DUAL_FAN_PROFILE


class WinetError(Exception):
    """A communication, response or command error without sensitive payloads."""


class InvalidDevice(WinetError):
    """The endpoint does not identify as a supported stove."""


def normalize_host(host: str) -> str:
    """Accept a host/IP and optional port, never credentials, paths or queries."""
    host = host.strip().lower()
    if not host or any(char in host for char in "/?#@\\") or any(c.isspace() for c in host):
        raise ValueError("Enter an IP address or hostname, optionally with a port")
    try:
        url = URL("http://" + host)
        hostname = url.host
        port = url.port
        if not hostname or port is None or not 1 <= port <= 65535:
            raise ValueError
        try:
            ipaddress.ip_address(hostname)
        except ValueError:
            if not re.fullmatch(r"[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?", hostname):
                raise ValueError
        address = f"[{hostname}]" if ":" in hostname else hostname
        return address if port == 80 else f"{address}:{port}"
    except (ValueError, TypeError) as err:
        raise ValueError("Invalid host or port") from err


def number(value: Any) -> float | None:
    """Preserve missing data; reject booleans, strings and non-finite numbers."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value) if math.isfinite(value) else None


@dataclass(frozen=True)
class StoveState:
    """Known fields only; arbitrary device data never reaches diagnostics."""

    status: int
    description: str
    air: float | None
    set_air: float | None
    water: float | None
    set_water: float | None
    power: float | None
    gasflue: float | None
    rpm_extractor: float | None
    fan_profile: int | None = None
    fan_1: int | None = None
    fan_2: int | None = None
    wifi_signal: int | None = None
    automation_mode: int | None = None
    operating_phase: int | None = None
    alarm_code: int | None = None
    wifi_rssi: int | None = None
    wifi_status: int | None = None
    cloud_status: int | None = None
    last_disconnect_reason: int | None = None
    last_cloud_error: int | None = None
    firmware_version: str | None = None

    def with_registers(self, data: dict[str, Any]) -> StoveState:
        """Read safe WiNet diagnostics and verified P937 registers."""
        profile = data.get("custom")
        profile = profile if type(profile) is int else None
        signal = data.get("signal")
        signal = signal if type(signal) is int and 0 <= signal <= 4 else None
        mode = data.get("mode")
        mode = mode if type(mode) is int and 0 <= mode <= 3 else None
        state = replace(
            self,
            fan_profile=profile,
            wifi_signal=signal,
            automation_mode=mode,
        )
        if profile != DUAL_FAN_PROFILE:
            return state
        params = data.get("params")
        if not isinstance(params, list):
            return state
        values = {}
        duplicates = set()
        for item in params:
            if not isinstance(item, list) or len(item) != 2:
                continue
            register, value = item
            if type(register) is not int or register not in (2, 3, 47, 48):
                continue
            if register in values:
                duplicates.add(register)
            values[register] = value if type(value) is int else None

        phase = values.get(2)
        phase = phase if phase is not None and 0 <= phase <= 255 else None
        alarm = values.get(3)
        alarm = alarm if alarm is not None and 0 <= alarm <= 255 else None

        def fan_value(register: int) -> int | None:
            value = values.get(register)
            return value if value is not None and 1 <= value <= 4 else None

        return replace(
            state,
            operating_phase=None if 2 in duplicates else phase,
            alarm_code=None if 3 in duplicates else alarm,
            fan_1=None if 47 in duplicates else fan_value(47),
            fan_2=None if 48 in duplicates else fan_value(48),
        )

    def with_module_status(self, data: dict[str, Any]) -> StoveState:
        """Read allowlisted health fields from the WiNet module status page."""

        def integer(key: str, allowed: set[int] | None = None) -> int | None:
            value = data.get(key)
            if type(value) is not int or (allowed is not None and value not in allowed):
                return None
            return value

        firmware = data.get("fwVer")
        if not isinstance(firmware, str) or not firmware or len(firmware) > 40:
            firmware = None
        module_signal = integer("signal", set(range(5)))
        return replace(
            self,
            wifi_signal=module_signal if module_signal is not None else self.wifi_signal,
            wifi_rssi=integer("rssi", set(range(-127, 1))),
            wifi_status=integer("status"),
            cloud_status=integer("client"),
            last_disconnect_reason=integer(
                "lastDisconnectReason",
                {*range(12), *range(13, 25), *range(200, 205)},
            ),
            last_cloud_error=integer(
                "lastCloudError",
                {0, -1, -3, -4, -5, -7, -8, -9, -10, -11, -12, -14, -15, -28, -61},
            ),
            firmware_version=firmware,
        )

    @classmethod
    def parse(cls, data: dict[str, Any]) -> StoveState:
        status = data.get("status")
        if isinstance(status, bool) or not isinstance(status, int):
            raise WinetError("Invalid stove status")
        description = data.get("description", "")
        if not isinstance(description, str):
            raise WinetError("Invalid stove description")
        return cls(
            status,
            description[:255],
            number(data.get("air")),
            number(data.get("setAir")),
            number(data.get("water")),
            number(data.get("setWater")),
            number(data.get("power")),
            number(data.get("gasflue", data.get("gasFlue"))),
            number(data.get("rpmExtractor")),
        )


class WinetClient:
    """HTTP API; GET paths with a value are writes, despite the HTTP method."""

    def __init__(self, session: aiohttp.ClientSession, host: str, *, dual_fan=False) -> None:
        self.session = session
        self.host = normalize_host(host)
        self.dual_fan = dual_fan

    async def _get(self, path: str) -> dict[str, Any]:
        try:
            async with asyncio.timeout(10):
                async with self.session.get(
                    f"http://{self.host}/api/{path}", allow_redirects=False
                ) as response:
                    if response.status != 200:
                        raise WinetError(f"WiNet HTTP error {response.status}")
                    data = await response.json(content_type=None)
        except (aiohttp.ClientError, TimeoutError, ValueError) as err:
            raise WinetError("Cannot read a valid response from WiNet") from err
        if not isinstance(data, dict):
            raise WinetError("WiNet response is not an object")
        return data

    async def _post(self, path: str, fields: dict[str, Any]) -> dict[str, Any]:
        """Match the web panel: form-encoded body with its JSON content type."""
        try:
            async with asyncio.timeout(10):
                async with self.session.post(
                    f"http://{self.host}/ajax/{path}",
                    data=urlencode(fields),
                    headers={"Content-Type": "application/json; charset=utf-8"},
                    allow_redirects=False,
                ) as response:
                    if response.status != 200:
                        raise WinetError(f"WiNet HTTP error {response.status}")
                    data = await response.json(content_type=None)
        except (aiohttp.ClientError, TimeoutError, ValueError) as err:
            raise WinetError("Cannot read a valid response from WiNet") from err
        if not isinstance(data, dict):
            raise WinetError("WiNet response is not an object")
        return data

    async def identify(self) -> dict[str, str]:
        data = await self._get("id")
        model, mac = data.get("id"), data.get("mac")
        if (
            not isinstance(model, str)
            or "winet" not in model.lower()
            or "stove" not in model.lower()
        ):
            raise InvalidDevice("Only WiNet Stove modules are supported")
        if not isinstance(mac, str):
            raise InvalidDevice("WiNet did not provide a device MAC")
        mac = re.sub(r"[:-]", "", mac).lower()
        if not re.fullmatch(r"[0-9a-f]{12}", mac):
            raise InvalidDevice("WiNet provided an invalid device MAC")
        # /id also contains the AP password. Keep only these two fields.
        return {"model": model[:100], "mac": mac}

    async def read(self) -> StoveState:
        state = StoveState.parse(await self._get("global"))
        if not self.dual_fan:
            return state
        try:
            registers = await self._post("get-registers", {"key": "020", "category": 0})
        except WinetError:
            # An auxiliary endpoint failure must not hide the main thermostat.
            pass
        else:
            state = state.with_registers(registers)
        try:
            module_status = await self._post("get-status", {})
        except WinetError:
            # Network diagnostics are optional and must not hide stove readings.
            return state
        return state.with_module_status(module_status)

    async def command_fan(self, fan: int, speed: int) -> None:
        """Write only the two verified logical registers; never change profiles."""
        if not self.dual_fan or type(fan) is not int or fan not in (1, 2):
            raise ValueError("Unsupported fan")
        if type(speed) is not int or not 1 <= speed <= 4:
            raise ValueError("Fan speed must be an integer from 1 to 4")
        result = await self._post(
            "set-register", {"key": "002", "memory": 1, "regId": 46 + fan, "value": speed}
        )
        if result.get("result") is not True:
            raise WinetError("WiNet rejected the fan command")

    async def command(self, path: str, value: float | int) -> None:
        if path not in {"status", "power", "temperature/air", "temperature/water"}:
            raise ValueError("Unsupported command")
        if number(value) is None:
            raise ValueError("Invalid command value")
        result = await self._get(f"{path}/{value:g}")
        if result.get("result") is not True:
            raise WinetError("WiNet rejected the command")
