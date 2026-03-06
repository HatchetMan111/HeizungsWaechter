"""Data coordinator for Heizungsüberwachung."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from .const import (
    DOMAIN,
    CONF_TEMPERATURE_SENSOR,
    CONF_TEMP_THRESHOLD,
    CONF_BURNER_POWER_KW,
    CONF_FUEL_PRICE_PER_KWH,
    CONF_EFFICIENCY,
    STORAGE_VERSION,
    STORAGE_KEY,
)

_LOGGER = logging.getLogger(__name__)


class HeizungCoordinator:
    """Tracks the burner state and accumulates statistics."""

    def __init__(self, hass: HomeAssistant, entry) -> None:
        self.hass = hass
        self.entry = entry
        self._store = Store(hass, STORAGE_VERSION, f"{STORAGE_KEY}_{entry.entry_id}")

        # Runtime config (merged from data + options)
        self._cfg: dict[str, Any] = {}

        # Live state
        self.burner_on: bool = False
        self._burner_start: datetime | None = None

        # Session accumulators (reset on HA restart, persistent via storage)
        self.runtime_today_s: float = 0.0
        self.runtime_month_s: float = 0.0
        self.runtime_total_s: float = 0.0
        self.kwh_today: float = 0.0
        self.kwh_month: float = 0.0
        self.kwh_total: float = 0.0
        self.cost_today: float = 0.0
        self.cost_month: float = 0.0
        self.cost_total: float = 0.0
        self.cycles_today: int = 0
        self.cycles_month: int = 0
        self.cycles_total: int = 0

        # Current session runtime (for live display)
        self.current_session_s: float = 0.0

        # Midnight tracking
        self._last_date: str = ""
        self._last_month: str = ""

        self._unsub_state = None
        self._unsub_midnight = None

    def _merge_config(self) -> None:
        self._cfg = {**self.entry.data, **self.entry.options}

    @property
    def threshold(self) -> float:
        return float(self._cfg.get(CONF_TEMP_THRESHOLD, 60.0))

    @property
    def power_kw(self) -> float:
        return float(self._cfg.get(CONF_BURNER_POWER_KW, 18.0))

    @property
    def price_per_kwh(self) -> float:
        return float(self._cfg.get(CONF_FUEL_PRICE_PER_KWH, 0.10))

    @property
    def efficiency(self) -> float:
        return float(self._cfg.get(CONF_EFFICIENCY, 85.0)) / 100.0

    @property
    def sensor_entity_id(self) -> str:
        return self._cfg.get(CONF_TEMPERATURE_SENSOR, "")

    async def async_setup(self) -> None:
        """Load stored data and subscribe to sensor changes."""
        self._merge_config()
        await self._async_load_storage()
        self._check_day_rollover()

        self._unsub_state = async_track_state_change_event(
            self.hass,
            [self.sensor_entity_id],
            self._handle_sensor_change,
        )

        # Also check the current state immediately
        state = self.hass.states.get(self.sensor_entity_id)
        if state and state.state not in ("unknown", "unavailable"):
            try:
                temp = float(state.state)
                self._update_burner_state(temp)
            except ValueError:
                pass

    async def async_teardown(self) -> None:
        """Unsubscribe and save."""
        if self._unsub_state:
            self._unsub_state()
        await self._async_save_storage()

    @callback
    def _handle_sensor_change(self, event) -> None:
        new_state = event.data.get("new_state")
        if new_state is None or new_state.state in ("unknown", "unavailable"):
            return
        try:
            temp = float(new_state.state)
        except ValueError:
            return

        self._check_day_rollover()
        self._update_burner_state(temp)
        self._notify_sensors()

    def _update_burner_state(self, temp: float) -> None:
        now = dt_util.utcnow()
        was_on = self.burner_on
        is_on = temp >= self.threshold

        if is_on and not was_on:
            # Burner just turned ON
            self.burner_on = True
            self._burner_start = now
            self.cycles_today += 1
            self.cycles_month += 1
            self.cycles_total += 1
            _LOGGER.debug("Burner ON – cycle start")

        elif not is_on and was_on:
            # Burner just turned OFF – record runtime
            self.burner_on = False
            if self._burner_start:
                elapsed = (now - self._burner_start).total_seconds()
                self._add_runtime(elapsed)
                self._burner_start = None
                self.current_session_s = 0.0
            _LOGGER.debug("Burner OFF – session recorded")

        elif is_on and was_on and self._burner_start:
            # Burner still running – update live session display
            self.current_session_s = (now - self._burner_start).total_seconds()

        self.hass.async_create_task(self._async_save_storage())

    def _add_runtime(self, seconds: float) -> None:
        """Add a completed run's seconds and compute kWh + cost."""
        self.runtime_today_s += seconds
        self.runtime_month_s += seconds
        self.runtime_total_s += seconds

        hours = seconds / 3600.0
        # kWh = power × hours × efficiency (actual heat delivered)
        kwh = self.power_kw * hours * self.efficiency
        cost = kwh * self.price_per_kwh

        self.kwh_today += kwh
        self.kwh_month += kwh
        self.kwh_total += kwh
        self.cost_today += cost
        self.cost_month += cost
        self.cost_total += cost

    def _check_day_rollover(self) -> None:
        today = dt_util.now().strftime("%Y-%m-%d")
        month = dt_util.now().strftime("%Y-%m")

        if self._last_date and self._last_date != today:
            # New day – reset daily counters
            self.runtime_today_s = 0.0
            self.kwh_today = 0.0
            self.cost_today = 0.0
            self.cycles_today = 0
            _LOGGER.info("Day rollover – daily stats reset")

        if self._last_month and self._last_month != month:
            # New month – reset monthly counters
            self.runtime_month_s = 0.0
            self.kwh_month = 0.0
            self.cost_month = 0.0
            self.cycles_month = 0
            _LOGGER.info("Month rollover – monthly stats reset")

        self._last_date = today
        self._last_month = month

    # ------------------------------------------------------------------ #
    #  Persistent storage                                                  #
    # ------------------------------------------------------------------ #

    async def _async_load_storage(self) -> None:
        data = await self._store.async_load()
        if not data:
            return
        self.runtime_today_s = data.get("runtime_today_s", 0.0)
        self.runtime_month_s = data.get("runtime_month_s", 0.0)
        self.runtime_total_s = data.get("runtime_total_s", 0.0)
        self.kwh_today = data.get("kwh_today", 0.0)
        self.kwh_month = data.get("kwh_month", 0.0)
        self.kwh_total = data.get("kwh_total", 0.0)
        self.cost_today = data.get("cost_today", 0.0)
        self.cost_month = data.get("cost_month", 0.0)
        self.cost_total = data.get("cost_total", 0.0)
        self.cycles_today = data.get("cycles_today", 0)
        self.cycles_month = data.get("cycles_month", 0)
        self.cycles_total = data.get("cycles_total", 0)
        self._last_date = data.get("last_date", "")
        self._last_month = data.get("last_month", "")

    async def _async_save_storage(self) -> None:
        await self._store.async_save(
            {
                "runtime_today_s": self.runtime_today_s,
                "runtime_month_s": self.runtime_month_s,
                "runtime_total_s": self.runtime_total_s,
                "kwh_today": self.kwh_today,
                "kwh_month": self.kwh_month,
                "kwh_total": self.kwh_total,
                "cost_today": self.cost_today,
                "cost_month": self.cost_month,
                "cost_total": self.cost_total,
                "cycles_today": self.cycles_today,
                "cycles_month": self.cycles_month,
                "cycles_total": self.cycles_total,
                "last_date": self._last_date,
                "last_month": self._last_month,
            }
        )

    def _notify_sensors(self) -> None:
        """Fire an event so sensors can update."""
        self.hass.bus.async_fire(f"{DOMAIN}_updated_{self.entry.entry_id}")

    def reload_config(self) -> None:
        self._merge_config()
