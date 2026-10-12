import asyncio
import json
import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from pydantic import BaseModel

from ..core.auth import verify_api_key
from ..core.config import settings
from ..core.container import container
from ..core.http import read_json
from ..core.minio import upload_file
from ..core.redis import _wait_for_message

router = APIRouter(dependencies=[Depends(verify_api_key)], tags=["ocr"])


class OCRResponse(BaseModel):
    text: str
    blocks: list[dict] | None = None
    task_id: str | None = None


@router.post("/ocr")
async def extract_text(
    request: Request,
    file: UploadFile = File(None),
    languages: str = Form(None),
    async_: bool = Form(False, alias="async"),
):
    content_type = request.headers.get("content-type", "").lower()
    lang = "en,ru"
    async_flag = False

    if "application/json" in content_type:
        body = await read_json(request)
        lang = body.get("languages", lang)
        async_flag = bool(body.get("async", False))
        if not file and "file_url" in body:
            pass
    else:
        if file is None:
            raise HTTPException(status_code=422, detail="File field required")
        lang = languages or lang
        async_flag = async_

    if file:
        contents = await file.read()
        if len(contents) > settings.max_upload_size_mb * 1024 * 1024:
            raise HTTPException(status_code=413, detail="File too large")
        object_name = await upload_file(contents, prefix="ocr/")
    else:
        raise HTTPException(status_code=400, detail="No file provided")

    langs_json = json.dumps(lang.split(","))
    payload = {"object_name": object_name, "languages": langs_json}

    r = await container.redis
    task_id = str(uuid.uuid4())
    payload["task_id"] = task_id
    channel = f"result:{task_id}"
    pubsub = r.pubsub()
    await pubsub.subscribe(channel)

    try:
        await r.xadd("surya:queue", payload, maxlen=1000)

        if not async_flag:
            try:
                result = await asyncio.wait_for(
                    _wait_for_message(pubsub),
                    timeout=settings.task_timeout,
                )
                if result:
                    data = json.loads(result["data"])
                    return OCRResponse(
                        text=data.get("text", ""),
                        blocks=data.get("blocks"),
                        task_id=task_id,
                    )
            except TimeoutError:
                pass

        return {"task_id": task_id, "status": "queued" if async_flag else "processing"}

    finally:
        await pubsub.unsubscribe(channel)
        await pubsub.aclose()

