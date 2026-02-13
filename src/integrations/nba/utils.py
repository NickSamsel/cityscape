"""NBA API integration utilities."""

from __future__ import annotations

from typing import Any


def parse_int_or_none(value: Any) -> int | None:
    """Parse value to int, returning None if invalid."""
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        return None


def parse_float_or_none(value: Any) -> float | None:
    """Parse value to float, returning None if invalid."""
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def parse_str_or_none(value: Any) -> str | None:
    """Parse value to string, returning None if empty or invalid."""
    if value is None:
        return None
    s = str(value).strip()
    return s if s else None


def parse_bool_or_none(value: Any) -> bool | None:
    """Parse value to bool, returning None if invalid."""
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        lower = value.lower()
        if lower in ("true", "1", "yes", "y"):
            return True
        if lower in ("false", "0", "no", "n"):
            return False
    return None
