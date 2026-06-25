"""Error hierarchy for the OpenAlex MCP server."""


class OpenAlexError(Exception):
    """Base exception for all OpenAlex MCP errors."""


class OpenAlexConfigError(OpenAlexError):
    """Raised when required configuration (API key, etc.) is missing or invalid."""


class OpenAlexAPIError(OpenAlexError):
    """Raised when the OpenAlex API returns an error response."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class OpenAlexAuthError(OpenAlexAPIError):
    """Raised on 401 / 403 — invalid or missing API key."""


class OpenAlexNotFoundError(OpenAlexAPIError):
    """Raised on 404 — entity not found."""


class OpenAlexRateLimitError(OpenAlexAPIError):
    """Raised on 429 — rate limit exhausted after all retries."""
