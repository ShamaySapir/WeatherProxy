from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    environment: str = "development"
    log_level: str = "INFO"
    redis_url: str = "redis://localhost:6379"
    cache_ttl_seconds: int = 3600
    upstream_timeout_seconds: float = 10.0

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False)


_settings: Settings | None = None


def get_settings() -> Settings:
    """Get or create settings instance."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
