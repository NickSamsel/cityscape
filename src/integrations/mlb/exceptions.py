"""MLB integration exceptions."""


class MlbApiError(Exception):
    """Base exception for MLB API errors."""
    pass


class MlbApiResponseError(MlbApiError):
    """Raised when MLB API returns unexpected response format."""
    pass


class MlbDataParseError(MlbApiError):
    """Raised when unable to parse MLB API data."""
    pass


class MlbSeasonNotFoundError(MlbApiError):
    """Raised when season data is not available."""
    pass


class MlbGameNotFoundError(MlbApiError):
    """Raised when game data is not available."""
    pass
