import json

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

from ..core.auth import verify_api_key
from ..core.config import settings
from ..core.minio import upload_file
from ..core.redis import push_and_wait, push_task

router = APIRouter(dependencies=[Depends(verify_api_key)], tags=["ocr"])


class OCRResponse(BaseModel):
    text: str
    blocks: list[dict] | None = None
    task_id: str | None = None


@router.post("/ocr")
async def extract_text(
    file: UploadFile = File(...),
    languages: str = Form("en,ru"),
    async_: bool = Form(False, alias="async"),
):
    contents = await file.read()
    if len(contents) > settings.max_upload_size_mb * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File too large")

    object_name = await upload_file(contents, prefix="ocr/")

    if async_:
        task_id = await push_task("surya:queue", {
            "object_name": object_name,
            "languages": json.dumps(languages.split(",")),
        })
        return {"task_id": task_id, "status": "queued"}

    result = await push_and_wait("surya:queue", {
        "object_name": object_name,
        "languages": languages.split(","),
    })
    if result is None:
        raise HTTPException(status_code=504, detail="Task timeout")
    return OCRResponse(text=result.get("text", ""), blocks=result.get("blocks"), task_id=result.get("task_id"))
