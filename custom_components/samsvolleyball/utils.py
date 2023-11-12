import json
import logging

from .const import (
    TICKER_TYPE,
)

_LOGGER = logging.getLogger(__name__)

def get_leaguelist(data: json) -> dict[str,str]:
    leagues: dict[str, str] = {}
    try:
        if data["type"] == TICKER_TYPE:
            allseries = data["payload"]["matchSeries"]
            for series_id in allseries:
                series = allseries.get(series_id)
                if series["class"] == "League":
                    leagues[series["name"]] = series_id
    except KeyError as e:
        _LOGGER.debug(f"get_leaguelist - cannot extract leagues")
        leagues = {}

    return leagues

def get_teamlist(data: json, league_id) -> dict[str,str]:
    teams: dict[str, str] = {}
    try:
        if data["type"] == TICKER_TYPE:
            allseries = data["payload"]["matchSeries"]
            series = allseries.get(league_id)
            for team in series["teams"]:
                teams[team["name"]] = team["id"]
    except KeyError as e:
        _LOGGER.debug(f"get_teamlist - cannot extract teams")
        teams = {}
    return teams

def get_league_data(data, league_id, field):
    try:
        if data["type"] == TICKER_TYPE:
            allseries = data["payload"]["matchSeries"]
            series = allseries.get(league_id)
            return series[field]
    except KeyError as e:
        _LOGGER.debug(f"get_league_data - cannot extract field, %s", field)