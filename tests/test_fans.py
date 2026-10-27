"""P937 wire format, native thermostat controls and failures, without a real stove."""

from dataclasses import replace
from unittest.mock import AsyncMock, call, patch

import pytest
from homeassistant.components.climate import ClimateEntityFeature
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from custom_components.winet.api import StoveState, WinetClient, WinetError

from .conftest import GLOBAL, HOST
from .test_integration import entity_id, setup

REGISTERS = {
    "custom": 27436,
    "params": [[47, 3], [48, 2]],
    "signal": 4,
    "mode": 0,
    "name": "not-for-diagnostics",
}


def fan_state(first=3, second=2):
    return StoveState.parse(GLOBAL).with_fans(
        {"custom": 27436, "params": [[47, first], [48, second]]}
    )


@pytest.fixture
async def fan_entry(hass, entry, api_mock):
    hass.config_entries.async_update_entry(
        entry, options=entry.options | {"dual_fan": True, "read_only": False}
    )
    api_mock.post(f"http://{HOST}/ajax/get-registers", json=REGISTERS)
    await setup(hass, entry)
    return entry


async def test_disabled_by_default(hass, entry, api_mock):
    await setup(hass, entry)
    climate = hass.states.get(entity_id(hass, "climate", "climate"))
    assert not climate.attributes["supported_features"] & ClimateEntityFeature.FAN_MODE
    assert "fan_modes" not in climate.attributes
    assert entity_id(hass, "number", "fan_1") is None
    assert all("/ajax/" not in str(url) for _, url, _, _ in api_mock.mock_calls)


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"custom": 27437, "params": [[47, 3], [48, 2]]},
        {"custom": "27436", "params": [[47, 3], [48, 2]]},
        {"custom": 27436, "params": None},
        {"custom": 27436, "params": [[47, True], [48, 0]]},
        {"custom": 27436, "params": [[47, 1.5], [48, 5]]},
        {"custom": 27436, "params": [[47, 3], [47, 2], [48, 1], [48, 2]]},
        {"custom": 27436, "params": [[47], None, {}, [[], 4], ["47", 3]]},
    ],
)
def test_invalid_or_unsupported_registers_stay_unknown(payload):
    state = StoveState.parse(GLOBAL).with_fans(payload)
    assert state.fan_1 is None
    assert state.fan_2 is None
    assert state.power == GLOBAL["power"]


async def test_exact_read_and_write_format(hass, api_mock):
    api_mock.post(f"http://{HOST}/ajax/get-registers", json=REGISTERS)
    api_mock.post(f"http://{HOST}/ajax/set-register", json={"result": True})
    client = WinetClient(async_get_clientsession(hass), HOST, dual_fan=True)
    state = await client.read()
    assert (state.fan_1, state.fan_2) == (3, 2)
    assert api_mock.mock_calls[-1][2] == "key=020&category=0"
    await client.command_fan(1, 4)
    assert api_mock.mock_calls[-1][2] == "key=002&memory=1&regId=47&value=4"
    await client.command_fan(2, 1)
    assert api_mock.mock_calls[-1][2] == "key=002&memory=1&regId=48&value=1"
    assert api_mock.mock_calls[-1][3]["Content-Type"] == "application/json; charset=utf-8"


@pytest.mark.parametrize("response", [{"result": False}, {"result": 1}, {}])
async def test_rejected_write(hass, aioclient_mock, response):
    aioclient_mock.post(f"http://{HOST}/ajax/set-register", json=response)
    with pytest.raises(WinetError):
        await WinetClient(async_get_clientsession(hass), HOST, dual_fan=True).command_fan(1, 3)
    assert aioclient_mock.call_count == 1


@pytest.mark.parametrize("response", ["[]", "not json"])
async def test_bad_auxiliary_response_preserves_thermostat(hass, api_mock, response):
    api_mock.post(f"http://{HOST}/ajax/get-registers", text=response)
    state = await WinetClient(async_get_clientsession(hass), HOST, dual_fan=True).read()
    assert state == StoveState.parse(GLOBAL)


async def test_timeout_write_sent_once(hass, aioclient_mock):
    aioclient_mock.post(f"http://{HOST}/ajax/set-register", exc=TimeoutError)
    with pytest.raises(WinetError):
        await WinetClient(async_get_clientsession(hass), HOST, dual_fan=True).command_fan(2, 3)
    assert aioclient_mock.call_count == 1


