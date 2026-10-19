"""Shared device registration."""

from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import WinetCoordinator


class WinetEntity(CoordinatorEntity[WinetCoordinator]):
    """An entity belonging to a single WiNet stove."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: WinetCoordinator, key: str) -> None:
        super().__init__(coordinator)
        mac = coordinator.identity["mac"]
        self._attr_unique_id = f"{mac}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, mac)},
            name="WiNet Stove",
            manufacturer="WiNet",
            model=coordinator.identity["model"],
            configuration_url=f"http://{coordinator.client.host}",
        )
