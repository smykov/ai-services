from app.core.config import settings


def test_default_config():
    assert settings.max_upload_size_mb == 100
    assert settings.task_timeout == 60
    assert settings.task_result_ttl == 3600
    assert settings.api_keys == set()
    assert settings.mcp_bearer_token is None


def test_config_env_prefix(monkeypatch):
    monkeypatch.setattr(settings, "redis_url", "redis://custom:6379/0")
    assert settings.redis_url == "redis://custom:6379/0"
