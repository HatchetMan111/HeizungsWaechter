"""HeizungsWächter – Gas/Öl/Fossil Heizung Monitor für Home Assistant."""
from __future__ import annotations

import logging
from pathlib import Path

from homeassistant.components.frontend import add_extra_js_url
from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN, PLATFORMS, VERSION
from .coordinator import HeizungsWaechterCoordinator

_LOGGER = logging.getLogger(__name__)

CARD_FILENAME = "heizungswaechter-card.js"
CARD_URL = f"/heizungswaechter/{CARD_FILENAME}"


async def _async_register_card(hass: HomeAssistant) -> None:
    """Lovelace-Card (React/Vite-Build) einmalig bereitstellen und laden."""
    if hass.data.get(f"{DOMAIN}_card_registered"):
        return
    card_file = Path(__file__).parent / "www" / CARD_FILENAME
    if not card_file.is_file():
        _LOGGER.warning("Card-Datei %s nicht gefunden – Frontend-Card deaktiviert", card_file)
        return
    await hass.http.async_register_static_paths(
        [StaticPathConfig(CARD_URL, str(card_file))]
    )
    add_extra_js_url(hass, f"{CARD_URL}?v={VERSION}")
    hass.data[f"{DOMAIN}_card_registered"] = True
    _LOGGER.debug("HeizungsWächter-Card unter %s registriert", CARD_URL)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up HeizungsWächter from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    await _async_register_card(hass)

    coordinator = HeizungsWaechterCoordinator(hass, entry)
    await coordinator.async_setup()
    hass.data[DOMAIN][entry.entry_id] = coordinator

    # Re-init coordinator when options change
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    _LOGGER.info("HeizungsWächter '%s' gestartet", entry.title)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    coordinator: HeizungsWaechterCoordinator = hass.data[DOMAIN].pop(entry.entry_id, None)
    if coordinator:
        await coordinator.async_teardown()

    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update – reload coordinator config."""
    coordinator: HeizungsWaechterCoordinator = hass.data[DOMAIN].get(entry.entry_id)
    if coordinator:
        coordinator.reload_config()
        # Sensor-Abo erneuern, falls der Temperatursensor gewechselt wurde
        coordinator.resubscribe()
        coordinator._schedule_save()
        _LOGGER.info("HeizungsWächter Konfiguration aktualisiert")
