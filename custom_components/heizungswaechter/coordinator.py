"""Coordinator für HeizungsWächter – verwaltet Brenner-Zustand und Statistiken."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.event import (
    async_track_state_change_event,
    async_track_time_interval,
)
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

# Verzögertes Schreiben (Sekunden) – schützt die SSD und schreibt
# trotzdem zuverlässig beim Shutdown (Store-Final-Write).
SAVE_DELAY = 60.0
UPDATE_INTERVAL = timedelta(minutes=1)


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

        self._unsub_sensor   = None
        self._unsub_interval = None

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

        self._unsub_sensor = async_track_state_change_event(
            self.hass,
            [self.sensor_entity_id],
            self._on_sensor_change,
        )
        # Minütlicher Takt: Rollover, Live-Session und Persistenz,
        # auch wenn der Zigbee-Sensor lange nichts meldet.
        self._unsub_interval = async_track_time_interval(
            self.hass, self._on_interval, UPDATE_INTERVAL
        )

        # Aktuellen Zustand übernehmen (auch nach HA-Neustart, ohne
        # eine Phantom-Taktung zu zählen)
        temp = self._read_sensor_temp()
        if temp is not None:
            self._sync_burner_state(temp)

    async def async_teardown(self) -> None:
        if self._unsub_sensor:
            self._unsub_sensor()
            self._unsub_sensor = None
        if self._unsub_interval:
            self._unsub_interval()
            self._unsub_interval = None
        await self._save()

    def resubscribe(self) -> None:
        """Sensor-Abo erneuern, wenn der konfigurierte Sensor gewechselt hat."""
        if self._unsub_sensor:
            self._unsub_sensor()
        self._unsub_sensor = async_track_state_change_event(
            self.hass,
            [self.sensor_entity_id],
            self._on_sensor_change,
        )
        # Laufende Session abschließen, bevor der neue Sensor übernommen wird
        if self.burner_on and self._burner_start:
            elapsed = (dt_util.utcnow() - self._burner_start).total_seconds()
            self._accumulate(elapsed)
        temp = self._read_sensor_temp()
        if temp is not None:
            self._sync_burner_state(temp)

    # ── Sensor-Änderung / Takt ─────────────────────────────────────────────── #

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

    @callback
    def _on_interval(self, _now) -> None:
        self._check_rollover()
        if self.burner_on and self._burner_start:
            self.current_session_s = (
                dt_util.utcnow() - self._burner_start
            ).total_seconds()
        self._schedule_save()
        self._fire_update()

    def _read_sensor_temp(self) -> float | None:
        state = self.hass.states.get(self.sensor_entity_id)
        if state and state.state not in ("unknown", "unavailable"):
            try:
                return float(state.state)
            except ValueError:
                return None
        return None

    def _sync_burner_state(self, temp: float) -> None:
        """Brennerzustand ohne Zählung setzen (Setup / Sensorwechsel).

        Nach einem Neustart ist die ursprüngliche Startzeit unbekannt –
        die Session-Zeit beginnt daher bei null.
        """
        is_on = temp >= self._threshold
        self.burner_on = is_on
        if is_on:
            self._burner_start = dt_util.utcnow()
        else:
            self._burner_start = None
            self.current_session_s = 0.0

    def _update_burner(self, temp: float) -> None:
        now    = dt_util.utcnow()
        was_on = self.burner_on
        is_on  = temp >= self._threshold

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
            self._burner_start     = None
            self.current_session_s = 0.0

        elif is_on and was_on and self._burner_start:
            # Noch am laufen – live Session-Zeit aktualisieren
            self.current_session_s = (now - self._burner_start).total_seconds()

        if is_on != was_on:
            # Übergänge umgehend (debounced) sichern
            self._schedule_save()

    def _accumulate(self, seconds: float) -> None:
        """Laufzeit, Brennstoff-Energie, Kosten und Volumen addieren.

        Die Brennerleistung vom Typenschild ist die Nennwärmeleistung
        (Abgabe). Der verbrauchte Brennstoff ergibt sich daraus über den
        Wirkungsgrad:  kWh = P × h / η
        """
        hours     = seconds / 3600.0
        effective = max(self._efficiency, 0.1)  # Schutz vor Division durch 0
        kwh       = self._power_kw * hours / effective
        cost      = kwh * self._price
        calorific = FUEL_CALORIFIC.get(self._fuel_type, 10.0)
        volume    = kwh / calorific

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

    def _schedule_save(self, delay: float = SAVE_DELAY) -> None:
        """Debounced Persistenz – schreibt spätestens beim HA-Shutdown."""
        self.hass.async_create_task(
            self._store.async_delay_save(self._snapshot, delay)
        )

    def _snapshot(self) -> dict:
        return {
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
            "burner_on":        self.burner_on,
            "last_date":        self._last_date,
            "last_month":       self._last_month,
        }

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
        self.burner_on        = bool(data.get("burner_on",   False))
        self._last_date       = data.get("last_date",        "")
        self._last_month      = data.get("last_month",       "")

    async def _save(self) -> None:
        await self._store.async_save(self._snapshot())

    def _fire_update(self) -> None:
        self.hass.bus.async_fire(f"{DOMAIN}_updated_{self.entry.entry_id}")
