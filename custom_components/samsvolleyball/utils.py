"""Utilities to evaluate and analyze json data from sams ticker."""

from __future__ import annotations

from datetime import datetime
import logging
import sys

import arrow

from homeassistant.util import dt as dt_util

from .const import STATES_IN, STATES_NOT_FOUND, STATES_POST, STATES_PRE

_LOGGER = logging.getLogger(__name__)

PAYLOAD = "payload"
MATCHSERIES = "matchSeries"
CLASS = "class"
CLASS_LEAGUE = "League"
DATE = "date"
FINISHED = "finished"
GENDER = "gender"
ID = "id"
NAME = "name"
MATCHDAYS = "matchDays"
MATCHSTATES = "matchStates"
MATCHES = "matches"
MATCH_UUID = "matchUuid"
TEAM = "team"
TEAMS = "teams"
TYPE = "type"
TYPE_MATCH = "MATCH_UPDATE"
STARTED = "started"

SECONDS_PER_DAY = 24 * 60 * 60


class SamsUtils:
    @staticmethod
    def is_overview(data: dict) -> bool:
        return MATCHDAYS in data

    @staticmethod
    def is_match(data: dict) -> bool:
        return data[TYPE] == TYPE_MATCH

    @staticmethod
    def is_my_match(data: dict, match: dict) -> bool:
        if SamsUtils.is_match(data):
            return data[PAYLOAD][MATCH_UUID] == match[ID]
        return False

    @staticmethod
    def get_leaguelist(data: dict, gender=None) -> list[dict[str, str]]:
        leagues: list[dict[str, str]] = []
        if SamsUtils.is_overview(data):
            if gender:
                leagues = [
                    {NAME: series[NAME], ID: series_id}
                    for series_id, series in data[MATCHSERIES].items()
                    if gender
                    and series[GENDER] == gender
                    and series[CLASS] == CLASS_LEAGUE
                ]
            else:
                leagues = [
                    {NAME: series[NAME], ID: series_id}
                    for series_id, series in data[MATCHSERIES].items()
                    if series[CLASS] == CLASS_LEAGUE
                ]
        return leagues

    @staticmethod
    def get_league_by_id(data: dict, league_id: str) -> dict:
        if SamsUtils.is_overview(data):
            return data[MATCHSERIES][league_id]
        return {}

    @staticmethod
    def get_teamlist(data: dict, league_id: str) -> dict[str, str]:
        teams: dict[str, str] = {}
        series = SamsUtils.get_league_by_id(data, league_id)
        for team in series[TEAMS]:
            teams[team[NAME]] = team[ID]
        return teams

    @staticmethod
    def get_league_data(data: dict, league_id: str, field):
        series = SamsUtils.get_league_by_id(data, league_id)
        return series[field]

    @staticmethod
    def get_uuids_by_name(data: dict, name: str, league: str):
        uuid = []
        if SamsUtils.is_overview(data):
            for series_id in data[MATCHSERIES]:
                series = data[MATCHSERIES][series_id]
                if series[NAME] == league:
                    for team in series[TEAMS]:
                        if team[NAME] == name:
                            uuid.append(team[ID])
        return uuid

    @staticmethod
    def get_team_by_id(data: dict, team_id: str):
        if SamsUtils.is_overview(data):
            for series_id in data[MATCHSERIES]:
                series = data[MATCHSERIES][series_id]
                for team in series[TEAMS]:
                    if team[ID] == team_id:
                        return team, series
        return None, None

    @staticmethod
    def get_match_data(data):
        return data[PAYLOAD]

    @staticmethod
    def get_matches(data: dict, team_id):
        matches = []
        if SamsUtils.is_overview(data):
            matchdays = data[MATCHDAYS]
            for matchday in matchdays:
                for match in matchday[MATCHES]:
                    if team_id in (match[TEAM + "1"], match[TEAM + "2"]):
                        matches.append(match)
        return matches

    @staticmethod
    def get_match_state(data: dict, match_id: str):
        if SamsUtils.is_overview(data):
            if match_id in data[MATCHSTATES]:
                return data[MATCHSTATES][match_id]
        return None

    @staticmethod
    def state_from_match_state(match_state: dict):
        state = STATES_NOT_FOUND
        if match_state:
            if match_state[FINISHED]:
                state = STATES_POST
            elif match_state[STARTED]:
                state = STATES_IN
            else:
                state = STATES_PRE
        else:
            state = STATES_PRE
        return state

    @staticmethod
    def state_from_match(data: dict, match: dict):
        match_state = SamsUtils.get_match_state(data, match[ID])
        return SamsUtils.state_from_match_state(match_state)

    @staticmethod
    def date_from_match(match) -> datetime:
        return dt_util.as_local(dt_util.utc_from_timestamp(float(match[DATE]) / 1000))

    @staticmethod
    def select_match(data: dict, matches: list):
        # assumes matches are sorted by date
        for match in matches:
            state = SamsUtils.state_from_match(data, match)
            # prefer active matches
            if state == STATES_IN:
                return match

        for match in matches:
            state = SamsUtils.state_from_match(data, match)
            if state == STATES_POST:
                duration = (
                    dt_util.now() - SamsUtils.date_from_match(match)
                ).total_seconds()
                if duration < SECONDS_PER_DAY:
                    return match

        min_timediff = sys.float_info.max
        next_match = None

        for match in matches:
            state = SamsUtils.state_from_match(data, match)
            if state == STATES_PRE:
                # select the next
                time_to_start = (
                    SamsUtils.date_from_match(match) - dt_util.now()
                ).total_seconds()
                if time_to_start < min_timediff:
                    min_timediff = time_to_start
                    next_match = match

        if next_match:
            return next_match

        # fallback return latest
        return matches.pop(-1)

    @staticmethod
    def _get_set_string(match_state, team_num, opponent_num, offset):
        set_string = ""
        sets = match_state["matchSets"]
        for i in range(len(sets) - offset):
            match_set = sets[i]
            if len(set_string) > 0:
                set_string += " | "
            set_string += f"{match_set['setScore'][team_num]} ({match_set['setNumber']}) {match_set['setScore'][opponent_num]}"
        return set_string

    @staticmethod
    def fill_match_attrs(
        attrs: dict, match_state: dict, state: str, team_num: str, opponent_num: str
    ):
        attrs["team_winner"] = None
        attrs["opponent_winner"] = None

        attrs["team_sets_won"] = match_state["setPoints"][team_num]
        attrs["opponent_sets_won"] = match_state["setPoints"][opponent_num]

        sets = match_state["matchSets"]
        attrs["match_sets_points"] = []

        for match_set in sets:
            attrs["match_sets_points"].append(
                [
                    match_set["setScore"][team_num],
                    match_set["setNumber"],
                    match_set["setScore"][opponent_num],
                ]
            )

        if state == STATES_POST:
            attrs["team_score"] = match_state["setPoints"][team_num]
            attrs["opponent_score"] = match_state["setPoints"][opponent_num]

            attrs["team_winner"] = int(attrs["team_score"]) > attrs["opponent_score"]
            attrs["opponent_winner"] = (
                int(attrs["opponent_score"]) > attrs["team_score"]
            )
            attrs["clock"] = SamsUtils._get_set_string(
                match_state, team_num, opponent_num, 0
            )

        if state == STATES_IN:
            attrs["team_score"] = match_state["matchSets"][-1]["setScore"][team_num]
            attrs["opponent_score"] = match_state["matchSets"][-1]["setScore"][
                opponent_num
            ]

            attrs["clock"] = match_state["matchSets"][-1]["setNumber"]
            attrs["last_play"] = SamsUtils._get_set_string(
                match_state, team_num, opponent_num, 1
            )

        return attrs

    @staticmethod
    def _get_ranking(league: dict, team_id: str):
        for rank in league["rankings"]["fullRankings"]:
            if rank[TEAM][ID] == team_id:
                return rank
        return None

    @staticmethod
    def fill_team_attributes(attrs: dict, data: dict, team: dict, state: str):
        try:
            _, league = SamsUtils.get_team_by_id(data, team[ID])
            rank_team = SamsUtils._get_ranking(league, team[ID])
            if rank_team:
                attrs["team_record"] = (
                    f"{rank_team['scoreDetails']['matchesPlayed']} - {rank_team['scoreDetails']['winScore']}"
                )
                attrs["team_rank"] = rank_team["rankingPosition"]
            attrs["league"] = league[NAME]
            attrs["last_update"] = dt_util.as_local(dt_util.now())

            attrs["team_name"] = team[NAME]
            if state == STATES_NOT_FOUND:
                attrs["team_abbr"] = team[NAME]
            else:
                attrs["team_abbr"] = (
                    team["shortName"]
                    if (len(team["shortName"]) > 0)
                    else team["letter"]
                )
            attrs["team_id"] = team[ID]

            attrs["team_logo"] = team["logoImage200"]
            attrs["team_colors"] = ["#ffffff", "#000000"]  # ToDo: extract from logo?

        except KeyError as e:  # pylint: disable=broad-except
            _LOGGER.warning("Fill_attributes - cannot extract attribute %s", e)
        return attrs

    @staticmethod
    def fill_match_attributes(attrs: dict, data: dict, match: dict, team: dict, lang):
        try:
            attrs["match_id"] = match[ID]
            state = SamsUtils.state_from_match(data, match)
            attrs = SamsUtils.fill_team_attributes(attrs, data, team, state)

            if match["team1"] == team[ID]:
                attrs["team_homeaway"] = "home"
                attrs["opponent_homeaway"] = "away"
                opponent, league = SamsUtils.get_team_by_id(data, match["team2"])
                team_num = "team1"
                opponent_num = "team2"
            else:
                attrs["team_homeaway"] = "away"
                attrs["opponent_homeaway"] = "home"
                opponent, league = SamsUtils.get_team_by_id(data, match["team1"])
                team_num = "team2"
                opponent_num = "team1"

            attrs["team_num"] = team_num
            attrs["opponent_num"] = opponent_num

            if league and opponent:
                rank_opponent = SamsUtils._get_ranking(league, opponent[ID])
                attrs["opponent_record"] = (
                    f"{rank_opponent['scoreDetails']['matchesPlayed']} - {rank_opponent['scoreDetails']['winScore']}"
                )
                attrs["opponent_rank"] = rank_opponent["rankingPosition"]

            attrs["event_name"] = None
            date = SamsUtils.date_from_match(match)
            attrs[DATE] = date
            attrs["kickoff_in"] = arrow.get(date).humanize(locale=lang)
            attrs["venue"] = None
            attrs["location"] = None

            attrs["opponent_name"] = opponent["name"]
            attrs["opponent_abbr"] = (
                opponent["shortName"]
                if (len(team["shortName"]) > 0)
                else team["letter"]
            )
            attrs["opponent_id"] = opponent[ID]
            attrs["opponent_logo"] = opponent["logoImage200"]
            attrs["opponent_colors"] = ["#ffffff", "#000000"]

            attrs["quarter"] = None

            match_state = SamsUtils.get_match_state(data, match[ID])
            if match_state:
                attrs = SamsUtils.fill_match_attrs(
                    attrs, match_state, state, team_num, opponent_num
                )
            else:
                attrs["clock"] = ""

            if state == STATES_POST:
                if attrs["team_score"] > attrs["opponent_score"]:
                    attrs["team_winner"] = True
                    attrs["opponent_winner"] = False
                else:
                    attrs["team_winner"] = False
                    attrs["opponent_winner"] = True

        except KeyError as e:  # pylint: disable=broad-except
            _LOGGER.warning("Fill_attributes - cannot extract attribute %s", e)
        return attrs

    @staticmethod
    def update_match_attributes(attrs: dict, data: dict):
        match_state = data
        state = SamsUtils.state_from_match_state(match_state)

        team_num = attrs["team_num"]
        opponent_num = attrs["opponent_num"]

        attrs = SamsUtils.fill_match_attrs(
            attrs, match_state, state, team_num, opponent_num
        )

        attrs["last_update"] = dt_util.as_local(dt_util.now())

        return attrs
