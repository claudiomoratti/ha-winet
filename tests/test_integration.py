"""Real HA setup and services with an entirely mocked device."""

import json
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers import entity_registry as er

from custom_components.winet.api import StoveState, WinetError
from custom_components.winet.diagnostics import async_get_config_entry_diagnostics

from .conftest import GLOBAL, MAC


def entity_id(hass, domain, key):
    return er.async_get(hass).async_get_entity_id(domain, "winet", f"{MAC}_{key}")


async def setup(hass, entry):
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry.runtime_data


async def test_native_entities_and_unload(hass, entry, api_mock):
    coordinator = await setup(hass, entry)
    climate = hass.states.get(entity_id(hass, "climate", "climate"))
    assert climate.state == "off"
    assert climate.attributes["current_temperature"] == 17.5
    assert climate.attributes["temperature"] == 19
    assert hass.states.get(entity_id(hass, "number", "power")).state == "5.0"
    assert hass.states.get(entity_id(hass, "sensor", "rpm_extractor")).state == "unknown"
    assert hass.states.get(entity_id(hass, "sensor", "gasflue")).state == "0.0"
    assert entity_id(hass, "number", "set_water") is None
    assert api_mock.call_count == 2  # Shared snapshot, not one poll per entity.
    diagnostics = await async_get_config_entry_diagnostics(hass, entry)
    assert "never-export-this" not in json.dumps(diagnostics)
    assert MAC not in json.dumps(diagnostics)
    assert coordinator.identity == {"model": "WiNET Gen.Stove", "mac": MAC}
    assert await hass.config_entries.async_unload(entry.entry_id)
    assert hass.states.get(climate.entity_id).state == "unavailable"
    assert not list(coordinator.async_contexts())


async def test_read_only_services(hass, entry, api_mock):
    await setup(hass, entry)
    with pytest.raises(ServiceValidationError, match="read-only"):
        await hass.services.async_call(
            "climate",
            "turn_on",
            {"entity_id": entity_id(hass, "climate", "climate")},
            blocking=True,
        )
    with pytest.raises(ServiceValidationError, match="read-only"):
        await hass.services.async_call(
            "number",
            "set_value",
            {"entity_id": entity_id(hass, "number", "power"), "value": 3},
            blocking=True,
        )
    with pytest.raises(ServiceValidationError, match="read-only"):
        await hass.services.async_call(
            "climate",
            "set_preset_mode",
            {"entity_id": entity_id(hass, "climate", "climate"), "preset_mode": "power_3"},
            blocking=True,
        )
    assert api_mock.call_count == 2


@pytest.mark.parametrize("max_power", [5, 9])
async def test_power_presets_follow_config_and_device(hass, entry, api_mock, max_power):
    hass.config_entries.async_update_entry(entry, options=entry.options | {"max_power": max_power})
    coordinator = await setup(hass, entry)
    climate_id = entity_id(hass, "climate", "climate")
    assert hass.states.get(climate_id).attributes["preset_modes"] == [
        f"power_{level}" for level in range(1, max_power + 1)
    ]
    for power in [1, max_power, None, 0, max_power + 1]:
        coordinator.async_set_updated_data(StoveState.parse(GLOBAL | {"power": power}))
        climate = hass.states.get(climate_id)
        expected = f"power_{power}" if power is not None and 1 <= power <= max_power else None
        assert climate.attributes.get("preset_mode") == expected
        assert climate.state == "off"
        assert climate.attributes["temperature"] == 19


