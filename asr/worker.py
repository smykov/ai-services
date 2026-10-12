import os
import tempfile

from embedder import embed
from transcriber import transcribe

from shared.minio_uploader import create_minio_client
from shared.worker_base import WorkerBase


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
        want_embedding = str(data.get("embed", "")).lower() in ("1", "true", "yes")

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            response = self._mc.get_object(
                os.environ.get("MINIO_BUCKET", "ai-services"),
                object_name,
            )
            f.write(response.read())
            audio_path = f.name

        try:
            result = transcribe(audio_path, language=language, model_name=model_name)
            if want_embedding:
                result["speaker"] = embed(audio_path)
            return result
        finally:
            os.unlink(audio_path)


if __name__ == "__main__":
    ASRWorker().start()
