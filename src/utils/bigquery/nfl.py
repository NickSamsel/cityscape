from __future__ import annotations

"""NFL BigQuery table configs.

This is intentionally minimal scaffolding so adding a new sport is just:
- table configs here
- API client in src/integrations/nfl/
- ingest logic in src/automations/ingest/nfl/
"""

from google.cloud import bigquery

from .engine import UpsertTableConfig


# Stub examples — add/adjust schemas as NFL ingestion is implemented.
NFL_TEAMS = UpsertTableConfig(
    dataset="raw",
    table="nfl_teams",
    key_columns=("team_id", "season"),
    schema=(
        bigquery.SchemaField("team_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("season", "INT64", mode="REQUIRED"),
        bigquery.SchemaField("team_name", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("team_abbr", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("raw", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("loaded_at", "TIMESTAMP", mode="REQUIRED"),
    ),
)
