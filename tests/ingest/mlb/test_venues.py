"""Unit tests for MLB venue ingestion."""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch

MODULE = "src.automations.ingest.mlb.venues"

VENUE_FIELDS = {
    "venue_id", "season", "venue_name", "active", "city", "state",
    "state_abbrev", "country", "latitude", "longitude", "capacity",
    "turf_type", "roof_type", "left_line", "right_line", "center",
    "left", "right", "left_center", "right_center", "raw",
}


class TestIngestMlbVenuesBigquery:
    def test_venue_row_has_correct_fields(self, settings, mlb_venue):
        with patch(f"{MODULE}.get_settings", return_value=settings), \
             patch(f"{MODULE}.get_client", return_value=MagicMock()), \
             patch(f"{MODULE}.ensure_raw_dataset"), \
             patch(f"{MODULE}.ensure_mlb_tables"), \
             patch(f"{MODULE}.upsert_mlb_venues", return_value=1) as mock_upsert, \
             patch(f"{MODULE}.MlbStatsApi") as MockApi:
            MockApi.return_value.list_venues.return_value = [mlb_venue]
            from src.automations.ingest.mlb.venues import ingest_mlb_venues_bigquery
            ingest_mlb_venues_bigquery(season=2024, venue_ids=[1])

        rows = mock_upsert.call_args[0][2]
        assert set(rows[0].keys()) == VENUE_FIELDS

    def test_venue_row_values_match_model(self, settings, mlb_venue):
        with patch(f"{MODULE}.get_settings", return_value=settings), \
             patch(f"{MODULE}.get_client", return_value=MagicMock()), \
             patch(f"{MODULE}.ensure_raw_dataset"), \
             patch(f"{MODULE}.ensure_mlb_tables"), \
             patch(f"{MODULE}.upsert_mlb_venues", return_value=1) as mock_upsert, \
             patch(f"{MODULE}.MlbStatsApi") as MockApi:
            MockApi.return_value.list_venues.return_value = [mlb_venue]
            from src.automations.ingest.mlb.venues import ingest_mlb_venues_bigquery
            ingest_mlb_venues_bigquery(season=2024, venue_ids=[1])

        row = mock_upsert.call_args[0][2][0]
        assert row["venue_id"] == 1
        assert row["venue_name"] == "Test Stadium"
        assert row["capacity"] == 42000
        assert row["turf_type"] == "Grass"

    def test_derives_venue_ids_from_schedule_when_none_given(
        self, settings, mlb_venue, mlb_schedule_entry_scheduled
    ):
        with patch(f"{MODULE}.get_settings", return_value=settings), \
             patch(f"{MODULE}.get_client", return_value=MagicMock()), \
             patch(f"{MODULE}.ensure_raw_dataset"), \
             patch(f"{MODULE}.ensure_mlb_tables"), \
             patch(f"{MODULE}.upsert_mlb_venues", return_value=1), \
             patch(f"{MODULE}.MlbStatsApi") as MockApi:
            MockApi.return_value.list_schedule.return_value = (
                [mlb_schedule_entry_scheduled], [], [],
            )
            MockApi.return_value.list_venues.return_value = [mlb_venue]
            from src.automations.ingest.mlb.venues import ingest_mlb_venues_bigquery
            ingest_mlb_venues_bigquery(season=2024)

        # venue_id 1 was on the schedule entry; list_venues should be called with it
        MockApi.return_value.list_venues.assert_called_once()
        call_kwargs = MockApi.return_value.list_venues.call_args[1]
        assert 1 in call_kwargs["venue_ids"]

    def test_returns_zero_when_no_venue_ids(self, settings):
        with patch(f"{MODULE}.get_settings", return_value=settings), \
             patch(f"{MODULE}.get_client", return_value=MagicMock()), \
             patch(f"{MODULE}.ensure_raw_dataset"), \
             patch(f"{MODULE}.ensure_mlb_tables"), \
             patch(f"{MODULE}.MlbStatsApi") as MockApi:
            MockApi.return_value.list_schedule.return_value = ([], [], [])
            from src.automations.ingest.mlb.venues import ingest_mlb_venues_bigquery
            result = ingest_mlb_venues_bigquery(season=2024)

        assert result == 0
        MockApi.return_value.list_venues.assert_not_called()

    def test_deduplicates_venue_ids_from_explicit_list(self, settings, mlb_venue):
        with patch(f"{MODULE}.get_settings", return_value=settings), \
             patch(f"{MODULE}.get_client", return_value=MagicMock()), \
             patch(f"{MODULE}.ensure_raw_dataset"), \
             patch(f"{MODULE}.ensure_mlb_tables"), \
             patch(f"{MODULE}.upsert_mlb_venues", return_value=1), \
             patch(f"{MODULE}.MlbStatsApi") as MockApi:
            MockApi.return_value.list_venues.return_value = [mlb_venue]
            from src.automations.ingest.mlb.venues import ingest_mlb_venues_bigquery
            ingest_mlb_venues_bigquery(season=2024, venue_ids=[1, 1, 1, 2, 2])

        call_kwargs = MockApi.return_value.list_venues.call_args[1]
        assert len(call_kwargs["venue_ids"]) == 2  # deduplicated
