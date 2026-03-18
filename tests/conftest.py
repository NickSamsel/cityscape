"""Shared fixtures for MLB ingestion unit tests."""
from __future__ import annotations

import pytest
from datetime import date, datetime
from unittest.mock import MagicMock

from src.integrations.mlb.models import (
    MlbBroadcast,
    MlbDivision,
    MlbGame,
    MlbLeague,
    MlbLineupEntry,
    MlbPlayer,
    MlbPlayerBattingStats,
    MlbPlayerPitchingStats,
    MlbRosterEntry,
    MlbScheduleEntry,
    MlbStandingsRecord,
    MlbStatcastBattedBall,
    MlbStatcastPitch,
    MlbTeam,
    MlbVenue,
)


@pytest.fixture
def settings():
    s = MagicMock()
    s.gcp_project_id = "test-project"
    s.gcp_credentials_path = None
    s.gcp_service_account_key = None
    return s


@pytest.fixture
def bq_client():
    return MagicMock()


# --- MLB model fixtures ---

@pytest.fixture
def batting_stat():
    return MlbPlayerBattingStats(
        game_id=123456, player_id=100, team_id=10, player_name="John Doe",
        batting_order="1", position="CF", at_bats=4, runs=1, hits=2,
        doubles=0, triples=0, home_runs=1, rbi=2, stolen_bases=0,
        walks=1, strikeouts=1, left_on_base=2,
        avg=".300", obp=".350", slg=".550", ops=".900", raw={},
    )


@pytest.fixture
def pitching_stat():
    return MlbPlayerPitchingStats(
        game_id=123456, player_id=200, team_id=10, player_name="Jane Smith",
        innings_pitched="6.0", hits=5, runs=2, earned_runs=2,
        walks=2, strikeouts=8, home_runs=1, pitches=95, strikes=62,
        era="3.00", raw={},
    )


@pytest.fixture
def mlb_game_final():
    return MlbGame(
        game_id=123456, season=2024, game_date=date(2024, 9, 1),
        game_type="R", status="Final", home_team_id=10, away_team_id=20,
        home_score=5, away_score=3, venue_id=1, raw={},
    )


@pytest.fixture
def mlb_game_scheduled():
    return MlbGame(
        game_id=999999, season=2024, game_date=date(2024, 9, 15),
        game_type="R", status="Scheduled", home_team_id=10, away_team_id=20,
        home_score=None, away_score=None, venue_id=1, raw={},
    )


@pytest.fixture
def mlb_team():
    return MlbTeam(
        team_id=10, team_name="Test Team", team_abbr="TST",
        league_id=103, division_id=200, raw={},
    )


@pytest.fixture
def mlb_league():
    return MlbLeague(league_id=103, league_name="American League", league_abbr="AL", raw={})


@pytest.fixture
def mlb_division():
    return MlbDivision(
        division_id=200, division_name="AL East", division_abbr="ALE",
        league_id=103, raw={},
    )


@pytest.fixture
def mlb_player():
    return MlbPlayer(
        player_id=100, full_name="John Doe", first_name="John", last_name="Doe",
        primary_number="7", birth_date=date(1995, 3, 15), current_age=29,
        birth_city="Dallas", birth_state_province="TX", birth_country="USA",
        height="6-2", weight=195, primary_position_code="CF",
        primary_position_name="Center Field", primary_position_abbr="CF",
        bat_side_code="R", bat_side_description="Right",
        pitch_hand_code=None, pitch_hand_description=None,
        mlb_debut_date=date(2018, 4, 1), active=True, raw={},
    )


@pytest.fixture
def mlb_standings_record():
    return MlbStandingsRecord(
        team_id=10, season=2024, standings_date=None, league_id=103,
        division_id=200, division_rank=1, wins=90, losses=72, win_pct=0.556,
        games_back=0.0, wildcard_games_back=None, streak="W3",
        last_ten_record="7-3", runs_scored=750, runs_allowed=650,
        run_differential=100, home_wins=48, home_losses=33,
        away_wins=42, away_losses=39, raw={},
    )


@pytest.fixture
def mlb_roster_entry():
    return MlbRosterEntry(
        team_id=10, player_id=100, season=2024, player_name="John Doe",
        position_code="CF", position_name="Center Field", position_abbr="CF",
        raw={},
    )


@pytest.fixture
def mlb_venue():
    return MlbVenue(
        venue_id=1, season=2024, venue_name="Test Stadium", active=True,
        city="Test City", state="Texas", state_abbrev="TX", country="USA",
        latitude=30.0, longitude=-97.0, capacity=42000, turf_type="Grass",
        roof_type="Open", left_line=330.0, right_line=330.0, center=404.0,
        left=340.0, right=340.0, left_center=375.0, right_center=375.0, raw={},
    )


@pytest.fixture
def mlb_schedule_entry_scheduled():
    return MlbScheduleEntry(
        game_id=123456, season=2024, game_date=date(2024, 9, 1),
        game_datetime=datetime(2024, 9, 1, 19, 5), game_type="R",
        status="Scheduled", day_night="night", venue_id=1, venue_name="Test Stadium",
        home_team_id=10, away_team_id=20, home_probable_pitcher_id=200,
        home_probable_pitcher_name="Jane Smith", away_probable_pitcher_id=300,
        away_probable_pitcher_name="Bob Smith", scheduled_innings=9,
        series_description="Regular Season", raw={},
    )


@pytest.fixture
def mlb_schedule_entry_final():
    return MlbScheduleEntry(
        game_id=654321, season=2024, game_date=date(2024, 9, 1),
        game_datetime=datetime(2024, 9, 1, 13, 5), game_type="R",
        status="Final", day_night="day", venue_id=2, venue_name="Other Stadium",
        home_team_id=30, away_team_id=40, home_probable_pitcher_id=None,
        home_probable_pitcher_name=None, away_probable_pitcher_id=None,
        away_probable_pitcher_name=None, scheduled_innings=9,
        series_description="Regular Season", raw={},
    )


@pytest.fixture
def mlb_broadcast():
    return MlbBroadcast(
        game_id=123456, broadcast_name="ESPN", broadcast_type="TV",
        call_sign="ESPN", is_national=True, home_away=None,
        language="en", raw={},
    )


@pytest.fixture
def mlb_lineup_entry():
    return MlbLineupEntry(
        game_id=123456, player_id=100, team_side="home",
        full_name="John Doe", position_abbreviation="CF",
        batting_order=1, raw={},
    )


@pytest.fixture
def mlb_statcast_pitch():
    return MlbStatcastPitch(
        play_id="abc-123", game_id=123456, at_bat_index=0,
        pitcher_id=200, batter_id=100, catcher_id=300, umpire_id=999,
        pitch_number=1, pitch_type="FF", pitch_type_description="Four-Seam Fastball",
        release_speed=95.2, release_spin_rate=2300.0, release_extension=6.5,
        release_pos_x=1.2, release_pos_y=54.3, release_pos_z=5.8,
        zone=5, plate_x=0.1, plate_z=2.5, strikes=0, balls=0, outs=0,
        pitch_result="ball", pitch_result_description="Ball", raw={},
    )


@pytest.fixture
def mlb_statcast_batted_ball():
    return MlbStatcastBattedBall(
        play_id="abc-124", game_id=123456, at_bat_index=1,
        batter_id=100, pitcher_id=200, launch_speed=105.3, launch_angle=28.0,
        launch_distance=420.0, hit_location=8, hit_trajectory="fly_ball",
        hit_result="home_run", sprint_speed=28.5, is_barrel=True,
        is_hard_hit=True, raw={},
    )
