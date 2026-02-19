from __future__ import annotations

import logging
from typing import Any

__all__ = ["get_logger", "get_run_logger"]


def get_logger(name: str | None = None) -> Any:
    """Return a standard logger.
    
    Args:
        name: Logger name (optional)
        
    Returns:
        A standard library logger instance
    """
    return logging.getLogger(name)


def get_run_logger() -> Any:
    """Return a logger for use in ingestion functions.
    
    Returns:
        A standard library logger instance
    """
    return get_logger("cityscape")