import os
import tempfile

from shared.worker_base import WorkerBase
from shared.minio_uploader import create_minio_client
from transcriber import transcribe


class ASRWorker(WorkerBase):
    queue_key = "asr:queue"
    group_name = "asr-workers"

    def __init__(self):
        super().__init__()
        self._mc = create_minio_client()

    async def process(self, data: dict) -> dict:
        object_name = data.get("object_name", "")
        language = data.get("language", "auto")
        model_name = data.get("model", "turbo")

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            response = self._mc.get_object(
                os.environ.get("MINIO_BUCKET", "ai-services"),
                object_name,
            )
            f.write(response.read())
            audio_path = f.name

        try:
            return transcribe(audio_path, language=language, model_name=model_name)
        finally:
            os.unlink(audio_path)


if __name__ == "__main__":
    ASRWorker().start()
