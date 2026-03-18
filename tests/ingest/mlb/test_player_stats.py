"""Unit tests for MLB player stats ingestion."""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch

from src.automations.ingest.mlb.player_stats import fetch_game_player_stats

MODULE = "src.automations.ingest.mlb.player_stats"

BATTING_FIELDS = {
    "game_id", "player_id", "team_id", "player_name", "batting_order",
    "position", "at_bats", "runs", "hits", "doubles", "triples",
    "home_runs", "rbi", "stolen_bases", "walks", "strikeouts",
    "left_on_base", "avg", "obp", "slg", "ops", "raw",
}
PITCHING_FIELDS = {
    "game_id", "player_id", "team_id", "player_name", "innings_pitched",
    "hits", "runs", "earned_runs", "walks", "strikeouts",
    "home_runs", "pitches", "strikes", "era", "raw",
}


class TestFetchGamePlayerStats:
    def test_returns_correctly_shaped_batting_rows(self, batting_stat):
        with patch(f"{MODULE}.MlbStatsApi") as MockApi, \
             patch(f"{MODULE}.get_run_logger"):
            MockApi.return_value.get_player_game_stats.return_value = ([batting_stat], [])
            batting_rows, _ = fetch_game_player_stats(123456)

        assert len(batting_rows) == 1
        assert set(batting_rows[0].keys()) == BATTING_FIELDS

    def test_batting_row_values_match_model(self, batting_stat):
        with patch(f"{MODULE}.MlbStatsApi") as MockApi, \
             patch(f"{MODULE}.get_run_logger"):
            MockApi.return_value.get_player_game_stats.return_value = ([batting_stat], [])
            batting_rows, _ = fetch_game_player_stats(123456)

        row = batting_rows[0]
        assert row["game_id"] == 123456
        assert row["player_id"] == 100
        assert row["hits"] == 2
        assert row["home_runs"] == 1
        assert row["avg"] == ".300"

    def test_returns_correctly_shaped_pitching_rows(self, pitching_stat):
        with patch(f"{MODULE}.MlbStatsApi") as MockApi, \
             patch(f"{MODULE}.get_run_logger"):
            MockApi.return_value.get_player_game_stats.return_value = ([], [pitching_stat])
            _, pitching_rows = fetch_game_player_stats(123456)

        assert len(pitching_rows) == 1
        assert set(pitching_rows[0].keys()) == PITCHING_FIELDS

    def test_pitching_row_values_match_model(self, pitching_stat):
        with patch(f"{MODULE}.MlbStatsApi") as MockApi, \
             patch(f"{MODULE}.get_run_logger"):
            MockApi.return_value.get_player_game_stats.return_value = ([], [pitching_stat])
            _, pitching_rows = fetch_game_player_stats(123456)

        row = pitching_rows[0]
        assert row["player_id"] == 200
        assert row["strikeouts"] == 8
        assert row["innings_pitched"] == "6.0"

    def test_returns_empty_lists_on_api_exception(self):
        with patch(f"{MODULE}.MlbStatsApi") as MockApi, \
             patch(f"{MODULE}.get_run_logger"):
            MockApi.return_value.get_player_game_stats.side_effect = Exception("API error")
            batting_rows, pitching_rows = fetch_game_player_stats(123456)

        assert batting_rows == []
        assert pitching_rows == []

    def test_retries_and_succeeds_on_second_attempt(self, batting_stat, pitching_stat):
        with patch(f"{MODULE}.MlbStatsApi") as MockApi, \
             patch(f"{MODULE}.get_run_logger"), \
             patch(f"{MODULE}.time") as mock_time:
            api = MockApi.return_value
            api.get_player_game_stats.side_effect = [
                Exception("transient error"),
                ([batting_stat], [pitching_stat]),
            ]
            batting_rows, pitching_rows = fetch_game_player_stats(123456, retries=3)

        assert len(batting_rows) == 1
        assert len(pitching_rows) == 1
        assert api.get_player_game_stats.call_count == 2
        mock_time.sleep.assert_called_once()

    def test_returns_empty_after_exhausting_all_retries(self):
        with patch(f"{MODULE}.MlbStatsApi") as MockApi, \
             patch(f"{MODULE}.get_run_logger"), \
             patch(f"{MODULE}.time"):
            MockApi.return_value.get_player_game_stats.side_effect = Exception("persistent error")
            batting_rows, pitching_rows = fetch_game_player_stats(123456, retries=2)

        assert batting_rows == []
        assert pitching_rows == []


