import time

from fastapi import APIRouter

router = APIRouter(tags=["metrics"])

_start_time = time.time()


@router.get("/metrics")
async def metrics():
    uptime = time.time() - _start_time
    return {
        "uptime_seconds": uptime,
        "service": "ecosystem-ai-services",
        "version": "0.1.0",
    }