@pytest.mark.parametrize("max_power,level", [(5, 1), (5, 5), (9, 9)])
async def test_set_power_preset_and_number_stay_synchronized(
    hass, entry, api_mock, max_power, level
):
    hass.config_entries.async_update_entry(
        entry, options=entry.options | {"read_only": False, "max_power": max_power}
    )
    coordinator = await setup(hass, entry)
    climate_id = entity_id(hass, "climate", "climate")
    power_id = entity_id(hass, "number", "power")
    with (
        patch.object(coordinator.client, "command", new_callable=AsyncMock) as command,
        patch.object(
            coordinator.client,
            "read",
            new=AsyncMock(return_value=StoveState.parse(GLOBAL | {"power": level})),
        ),
    ):
        await hass.services.async_call(
            "climate",
            "set_preset_mode",
            {"entity_id": climate_id, "preset_mode": f"power_{level}"},
            blocking=True,
        )
        command.assert_awaited_once_with("power", level)
    assert hass.states.get(power_id).state == f"{level}.0"
    assert hass.states.get(climate_id).attributes["preset_mode"] == f"power_{level}"
    assert hass.states.get(climate_id).state == "off"
    assert hass.states.get(climate_id).attributes["temperature"] == 19
    with (
        patch.object(coordinator.client, "command", new_callable=AsyncMock) as command,
        patch.object(
            coordinator.client, "read", new=AsyncMock(return_value=StoveState.parse(GLOBAL))
        ),
    ):
        await hass.services.async_call(
            "number",
            "set_value",
            {"entity_id": power_id, "value": 5},
            blocking=True,
        )
        command.assert_awaited_once_with("power", 5)
    assert hass.states.get(climate_id).attributes["preset_mode"] == "power_5"


@pytest.mark.parametrize("preset", ["power_0", "power_6", "power_9", "eco", "power_2.5"])
async def test_invalid_power_preset_never_sends_command(hass, entry, api_mock, preset):
    hass.config_entries.async_update_entry(entry, options=entry.options | {"read_only": False})
    coordinator = await setup(hass, entry)
    with patch.object(coordinator.client, "command", new_callable=AsyncMock) as command:
        with pytest.raises(ServiceValidationError):
            await hass.services.async_call(
                "climate",
                "set_preset_mode",
                {"entity_id": entity_id(hass, "climate", "climate"), "preset_mode": preset},
                blocking=True,
            )
        command.assert_not_awaited()


async def test_power_preset_uses_readback_instead_of_requested_value(hass, entry, api_mock):
    hass.config_entries.async_update_entry(entry, options=entry.options | {"read_only": False})
    coordinator = await setup(hass, entry)
    with patch.object(coordinator.client, "command", new_callable=AsyncMock) as command:
        await hass.services.async_call(
            "climate",
            "set_preset_mode",
            {"entity_id": entity_id(hass, "climate", "climate"), "preset_mode": "power_3"},
            blocking=True,
        )
        command.assert_awaited_once_with("power", 3)
    assert (
        hass.states.get(entity_id(hass, "climate", "climate")).attributes["preset_mode"]
        == "power_5"
    )
    assert hass.states.get(entity_id(hass, "number", "power")).state == "5.0"


async def test_conversion_and_readback(hass, entry, api_mock):
    hass.config_entries.async_update_entry(entry, options=entry.options | {"read_only": False})
    coordinator = await setup(hass, entry)
    with (
        patch.object(coordinator.client, "command", new_callable=AsyncMock) as command,
        patch.object(
            coordinator.client,
            "read",
            new=AsyncMock(return_value=StoveState.parse(GLOBAL | {"setAir": 41})),
        ),
    ):
        await hass.services.async_call(
            "climate",
            "set_temperature",
            {"entity_id": entity_id(hass, "climate", "climate"), "temperature": 20.5},
            blocking=True,
        )
        command.assert_awaited_once_with("temperature/air", 41.0)
    assert hass.states.get(entity_id(hass, "climate", "climate")).attributes["temperature"] == 20.5


@pytest.mark.parametrize("status", [2, 3, 4, 99])
async def test_start_blocked(hass, entry, api_mock, status):
    hass.config_entries.async_update_entry(entry, options=entry.options | {"read_only": False})
    coordinator = await setup(hass, entry)
    with (
        patch.object(
            coordinator.client,
            "read",
            new=AsyncMock(return_value=StoveState.parse(GLOBAL | {"status": status})),
        ),
        patch.object(coordinator.client, "command", new_callable=AsyncMock) as command,
    ):
        with pytest.raises(ServiceValidationError):
            await coordinator.async_command("status", 1)
        command.assert_not_awaited()