async def test_entities_track_remote_and_unknown_values(hass, fan_entry):
    coordinator = fan_entry.runtime_data
    climate_id = entity_id(hass, "climate", "climate")
    climate = hass.states.get(climate_id)
    assert climate.attributes["supported_features"] & ClimateEntityFeature.FAN_MODE
    assert len(climate.attributes["fan_modes"]) == 16
    assert climate.attributes["fan_mode"] == "fans_3_2"
    assert hass.states.get(entity_id(hass, "sensor", "wifi_signal")).state == "4"
    assert hass.states.get(entity_id(hass, "sensor", "fan_profile")).state == "27436"
    assert hass.states.get(entity_id(hass, "sensor", "automation_mode")).state == "disabled"
    for fan, speed in [(1, 3), (2, 2)]:
        state = hass.states.get(entity_id(hass, "number", f"fan_{fan}"))
        assert state.state == str(speed)
        assert (state.attributes["min"], state.attributes["max"], state.attributes["step"]) == (
            1,
            4,
            1,
        )
    coordinator.async_set_updated_data(fan_state(2, 4))
    assert hass.states.get(climate_id).attributes["fan_mode"] == "fans_2_4"
    coordinator.async_set_updated_data(replace(fan_state(), fan_2=None))
    assert hass.states.get(entity_id(hass, "number", "fan_2")).state == "unavailable"
    assert hass.states.get(entity_id(hass, "number", "fan_1")).state == "3"
    assert hass.states.get(climate_id).attributes["fan_mode"] is None
    assert hass.states.get(climate_id).state == "off"


async def test_climate_pair_and_number_share_immediate_readback(hass, fan_entry):
    coordinator = fan_entry.runtime_data
    climate_id = entity_id(hass, "climate", "climate")
    with (
        patch.object(
            coordinator.client,
            "read",
            new=AsyncMock(
                side_effect=[fan_state(), fan_state(1, 4), fan_state(1, 4), fan_state(2, 4)]
            ),
        ),
        patch.object(coordinator.client, "command_fan", new_callable=AsyncMock) as command,
        patch.object(coordinator.client, "command", new_callable=AsyncMock) as stove_command,
    ):
        await hass.services.async_call(
            "climate",
            "set_fan_mode",
            {"entity_id": climate_id, "fan_mode": "fans_1_4"},
            blocking=True,
        )
        assert hass.states.get(climate_id).attributes["fan_mode"] == "fans_1_4"
        await hass.services.async_call(
            "number",
            "set_value",
            {"entity_id": entity_id(hass, "number", "fan_1"), "value": 2},
            blocking=True,
        )
        assert hass.states.get(climate_id).attributes["fan_mode"] == "fans_2_4"
        assert command.await_args_list == [call(1, 1), call(2, 4), call(1, 2)]
        stove_command.assert_not_awaited()
    assert hass.states.get(entity_id(hass, "number", "fan_2")).state == "4"
    assert hass.states.get(climate_id).attributes["temperature"] == 19
    assert hass.states.get(entity_id(hass, "number", "power")).state == "5.0"


async def test_unchanged_fan_not_written(hass, fan_entry):
    coordinator = fan_entry.runtime_data
    with (
        patch.object(
            coordinator.client, "read", new=AsyncMock(side_effect=[fan_state(), fan_state(3, 4)])
        ),
        patch.object(coordinator.client, "command_fan", new_callable=AsyncMock) as command,
    ):
        await coordinator.async_set_fan_speeds(fan_1=3, fan_2=4)
        command.assert_awaited_once_with(2, 4)


async def test_fan_services_read_only(hass, fan_entry):
    coordinator = fan_entry.runtime_data
    coordinator.settings["read_only"] = True
    with patch.object(coordinator.client, "command_fan", new_callable=AsyncMock) as command:
        for domain, service, data in [
            (
                "climate",
                "set_fan_mode",
                {"entity_id": entity_id(hass, "climate", "climate"), "fan_mode": "fans_1_4"},
            ),
            ("number", "set_value", {"entity_id": entity_id(hass, "number", "fan_1"), "value": 3}),
        ]:
            with pytest.raises(ServiceValidationError, match="read-only"):
                await hass.services.async_call(domain, service, data, blocking=True)
        command.assert_not_awaited()


