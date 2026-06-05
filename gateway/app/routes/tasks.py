from fastapi import APIRouter, Depends, HTTPException

from ..core.auth import verify_api_key
from ..core.redis import get_task_result
from ..core.minio import get_presigned_url

router = APIRouter(dependencies=[Depends(verify_api_key)])


@router.get("/tasks/{task_id}")
async def get_task(task_id: str):
    result = await get_task_result(task_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"task_id": task_id, "status": "completed", "result": result}


@router.get("/tasks/{task_id}/download")
async def download_task_file(task_id: str):
    result = await get_task_result(task_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Task not found")
    object_name = result.get("object_name")
    if not object_name:
        raise HTTPException(status_code=404, detail="No file in task result")
    url = get_presigned_url(object_name)
    return {"download_url": url}
