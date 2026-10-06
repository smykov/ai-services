from app.core.config import Settings, settings


def test_default_config():
    s = Settings()
    assert s.max_upload_size_mb == 100
    assert s.task_timeout == 120
    assert s.task_result_ttl == 3600
    assert s.api_keys == set()
    assert s.mcp_bearer_token is None


def test_llm_config_defaults():
    s = Settings()
    assert s.llm_base_url == "http://ollama:11434/v1"
    assert s.llm_api_key == ""
    assert s.llm_model == "qwen2.5:7b"
    assert "intent, entities, and classification" in s.default_nlp_system_prompt


def test_llm_config_env_override(monkeypatch):
    monkeypatch.setattr(settings, "llm_base_url", "https://api.openai.com/v1")
    monkeypatch.setattr(settings, "llm_api_key", "sk-test")
    monkeypatch.setattr(settings, "llm_model", "gpt-4o")
    assert settings.llm_base_url == "https://api.openai.com/v1"
    assert settings.llm_api_key == "sk-test"
    assert settings.llm_model == "gpt-4o"


def test_config_env_prefix(monkeypatch):
    monkeypatch.setattr(settings, "redis_url", "redis://custom:6379/0")
    assert settings.redis_url == "redis://custom:6379/0"
