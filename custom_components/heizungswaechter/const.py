"""Konstanten für HeizungsWächter."""
DOMAIN = "heizungswaechter"
VERSION = "1.2.0"

# Konfigurationsschlüssel
CONF_NAME                = "name"
CONF_TEMPERATURE_SENSOR  = "temperature_sensor"
CONF_TEMP_THRESHOLD      = "temp_threshold"
CONF_BURNER_POWER_KW     = "burner_power_kw"
CONF_FUEL_TYPE           = "fuel_type"
CONF_FUEL_PRICE_PER_KWH  = "fuel_price_per_kwh"
CONF_EFFICIENCY          = "efficiency"

# Standardwerte
DEFAULT_NAME            = "HeizungsWächter"
DEFAULT_TEMP_THRESHOLD  = 60.0   # °C
DEFAULT_EFFICIENCY      = 85.0   # %
DEFAULT_BURNER_POWER    = 18.0   # kW
DEFAULT_FUEL_PRICE      = 0.10   # €/kWh

# Brennstofftypen
FUEL_TYPES = {
    "heizoel":     "Heizöl (EL)",
    "erdgas":      "Erdgas (H-Gas)",
    "fluessiggas": "Flüssiggas (Propan/Butan)",
    "pellets":     "Holzpellets",
}

# Heizwert je Brennstoff (kWh pro Einheit)
FUEL_CALORIFIC = {
    "heizoel":     10.0,   # kWh/L
    "erdgas":      10.0,   # kWh/m³
    "fluessiggas": 12.8,   # kWh/kg
    "pellets":      4.8,   # kWh/kg
}

# Physikalische Einheit je Brennstoff
FUEL_UNIT = {
    "heizoel":     "L",
    "erdgas":      "m³",
    "fluessiggas": "kg",
    "pellets":     "kg",
}

# Brennstoffe mit HA device_class GAS (m³ → Energie-Dashboard)
FUEL_GAS_TYPES = {"erdgas"}

# Speicher
STORAGE_VERSION = 1
STORAGE_KEY     = f"{DOMAIN}.statistics"

# Plattformen
PLATFORMS = ["sensor"]
