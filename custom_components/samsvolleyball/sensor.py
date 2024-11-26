"""The sams volleyball sensor platform."""
from __future__ import annotations

import locale
import logging
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_ATTRIBUTION
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util
from homeassistant.util import slugify

from . import SamsDataCoordinator
from .const import (
    ATTRIBUTION,
    CONF_GENDER,
    CONF_LEAGUE,
    CONF_LEAGUE_NAME,
    CONF_REGION,
    CONF_TEAM_NAME,
    CONF_TEAM_UUID,
    DEFAULT_ICON,
    DOMAIN,
    IN_GAME,
    LEAGUE_URL_LOGO_MAP,
    NEAR_GAME,
    NO_GAME,
    STATES_IN,
    STATES_NOT_FOUND,
    VOLLEYBALL,
)
from .utils import SamsUtils

_LOGGER = logging.getLogger(__name__)
SCAN_INTERVAL = timedelta(seconds=5)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the sams volleyball sensor platform."""
    coordinator = hass.data[DOMAIN][entry.data[CONF_REGION]]

    # Create entities list.
    entities = [
        SamsTeamTracker(hass, coordinator, entry),
    ]

    # Add sensor entities.
    async_add_entities(entities, update_before_add=False)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    return True


class SamsTeamTracker(CoordinatorEntity):
    """Representation of a sensor to provide team tracker compatible data."""

    def __init__(
        self,
        hass: HomeAssistant,
        coordinator: SamsDataCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize sensor base entity."""
        super().__init__(coordinator, context=self.get_active_state)

        self.hass = hass
        self._coordinator = coordinator
        self._name = entry.data[CONF_TEAM_NAME]
        self._team_uuid = [entry.data[CONF_TEAM_UUID]]
        self._team_league = entry.data[CONF_LEAGUE]
        self._league_name = entry.data[CONF_LEAGUE_NAME]
        self._team_gender = entry.data[CONF_GENDER]
        self._team = None
        self._match = None
        self._config = entry
        self._state = STATES_NOT_FOUND
        self._attr: dict[str, Any] = {}
        self._lang: str = ""
        self._ticker_data = None
        self._match_data = None
        self._changed = False

    async def async_added_to_hass(self) -> None:
        """Subscribe timer events."""
        await super().async_added_to_hass()
        try:
            self._lang = self.hass.config.language
        except Exception:  # pylint: disable=broad-except
            lang, _ = locale.getlocale()
            self._lang = lang or "en_US"
        _LOGGER.debug(
            f"Added entity {self.name} with coordinator {self._coordinator.name} listener {len(self._coordinator._listeners)}"
        )

    def _update_overview(self, data):
        _LOGGER.debug("Update team data for sensor %s", self._name)
        self._ticker_data = data
        self._changed = True
        uuid_list = SamsUtils.get_uuids_by_name(data, self._name, self._league_name)
        if len(uuid_list) == 0:
            _LOGGER.warning(
                f"No team data found for {self._name} - {self._league_name}"
            )
            return
        matches = []
        idx = 0
        while len(matches) == 0 and idx < len(uuid_list):
            matches = SamsUtils.get_matches(data, uuid_list[idx])
            idx += 1
        if len(matches) > 0:
            self._team_uuid = uuid_list[idx - 1]
            self._team, _ = SamsUtils.get_team_by_id(data, self._team_uuid)
            self._match = SamsUtils.select_match(data, matches)
            self._state = SamsUtils.state_from_match(data, self._match)
        else:
            self._team, _ = SamsUtils.get_team_by_id(data, uuid_list[0])
            self._state = STATES_NOT_FOUND
            self._match = None

    def get_active_state(self):
        # check if we are nearby (2 hours before / 3 hours behind)
        if self._state == STATES_IN:
            return IN_GAME
        elif self._match and "date" in self._attr:
            date = self._attr["date"]
            duration = (dt_util.now() - date).total_seconds()
            if (-2 * 60 * 60) < duration < (3 * 60 * 60):
                return NEAR_GAME
        return NO_GAME

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""

        data = self._coordinator.data
        if data is not None:
            if SamsUtils.is_overview(data):
                self._update_overview(data)
            elif SamsUtils.is_match(data):
                if self._match and SamsUtils.is_my_match(data, self._match):
                    self._match_data = SamsUtils.get_match_data(data)
                    self._changed = True
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
        if not self._changed:
            return self._attr

        self._attr[ATTR_ATTRIBUTION] = ATTRIBUTION
        self._attr["sport"] = VOLLEYBALL
        self._attr["league_logo"] = LEAGUE_URL_LOGO_MAP[self._config.data[CONF_REGION]]

        if self._ticker_data is None:
            return self._attr

        try:
            if self._match:
                self._attr = SamsUtils.fill_match_attributes(
                    self._attr, self._ticker_data, self._match, self._team, self._lang
                )
            else:
                if self._team:
                    self._attr = SamsUtils.fill_team_attributes(
                        self._attr, self._ticker_data, self._team, self._state
                    )
            if self._match_data:
                self._attr = SamsUtils.update_match_attributes(
                    self._attr, self._match_data
                )
        except Exception as e:
            _LOGGER.warning("Fill attributes - exception %s", e)
        self._changed = False
        return self._attr

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self._coordinator.last_update_success

    @property
    def icon(self) -> str:
        """Return the icon to use in the frontend, if any."""
        return DEFAULT_ICON

    @property
    def should_poll(self) -> bool:
        return True
