"""Config flow for samsvolleyball integration."""
from __future__ import annotations

import logging
import json
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.const import CONF_NAME
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.aiohttp_client import async_get_clientsession

import urllib.parse

from . import SamsDataCoordinator
from .utils import get_leaguelist, get_teamlist

from .const import (
    DOMAIN,
    DEFAULT_OPTIONS,
    CONF_HOST,
    CONF_LEAGUE,
    CONF_REGION,
    CONF_REGION_LIST,
    CONF_TEAM_NAME,
    CONFIG_ENTRY_VERSION,
)

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_NAME, default=DEFAULT_OPTIONS[CONF_NAME]): str,
        vol.Required(CONF_HOST, default=DEFAULT_OPTIONS[CONF_HOST]): str,
        vol.Required(CONF_REGION, default=DEFAULT_OPTIONS[CONF_REGION]): vol.In(CONF_REGION_LIST),
    }
)

STEP_TEAM_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_TEAM_NAME, default=DEFAULT_OPTIONS[CONF_TEAM_NAME]): str,
    }
)

async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect.

    Data has the keys from STEP_USER_DATA_SCHEMA with values provided by the user.
    """

    url = urllib.parse.urljoin(data[CONF_HOST], data[CONF_REGION])
    session = async_get_clientsession(hass)
    coordinator = SamsDataCoordinator(hass, session, "ConfigValidate", url)

    try:
        data = await coordinator.data_received()
    except Exception as exc:
        raise CannotConnect from exc
    if not data:
        raise InvalidData

    leagues = get_leaguelist(data)
    if 0 == len(leagues):
       raise InvalidData

    # Return info that you want to store in the config entry.
    return data, leagues

class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for samsvolleyball."""

    VERSION = CONFIG_ENTRY_VERSION

    _cfg_data: Optional[Dict[str, Any]]
    _data = None
    _leagues: dict[str, str] = None
    _teams: dict[str, str] = None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                self._data, self._leagues = await validate_input(self.hass, user_input)
                self._cfg_data = user_input
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
                return await self.async_step_league()

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )

    async def async_step_league(
            self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            league_id = self._leagues[user_input[CONF_LEAGUE]]
            self._teams = get_teamlist(self._data, league_id)
            if 0 == len(self._teams):
                errors["base"] = "no_teams"
            else:
                self._cfg_data[CONF_LEAGUE] = user_input[CONF_LEAGUE]
                return await self.async_step_team()

        step_league_schema = vol.Schema(
            {
                vol.Required(CONF_LEAGUE): vol.In(list(self._leagues.keys())),
            }
        )
        return self.async_show_form(
            step_id="league", data_schema=step_league_schema, errors=errors
        )

    async def async_step_team(
            self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:

        if user_input is not None:
            self._cfg_data[CONF_TEAM_NAME] = user_input[CONF_TEAM_NAME]
            devicename = user_input[CONF_TEAM_NAME] + ' ' + self._cfg_data[CONF_REGION].capitalize()
            return self.async_create_entry(title=devicename, data=self._cfg_data)

        step_team_schema = vol.Schema(
            {
                vol.Required(CONF_TEAM_NAME): vol.In(list(self._teams.keys())),
            }
        )
        return self.async_show_form(
            step_id="team", data_schema=step_team_schema
        )



class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""

class InvalidData(HomeAssistantError):
    """Error to indicate we received invalid data."""

class TeamNotFound(HomeAssistantError):
    """Error to indicate the school is not found."""