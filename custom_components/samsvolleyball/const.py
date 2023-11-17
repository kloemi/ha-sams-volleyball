"""Constants for the samsvolleyball integration."""
from homeassistant.const import CONF_NAME, Platform

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
    CONF_NAME: "Volleyball Tracker",
    CONF_HOST: "wss://backend.sams-ticker.de",
    CONF_REGION: "baden",
}

CONF_REGION_LIST = [
    "baden",
    "bvv",
    "dvv",
    "flvb",
    "hvbv",
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

TIMEOUT_PERIOD_CHECK = 30  # sec
NO_GAME = 0
NEAR_GAME = 1
IN_GAME = 2

TIMEOUT = {
    NO_GAME: 2 * 60 * 60,  # 2h min.
    NEAR_GAME: 12 * 60,  # 12 min.
    IN_GAME: 5 * 60,  # 5 min.
}

DEFAULT_ICON = "mdi:volleyball"
VOLLEYBALL = "volleyball"

VERSION = "v0.0.0"

ATTRIBUTION = "Data provided by sams-ticker"

STATES_IN = "IN"
STATES_NOT_FOUND = "NOT_FOUND"
STATES_PRE = "PRE"
STATES_POST = "POST"
