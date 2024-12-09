"""Constants for the samsvolleyball integration."""

from homeassistant.const import CONF_NAME, Platform

# Misc
DOMAIN = "samsvolleyball"
PLATFORMS = [Platform.SENSOR]

CONF_HOST = "host"
CONF_REGION = "region"
CONF_LEAGUE = "league"
CONF_GENDER = "gender"
CONF_GENDER_FEMALE = "FEMALE"
CONF_GENDER_MALE = "MALE"
CONF_GENDER_MIXED = "MIXED"
CONF_LEAGUE_NAME = "league_name"

CONF_TEAM_NAME = "team"
CONF_TEAM_UUID = "team_id"

CONFIG_ENTRY_VERSION = 1

DEFAULT_OPTIONS = {
    CONF_NAME: "Volleyball Tracker",
    CONF_HOST: "wss://backend.sams-ticker.de",
    CONF_REGION: "baden",
}

URL_GET = "https://backend.sams-ticker.de/live/tickers/"
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

CONF_GENDER_LIST = [
    "female",
    "male",
    "mixed",
]

LEAGUE_URL_LOGO_MAP = {
    "baden": "https://www.sbvv-online.de/cms/files/Baden_Dateien/layout/images/logos/logo_sbvv.png",
    "bvv": "https://vvb.sams-server.de/cms/files/VVB_Dateien/layout_homepage/logo/vvb_logo.jpg",
    "dvv": "https://www.volleyball-verband.de/?proxy=img/logo_dvv.png",
    "flvb": "https://flvb.lu/images/logos/FLVB%20Logo%2060%20ans%20SVG.svg",
    "hvbv": "https://www.hvbv.de/cms/files/hvbv/layout/images/logo.png",
    "hvv": "https://www.hessen-volley.de/cms/files/hvv/layout/images/logo/hvv-logo-internet-w.svg",
    "nwvv": "https://www.nwvv.de/cms/files/layout/images/nwvv_nvv-blau_transparent_426w.png",
    "shvv": "https://www.shvv.de/cms/files/shvv/layout/logos/shvv_logo_400.png",
    "ssvb": "https://www.ssvb.org/cms/files/SSVB_Dateien/layout/images/SSVB-Logo.png",
    "svv": "https://www.volley-saar.de/cms/files/SVV_Dateien/layout_homepage/images/logo/SVV%20Logo.jpg",
    "tvv": "https://www.tv-v.de/cms/files/TVV_Dateien/layout_homepage/images/logo/TVV_Logo.png",
    "vbl": "https://www.volleyball-bundesliga.de/cms/files/layout/images/vbl_logo_ohne_text_320x320.png",
    "vmv": "https://www.vmv24.de/srv/images/vmv-logo.gif",
    "vlw": "https://www.vlw-online.de/cms/files/VLW_Dateien/layout_homepage/images/logo/VLW_Logo.png",
    "vvb": "https://vvb.sams-server.de/cms/files/VVB_Dateien/layout_homepage/logo/vvb_logo.jpg",
    "vvrp": "https://www.vvrp.de/cms/files/VVRP_Dateien/layout/logos/Logo_VVRP.svg",
}

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
