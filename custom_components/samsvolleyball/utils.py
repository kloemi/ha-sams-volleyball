import json
import logging
import arrow

from homeassistant.const import ATTR_ATTRIBUTION
from homeassistant.util import dt as dt_util

_LOGGER = logging.getLogger(__name__)

from .const import (
    ATTRIBUTION,
    STATES_IN,
    STATES_NOT_FOUND,
    STATES_PRE,
    STATES_POST,
    VOLLEYBALL,
)

PAYLOAD = "payload"
MATCHSERIES  = "matchSeries"
CLASS = "class"
CLASS_LEAGUE = "League"
ID = "id"
NAME = "name"
MATCHDAYS = "matchDays"
MATCHSTATES = "matchStates"
MATCHES = "matches"
MATCH_UUID = "matchUuid"
TEAM = "team"
TEAMS = "teams"
TYPE = "type"
TYPE_TICKER = "FETCH_ASSOCIATION_TICKER_RESPONSE"
TYPE_MATCH = "MATCH_UPDATE"

def is_ticker(data) -> bool:
    try:
        return data[TYPE] == TYPE_TICKER
    except KeyError as e:
        _LOGGER.debug(f"is_ticker - cannot extract type")

def is_my_match(data, match) -> bool:
    try:
        if data[TYPE] == TYPE_MATCH:
            if data[PAYLOAD][MATCH_UUID] == match[ID]:
                return True
    except KeyError as e:
        _LOGGER.debug(f"is_my_match - cannot extract type")
    return False

def get_leaguelist(data: json) -> dict[str,str]:
    leagues: dict[str, str] = {}
    try:
        if is_ticker(data):
            allseries = data[PAYLOAD][MATCHSERIES]
            for series_id in allseries:
                series = allseries.get(series_id)
                if series[CLASS] == CLASS_LEAGUE:
                    leagues[series[NAME]] = series_id
    except KeyError as e:
        _LOGGER.debug(f"get_leaguelist - cannot extract leagues")
        leagues = {}

    return leagues

def get_league(data: json, league_id) -> json:
    try:
        if is_ticker(data):
            allseries = data[PAYLOAD][MATCHSERIES]
            series = allseries.get(league_id)
            return series
    except KeyError as e:
        _LOGGER.debug("get_league - cannot extract league %s", league_id)

def get_teamlist(data: json, league_id) -> dict[str,str]:
    teams: dict[str, str] = {}
    try:
        series = get_league(data, league_id)
        for team in series[TEAMS]:
            teams[team[NAME]] = team[ID]
    except KeyError as e:
        _LOGGER.debug(f"get_teamlist - cannot extract teams")
        teams = {}
    return teams

def get_league_data(data: json, league_id, field):
    try:
        series = get_league(data, league_id)
        return series[field]
    except KeyError as e:
        _LOGGER.debug(f"get_league_data - cannot extract field, %s", field)

def get_team(data: json, team_id):
    try:
        if is_ticker(data):
            allseries = data[PAYLOAD][MATCHSERIES]
            for series_id in allseries:
                series = allseries.get(series_id)
                for team in series[TEAMS]:
                    if team[ID] == team_id:
                        return team, series
    except KeyError as e:
        _LOGGER.debug(f"get_team - cannot extract team, %s", team_id)

def get_matches(data: json, team_id):
    matches = []
    try:
        if is_ticker(data):
            matchdays = data[PAYLOAD][MATCHDAYS]
            for matchday in matchdays:
                for match in matchday[MATCHES]:
                    if team_id in (match['team1'], match['team2']):
                        matches.append(match)
    except KeyError as e:
        _LOGGER.debug(f"get_team - cannot extract team, %s", team_id)
    return matches

def get_match_state(data: json , match_id: str):
    state = STATES_NOT_FOUND
    try:
        if is_ticker(data):
            if match_id in data[PAYLOAD][MATCHSTATES]:
                return data[PAYLOAD][MATCHSTATES][match_id]
    except KeyError as e:
        _LOGGER.debug(f"get_team - cannot extract team, %s", team_id)
    return None

def select_match(matches: list):
    #ToDo: select by date
    return matches.pop(-1)

def state_from_match(data: json , match: json):
    state = STATES_NOT_FOUND
    try:
        match_id = match[ID]
        if match_id in data[PAYLOAD][MATCHSTATES]:
            match_state = data[PAYLOAD][MATCHSTATES][match_id]
            if match_state["finished"]:
                state = STATES_POST
            else:
                if match_state["started"]:
                    state = STATES_IN
                else:
                    state = STATES_PRE
        else:
            state = STATES_PRE
    except KeyError as e:
        _LOGGER.debug(f"state_from_match - cannot extract state")
    return state

def fill_attributes(attrs, data, match, team, lang):
    attrs[ATTR_ATTRIBUTION] = ATTRIBUTION
    attrs["sport"] = VOLLEYBALL
    try:
        match_id = match[ID]
        match_state = get_match_state(data, match_id)
        state = state_from_match(data, match)

        if match["team1"] == team[ID]:
            attrs["team_homeaway"] = "home"
            attrs["opponent_homeaway"] = "away"
            opponent, league = get_team(data, match["team2"])
            team_num = "team1"
            opponent_num = "team2"
        else:
            attrs["team_homeaway"] = "away"
            attrs["opponent_homeaway"] = "home"
            opponent, league = get_team(data, match["team1"])
            team_num = "team2"
            opponent_num = "team1"

        if match_state:
                attrs["team_score"] = match_state["setPoints"][team_num]
                attrs["team_winner"] = None
                attrs["opponent_score"] = match_state["setPoints"][opponent_num]
                attrs["opponent_winner"] = None

        attrs["league"] = league[NAME]
        attrs["league_logo"] = None #ToDo: needed from region out of config

        attrs["event_name"] = None
        date = dt_util.as_local(dt_util.utc_from_timestamp(float(match["date"]) / 1000))
        attrs["date"] = date
        attrs["kickoff_in"] = arrow.get(date).humanize(locale=lang)
        attrs["venue"] = None
        attrs["location"] = None

        attrs["team_name"] = team["name"]
        attrs["team_abbr"] = team["shortName"] if (len(team["shortName"])>0) else team["letter"]
        attrs["team_id"] = team[ID]
        attrs["team_record"] = None
        attrs["team_rank"] = None
        attrs["team_logo"] = team["logoImage200"]
        attrs["team_colors"] = "#ffffff,#000000" #ToDo: extract from logo?


        attrs["opponent_name"] = opponent["name"]
        attrs["opponent_abbr"] = opponent["shortName"] if (len(team["shortName"]) > 0) else team["letter"]
        attrs["opponent_id"] = opponent[ID]
        attrs["opponent_record"] = None
        attrs["opponent_rank"] = None
        attrs["opponent_logo"] = opponent["logoImage200"]
        attrs["opponent_colors"] = "#ffffff,#000000"


        attrs["quarter"] = None
        if state == STATES_POST:
            attrs["clock"] = dt_util.as_local(dt_util.utc_from_timestamp(float(match["date"]) / 1000)).time().strftime("%H:%M")
        else: attrs["clock"] = ""

        attrs["team_sets_won"] = None
        attrs["opponent_sets_won"] = None

    except KeyError as e:
        _LOGGER.debug(f"fill_attributes - cannot extract attribute")
    return attrs

def update_match_attributes(attrs, data, match, team_uuid):
    return attrs
