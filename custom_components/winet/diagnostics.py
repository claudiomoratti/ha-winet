"""Allowlisted diagnostics: never export Wi-Fi credentials or identifiers."""

from dataclasses import asdict


async def async_get_config_entry_diagnostics(hass, entry):
    coordinator = entry.runtime_data
    state = asdict(coordinator.data)
    state.pop("description", None)  # Free-form text is not required for diagnostics.
    return {
        "options": coordinator.settings,
        "last_update_success": coordinator.last_update_success,
        "state_raw": state,
    }
