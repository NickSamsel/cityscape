"""MLB Stats API client."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

import statsapi as mlb_statsapi

from .exceptions import MlbApiResponseError
from .models import (
    MlbBroadcast,
    MlbDivision,
    MlbGame,
    MlbLeague,
    MlbLineupEntry,
    MlbPlayer,
    MlbPlayerBattingStats,
    MlbPlayerPitchingStats,
    MlbScheduleEntry,
    MlbStandingsRecord,
    MlbStatcastBattedBall,
    MlbStatcastPitch,
    MlbTeam,
    MlbVenue,
    MlbRosterEntry,
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

    def list_standings(
        self,
        *,
        season: int,
        standings_date: date | None = None,
    ) -> list[MlbStandingsRecord]:
        """Fetch MLB standings for a season, optionally as of a specific date.

        Args:
            season: The MLB season year (e.g., 2024)
            standings_date: Optional date to get historical standings snapshot.
                            If None, returns end-of-season standings.

        Returns:
            List of MlbStandingsRecord objects, one per team.
        """
        params: dict[str, Any] = {
            "leagueId": "103,104",  # AL + NL
            "season": season,
            "standingsTypes": "regularSeason",
        }
        if standings_date is not None:
            params["date"] = standings_date.isoformat()

        payload = self._get_json("standings", params)

        out: list[MlbStandingsRecord] = []
        records = payload.get("records", [])

        for division_record in records:
            if not isinstance(division_record, dict):
                continue

            division_info = division_record.get("division", {})
            division_id = (
                int(division_info["id"])
                if isinstance(division_info, dict) and division_info.get("id") is not None
                else None
            )

            league_info = division_record.get("league", {})
            league_id = (
                int(league_info["id"])
                if isinstance(league_info, dict) and league_info.get("id") is not None
                else None
            )

            team_records = division_record.get("teamRecords", [])
            for tr in team_records:
                if not isinstance(tr, dict):
                    continue

                team_info = tr.get("team", {})
                team_id = int(team_info["id"]) if isinstance(team_info, dict) and team_info.get("id") is not None else None
                if team_id is None:
                    continue

                # Parse streak
                streak_obj = tr.get("streak", {})
                streak_str = None
                if isinstance(streak_obj, dict) and streak_obj.get("streakCode"):
                    streak_str = str(streak_obj["streakCode"])

                # Parse last 10 record from records.splitRecords
                last_ten = None
                split_records = tr.get("records", {}).get("splitRecords", []) if isinstance(tr.get("records"), dict) else []
                for sr in split_records:
                    if isinstance(sr, dict) and sr.get("type") == "lastTen":
                        last_ten = f"{sr.get('wins', 0)}-{sr.get('losses', 0)}"
                        break

                # Parse home/away records
                home_wins = None
                home_losses = None
                away_wins = None
                away_losses = None
                for sr in split_records:
                    if isinstance(sr, dict):
                        if sr.get("type") == "home":
                            home_wins = parse_int_or_none(sr.get("wins"))
                            home_losses = parse_int_or_none(sr.get("losses"))
                        elif sr.get("type") == "away":
                            away_wins = parse_int_or_none(sr.get("wins"))
                            away_losses = parse_int_or_none(sr.get("losses"))

                # Parse games back
                gb_str = tr.get("gamesBack")
                games_back: float | None = None
                if gb_str is not None and gb_str != "-":
                    try:
                        games_back = float(gb_str)
                    except (ValueError, TypeError):
                        pass
                elif gb_str == "-":
                    games_back = 0.0

                wc_gb_str = tr.get("wildCardGamesBack")
                wc_games_back: float | None = None
                if wc_gb_str is not None and wc_gb_str != "-":
                    try:
                        wc_games_back = float(wc_gb_str)
                    except (ValueError, TypeError):
                        pass
                elif wc_gb_str == "-":
                    wc_games_back = 0.0

                wins = parse_int_or_none(tr.get("wins"))
                losses = parse_int_or_none(tr.get("losses"))
                rs = parse_int_or_none(tr.get("runsScored"))
                ra = parse_int_or_none(tr.get("runsAllowed"))

                out.append(
                    MlbStandingsRecord(
                        team_id=team_id,
                        season=season,
                        standings_date=standings_date,
                        league_id=league_id,
                        division_id=division_id,
                        division_rank=parse_int_or_none(tr.get("divisionRank")),
                        wins=wins,
                        losses=losses,
                        win_pct=self._safe_float(tr.get("winningPercentage")),
                        games_back=games_back,
                        wildcard_games_back=wc_games_back,
                        streak=streak_str,
                        last_ten_record=last_ten,
                        runs_scored=rs,
                        runs_allowed=ra,
                        run_differential=rs - ra if rs is not None and ra is not None else None,
                        home_wins=home_wins,
                        home_losses=home_losses,
                        away_wins=away_wins,
                        away_losses=away_losses,
                        raw=tr,
                    )
                )

        return out

    def list_games(
        self,
        *,
        season: int,
        game_types: str = "R,F,L,W",  # Default: all except spring (R=regular, F=wild card, L=league championship, W=world series)
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[MlbGame]:
        """List games for a given season and date range.

        Args:
            season: The MLB season year (e.g., 2024)
            game_types: Comma-separated game types (R=regular, F=wild card, L=league championship, W=world series, etc.)
                        Default is all except spring training.
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

                venue = g.get("venue") if isinstance(g.get("venue"), dict) else {}
                venue_id = parse_int_or_none(venue.get("id"))

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
                        venue_id=venue_id,
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

    def get_player_info(self, *, player_id: int) -> MlbPlayer | None:
        """Get detailed player information.
        
        Args:
            player_id: The MLB player ID
            
        Returns:
            MlbPlayer object with player details, or None if not found
        """
        payload = self._get_json("person", {"personId": player_id})
        people = payload.get("people", [])
        
        if not people or not isinstance(people[0], dict):
            return None
        
        p = people[0]
        
        # Parse birth date
        birth_date_str = p.get("birthDate")
        birth_date: date | None = None
        if isinstance(birth_date_str, str) and birth_date_str:
            try:
                birth_date = date.fromisoformat(birth_date_str)
            except ValueError:
                pass
        
        # Parse MLB debut date
        debut_date_str = p.get("mlbDebutDate")
        debut_date: date | None = None
        if isinstance(debut_date_str, str) and debut_date_str:
            try:
                debut_date = date.fromisoformat(debut_date_str)
            except ValueError:
                pass
        
        # Extract position info
        primary_position = p.get("primaryPosition", {})
        position_code = primary_position.get("code") if isinstance(primary_position, dict) else None
        position_name = primary_position.get("name") if isinstance(primary_position, dict) else None
        position_abbr = primary_position.get("abbreviation") if isinstance(primary_position, dict) else None
        
        # Extract bat/pitch hand info
        bat_side = p.get("batSide", {})
        bat_code = bat_side.get("code") if isinstance(bat_side, dict) else None
        bat_desc = bat_side.get("description") if isinstance(bat_side, dict) else None
        
        pitch_hand = p.get("pitchHand", {})
        pitch_code = pitch_hand.get("code") if isinstance(pitch_hand, dict) else None
        pitch_desc = pitch_hand.get("description") if isinstance(pitch_hand, dict) else None
        
        return MlbPlayer(
            player_id=int(p.get("id")),
            full_name=str(p.get("fullName", "")),
            first_name=parse_str_or_none(p.get("firstName")),
            last_name=parse_str_or_none(p.get("lastName")),
            primary_number=parse_str_or_none(p.get("primaryNumber")),
            birth_date=birth_date,
            current_age=parse_int_or_none(p.get("currentAge")),
            birth_city=parse_str_or_none(p.get("birthCity")),
            birth_state_province=parse_str_or_none(p.get("birthStateProvince")),
            birth_country=parse_str_or_none(p.get("birthCountry")),
            height=parse_str_or_none(p.get("height")),
            weight=parse_int_or_none(p.get("weight")),
            primary_position_code=parse_str_or_none(position_code),
            primary_position_name=parse_str_or_none(position_name),
            primary_position_abbr=parse_str_or_none(position_abbr),
            bat_side_code=parse_str_or_none(bat_code),
            bat_side_description=parse_str_or_none(bat_desc),
            pitch_hand_code=parse_str_or_none(pitch_code),
            pitch_hand_description=parse_str_or_none(pitch_desc),
            mlb_debut_date=debut_date,
            active=p.get("active") if isinstance(p.get("active"), bool) else None,
            raw=p,
        )

    def get_game_statcast_data(
        self, *, game_id: int
    ) -> tuple[list[MlbStatcastPitch], list[MlbStatcastBattedBall]]:
        """Fetch Statcast pitch-level and batted ball data for a game.
        
        Args:
            game_id: The MLB game ID (gamePk)
            
        Returns:
            Tuple of (pitch_data, batted_ball_data) lists with Statcast metrics
        """
        # Get play-by-play data which includes Statcast metrics
        try:
            payload = self._get_json("game_playByPlay", {"gamePk": game_id})
        except Exception:
            # If playByPlay not available, return empty data
            return [], []
        
        pitches: list[MlbStatcastPitch] = []
        batted_balls: list[MlbStatcastBattedBall] = []
        
        all_plays = payload.get("allPlays", [])
        
        for at_bat_index, play in enumerate(all_plays):
            if not isinstance(play, dict):
                continue
            
            # Extract matchup info
            matchup = play.get("matchup", {})
            if not isinstance(matchup, dict):
                continue
            
            batter = matchup.get("batter", {})
            pitcher = matchup.get("pitcher", {})
            
            batter_id = batter.get("id") if isinstance(batter, dict) else None
            pitcher_id = pitcher.get("id") if isinstance(pitcher, dict) else None
            
            if not batter_id or not pitcher_id:
                continue
            
            # Process each pitch in the at-bat
            play_events = play.get("playEvents", [])
            
            for pitch_num, event in enumerate(play_events, 1):
                if not isinstance(event, dict):
                    continue
                
                # Process pitch data if available
                pitch_data = event.get("pitchData", {})
                if isinstance(pitch_data, dict) and pitch_data:
                    # Extract pitch metrics
                    details = event.get("details", {})
                    if not isinstance(details, dict):
                        details = {}
                    
                    count = event.get("count", {})
                    if not isinstance(count, dict):
                        count = {}
                    
                    # Create unique play ID
                    play_id = f"{game_id}_{at_bat_index}_{pitch_num}"
                    
                    # Extract Statcast pitch metrics
                    coordinates = pitch_data.get("coordinates", {})
                    if not isinstance(coordinates, dict):
                        coordinates = {}
                    
                    breaks = pitch_data.get("breaks", {})
                    if not isinstance(breaks, dict):
                        breaks = {}
                    
                    # Get pitch type
                    pitch_type_obj = details.get("type", {})
                    if isinstance(pitch_type_obj, dict):
                        pitch_type = pitch_type_obj.get("code")
                        pitch_type_desc = pitch_type_obj.get("description")
                    else:
                        pitch_type = None
                        pitch_type_desc = None
                    
                    # Create Statcast pitch record
                    statcast_pitch = MlbStatcastPitch(
                        play_id=play_id,
                        game_id=game_id,
                        at_bat_index=at_bat_index,
                        pitcher_id=pitcher_id,
                        batter_id=batter_id,
                        catcher_id=matchup.get("catcher", {}).get("id") if isinstance(matchup.get("catcher"), dict) else None,
                        umpire_id=None,  # Not always available in play-by-play
                        pitch_number=pitch_num,
                        pitch_type=pitch_type,
                        pitch_type_description=pitch_type_desc,
                        release_speed=self._safe_float(pitch_data.get("startSpeed")),
                        release_spin_rate=self._safe_float(breaks.get("spinRate")),
                        release_extension=self._safe_float(pitch_data.get("extension")),
                        release_pos_x=self._safe_float(coordinates.get("x")),
                        release_pos_y=self._safe_float(coordinates.get("y")),
                        release_pos_z=self._safe_float(pitch_data.get("coordinates", {}).get("pZ")),
                        zone=parse_int_or_none(pitch_data.get("zone")),
                        plate_x=self._safe_float(coordinates.get("pX")),
                        plate_z=self._safe_float(coordinates.get("pZ")),
                        strikes=parse_int_or_none(count.get("strikes")),
                        balls=parse_int_or_none(count.get("balls")),
                        outs=parse_int_or_none(count.get("outs")),
                        pitch_result=details.get("code"),
                        pitch_result_description=details.get("description"),
                        raw=event,
                    )
                    pitches.append(statcast_pitch)
                
                # Check for batted ball data (separate from pitch data check)
                hit_data = event.get("hitData", {})
                if isinstance(hit_data, dict) and hit_data:
                    # Extract details for context
                    details = event.get("details", {})
                    if not isinstance(details, dict):
                        details = {}
                    
                    # Create unique play ID for batted ball
                    play_id = f"{game_id}_{at_bat_index}_{pitch_num}"
                    
                    # Extract batted ball metrics
                    launch_speed = self._safe_float(hit_data.get("launchSpeed"))
                    launch_angle = self._safe_float(hit_data.get("launchAngle"))
                    
                    # Determine if it's a barrel or hard hit
                    is_barrel = False
                    is_hard_hit = False
                    
                    if launch_speed and launch_angle:
                        is_hard_hit = launch_speed >= 95.0
                        # Barrel definition: 98+ mph exit velo, 26-30 degree launch angle
                        if launch_speed >= 98.0 and 26.0 <= launch_angle <= 30.0:
                            is_barrel = True
                    
                    batted_ball = MlbStatcastBattedBall(
                        play_id=play_id,
                        game_id=game_id,
                        at_bat_index=at_bat_index,
                        batter_id=batter_id,
                        pitcher_id=pitcher_id,
                        launch_speed=launch_speed,
                        launch_angle=launch_angle,
                        launch_distance=self._safe_float(hit_data.get("totalDistance")),
                        hit_location=parse_int_or_none(hit_data.get("location")),
                        hit_trajectory=hit_data.get("trajectory"),
                        hit_result=details.get("event"),
                        sprint_speed=None,  # Not available in play-by-play
                        is_barrel=is_barrel if launch_speed and launch_angle else None,
                        is_hard_hit=is_hard_hit if launch_speed else None,
                        raw=hit_data,
                    )
                    batted_balls.append(batted_ball)
        
        return pitches, batted_balls
        
    def list_schedule(
        self,
        *,
        season: int,
        game_types: str = "R,F,D,L,W,S",
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> Tuple[list["MlbScheduleEntry"], list["MlbBroadcast"], list["MlbLineupEntry"]]:
        """Fetch the entire season's schedule with all hydrations."""
        
        # This matches your working URL exactly
        params: dict[str, Any] = {
            "sportId": 1,
            "season": season,
            "gameTypes": game_types,
            "hydrate": "probablePitcher,broadcasts,venue,lineups",
        }

        if start_date is not None:
            params["startDate"] = start_date.isoformat()
        if end_date is not None:
            params["endDate"] = end_date.isoformat()

        payload = self._get_json("schedule", params)

        schedule_entries: list[MlbScheduleEntry] = []
        broadcasts: list[MlbBroadcast] = []
        lineup_entries: list[MlbLineupEntry] = []

        # The API nests games under a list of "dates"
        for d in payload.get("dates", []):
            for g in d.get("games", []):
                game_id = int(g.get("gamePk"))

                # 1. Parse Game Details
                teams = g.get("teams", {})
                home = teams.get("home", {})
                away = teams.get("away", {})
                
                # 2. Extract Probable Pitchers
                home_pp = home.get("probablePitcher", {})
                away_pp = away.get("probablePitcher", {})

                # 3. Create Schedule Entry
                entry = MlbScheduleEntry(
                    game_id=game_id,
                    season=season,
                    game_date=date.fromisoformat(g["officialDate"]) if g.get("officialDate") else None,
                    game_datetime=datetime.fromisoformat(g["gameDate"].replace("Z", "+00:00")) if g.get("gameDate") else None,
                    game_type=g.get("gameType"),
                    status=g.get("status", {}).get("detailedState"),
                    day_night=g.get("dayNight"),
                    venue_id=parse_int_or_none(g.get("venue", {}).get("id")),
                    venue_name=g.get("venue", {}).get("name"),
                    home_team_id=extract_team_id(home),
                    away_team_id=extract_team_id(away),
                    home_probable_pitcher_id=parse_int_or_none(home_pp.get("id")),
                    home_probable_pitcher_name=home_pp.get("fullName"),
                    away_probable_pitcher_id=parse_int_or_none(away_pp.get("id")),
                    away_probable_pitcher_name=away_pp.get("fullName"),
                    scheduled_innings=g.get("scheduledInnings"),
                    series_description=g.get("seriesDescription"),
                    raw=g,
                )
                schedule_entries.append(entry)

                # 4. Extract Broadcasts
                for bc in g.get("broadcasts", []):
                    broadcasts.append(MlbBroadcast(
                        game_id=game_id,
                        broadcast_name=bc.get("name"),
                        broadcast_type=bc.get("type"),
                        call_sign=bc.get("callSign"),
                        is_national=bc.get("isNational"),
                        home_away=bc.get("homeAway"),
                        language=bc.get("language"),
                        raw=bc,
                    ))

                # 5. Extract Lineups
                lineups = g.get("lineups", {})
                for side in ["home", "away"]:
                    players = lineups.get(f"{side}Players", [])
                    for order_idx, player in enumerate(players, 1):
                        pid = parse_int_or_none(player.get("id"))
                        if not pid: continue
                        
                        lineup_entries.append(MlbLineupEntry(
                            game_id=game_id,
                            player_id=pid,
                            team_side=side,
                            full_name=player.get("fullName", ""),
                            position_abbreviation=player.get("primaryPosition", {}).get("abbreviation"),
                            batting_order=order_idx,
                            raw=player,
                        ))

        return schedule_entries, broadcasts, lineup_entries

    def list_venues(
        self,
        *,
        venue_ids: list[int],
        season: int | None = None,
        hydrate: str = "location,fieldInfo",
    ) -> list[MlbVenue]:
        """Fetch venue (ballpark) reference data.

        Uses the MLB Stats API `venue` endpoint, which requires venueIds.
        """
        if not venue_ids:
            return []

        params: dict[str, Any] = {
            "venueIds": ",".join(str(v) for v in sorted(set(venue_ids))),
        }
        if season is not None:
            params["season"] = season
        if hydrate:
            params["hydrate"] = hydrate

        payload = self._get_json("venue", params)

        venues: list[MlbVenue] = []
        for v in payload.get("venues", []):
            if not isinstance(v, dict):
                continue

            venue_id = parse_int_or_none(v.get("id"))
            if venue_id is None:
                continue

            location = v.get("location") if isinstance(v.get("location"), dict) else {}
            default_coords = (
                location.get("defaultCoordinates")
                if isinstance(location.get("defaultCoordinates"), dict)
                else {}
            )
            field_info = v.get("fieldInfo") if isinstance(v.get("fieldInfo"), dict) else {}

            venues.append(
                MlbVenue(
                    venue_id=venue_id,
                    season=parse_int_or_none(v.get("season")),
                    venue_name=parse_str_or_none(v.get("name")),
                    active=v.get("active") if isinstance(v.get("active"), bool) else None,
                    city=parse_str_or_none(location.get("city")),
                    state=parse_str_or_none(location.get("state")),
                    state_abbrev=parse_str_or_none(location.get("stateAbbrev")),
                    country=parse_str_or_none(location.get("country")),
                    latitude=self._safe_float(default_coords.get("latitude")),
                    longitude=self._safe_float(default_coords.get("longitude")),
                    capacity=parse_int_or_none(field_info.get("capacity")),
                    turf_type=parse_str_or_none(field_info.get("turfType")),
                    roof_type=parse_str_or_none(field_info.get("roofType")),
                    left_line=self._safe_float(field_info.get("leftLine")),
                    right_line=self._safe_float(field_info.get("rightLine")),
                    center=self._safe_float(field_info.get("center")),
                    left=self._safe_float(field_info.get("left")),
                    right=self._safe_float(field_info.get("right")),
                    left_center=self._safe_float(field_info.get("leftCenter")),
                    right_center=self._safe_float(field_info.get("rightCenter")),
                    raw=v,
                )
            )

        return venues
    def get_roster(self, *, team_id: int, season: int) -> list[MlbRosterEntry]:
        """Fetch the roster for a given team and season."""
        params = {
            "teamId": team_id,
            "season": season,
        }
        payload = self._get_json("team_roster", params)

        roster: list[MlbRosterEntry] = []
        for p in payload.get("roster", []):
            if not isinstance(p, dict):
                continue

            person = p.get("person", {})
            if not isinstance(person, dict):
                continue

            player_id = parse_int_or_none(person.get("id"))
            if player_id is None:
                continue

            position = p.get("position", {})
            roster.append(
                MlbRosterEntry(
                    team_id=team_id,
                    season=season,
                    player_id=player_id,
                    player_name=person.get("fullName"),
                    position_code=position.get("code") if isinstance(position, dict) else None,
                    position_name=position.get("name") if isinstance(position, dict) else None,
                    position_abbr=position.get("abbreviation") if isinstance(position, dict) else None,
                    raw=p,
                )
            )

        return roster
    
    def _safe_float(self, value: Any) -> float | None:
        """Safely convert value to float, returning None if invalid."""
        if value is None:
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None
