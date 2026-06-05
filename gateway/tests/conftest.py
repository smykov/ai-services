import pytest
from httpx import ASGITransport, AsyncClient

from app.core.config import settings
from app.core.container import container
from app.main import app


@pytest.fixture
async def client():
    container._redis = None
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as c:
        yield c
    await container.close_redis()
    container._redis = None


@pytest.fixture(autouse=True)
def patch_settings(monkeypatch):
    monkeypatch.setattr(settings, "api_keys", {"test-key-123"})
    monkeypatch.setattr(settings, "redis_url", "redis://localhost:6379/0")
    monkeypatch.setattr(settings, "minio_endpoint", "localhost:9000")
    monkeypatch.setattr(settings, "minio_access_key", "minioadmin")
    monkeypatch.setattr(settings, "minio_secret_key", "minioadmin")
    monkeypatch.setattr(settings, "minio_bucket", "ai-services-test")
    monkeypatch.setattr(settings, "task_timeout", 1)
