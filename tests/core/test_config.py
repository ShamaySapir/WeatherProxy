from app.core import Settings, get_settings


def test_settings_default_values():
    """Test that default values are set correctly."""
    settings = Settings()
    assert settings.environment == "development"
    assert settings.log_level == "INFO"
    assert settings.redis_url == "redis://localhost:6379"
    assert settings.cache_ttl_seconds == 3600
    assert settings.upstream_timeout_seconds == 10.0


def test_settings_env_override(monkeypatch):
    """Test that environment variables override defaults."""
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("REDIS_URL", "redis://redis-server:6379")
    monkeypatch.setenv("CACHE_TTL_SECONDS", "7200")
    monkeypatch.setenv("UPSTREAM_TIMEOUT_SECONDS", "30.0")

    settings = Settings()
    assert settings.environment == "production"
    assert settings.log_level == "DEBUG"
    assert settings.redis_url == "redis://redis-server:6379"
    assert settings.cache_ttl_seconds == 7200
    assert settings.upstream_timeout_seconds == 30.0


def test_get_settings_singleton():
    """Test that get_settings returns the same instance."""
    settings1 = get_settings()
    settings2 = get_settings()
    assert settings1 is settings2
