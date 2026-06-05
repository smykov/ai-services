from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from pydantic import BaseModel

from ..core.auth import verify_api_key
from ..core.redis import push_task, set_task_result, get_task_result, publish_result

router = APIRouter(dependencies=[Depends(verify_api_key)])


class TranscriptionResponse(BaseModel):
    text: str
    task_id: str | None = None


class SpeechResponse(BaseModel):
    audio_url: str
    task_id: str | None = None


class TaskStatus(BaseModel):
    task_id: str
    status: str
    result: dict | None = None


@router.post("/audio/transcriptions")
async def transcribe_audio(
    file: UploadFile = File(...),
    language: str = Form("auto"),
    model: str = Form("turbo"),
    async_: bool = Form(False, alias="async"),
):
    contents = await file.read()
    task_id = await push_task("asr:queue", {
        "filename": file.filename,
        "language": language,
        "model": model,
        "data": contents.hex(),
    })

    if async_:
        return {"task_id": task_id, "status": "queued"}

    result = await get_task_result(task_id)
    if result is None:
        return {"task_id": task_id, "status": "processing"}
    return {"text": result.get("text", ""), "task_id": task_id}


@router.post("/audio/speech")
async def synthesize_speech(
    text: str = Form(...),
    voice: str = Form("default"),
    model: str = Form("xtts-v2"),
    async_: bool = Form(False, alias="async"),
):
    task_id = await push_task("tts:queue", {
        "text": text,
        "voice": voice,
        "model": model,
    })

    if async_:
        return {"task_id": task_id, "status": "queued"}

    result = await get_task_result(task_id)
    if result is None:
        return {"task_id": task_id, "status": "processing"}
    return {"audio_url": result.get("audio_url", ""), "task_id": task_id}
