import pytest
from app.core.config import settings
from app.core.container import container
from app.main import app
from httpx import ASGITransport, AsyncClient


@pytest.fixture(autouse=True)
def reset_container():
    container._redis = None
    container._minio = None
    container._llm = None


@pytest.fixture
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as c:
        yield c
    await container.close_redis()
    await container.close_llm()
    container._redis = None
    container._minio = None
    container._llm = None


@pytest.fixture(autouse=True)
def patch_settings(monkeypatch):
    monkeypatch.setattr(settings, "api_keys", {"test-key-123"})
    monkeypatch.setattr(settings, "redis_url", "redis://localhost:6379/0")
    monkeypatch.setattr(settings, "minio_endpoint", "localhost:9000")
    monkeypatch.setattr(settings, "minio_access_key", "minioadmin")
    monkeypatch.setattr(settings, "minio_secret_key", "minioadmin")
    monkeypatch.setattr(settings, "minio_bucket", "ai-services-test")
    monkeypatch.setattr(settings, "task_timeout", 1)


@pytest.fixture(autouse=True)
def mock_llm(monkeypatch):
    async def mock_chat_completions(self, messages, **kwargs):
        return {
            "id": "chatcmpl-test",
            "object": "chat.completion",
            "choices": [{
                "index": 0,
                "message": {"role": "assistant", "content": '{"intent": "test"}'},
                "finish_reason": "stop",
            }],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
        }
    monkeypatch.setattr("app.core.llm.LLMService.chat_completions", mock_chat_completions)
