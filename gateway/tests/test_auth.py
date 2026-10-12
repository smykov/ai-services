import pytest


@pytest.mark.asyncio
async def test_health_no_auth(client):
    resp = await client.get("/health")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_audio_missing_api_key(client):
    # Auth runs before body validation, so a request without a key is rejected first.
    resp = await client.post("/v1/audio/transcriptions")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_audio_wrong_api_key(client):
    headers = {"X-API-Key": "wrong-key"}
    resp = await client.post("/v1/audio/transcriptions", headers=headers)
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_audio_valid_api_key_no_file(client):
    headers = {"X-API-Key": "test-key-123"}
    resp = await client.post("/v1/audio/transcriptions", headers=headers)
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_chat_missing_api_key(client, monkeypatch):
    from app.core.config import settings
    monkeypatch.setattr(settings, "api_keys", set())
    resp = await client.post(
        "/v1/chat/completions",
        json={"messages": [{"role": "user", "content": "Hi"}]},
    )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_chat_no_keys_wrong_key(client, monkeypatch):
    from app.core.config import settings
    monkeypatch.setattr(settings, "api_keys", set())
    resp = await client.post(
        "/v1/chat/completions",
        headers={"X-API-Key": "any-key"},
        json={"messages": [{"role": "user", "content": "Hi"}]},
    )
    assert resp.status_code == 200
