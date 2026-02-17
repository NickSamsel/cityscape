from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping, Sequence

import pandas as pd
from google.cloud import bigquery


# Sentinel used to mean "use cfg.schema for staging loads".
INFER_SCHEMA: object = object()


def _quote_col(col: str) -> str:
    # BigQuery allows backticked column identifiers, including reserved words.
    return f"`{col}`"


def build_merge_sql(
    *,
    target_table_id: str,
    staging_table_id: str,
    on_clause: str,
    update_columns: Sequence[str],
    insert_columns: Sequence[str],
    update_expressions: Mapping[str, str] | None = None,
    insert_expressions: Mapping[str, str] | None = None,
    target_alias: str = "T",
    staging_alias: str = "S",
) -> str:
    if not update_columns:
        raise ValueError("update_columns cannot be empty")

    update_expressions = update_expressions or {}
    insert_expressions = insert_expressions or {}

    update_set = ",\n        ".join(
        f"{_quote_col(c)} = {update_expressions.get(c, f'{staging_alias}.{_quote_col(c)}')}"
        for c in update_columns
    )
    insert_cols = ", ".join(_quote_col(c) for c in insert_columns)
    insert_vals = ", ".join(
        insert_expressions.get(c, f"{staging_alias}.{_quote_col(c)}") for c in insert_columns
    )

    return (
        f"""
MERGE `{target_table_id}` {target_alias}
USING `{staging_table_id}` {staging_alias}
ON {on_clause}
WHEN MATCHED THEN
  UPDATE SET
        {update_set}
WHEN NOT MATCHED THEN
  INSERT ({insert_cols})
  VALUES ({insert_vals})
"""
    ).strip()


@dataclass(frozen=True, slots=True)
class UpsertTableConfig:
    dataset: str
    table: str
    schema: Sequence[bigquery.SchemaField] | None = None
    staging_schema: Sequence[bigquery.SchemaField] | None | object = field(
        default_factory=lambda: INFER_SCHEMA
    )
    key_columns: Sequence[str] = ()
    on_clause: str | None = None
    update_expressions: Mapping[str, str] = field(default_factory=dict)
    insert_expressions: Mapping[str, str] = field(default_factory=dict)

    def table_id(self, project_id: str) -> str:
        return f"{project_id}.{self.dataset}.{self.table}"

    def staging_table_id(self, project_id: str) -> str:
        return f"{self.table_id(project_id)}_temp"

    def resolved_on_clause(self) -> str:
        if self.on_clause:
            return self.on_clause
        if not self.key_columns:
            raise ValueError("Either on_clause or key_columns must be provided")
        parts = [f"T.{_quote_col(c)} = S.{_quote_col(c)}" for c in self.key_columns]
        return " AND ".join(parts)


def upsert_dataframe(
    *,
    client: bigquery.Client,
    project_id: str,
    cfg: UpsertTableConfig,
    df: pd.DataFrame,
    cleanup_staging: bool = True,
) -> None:
    if df.empty:
        return

    target_table_id = cfg.table_id(project_id)
    staging_table_id = cfg.staging_table_id(project_id)

    job_config = bigquery.LoadJobConfig(write_disposition="WRITE_TRUNCATE")

    staging_schema = cfg.staging_schema
    if staging_schema is INFER_SCHEMA:
        staging_schema = cfg.schema

    if staging_schema is not None:
        job_config.schema = list(staging_schema)

    load_job = client.load_table_from_dataframe(df, staging_table_id, job_config=job_config)
    load_job.result()

    insert_columns: list[str] = list(df.columns)
    update_columns = [c for c in insert_columns if c not in set(cfg.key_columns)]

    merge_sql = build_merge_sql(
        target_table_id=target_table_id,
        staging_table_id=staging_table_id,
        on_clause=cfg.resolved_on_clause(),
        update_columns=update_columns,
        insert_columns=insert_columns,
        update_expressions=cfg.update_expressions,
        insert_expressions=cfg.insert_expressions,
    )

    query_job = client.query(merge_sql)
    query_job.result()

    if cleanup_staging:
        client.delete_table(staging_table_id, not_found_ok=True)


def ensure_table(*, client: bigquery.Client, project_id: str, cfg: UpsertTableConfig) -> None:
    if cfg.schema is None:
        return
    table_id = cfg.table_id(project_id)
    client.create_table(bigquery.Table(table_id, schema=list(cfg.schema)), exists_ok=True)
