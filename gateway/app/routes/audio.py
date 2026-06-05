from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

from ..core.auth import verify_api_key
from ..core.config import settings
from ..core.minio import upload_file
from ..core.redis import push_and_wait, push_task

router = APIRouter(dependencies=[Depends(verify_api_key)], tags=["audio"])


class TranscriptionResponse(BaseModel):
    text: str
    task_id: str | None = None


class SpeechResponse(BaseModel):
    audio_url: str
    task_id: str | None = None


@router.post("/audio/transcriptions")
async def transcribe_audio(
    file: UploadFile = File(...),
    language: str = Form("auto"),
    model: str = Form("turbo"),
    async_: bool = Form(False, alias="async"),
):
    contents = await file.read()
    if len(contents) > settings.max_upload_size_mb * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File too large")

    object_name = await upload_file(contents, prefix="audio/")

    if async_:
        task_id = await push_task("asr:queue", {
            "object_name": object_name,
            "language": language,
            "model": model,
        })
        return {"task_id": task_id, "status": "queued"}

    result = await push_and_wait("asr:queue", {
        "object_name": object_name,
        "language": language,
        "model": model,
    })
    if result is None:
        raise HTTPException(status_code=504, detail="Task timeout")
    return TranscriptionResponse(text=result.get("text", ""), task_id=result.get("task_id"))


@router.post("/audio/speech")
async def synthesize_speech(
    text: str = Form(...),
    voice: str = Form("default"),
    model: str = Form("xtts-v2"),
    async_: bool = Form(False, alias="async"),
):
    if async_:
        task_id = await push_task("tts:queue", {
            "text": text,
            "voice": voice,
            "model": model,
        })
        return {"task_id": task_id, "status": "queued"}

    result = await push_and_wait("tts:queue", {
        "text": text,
        "voice": voice,
        "model": model,
    })
    if result is None:
        raise HTTPException(status_code=504, detail="Task timeout")
    return SpeechResponse(audio_url=result.get("audio_url", ""), task_id=result.get("task_id"))
