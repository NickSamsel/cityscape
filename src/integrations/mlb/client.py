"""MLB Stats API client."""

from __future__ import annotations

from datetime import date
from typing import Any

import statsapi as mlb_statsapi

from .exceptions import MlbApiResponseError
from .models import (
    MlbDivision,
    MlbGame,
    MlbLeague,
    MlbPlayerBattingStats,
    MlbPlayerPitchingStats,
    MlbTeam,
)
from .utils import extract_score, extract_team_id, parse_int_or_none, parse_str_or_none


class MlbStatsApi:
    """Free MLB Stats API client (no authentication required).
    
    This client wraps the MLB-StatsAPI package to provide typed, structured
    access to MLB game, team, and player statistics data.
    """

    def _get_json(self, endpoint: str, params: dict[str, Any]) -> dict[str, Any]:
        """Make a request to the MLB Stats API and return JSON response."""
        payload = mlb_statsapi.get(endpoint, params)
        if not isinstance(payload, dict):
            raise MlbApiResponseError(
                f"Expected dict from statsapi.get({endpoint!r}, ...), got {type(payload)}"
            )
        return payload

    def list_leagues(self) -> list[MlbLeague]:
        """List all MLB leagues.
        
        Returns:
            List of MlbLeague objects containing league information
        """
        payload = self._get_json("league", {"sportId": 1})
        leagues = payload.get("leagues", [])
        out: list[MlbLeague] = []
        
        for lg in leagues:
            if not isinstance(lg, dict):
                continue
            league_id = int(lg.get("id"))
            out.append(
                MlbLeague(
                    league_id=league_id,
                    league_name=str(lg.get("name") or ""),
                    league_abbr=(lg.get("abbreviation") if isinstance(lg.get("abbreviation"), str) else None),
                    raw=lg,
                )
            )
        return out

    def list_divisions(self) -> list[MlbDivision]:
        """List all MLB divisions.
        
        Returns:
            List of MlbDivision objects containing division information
        """
        payload = self._get_json("divisions", {"sportId": 1})
        divisions = payload.get("divisions", [])
        out: list[MlbDivision] = []
        
        for d in divisions:
            if not isinstance(d, dict):
                continue
            division_id = int(d.get("id"))
            out.append(
                MlbDivision(
                    division_id=division_id,
                    division_name=str(d.get("name") or ""),
                    division_abbr=(d.get("abbreviation") if isinstance(d.get("abbreviation"), str) else None),
                    league_id=(
                        int(d["league"]["id"])
                        if isinstance(d.get("league"), dict) and d["league"].get("id") is not None
                        else None
                    ),
                    raw=d,
                )
            )
        return out

    def list_teams(self, *, season: int) -> list[MlbTeam]:
        """List all MLB teams for a given season.
        
        Args:
            season: The MLB season year (e.g., 2024)
            
        Returns:
            List of MlbTeam objects containing team information
        """
        payload = self._get_json("teams", {"sportId": 1, "season": season})
        teams = payload.get("teams", [])
        out: list[MlbTeam] = []
        
        for t in teams:
            if not isinstance(t, dict):
                continue
            team_id = int(t.get("id"))
            out.append(
                MlbTeam(
                    team_id=team_id,
                    team_name=str(t.get("name") or ""),
                    team_abbr=(t.get("abbreviation") if isinstance(t.get("abbreviation"), str) else None),
                    league_id=(
                        int(t["league"]["id"])
                        if isinstance(t.get("league"), dict) and t["league"].get("id") is not None
                        else None
                    ),
                    division_id=(
                        int(t["division"]["id"])
                        if isinstance(t.get("division"), dict) and t["division"].get("id") is not None
                        else None
                    ),
                    raw=t,
                )
            )
        return out

    def get_regular_season_bounds(self, *, season: int) -> tuple[date | None, date | None]:
        """Return start and end dates for the MLB regular season.

        Args:
            season: The MLB season year (e.g., 2024)
            
        Returns:
            Tuple of (start_date, end_date) for the season, or (None, None) if unavailable
        """
        payload = self._get_json("seasons", {"sportId": 1, "season": season})
        seasons = payload.get("seasons", [])
        
        if not seasons or not isinstance(seasons[0], dict):
            return None, None

        s0: dict[str, Any] = seasons[0]
        start_s = s0.get("regularSeasonStartDate")
        end_s = s0.get("regularSeasonEndDate")

        start_d = date.fromisoformat(start_s) if isinstance(start_s, str) and start_s else None
        end_d = date.fromisoformat(end_s) if isinstance(end_s, str) and end_s else None
        return start_d, end_d

    def list_games(
        self,
        *,
        season: int,
        game_types: str = "R",
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[MlbGame]:
        """List games for a given season and date range.
        
        Args:
            season: The MLB season year (e.g., 2024)
            game_types: Comma-separated game types (R=regular, S=spring, F=wild card, etc.)
            start_date: Optional start date filter
            end_date: Optional end date filter
            
        Returns:
            List of MlbGame objects
        """
        params: dict[str, Any] = {
            "sportId": 1,
            "season": season,
            "gameTypes": game_types,
        }
        if start_date is not None:
            params["startDate"] = start_date.isoformat()
        if end_date is not None:
            params["endDate"] = end_date.isoformat()

        payload = self._get_json("schedule", params)

        out: list[MlbGame] = []
        dates = payload.get("dates", [])
        
        for d in dates:
            if not isinstance(d, dict):
                continue
            games = d.get("games", [])
            
            for g in games:
                if not isinstance(g, dict):
                    continue

                game_id = int(g.get("gamePk"))

                official_date = g.get("officialDate")
                game_date: date | None
                if isinstance(official_date, str) and official_date:
                    try:
                        game_date = date.fromisoformat(official_date)
                    except ValueError:
                        game_date = None
                else:
                    game_date = None

                teams = g.get("teams") if isinstance(g.get("teams"), dict) else {}
                home = teams.get("home") if isinstance(teams.get("home"), dict) else {}
                away = teams.get("away") if isinstance(teams.get("away"), dict) else {}

                status = g.get("status") if isinstance(g.get("status"), dict) else {}
                detailed_state = (
                    status.get("detailedState") if isinstance(status.get("detailedState"), str) else None
                )

                out.append(
                    MlbGame(
                        game_id=game_id,
                        season=season,
                        game_date=game_date,
                        game_type=(g.get("gameType") if isinstance(g.get("gameType"), str) else None),
                        status=detailed_state,
                        home_team_id=extract_team_id(home),
                        away_team_id=extract_team_id(away),
                        home_score=extract_score(home),
                        away_score=extract_score(away),
                        raw=g,
                    )
                )

        return out

    def get_player_game_stats(
        self, *, game_id: int
    ) -> tuple[list[MlbPlayerBattingStats], list[MlbPlayerPitchingStats]]:
        """Fetch player batting and pitching statistics for a single game.
        
        Args:
            game_id: The MLB game ID (gamePk)
            
        Returns:
            Tuple of (batting_stats, pitching_stats) lists
        """
        boxscore = mlb_statsapi.boxscore_data(game_id)
        
        team_info = boxscore.get("teamInfo", {})
        away_team_id = team_info.get("away", {}).get("id")
        home_team_id = team_info.get("home", {}).get("id")
        
        batting_stats: list[MlbPlayerBattingStats] = []
        pitching_stats: list[MlbPlayerPitchingStats] = []
        
        # Process away batters
        for batter in boxscore.get("awayBatters", []):
            if batter.get("personId", 0) > 0:  # Skip header rows
                batting_stats.append(self._parse_batting_stats(batter, game_id, away_team_id))
        
        # Process home batters
        for batter in boxscore.get("homeBatters", []):
            if batter.get("personId", 0) > 0:
                batting_stats.append(self._parse_batting_stats(batter, game_id, home_team_id))
        
        # Process away pitchers
        for pitcher in boxscore.get("awayPitchers", []):
            if pitcher.get("personId", 0) > 0:  # Skip header rows
                pitching_stats.append(self._parse_pitching_stats(pitcher, game_id, away_team_id))
        
        # Process home pitchers
        for pitcher in boxscore.get("homePitchers", []):
            if pitcher.get("personId", 0) > 0:
                pitching_stats.append(self._parse_pitching_stats(pitcher, game_id, home_team_id))
        
        return batting_stats, pitching_stats
    
    def _parse_batting_stats(
        self, batter: dict[str, Any], game_id: int, team_id: int | None
    ) -> MlbPlayerBattingStats:
        """Parse batting statistics from boxscore data."""
        return MlbPlayerBattingStats(
            game_id=game_id,
            player_id=int(batter.get("personId", 0)),
            team_id=team_id or 0,
            player_name=str(batter.get("name", "")),
            batting_order=parse_str_or_none(batter.get("battingOrder")),
            position=parse_str_or_none(batter.get("position")),
            at_bats=parse_int_or_none(batter.get("ab")),
            runs=parse_int_or_none(batter.get("r")),
            hits=parse_int_or_none(batter.get("h")),
            doubles=parse_int_or_none(batter.get("doubles")),
            triples=parse_int_or_none(batter.get("triples")),
            home_runs=parse_int_or_none(batter.get("hr")),
            rbi=parse_int_or_none(batter.get("rbi")),
            stolen_bases=parse_int_or_none(batter.get("sb")),
            walks=parse_int_or_none(batter.get("bb")),
            strikeouts=parse_int_or_none(batter.get("k")),
            left_on_base=parse_int_or_none(batter.get("lob")),
            avg=parse_str_or_none(batter.get("avg")),
            obp=parse_str_or_none(batter.get("obp")),
            slg=parse_str_or_none(batter.get("slg")),
            ops=parse_str_or_none(batter.get("ops")),
            raw=batter,
        )
    
    def _parse_pitching_stats(
        self, pitcher: dict[str, Any], game_id: int, team_id: int | None
    ) -> MlbPlayerPitchingStats:
        """Parse pitching statistics from boxscore data."""
        return MlbPlayerPitchingStats(
            game_id=game_id,
            player_id=int(pitcher.get("personId", 0)),
            team_id=team_id or 0,
            player_name=str(pitcher.get("name", "")),
            innings_pitched=parse_str_or_none(pitcher.get("ip")),
            hits=parse_int_or_none(pitcher.get("h")),
            runs=parse_int_or_none(pitcher.get("r")),
            earned_runs=parse_int_or_none(pitcher.get("er")),
            walks=parse_int_or_none(pitcher.get("bb")),
            strikeouts=parse_int_or_none(pitcher.get("k")),
            home_runs=parse_int_or_none(pitcher.get("hr")),
            pitches=parse_int_or_none(pitcher.get("p")),
            strikes=parse_int_or_none(pitcher.get("s")),
            era=parse_str_or_none(pitcher.get("era")),
            raw=pitcher,
        )
