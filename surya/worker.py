import os
import tempfile

from reader import extract_text

from shared.minio_uploader import create_minio_client
from shared.worker_base import WorkerBase


BUCKET = os.environ.get("MINIO_BUCKET", "ai-services")


class SuryaWorker(WorkerBase):
    queue_key = "surya:queue"
    group_name = "surya-workers"

    def __init__(self):
        super().__init__()
        self._mc = create_minio_client()

    async def process(self, data: dict) -> dict:
        object_name = data.get("object_name", "")
        languages = data.get("languages", ["en", "ru"])

        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            response = self._mc.get_object(BUCKET, object_name)
            f.write(response.read())
            image_path = f.name

        try:
            return extract_text(image_path, languages=languages)
        finally:
            os.unlink(image_path)


if __name__ == "__main__":
    SuryaWorker().start()
