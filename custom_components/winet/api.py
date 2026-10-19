"""Small async client for the WiNet local API. No automatic write retries."""

from __future__ import annotations

import asyncio
import ipaddress
import math
import re
from dataclasses import dataclass
from typing import Any

import aiohttp
from yarl import URL


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

    def __init__(self, session: aiohttp.ClientSession, host: str) -> None:
        self.session = session
        self.host = normalize_host(host)

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
        return StoveState.parse(await self._get("global"))

    async def command(self, path: str, value: float | int) -> None:
        if path not in {"status", "power", "temperature/air", "temperature/water"}:
            raise ValueError("Unsupported command")
        if number(value) is None:
            raise ValueError("Invalid command value")
        result = await self._get(f"{path}/{value:g}")
        if result.get("result") is not True:
            raise WinetError("WiNet rejected the command")
