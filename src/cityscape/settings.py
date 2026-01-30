from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Settings:
    prefect_api_url: str | None = None


def get_settings() -> Settings:
    return Settings(
        prefect_api_url=os.getenv("PREFECT_API_URL"),
    )
