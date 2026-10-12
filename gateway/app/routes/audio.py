import asyncio
import base64
import binascii
import json
import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from pydantic import BaseModel

from ..core.auth import verify_api_key
from ..core.config import settings
from ..core.container import container
from ..core.http import read_json
from ..core.minio import get_presigned_url, upload_file
from ..core.redis import _wait_for_message

router = APIRouter(dependencies=[Depends(verify_api_key)], tags=["audio"])


class SpeakerEmbedding(BaseModel):
    embedding: list[float]
    seconds: float
    reliable: bool


class TranscriptionResponse(BaseModel):
    text: str
    task_id: str | None = None
    speaker: SpeakerEmbedding | None = None


class SpeechResponse(BaseModel):
    audio_url: str | None = None
    task_id: str | None = None
    status: str | None = None


@router.post("/audio/transcriptions")
async def transcribe_audio(
    request: Request,
    file: UploadFile = File(None),
    language: str = Form(None),
    model: str = Form(None),
    embed: bool = Form(False),
    async_: bool = Form(False, alias="async"),
):
    content_type = request.headers.get("content-type", "").lower()
    lang = "auto"
    model_val = "turbo"
    async_flag = False
    embed_flag = False

    if "application/json" in content_type:
        body = await read_json(request)
        lang = body.get("language", lang)
        model_val = body.get("model", model_val)
        async_flag = bool(body.get("async", False))
        embed_flag = bool(body.get("embed", False))
        if not file and "file_url" in body:
            pass
    else:
        if file is None:
            raise HTTPException(status_code=422, detail="File field required")
        lang = language or lang
        model_val = model or model_val
        async_flag = async_
        embed_flag = embed

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
        "embed": "1" if embed_flag else "0",
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
                    return TranscriptionResponse(
                        text=data.get("text", ""),
                        task_id=task_id,
                        speaker=data.get("speaker"),
                    )
            except TimeoutError:
                pass

        return {"task_id": task_id, "status": "queued" if async_flag else "processing"}

    finally:
        await pubsub.unsubscribe(channel)
        await pubsub.aclose()


_SPEECH_REQUEST_BODY = {
    "required": True,
    "content": {
        "application/json": {
            "schema": {
                "type": "object",
                "required": ["input"],
                "properties": {
    "input": {"type": "string", "description": "Text to synthesize (alias: text)"},
    "voice": {"type": "string", "default": "default", "description": "Voice name; ignored by XTTS unless a speaker_wav is given"},
    "model": {"type": "string", "default": "xtts-v2", "description": "TTS model (tts-1 / tts-1-hd are aliases of xtts-v2)"},
    "language": {"type": "string", "default": "ru", "description": "Language code (alias: locale)"},
    "async": {"type": "boolean", "default": False, "description": "Return task_id immediately instead of waiting"},
    "speaker_wav": {"type": "string", "format": "byte", "description": "Voice sample for XTTS cloning, base64-encoded wav"},
},
            }
        },
        "multipart/form-data": {
            "schema": {
                "type": "object",
                "required": ["input"],
                "properties": {
    "input": {"type": "string", "description": "Text to synthesize (alias: text)"},
    "voice": {"type": "string", "default": "default", "description": "Voice name; ignored by XTTS unless a speaker_wav is given"},
    "model": {"type": "string", "default": "xtts-v2", "description": "TTS model (tts-1 / tts-1-hd are aliases of xtts-v2)"},
    "language": {"type": "string", "default": "ru", "description": "Language code (alias: locale)"},
    "async": {"type": "boolean", "default": False, "description": "Return task_id immediately instead of waiting"},
    "speaker_wav": {"type": "string", "format": "binary", "description": "Reference voice sample for XTTS cloning (wav file)"},
},
            }
        },
    },
}


@router.post(
    "/audio/speech",
    response_model=SpeechResponse,
    response_model_exclude_none=True,
    summary="Synthesize speech (XTTS-v2), optionally cloning a voice from a sample",
    openapi_extra={"requestBody": _SPEECH_REQUEST_BODY},
)
async def synthesize_speech(request: Request):
    content_type = request.headers.get("content-type", "").lower()

    if "application/json" in content_type:
        body = await read_json(request)
    else:
        form = await request.form()
        body = {k: v for k, v in form.items()}

    text = body.get("input", body.get("text"))
    voice = body.get("voice", "default")
    model_value = body.get("model", "xtts-v2")
    language = body.get("language", body.get("locale", "ru"))
    async_flag = str(body.get("async", body.get("async_", "false"))).lower() in ("true", "1")

    if not text:
        raise HTTPException(status_code=422, detail="Field 'input' or 'text' is required")

    payload = {"text": text, "voice": voice, "model": model_value, "language": language}

    # Reference voice for XTTS: multipart file `speaker_wav`, or base64 string in JSON/form.
    sample = body.get("speaker_wav")
    if sample is not None and sample != "":
        if hasattr(sample, "read"):
            sample_bytes = await sample.read()
        else:
            try:
                sample_bytes = base64.b64decode(str(sample), validate=True)
            except (binascii.Error, ValueError):
                raise HTTPException(status_code=422, detail="'speaker_wav' must be a file or base64-encoded audio")
        if not sample_bytes:
            raise HTTPException(status_code=422, detail="'speaker_wav' is empty")
        if len(sample_bytes) > settings.max_upload_size_mb * 1024 * 1024:
            raise HTTPException(status_code=413, detail="Speaker sample too large")
        payload["speaker_object"] = await upload_file(sample_bytes, prefix="speaker/")

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
                    if data.get("error"):
                        raise HTTPException(status_code=502, detail=f"TTS worker failed: {data['error']}")
                    object_name = data.get("object_name", "")
                    audio_url = get_presigned_url(object_name) if object_name else data.get("audio_url", "")
                    return SpeechResponse(audio_url=audio_url, task_id=task_id)
            except TimeoutError:
                pass

        return SpeechResponse(task_id=task_id, status="queued" if async_flag else "processing")

    finally:
        await pubsub.unsubscribe(channel)
        await pubsub.aclose()
