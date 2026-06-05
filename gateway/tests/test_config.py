from app.core.config import Settings, settings


def test_default_config():
    s = Settings()
    assert s.max_upload_size_mb == 100
    assert s.task_timeout == 60
    assert s.task_result_ttl == 3600
    assert s.api_keys == set()
    assert s.mcp_bearer_token is None


def test_config_env_prefix(monkeypatch):
    monkeypatch.setattr(settings, "redis_url", "redis://custom:6379/0")
    assert settings.redis_url == "redis://custom:6379/0"
