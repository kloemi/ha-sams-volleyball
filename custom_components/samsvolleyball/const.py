"""Constants for the samsvolleyball integration."""
from homeassistant.const import Platform

# Misc
DOMAIN = "samsvolleyball"
PLATFORMS = [Platform.SENSOR]

CONF_HOST = "host"
CONF_REGION = "region"
CONF_LEAGUE = "league"
CONF_LEAGUE_GENDER = "gender"
CONF_LEAGUE_NAME = "league_name"

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
    "bvv",
    "dvv",
    "flvb",
    "hvbh",
    "hvv",
    "nwvv",
    "shvv",
    "ssvb",
    "svv",
    "tvv",
    "vbl",
    "vmv",
    "vlw",
    "vvb",
    "vvrp",
]

DEFAULT_ICON = "mdi:volleyball"
VOLLEYBALL = "volleyball"

VERSION = "v0.0.0"

ATTRIBUTION = "Data provided by sams-ticker"

TICKER_TYPE = "FETCH_ASSOCIATION_TICKER_RESPONSE"
MATCH_TYPE = "MATCH_UPDATE"
