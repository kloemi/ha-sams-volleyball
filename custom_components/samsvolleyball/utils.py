from __future__ import annotations

import logging
import sys
from datetime import datetime

import arrow
from homeassistant.util import dt as dt_util

from .const import STATES_IN, STATES_NOT_FOUND, STATES_POST, STATES_PRE

_LOGGER = logging.getLogger(__name__)

PAYLOAD = "payload"
MATCHSERIES = "matchSeries"
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

SECONDS_PER_DAY = 24 * 60 * 60


def is_ticker(data) -> bool:
    try:
        return data[TYPE] == TYPE_TICKER
    except KeyError as e:
        _LOGGER.debug("is_ticker - cannot extract type %s", e)
    return False


def is_my_match(data, match) -> bool:
    try:
        if data[TYPE] == TYPE_MATCH:
            if data[PAYLOAD][MATCH_UUID] == match[ID]:
                return True
    except KeyError as e:
        _LOGGER.debug("is_my_match - cannot extract type %s", e)
    return False


def get_leaguelist(data) -> dict[str, str]:
    leagues: dict[str, str] = {}
    try:
        if is_ticker(data):
            allseries = data[PAYLOAD][MATCHSERIES]
            for series_id in allseries:
                series = allseries.get(series_id)
                if series[CLASS] == CLASS_LEAGUE:
                    leagues[series[NAME]] = series_id
    except KeyError as e:
        _LOGGER.debug("get_leaguelist - cannot extract leagues %s", e)
        leagues = {}

    return leagues


def get_league(data, league_id):
    try:
        if is_ticker(data):
            allseries = data[PAYLOAD][MATCHSERIES]
            series = allseries.get(league_id)
            return series
    except KeyError:
        _LOGGER.debug("get_league - cannot extract league %s", league_id)


def get_teamlist(data, league_id) -> dict[str, str]:
    teams: dict[str, str] = {}
    try:
        series = get_league(data, league_id)
        for team in series[TEAMS]:
            teams[team[NAME]] = team[ID]
    except KeyError as e:
        _LOGGER.debug("get_teamlist - cannot extract teams", e)
        teams = {}
    return teams


def get_league_data(data, league_id, field):
    try:
        series = get_league(data, league_id)
        return series[field]
    except KeyError:
        _LOGGER.debug("get_league_data - cannot extract field, %s", field)


def get_team(data, team_id):
    try:
        if is_ticker(data):
            allseries = data[PAYLOAD][MATCHSERIES]
            for series_id in allseries:
                series = allseries.get(series_id)
                for team in series[TEAMS]:
                    if team[ID] == team_id:
                        return team, series
    except KeyError:
        _LOGGER.debug("get_team - cannot extract team, %s", team_id)


def get_matches(data, team_id):
    matches = []
    try:
        if is_ticker(data):
            matchdays = data[PAYLOAD][MATCHDAYS]
            for matchday in matchdays:
                for match in matchday[MATCHES]:
                    if team_id in (match["team1"], match["team2"]):
                        matches.append(match)
    except KeyError:
        _LOGGER.debug("get_team - cannot extract team, %s", team_id)
    return matches


def get_match_state(data, match_id: str):
    try:
        if is_ticker(data):
            if match_id in data[PAYLOAD][MATCHSTATES]:
                return data[PAYLOAD][MATCHSTATES][match_id]
    except KeyError:
        _LOGGER.debug("get_team - cannot extract team, %s", match_id)
    return


def state_from_match_state(match_state):
    state = STATES_NOT_FOUND
    try:
        if match_state:
            if match_state["finished"]:
                state = STATES_POST
            else:
                if match_state["started"]:
                    state = STATES_IN
                else:
                    state = STATES_PRE
        else:
            state = STATES_PRE
    except KeyError:
        _LOGGER.debug("state_from_match - cannot extract state")
    return state


def state_from_match(data, match):
    state = STATES_NOT_FOUND
    try:
        match_state = get_match_state(data, match[ID])
        return state_from_match_state(match_state)
    except KeyError:
        _LOGGER.debug("state_from_match - cannot extract state")
    return state


def date_from_match(match) -> datetime:
    return dt_util.as_local(dt_util.utc_from_timestamp(float(match["date"]) / 1000))


