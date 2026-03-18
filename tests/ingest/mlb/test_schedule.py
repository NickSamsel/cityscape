"""Unit tests for MLB schedule ingestion."""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch

MODULE = "src.automations.ingest.mlb.schedule"

SCHEDULE_FIELDS = {
    "game_id", "season", "game_date", "game_datetime", "game_type", "status",
    "day_night", "venue_id", "venue_name", "home_team_id", "away_team_id",
    "home_probable_pitcher_id", "home_probable_pitcher_name",
    "away_probable_pitcher_id", "away_probable_pitcher_name",
    "scheduled_innings", "series_description", "raw",
}
BROADCAST_FIELDS = {
    "game_id", "broadcast_name", "broadcast_type", "call_sign",
    "is_national", "home_away", "language", "raw",
}
LINEUP_FIELDS = {
    "game_id", "player_id", "team_side", "full_name",
    "position_abbreviation", "batting_order", "raw",
}


class TestIngestMlbScheduleBigquery:
    def _make_api(self, MockApi, scheduled_entry, final_entry, broadcast, lineup_entry):
        MockApi.return_value.list_schedule.return_value = (
            [scheduled_entry, final_entry],
            [broadcast],
            [lineup_entry],
        )

    def test_filters_schedule_to_scheduled_games_only(
        self, settings, mlb_schedule_entry_scheduled, mlb_schedule_entry_final
    ):
        with patch(f"{MODULE}.get_settings", return_value=settings), \
             patch(f"{MODULE}.get_client", return_value=MagicMock()), \
             patch(f"{MODULE}.ensure_raw_dataset"), \
             patch(f"{MODULE}.ensure_mlb_tables"), \
             patch(f"{MODULE}.upsert_mlb_schedule", return_value=1) as mock_upsert_sched, \
             patch(f"{MODULE}.upsert_mlb_game_broadcasts", return_value=0), \
             patch(f"{MODULE}.upsert_mlb_game_lineups", return_value=0), \
             patch(f"{MODULE}.MlbStatsApi") as MockApi:
            MockApi.return_value.list_schedule.return_value = (
                [mlb_schedule_entry_scheduled, mlb_schedule_entry_final],
                [], [],
            )
            from src.automations.ingest.mlb.schedule import ingest_mlb_schedule_bigquery
            ingest_mlb_schedule_bigquery(season=2024)

        rows = mock_upsert_sched.call_args[0][2]
        assert len(rows) == 1
        assert rows[0]["game_id"] == mlb_schedule_entry_scheduled.game_id

    def test_broadcasts_filtered_to_scheduled_game_ids(
        self, settings, mlb_schedule_entry_scheduled, mlb_schedule_entry_final, mlb_broadcast
    ):
        # Broadcast belongs to scheduled game (123456); final game (654321) has no broadcast
        broadcast_for_final = MagicMock()
        broadcast_for_final.game_id = mlb_schedule_entry_final.game_id  # 654321 — not scheduled

        with patch(f"{MODULE}.get_settings", return_value=settings), \
             patch(f"{MODULE}.get_client", return_value=MagicMock()), \
             patch(f"{MODULE}.ensure_raw_dataset"), \
             patch(f"{MODULE}.ensure_mlb_tables"), \
             patch(f"{MODULE}.upsert_mlb_schedule", return_value=1), \
             patch(f"{MODULE}.upsert_mlb_game_broadcasts", return_value=1) as mock_upsert_bc, \
             patch(f"{MODULE}.upsert_mlb_game_lineups", return_value=0), \
             patch(f"{MODULE}.MlbStatsApi") as MockApi:
            MockApi.return_value.list_schedule.return_value = (
                [mlb_schedule_entry_scheduled, mlb_schedule_entry_final],
                [mlb_broadcast, broadcast_for_final],
                [],
            )
            from src.automations.ingest.mlb.schedule import ingest_mlb_schedule_bigquery
            ingest_mlb_schedule_bigquery(season=2024)

        rows = mock_upsert_bc.call_args[0][2]
        assert all(r["game_id"] == mlb_schedule_entry_scheduled.game_id for r in rows)
        assert len(rows) == 1

    def test_schedule_row_has_correct_fields(self, settings, mlb_schedule_entry_scheduled):
        with patch(f"{MODULE}.get_settings", return_value=settings), \
             patch(f"{MODULE}.get_client", return_value=MagicMock()), \
             patch(f"{MODULE}.ensure_raw_dataset"), \
             patch(f"{MODULE}.ensure_mlb_tables"), \
             patch(f"{MODULE}.upsert_mlb_schedule", return_value=1) as mock_upsert_sched, \
             patch(f"{MODULE}.upsert_mlb_game_broadcasts", return_value=0), \
             patch(f"{MODULE}.upsert_mlb_game_lineups", return_value=0), \
             patch(f"{MODULE}.MlbStatsApi") as MockApi:
            MockApi.return_value.list_schedule.return_value = (
                [mlb_schedule_entry_scheduled], [], [],
            )
            from src.automations.ingest.mlb.schedule import ingest_mlb_schedule_bigquery
            ingest_mlb_schedule_bigquery(season=2024)

        rows = mock_upsert_sched.call_args[0][2]
        assert set(rows[0].keys()) == SCHEDULE_FIELDS

    def test_broadcast_row_has_correct_fields(self, settings, mlb_schedule_entry_scheduled, mlb_broadcast):
        with patch(f"{MODULE}.get_settings", return_value=settings), \
             patch(f"{MODULE}.get_client", return_value=MagicMock()), \
             patch(f"{MODULE}.ensure_raw_dataset"), \
             patch(f"{MODULE}.ensure_mlb_tables"), \
             patch(f"{MODULE}.upsert_mlb_schedule", return_value=1), \
             patch(f"{MODULE}.upsert_mlb_game_broadcasts", return_value=1) as mock_upsert_bc, \
             patch(f"{MODULE}.upsert_mlb_game_lineups", return_value=0), \
             patch(f"{MODULE}.MlbStatsApi") as MockApi:
            MockApi.return_value.list_schedule.return_value = (
                [mlb_schedule_entry_scheduled], [mlb_broadcast], [],
            )
            from src.automations.ingest.mlb.schedule import ingest_mlb_schedule_bigquery
            ingest_mlb_schedule_bigquery(season=2024)

        rows = mock_upsert_bc.call_args[0][2]
        assert set(rows[0].keys()) == BROADCAST_FIELDS

    def test_lineup_row_has_correct_fields(
        self, settings, mlb_schedule_entry_scheduled, mlb_lineup_entry
    ):
        with patch(f"{MODULE}.get_settings", return_value=settings), \
             patch(f"{MODULE}.get_client", return_value=MagicMock()), \
             patch(f"{MODULE}.ensure_raw_dataset"), \
             patch(f"{MODULE}.ensure_mlb_tables"), \
             patch(f"{MODULE}.upsert_mlb_schedule", return_value=1), \
             patch(f"{MODULE}.upsert_mlb_game_broadcasts", return_value=0), \
             patch(f"{MODULE}.upsert_mlb_game_lineups", return_value=1) as mock_upsert_lu, \
             patch(f"{MODULE}.MlbStatsApi") as MockApi:
            MockApi.return_value.list_schedule.return_value = (
                [mlb_schedule_entry_scheduled], [], [mlb_lineup_entry],
            )
            from src.automations.ingest.mlb.schedule import ingest_mlb_schedule_bigquery
            ingest_mlb_schedule_bigquery(season=2024)

        rows = mock_upsert_lu.call_args[0][2]
        assert set(rows[0].keys()) == LINEUP_FIELDS

    def test_returns_triple_of_counts(self, settings, mlb_schedule_entry_scheduled):
        with patch(f"{MODULE}.get_settings", return_value=settings), \
             patch(f"{MODULE}.get_client", return_value=MagicMock()), \
             patch(f"{MODULE}.ensure_raw_dataset"), \
             patch(f"{MODULE}.ensure_mlb_tables"), \
             patch(f"{MODULE}.upsert_mlb_schedule", return_value=5), \
             patch(f"{MODULE}.upsert_mlb_game_broadcasts", return_value=3), \
             patch(f"{MODULE}.upsert_mlb_game_lineups", return_value=18), \
             patch(f"{MODULE}.MlbStatsApi") as MockApi:
            MockApi.return_value.list_schedule.return_value = (
                [mlb_schedule_entry_scheduled], [], [],
            )
            from src.automations.ingest.mlb.schedule import ingest_mlb_schedule_bigquery
            schedule, broadcasts, lineups = ingest_mlb_schedule_bigquery(season=2024)

        assert schedule == 5
        assert broadcasts == 3
        assert lineups == 18
