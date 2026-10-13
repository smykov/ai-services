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


@pytest.mark.asyncio
async def test_talking_head_async_with_face(client):
    resp = await client.post(
        "/v1/video/talking-head",
        headers=HEADERS,
        files={"audio": ("a.wav", b"fake-audio", "audio/wav"), "face": ("f.mp4", b"fake-video", "video/mp4")},
        data={"restore_weight": "0.5"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "queued"
    assert "task_id" in data


@pytest.mark.asyncio
async def test_talking_head_reuses_face_id(client):
    resp = await client.post(
        "/v1/video/talking-head",
        headers=HEADERS,
        files={"audio": ("a.wav", b"fake-audio", "audio/wav")},
        data={"face_id": "0123456789abcdef0123456789abcdef"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "queued"


@pytest.mark.asyncio
async def test_talking_head_requires_face(client):
    resp = await client.post(
        "/v1/video/talking-head",
        headers=HEADERS,
        files={"audio": ("a.wav", b"fake-audio", "audio/wav")},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
@pytest.mark.parametrize("field,value", [("face_id", "../etc"), ("restore_weight", "1.5"), ("parsing_mode", "nose")])
async def test_talking_head_rejects_bad_options(client, field, value):
    data = {"face_id": "0123456789abcdef0123456789abcdef", field: value}
    resp = await client.post(
        "/v1/video/talking-head",
        headers=HEADERS,
        files={"audio": ("a.wav", b"fake-audio", "audio/wav")},
        data=data,
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_task_reports_progress_before_result(client):
    from app.core.container import container

    r = await container.redis
    await r.set("task:progress-test:progress", '{"stage": "rendering", "frames_done": 10}', ex=60)
    resp = await client.get("/v1/tasks/progress-test", headers=HEADERS)
    await r.delete("task:progress-test:progress")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "processing"
    assert data["progress"]["frames_done"] == 10


class _FakePubSub:
    async def subscribe(self, channel):
        pass

    async def unsubscribe(self, channel):
        pass

    async def aclose(self):
        pass


class _FakeRedis:
    def pubsub(self):
        return _FakePubSub()

    async def xadd(self, *args, **kwargs):
        pass


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("module", "url", "worker"),
    [("audio", "/v1/audio/transcriptions", "ASR"), ("ocr", "/v1/ocr", "OCR")],
)
async def test_sync_worker_error_returns_502(client, monkeypatch, module, url, worker):
    """A failed worker task must surface as 502, not as 200 with empty text."""
    import json

    from app.core.container import container

    async def fake_redis():
        return _FakeRedis()

    async def fake_upload(*args, **kwargs):
        return "obj"

    async def fake_wait(pubsub):
        return {"data": json.dumps({"error": "CUDA out of memory"})}

    monkeypatch.setattr(type(container), "redis", property(lambda self: fake_redis()))
    monkeypatch.setattr(f"app.routes.{module}.upload_file", fake_upload)
    monkeypatch.setattr(f"app.routes.{module}._wait_for_message", fake_wait)
    resp = await client.post(url, headers=HEADERS, files={"file": ("f.bin", b"data", "application/octet-stream")})
    assert resp.status_code == 502
    assert f"{worker} worker failed: CUDA out of memory" in resp.json()["detail"]
