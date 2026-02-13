"""NBA Stats API integration.

This module provides a typed interface to the NBA Stats API.
"""

from __future__ import annotations

from .client import NbaStatsApi
from .exceptions import (
    NbaApiError,
    NbaApiResponseError,
    NbaDataParseError,
    NbaGameNotFoundError,
    NbaPlayerNotFoundError,
    NbaSeasonNotFoundError,
)
from .models import (
    NbaConference,
    NbaDivision,
    NbaGame,
    NbaPlayer,
    NbaPlayerGameStats,
    NbaStandingsRecord,
    NbaTeam,
)

__all__ = [
    # Client
    "NbaStatsApi",
    # Models
    "NbaConference",
    "NbaDivision",
    "NbaTeam",
    "NbaGame",
    "NbaPlayer",
    "NbaPlayerGameStats",
    "NbaStandingsRecord",
    # Exceptions
    "NbaApiError",
    "NbaApiResponseError",
    "NbaDataParseError",
    "NbaSeasonNotFoundError",
    "NbaGameNotFoundError",
    "NbaPlayerNotFoundError",
]
