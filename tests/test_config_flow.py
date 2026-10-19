"""Setup, duplicate protection and option persistence."""

from unittest.mock import AsyncMock, patch

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResultType

from custom_components.winet.const import DEFAULTS

from .conftest import HOST, MAC


async def test_setup_flow(hass, api_mock):
    with patch("custom_components.winet.async_setup_entry", new=AsyncMock(return_value=True)):
        result = await hass.config_entries.flow.async_init(
            "winet", context={"source": config_entries.SOURCE_USER}
        )
        assert result["type"] is FlowResultType.FORM
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"host": HOST} | DEFAULTS
        )
        assert result["type"] is FlowResultType.CREATE_ENTRY
        assert result["result"].unique_id == MAC
        assert result["data"] == {"host": HOST}
        assert result["options"]["read_only"] is True


async def test_duplicate(hass, entry, api_mock):
    result = await hass.config_entries.flow.async_init(
        "winet", context={"source": "user"}, data={"host": HOST} | DEFAULTS
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_invalid_host(hass):
    result = await hass.config_entries.flow.async_init(
        "winet", context={"source": "user"}, data={"host": "http://bad/path"} | DEFAULTS
    )
    assert result["errors"] == {"host": "invalid_host"}


async def test_unreachable(hass, aioclient_mock):
    aioclient_mock.get(f"http://{HOST}/api/id", exc=TimeoutError)
    result = await hass.config_entries.flow.async_init(
        "winet", context={"source": "user"}, data={"host": HOST} | DEFAULTS
    )
    assert result["errors"] == {"base": "cannot_connect"}


async def test_options(hass, entry):
    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], DEFAULTS | {"max_power": 9}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options["max_power"] == 9


async def test_reconfigure_wrong_device(hass, entry, aioclient_mock):
    aioclient_mock.get(
        "http://other.test/api/id", json={"id": "WiNET Gen.Stove", "mac": "112233445566"}
    )
    aioclient_mock.get("http://other.test/api/global", json={"status": 0})
    result = await hass.config_entries.flow.async_init(
        "winet",
        context={"source": "reconfigure", "entry_id": entry.entry_id},
        data={"host": "other.test"},
    )
    assert result["errors"] == {"base": "wrong_device"}
    assert entry.data["host"] == HOST


async def test_reconfigure_same_device(hass, entry, aioclient_mock):
    from .conftest import GLOBAL, IDENTITY

    aioclient_mock.get("http://new-stove.test/api/id", json=IDENTITY)
    aioclient_mock.get("http://new-stove.test/api/global", json=GLOBAL)
    with patch(
        "homeassistant.config_entries.ConfigEntries.async_reload", new=AsyncMock(return_value=True)
    ):
        result = await hass.config_entries.flow.async_init(
            "winet",
            context={"source": "reconfigure", "entry_id": entry.entry_id},
            data={"host": "new-stove.test"},
        )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    assert entry.data["host"] == "new-stove.test"
