"""Unit tests for MLB season data ingestion."""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch

from src.automations.ingest.mlb.seasons import (
    fetch_mlb_season_data,
    fetch_mlb_reference_data,
)

MODULE = "src.automations.ingest.mlb.seasons"


class TestFetchMlbSeasonData:
    def test_filters_games_to_final_status_only(self, mlb_team, mlb_game_final, mlb_game_scheduled):
        with patch(f"{MODULE}.MlbStatsApi") as MockApi, \
             patch(f"{MODULE}.get_run_logger"):
            api = MockApi.return_value
            api.list_teams.return_value = [mlb_team]
            api.list_games.return_value = [mlb_game_final, mlb_game_scheduled]
            _, game_rows = fetch_mlb_season_data(season=2024)

        assert len(game_rows) == 1
        assert game_rows[0]["game_id"] == mlb_game_final.game_id

    def test_team_row_has_correct_fields(self, mlb_team):
        with patch(f"{MODULE}.MlbStatsApi") as MockApi, \
             patch(f"{MODULE}.get_run_logger"):
            api = MockApi.return_value
            api.list_teams.return_value = [mlb_team]
            api.list_games.return_value = []
            team_rows, _ = fetch_mlb_season_data(season=2024)

        assert len(team_rows) == 1
        expected_fields = {"team_id", "season", "team_name", "team_abbr", "league_id", "division_id", "raw"}
        assert set(team_rows[0].keys()) == expected_fields

    def test_team_row_values_match_model(self, mlb_team):
        with patch(f"{MODULE}.MlbStatsApi") as MockApi, \
             patch(f"{MODULE}.get_run_logger"):
            api = MockApi.return_value
            api.list_teams.return_value = [mlb_team]
            api.list_games.return_value = []
            team_rows, _ = fetch_mlb_season_data(season=2024)

        row = team_rows[0]
        assert row["team_id"] == 10
        assert row["team_name"] == "Test Team"
        assert row["team_abbr"] == "TST"
        assert row["season"] == 2024

    def test_game_row_has_correct_fields(self, mlb_team, mlb_game_final):
        with patch(f"{MODULE}.MlbStatsApi") as MockApi, \
             patch(f"{MODULE}.get_run_logger"):
            api = MockApi.return_value
            api.list_teams.return_value = [mlb_team]
            api.list_games.return_value = [mlb_game_final]
            _, game_rows = fetch_mlb_season_data(season=2024)

        expected_fields = {
            "game_id", "season", "game_date", "game_type", "status",
            "home_team_id", "away_team_id", "home_score", "away_score", "venue_id", "raw",
        }
        assert set(game_rows[0].keys()) == expected_fields

    def test_game_row_values_match_model(self, mlb_team, mlb_game_final):
        with patch(f"{MODULE}.MlbStatsApi") as MockApi, \
             patch(f"{MODULE}.get_run_logger"):
            api = MockApi.return_value
            api.list_teams.return_value = [mlb_team]
            api.list_games.return_value = [mlb_game_final]
            _, game_rows = fetch_mlb_season_data(season=2024)

        row = game_rows[0]
        assert row["game_id"] == 123456
        assert row["home_score"] == 5
        assert row["away_score"] == 3


class TestFetchMlbReferenceData:
    def test_league_row_has_correct_fields(self, mlb_league):
        with patch(f"{MODULE}.MlbStatsApi") as MockApi, \
             patch(f"{MODULE}.get_run_logger"):
            api = MockApi.return_value
            api.list_leagues.return_value = [mlb_league]
            api.list_divisions.return_value = []
            league_rows, _ = fetch_mlb_reference_data()

        expected_fields = {"league_id", "league_name", "league_abbr", "raw"}
        assert set(league_rows[0].keys()) == expected_fields

    def test_league_row_values_match_model(self, mlb_league):
        with patch(f"{MODULE}.MlbStatsApi") as MockApi, \
             patch(f"{MODULE}.get_run_logger"):
            api = MockApi.return_value
            api.list_leagues.return_value = [mlb_league]
            api.list_divisions.return_value = []
            league_rows, _ = fetch_mlb_reference_data()

        assert league_rows[0]["league_id"] == 103
        assert league_rows[0]["league_abbr"] == "AL"

    def test_division_row_has_correct_fields(self, mlb_division):
        with patch(f"{MODULE}.MlbStatsApi") as MockApi, \
             patch(f"{MODULE}.get_run_logger"):
            api = MockApi.return_value
            api.list_leagues.return_value = []
            api.list_divisions.return_value = [mlb_division]
            _, division_rows = fetch_mlb_reference_data()

        expected_fields = {"division_id", "division_name", "division_abbr", "league_id", "raw"}
        assert set(division_rows[0].keys()) == expected_fields

    def test_division_row_values_match_model(self, mlb_division):
        with patch(f"{MODULE}.MlbStatsApi") as MockApi, \
             patch(f"{MODULE}.get_run_logger"):
            api = MockApi.return_value
            api.list_leagues.return_value = []
            api.list_divisions.return_value = [mlb_division]
            _, division_rows = fetch_mlb_reference_data()

        assert division_rows[0]["division_id"] == 200
        assert division_rows[0]["league_id"] == 103


