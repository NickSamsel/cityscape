"""Unit tests for MLB Statcast ingestion."""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch

from src.automations.ingest.mlb.statcast import _fetch_game_statcast_data

MODULE = "src.automations.ingest.mlb.statcast"

PITCH_FIELDS = {
    "play_id", "game_id", "at_bat_index", "pitcher_id", "batter_id",
    "catcher_id", "umpire_id", "pitch_number", "pitch_type",
    "pitch_type_description", "release_speed", "release_spin_rate",
    "release_extension", "release_pos_x", "release_pos_y", "release_pos_z",
    "zone", "plate_x", "plate_z", "strikes", "balls", "outs",
    "pitch_result", "pitch_result_description", "raw",
}
BATTED_BALL_FIELDS = {
    "play_id", "game_id", "at_bat_index", "batter_id", "pitcher_id",
    "launch_speed", "launch_angle", "launch_distance", "hit_location",
    "hit_trajectory", "hit_result", "sprint_speed", "is_barrel", "is_hard_hit", "raw",
}


class TestFetchGameStatcastData:
    def test_returns_correctly_shaped_pitch_rows(self, mlb_statcast_pitch):
        api = MagicMock()
        api.get_game_statcast_data.return_value = ([mlb_statcast_pitch], [])
        pitch_rows, _ = _fetch_game_statcast_data(123456, api)

        assert len(pitch_rows) == 1
        assert set(pitch_rows[0].keys()) == PITCH_FIELDS

    def test_pitch_row_values_match_model(self, mlb_statcast_pitch):
        api = MagicMock()
        api.get_game_statcast_data.return_value = ([mlb_statcast_pitch], [])
        pitch_rows, _ = _fetch_game_statcast_data(123456, api)

        row = pitch_rows[0]
        assert row["play_id"] == "abc-123"
        assert row["game_id"] == 123456
        assert row["pitch_type"] == "FF"
        assert row["release_speed"] == 95.2

    def test_returns_correctly_shaped_batted_ball_rows(self, mlb_statcast_batted_ball):
        api = MagicMock()
        api.get_game_statcast_data.return_value = ([], [mlb_statcast_batted_ball])
        _, batted_ball_rows = _fetch_game_statcast_data(123456, api)

        assert len(batted_ball_rows) == 1
        assert set(batted_ball_rows[0].keys()) == BATTED_BALL_FIELDS

    def test_batted_ball_row_values_match_model(self, mlb_statcast_batted_ball):
        api = MagicMock()
        api.get_game_statcast_data.return_value = ([], [mlb_statcast_batted_ball])
        _, batted_ball_rows = _fetch_game_statcast_data(123456, api)

        row = batted_ball_rows[0]
        assert row["play_id"] == "abc-124"
        assert row["launch_speed"] == 105.3
        assert row["is_barrel"] is True

    def test_returns_empty_tuples_on_exception(self):
        api = MagicMock()
        api.get_game_statcast_data.side_effect = Exception("API error")
        pitch_rows, batted_ball_rows = _fetch_game_statcast_data(123456, api)

        assert pitch_rows == []
        assert batted_ball_rows == []


