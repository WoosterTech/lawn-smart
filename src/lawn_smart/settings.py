"""
Centralized application settings.

Uses pydantic-settings to load environment variables and .env file.
Controls things like DEBUG mode and logging defaults.

Additional settings can be added as needed.
"""

import logging

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config: SettingsConfigDict = SettingsConfigDict(  # pyright: ignore[reportIncompatibleVariableOverride]
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        env_prefix="LAWN_SMART_",
        extra="ignore",
    )

    debug: bool = False
    log_level: str | None = None

    @property
    def default_log_level(self) -> int:
        if self.debug:
            return logging.DEBUG
        return logging.INFO


settings = Settings()
