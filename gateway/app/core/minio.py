import io
import uuid
from datetime import timedelta

from minio import Minio

from .config import settings
from .container import container


async def upload_file(data: bytes, prefix: str = "") -> str:
    mc = container.minio
    object_name = f"{prefix}{uuid.uuid4()}"
    mc.put_object(
        settings.minio_bucket,
        object_name,
        io.BytesIO(data),
        length=len(data),
    )
    return object_name


def get_presigned_url(object_name: str, expires: int = 3600) -> str:
    endpoint = settings.minio_public_endpoint or settings.minio_endpoint
    mc = Minio(
        endpoint,
        access_key=settings.minio_access_key,
        secret_key=settings.minio_secret_key,
        secure=settings.minio_secure,
        region=settings.minio_region,
    )
    return mc.presigned_get_object(settings.minio_bucket, object_name, expires=timedelta(seconds=expires))
