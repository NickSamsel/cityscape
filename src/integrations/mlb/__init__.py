"""MLB Stats API integration.

This module provides a typed interface to the free MLB Stats API.
"""

from __future__ import annotations

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
    # Client
    "MlbStatsApi",
    # Models
    "MlbTeam",
    "MlbGame",
    "MlbPlayerBattingStats",
    "MlbPlayerPitchingStats",
    # Exceptions
    "MlbApiError",
    "MlbApiResponseError",
    "MlbDataParseError",
    "MlbSeasonNotFoundError",
    "MlbGameNotFoundError",
]


__all__ = [
    "MlbGame",
    "MlbPlayerBattingStats",
    "MlbPlayerPitchingStats",
    "MlbStatsApi",
    "MlbTeam",
]
