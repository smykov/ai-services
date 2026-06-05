from contextlib import asynccontextmanager

from fastapi import FastAPI

from .core.redis import init_redis, close_redis
from .core.minio import init_minio
from .mcp.server import mcp_app
from .routes import audio, ocr, tasks, health


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_redis()
    await init_minio()
    yield
    await close_redis()


app = FastAPI(
    title="Ecosystem AI Services",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs",
)

app.include_router(health.router)
app.include_router(audio.router, prefix="/v1")
app.include_router(ocr.router, prefix="/v1")
app.include_router(tasks.router, prefix="/v1")
app.mount("/mcp", mcp_app)
