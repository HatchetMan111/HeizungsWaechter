"""Config flow for Heizungsüberwachung."""
from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import selector
import homeassistant.helpers.config_validation as cv

from .const import (
    DOMAIN,
    CONF_TEMPERATURE_SENSOR,
    CONF_TEMP_THRESHOLD,
    CONF_BURNER_POWER_KW,
    CONF_FUEL_TYPE,
    CONF_FUEL_PRICE_PER_KWH,
    CONF_EFFICIENCY,
    DEFAULT_TEMP_THRESHOLD,
    DEFAULT_EFFICIENCY,
    DEFAULT_NAME,
    FUEL_TYPES,
)


def _build_schema(defaults: dict) -> vol.Schema:
    return vol.Schema(
        {
            vol.Required("name", default=defaults.get("name", DEFAULT_NAME)): str,
            vol.Required(CONF_TEMPERATURE_SENSOR): selector.selector(
                {"entity": {"domain": "sensor", "device_class": "temperature"}}
            ),
            vol.Required(
                CONF_TEMP_THRESHOLD,
                default=defaults.get(CONF_TEMP_THRESHOLD, DEFAULT_TEMP_THRESHOLD),
            ): selector.selector(
                {"number": {"min": 30, "max": 300, "step": 1, "unit_of_measurement": "°C", "mode": "box"}}
            ),
            vol.Required(
                CONF_BURNER_POWER_KW,
                default=defaults.get(CONF_BURNER_POWER_KW, 18.0),
            ): selector.selector(
                {"number": {"min": 1, "max": 500, "step": 0.1, "unit_of_measurement": "kW", "mode": "box"}}
            ),
            vol.Required(
                CONF_FUEL_TYPE,
                default=defaults.get(CONF_FUEL_TYPE, "heizoel"),
            ): selector.selector(
                {"select": {"options": [{"value": k, "label": v} for k, v in FUEL_TYPES.items()]}}
            ),
            vol.Required(
                CONF_FUEL_PRICE_PER_KWH,
                default=defaults.get(CONF_FUEL_PRICE_PER_KWH, 0.10),
            ): selector.selector(
                {"number": {"min": 0.001, "max": 10.0, "step": 0.001, "unit_of_measurement": "€/kWh", "mode": "box"}}
            ),
            vol.Required(
                CONF_EFFICIENCY,
                default=defaults.get(CONF_EFFICIENCY, DEFAULT_EFFICIENCY),
            ): selector.selector(
                {"number": {"min": 50, "max": 110, "step": 1, "unit_of_measurement": "%", "mode": "box"}}
            ),
        }
    )


def _options_schema(defaults: dict) -> vol.Schema:
    return vol.Schema(
        {
            vol.Required(
                CONF_TEMP_THRESHOLD,
                default=defaults.get(CONF_TEMP_THRESHOLD, DEFAULT_TEMP_THRESHOLD),
            ): selector.selector(
                {"number": {"min": 30, "max": 300, "step": 1, "unit_of_measurement": "°C", "mode": "box"}}
            ),
            vol.Required(
                CONF_BURNER_POWER_KW,
                default=defaults.get(CONF_BURNER_POWER_KW, 18.0),
            ): selector.selector(
                {"number": {"min": 1, "max": 500, "step": 0.1, "unit_of_measurement": "kW", "mode": "box"}}
            ),
            vol.Required(
                CONF_FUEL_TYPE,
                default=defaults.get(CONF_FUEL_TYPE, "heizoel"),
            ): selector.selector(
                {"select": {"options": [{"value": k, "label": v} for k, v in FUEL_TYPES.items()]}}
            ),
            vol.Required(
                CONF_FUEL_PRICE_PER_KWH,
                default=defaults.get(CONF_FUEL_PRICE_PER_KWH, 0.10),
            ): selector.selector(
                {"number": {"min": 0.001, "max": 10.0, "step": 0.001, "unit_of_measurement": "€/kWh", "mode": "box"}}
            ),
            vol.Required(
                CONF_EFFICIENCY,
                default=defaults.get(CONF_EFFICIENCY, DEFAULT_EFFICIENCY),
            ): selector.selector(
                {"number": {"min": 50, "max": 110, "step": 1, "unit_of_measurement": "%", "mode": "box"}}
            ),
        }
    )


class HeizungMonitorConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle the config flow for Heizungsüberwachung."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}

        if user_input is not None:
            # Validate sensor exists
            state = self.hass.states.get(user_input[CONF_TEMPERATURE_SENSOR])
            if state is None:
                errors[CONF_TEMPERATURE_SENSOR] = "sensor_not_found"
            elif user_input[CONF_BURNER_POWER_KW] <= 0:
                errors[CONF_BURNER_POWER_KW] = "invalid_power"
            else:
                await self.async_set_unique_id(
                    f"{DOMAIN}_{user_input[CONF_TEMPERATURE_SENSOR]}"
                )
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=user_input.get("name", DEFAULT_NAME),
                    data=user_input,
                )

        return self.async_show_form(
            step_id="user",
            data_schema=_build_schema({}),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return HeizungMonitorOptionsFlow(config_entry)


class HeizungMonitorOptionsFlow(config_entries.OptionsFlow):
    """Handle options flow (edit settings after setup)."""

    def __init__(self, config_entry):
        self._config_entry = config_entry

    async def async_step_init(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current = {**self._config_entry.data, **self._config_entry.options}
        return self.async_show_form(
            step_id="init",
            data_schema=_options_schema(current),
        )
