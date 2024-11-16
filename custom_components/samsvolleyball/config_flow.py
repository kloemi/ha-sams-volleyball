"""Config flow for samsvolleyball integration."""
from __future__ import annotations

import logging
import urllib.parse
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import selector
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from . import SamsDataCoordinator
from .const import (
    CONF_GENDER,
    CONF_GENDER_FEMALE,
    CONF_GENDER_LIST,
    CONF_GENDER_MALE,
    CONF_GENDER_MIXED,
    CONF_HOST,
    CONF_LEAGUE,
    CONF_LEAGUE_NAME,
    CONF_REGION,
    CONF_REGION_LIST,
    CONF_TEAM_NAME,
    CONF_TEAM_UUID,
    CONFIG_ENTRY_VERSION,
    DEFAULT_OPTIONS,
    URL_GET,
)
from .utils import SamsUtils

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST, default=DEFAULT_OPTIONS[CONF_HOST]): str,
        vol.Required(
            CONF_REGION, default=DEFAULT_OPTIONS[CONF_REGION]
        ): selector.SelectSelector(
            selector.SelectSelectorConfig(
                options=CONF_REGION_LIST, translation_key=CONF_REGION
            ),
        ),
    }
)

GENDER_MAP = {
    "female": CONF_GENDER_FEMALE,
    "male": CONF_GENDER_MALE,
    "mixed": CONF_GENDER_MIXED,
}


async def validate_input(hass: HomeAssistant, data: dict[str, Any]):
    """Validate the user input allows us to connect.

    Data has the keys from STEP_USER_DATA_SCHEMA with values provided by the user.
    """

    url = urllib.parse.urljoin(data[CONF_HOST], data[CONF_REGION])
    get_url = urllib.parse.urljoin(URL_GET, data[CONF_REGION])
    session = async_get_clientsession(hass)
    coordinator = SamsDataCoordinator(hass, session, "ConfigValidate", url, get_url)

    try:
        data = await coordinator.get_initial_data()
    except Exception as exc:
        raise CannotConnect from exc
    if not data:
        raise InvalidData

    leagues = SamsUtils.get_leaguelist(data)
    if 0 == len(leagues):
        raise InvalidData

    # Return info that you want to store in the config entry.
    return data, leagues


class ConfigFlow(config_entries.ConfigFlow):
    """Handle a config flow for samsvolleyball."""

    VERSION = CONFIG_ENTRY_VERSION

    cfg_data: dict[str, Any] = {}
    data = None
    leagues: dict[str, str] = {}
    teams: dict[str, str] = {}

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                self.data, self.leagues = await validate_input(self.hass, user_input)
                self.cfg_data = user_input
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidData:
                errors["base"] = "invalid_data"
            except TeamNotFound:
                errors["base"] = "invalid_team"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                return await self.async_step_gender()

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )

    async def async_step_gender(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            self.cfg_data[CONF_GENDER] = GENDER_MAP[user_input[CONF_GENDER]]
            return await self.async_step_league()

        step_gender_schema = vol.Schema(
            {
                vol.Required(CONF_GENDER): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=CONF_GENDER_LIST, translation_key=CONF_GENDER
                    )
                )
            }
        )
        return self.async_show_form(
            step_id="gender", data_schema=step_gender_schema, errors=errors
        )

    async def async_step_league(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            league_id = user_input[CONF_LEAGUE]
            self.teams = SamsUtils.get_teamlist(self.data, league_id)
            self.cfg_data[CONF_LEAGUE_NAME] = SamsUtils.get_league_data(
                self.data, league_id, "name"
            )
            if 0 == len(self.teams):
                errors["base"] = "no_teams"
            else:
                self.cfg_data[CONF_LEAGUE] = user_input[CONF_LEAGUE]
                return await self.async_step_team()

        leagues_filter = SamsUtils.get_leaguelist(self.data, self.cfg_data[CONF_GENDER])
        league_select = []
        for league in leagues_filter:
            league_select.append({"label": league["name"], "value": league["id"]})

        step_league_schema = vol.Schema(
            {
                vol.Required(CONF_LEAGUE): selector.SelectSelector(
                    selector.SelectSelectorConfig(options=league_select)
                )
            }
        )
        return self.async_show_form(
            step_id="league", data_schema=step_league_schema, errors=errors
        )

    async def async_step_team(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        if user_input is not None:
            self.cfg_data[CONF_TEAM_NAME] = user_input[CONF_TEAM_NAME]
            team_id = self.teams[user_input[CONF_TEAM_NAME]]
            self.cfg_data[CONF_TEAM_UUID] = team_id

            devicename = (
                f"{user_input[CONF_TEAM_NAME]} ({self.cfg_data[CONF_LEAGUE_NAME]})"
            )
            return self.async_create_entry(title=devicename, data=self.cfg_data)

        step_team_schema = vol.Schema(
            {
                vol.Required(CONF_TEAM_NAME): vol.In(list(self.teams.keys())),
            }
        )
        return self.async_show_form(step_id="team", data_schema=step_team_schema)


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidData(HomeAssistantError):
    """Error to indicate we received invalid data."""


class TeamNotFound(HomeAssistantError):
    """Error to indicate the school is not found."""