def select_match(data, matches: list):
    # assumes matches are sorted by date
    for match in matches:
        state = state_from_match(data, match)
        # prefer active matches
        if STATES_IN == state:
            return match

    for match in matches:
        state = state_from_match(data, match)
        if STATES_POST == state:
            duration = (dt_util.now() - date_from_match(match)).total_seconds()
            if duration < SECONDS_PER_DAY:
                return match

    min_timediff = sys.float_info.max
    next_match = None

    for match in matches:
        state = state_from_match(data, match)
        if STATES_PRE == state:
            # select the next
            time_to_start = (date_from_match(match) - dt_util.now()).total_seconds()
            if time_to_start < min_timediff:
                min_timediff = time_to_start
                next_match = match

    if next_match:
        return next_match

    # fallback return latest
    return matches.pop(-1)


def get_set_string(match_state, team_num, opponent_num, offset):
    set_string = ""
    sets = match_state["matchSets"]
    for i in range(len(sets) - offset):
        match_set = sets[i]
        if len(set_string) > 0:
            set_string += " | "
        set_string += f"{match_set['setScore'][team_num]} ({match_set['setNumber']}) {match_set['setScore'][opponent_num]}"
    return set_string


def fill_match_attrs(attrs, match_state, state, team_num, opponent_num):
    attrs["team_winner"] = None
    attrs["opponent_winner"] = None

    attrs["team_sets_won"] = match_state["setPoints"][team_num]
    attrs["opponent_sets_won"] = match_state["setPoints"][opponent_num]

    if STATES_POST == state:
        attrs["team_score"] = match_state["setPoints"][team_num]
        attrs["opponent_score"] = match_state["setPoints"][opponent_num]

        attrs["team_winner"] = int(attrs["team_score"]) > attrs["opponent_score"]
        attrs["opponent_winner"] = int(attrs["opponent_score"]) > attrs["team_score"]
        attrs["clock"] = get_set_string(match_state, team_num, opponent_num, 0)

    if STATES_IN == state:
        attrs["team_score"] = match_state["matchSets"][-1]["setScore"][team_num]
        attrs["opponent_score"] = match_state["matchSets"][-1]["setScore"][opponent_num]

        attrs["clock"] = match_state["matchSets"][-1]["setNumber"]
        attrs["last_play"] = get_set_string(match_state, team_num, opponent_num, 1)

    return attrs


def fill_attributes(attrs, data, match, team, lang):
    try:
        match_id = match[ID]
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

        attrs["league"] = league[NAME]

        attrs["event_name"] = None
        date = date_from_match(match)
        attrs["date"] = date
        attrs["kickoff_in"] = arrow.get(date).humanize(locale=lang)
        attrs["venue"] = None
        attrs["location"] = None

        attrs["team_name"] = team["name"]
        attrs["team_abbr"] = (
            team["shortName"] if (len(team["shortName"]) > 0) else team["letter"]
        )
        attrs["team_id"] = team[ID]
        attrs["team_record"] = None
        attrs["team_rank"] = None
        attrs["team_logo"] = team["logoImage200"]
        attrs["team_colors"] = "#ffffff,#000000"  # ToDo: extract from logo?

        attrs["opponent_name"] = opponent["name"]
        attrs["opponent_abbr"] = (
            opponent["shortName"] if (len(team["shortName"]) > 0) else team["letter"]
        )
        attrs["opponent_id"] = opponent[ID]
        attrs["opponent_record"] = None
        attrs["opponent_rank"] = None
        attrs["opponent_logo"] = opponent["logoImage200"]
        attrs["opponent_colors"] = "#ffffff,#000000"

        attrs["quarter"] = None

        state = state_from_match(data, match)

        match_state = get_match_state(data, match_id)
        if match_state:
            attrs = fill_match_attrs(attrs, match_state, state, team_num, opponent_num)
        else:
            attrs["clock"] = ""

        if state == STATES_POST:
            if attrs["team_score"] > attrs["opponent_score"]:
                attrs["team_winner"] = True
                attrs["opponent_winner"] = False
            else:
                attrs["team_winner"] = False
                attrs["opponent_winner"] = True

    except KeyError as e:
        _LOGGER.debug("fill_attributes - cannot extract attribute %s", e)
    return attrs


def update_match_attributes(attrs, data, match, team_uuid):
    match_state = data[PAYLOAD]
    state = state_from_match_state(match_state)

    if match["team1"] == team_uuid:
        team_num = "team1"
        opponent_num = "team2"
    else:
        team_num = "team2"
        opponent_num = "team1"

    attrs = fill_match_attrs(attrs, match_state, state, team_num, opponent_num)

    return attrs
