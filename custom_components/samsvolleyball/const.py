"""Constants for the samsvolleyball integration."""
from homeassistant.const import Platform

# Misc
DOMAIN = "samsvolleyball"
PLATFORMS = [Platform.SENSOR]

CONF_HOST = "host"
CONF_REGION = "region"
CONF_LEAGUE = "league"
CONF_TEAM_NAME = "team"
CONF_TEAM_UUID = "team_id"

CONFIG_ENTRY_VERSION = 1

DEFAULT_OPTIONS = {
    "name": "Volleyball Tracker",
    CONF_HOST: "wss://backend.sams-ticker.de",
    CONF_REGION: "baden",
    CONF_TEAM_NAME: "FT 1844 Freiburg 4",
}

CONF_REGION_LIST = [
    "baden",
    "dvv",
    "vbl",
    "unknonwn",
]

DEFAULT_ICON = "mdi:volleyball"
VOLLEYBALL = "volleyball"

VERSION = "v0.0.0"

ATTRIBUTION = "Data provided by sams"

TICKER_TYPE = "FETCH_ASSOCIATION_TICKER_RESPONSE"
MATCH_TYPE = "MATCH_UPDATE"