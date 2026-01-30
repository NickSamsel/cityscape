from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Settings:
    prefect_api_url: str | None = None
    postgres_host: str | None = None
    postgres_port: int | None = None
    postgres_user: str | None = None
    postgres_password: str | None = None
    postgres_dbname: str | None = None


def get_settings() -> Settings:
    return Settings(
        prefect_api_url=os.getenv("PREFECT_API_URL"),
        postgres_host=os.getenv("DBT_HOST") or os.getenv("POSTGRES_HOST") or os.getenv("PGHOST"),
        postgres_port=(
            int(os.getenv("DBT_PORT"))
            if os.getenv("DBT_PORT")
            else (int(os.getenv("POSTGRES_PORT")) if os.getenv("POSTGRES_PORT") else None)
        ),
        postgres_user=os.getenv("DBT_USER") or os.getenv("POSTGRES_USER") or os.getenv("PGUSER"),
        postgres_password=os.getenv("DBT_PASSWORD") or os.getenv("POSTGRES_PASSWORD") or os.getenv("PGPASSWORD"),
        postgres_dbname=os.getenv("DBT_DBNAME") or os.getenv("POSTGRES_DB") or os.getenv("PGDATABASE"),
    )
