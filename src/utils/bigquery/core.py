from __future__ import annotations

import json
from dataclasses import dataclass

from google.cloud import bigquery


@dataclass(frozen=True, slots=True)
class BigQueryConfig:
    project_id: str | None
    location: str = "US"
    credentials_path: str | None = None
    service_account_key: str | None = None


def get_client(cfg: BigQueryConfig) -> bigquery.Client:
    credentials = None

    if cfg.service_account_key:
        from google.oauth2 import service_account

        info = json.loads(cfg.service_account_key)
        credentials = service_account.Credentials.from_service_account_info(info)
    elif cfg.credentials_path:
        from google.oauth2 import service_account

        credentials = service_account.Credentials.from_service_account_file(cfg.credentials_path)

    return bigquery.Client(
        project=cfg.project_id,
        credentials=credentials,
        location=cfg.location,
    )


def ensure_raw_dataset(client: bigquery.Client, project_id: str) -> None:
    dataset_id = f"{project_id}.raw"
    dataset = bigquery.Dataset(dataset_id)
    client.create_dataset(dataset, exists_ok=True)
