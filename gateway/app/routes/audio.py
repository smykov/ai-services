import asyncio
import json
import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from pydantic import BaseModel

from ..core.auth import verify_api_key
from ..core.config import settings
from ..core.container import container
from ..core.minio import get_presigned_url, upload_file
from ..core.redis import push_and_wait, push_task, _wait_for_message

router = APIRouter(dependencies=[Depends(verify_api_key)], tags=["audio"])


class TranscriptionResponse(BaseModel):
    text: str
    task_id: str | None = None


class SpeechResponse(BaseModel):
    audio_url: str
    task_id: str | None = None


@router.post("/audio/transcriptions")
async def transcribe_audio(
    request: Request,
    file: UploadFile = File(None),
    language: str = Form(None),
    model: str = Form(None),
    async_: bool = Form(False, alias="async"),
):
    content_type = request.headers.get("content-type", "").lower()
    lang = "auto"
    model_val = "turbo"
    async_flag = False

    if "application/json" in content_type:
        body = await request.json()
        lang = body.get("language", lang)
        model_val = body.get("model", model_val)
        async_flag = bool(body.get("async", False))
        if not file and "file_url" in body:
            pass
    else:
        if file is None:
            raise HTTPException(status_code=422, detail="File field required")
        lang = language or lang
        model_val = model or model_val
        async_flag = async_

    if file:
        contents = await file.read()
        if len(contents) > settings.max_upload_size_mb * 1024 * 1024:
            raise HTTPException(status_code=413, detail="File too large")
        object_name = await upload_file(contents, prefix="audio/")
    else:
        raise HTTPException(status_code=400, detail="No file provided")

    payload = {
        "object_name": object_name,
        "language": lang,
        "model": model_val,
    }

    r = await container.redis
    task_id = str(uuid.uuid4())
    payload["task_id"] = task_id
    channel = f"result:{task_id}"
    pubsub = r.pubsub()
    await pubsub.subscribe(channel)

    try:
        await r.xadd("asr:queue", payload, maxlen=1000)

        if not async_flag:
            try:
                result = await asyncio.wait_for(
                    _wait_for_message(pubsub),
                    timeout=settings.task_timeout,
                )
                if result:
                    data = json.loads(result["data"])
                    return TranscriptionResponse(text=data.get("text", ""), task_id=task_id)
            except asyncio.TimeoutError:
                pass

        return {"task_id": task_id, "status": "queued" if async_flag else "processing"}

    finally:
        await pubsub.unsubscribe(channel)
        await pubsub.aclose()


@router.post("/audio/speech")
async def synthesize_speech(request: Request):
    content_type = request.headers.get("content-type", "").lower()

    if "application/json" in content_type:
        body = await request.json()
    else:
        form = await request.form()
        body = {k: v for k, v in form.items()}

    text = body.get("input", body.get("text"))
    voice = body.get("voice", "default")
    model_value = body.get("model", "xtts-v2")
    async_flag = str(body.get("async", body.get("async_", "false"))).lower() in ("true", "1")

    if not text:
        raise HTTPException(status_code=422, detail="Field 'input' or 'text' is required")

    payload = {"text": text, "voice": voice, "model": model_value}

    r = await container.redis
    task_id = str(uuid.uuid4())
    payload["task_id"] = task_id
    channel = f"result:{task_id}"
    pubsub = r.pubsub()
    await pubsub.subscribe(channel)

    try:
        await r.xadd("tts:queue", payload, maxlen=1000)

        if not async_flag:
            try:
                result = await asyncio.wait_for(
                    _wait_for_message(pubsub),
                    timeout=settings.task_timeout,
                )
                if result:
                    data = json.loads(result["data"])
                    object_name = data.get("object_name", "")
                    audio_url = get_presigned_url(object_name) if object_name else data.get("audio_url", "")
                    return SpeechResponse(audio_url=audio_url, task_id=task_id)
            except asyncio.TimeoutError:
                pass

        return {"task_id": task_id, "status": "queued" if async_flag else "processing"}

    finally:
        await pubsub.unsubscribe(channel)
        await pubsub.aclose()
