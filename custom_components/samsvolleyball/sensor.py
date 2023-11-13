"""The sams volleyball sensor platform."""
import json
import logging

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, CALLBACK_TYPE, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import slugify
from typing import Any

from . import SamsDataCoordinator
from .utils import (
    is_ticker,
    is_my_match,
    get_team,
    get_matches,
    select_match,
    state_from_match,
    fill_attributes,
    update_match_attributes,
)
from .const import (
    CONF_REGION,
    CONF_TEAM_NAME,
    CONF_TEAM_UUID,
    DOMAIN,
    DEFAULT_ICON,
    STATES_NOT_FOUND,
    STATES_PRE,
)

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the sams volleyball sensor platform."""
    coordinator  = hass.data[DOMAIN][entry.data[CONF_REGION]]

    # Create entities list.
    entities = [
        SamsTeamTracker(coordinator, entry),
    ]

    # Add sensor entities.
    async_add_entities(entities, True)

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:

    return True

class SamsTeamTracker(CoordinatorEntity):
    """Representation of a Sensor to provide team tracker compatible data."""

    def __init__(self,
                 coordinator: SamsDataCoordinator,
                 entry: ConfigEntry,
    ) -> None:
        """Initialize sensor base entity."""
        super().__init__(coordinator)

        self._coordinator = coordinator
        self._name = entry.data[CONF_TEAM_NAME]
        self._team_uuid = entry.data[CONF_TEAM_UUID]
        self._team = None
        self._match = None
        self._config = entry
        self._state = STATES_PRE
        self._attr = {}

    def update_team(self, data: json):
        _LOGGER.debug("Update team data for sensor %s", self._name)
        self._team = get_team(data, self._team_uuid)
        matches = get_matches(data, self._team_uuid)
        if len(matches) > 0:
            self._match = select_match(matches)
            self._state = state_from_match(data, self._match)
        else:
            self._state = STATES_NOT_FOUND
            self._match = None

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""

        data = self._coordinator.data
        if data is not None:
            if is_ticker(data):
                self.update_team(data)
        super()._handle_coordinator_update()

    @property
    def unique_id(self) -> str:
        """Return a unique, Home Assistant friendly identifier for this entity."""
        return f"{slugify(self._name)}_{self._config.entry_id}"

    @property
    def name(self) -> str:
        """Return the name of the sensor."""
        return self._name

    @property
    def state(self) -> str:
        return self._state

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the state message."""

        if self.coordinator.data is None:
            return self._attr

        data = self._coordinator.data
        if is_ticker(data):
            self._attr = fill_attributes(self._attr, data, self._match, self._team_uuid)
        if is_my_match(data, self._match):
            self._attr = update_match_attributes(self._attr, data, self._match, self._team_uuid)

        return self._attr

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self._coordinator.last_update_success

    @property
    def icon(self) -> str:
        """Return the icon to use in the frontend, if any."""
        return DEFAULT_ICON