from __future__ import annotations

import logging
from typing import Any

__all__ = ["get_logger", "get_run_logger"]


def get_logger(name: str | None = None) -> Any:
    """Return a logger.

    Uses Prefect's logger when Prefect is available, otherwise falls back to
    the standard library `logging`.
    """

    # Prefect's `get_logger()` returns a standard logger configured with Prefect
    # logging settings, but does NOT send logs to the Prefect API.
    try:
        from prefect.logging import get_logger as prefect_get_logger

        return prefect_get_logger(name)
    except Exception:
        return logging.getLogger(name)


def get_run_logger() -> Any:
    """Return a Prefect run logger when inside a flow/task.

    Prefect v3 best practice:
    - Use `prefect.logging.get_run_logger()` inside flows/tasks to emit logs
      associated with the current run (visible in the Prefect UI).
    - Outside Prefect run context, fall back to a normal logger.
    """

    try:
        from prefect.logging import get_run_logger as prefect_get_run_logger

        return prefect_get_run_logger()
    except Exception:
        # Likely not running inside a flow/task (or Prefect not installed).
        return get_logger("cityscape")