class TestIngestMlbStatcastDataBigquery:
    def test_returns_zero_for_pre_2015_season(self, settings):
        with patch(f"{MODULE}.get_settings", return_value=settings), \
             patch(f"{MODULE}.get_run_logger"):
            from src.automations.ingest.mlb.statcast import ingest_mlb_statcast_data_bigquery
            pitches, batted_balls = ingest_mlb_statcast_data_bigquery(season=2014)

        assert pitches == 0
        assert batted_balls == 0

    def test_skips_api_call_entirely_for_pre_2015(self, settings):
        with patch(f"{MODULE}.get_settings", return_value=settings), \
             patch(f"{MODULE}.get_run_logger"), \
             patch(f"{MODULE}.MlbStatsApi") as MockApi:
            from src.automations.ingest.mlb.statcast import ingest_mlb_statcast_data_bigquery
            ingest_mlb_statcast_data_bigquery(season=2010)

        MockApi.assert_not_called()

    def test_filters_out_scheduled_games(self, settings, mlb_game_final, mlb_game_scheduled):
        with patch(f"{MODULE}.get_settings", return_value=settings), \
             patch(f"{MODULE}.get_run_logger"), \
             patch(f"{MODULE}.get_client", return_value=MagicMock()), \
             patch(f"{MODULE}.ensure_raw_dataset"), \
             patch(f"{MODULE}.ensure_mlb_tables"), \
             patch("src.utils.bigquery.upsert_mlb_statcast_pitches", return_value=0), \
             patch("src.utils.bigquery.upsert_mlb_statcast_batted_balls", return_value=0), \
             patch(f"{MODULE}.fetch_mlb_statcast_data", return_value=([], [])) as mock_fetch, \
             patch(f"{MODULE}.MlbStatsApi") as MockApi:
            MockApi.return_value.list_games.return_value = [mlb_game_final, mlb_game_scheduled]
            from src.automations.ingest.mlb.statcast import ingest_mlb_statcast_data_bigquery
            ingest_mlb_statcast_data_bigquery(season=2024)

        # Only the Final game should be passed through
        call_kwargs = mock_fetch.call_args[1]
        assert mlb_game_final.game_id in call_kwargs["game_ids"]
        assert mlb_game_scheduled.game_id not in call_kwargs["game_ids"]

    def test_does_not_instantiate_api_when_game_ids_provided(self, settings):
        with patch(f"{MODULE}.get_settings", return_value=settings), \
             patch(f"{MODULE}.get_run_logger"), \
             patch(f"{MODULE}.get_client", return_value=MagicMock()), \
             patch(f"{MODULE}.ensure_raw_dataset"), \
             patch(f"{MODULE}.ensure_mlb_tables"), \
             patch("src.utils.bigquery.upsert_mlb_statcast_pitches", return_value=0), \
             patch("src.utils.bigquery.upsert_mlb_statcast_batted_balls", return_value=0), \
             patch(f"{MODULE}.fetch_mlb_statcast_data", return_value=([], [])), \
             patch(f"{MODULE}.MlbStatsApi") as MockApi:
            from src.automations.ingest.mlb.statcast import ingest_mlb_statcast_data_bigquery
            ingest_mlb_statcast_data_bigquery(game_ids=[123456, 789012])

        MockApi.assert_not_called()

    def test_raises_if_neither_season_nor_game_ids(self, settings):
        with patch(f"{MODULE}.get_settings", return_value=settings), \
             patch(f"{MODULE}.get_run_logger"):
            from src.automations.ingest.mlb.statcast import ingest_mlb_statcast_data_bigquery
            with pytest.raises(ValueError):
                ingest_mlb_statcast_data_bigquery()

    def test_returns_loaded_counts(self, settings, mlb_game_final, mlb_statcast_pitch, mlb_statcast_batted_ball):
        with patch(f"{MODULE}.get_settings", return_value=settings), \
             patch(f"{MODULE}.get_run_logger"), \
             patch(f"{MODULE}.get_client", return_value=MagicMock()), \
             patch(f"{MODULE}.ensure_raw_dataset"), \
             patch(f"{MODULE}.ensure_mlb_tables"), \
             patch("src.utils.bigquery.upsert_mlb_statcast_pitches", return_value=10), \
             patch("src.utils.bigquery.upsert_mlb_statcast_batted_balls", return_value=4), \
             patch(f"{MODULE}.fetch_mlb_statcast_data", return_value=([{}] * 10, [{}] * 4)):
            from src.automations.ingest.mlb.statcast import ingest_mlb_statcast_data_bigquery
            pitches, batted_balls = ingest_mlb_statcast_data_bigquery(game_ids=[123456])

        assert pitches == 10
        assert batted_balls == 4
