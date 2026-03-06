"""Constants for Heizungsüberwachung integration."""

DOMAIN = "heizungswaechter"
VERSION = "1.0.0"

# Config keys
CONF_TEMPERATURE_SENSOR = "temperature_sensor"
CONF_TEMP_THRESHOLD = "temp_threshold"
CONF_BURNER_POWER_KW = "burner_power_kw"
CONF_FUEL_TYPE = "fuel_type"
CONF_FUEL_PRICE_PER_KWH = "fuel_price_per_kwh"
CONF_EFFICIENCY = "efficiency"

# Defaults
DEFAULT_TEMP_THRESHOLD = 60.0   # °C – above this = burner is ON
DEFAULT_EFFICIENCY = 85.0        # %
DEFAULT_NAME = "Heizung"

# Fuel types with their kWh per liter/m³ (for reference display only)
FUEL_TYPES = {
    "heizoel": "Heizöl (EL)",
    "erdgas": "Erdgas (H-Gas)",
    "fluessiggas": "Flüssiggas (Propan/Butan)",
    "pellets": "Holzpellets",
}

# Typical calorific values (kWh per unit) – used for volume/mass calculation
FUEL_CALORIFIC = {
    "heizoel":     10.0,   # kWh/L
    "erdgas":      10.0,   # kWh/m³
    "fluessiggas": 12.8,   # kWh/kg
    "pellets":      4.8,   # kWh/kg
}

# Physical unit per fuel type (for display + energy dashboard)
FUEL_UNIT = {
    "heizoel":     "L",    # Liter
    "erdgas":      "m³",   # Kubikmeter
    "fluessiggas": "kg",   # Kilogramm
    "pellets":     "kg",   # Kilogramm
}

# Fuel types that use device_class GAS (m³) – HA Energie-Dashboard native
FUEL_GAS_TYPES = {"erdgas"}

# Fuel types best tracked via kWh in the energy dashboard
FUEL_KWH_TYPES = {"heizoel", "fluessiggas", "pellets"}

# Storage keys
STORAGE_VERSION = 1
STORAGE_KEY = f"{DOMAIN}.statistics"

# Update interval in seconds
UPDATE_INTERVAL = 30

# Platforms
PLATFORMS = ["sensor"]
