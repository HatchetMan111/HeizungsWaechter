"""Sensor-Plattform für HeizungsWächter – 18 Entitäten."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfEnergy, UnitOfTime
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    CONF_FUEL_TYPE,
    DOMAIN,
    FUEL_TYPES,
    FUEL_UNIT,
    FUEL_GAS_TYPES,
)
from .coordinator import HeizungsWaechterCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: HeizungsWaechterCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([
        # Status & Temperatur
        StatusSensor(coordinator, entry),
        TemperaturSensor(coordinator, entry),
        # Laufzeit
        AktuelleLaufzeitSensor(coordinator, entry),
        LaufzeitHeuteSensor(coordinator, entry),
        LaufzeitMonatSensor(coordinator, entry),
        LaufzeitGesamtSensor(coordinator, entry),
        # Energie (kWh)
        KwhHeuteSensor(coordinator, entry),
        KwhMonatSensor(coordinator, entry),
        KwhGesamtSensor(coordinator, entry),
        # Kosten
        KostenHeuteSensor(coordinator, entry),
        KostenMonatSensor(coordinator, entry),
        KostenGesamtSensor(coordinator, entry),
        # Taktungen
        TaktungenHeuteSensor(coordinator, entry),
        TaktungenMonatSensor(coordinator, entry),
        TaktungenGesamtSensor(coordinator, entry),
        # Volumen / Masse (m³, L oder kg)
        VolumenHeuteSensor(coordinator, entry),
        VolumenMonatSensor(coordinator, entry),
        VolumenGesamtSensor(coordinator, entry),
    ])


# ── Hilfsfunktionen ───────────────────────────────────────────────────────────

def _device(entry: ConfigEntry) -> DeviceInfo:
    cfg = {**entry.data, **entry.options}
    return DeviceInfo(
        identifiers={(DOMAIN, entry.entry_id)},
        name=entry.title,
        manufacturer="HeizungsWächter",
        model=FUEL_TYPES.get(cfg.get(CONF_FUEL_TYPE, "heizoel"), "Fossil"),
        sw_version="1.2.0",
    )


def _fuel(entry: ConfigEntry) -> str:
    cfg = {**entry.data, **entry.options}
    return cfg.get(CONF_FUEL_TYPE, "heizoel")


# ── Basis-Klasse ──────────────────────────────────────────────────────────────

class _Base(SensorEntity):
    _attr_should_poll = False

    def __init__(
        self,
        coordinator: HeizungsWaechterCoordinator,
        entry: ConfigEntry,
        unique_suffix: str,
    ) -> None:
        self._c     = coordinator
        self._entry = entry
        self._attr_unique_id   = f"{entry.entry_id}_{unique_suffix}"
        self._attr_device_info = _device(entry)

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(
            self.hass.bus.async_listen(
                f"{DOMAIN}_updated_{self._entry.entry_id}",
                self._on_update,
            )
        )

    @callback
    def _on_update(self, _event) -> None:
        self.async_write_ha_state()


# ── Status ────────────────────────────────────────────────────────────────────

class StatusSensor(_Base):
    _attr_name = "Brenner Status"
    _attr_icon = "mdi:fire"

    def __init__(self, c, e):
        super().__init__(c, e, "status")

    @property
    def native_value(self) -> str:
        return "AN" if self._c.burner_on else "AUS"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        cfg = {**self._entry.data, **self._entry.options}
        return {
            "schwellwert_°C":       cfg.get("temp_threshold"),
            "brennerleistung_kW":   cfg.get("burner_power_kw"),
            "brennstoff":           FUEL_TYPES.get(cfg.get("fuel_type", ""), ""),
            "wirkungsgrad_%":       cfg.get("efficiency"),
            "preis_€_pro_kWh":      cfg.get("fuel_price_per_kwh"),
        }


class TemperaturSensor(_Base):
    _attr_name                     = "Ofenrohr Temperatur"
    _attr_device_class             = SensorDeviceClass.TEMPERATURE
    _attr_native_unit_of_measurement = "°C"
    _attr_state_class              = SensorStateClass.MEASUREMENT
    _attr_icon                     = "mdi:thermometer-high"

    def __init__(self, c, e):
        super().__init__(c, e, "temperatur")

    @property
    def native_value(self) -> float | None:
        s = self.hass.states.get(self._c.sensor_entity_id)
        if s and s.state not in ("unknown", "unavailable"):
            try:
                return round(float(s.state), 1)
            except ValueError:
                pass
        return None


# ── Laufzeit ──────────────────────────────────────────────────────────────────

class AktuelleLaufzeitSensor(_Base):
    _attr_name                       = "Aktuelle Laufzeit"
    _attr_native_unit_of_measurement = UnitOfTime.MINUTES
    _attr_state_class                = SensorStateClass.MEASUREMENT
    _attr_icon                       = "mdi:timer-play"

    def __init__(self, c, e): super().__init__(c, e, "laufzeit_aktuell")

    @property
    def native_value(self) -> float:
        return round(self._c.current_session_s / 60, 1)


class LaufzeitHeuteSensor(_Base):
    _attr_name                       = "Laufzeit Heute"
    _attr_native_unit_of_measurement = UnitOfTime.MINUTES
    _attr_state_class                = SensorStateClass.TOTAL_INCREASING
    _attr_icon                       = "mdi:timer-outline"

    def __init__(self, c, e): super().__init__(c, e, "laufzeit_heute")

    @property
    def native_value(self) -> float:
        return round(self._c.runtime_today_s / 60, 1)


class LaufzeitMonatSensor(_Base):
    _attr_name                       = "Laufzeit Monat"
    _attr_native_unit_of_measurement = UnitOfTime.HOURS
    _attr_state_class                = SensorStateClass.TOTAL_INCREASING
    _attr_icon                       = "mdi:timer-outline"

    def __init__(self, c, e): super().__init__(c, e, "laufzeit_monat")

    @property
    def native_value(self) -> float:
        return round(self._c.runtime_month_s / 3600, 2)


class LaufzeitGesamtSensor(_Base):
    _attr_name                       = "Laufzeit Gesamt"
    _attr_native_unit_of_measurement = UnitOfTime.HOURS
    _attr_state_class                = SensorStateClass.TOTAL_INCREASING
    _attr_icon                       = "mdi:timer-sand"

    def __init__(self, c, e): super().__init__(c, e, "laufzeit_gesamt")

    @property
    def native_value(self) -> float:
        return round(self._c.runtime_total_s / 3600, 2)


# ── Energie (kWh) ─────────────────────────────────────────────────────────────

class KwhHeuteSensor(_Base):
    _attr_name                       = "Verbrauch Heute kWh"
    _attr_device_class               = SensorDeviceClass.ENERGY
    _attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
    _attr_state_class                = SensorStateClass.TOTAL_INCREASING
    _attr_icon                       = "mdi:lightning-bolt"

    def __init__(self, c, e): super().__init__(c, e, "kwh_heute")

    @property
    def native_value(self) -> float:
        return round(self._c.kwh_today, 3)


class KwhMonatSensor(_Base):
    _attr_name                       = "Verbrauch Monat kWh"
    _attr_device_class               = SensorDeviceClass.ENERGY
    _attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
    _attr_state_class                = SensorStateClass.TOTAL_INCREASING
    _attr_icon                       = "mdi:lightning-bolt"

    def __init__(self, c, e): super().__init__(c, e, "kwh_monat")

    @property
    def native_value(self) -> float:
        return round(self._c.kwh_month, 2)


class KwhGesamtSensor(_Base):
    _attr_name                       = "Verbrauch Gesamt kWh"
    _attr_device_class               = SensorDeviceClass.ENERGY
    _attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
    _attr_state_class                = SensorStateClass.TOTAL_INCREASING
    _attr_icon                       = "mdi:lightning-bolt"

    def __init__(self, c, e): super().__init__(c, e, "kwh_gesamt")

    @property
    def native_value(self) -> float:
        return round(self._c.kwh_total, 2)


# ── Kosten ────────────────────────────────────────────────────────────────────

class KostenHeuteSensor(_Base):
    _attr_name                       = "Kosten Heute"
    _attr_device_class               = SensorDeviceClass.MONETARY
    _attr_native_unit_of_measurement = "EUR"
    _attr_state_class                = SensorStateClass.TOTAL_INCREASING
    _attr_icon                       = "mdi:currency-eur"

    def __init__(self, c, e): super().__init__(c, e, "kosten_heute")

    @property
    def native_value(self) -> float:
        return round(self._c.cost_today, 4)


class KostenMonatSensor(_Base):
    _attr_name                       = "Kosten Monat"
    _attr_device_class               = SensorDeviceClass.MONETARY
    _attr_native_unit_of_measurement = "EUR"
    _attr_state_class                = SensorStateClass.TOTAL_INCREASING
    _attr_icon                       = "mdi:currency-eur"

    def __init__(self, c, e): super().__init__(c, e, "kosten_monat")

    @property
    def native_value(self) -> float:
        return round(self._c.cost_month, 2)


class KostenGesamtSensor(_Base):
    _attr_name                       = "Kosten Gesamt"
    _attr_device_class               = SensorDeviceClass.MONETARY
    _attr_native_unit_of_measurement = "EUR"
    _attr_state_class                = SensorStateClass.TOTAL_INCREASING
    _attr_icon                       = "mdi:currency-eur"

    def __init__(self, c, e): super().__init__(c, e, "kosten_gesamt")

    @property
    def native_value(self) -> float:
        return round(self._c.cost_total, 2)


# ── Taktungen ─────────────────────────────────────────────────────────────────

class TaktungenHeuteSensor(_Base):
    _attr_name                       = "Brennerstarts Heute"
    _attr_native_unit_of_measurement = "Starts"
    _attr_state_class                = SensorStateClass.TOTAL_INCREASING
    _attr_icon                       = "mdi:counter"

    def __init__(self, c, e): super().__init__(c, e, "taktungen_heute")

    @property
    def native_value(self) -> int:
        return self._c.cycles_today


class TaktungenMonatSensor(_Base):
    _attr_name                       = "Brennerstarts Monat"
    _attr_native_unit_of_measurement = "Starts"
    _attr_state_class                = SensorStateClass.TOTAL_INCREASING
    _attr_icon                       = "mdi:counter"

    def __init__(self, c, e): super().__init__(c, e, "taktungen_monat")

    @property
    def native_value(self) -> int:
        return self._c.cycles_month


class TaktungenGesamtSensor(_Base):
    _attr_name                       = "Brennerstarts Gesamt"
    _attr_native_unit_of_measurement = "Starts"
    _attr_state_class                = SensorStateClass.TOTAL_INCREASING
    _attr_icon                       = "mdi:counter"

    def __init__(self, c, e): super().__init__(c, e, "taktungen_gesamt")

    @property
    def native_value(self) -> int:
        return self._c.cycles_total


# ── Volumen / Masse ───────────────────────────────────────────────────────────

def _vol_unit(entry: ConfigEntry) -> str:
    return FUEL_UNIT.get(_fuel(entry), "L")


def _vol_device_class(entry: ConfigEntry) -> SensorDeviceClass | None:
    """Erdgas → device_class GAS (m³) für Energie-Dashboard."""
    return SensorDeviceClass.GAS if _fuel(entry) in FUEL_GAS_TYPES else None


def _vol_icon(entry: ConfigEntry) -> str:
    return {
        "heizoel":     "mdi:barrel",
        "erdgas":      "mdi:meter-gas",
        "fluessiggas": "mdi:propane-tank",
        "pellets":     "mdi:sack",
    }.get(_fuel(entry), "mdi:gauge")


class VolumenHeuteSensor(_Base):
    _attr_state_class = SensorStateClass.TOTAL_INCREASING

    def __init__(self, c, e):
        super().__init__(c, e, "volumen_heute")
        unit = _vol_unit(e)
        self._attr_name                       = f"Verbrauch Heute {unit}"
        self._attr_native_unit_of_measurement = unit
        self._attr_device_class               = _vol_device_class(e)
        self._attr_icon                       = _vol_icon(e)

    @property
    def native_value(self) -> float:
        return round(self._c.volume_today, 3)


class VolumenMonatSensor(_Base):
    _attr_state_class = SensorStateClass.TOTAL_INCREASING

    def __init__(self, c, e):
        super().__init__(c, e, "volumen_monat")
        unit = _vol_unit(e)
        self._attr_name                       = f"Verbrauch Monat {unit}"
        self._attr_native_unit_of_measurement = unit
        self._attr_device_class               = _vol_device_class(e)
        self._attr_icon                       = _vol_icon(e)

    @property
    def native_value(self) -> float:
        return round(self._c.volume_month, 3)


class VolumenGesamtSensor(_Base):
    _attr_state_class = SensorStateClass.TOTAL_INCREASING

    def __init__(self, c, e):
        super().__init__(c, e, "volumen_gesamt")
        unit = _vol_unit(e)
        self._attr_name                       = f"Verbrauch Gesamt {unit}"
        self._attr_native_unit_of_measurement = unit
        self._attr_device_class               = _vol_device_class(e)
        self._attr_icon                       = _vol_icon(e)

    @property
    def native_value(self) -> float:
        return round(self._c.volume_total, 3)
