"""NBA API integration exceptions."""

from __future__ import annotations


class NbaApiError(Exception):
    """Base exception for NBA API errors."""
    pass


class NbaApiResponseError(NbaApiError):
    """Raised when the NBA API returns an unexpected response format."""
    pass


class NbaDataParseError(NbaApiError):
    """Raised when NBA API data cannot be parsed into expected format."""
    pass


class NbaSeasonNotFoundError(NbaApiError):
    """Raised when a requested NBA season is not found."""
    pass


class NbaGameNotFoundError(NbaApiError):
    """Raised when a requested NBA game is not found."""
    pass


class NbaPlayerNotFoundError(NbaApiError):
    """Raised when a requested NBA player is not found."""
    pass
