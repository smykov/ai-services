import pytest

HEADERS = {"X-API-Key": "test-key-123"}


@pytest.mark.asyncio
async def test_transcribe_async(client):
    resp = await client.post(
        "/v1/audio/transcriptions",
        headers=HEADERS,
        files={"file": ("test.wav", b"fake-audio-data", "audio/wav")},
        data={"language": "ru", "async": "true"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "queued"
    assert "task_id" in data


@pytest.mark.asyncio
async def test_ocr_async(client):
    resp = await client.post(
        "/v1/ocr",
        headers=HEADERS,
        files={"file": ("test.png", b"fake-image-data", "image/png")},
        data={"languages": "en,ru", "async": "true"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "queued"
    assert "task_id" in data


@pytest.mark.asyncio
async def test_synthesize_speech_async(client):
    resp = await client.post(
        "/v1/audio/speech",
        headers=HEADERS,
        data={"text": "Hello world", "voice": "default", "model": "xtts-v2", "async": "true"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "queued"
    assert "task_id" in data


@pytest.mark.asyncio
async def test_task_not_found(client):
    resp = await client.get("/v1/tasks/nonexistent-id", headers=HEADERS)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_task_download_not_found(client):
    resp = await client.get("/v1/tasks/nonexistent-id/download", headers=HEADERS)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_file_too_large(client, monkeypatch):
    from app.core.config import settings
    monkeypatch.setattr(settings, "max_upload_size_mb", 0)

    resp = await client.post(
        "/v1/ocr",
        headers=HEADERS,
        files={"file": ("test.png", b"x" * 1024, "image/png")},
        data={"async": "true"},
    )
    assert resp.status_code == 413
