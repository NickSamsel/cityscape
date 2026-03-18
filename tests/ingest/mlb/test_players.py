"""Unit tests for MLB player dimension ingestion."""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch

from src.automations.ingest.mlb.players import fetch_player_info

MODULE = "src.automations.ingest.mlb.players"

PLAYER_FIELDS = {
    "player_id", "full_name", "first_name", "last_name", "primary_number",
    "birth_date", "current_age", "birth_city", "birth_state_province",
    "birth_country", "height", "weight", "primary_position_code",
    "primary_position_name", "primary_position_abbr", "bat_side_code",
    "bat_side_description", "pitch_hand_code", "pitch_hand_description",
    "mlb_debut_date", "active", "raw",
}


class TestFetchPlayerInfo:
    def test_returns_correctly_shaped_row(self, mlb_player):
        with patch(f"{MODULE}.MlbStatsApi") as MockApi, \
             patch(f"{MODULE}.get_run_logger"):
            MockApi.return_value.get_player_info.return_value = mlb_player
            result = fetch_player_info(100)

        assert result is not None
        assert set(result.keys()) == PLAYER_FIELDS

    def test_row_values_match_model(self, mlb_player):
        with patch(f"{MODULE}.MlbStatsApi") as MockApi, \
             patch(f"{MODULE}.get_run_logger"):
            MockApi.return_value.get_player_info.return_value = mlb_player
            result = fetch_player_info(100)

        assert result["player_id"] == 100
        assert result["full_name"] == "John Doe"
        assert result["primary_position_code"] == "CF"
        assert result["active"] is True

    def test_returns_none_when_api_returns_none(self):
        with patch(f"{MODULE}.MlbStatsApi") as MockApi, \
             patch(f"{MODULE}.get_run_logger"):
            MockApi.return_value.get_player_info.return_value = None
            result = fetch_player_info(999)

        assert result is None

    def test_returns_none_on_exception(self):
        with patch(f"{MODULE}.MlbStatsApi") as MockApi, \
             patch(f"{MODULE}.get_run_logger"):
            MockApi.return_value.get_player_info.side_effect = Exception("API error")
            result = fetch_player_info(999)

        assert result is None


class TestIngestPlayersParallel:
    def test_processes_all_player_ids(self, settings, mlb_player):
        player_ids = [100, 200, 300, 400, 500]
        with patch(f"{MODULE}.get_settings", return_value=settings), \
             patch(f"{MODULE}.get_client", return_value=MagicMock()), \
             patch(f"{MODULE}.ensure_raw_dataset"), \
             patch(f"{MODULE}.ensure_mlb_tables"), \
             patch(f"{MODULE}.upsert_mlb_players", return_value=5), \
             patch(f"{MODULE}.fetch_player_info") as mock_fetch:
            player_row = {"player_id": 100, "full_name": "John Doe"}
            mock_fetch.return_value = player_row
            from src.automations.ingest.mlb.players import ingest_players_parallel
            count = ingest_players_parallel(player_ids=player_ids)

        assert mock_fetch.call_count == 5
        assert count == 5

    def test_returns_zero_when_all_fetches_fail(self, settings):
        with patch(f"{MODULE}.get_settings", return_value=settings), \
             patch(f"{MODULE}.get_client", return_value=MagicMock()), \
             patch(f"{MODULE}.ensure_raw_dataset"), \
             patch(f"{MODULE}.ensure_mlb_tables"), \
             patch(f"{MODULE}.upsert_mlb_players", return_value=0), \
             patch(f"{MODULE}.fetch_player_info", return_value=None):
            from src.automations.ingest.mlb.players import ingest_players_parallel
            count = ingest_players_parallel(player_ids=[100, 200])

        assert count == 0

    def test_batches_bq_writes_by_batch_size(self, settings, mlb_player):
        player_ids = list(range(250))
        player_row = {"player_id": 0, "full_name": "Test"}
        with patch(f"{MODULE}.get_settings", return_value=settings), \
             patch(f"{MODULE}.get_client", return_value=MagicMock()), \
             patch(f"{MODULE}.ensure_raw_dataset"), \
             patch(f"{MODULE}.ensure_mlb_tables"), \
             patch(f"{MODULE}.upsert_mlb_players", return_value=100) as mock_upsert, \
             patch(f"{MODULE}.fetch_player_info", return_value=player_row):
            from src.automations.ingest.mlb.players import ingest_players_parallel
            ingest_players_parallel(player_ids=player_ids, batch_size=100)

        # 250 players / 100 per batch = 3 upsert calls
        assert mock_upsert.call_count == 3


class TestIngestPlayersFromStats:
    def test_delegates_to_ingest_players_parallel(self, settings):
        player_ids = {100, 200, 300}
        with patch(f"{MODULE}.get_settings", return_value=settings), \
             patch(f"{MODULE}.get_unique_player_ids_from_bigquery", return_value=player_ids), \
             patch(f"{MODULE}.ingest_players_parallel", return_value=3) as mock_parallel:
            from src.automations.ingest.mlb.players import ingest_players_from_stats
            result = ingest_players_from_stats()

        mock_parallel.assert_called_once()
        call_kwargs = mock_parallel.call_args[1]
        assert set(call_kwargs["player_ids"]) == player_ids
        assert result == 3

    def test_returns_zero_when_no_player_ids_found(self, settings):
        with patch(f"{MODULE}.get_settings", return_value=settings), \
             patch(f"{MODULE}.get_unique_player_ids_from_bigquery", return_value=set()), \
             patch(f"{MODULE}.ingest_players_parallel") as mock_parallel:
            from src.automations.ingest.mlb.players import ingest_players_from_stats
            result = ingest_players_from_stats()

        mock_parallel.assert_not_called()
        assert result == 0


class TestIngestPlayersFromRosters:
    def test_delegates_to_ingest_players_parallel(self, settings):
        player_ids = {100, 200}
        with patch("src.automations.ingest.mlb.rosters.get_unique_player_ids_from_rosters",
                   return_value=player_ids), \
             patch(f"{MODULE}.ingest_players_parallel", return_value=2) as mock_parallel:
            from src.automations.ingest.mlb.players import ingest_players_from_rosters
            result = ingest_players_from_rosters(season=2024)

        mock_parallel.assert_called_once()
        assert result == 2

    def test_returns_zero_when_no_roster_player_ids(self):
        with patch("src.automations.ingest.mlb.rosters.get_unique_player_ids_from_rosters",
                   return_value=set()), \
             patch(f"{MODULE}.ingest_players_parallel") as mock_parallel:
            from src.automations.ingest.mlb.players import ingest_players_from_rosters
            result = ingest_players_from_rosters(season=2024)

        mock_parallel.assert_not_called()
        assert result == 0
