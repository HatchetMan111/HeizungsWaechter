"""Coordinator für HeizungsWächter – verwaltet Brenner-Zustand und Statistiken."""
from __future__ import annotations

import logging
from datetime import datetime

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from .const import (
    DOMAIN,
    CONF_TEMPERATURE_SENSOR,
    CONF_TEMP_THRESHOLD,
    CONF_BURNER_POWER_KW,
    CONF_FUEL_TYPE,
    CONF_FUEL_PRICE_PER_KWH,
    CONF_EFFICIENCY,
    FUEL_CALORIFIC,
    STORAGE_VERSION,
    STORAGE_KEY,
)

_LOGGER = logging.getLogger(__name__)


class HeizungsWaechterCoordinator:
    """Verwaltet den Brennerzustand und alle akkumulierten Statistiken."""

    def __init__(self, hass: HomeAssistant, entry) -> None:
        self.hass  = hass
        self.entry = entry
        self._store = Store(hass, STORAGE_VERSION, f"{STORAGE_KEY}_{entry.entry_id}")
        self._cfg: dict = {}

        # Brenner-Zustand
        self.burner_on: bool             = False
        self._burner_start: datetime | None = None
        self.current_session_s: float    = 0.0

        # Tageszähler
        self.runtime_today_s:  float = 0.0
        self.kwh_today:        float = 0.0
        self.cost_today:       float = 0.0
        self.volume_today:     float = 0.0
        self.cycles_today:     int   = 0

        # Monatszähler
        self.runtime_month_s:  float = 0.0
        self.kwh_month:        float = 0.0
        self.cost_month:       float = 0.0
        self.volume_month:     float = 0.0
        self.cycles_month:     int   = 0

        # Gesamtzähler
        self.runtime_total_s:  float = 0.0
        self.kwh_total:        float = 0.0
        self.cost_total:       float = 0.0
        self.volume_total:     float = 0.0
        self.cycles_total:     int   = 0

        # Rollover-Tracking
        self._last_date:  str = ""
        self._last_month: str = ""

        self._unsub = None

    # ── Konfiguration ──────────────────────────────────────────────────────── #

    def reload_config(self) -> None:
        self._cfg = {**self.entry.data, **self.entry.options}

    @property
    def _threshold(self) -> float:
        return float(self._cfg.get(CONF_TEMP_THRESHOLD, 60.0))

    @property
    def _power_kw(self) -> float:
        return float(self._cfg.get(CONF_BURNER_POWER_KW, 18.0))

    @property
    def _price(self) -> float:
        return float(self._cfg.get(CONF_FUEL_PRICE_PER_KWH, 0.10))

    @property
    def _efficiency(self) -> float:
        return float(self._cfg.get(CONF_EFFICIENCY, 85.0)) / 100.0

    @property
    def _fuel_type(self) -> str:
        return str(self._cfg.get(CONF_FUEL_TYPE, "heizoel"))

    @property
    def sensor_entity_id(self) -> str:
        return str(self._cfg.get(CONF_TEMPERATURE_SENSOR, ""))

    # ── Setup / Teardown ───────────────────────────────────────────────────── #

    async def async_setup(self) -> None:
        self.reload_config()
        await self._load()
        self._check_rollover()

        self._unsub = async_track_state_change_event(
            self.hass,
            [self.sensor_entity_id],
            self._on_sensor_change,
        )

        # Sofort aktuellen Zustand prüfen
        state = self.hass.states.get(self.sensor_entity_id)
        if state and state.state not in ("unknown", "unavailable"):
            try:
                self._update_burner(float(state.state))
            except ValueError:
                pass

    async def async_teardown(self) -> None:
        if self._unsub:
            self._unsub()
        await self._save()

    # ── Sensor-Änderung ────────────────────────────────────────────────────── #

    @callback
    def _on_sensor_change(self, event) -> None:
        new = event.data.get("new_state")
        if not new or new.state in ("unknown", "unavailable"):
            return
        try:
            temp = float(new.state)
        except ValueError:
            return
        self._check_rollover()
        self._update_burner(temp)
        self._fire_update()

    def _update_burner(self, temp: float) -> None:
        now      = dt_util.utcnow()
        was_on   = self.burner_on
        is_on    = temp >= self._threshold

        if is_on and not was_on:
            # Brenner springt AN
            self.burner_on      = True
            self._burner_start  = now
            self.cycles_today  += 1
            self.cycles_month  += 1
            self.cycles_total  += 1

        elif not is_on and was_on:
            # Brenner geht AUS
            self.burner_on = False
            if self._burner_start:
                elapsed = (now - self._burner_start).total_seconds()
                self._accumulate(elapsed)
                self._burner_start    = None
                self.current_session_s = 0.0

        elif is_on and was_on and self._burner_start:
            # Noch am laufen – live Session-Zeit aktualisieren
            self.current_session_s = (now - self._burner_start).total_seconds()

        self.hass.async_create_task(self._save())

    def _accumulate(self, seconds: float) -> None:
        """Laufzeit, kWh, Kosten und Volumen addieren."""
        hours    = seconds / 3600.0
        kwh      = self._power_kw * hours * self._efficiency
        cost     = kwh * self._price
        calorific = FUEL_CALORIFIC.get(self._fuel_type, 10.0)
        volume   = kwh / calorific

        self.runtime_today_s += seconds;  self.runtime_month_s += seconds;  self.runtime_total_s += seconds
        self.kwh_today       += kwh;      self.kwh_month       += kwh;      self.kwh_total       += kwh
        self.cost_today      += cost;     self.cost_month      += cost;     self.cost_total      += cost
        self.volume_today    += volume;   self.volume_month    += volume;   self.volume_total    += volume

    # ── Rollover ───────────────────────────────────────────────────────────── #

    def _check_rollover(self) -> None:
        today = dt_util.now().strftime("%Y-%m-%d")
        month = dt_util.now().strftime("%Y-%m")

        if self._last_date and self._last_date != today:
            self.runtime_today_s = self.kwh_today = self.cost_today = self.volume_today = 0.0
            self.cycles_today = 0

        if self._last_month and self._last_month != month:
            self.runtime_month_s = self.kwh_month = self.cost_month = self.volume_month = 0.0
            self.cycles_month = 0

        self._last_date  = today
        self._last_month = month

    # ── Persistenz ─────────────────────────────────────────────────────────── #

    async def _load(self) -> None:
        data = await self._store.async_load()
        if not data:
            return
        self.runtime_today_s  = data.get("runtime_today_s",  0.0)
        self.runtime_month_s  = data.get("runtime_month_s",  0.0)
        self.runtime_total_s  = data.get("runtime_total_s",  0.0)
        self.kwh_today        = data.get("kwh_today",        0.0)
        self.kwh_month        = data.get("kwh_month",        0.0)
        self.kwh_total        = data.get("kwh_total",        0.0)
        self.cost_today       = data.get("cost_today",       0.0)
        self.cost_month       = data.get("cost_month",       0.0)
        self.cost_total       = data.get("cost_total",       0.0)
        self.volume_today     = data.get("volume_today",     0.0)
        self.volume_month     = data.get("volume_month",     0.0)
        self.volume_total     = data.get("volume_total",     0.0)
        self.cycles_today     = data.get("cycles_today",     0)
        self.cycles_month     = data.get("cycles_month",     0)
        self.cycles_total     = data.get("cycles_total",     0)
        self._last_date       = data.get("last_date",        "")
        self._last_month      = data.get("last_month",       "")

    async def _save(self) -> None:
        await self._store.async_save({
            "runtime_today_s":  self.runtime_today_s,
            "runtime_month_s":  self.runtime_month_s,
            "runtime_total_s":  self.runtime_total_s,
            "kwh_today":        self.kwh_today,
            "kwh_month":        self.kwh_month,
            "kwh_total":        self.kwh_total,
            "cost_today":       self.cost_today,
            "cost_month":       self.cost_month,
            "cost_total":       self.cost_total,
            "volume_today":     self.volume_today,
            "volume_month":     self.volume_month,
            "volume_total":     self.volume_total,
            "cycles_today":     self.cycles_today,
            "cycles_month":     self.cycles_month,
            "cycles_total":     self.cycles_total,
            "last_date":        self._last_date,
            "last_month":       self._last_month,
        })

    def _fire_update(self) -> None:
        self.hass.bus.async_fire(f"{DOMAIN}_updated_{self.entry.entry_id}")
