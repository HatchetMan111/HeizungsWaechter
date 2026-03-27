"""Config Flow für HeizungsWächter.

Registriert die Integration im HA UI unter
Einstellungen → Geräte & Dienste → + Integration hinzufügen.
"""
from __future__ import annotations

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import (
    DOMAIN,
    CONF_NAME,
    CONF_TEMPERATURE_SENSOR,
    CONF_TEMP_THRESHOLD,
    CONF_BURNER_POWER_KW,
    CONF_FUEL_TYPE,
    CONF_FUEL_PRICE_PER_KWH,
    CONF_EFFICIENCY,
    DEFAULT_NAME,
    DEFAULT_TEMP_THRESHOLD,
    DEFAULT_EFFICIENCY,
    DEFAULT_BURNER_POWER,
    DEFAULT_FUEL_PRICE,
    FUEL_TYPES,
)


def _build_user_schema(defaults: dict) -> vol.Schema:
    """Formular für die Ersteinrichtung."""
    return vol.Schema(
        {
            # Name der Anlage
            vol.Required(
                CONF_NAME,
                default=defaults.get(CONF_NAME, DEFAULT_NAME),
            ): selector.TextSelector(
                selector.TextSelectorConfig(
                    type=selector.TextSelectorType.TEXT
                )
            ),

            # Zigbee-/Temperatursensor aus HA auswählen
            vol.Required(
                CONF_TEMPERATURE_SENSOR,
            ): selector.EntitySelector(
                selector.EntitySelectorConfig(
                    domain="sensor",
                    device_class="temperature",
                )
            ),

            # Ab welcher Temperatur gilt Brenner als AN
            vol.Required(
                CONF_TEMP_THRESHOLD,
                default=defaults.get(CONF_TEMP_THRESHOLD, DEFAULT_TEMP_THRESHOLD),
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=30,
                    max=300,
                    step=1,
                    unit_of_measurement="°C",
                    mode=selector.NumberSelectorMode.BOX,
                )
            ),

            # Brennerleistung vom Typenschild
            vol.Required(
                CONF_BURNER_POWER_KW,
                default=defaults.get(CONF_BURNER_POWER_KW, DEFAULT_BURNER_POWER),
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=1,
                    max=500,
                    step=0.1,
                    unit_of_measurement="kW",
                    mode=selector.NumberSelectorMode.BOX,
                )
            ),

            # Brennstofftyp auswählen
            vol.Required(
                CONF_FUEL_TYPE,
                default=defaults.get(CONF_FUEL_TYPE, "heizoel"),
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=[
                        selector.SelectOptionDict(value=k, label=v)
                        for k, v in FUEL_TYPES.items()
                    ],
                    mode=selector.SelectSelectorMode.LIST,
                )
            ),

            # Preis pro kWh
            vol.Required(
                CONF_FUEL_PRICE_PER_KWH,
                default=defaults.get(CONF_FUEL_PRICE_PER_KWH, DEFAULT_FUEL_PRICE),
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=0.001,
                    max=10.0,
                    step=0.001,
                    unit_of_measurement="€/kWh",
                    mode=selector.NumberSelectorMode.BOX,
                )
            ),

            # Wirkungsgrad des Brenners
            vol.Required(
                CONF_EFFICIENCY,
                default=defaults.get(CONF_EFFICIENCY, DEFAULT_EFFICIENCY),
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=50,
                    max=110,
                    step=1,
                    unit_of_measurement="%",
                    mode=selector.NumberSelectorMode.BOX,
                )
            ),
        }
    )


def _build_options_schema(defaults: dict) -> vol.Schema:
    """Formular für nachträgliche Änderungen (Optionen-Flow)."""
    return vol.Schema(
        {
            vol.Required(
                CONF_TEMP_THRESHOLD,
                default=defaults.get(CONF_TEMP_THRESHOLD, DEFAULT_TEMP_THRESHOLD),
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=30,
                    max=300,
                    step=1,
                    unit_of_measurement="°C",
                    mode=selector.NumberSelectorMode.BOX,
                )
            ),
            vol.Required(
                CONF_BURNER_POWER_KW,
                default=defaults.get(CONF_BURNER_POWER_KW, DEFAULT_BURNER_POWER),
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=1,
                    max=500,
                    step=0.1,
                    unit_of_measurement="kW",
                    mode=selector.NumberSelectorMode.BOX,
                )
            ),
            vol.Required(
                CONF_FUEL_TYPE,
                default=defaults.get(CONF_FUEL_TYPE, "heizoel"),
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=[
                        selector.SelectOptionDict(value=k, label=v)
                        for k, v in FUEL_TYPES.items()
                    ],
                    mode=selector.SelectSelectorMode.LIST,
                )
            ),
            vol.Required(
                CONF_FUEL_PRICE_PER_KWH,
                default=defaults.get(CONF_FUEL_PRICE_PER_KWH, DEFAULT_FUEL_PRICE),
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=0.001,
                    max=10.0,
                    step=0.001,
                    unit_of_measurement="€/kWh",
                    mode=selector.NumberSelectorMode.BOX,
                )
            ),
            vol.Required(
                CONF_EFFICIENCY,
                default=defaults.get(CONF_EFFICIENCY, DEFAULT_EFFICIENCY),
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=50,
                    max=110,
                    step=1,
                    unit_of_measurement="%",
                    mode=selector.NumberSelectorMode.BOX,
                )
            ),
        }
    )


class HeizungsWaechterConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Vollständiger UI Config Flow für HeizungsWächter.

    HA erkennt diesen Flow automatisch durch:
      - "config_flow": true  im manifest.json
      - Klassenname endet auf ConfigFlow
      - domain=DOMAIN  im Klassen-Dekorator
    """

    VERSION = 1

    async def async_step_user(
        self, user_input: dict | None = None
    ) -> config_entries.FlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            # Sensor-Existenz prüfen
            state = self.hass.states.get(user_input[CONF_TEMPERATURE_SENSOR])
            if state is None:
                errors[CONF_TEMPERATURE_SENSOR] = "sensor_not_found"
            else:
                # Duplikat verhindern: gleicher Sensor darf nur einmal verwendet werden
                await self.async_set_unique_id(
                    f"{DOMAIN}_{user_input[CONF_TEMPERATURE_SENSOR]}"
                )
                self._abort_if_unique_id_configured()

                return self.async_create_entry(
                    title=user_input.get(CONF_NAME, DEFAULT_NAME),
                    data=user_input,
                )

        return self.async_show_form(
            step_id="user",
            data_schema=_build_user_schema(user_input or {}),
            errors=errors,
            description_placeholders={
                "docs_url": "https://github.com/HatchetMan111/HeizungsWaechter"
            },
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        return HeizungsWaechterOptionsFlow(config_entry)


class HeizungsWaechterOptionsFlow(config_entries.OptionsFlow):
    """Optionen-Flow: Einstellungen nachträglich im UI ändern."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self._entry = config_entry

    async def async_step_init(
        self, user_input: dict | None = None
    ) -> config_entries.FlowResult:
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        # Aktuelle Werte (data + options zusammenführen) als Vorbelegung
        current = {**self._entry.data, **self._entry.options}
        return self.async_show_form(
            step_id="init",
            data_schema=_build_options_schema(current),
        )
