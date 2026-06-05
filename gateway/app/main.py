from contextlib import asynccontextmanager

from fastapi import FastAPI

from .core.container import container
from .core.redis import push_task, wait_for_result
from .mcp.server import mcp_app
from .routes import audio, ocr, tasks, health, metrics


@asynccontextmanager
async def lifespan(app: FastAPI):
    _ = container.minio
    _ = await container.redis
    yield
    await container.close_redis()


app = FastAPI(
    title="Ecosystem AI Services",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs",
)

app.include_router(health.router)
app.include_router(metrics.router)
app.include_router(audio.router, prefix="/v1")
app.include_router(ocr.router, prefix="/v1")
app.include_router(tasks.router, prefix="/v1")
app.mount("/mcp", mcp_app)
