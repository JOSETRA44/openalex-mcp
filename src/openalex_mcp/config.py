"""Configuration via environment variables using pydantic-settings."""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from .exceptions import OpenAlexConfigError


class OpenAlexSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
        populate_by_name=True,
    )

    api_key: str | None = Field(default=None, alias="OPENALEX_API_KEY")
    email: str | None = Field(default=None, alias="OPENALEX_EMAIL")
    cache_ttl: int = Field(default=300, alias="OPENALEX_CACHE_TTL", ge=0)
    max_retries: int = Field(default=3, alias="OPENALEX_MAX_RETRIES", ge=0, le=10)
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    def auth_warning(self) -> str | None:
        """Advise on rate limits, if nothing identifies us to OpenAlex.

        OpenAlex serves anonymous requests, so refusing to start without a key
        would be inventing a requirement the API does not have — and it made
        this server unusable exactly as our own README describes installing it.
        Supplying an email joins the *polite pool*, which raises the rate limit;
        that is worth recommending, not worth blocking on.
        """
        if not self.api_key and not self.email:
            return (
                "No OPENALEX_EMAIL or OPENALEX_API_KEY set — running in the anonymous "
                "pool, which has a lower rate limit. Set OPENALEX_EMAIL to your address "
                "to join the polite pool: https://docs.openalex.org/how-to-use-the-api/"
                "api-overview#authentication"
            )
        return None

    def validate_auth(self) -> None:
        """Kept for callers that predate :meth:`auth_warning`. Never raises now."""
        return None


@lru_cache(maxsize=1)
def get_settings() -> OpenAlexSettings:
    return OpenAlexSettings()