class TestIngestMlbSeasonBigquery:
    def test_returns_counts_for_all_four_tables(self, settings, mlb_team, mlb_game_final, mlb_league, mlb_division):
        with patch(f"{MODULE}.get_settings", return_value=settings), \
             patch(f"{MODULE}.get_client", return_value=MagicMock()), \
             patch(f"{MODULE}.ensure_raw_dataset"), \
             patch(f"{MODULE}.ensure_mlb_tables"), \
             patch(f"{MODULE}.upsert_mlb_teams", return_value=30), \
             patch(f"{MODULE}.upsert_mlb_games", return_value=162), \
             patch(f"{MODULE}.upsert_mlb_leagues", return_value=2), \
             patch(f"{MODULE}.upsert_mlb_divisions", return_value=6), \
             patch(f"{MODULE}.MlbStatsApi") as MockApi:
            api = MockApi.return_value
            api.list_teams.return_value = [mlb_team]
            api.list_games.return_value = [mlb_game_final]
            api.list_leagues.return_value = [mlb_league]
            api.list_divisions.return_value = [mlb_division]
            from src.automations.ingest.mlb.seasons import ingest_mlb_season_bigquery
            teams, games, leagues, divisions = ingest_mlb_season_bigquery(season=2024)

        assert teams == 30
        assert games == 162
        assert leagues == 2
        assert divisions == 6


class TestIngestMlbMultiSeasonBigquery:
    def test_raises_value_error_when_start_after_end(self):
        from src.automations.ingest.mlb.seasons import ingest_mlb_multi_season_bigquery
        with pytest.raises(ValueError, match="start_year"):
            ingest_mlb_multi_season_bigquery(start_year=2024, end_year=2020)

    def test_processes_all_seasons_in_range(self, settings, mlb_team, mlb_game_final, mlb_league, mlb_division):
        with patch(f"{MODULE}.get_settings", return_value=settings), \
             patch(f"{MODULE}.get_client", return_value=MagicMock()), \
             patch(f"{MODULE}.ensure_raw_dataset"), \
             patch(f"{MODULE}.ensure_mlb_tables"), \
             patch(f"{MODULE}.upsert_mlb_teams", return_value=30), \
             patch(f"{MODULE}.upsert_mlb_games", return_value=100), \
             patch(f"{MODULE}.upsert_mlb_leagues", return_value=2), \
             patch(f"{MODULE}.upsert_mlb_divisions", return_value=6), \
             patch(f"{MODULE}.MlbStatsApi") as MockApi:
            api = MockApi.return_value
            api.list_teams.return_value = [mlb_team]
            api.list_games.return_value = [mlb_game_final]
            api.list_leagues.return_value = [mlb_league]
            api.list_divisions.return_value = [mlb_division]
            from src.automations.ingest.mlb.seasons import ingest_mlb_multi_season_bigquery
            result = ingest_mlb_multi_season_bigquery(start_year=2022, end_year=2024)

        assert result["seasons_processed"] == 3
        assert api.list_teams.call_count == 3  # once per season

    def test_returns_summary_dict_keys(self, settings, mlb_team, mlb_game_final, mlb_league, mlb_division):
        with patch(f"{MODULE}.get_settings", return_value=settings), \
             patch(f"{MODULE}.get_client", return_value=MagicMock()), \
             patch(f"{MODULE}.ensure_raw_dataset"), \
             patch(f"{MODULE}.ensure_mlb_tables"), \
             patch(f"{MODULE}.upsert_mlb_teams", return_value=30), \
             patch(f"{MODULE}.upsert_mlb_games", return_value=100), \
             patch(f"{MODULE}.upsert_mlb_leagues", return_value=2), \
             patch(f"{MODULE}.upsert_mlb_divisions", return_value=6), \
             patch(f"{MODULE}.MlbStatsApi") as MockApi:
            api = MockApi.return_value
            api.list_teams.return_value = [mlb_team]
            api.list_games.return_value = [mlb_game_final]
            api.list_leagues.return_value = [mlb_league]
            api.list_divisions.return_value = [mlb_division]
            from src.automations.ingest.mlb.seasons import ingest_mlb_multi_season_bigquery
            result = ingest_mlb_multi_season_bigquery(start_year=2024, end_year=2024)

        expected_keys = {"seasons_processed", "total_teams", "total_games", "total_leagues", "total_divisions", "seasons"}
        assert set(result.keys()) == expected_keys
