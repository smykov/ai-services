import uuid

from .container import container
from .config import settings


async def upload_file(data: bytes, prefix: str = "") -> str:
    mc = container.minio
    object_name = f"{prefix}{uuid.uuid4()}"
    mc.put_object(
        settings.minio_bucket,
        object_name,
        data,
        length=len(data),
    )
    return object_name


def get_presigned_url(object_name: str, expires: int = 3600) -> str:
    mc = container.minio
    return mc.presigned_get_object(settings.minio_bucket, object_name, expires=expires)
