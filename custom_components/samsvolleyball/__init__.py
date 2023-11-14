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
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_util

from .const import (
    CONF_HOST,
    CONF_REGION,
    DOMAIN,
    NO_GAME_TIMEOUT,
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
        self.ws_task = None
        self.last_receive_ts = dt_util.as_timestamp(dt_util.utcnow())
        self.connected = False
        self.loop: asyncio.AbstractEventLoop = asyncio.get_event_loop()
        self.receive_timout = NO_GAME_TIMEOUT

        super().__init__(hass, _LOGGER, name=self.name)

    async def _async_update_data(self):
        if not self.ws or not self.connected:
            _LOGGER.debug("Connect to %s",self.websocket_url)
            await self.connect()

    async def _on_close(self):
        _LOGGER.debug("Connection closed")
        self.connected = False

    async def _on_open(self):
        _LOGGER.debug("Connection opened")
        self.connected = True

    async def _on_message(self, message: WSMessage):
        if message.type == WSMsgType.TEXT:
            data = json.loads(message.data)
            _LOGGER.debug("Received data: %s ", str(message)[1:500])
            self.async_set_updated_data(data)
            self.last_receive_ts = dt_util.as_timestamp(dt_util.utcnow())
        else:
            _LOGGER.info("Received unexpected message: %s ", str(message)[1:500])

    async def _process_messages(self):
        try:
            async for msg in self.ws:
                await self._on_message(msg)
        except RuntimeError as exc:
            _LOGGER.warning("Sams Websocket runtime error %s", exc)
            await self._on_close()
        except ConnectionResetError:
            _LOGGER.info("Sams Websocket Connection Reset")
            await self._on_close()
#        except Exception as exc:
#            _LOGGER.warning("Error during processing new message: %s", exc.with_traceback())

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
            self.ws_task = self.loop.create_task(self._process_messages())
            await self._on_open()
        except Exception as exc:
            _LOGGER.warning("Error during processing new message: %s", exc)
            self.disconnect()

    async def disconnect(self):
        """Close web socket connection"""
        if self.ws_task is not None:
            self.ws_task.cancel()
            self.ws_task = None
        if self.ws is not None:
            await self.ws.close()
            self.ws = None

    async def check_timeout(self, now):
        #check last received data time
        ts = dt_util.as_timestamp(now)
        diff = ts - self.last_receive_ts
        if diff > self.receive_timout:
            self.last_receive_ts = ts #prevent rush of reconnects
            _LOGGER.info("Sams Websocket reset - recive data timeout")
            await self.disconnect()
            await self.connect()

    def hasListener(self) -> bool:
        return len(self._listeners) > 0