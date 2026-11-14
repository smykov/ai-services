import os

from synthesizer import synthesize

from shared.minio_uploader import create_minio_client, ensure_bucket
from shared.worker_base import WorkerBase

BUCKET = os.environ.get("MINIO_BUCKET", "ai-services")


class TTSKokoroWorker(WorkerBase):
    queue_key = "tts:kokoro:queue"
    group_name = "tts-kokoro-workers"

    def __init__(self):
        super().__init__()
        self._mc = create_minio_client()
        ensure_bucket(self._mc, BUCKET)

    async def process(self, data: dict) -> dict:
        output_path = synthesize(
            data["text"],
            voice=data.get("voice", "default"),
            language=data.get("language", "en"),
            speed=float(data.get("speed") or 1.0),
        )
        object_name = f"tts/{data['task_id']}.wav"
        try:
            with open(output_path, "rb") as f:
                self._mc.put_object(BUCKET, object_name, f, length=os.path.getsize(output_path), content_type="audio/wav")
        finally:
            os.unlink(output_path)

        return {
            "audio_url": f"{os.environ.get('MINIO_ENDPOINT', 'minio:9000')}/{BUCKET}/{object_name}",
            "object_name": object_name,
        }


if __name__ == "__main__":
    TTSKokoroWorker().start()
