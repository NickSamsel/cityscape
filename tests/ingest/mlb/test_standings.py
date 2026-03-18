"""Unit tests for MLB standings ingestion."""
from __future__ import annotations

import pytest
from datetime import date
from unittest.mock import MagicMock, patch

from src.automations.ingest.mlb.standings import (
    _standings_to_rows,
    _fetch_standings_for_date,
)

MODULE = "src.automations.ingest.mlb.standings"

STANDINGS_FIELDS = {
    "team_id", "season", "standings_date", "league_id", "division_id",
    "division_rank", "wins", "losses", "win_pct", "games_back",
    "wildcard_games_back", "streak", "last_ten_record", "runs_scored",
    "runs_allowed", "run_differential", "home_wins", "home_losses",
    "away_wins", "away_losses", "raw",
}


class TestStandingsToRows:
    def test_correct_field_set(self, mlb_standings_record):
        snapshot_date = date(2024, 7, 1)
        rows = _standings_to_rows([mlb_standings_record], snapshot_date)

        assert len(rows) == 1
        assert set(rows[0].keys()) == STANDINGS_FIELDS

    def test_uses_passed_standings_date_not_record_date(self, mlb_standings_record):
        snapshot_date = date(2024, 7, 1)
        rows = _standings_to_rows([mlb_standings_record], snapshot_date)

        # The row's standings_date should be the argument, not mlb_standings_record.standings_date (None)
        assert rows[0]["standings_date"] == snapshot_date

    def test_row_values_match_record(self, mlb_standings_record):
        snapshot_date = date(2024, 7, 1)
        rows = _standings_to_rows([mlb_standings_record], snapshot_date)

        row = rows[0]
        assert row["team_id"] == 10
        assert row["wins"] == 90
        assert row["losses"] == 72
        assert row["win_pct"] == 0.556
        assert row["division_rank"] == 1

    def test_multiple_records(self, mlb_standings_record):
        snapshot_date = date(2024, 7, 1)
        rows = _standings_to_rows([mlb_standings_record] * 30, snapshot_date)

        assert len(rows) == 30
        assert all(r["standings_date"] == snapshot_date for r in rows)

    def test_empty_input_returns_empty_list(self):
        rows = _standings_to_rows([], date(2024, 7, 1))
        assert rows == []


class TestFetchStandingsForDate:
    def test_returns_date_and_rows_on_success(self, mlb_standings_record):
        target_date = date(2024, 7, 1)
        with patch(f"{MODULE}.MlbStatsApi") as MockApi:
            MockApi.return_value.list_standings.return_value = [mlb_standings_record]
            result_date, rows = _fetch_standings_for_date(2024, target_date)

        assert result_date == target_date
        assert rows is not None
        assert len(rows) == 1

    def test_returns_none_rows_when_api_returns_empty(self):
        target_date = date(2024, 7, 1)
        with patch(f"{MODULE}.MlbStatsApi") as MockApi:
            MockApi.return_value.list_standings.return_value = []
            result_date, rows = _fetch_standings_for_date(2024, target_date)

        assert result_date == target_date
        assert rows is None

    def test_returns_none_rows_after_all_retries_fail(self):
        target_date = date(2024, 7, 1)
        with patch(f"{MODULE}.MlbStatsApi") as MockApi, \
             patch(f"{MODULE}.time") as mock_time:
            MockApi.return_value.list_standings.side_effect = Exception("API error")
            result_date, rows = _fetch_standings_for_date(2024, target_date, retries=2)

        assert result_date == target_date
        assert rows is None
        assert mock_time.sleep.call_count == 1  # retries - 1

    def test_retries_before_giving_up(self):
        target_date = date(2024, 7, 1)
        with patch(f"{MODULE}.MlbStatsApi") as MockApi, \
             patch(f"{MODULE}.time"):
            MockApi.return_value.list_standings.side_effect = Exception("transient")
            _fetch_standings_for_date(2024, target_date, retries=3)

        assert MockApi.return_value.list_standings.call_count == 3