class TestIngestPlayerStatsParallel:
    def _patch_all(self, settings, extra_patches=None):
        patches = {
            f"{MODULE}.get_settings": settings,
            f"{MODULE}.get_client": MagicMock(return_value=MagicMock()),
            f"{MODULE}.ensure_raw_dataset": MagicMock(),
            f"{MODULE}.ensure_mlb_tables": MagicMock(),
            f"{MODULE}.upsert_mlb_player_batting_stats": MagicMock(return_value=0),
            f"{MODULE}.upsert_mlb_player_pitching_stats": MagicMock(return_value=0),
        }
        if extra_patches:
            patches.update(extra_patches)
        return patches

    def test_bq_setup_happens_before_list_games(self, settings, mlb_game_final, batting_stat):
        call_order = []

        def track(name):
            return lambda *a, **kw: call_order.append(name)

        with patch(f"{MODULE}.get_settings", return_value=settings), \
             patch(f"{MODULE}.get_client", return_value=MagicMock()), \
             patch(f"{MODULE}.ensure_raw_dataset", side_effect=track("ensure_raw")), \
             patch(f"{MODULE}.ensure_mlb_tables", side_effect=track("ensure_tables")), \
             patch(f"{MODULE}.upsert_mlb_player_batting_stats", return_value=0), \
             patch(f"{MODULE}.upsert_mlb_player_pitching_stats", return_value=0), \
             patch(f"{MODULE}.MlbStatsApi") as MockApi:
            api = MockApi.return_value
            api.list_games.side_effect = lambda *a, **kw: call_order.append("list_games") or [mlb_game_final]
            api.get_player_game_stats.return_value = ([batting_stat], [])
            from src.automations.ingest.mlb.player_stats import ingest_player_stats_parallel
            ingest_player_stats_parallel(season=2024)

        assert call_order.index("ensure_raw") < call_order.index("list_games")

    def test_returns_batting_and_pitching_counts(self, settings, mlb_game_final, batting_stat, pitching_stat):
        with patch(f"{MODULE}.get_settings", return_value=settings), \
             patch(f"{MODULE}.get_client", return_value=MagicMock()), \
             patch(f"{MODULE}.ensure_raw_dataset"), \
             patch(f"{MODULE}.ensure_mlb_tables"), \
             patch(f"{MODULE}.upsert_mlb_player_batting_stats", return_value=7), \
             patch(f"{MODULE}.upsert_mlb_player_pitching_stats", return_value=3), \
             patch(f"{MODULE}.MlbStatsApi") as MockApi:
            MockApi.return_value.list_games.return_value = [mlb_game_final]
            MockApi.return_value.get_player_game_stats.return_value = ([batting_stat], [pitching_stat])
            from src.automations.ingest.mlb.player_stats import ingest_player_stats_parallel
            batting_count, pitching_count = ingest_player_stats_parallel(season=2024)

        assert batting_count == 7
        assert pitching_count == 3

    def test_processes_all_game_ids(self, settings, batting_stat):
        games = [MagicMock(game_id=i) for i in range(5)]
        with patch(f"{MODULE}.get_settings", return_value=settings), \
             patch(f"{MODULE}.get_client", return_value=MagicMock()), \
             patch(f"{MODULE}.ensure_raw_dataset"), \
             patch(f"{MODULE}.ensure_mlb_tables"), \
             patch(f"{MODULE}.upsert_mlb_player_batting_stats", return_value=5), \
             patch(f"{MODULE}.upsert_mlb_player_pitching_stats", return_value=0), \
             patch(f"{MODULE}.MlbStatsApi") as MockApi:
            MockApi.return_value.list_games.return_value = games
            MockApi.return_value.get_player_game_stats.return_value = ([batting_stat], [])
            from src.automations.ingest.mlb.player_stats import ingest_player_stats_parallel
            ingest_player_stats_parallel(season=2024)

        assert MockApi.return_value.get_player_game_stats.call_count == 5


class TestIngestPlayerStatsSequential:
    def test_delegates_to_fetch_helper(self, settings, mlb_game_final):
        """Sequential ingest should call fetch_game_player_stats (with its retry logic)."""
        with patch(f"{MODULE}.get_settings", return_value=settings), \
             patch(f"{MODULE}.get_client", return_value=MagicMock()), \
             patch(f"{MODULE}.ensure_raw_dataset"), \
             patch(f"{MODULE}.ensure_mlb_tables"), \
             patch(f"{MODULE}.upsert_mlb_player_batting_stats", return_value=0), \
             patch(f"{MODULE}.upsert_mlb_player_pitching_stats", return_value=0), \
             patch(f"{MODULE}.MlbStatsApi") as MockApi, \
             patch(f"{MODULE}.fetch_game_player_stats", return_value=([], [])) as mock_fetch:
            MockApi.return_value.list_games.return_value = [mlb_game_final]
            from src.automations.ingest.mlb.player_stats import ingest_player_stats_sequential
            ingest_player_stats_sequential(season=2024)

        mock_fetch.assert_called_once_with(mlb_game_final.game_id)

    def test_bq_setup_happens_before_list_games(self, settings, mlb_game_final):
        call_order = []
        with patch(f"{MODULE}.get_settings", return_value=settings), \
             patch(f"{MODULE}.get_client", return_value=MagicMock()), \
             patch(f"{MODULE}.ensure_raw_dataset", side_effect=lambda *a: call_order.append("ensure_raw")), \
             patch(f"{MODULE}.ensure_mlb_tables", side_effect=lambda *a: call_order.append("ensure_tables")), \
             patch(f"{MODULE}.upsert_mlb_player_batting_stats", return_value=0), \
             patch(f"{MODULE}.upsert_mlb_player_pitching_stats", return_value=0), \
             patch(f"{MODULE}.MlbStatsApi") as MockApi, \
             patch(f"{MODULE}.fetch_game_player_stats", return_value=([], [])):
            api = MockApi.return_value
            api.list_games.side_effect = lambda *a, **kw: call_order.append("list_games") or [mlb_game_final]
            from src.automations.ingest.mlb.player_stats import ingest_player_stats_sequential
            ingest_player_stats_sequential(season=2024)

        assert call_order.index("ensure_raw") < call_order.index("list_games")
