from __future__ import annotations

from typing import Any, Iterable

import pandas as pd
from google.cloud import bigquery
from prefect import get_run_logger

from .engine import UpsertTableConfig, ensure_table, upsert_dataframe


def _ts(expr: str) -> str:
    return f"TIMESTAMP({expr})"


NBA_TEAMS = UpsertTableConfig(
    dataset="raw",
    table="nba_teams",
    key_columns=("team_id", "season"),
    schema=(
        bigquery.SchemaField("team_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("season", "INT64", mode="REQUIRED"),
        bigquery.SchemaField("team_name", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("team_abbr", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("conference", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("division", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("raw", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("loaded_at", "TIMESTAMP", mode="REQUIRED"),
    ),
    update_expressions={"loaded_at": _ts("S.`loaded_at`")},
    insert_expressions={"loaded_at": _ts("S.`loaded_at`")},
)


NBA_GAMES = UpsertTableConfig(
    dataset="raw",
    table="nba_games",
    key_columns=("game_id", "season"),
    schema=(
        bigquery.SchemaField("game_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("season", "INT64", mode="REQUIRED"),
        bigquery.SchemaField("game_date", "DATE", mode="NULLABLE"),
        bigquery.SchemaField("status", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("home_team_id", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("away_team_id", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("home_score", "INT64", mode="NULLABLE"),
        bigquery.SchemaField("away_score", "INT64", mode="NULLABLE"),
        bigquery.SchemaField("raw", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("loaded_at", "TIMESTAMP", mode="REQUIRED"),
    ),
    update_expressions={"loaded_at": _ts("S.`loaded_at`")},
    insert_expressions={"loaded_at": _ts("S.`loaded_at`")},
)


def ensure_nba_tables(client: bigquery.Client, project_id: str) -> None:
    for cfg in (NBA_TEAMS, NBA_GAMES):
        ensure_table(client=client, project_id=project_id, cfg=cfg)


def upsert_nba_teams(client: bigquery.Client, project_id: str, rows: Iterable[dict[str, Any]]) -> int:
    if not rows:
        return 0

    import json
    from datetime import datetime

    data: list[dict[str, Any]] = []
    for r in rows:
        data.append(
            {
                "team_id": str(r["team_id"]),
                "season": r["season"],
                "team_name": r["team_name"],
                "team_abbr": r.get("team_abbr"),
                "conference": r.get("conference"),
                "division": r.get("division"),
                "raw": json.dumps(r["raw"]),
                "loaded_at": datetime.utcnow(),
            }
        )

    df = pd.DataFrame(data)
    initial_count = len(df)
    df = df.drop_duplicates(subset=["team_id", "season"], keep="last")
    if initial_count > len(df):
        get_run_logger().warning(f"Removed {initial_count - len(df)} duplicate NBA team records")

    upsert_dataframe(client=client, project_id=project_id, cfg=NBA_TEAMS, df=df)
    return len(df)


def upsert_nba_games(client: bigquery.Client, project_id: str, rows: Iterable[dict[str, Any]]) -> int:
    if not rows:
        return 0

    import json
    from datetime import datetime

    data: list[dict[str, Any]] = []
    for r in rows:
        data.append(
            {
                "game_id": str(r["game_id"]),
                "season": r["season"],
                "game_date": r.get("game_date"),
                "status": r.get("status"),
                "home_team_id": str(r["home_team_id"]) if r.get("home_team_id") else None,
                "away_team_id": str(r["away_team_id"]) if r.get("away_team_id") else None,
                "home_score": r.get("home_score"),
                "away_score": r.get("away_score"),
                "raw": json.dumps(r["raw"]),
                "loaded_at": datetime.utcnow(),
            }
        )

    df = pd.DataFrame(data)
    initial_count = len(df)
    df = df.drop_duplicates(subset=["game_id", "season"], keep="last")
    if initial_count > len(df):
        get_run_logger().warning(f"Removed {initial_count - len(df)} duplicate NBA game records")

    upsert_dataframe(client=client, project_id=project_id, cfg=NBA_GAMES, df=df)
    return len(df)
