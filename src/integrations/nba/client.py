"""NBA API client."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from nba_api.stats.endpoints import (
    boxscoretraditionalv2,
    commonteamroster,
    leaguestandingsv3,
    playergamelog,
    scoreboardv2,
    shotchartdetail,
    teamgamelog,
)
from nba_api.stats.static import players as static_players
from nba_api.stats.static import teams as static_teams

from .exceptions import NbaApiResponseError, NbaGameNotFoundError, NbaPlayerNotFoundError
from .models import (
    NbaConference,
    NbaDivision,
    NbaGame,
    NbaPlayer,
    NbaPlayerGameStats,
    NbaShotDetail,
    NbaStandingsRecord,
    NbaTeam,
)
from .utils import parse_bool_or_none, parse_float_or_none, parse_int_or_none, parse_str_or_none


class NbaStatsApi:
    """NBA Stats API client.

    This client wraps the nba_api package to provide typed, structured
    access to NBA game, team, and player statistics data.
    """

    def list_teams(self) -> list[NbaTeam]:
        """List all NBA teams.

        Returns:
            List of NbaTeam objects containing team information
        """
        teams_data = static_teams.get_teams()
        out: list[NbaTeam] = []

        for team in teams_data:
            if not isinstance(team, dict):
                continue

            team_id = parse_int_or_none(team.get("id"))
            if team_id is None:
                continue

            out.append(
                NbaTeam(
                    team_id=team_id,
                    team_name=parse_str_or_none(team.get("full_name")),
                    team_abbr=parse_str_or_none(team.get("abbreviation")),
                    team_city=parse_str_or_none(team.get("city")),
                    conference_id=None,  # Not in static data
                    division_id=None,  # Not in static data
                    year_founded=parse_int_or_none(team.get("year_founded")),
                    raw=team,
                )
            )
        return out

    def list_divisions(self) -> list[NbaDivision]:
        """List all NBA divisions.

        Returns:
            List of NbaDivision objects
        """
        # NBA divisions are relatively static
        divisions = [
            {"id": 1, "name": "Atlantic", "abbr": "ATL", "conference_id": 0},
            {"id": 2, "name": "Central", "abbr": "CEN", "conference_id": 0},
            {"id": 3, "name": "Southeast", "abbr": "SE", "conference_id": 0},
            {"id": 4, "name": "Northwest", "abbr": "NW", "conference_id": 1},
            {"id": 5, "name": "Pacific", "abbr": "PAC", "conference_id": 1},
            {"id": 6, "name": "Southwest", "abbr": "SW", "conference_id": 1},
        ]

        out: list[NbaDivision] = []
        for div in divisions:
            out.append(
                NbaDivision(
                    division_id=div["id"],
                    division_name=div["name"],
                    division_abbr=div["abbr"],
                    conference_id=div["conference_id"],
                    raw=div,
                )
            )
        return out

    def list_conferences(self) -> list[NbaConference]:
        """List all NBA conferences.

        Returns:
            List of NbaConference objects
        """
        conferences = [
            {"id": 0, "name": "Eastern Conference", "abbr": "East"},
            {"id": 1, "name": "Western Conference", "abbr": "West"},
        ]

        out: list[NbaConference] = []
        for conf in conferences:
            out.append(
                NbaConference(
                    conference_id=conf["id"],
                    conference_name=conf["name"],
                    conference_abbr=conf["abbr"],
                    raw=conf,
                )
            )
        return out

    def list_games(
        self,
        *,
        season: int,
        season_type: str = "Regular Season",
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[NbaGame]:
        """List games for a given season and date range.

        Args:
            season: The NBA season year (e.g., 2024 for 2024-25 season)
            season_type: Season type (Regular Season, Playoffs, etc.)
            start_date: Optional start date filter
            end_date: Optional end date filter

        Returns:
            List of NbaGame objects
        """
        # If no date range provided, use full season
        if start_date is None:
            start_date = date(season, 10, 1)  # NBA season typically starts in October
        if end_date is None:
            if season_type == "Playoffs":
                end_date = date(season + 1, 6, 30)  # Playoffs can go into June
            else:
                end_date = date(season + 1, 4, 30)  # Regular season typically ends in April

        out: list[NbaGame] = []
        current_date = start_date

        # Iterate through each date and fetch games
        while current_date <= end_date:
            try:
                scoreboard_data = scoreboardv2.ScoreboardV2(
                    game_date=current_date.strftime("%Y-%m-%d")
                )
                games_dict = scoreboard_data.get_normalized_dict()

                if "GameHeader" in games_dict:
                    for game in games_dict["GameHeader"]:
                        game_date_str = game.get("GAME_DATE_EST")
                        game_date_obj: date | None = None
                        if game_date_str:
                            try:
                                game_date_obj = datetime.strptime(
                                    game_date_str, "%Y-%m-%dT%H:%M:%S"
                                ).date()
                            except (ValueError, TypeError):
                                pass

                        game_id = parse_str_or_none(game.get("GAME_ID"))
                        if not game_id:
                            continue

                        out.append(
                            NbaGame(
                                game_id=game_id,
                                season=season,
                                season_type=season_type,
                                game_date=game_date_obj,
                                status=parse_str_or_none(game.get("GAME_STATUS_TEXT")),
                                home_team_id=parse_int_or_none(game.get("HOME_TEAM_ID")),
                                away_team_id=parse_int_or_none(game.get("VISITOR_TEAM_ID")),
                                home_score=parse_int_or_none(game.get("HOME_TEAM_SCORE")),
                                away_score=parse_int_or_none(game.get("VISITOR_TEAM_SCORE")),
                                arena=parse_str_or_none(game.get("ARENA_NAME")),
                                attendance=parse_int_or_none(game.get("ATTENDANCE")),
                                raw=game,
                            )
                        )
            except Exception:
                # Skip dates with no games or API errors
                pass

            # Move to next day
            from datetime import timedelta
            current_date += timedelta(days=1)

        return out

    def get_player_game_stats(self, *, game_id: str) -> list[NbaPlayerGameStats]:
        """Fetch player statistics for a single game.

        Args:
            game_id: The NBA game ID

        Returns:
            List of NbaPlayerGameStats objects for all players in the game
        """
        try:
            boxscore = boxscoretraditionalv2.BoxScoreTraditionalV2(game_id=game_id)
            boxscore_dict = boxscore.get_normalized_dict()
        except Exception as e:
            raise NbaGameNotFoundError(f"Game {game_id} not found or unavailable") from e

        out: list[NbaPlayerGameStats] = []

        if "PlayerStats" in boxscore_dict:
            for player_stat in boxscore_dict["PlayerStats"]:
                player_id = parse_int_or_none(player_stat.get("PLAYER_ID"))
                if player_id is None or player_id == 0:
                    continue

                out.append(
                    NbaPlayerGameStats(
                        game_id=game_id,
                        player_id=player_id,
                        team_id=parse_int_or_none(player_stat.get("TEAM_ID")) or 0,
                        player_name=parse_str_or_none(player_stat.get("PLAYER_NAME")) or "",
                        starter=parse_bool_or_none(player_stat.get("START_POSITION")),
                        minutes=parse_str_or_none(player_stat.get("MIN")),
                        field_goals_made=parse_int_or_none(player_stat.get("FGM")),
                        field_goals_attempted=parse_int_or_none(player_stat.get("FGA")),
                        field_goal_pct=parse_float_or_none(player_stat.get("FG_PCT")),
                        three_pointers_made=parse_int_or_none(player_stat.get("FG3M")),
                        three_pointers_attempted=parse_int_or_none(player_stat.get("FG3A")),
                        three_point_pct=parse_float_or_none(player_stat.get("FG3_PCT")),
                        free_throws_made=parse_int_or_none(player_stat.get("FTM")),
                        free_throws_attempted=parse_int_or_none(player_stat.get("FTA")),
                        free_throw_pct=parse_float_or_none(player_stat.get("FT_PCT")),
                        offensive_rebounds=parse_int_or_none(player_stat.get("OREB")),
                        defensive_rebounds=parse_int_or_none(player_stat.get("DREB")),
                        total_rebounds=parse_int_or_none(player_stat.get("REB")),
                        assists=parse_int_or_none(player_stat.get("AST")),
                        steals=parse_int_or_none(player_stat.get("STL")),
                        blocks=parse_int_or_none(player_stat.get("BLK")),
                        turnovers=parse_int_or_none(player_stat.get("TO")),
                        personal_fouls=parse_int_or_none(player_stat.get("PF")),
                        points=parse_int_or_none(player_stat.get("PTS")),
                        plus_minus=parse_int_or_none(player_stat.get("PLUS_MINUS")),
                        raw=player_stat,
                    )
                )

        return out

    def get_player_info(self, *, player_id: int) -> NbaPlayer | None:
        """Get detailed player information.

        Args:
            player_id: The NBA player ID

        Returns:
            NbaPlayer object with player details, or None if not found
        """
        # First try to find in static players data
        all_players = static_players.get_players()

        player_data = None
        for p in all_players:
            if parse_int_or_none(p.get("id")) == player_id:
                player_data = p
                break

        if player_data is None:
            return None

        return NbaPlayer(
            player_id=player_id,
            full_name=parse_str_or_none(player_data.get("full_name")) or "",
            first_name=parse_str_or_none(player_data.get("first_name")),
            last_name=parse_str_or_none(player_data.get("last_name")),
            jersey_number=None,  # Not in static data
            position=None,  # Not in static data
            height=None,  # Not in static data
            weight=None,  # Not in static data
            birth_date=None,  # Not in static data
            country=None,  # Not in static data
            draft_year=None,  # Not in static data
            draft_round=None,  # Not in static data
            draft_number=None,  # Not in static data
            is_active=parse_bool_or_none(player_data.get("is_active")),
            raw=player_data,
        )

    def list_standings(
        self,
        *,
        season: str,
        season_type: str = "Regular Season",
    ) -> list[NbaStandingsRecord]:
        """Fetch NBA standings for a season.

        Args:
            season: The NBA season in format "2024-25"
            season_type: Season type (Regular Season, Playoffs, etc.)

        Returns:
            List of NbaStandingsRecord objects, one per team
        """
        try:
            standings = leaguestandingsv3.LeagueStandingsV3(
                league_id="00",
                season=season,
                season_type=season_type,
            )
            standings_dict = standings.get_normalized_dict()
        except Exception as e:
            raise NbaApiResponseError(f"Failed to fetch standings for {season}") from e

        out: list[NbaStandingsRecord] = []

        if "Standings" in standings_dict:
            for record in standings_dict["Standings"]:
                team_id = parse_int_or_none(record.get("TeamID"))
                if team_id is None:
                    continue

                season_year = parse_int_or_none(season.split("-")[0])

                out.append(
                    NbaStandingsRecord(
                        team_id=team_id,
                        season=season_year or 0,
                        season_type=season_type,
                        standings_date=None,  # Current standings
                        conference_id=None,  # Would need mapping
                        division_id=None,  # Would need mapping
                        conference_rank=parse_int_or_none(record.get("Conference")),
                        division_rank=parse_int_or_none(record.get("Division")),
                        wins=parse_int_or_none(record.get("WINS")),
                        losses=parse_int_or_none(record.get("LOSSES")),
                        win_pct=parse_float_or_none(record.get("WinPCT")),
                        games_back=parse_float_or_none(record.get("ConferenceGamesBack")),
                        conference_wins=parse_int_or_none(record.get("ConferenceRecord", "").split("-")[0] if "-" in str(record.get("ConferenceRecord", "")) else None),
                        conference_losses=parse_int_or_none(record.get("ConferenceRecord", "").split("-")[1] if "-" in str(record.get("ConferenceRecord", "")) else None),
                        home_wins=parse_int_or_none(record.get("HOME").split("-")[0] if "-" in str(record.get("HOME", "")) else None),
                        home_losses=parse_int_or_none(record.get("HOME").split("-")[1] if "-" in str(record.get("HOME", "")) else None),
                        away_wins=parse_int_or_none(record.get("ROAD").split("-")[0] if "-" in str(record.get("ROAD", "")) else None),
                        away_losses=parse_int_or_none(record.get("ROAD").split("-")[1] if "-" in str(record.get("ROAD", "")) else None),
                        last_ten_wins=parse_int_or_none(record.get("L10").split("-")[0] if "-" in str(record.get("L10", "")) else None),
                        last_ten_losses=parse_int_or_none(record.get("L10").split("-")[1] if "-" in str(record.get("L10", "")) else None),
                        streak=parse_str_or_none(record.get("strCurrentStreak")),
                        points_per_game=None,  # Not in this endpoint
                        opp_points_per_game=None,  # Not in this endpoint
                        diff_points_per_game=None,  # Not in this endpoint
                        raw=record,
                    )
                )

        return out

    def get_shot_chart_detail(
        self,
        *,
        game_id: str,
        player_id: int | None = None,
        team_id: int | None = None,
    ) -> list[NbaShotDetail]:
        """Fetch shot chart details for a game.

        Gets individual shot data including location, type, and outcome.
        Similar to MLB Statcast data.

        Args:
            game_id: The NBA game ID
            player_id: Optional - filter to specific player (0 = all players)
            team_id: Optional - filter to specific team (0 = all teams)

        Returns:
            List of NbaShotDetail objects for all shots in the game
        """
        try:
            shot_chart = shotchartdetail.ShotChartDetail(
                team_id=team_id or 0,
                player_id=player_id or 0,
                game_id=game_id,
                context_measure_simple="FGA",  # Field Goal Attempts
                season_nullable="",
                season_type_all_star="",
            )
            shot_data = shot_chart.get_normalized_dict()
        except Exception as e:
            raise NbaGameNotFoundError(
                f"Failed to fetch shot chart for game {game_id}"
            ) from e

        out: list[NbaShotDetail] = []

        if "Shot_Chart_Detail" in shot_data:
            for shot in shot_data["Shot_Chart_Detail"]:
                out.append(
                    NbaShotDetail(
                        game_id=game_id,
                        game_event_id=parse_int_or_none(shot.get("GAME_EVENT_ID")),
                        player_id=parse_int_or_none(shot.get("PLAYER_ID")) or 0,
                        player_name=parse_str_or_none(shot.get("PLAYER_NAME")),
                        team_id=parse_int_or_none(shot.get("TEAM_ID")) or 0,
                        team_name=parse_str_or_none(shot.get("TEAM_NAME")),
                        period=parse_int_or_none(shot.get("PERIOD")),
                        minutes_remaining=parse_int_or_none(shot.get("MINUTES_REMAINING")),
                        seconds_remaining=parse_int_or_none(shot.get("SECONDS_REMAINING")),
                        event_type=parse_str_or_none(shot.get("EVENT_TYPE")),
                        action_type=parse_str_or_none(shot.get("ACTION_TYPE")),
                        shot_type=parse_str_or_none(shot.get("SHOT_TYPE")),
                        shot_zone_basic=parse_str_or_none(shot.get("SHOT_ZONE_BASIC")),
                        shot_zone_area=parse_str_or_none(shot.get("SHOT_ZONE_AREA")),
                        shot_zone_range=parse_str_or_none(shot.get("SHOT_ZONE_RANGE")),
                        shot_distance=parse_int_or_none(shot.get("SHOT_DISTANCE")),
                        loc_x=parse_int_or_none(shot.get("LOC_X")),
                        loc_y=parse_int_or_none(shot.get("LOC_Y")),
                        shot_attempted_flag=parse_int_or_none(shot.get("SHOT_ATTEMPTED_FLAG")),
                        shot_made_flag=parse_int_or_none(shot.get("SHOT_MADE_FLAG")),
                        game_date=parse_str_or_none(shot.get("GAME_DATE")),
                        htm=parse_str_or_none(shot.get("HTM")),
                        vtm=parse_str_or_none(shot.get("VTM")),
                        raw=shot,
                    )
                )

        return out
