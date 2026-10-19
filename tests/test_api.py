"""Protocol behavior and hostile/malformed responses."""

import pytest
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from custom_components.winet.api import (
    InvalidDevice,
    StoveState,
    WinetClient,
    WinetError,
    normalize_host,
)

from .conftest import GLOBAL, HOST, MAC


@pytest.mark.parametrize(
    "host",
    [
        "http://stove",
        "stove/path",
        "user:password@stove",
        "stove?x=1",
        "",
        "stove:99999",
        "stove name",
    ],
)
def test_invalid_host(host):
    with pytest.raises(ValueError):
        normalize_host(host)


@pytest.mark.parametrize("host", ["stove.local", "192.0.2.1", "stove.local:8080", "[::1]:8080"])
def test_valid_host(host):
    assert normalize_host(host) == host


def test_nulls_and_case_alias():
    state = StoveState.parse(GLOBAL | {"gasflue": None, "power": False})
    assert state.rpm_extractor is None
    assert state.gasflue is None
    assert state.power is None
    data = {k: v for k, v in GLOBAL.items() if k != "gasflue"}
    assert StoveState.parse(data | {"gasFlue": 24}).gasflue == 24


@pytest.mark.parametrize("status", [None, True, "0", 1.5])
def test_invalid_status(status):
    with pytest.raises(WinetError):
        StoveState.parse(GLOBAL | {"status": status})


async def test_identity_is_allowlisted(hass, api_mock):
    client = WinetClient(async_get_clientsession(hass), HOST)
    assert await client.identify() == {"model": "WiNET Gen.Stove", "mac": MAC}
    assert (await client.read()).air == 35


async def test_blower_is_not_a_stove(hass, aioclient_mock):
    aioclient_mock.get(f"http://{HOST}/api/id", json={"id": "WiNET Blower Cube", "mac": MAC})
    with pytest.raises(InvalidDevice):
        await WinetClient(async_get_clientsession(hass), HOST).identify()


@pytest.mark.parametrize("response", [{"result": False}, {"result": 1}, {}, {"result": "true"}])
async def test_command_rejected(hass, aioclient_mock, response):
    aioclient_mock.get(f"http://{HOST}/api/power/3", json=response)
    with pytest.raises(WinetError):
        await WinetClient(async_get_clientsession(hass), HOST).command("power", 3)
    assert aioclient_mock.call_count == 1


async def test_timeout_not_retried(hass, aioclient_mock):
    aioclient_mock.get(f"http://{HOST}/api/status/1", exc=TimeoutError)
    with pytest.raises(WinetError):
        await WinetClient(async_get_clientsession(hass), HOST).command("status", 1)
    assert aioclient_mock.call_count == 1


@pytest.mark.parametrize("payload", ["not json", "[]"])
async def test_invalid_response(hass, aioclient_mock, payload):
    aioclient_mock.get(f"http://{HOST}/api/global", text=payload)
    with pytest.raises(WinetError):
        await WinetClient(async_get_clientsession(hass), HOST).read()


@pytest.mark.parametrize("code", [301, 403, 500])
async def test_http_errors(hass, aioclient_mock, code):
    aioclient_mock.get(f"http://{HOST}/api/global", status=code)
    with pytest.raises(WinetError):
        await WinetClient(async_get_clientsession(hass), HOST).read()
    assert aioclient_mock.call_count == 1
