"""The sams-volleyball integration."""
from __future__ import annotations
import asyncio
import aiohttp
import logging
import json
import urllib.parse
import websockets

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.components.sensor import PLATFORM_SCHEMA
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    CONF_HOST,
    CONF_REGION,
    DOMAIN,
    PLATFORMS,
    VERSION,
)

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up sams-volleyball from a config entry."""
    _LOGGER.info(
        "Sams Volleyball Tracker version %s is starting!",
        VERSION,
    )

    domain_data = hass.data.setdefault(DOMAIN, {})
    name = entry.data[CONF_NAME] + " " + entry.data[CONF_REGION].capitalize()
    entry.unique_id = name
    url = urllib.parse.urljoin(entry.data[CONF_HOST], entry.data[CONF_REGION])

    session = async_get_clientsession(hass)

    coordinator  = SamsDataCoordinator(hass, session, name, url)
    domain_data[entry.unique_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.unique_id)

    return unload_ok

class SamsDataCoordinator(DataUpdateCoordinator):
    """Class to manage fetching sams ticker data."""

    def __init__(self,
                 hass: HomeAssistant,
                 session: aiohttp.ClientSession,
                 name,
                 websocket_url
                 ) -> None:
        """ init websocket instance"""
        self.hass = hass
        self.session = session
        self.name =  name
        self.websocket_url = websocket_url
        self.ws = None
        self._connected = False
        self._ws_task = None

        super().__init__(hass, _LOGGER, name=self.name)


    async def _async_update_data(self):
        _LOGGER.debug("Async update")
        if not self.ws or False == self._connected:
            _LOGGER.debug("Connect to %s",self.websocket_url)
            await self.async_connect()

    async def _on_message(self, message: str):
        data = json.loads(message)
        _LOGGER.debug("Received data: %s ", message[1:200])
        self.async_set_updated_data(data)

    async def _on_close(self):
        _LOGGER.debug("Connection closed")
        self._connected = False

    async def _on_open(self):
        _LOGGER.debug("Connection opened")
        self._connected = True

    async def run_websocket(self):
        try:
            async with self.session.ws_connect(self.websocket_url) as ws:
                await self._on_open()
                async for msg in ws:
                    await self._on_message(msg.data)
        except aiohttp.ClientConnectionError:
            _LOGGER.info("Connection closed")
        finally:
            await self._on_close()

    async def async_connect(self):
        try:
            await self.run_websocket()
        finally:
            await self.session.close()