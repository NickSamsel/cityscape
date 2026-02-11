"""MLB Stats API client - DEPRECATED.

This module is deprecated. Import from:
- cityscape.integrations.mlb.models for data models
- cityscape.integrations.mlb.client for MlbStatsApi
- cityscape.integrations.mlb.exceptions for exceptions
- cityscape.integrations.mlb for all public interfaces

This file remains for backward compatibility only.
"""

from __future__ import annotations

# Re-export from new modules for backward compatibility
from .client import MlbStatsApi
from .exceptions import (
    MlbApiError,
    MlbApiResponseError,
    MlbDataParseError,
    MlbGameNotFoundError,
    MlbSeasonNotFoundError,
)
from .models import MlbGame, MlbPlayerBattingStats, MlbPlayerPitchingStats, MlbTeam

__all__ = [
    "MlbStatsApi",
    "MlbTeam",
    "MlbGame",
    "MlbPlayerBattingStats",
    "MlbPlayerPitchingStats",
    "MlbApiError",
    "MlbApiResponseError",
    "MlbDataParseError",
    "MlbSeasonNotFoundError",
    "MlbGameNotFoundError",
]
