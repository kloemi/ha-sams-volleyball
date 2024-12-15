"""The sams-volleyball integration."""

from __future__ import annotations

import asyncio
from datetime import timedelta
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
    CONF_TEAM_NAME,
    DOMAIN,
    HEADERS,
    IN_GAME,
    NEAR_GAME,
    NO_GAME,
    PLATFORMS,
    TIMEOUT,
    TIMEOUT_PERIOD_CHECK,
    URL_GET,
    VERSION,
)

UPDATE_FULL_INTERVAL = timedelta(minutes=5)
UPDATE_INTERVAL_NO_GAME = timedelta(minutes=60)
_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up sams-volleyball from a config entry."""
    _LOGGER.info(
        "Sams Volleyball Tracker version %s is starting (%s)!",
        VERSION,
        entry.data[CONF_TEAM_NAME],
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
        in_use, _ = coordinator.has_listener()
        if not in_use:
            coordinator = hass.data[DOMAIN].pop(entry.data[CONF_REGION])
            await coordinator.disconnect()
            _LOGGER.info(
                "Sams Volleyball Tracker removed coordinator for region %s ",
                entry.data[CONF_REGION],
            )
    return unload_ok


class SamsDataCoordinator(DataUpdateCoordinator):
    """Class to manage fetching sams ticker data. It is instantiated once per used region/websocket.

    It receives the data either periodic per GET request or if a game of the attached sensors is active
    or nearby it connects per websocket to sams.
    """

    def __init__(
        self,
        hass: HomeAssistant,
        session: ClientSession,
        name: str,
        websocket_url: str,
        get_url: str,
    ) -> None:
        """Init the data update instance."""
        ts_now = dt_util.as_timestamp(dt_util.utcnow())
        self.session = session
        self.websocket_url = websocket_url
        self.get_url = get_url
        self.ws = None
        self.ws_task = None
        self._lock = asyncio.Lock()
        self.last_get_ts = dt_util.as_timestamp(dt_util.start_of_local_day())
        self.last_ws_receive_ts = ts_now
        self.last_check_ts = ts_now
        self.connected = False
        self.loop: asyncio.AbstractEventLoop = asyncio.get_event_loop()
        super().__init__(
            hass,
            _LOGGER,
            name=name,
            update_interval=timedelta(minutes=5),
        )
        _LOGGER.debug("Init coordinator for region %s", self.name)

    async def get_full_data(self) -> dict:
        """Get the full data json from SAMS by GET request."""
        resp = await self.session.get(self.get_url, raise_for_status=True)
        _LOGGER.debug("%s received full ticker json", self.name)
        return await resp.json()

    async def _async_update_data(self):
        """Fetch data from API endpoint.

        This is the place to pre-process the data to lookup tables
        so entities can quickly look up their data.
        """
        data = await self.get_full_data()
        self.last_get_ts = dt_util.as_timestamp(dt_util.utcnow())
        return data

    async def _on_close(self):
        _LOGGER.debug("Connection closed - %s", self.name)
        self.connected = False

    async def _on_open(self):
        _LOGGER.info("Connection opened - %s", self.name)
        self.connected = True

    async def _on_message(self, message: WSMessage):
        if message.type == WSMsgType.TEXT:
            data = json.loads(message.data)
            _LOGGER.debug("Received data: %s ", str(message)[1:500])
            if data:
                self.async_set_updated_data(data)
                self.last_ws_receive_ts = dt_util.as_timestamp(dt_util.utcnow())
        else:
            _LOGGER.info(
                "%s - received unexpected message: %s ", self.name, str(message)[1:500]
            )

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

    async def _connect_ws(self):
        async with self._lock:
            if not self.ws or not self.connected:
                _LOGGER.info("Connect to %s", self.websocket_url)
                try:
                    self.ws = await self.session.ws_connect(
                        self.websocket_url,
                        autoclose=False,
                        headers=HEADERS,
                    )
                    self.loop = asyncio.get_event_loop()
                    self.ws_task = self.loop.create_task(self._process_messages())
                    await self._on_open()
                except ClientError as exc:  # pylint: disable=broad-except
                    _LOGGER.warning("Error during processing new message: %s", exc)
                    self.disconnect()

    async def disconnect(self):
        """Close web socket connection."""
        if self.ws_task is not None:
            self.ws_task.cancel()
            self.ws_task = None
        if self.ws is not None:
            await self.ws.close()
            self.ws = None

    async def periodic_work(self, now):
        ts = dt_util.as_timestamp(now)
        if ts - self.last_check_ts > TIMEOUT_PERIOD_CHECK:
            if self._game_nearby():
                if self.update_interval != UPDATE_FULL_INTERVAL:
                    _LOGGER.debug(
                        "%s - game nearby - increase update interval to 5 min",
                        self.name,
                    )
                    self.update_interval = UPDATE_FULL_INTERVAL
                if not self.ws or not self.connected:
                    await self._connect_ws()
                    self.last_ws_receive_ts = ts
                timeout = (
                    TIMEOUT[IN_GAME] if self._game_active() else TIMEOUT[NEAR_GAME]
                )
                if ts - self.last_ws_receive_ts > timeout:
                    _LOGGER.debug("Timeout on ws %s - reconnect", self.name)
                    await self.disconnect()
                    await self._connect_ws()
                    self.last_ws_receive_ts = ts
            else:
                if self.ws and self.connected:
                    _LOGGER.info("%s - no game active - close socket", self.name)
                    await self.disconnect()
                if self.update_interval != UPDATE_INTERVAL_NO_GAME:
                    _LOGGER.debug(
                        "%s - no game active - reduce update interval to 60 min",
                        self.name,
                    )
                    self.update_interval = UPDATE_INTERVAL_NO_GAME
            self.last_check_ts = ts

    def _game_active(self) -> bool:
        return any(
            active_cb() == IN_GAME for _, active_cb in list(self._listeners.values())
        )

    def _game_nearby(self) -> bool:
        return any(
            active_cb() > NO_GAME for _, active_cb in list(self._listeners.values())
        )

    def has_listener(self) -> tuple:
        return len(self._listeners) > 0, len(self._listeners)
