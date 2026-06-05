from fastapi import APIRouter, Depends, UploadFile, File, Form
from pydantic import BaseModel

from ..core.auth import verify_api_key
from ..core.redis import push_task, get_task_result

router = APIRouter(dependencies=[Depends(verify_api_key)])


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
    task_id = await push_task("surya:queue", {
        "filename": file.filename,
        "languages": languages.split(","),
        "data": contents.hex(),
    })

    if async_:
        return {"task_id": task_id, "status": "queued"}

    result = await get_task_result(task_id)
    if result is None:
        return {"task_id": task_id, "status": "processing"}
    return {
        "text": result.get("text", ""),
        "blocks": result.get("blocks"),
        "task_id": task_id,
    }
