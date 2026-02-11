"""MLB integration utility functions."""

from typing import Any


def parse_int_or_none(val: Any) -> int | None:
    """Parse value to int or None if invalid."""
    if val is None or val == "":
        return None
    try:
        return int(val)
    except (ValueError, TypeError):
        return None


def parse_str_or_none(val: Any) -> str | None:
    """Parse value to string or None if empty."""
    return str(val) if val and val != "" else None


def extract_team_id(side: dict[str, Any]) -> int | None:
    """Extract team ID from team side dictionary."""
    team = side.get("team") if isinstance(side.get("team"), dict) else None
    team_id_val = team.get("id") if isinstance(team, dict) else None
    return int(team_id_val) if team_id_val is not None else None


def extract_score(side: dict[str, Any]) -> int | None:
    """Extract score from team side dictionary."""
    score_val = side.get("score")
    return int(score_val) if score_val is not None else None
