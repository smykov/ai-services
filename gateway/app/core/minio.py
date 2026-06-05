from minio import Minio

from .config import settings

minio_client: Minio | None = None


async def init_minio():
    global minio_client
    minio_client = Minio(
        settings.minio_endpoint,
        access_key=settings.minio_access_key,
        secret_key=settings.minio_secret_key,
        secure=False,
    )
    if not minio_client.bucket_exists(settings.minio_bucket):
        minio_client.make_bucket(settings.minio_bucket)


def get_minio() -> Minio:
    if minio_client is None:
        raise RuntimeError("MinIO not initialized")
    return minio_client


def get_presigned_url(object_name: str, expires: int = 3600) -> str:
    mc = get_minio()
    return mc.presigned_get_object(settings.minio_bucket, object_name, expires=expires)
