"""Heizungsüberwachung – Gas/Öl/Fossil Heizung Monitor für Home Assistant."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN, PLATFORMS
from .coordinator import HeizungCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Heizungsüberwachung from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    coordinator = HeizungCoordinator(hass, entry)
    await coordinator.async_setup()
    hass.data[DOMAIN][entry.entry_id] = coordinator

    # Re-init coordinator when options change
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    _LOGGER.info("Heizungsüberwachung '%s' gestartet", entry.title)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    coordinator: HeizungCoordinator = hass.data[DOMAIN].pop(entry.entry_id, None)
    if coordinator:
        await coordinator.async_teardown()

    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update – reload coordinator config."""
    coordinator: HeizungCoordinator = hass.data[DOMAIN].get(entry.entry_id)
    if coordinator:
        coordinator.reload_config()
        _LOGGER.info("Heizungsüberwachung Konfiguration aktualisiert")
