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

    def validate_auth(self) -> None:
        """Ensure at least one auth method is configured."""
        if not self.api_key and not self.email:
            raise OpenAlexConfigError(
                "Set OPENALEX_API_KEY (recommended) or OPENALEX_EMAIL in your environment. "
                "Get a free key at https://openalex.org/settings/api"
            )


@lru_cache(maxsize=1)
def get_settings() -> OpenAlexSettings:
    return OpenAlexSettings()
