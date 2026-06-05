import os

from minio import Minio


def create_minio_client() -> Minio:
    return Minio(
        os.environ.get("MINIO_ENDPOINT", "minio:9000"),
        access_key=os.environ.get("MINIO_ACCESS_KEY", "minioadmin"),
        secret_key=os.environ.get("MINIO_SECRET_KEY", "minioadmin"),
        secure=False,
    )


def ensure_bucket(mc: Minio, bucket: str):
    if not mc.bucket_exists(bucket):
        mc.make_bucket(bucket)
