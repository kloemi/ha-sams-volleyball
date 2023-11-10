"""Constants for the samsvolleyball integration."""
from homeassistant.const import Platform

# Misc
DOMAIN = "samsvolleyball"
PLATFORMS = [Platform.SENSOR]

CONF_HOST = "host"
CONF_REGION = "region"
CONF_TEAM = "team"

CONFIG_ENTRY_VERSION = 1

DEFAULT_OPTIONS = {
    "name": "Volleyball Tracker",
    CONF_HOST: "wss://backend.sams-ticker.de",
    CONF_REGION: "baden",
    CONF_TEAM: "FT 1844 Freiburg 4",
}

DEFAULT_ICON = "mdi:volleyball"
VOLLEYBALL = "volleyball"

VERSION = "v0.0.0"