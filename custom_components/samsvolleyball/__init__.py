"""The sams-volleyball integration."""

from __future__ import annotations

import asyncio
import json
import logging
import urllib.parse

from aiohttp import ClientError, ClientSession, WSMessage, WSMsgType
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_util

from .const import (
    CONF_HOST,
    CONF_REGION,
    DOMAIN,
    NO_GAME,
    PLATFORMS,
    TIMEOUT,
    URL_GET,
    VERSION,
)

UPDATE_FULL_INTERVAL = 5 * 60  # 5 min.
_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up sams-volleyball from a config entry."""
    _LOGGER.info(
        "Sams Volleyball Tracker version %s is starting!",
        VERSION,
    )

    domain_data = hass.data.setdefault(DOMAIN, {})
    name = f"Sams Tracker {entry.data[CONF_REGION].capitalize()}"
    url_ws = urllib.parse.urljoin(entry.data[CONF_HOST], entry.data[CONF_REGION])
    url_get = urllib.parse.urljoin(URL_GET, entry.data[CONF_REGION])

    if entry.data[CONF_REGION] in domain_data:
        # we already have a coordinator for that region
        coordinator = domain_data[entry.data[CONF_REGION]]
    else:
        # create new coordinator for the sams region
        session = async_get_clientsession(hass)
        coordinator = SamsDataCoordinator(hass, session, name, url_ws, url_get)
        domain_data[entry.data[CONF_REGION]] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        coordinator = hass.data[DOMAIN][entry.data[CONF_REGION]]
        if not coordinator.has_listener():
            coordinator = hass.data[DOMAIN].pop(entry.data[CONF_REGION])
            await coordinator.disconnect()
            _LOGGER.info(
                "Sams Volleyball Tracker removed coordinator for region %s ",
                entry.data[CONF_REGION],
            )
    return unload_ok


class SamsDataCoordinator(DataUpdateCoordinator):
    """Class to manage fetching sams ticker data. It is intantiated once per used region/websocket."""

    def __init__(
        self, hass: HomeAssistant, session: ClientSession, name, websocket_url, get_url
    ) -> None:
        """init websocket instance"""
        self.hass = hass
        self.session = session
        self.name = name
        self.websocket_url = websocket_url
        self.get_url = get_url
        self.ws = None
        self.ws_task = None
        self.last_get_ts = dt_util.as_timestamp(dt_util.start_of_local_day())
        self.last_ws_receive_ts = dt_util.as_timestamp(dt_util.utcnow())
        self.connected = False
        self.loop: asyncio.AbstractEventLoop = asyncio.get_event_loop()
        self.receive_timout = TIMEOUT[NO_GAME]
        self.headers = {
            "Connection": "Upgrade",
            "Pragma": "no-cache",
            "Cache-Control": "no-cache",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36",
            "Upgrade": "websocket",
            "Accept-Encoding": "gzip, deflate, br, zstd",
            "Accept-Language": "de-DE,de;q=0.9,en-US;q=0.8,en;q=0.7",
        }
        _LOGGER.debug("Init coordinator for %s", self.name)
        super().__init__(hass, _LOGGER, name=self.name)

    async def _async_update_data(self):
        now = dt_util.utcnow()
        ts = dt_util.as_timestamp(now)
        data = None
        if (ts - self.last_get_ts) > UPDATE_FULL_INTERVAL:
            data = await self.get_full_data()
            self.last_get_ts = ts

        if await self.game_active():
            if not self.ws or not self.connected:
                _LOGGER.debug("Connect to %s", self.websocket_url)
                await self.connect()
                self.last_ws_receive_ts = ts
            if ts - self.last_ws_receive_ts > self.receive_timout:
                _LOGGER.debug("Timeout on ws %s - reconnect", self.name)
                await self.disconnect()
                await self.connect()
                self.last_ws_receive_ts = ts
        return data

    async def _on_close(self):
        _LOGGER.debug(f"Connection closed - {self.name}")
        self.connected = False

    async def _on_open(self):
        _LOGGER.info(f"Connection opened - {self.name}")
        self.connected = True

    async def _on_message(self, message: WSMessage):
        if message.type == WSMsgType.TEXT:
            data = json.loads(message.data)
            _LOGGER.debug("Received data: %s ", str(message)[1:500])
            if data:
                self.async_set_updated_data(data)
                self.last_ws_receive_ts = dt_util.as_timestamp(dt_util.utcnow())
                if self.receive_timout == TIMEOUT[NO_GAME]:
                    _LOGGER.info(f"{self.name} - no game active - close socket.")
                    await self.disconnect()
        else:
            _LOGGER.info(
                "%s - received unexpected message: %s ", self.name, str(message)[1:500]
            )

    async def get_full_data(self) -> dict:
        resp = await self.session.get(self.get_url, raise_for_status=True)
        _LOGGER.info("%s received full ticker json", self.name)
        data = await resp.json()
        return data

    async def _process_messages(self):
        try:
            async for msg in self.ws:
                await self._on_message(msg)
        except RuntimeError as exc:
            _LOGGER.warning("Sams Websocket runtime error %s", exc)
            await self._on_close()
        except ConnectionResetError:
            _LOGGER.info("%s Websocket Connection Reset", self.name)
            await self._on_close()
        except Exception as exc:  # pylint: disable=broad-except
            _LOGGER.warning(
                "Error during processing new message: %s", exc.with_traceback()
            )

    async def connect(self):
        try:
            self.ws = await self.session.ws_connect(
                self.websocket_url,
                autoclose=False,
                headers=self.headers,
            )
            self.loop = asyncio.get_event_loop()
            self.ws_task = self.loop.create_task(self._process_messages())
            await self._on_open()
        except ClientError as exc:  # pylint: disable=broad-except
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

    async def game_active(self) -> bool:
        for _, active_cb in list(self._listeners.values()):
            # call function get_active_state
            if active_cb() > 0:
                return True
        return False

    def has_listener(self) -> tuple:
        return len(self._listeners) > 0, len(self._listeners)
