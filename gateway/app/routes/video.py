import asyncio
import json
import re
import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

from ..core.auth import verify_api_key
from ..core.config import settings
from ..core.container import container
from ..core.minio import get_presigned_url, upload_file
from ..core.redis import _wait_for_message

router = APIRouter(dependencies=[Depends(verify_api_key)], tags=["video"])

_FACE_ID = re.compile(r"^[0-9a-f]{32}$")


class TalkingHeadResponse(BaseModel):
    video_url: str | None = None
    face_id: str | None = None
    task_id: str | None = None
    status: str | None = None
    seconds: float | None = None


async def _read_upload(upload: UploadFile, what: str) -> bytes:
    data = await upload.read()
    if not data:
        raise HTTPException(status_code=422, detail=f"'{what}' is empty")
    if len(data) > settings.max_upload_size_mb * 1024 * 1024:
        raise HTTPException(status_code=413, detail=f"'{what}' too large")
    return data


@router.post(
    "/video/talking-head",
    response_model=TalkingHeadResponse,
    response_model_exclude_none=True,
    summary="Lip-sync a face video or photo to speech (MuseTalk 1.5, optional GFPGAN restoration)",
)
async def talking_head(
    audio: UploadFile = File(..., description="Speech to lip-sync (any format ffmpeg reads)"),
    face: UploadFile = File(None, description="Face video (or photo): looking at the camera, mouth closed, up to 30 s are used"),
    face_id: str = Form(None, description="Reuse a face prepared by an earlier call instead of uploading it again"),
    restore: bool = Form(True, description="Restore the face with GFPGAN: sharper mouth and beard"),
    restore_weight: float = Form(0.5, ge=0.0, le=1.0, description="GFPGAN strength; higher is sharper but smoother skin"),
    parsing_mode: str = Form("jaw", pattern="^(jaw|raw)$", description="Blend border: along the jaw or the whole lower face"),
    left_cheek_width: int = Form(90, ge=0, le=200),
    right_cheek_width: int = Form(90, ge=0, le=200),
    extra_margin: int = Form(10, ge=0, le=60, description="Extra pixels below the chin for an open mouth"),
    max_side: int = Form(720, ge=256, le=1920, description="Longer side of the output video, px"),
    async_: bool = Form(True, alias="async", description="Return task_id immediately (renders take minutes)"),
):
    if face is None and not face_id:
        raise HTTPException(status_code=422, detail="Provide 'face' (file) or 'face_id'")
    if face_id and not _FACE_ID.match(face_id):
        raise HTTPException(status_code=422, detail="'face_id' must be 32 hex characters")

    payload = {
        "audio_object": await upload_file(await _read_upload(audio, "audio"), prefix="avatar-in/audio-"),
        "restore": "1" if restore else "0",
        "restore_weight": str(restore_weight),
        "parsing_mode": parsing_mode,
        "left_cheek_width": str(left_cheek_width),
        "right_cheek_width": str(right_cheek_width),
        "extra_margin": str(extra_margin),
        "max_side": str(max_side),
    }
    if face is not None:
        payload["face_object"] = await upload_file(await _read_upload(face, "face"), prefix="avatar-in/face-")
    else:
        payload["face_id"] = face_id

    r = await container.redis
    task_id = str(uuid.uuid4())
    payload["task_id"] = task_id
    channel = f"result:{task_id}"
    pubsub = r.pubsub()
    await pubsub.subscribe(channel)

    try:
        await r.xadd("avatar:queue", payload, maxlen=1000)

        if not async_:
            try:
                result = await asyncio.wait_for(_wait_for_message(pubsub), timeout=settings.task_timeout)
                if result:
                    data = json.loads(result["data"])
                    if data.get("error"):
                        raise HTTPException(status_code=502, detail=f"Avatar worker failed: {data['error']}")
                    return TalkingHeadResponse(
                        video_url=get_presigned_url(data["object_name"]),
                        face_id=data.get("face_id"),
                        task_id=task_id,
                        seconds=data.get("seconds"),
                    )
            except TimeoutError:
                pass

        return TalkingHeadResponse(task_id=task_id, status="queued" if async_ else "processing")

    finally:
        await pubsub.unsubscribe(channel)
        await pubsub.aclose()
