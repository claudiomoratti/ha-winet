"""Tests never connect to a real stove."""

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.winet.const import DEFAULTS

HOST = "stove.example.test"
MAC = "aabbccddeeff"
IDENTITY = {"id": "WiNET Gen.Stove", "mac": MAC, "apWpaPwd": "never-export-this"}
GLOBAL = {
    "status": 0,
    "description": "OFF",
    "air": 35,
    "setAir": 38,
    "water": None,
    "setWater": None,
    "power": 5,
    "gasflue": 0,
    "rpmExtractor": None,
}


@pytest.fixture(autouse=True)
def custom_integrations(enable_custom_integrations):
    yield


@pytest.fixture
def entry(hass):
    item = MockConfigEntry(
        domain="winet",
        unique_id=MAC,
        title="WiNet Stove",
        data={"host": HOST},
        options=dict(DEFAULTS),
    )
    item.add_to_hass(hass)
    return item


@pytest.fixture
def api_mock(aioclient_mock):
    aioclient_mock.get(f"http://{HOST}/api/id", json=IDENTITY)
    aioclient_mock.get(f"http://{HOST}/api/global", json=GLOBAL)
    return aioclient_mock