class TestIngestStandingsSnapshot:
    def test_uses_season_end_date_when_no_date_given(self, settings, mlb_standings_record):
        season_end = date(2024, 10, 1)
        with patch(f"{MODULE}.get_settings", return_value=settings), \
             patch(f"{MODULE}.get_client", return_value=MagicMock()), \
             patch(f"{MODULE}.ensure_raw_dataset"), \
             patch(f"{MODULE}.ensure_mlb_tables"), \
             patch(f"{MODULE}.upsert_mlb_standings", return_value=30) as mock_upsert, \
             patch(f"{MODULE}.MlbStatsApi") as MockApi:
            api = MockApi.return_value
            api.list_standings.return_value = [mlb_standings_record]
            api.get_regular_season_bounds.return_value = (date(2024, 3, 28), season_end)
            from src.automations.ingest.mlb.standings import ingest_standings_snapshot
            ingest_standings_snapshot(season=2024)

        # The rows passed to upsert should use the season end date
        rows = mock_upsert.call_args[0][2]
        assert all(r["standings_date"] == season_end for r in rows)

    def test_uses_provided_date(self, settings, mlb_standings_record):
        target_date = date(2024, 7, 15)
        with patch(f"{MODULE}.get_settings", return_value=settings), \
             patch(f"{MODULE}.get_client", return_value=MagicMock()), \
             patch(f"{MODULE}.ensure_raw_dataset"), \
             patch(f"{MODULE}.ensure_mlb_tables"), \
             patch(f"{MODULE}.upsert_mlb_standings", return_value=30) as mock_upsert, \
             patch(f"{MODULE}.MlbStatsApi") as MockApi:
            MockApi.return_value.list_standings.return_value = [mlb_standings_record]
            from src.automations.ingest.mlb.standings import ingest_standings_snapshot
            ingest_standings_snapshot(season=2024, standings_date=target_date)

        rows = mock_upsert.call_args[0][2]
        assert all(r["standings_date"] == target_date for r in rows)

    def test_returns_zero_when_api_returns_no_records(self, settings):
        with patch(f"{MODULE}.get_settings", return_value=settings), \
             patch(f"{MODULE}.get_client", return_value=MagicMock()), \
             patch(f"{MODULE}.ensure_raw_dataset"), \
             patch(f"{MODULE}.ensure_mlb_tables"), \
             patch(f"{MODULE}.MlbStatsApi") as MockApi:
            MockApi.return_value.list_standings.return_value = []
            from src.automations.ingest.mlb.standings import ingest_standings_snapshot
            result = ingest_standings_snapshot(season=2024, standings_date=date(2024, 7, 1))

        assert result == 0


class TestIngestStandingsHistoricalParallel:
    def test_fetches_snapshots_and_upserts(self, settings, mlb_standings_record):
        season_start = date(2024, 3, 28)
        season_end = date(2024, 4, 14)  # Small range → 2 snapshots at 7-day interval

        with patch(f"{MODULE}.get_settings", return_value=settings), \
             patch(f"{MODULE}.get_client", return_value=MagicMock()), \
             patch(f"{MODULE}.ensure_raw_dataset"), \
             patch(f"{MODULE}.ensure_mlb_tables"), \
             patch(f"{MODULE}.upsert_mlb_standings", return_value=30) as mock_upsert, \
             patch(f"{MODULE}.MlbStatsApi") as MockApi, \
             patch(f"{MODULE}._fetch_standings_for_date") as mock_fetch:
            MockApi.return_value.get_regular_season_bounds.return_value = (season_start, season_end)
            mock_fetch.return_value = (date(2024, 4, 4), [{"team_id": 10}])
            from src.automations.ingest.mlb.standings import ingest_standings_historical_parallel
            ingest_standings_historical_parallel(season=2024)

        assert mock_fetch.call_count >= 1
        assert mock_upsert.called

    def test_skips_dates_with_no_data(self, settings):
        season_start = date(2024, 3, 28)
        season_end = date(2024, 4, 7)

        with patch(f"{MODULE}.get_settings", return_value=settings), \
             patch(f"{MODULE}.get_client", return_value=MagicMock()), \
             patch(f"{MODULE}.ensure_raw_dataset"), \
             patch(f"{MODULE}.ensure_mlb_tables"), \
             patch(f"{MODULE}.upsert_mlb_standings", return_value=0) as mock_upsert, \
             patch(f"{MODULE}.MlbStatsApi") as MockApi, \
             patch(f"{MODULE}._fetch_standings_for_date") as mock_fetch:
            MockApi.return_value.get_regular_season_bounds.return_value = (season_start, season_end)
            mock_fetch.return_value = (date(2024, 4, 4), None)  # No data
            from src.automations.ingest.mlb.standings import ingest_standings_historical_parallel
            result = ingest_standings_historical_parallel(season=2024)

        # No rows → upsert should not be called
        mock_upsert.assert_not_called()
        assert result == 0
