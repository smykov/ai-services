from minio import Minio
from redis.asyncio import Redis

from .config import settings
from .llm import LLMService


class Container:
    def __init__(self):
        self._redis: Redis | None = None
        self._minio: Minio | None = None
        self._llm: LLMService | None = None

    @property
    async def redis(self) -> Redis:
        if self._redis is None:
            self._redis = Redis.from_url(settings.redis_url, decode_responses=True)
            await self._redis.ping()
        return self._redis

    @property
    def minio(self) -> Minio:
        if self._minio is None:
            self._minio = Minio(
                settings.minio_endpoint,
                access_key=settings.minio_access_key,
                secret_key=settings.minio_secret_key,
                secure=settings.minio_secure,
            )
            if not self._minio.bucket_exists(settings.minio_bucket):
                self._minio.make_bucket(settings.minio_bucket)
        return self._minio

    @property
    def llm(self) -> LLMService:
        if self._llm is None:
            self._llm = LLMService()
        return self._llm

    async def close_redis(self):
        if self._redis:
            await self._redis.aclose()
            self._redis = None

    async def close_llm(self):
        if self._llm:
            await self._llm.close()
            self._llm = None


container = Container()