@pytest.mark.parametrize(
    "path,value",
    [
        ("power", 0),
        ("power", 6),
        ("power", 2.5),
        ("temperature/air", 41),
        ("temperature/air", 19.1),
        ("temperature/water", 50),
        ("status", 2),
        ("power", float("nan")),
    ],
)
async def test_invalid_commands(hass, entry, api_mock, path, value):
    hass.config_entries.async_update_entry(entry, options=entry.options | {"read_only": False})
    coordinator = await setup(hass, entry)
    with patch.object(coordinator.client, "command", new_callable=AsyncMock) as command:
        with pytest.raises(ServiceValidationError):
            await coordinator.async_command(path, value)
        command.assert_not_awaited()


async def test_failure_recovery(hass, entry, api_mock):
    coordinator = await setup(hass, entry)
    with patch.object(coordinator.client, "read", new=AsyncMock(side_effect=WinetError("offline"))):
        await coordinator.async_refresh()
    assert hass.states.get(entity_id(hass, "climate", "climate")).state == "unavailable"
    await coordinator.async_refresh()
    assert hass.states.get(entity_id(hass, "climate", "climate")).state == "off"


async def test_hydro_and_direct_degrees(hass, entry, api_mock):
    hass.config_entries.async_update_entry(
        entry, options=entry.options | {"hydro": True, "air_divisor": 1, "read_only": False}
    )
    coordinator = await setup(hass, entry)
    assert hass.states.get(entity_id(hass, "climate", "climate")).attributes["temperature"] == 38
    assert hass.states.get(entity_id(hass, "number", "set_water")).state == "unknown"
    with patch.object(coordinator.client, "command", new_callable=AsyncMock) as command:
        await coordinator.async_command("temperature/water", 65)
        command.assert_awaited_once_with("temperature/water", 65)


async def test_write_error_not_retried(hass, entry, api_mock):
    hass.config_entries.async_update_entry(entry, options=entry.options | {"read_only": False})
    coordinator = await setup(hass, entry)
    with patch.object(
        coordinator.client, "command", new=AsyncMock(side_effect=WinetError("timeout"))
    ) as command:
        with pytest.raises(HomeAssistantError, match="uncertain"):
            await coordinator.async_command("power", 3)
        command.assert_awaited_once()


async def test_unknown_state_is_not_off(hass, entry, api_mock):
    coordinator = await setup(hass, entry)
    coordinator.async_set_updated_data(StoveState.parse(GLOBAL | {"status": 99}))
    assert hass.states.get(entity_id(hass, "climate", "climate")).state == "unknown"
    assert hass.states.get(entity_id(hass, "binary_sensor", "alarm")).state == "unknown"
    assert hass.states.get(entity_id(hass, "sensor", "status")).state == "unrecognized"


async def test_start_and_already_on(hass, entry, api_mock):
    hass.config_entries.async_update_entry(entry, options=entry.options | {"read_only": False})
    coordinator = await setup(hass, entry)
    with patch.object(coordinator.client, "command", new_callable=AsyncMock) as command:
        await coordinator.async_command("status", 1)
        command.assert_awaited_once_with("status", 1)
    with (
        patch.object(
            coordinator.client,
            "read",
            new=AsyncMock(return_value=StoveState.parse(GLOBAL | {"status": 1})),
        ),
        patch.object(coordinator.client, "command", new_callable=AsyncMock) as command,
    ):
        await coordinator.async_command("status", 1)
        command.assert_not_awaited()


async def test_successful_write_failed_readback(hass, entry, api_mock):
    hass.config_entries.async_update_entry(entry, options=entry.options | {"read_only": False})
    coordinator = await setup(hass, entry)
    with (
        patch.object(coordinator.client, "command", new_callable=AsyncMock) as command,
        patch.object(coordinator.client, "read", new=AsyncMock(side_effect=WinetError("offline"))),
    ):
        with pytest.raises(HomeAssistantError, match="accepted"):
            await coordinator.async_command("power", 3)
        command.assert_awaited_once()
    assert hass.states.get(entity_id(hass, "climate", "climate")).state == "unavailable"


async def test_identity_changed(hass, entry, aioclient_mock):
    from .conftest import HOST

    aioclient_mock.get(
        f"http://{HOST}/api/id", json={"id": "WiNET Gen.Stove", "mac": "112233445566"}
    )
    assert not await hass.config_entries.async_setup(entry.entry_id)
    assert aioclient_mock.call_count == 1
