from minio import Minio
from redis.asyncio import Redis

from .config import settings


class Container:
    def __init__(self):
        self._redis: Redis | None = None
        self._minio: Minio | None = None

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

    async def close_redis(self):
        if self._redis:
            await self._redis.aclose()
            self._redis = None


container = Container()
