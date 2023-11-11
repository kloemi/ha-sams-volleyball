"""Config flow for samsvolleyball integration."""
from __future__ import annotations

import logging
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

from .const import (
    DOMAIN,
    DEFAULT_OPTIONS,
    CONF_HOST,
    CONF_REGION,
    CONF_TEAM_NAME,
    CONFIG_ENTRY_VERSION,
    CONF_REGION_LIST,
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

    #leagues = get_leaguelist(coordinator.data)
    #if not data:
    #   raise InvalidData

    devicename = data[CONF_TEAM_NAME] + ' ' + data[CONF_REGION].capitalize()
    # Return info that you want to store in the config entry.
    return {"title": devicename}

class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for samsvolleyball."""

    VERSION = CONFIG_ENTRY_VERSION

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                info = await validate_input(self.hass, user_input)
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
                return self.async_create_entry(title=info["title"], data=user_input)

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )

class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""

class InvalidData(HomeAssistantError):
    """Error to indicate we received invalid data."""

class TeamNotFound(HomeAssistantError):
    """Error to indicate the school is not found."""