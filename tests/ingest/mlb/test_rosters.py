"""Unit tests for MLB roster ingestion."""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch

from src.automations.ingest.mlb.rosters import fetch_team_roster

MODULE = "src.automations.ingest.mlb.rosters"

ROSTER_FIELDS = {
    "team_id", "player_id", "season", "player_name",
    "position_code", "position_name", "position_abbr", "raw",
}


class TestFetchTeamRoster:
    def test_returns_correctly_shaped_rows(self, mlb_roster_entry):
        with patch(f"{MODULE}.MlbStatsApi") as MockApi, \
             patch(f"{MODULE}.get_run_logger"):
            MockApi.return_value.get_roster.return_value = [mlb_roster_entry]
            rows = fetch_team_roster(10, 2024)

        assert len(rows) == 1
        assert set(rows[0].keys()) == ROSTER_FIELDS

    def test_row_values_match_model(self, mlb_roster_entry):
        with patch(f"{MODULE}.MlbStatsApi") as MockApi, \
             patch(f"{MODULE}.get_run_logger"):
            MockApi.return_value.get_roster.return_value = [mlb_roster_entry]
            rows = fetch_team_roster(10, 2024)

        row = rows[0]
        assert row["team_id"] == 10
        assert row["player_id"] == 100
        assert row["season"] == 2024
        assert row["position_code"] == "CF"

    def test_returns_empty_list_on_exception(self):
        with patch(f"{MODULE}.MlbStatsApi") as MockApi, \
             patch(f"{MODULE}.get_run_logger"):
            MockApi.return_value.get_roster.side_effect = Exception("API error")
            rows = fetch_team_roster(10, 2024)

        assert rows == []

    def test_returns_empty_list_when_api_returns_empty(self):
        with patch(f"{MODULE}.MlbStatsApi") as MockApi, \
             patch(f"{MODULE}.get_run_logger"):
            MockApi.return_value.get_roster.return_value = []
            rows = fetch_team_roster(10, 2024)

        assert rows == []


class TestIngestMlbRostersBigquery:
    def test_fetches_all_teams_when_no_team_ids_given(self, settings, mlb_team, mlb_roster_entry):
        with patch(f"{MODULE}.get_settings", return_value=settings), \
             patch(f"{MODULE}.get_client", return_value=MagicMock()), \
             patch(f"{MODULE}.ensure_raw_dataset"), \
             patch(f"{MODULE}.ensure_mlb_tables"), \
             patch(f"{MODULE}.upsert_mlb_rosters", return_value=30) as mock_upsert, \
             patch(f"{MODULE}.MlbStatsApi") as MockApi:
            MockApi.return_value.list_teams.return_value = [mlb_team]
            MockApi.return_value.get_roster.return_value = [mlb_roster_entry]
            from src.automations.ingest.mlb.rosters import ingest_mlb_rosters_bigquery
            count = ingest_mlb_rosters_bigquery(season=2024)

        assert count == 30
        MockApi.return_value.get_roster.assert_called_once_with(
            team_id=mlb_team.team_id, season=2024
        )

    def test_uses_provided_team_ids(self, settings, mlb_roster_entry):
        with patch(f"{MODULE}.get_settings", return_value=settings), \
             patch(f"{MODULE}.get_client", return_value=MagicMock()), \
             patch(f"{MODULE}.ensure_raw_dataset"), \
             patch(f"{MODULE}.ensure_mlb_tables"), \
             patch(f"{MODULE}.upsert_mlb_rosters", return_value=5), \
             patch(f"{MODULE}.MlbStatsApi") as MockApi:
            MockApi.return_value.get_roster.return_value = [mlb_roster_entry]
            from src.automations.ingest.mlb.rosters import ingest_mlb_rosters_bigquery
            ingest_mlb_rosters_bigquery(season=2024, team_ids=[10, 20, 30])

        # list_teams should NOT be called when team_ids are explicitly provided
        MockApi.return_value.list_teams.assert_not_called()
        assert MockApi.return_value.get_roster.call_count == 3

    def test_parallel_fetches_all_teams(self, settings, mlb_roster_entry):
        team_ids = list(range(30))
        with patch(f"{MODULE}.get_settings", return_value=settings), \
             patch(f"{MODULE}.get_client", return_value=MagicMock()), \
             patch(f"{MODULE}.ensure_raw_dataset"), \
             patch(f"{MODULE}.ensure_mlb_tables"), \
             patch(f"{MODULE}.upsert_mlb_rosters", return_value=600), \
             patch(f"{MODULE}.MlbStatsApi") as MockApi:
            MockApi.return_value.get_roster.return_value = [mlb_roster_entry]
            from src.automations.ingest.mlb.rosters import ingest_mlb_rosters_bigquery
            ingest_mlb_rosters_bigquery(season=2024, team_ids=team_ids, parallel=True, max_workers=5)

        assert MockApi.return_value.get_roster.call_count == 30

    def test_sequential_fetches_all_teams(self, settings, mlb_roster_entry):
        team_ids = [10, 20, 30]
        with patch(f"{MODULE}.get_settings", return_value=settings), \
             patch(f"{MODULE}.get_client", return_value=MagicMock()), \
             patch(f"{MODULE}.ensure_raw_dataset"), \
             patch(f"{MODULE}.ensure_mlb_tables"), \
             patch(f"{MODULE}.upsert_mlb_rosters", return_value=9), \
             patch(f"{MODULE}.MlbStatsApi") as MockApi:
            MockApi.return_value.get_roster.return_value = [mlb_roster_entry]
            from src.automations.ingest.mlb.rosters import ingest_mlb_rosters_bigquery
            count = ingest_mlb_rosters_bigquery(season=2024, team_ids=team_ids, parallel=False)

        assert MockApi.return_value.get_roster.call_count == 3
        assert count == 9
