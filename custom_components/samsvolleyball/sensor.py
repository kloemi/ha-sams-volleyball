"""The sams volleyball sensor platform."""

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, CALLBACK_TYPE, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import slugify

from . import SamsDataCoordinator
from .const import (
    CONF_TEAM,
    DOMAIN,
    DEFAULT_ICON,
    VOLLEYBALL,
)

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the sams volleyball sensor platform."""
    coordinator  = hass.data[DOMAIN][entry.unique_id]

    # Create entities list.
    entities = [
        SamsTeamTracker(coordinator, entry),
    ]

    # Add sensor entities.
    async_add_entities(entities, True)

class SamsTeamTracker(CoordinatorEntity):
    """Representation of a Sensor to provide team tracker compatible data."""

    def __init__(self,
                 coordinator: SamsDataCoordinator,
                 entry: ConfigEntry,
    ) -> None:
        """Initialize sensor base entity."""
        super().__init__(coordinator)

        self._coordinator = coordinator
        self._name = entry.data[CONF_TEAM]
        self._config = entry
        self._state = "PRE"

        self._sport = VOLLEYBALL
        self._league = None
        self._league_logo = None
        self._team_abbr = None
        self._opponent_abbr = None

        self._event_name = None
        self._date = None
        self._kickoff_in = None
        self._venue = None
        self._location = None
        self._tv_network = None
        self._odds = None
        self._overunder = None

        self._team_name = None
        self._team_id = None
        self._team_record = None
        self._team_rank = None
        self._team_homeaway = None
        self._team_logo = None
        self._team_colors = None
        self._team_score = None
        self._team_win_probability = None
        self._team_winner = None
        self._team_timeouts = None

        self._opponent_name = None
        self._opponent_id = None
        self._opponent_record = None
        self._opponent_rank = None
        self._opponent_homeaway = None
        self._opponent_logo = None
        self._opponent_colors = None
        self._opponent_score = None
        self._opponent_win_probability = None
        self._opponent_winner = None
        self._opponent_timeouts = None

        self._quarter = None
        self._clock = None
        self._possession = None
        self._last_play = None
        self._down_distance_text = None

        self._outs = None
        self._balls = None
        self._strikes = None
        self._on_first = None
        self._on_second = None
        self._on_third = None

        self._team_shots_on_target = None
        self._team_total_shots = None
        self._opponent_shots_on_target = None
        self._opponent_total_shots = None

        self._team_sets_won = None
        self._opponent_sets_won = None

        self._last_update = None
        self._api_message = None

    @property
    def unique_id(self) -> str:
        """
        Return a unique, Home Assistant friendly identifier for this entity.
        """
        return f"{slugify(self._name)}_{self._config.entry_id}"

    @property
    def name(self) -> str:
        """Return the name of the sensor."""
        return self._name

    @property
    def state(self) -> str:
        return self._state

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.coordinator.last_update_success

    @property
    def icon(self) -> str:
        """Return the icon to use in the frontend, if any."""
        return DEFAULT_ICON
