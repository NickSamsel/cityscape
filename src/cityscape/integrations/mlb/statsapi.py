from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any

import statsapi as mlb_statsapi


@dataclass(frozen=True, slots=True)
class MlbTeam:
    team_id: int
    team_name: str
    team_abbr: str | None
    league_id: int | None
    division_id: int | None
    raw: dict[str, Any]


@dataclass(frozen=True, slots=True)
class MlbGame:
    game_id: int
    season: int
    game_date: date | None
    game_type: str | None
    status: str | None
    home_team_id: int | None
    away_team_id: int | None
    home_score: int | None
    away_score: int | None
    raw: dict[str, Any]


class MlbStatsApi:
    """Free MLB Stats API client (no auth required)."""

    def _get_json(self, endpoint: str, params: dict[str, Any]) -> dict[str, Any]:
        payload = mlb_statsapi.get(endpoint, params)
        if not isinstance(payload, dict):
            raise TypeError(f"Expected dict from statsapi.get({endpoint!r}, ...), got {type(payload)}")
        return payload

    def list_teams(self, *, season: int) -> list[MlbTeam]:
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
                    league_id=(int(t["league"]["id"]) if isinstance(t.get("league"), dict) and t["league"].get("id") is not None else None),
                    division_id=(int(t["division"]["id"]) if isinstance(t.get("division"), dict) and t["division"].get("id") is not None else None),
                    raw=t,
                )
            )
        return out

    def get_regular_season_bounds(self, *, season: int) -> tuple[date | None, date | None]:
        """Return (start_date, end_date) for the MLB regular season.

        Uses the free MLB Stats API seasons endpoint.
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
        # gameTypes: comma-separated; common values include R (regular), S (spring), F (wild card), D, L, W
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

                def _team_id(side: dict[str, Any]) -> int | None:
                    team = side.get("team") if isinstance(side.get("team"), dict) else None
                    team_id_val = team.get("id") if isinstance(team, dict) else None
                    return int(team_id_val) if team_id_val is not None else None

                def _score(side: dict[str, Any]) -> int | None:
                    score_val = side.get("score")
                    return int(score_val) if score_val is not None else None

                status = g.get("status") if isinstance(g.get("status"), dict) else {}
                detailed_state = status.get("detailedState") if isinstance(status.get("detailedState"), str) else None

                out.append(
                    MlbGame(
                        game_id=game_id,
                        season=season,
                        game_date=game_date,
                        game_type=(g.get("gameType") if isinstance(g.get("gameType"), str) else None),
                        status=detailed_state,
                        home_team_id=_team_id(home),
                        away_team_id=_team_id(away),
                        home_score=_score(home),
                        away_score=_score(away),
                        raw=g,
                    )
                )

        return out
