from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

import httpx


@dataclass(frozen=True, slots=True)
class HttpClient:
    base_url: str
    timeout_s: float = 30.0
    retries: int = 3
    backoff_s: float = 0.5

    def get_json(self, path: str, *, params: dict[str, Any] | None = None) -> dict[str, Any]:
        url = f"{self.base_url.rstrip('/')}/{path.lstrip('/')}"

        last_exc: Exception | None = None
        for attempt in range(self.retries + 1):
            try:
                with httpx.Client(timeout=self.timeout_s) as client:
                    resp = client.get(url, params=params)
                    resp.raise_for_status()
                    data = resp.json()
                    if not isinstance(data, dict):
                        raise TypeError(f"Expected JSON object from {url}, got {type(data)}")
                    return data
            except Exception as exc:
                last_exc = exc
                if attempt >= self.retries:
                    break
                time.sleep(self.backoff_s * (2**attempt))

        assert last_exc is not None
        raise last_exc
