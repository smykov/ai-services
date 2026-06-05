import pytest


@pytest.mark.asyncio
async def test_health_no_auth(client):
    resp = await client.get("/health")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_audio_missing_api_key(client):
    resp = await client.post("/v1/audio/transcriptions")
    assert resp.status_code == 403


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