@pytest.mark.parametrize("speed", [0, 5, 2.5, True, "3", float("nan"), float("inf")])
async def test_invalid_speed_never_written(hass, fan_entry, speed):
    coordinator = fan_entry.runtime_data
    with patch.object(coordinator.client, "command_fan", new_callable=AsyncMock) as command:
        with pytest.raises(ServiceValidationError):
            await coordinator.async_set_fan_speeds(fan_1=speed)
        command.assert_not_awaited()


@pytest.mark.parametrize(
    "fresh",
    [
        StoveState.parse(GLOBAL),
        replace(fan_state(), fan_profile=27437),
        replace(fan_state(), fan_1=None),
    ],
)
async def test_profile_rechecked_before_write(hass, fan_entry, fresh):
    coordinator = fan_entry.runtime_data
    with (
        patch.object(coordinator.client, "read", new=AsyncMock(return_value=fresh)),
        patch.object(coordinator.client, "command_fan", new_callable=AsyncMock) as command,
    ):
        with pytest.raises(ServiceValidationError, match="profile 27436"):
            await coordinator.async_set_fan_speeds(fan_1=1)
        command.assert_not_awaited()


async def test_accepted_but_unchanged_not_reported_as_success(hass, fan_entry):
    coordinator = fan_entry.runtime_data
    with patch.object(coordinator.client, "command_fan", new_callable=AsyncMock) as command:
        with pytest.raises(HomeAssistantError, match="did not confirm"):
            await coordinator.async_set_fan_speeds(fan_2=4)
        command.assert_awaited_once_with(2, 4)
    assert coordinator.data.fan_2 == 2


async def test_partial_pair_failure_reads_actual_values_and_does_not_retry(hass, fan_entry):
    coordinator = fan_entry.runtime_data
    with (
        patch.object(
            coordinator.client, "read", new=AsyncMock(side_effect=[fan_state(), fan_state(1, 2)])
        ),
        patch.object(
            coordinator.client,
            "command_fan",
            new=AsyncMock(side_effect=[None, WinetError("timeout")]),
        ) as command,
    ):
        with pytest.raises(HomeAssistantError, match="uncertain"):
            await coordinator.async_set_fan_speeds(fan_1=1, fan_2=4)
        assert command.await_args_list == [call(1, 1), call(2, 4)]
    assert (coordinator.data.fan_1, coordinator.data.fan_2) == (1, 2)


async def test_auxiliary_timeout_keeps_main_climate_available(hass, fan_entry, api_mock):
    api_mock.clear_requests()
    api_mock.get(f"http://{HOST}/api/global", json=GLOBAL)
    api_mock.post(f"http://{HOST}/ajax/get-registers", exc=TimeoutError)
    coordinator = fan_entry.runtime_data
    await coordinator.async_refresh()
    assert coordinator.last_update_success
    assert hass.states.get(entity_id(hass, "climate", "climate")).state == "off"
    assert hass.states.get(entity_id(hass, "number", "fan_1")).state == "unavailable"
    assert hass.states.get(entity_id(hass, "number", "fan_2")).state == "unavailable"


async def test_unchanged_pair_does_not_write(hass, fan_entry):
    coordinator = fan_entry.runtime_data
    with patch.object(coordinator.client, "command_fan", new_callable=AsyncMock) as command:
        await coordinator.async_set_fan_speeds(fan_1=3, fan_2=2)
        command.assert_not_awaited()


async def test_readback_failure_reports_uncertain_and_recovers(hass, fan_entry):
    coordinator = fan_entry.runtime_data
    with (
        patch.object(
            coordinator.client,
            "read",
            new=AsyncMock(side_effect=[fan_state(), WinetError("offline"), fan_state(3, 4)]),
        ),
        patch.object(coordinator.client, "command_fan", new_callable=AsyncMock) as command,
    ):
        with pytest.raises(HomeAssistantError, match="uncertain"):
            await coordinator.async_set_fan_speeds(fan_2=4)
        command.assert_awaited_once_with(2, 4)
    assert (coordinator.data.fan_1, coordinator.data.fan_2) == (3, 4)


async def test_italian_fan_labels(hass, fan_entry):
    from homeassistant.helpers.translation import async_get_translations

    translations = await async_get_translations(hass, "it", "entity", {"winet"})
    assert (
        translations[
            "component.winet.entity.climate.stove.state_attributes.fan_mode.state.fans_3_2"
        ]
        == "V1: 3 · V2: 2"
    )
    assert translations["component.winet.entity.number.fan_1.name"] == "Ventola 1"
