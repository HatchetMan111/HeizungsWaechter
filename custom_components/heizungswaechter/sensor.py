"""Sensor platform for Heizungsüberwachung."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import (
    SensorEntity,
    SensorDeviceClass,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    UnitOfEnergy,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, FUEL_TYPES, FUEL_UNIT, FUEL_GAS_TYPES, CONF_FUEL_TYPE
from .coordinator import HeizungCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: HeizungCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities = [
        HeizungStatusSensor(coordinator, entry),
        HeizungTemperatureSensor(coordinator, entry),
        HeizungCurrentSessionSensor(coordinator, entry),
        HeizungRuntimeTodaySensor(coordinator, entry),
        HeizungRuntimeMonthSensor(coordinator, entry),
        HeizungRuntimeTotalSensor(coordinator, entry),
        HeizungKwhTodaySensor(coordinator, entry),
        HeizungKwhMonthSensor(coordinator, entry),
        HeizungKwhTotalSensor(coordinator, entry),
        HeizungCostTodaySensor(coordinator, entry),
        HeizungCostMonthSensor(coordinator, entry),
        HeizungCostTotalSensor(coordinator, entry),
        HeizungCyclesTodaySensor(coordinator, entry),
        HeizungCyclesMonthSensor(coordinator, entry),
        HeizungCyclesTotalSensor(coordinator, entry),
        # Volume/mass sensors (m³, L or kg depending on fuel)
        HeizungVolumeTodaySensor(coordinator, entry),
        HeizungVolumeMonthSensor(coordinator, entry),
        HeizungVolumeTotalSensor(coordinator, entry),
    ]
    async_add_entities(entities)


def _device_info(entry: ConfigEntry) -> DeviceInfo:
    return DeviceInfo(
        identifiers={(DOMAIN, entry.entry_id)},
        name=entry.title,
        manufacturer="Heizungsüberwachung",
        model=FUEL_TYPES.get(
            entry.data.get(CONF_FUEL_TYPE, "heizoel"), "Fossil"
        ),
        sw_version="1.0.0",
    )


class _HeizungBase(SensorEntity):
    """Base class for all Heizung sensors."""

    _attr_should_poll = False

    def __init__(self, coordinator: HeizungCoordinator, entry: ConfigEntry, suffix: str) -> None:
        self._coordinator = coordinator
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_{suffix}"
        self._attr_device_info = _device_info(entry)

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(
            self.hass.bus.async_listen(
                f"{DOMAIN}_updated_{self._entry.entry_id}",
                self._handle_update,
            )
        )

    @callback
    def _handle_update(self, _event) -> None:
        self.async_write_ha_state()


# ── Status ────────────────────────────────────────────────────────────────────

class HeizungStatusSensor(_HeizungBase):
    _attr_name = "Brenner Status"
    _attr_icon = "mdi:fire"

    def __init__(self, c, e):
        super().__init__(c, e, "status")

    @property
    def native_value(self) -> str:
        return "AN" if self._coordinator.burner_on else "AUS"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        cfg = {**self._entry.data, **self._entry.options}
        return {
            "schwellwert_c": cfg.get("temp_threshold"),
            "brennerleistung_kw": cfg.get("burner_power_kw"),
            "brennstoff": FUEL_TYPES.get(cfg.get("fuel_type", ""), ""),
            "wirkungsgrad_prozent": cfg.get("efficiency"),
            "preis_eur_pro_kwh": cfg.get("fuel_price_per_kwh"),
        }


class HeizungTemperatureSensor(_HeizungBase):
    _attr_name = "Ofenrohr Temperatur"
    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_native_unit_of_measurement = "°C"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:thermometer-high"

    def __init__(self, c, e):
        super().__init__(c, e, "temperature")

    @property
    def native_value(self) -> float | None:
        state = self.hass.states.get(self._coordinator.sensor_entity_id)
        if state and state.state not in ("unknown", "unavailable"):
            try:
                return round(float(state.state), 1)
            except ValueError:
                pass
        return None


# ── Runtime ───────────────────────────────────────────────────────────────────

class HeizungCurrentSessionSensor(_HeizungBase):
    _attr_name = "Aktuelle Laufzeit"
    _attr_native_unit_of_measurement = UnitOfTime.MINUTES
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:timer-play"

    def __init__(self, c, e):
        super().__init__(c, e, "current_session")

    @property
    def native_value(self) -> float:
        return round(self._coordinator.current_session_s / 60, 1)


class HeizungRuntimeTodaySensor(_HeizungBase):
    _attr_name = "Laufzeit Heute"
    _attr_native_unit_of_measurement = UnitOfTime.MINUTES
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_icon = "mdi:timer-outline"

    def __init__(self, c, e):
        super().__init__(c, e, "runtime_today")

    @property
    def native_value(self) -> float:
        return round(self._coordinator.runtime_today_s / 60, 1)


class HeizungRuntimeMonthSensor(_HeizungBase):
    _attr_name = "Laufzeit Diesen Monat"
    _attr_native_unit_of_measurement = UnitOfTime.HOURS
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_icon = "mdi:timer-outline"

    def __init__(self, c, e):
        super().__init__(c, e, "runtime_month")

    @property
    def native_value(self) -> float:
        return round(self._coordinator.runtime_month_s / 3600, 2)


class HeizungRuntimeTotalSensor(_HeizungBase):
    _attr_name = "Laufzeit Gesamt"
    _attr_native_unit_of_measurement = UnitOfTime.HOURS
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_icon = "mdi:timer-sand"

    def __init__(self, c, e):
        super().__init__(c, e, "runtime_total")

    @property
    def native_value(self) -> float:
        return round(self._coordinator.runtime_total_s / 3600, 2)


# ── kWh ───────────────────────────────────────────────────────────────────────

class HeizungKwhTodaySensor(_HeizungBase):
    _attr_name = "Verbrauch Heute (kWh)"
    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_icon = "mdi:lightning-bolt"

    def __init__(self, c, e):
        super().__init__(c, e, "kwh_today")

    @property
    def native_value(self) -> float:
        return round(self._coordinator.kwh_today, 3)


class HeizungKwhMonthSensor(_HeizungBase):
    _attr_name = "Verbrauch Diesen Monat (kWh)"
    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_icon = "mdi:lightning-bolt"

    def __init__(self, c, e):
        super().__init__(c, e, "kwh_month")

    @property
    def native_value(self) -> float:
        return round(self._coordinator.kwh_month, 2)


class HeizungKwhTotalSensor(_HeizungBase):
    _attr_name = "Verbrauch Gesamt (kWh)"
    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_icon = "mdi:lightning-bolt"

    def __init__(self, c, e):
        super().__init__(c, e, "kwh_total")

    @property
    def native_value(self) -> float:
        return round(self._coordinator.kwh_total, 2)


# ── Kosten ────────────────────────────────────────────────────────────────────

class HeizungCostTodaySensor(_HeizungBase):
    _attr_name = "Kosten Heute"
    _attr_native_unit_of_measurement = "EUR"
    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_icon = "mdi:currency-eur"

    def __init__(self, c, e):
        super().__init__(c, e, "cost_today")

    @property
    def native_value(self) -> float:
        return round(self._coordinator.cost_today, 4)


class HeizungCostMonthSensor(_HeizungBase):
    _attr_name = "Kosten Diesen Monat"
    _attr_native_unit_of_measurement = "EUR"
    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_icon = "mdi:currency-eur"

    def __init__(self, c, e):
        super().__init__(c, e, "cost_month")

    @property
    def native_value(self) -> float:
        return round(self._coordinator.cost_month, 2)


class HeizungCostTotalSensor(_HeizungBase):
    _attr_name = "Kosten Gesamt"
    _attr_native_unit_of_measurement = "EUR"
    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_icon = "mdi:currency-eur"

    def __init__(self, c, e):
        super().__init__(c, e, "cost_total")

    @property
    def native_value(self) -> float:
        return round(self._coordinator.cost_total, 2)


# ── Taktungen ─────────────────────────────────────────────────────────────────

class HeizungCyclesTodaySensor(_HeizungBase):
    _attr_name = "Brennerstarts Heute"
    _attr_native_unit_of_measurement = "Starts"
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_icon = "mdi:counter"

    def __init__(self, c, e):
        super().__init__(c, e, "cycles_today")

    @property
    def native_value(self) -> int:
        return self._coordinator.cycles_today


class HeizungCyclesMonthSensor(_HeizungBase):
    _attr_name = "Brennerstarts Diesen Monat"
    _attr_native_unit_of_measurement = "Starts"
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_icon = "mdi:counter"

    def __init__(self, c, e):
        super().__init__(c, e, "cycles_month")

    @property
    def native_value(self) -> int:
        return self._coordinator.cycles_month


class HeizungCyclesTotalSensor(_HeizungBase):
    _attr_name = "Brennerstarts Gesamt"
    _attr_native_unit_of_measurement = "Starts"
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_icon = "mdi:counter"

    def __init__(self, c, e):
        super().__init__(c, e, "cycles_total")

    @property
    def native_value(self) -> int:
        return self._coordinator.cycles_total


# ── Volumen / Masse ───────────────────────────────────────────────────────────

def _get_fuel_type(entry: ConfigEntry) -> str:
    cfg = {**entry.data, **entry.options}
    return cfg.get(CONF_FUEL_TYPE, "heizoel")


def _volume_unit(entry: ConfigEntry) -> str:
    return FUEL_UNIT.get(_get_fuel_type(entry), "L")


def _volume_device_class(entry: ConfigEntry):
    """Return GAS device_class for m³ sensors (Energie-Dashboard kompatibel)."""
    fuel = _get_fuel_type(entry)
    if fuel in FUEL_GAS_TYPES:
        return SensorDeviceClass.GAS   # m³ – nativ im Energie-Dashboard
    return None  # L / kg – kein spezieller device_class nötig


def _volume_icon(entry: ConfigEntry) -> str:
    fuel = _get_fuel_type(entry)
    icons = {
        "heizoel":     "mdi:barrel",
        "erdgas":      "mdi:meter-gas",
        "fluessiggas": "mdi:propane-tank",
        "pellets":     "mdi:bag-personal",
    }
    return icons.get(fuel, "mdi:gauge")


class HeizungVolumeTodaySensor(_HeizungBase):
    _attr_state_class = SensorStateClass.TOTAL_INCREASING

    def __init__(self, c, e):
        super().__init__(c, e, "volume_today")
        fuel_label = FUEL_UNIT.get(_get_fuel_type(e), "L")
        self._attr_name = f"Verbrauch Heute ({fuel_label})"
        self._attr_native_unit_of_measurement = _volume_unit(e)
        self._attr_device_class = _volume_device_class(e)
        self._attr_icon = _volume_icon(e)

    @property
    def native_value(self) -> float:
        return round(self._coordinator.volume_today, 3)


class HeizungVolumeMonthSensor(_HeizungBase):
    _attr_state_class = SensorStateClass.TOTAL_INCREASING

    def __init__(self, c, e):
        super().__init__(c, e, "volume_month")
        fuel_label = FUEL_UNIT.get(_get_fuel_type(e), "L")
        self._attr_name = f"Verbrauch Diesen Monat ({fuel_label})"
        self._attr_native_unit_of_measurement = _volume_unit(e)
        self._attr_device_class = _volume_device_class(e)
        self._attr_icon = _volume_icon(e)

    @property
    def native_value(self) -> float:
        return round(self._coordinator.volume_month, 3)


class HeizungVolumeTotalSensor(_HeizungBase):
    _attr_state_class = SensorStateClass.TOTAL_INCREASING

    def __init__(self, c, e):
        super().__init__(c, e, "volume_total")
        fuel_label = FUEL_UNIT.get(_get_fuel_type(e), "L")
        self._attr_name = f"Verbrauch Gesamt ({fuel_label})"
        self._attr_native_unit_of_measurement = _volume_unit(e)
        self._attr_device_class = _volume_device_class(e)
        self._attr_icon = _volume_icon(e)

    @property
    def native_value(self) -> float:
        return round(self._coordinator.volume_total, 3)
