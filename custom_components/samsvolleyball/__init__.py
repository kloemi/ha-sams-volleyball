"""The sams-volleyball integration."""
from __future__ import annotations
import asyncio
import logging
import json
import urllib.parse

from aiohttp import ClientSession, WSMessage, WSMsgType
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
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
    name = f"Sams Tracker {entry.data[CONF_REGION].capitalize()}"
    entry.unique_id = name
    url = urllib.parse.urljoin(entry.data[CONF_HOST], entry.data[CONF_REGION])

    if entry.data[CONF_REGION] in domain_data:
        # we already have a coordinator for that region
        coordinator = domain_data[entry.data[CONF_REGION]]
    else:
        #create new coordinator for the sams region
        session = async_get_clientsession(hass)
        coordinator  = SamsDataCoordinator(hass, session, name, url)
        domain_data[entry.data[CONF_REGION]] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        coordinator = hass.data[DOMAIN][entry.data[CONF_REGION]]
        if not coordinator.hasListener():
            coordinator = hass.data[DOMAIN].pop(entry.data[CONF_REGION])
            await coordinator.disconnect()
            _LOGGER.info(
                "Sams Volleyball Tracker removed coordinator for region %s ",
                entry.data[CONF_REGION],
            )
    return unload_ok

class SamsDataCoordinator(DataUpdateCoordinator):
    """Class to manage fetching sams ticker data. It is intantiated once per used region/websocket."""

    def __init__(self,
                 hass: HomeAssistant,
                 session: ClientSession,
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
        self.loop: asyncio.AbstractEventLoop = asyncio.get_event_loop()

        super().__init__(hass, _LOGGER, name=self.name)

    async def _async_update_data(self):
        if not self.ws or not self._connected:
            _LOGGER.debug("Connect to %s",self.websocket_url)
            await self.connect()

    async def _on_close(self):
        _LOGGER.debug("Connection closed")
        self._connected = False

    async def _on_open(self):
        _LOGGER.debug("Connection opened")
        self._connected = True

    async def _on_message(self, message: WSMessage):
        if message.type == WSMsgType.TEXT:
            data = json.loads(message.data)
            _LOGGER.debug("Received data: %s ", str(message)[1:500])
            self.async_set_updated_data(data)
        else:
            _LOGGER.info("Received unexpected message: %s ", str(message)[1:500])

    async def _process_messages(self):
        try:
            async for msg in self.ws:
                await self._on_message(msg)
        except RuntimeError:
            _LOGGER.info("Sams Websocket runtime error")
            await self._on_close()
        except ConnectionResetError:
            _LOGGER.info("Sams Websocket Connection Reset")
            await self._on_close()
        except Exception as exc:
            _LOGGER.warning("Error during processing new message: ",exc)

    async def data_received(self):
        try:
            ws = await self.session.ws_connect(self.websocket_url, autoclose=False)
            data = await ws.receive_json()
        finally:
            await ws.close()
        return data

    async def connect(self):
        try:
            self.ws = await self.session.ws_connect(self.websocket_url, autoclose=False)
        except Exception as exc:
            print(exc)
        self._ws_task = self.loop.create_task(self._process_messages())
        await self._on_open()

    async def disconnect(self):
        """Close web socket connection"""
        if self._ws_task is not None:
            self._ws_task.cancel()
            self._ws_task = None
        if self.ws is not None:
            await self.ws.close()
            self.ws = None

    def hasListener(self) -> bool:
        return len(self._listeners) > 0
