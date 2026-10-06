import os
import tempfile

from shared.minio_uploader import create_minio_client, ensure_bucket
from shared.worker_base import WorkerBase
from synthesizer import synthesize


BUCKET = os.environ.get("MINIO_BUCKET", "ai-services")


class TTSGPUWorker(WorkerBase):
    queue_key = "tts:queue"
    group_name = "tts-workers"

    def __init__(self):
        super().__init__()
        self._mc = create_minio_client()
        ensure_bucket(self._mc, BUCKET)

    async def process(self, data: dict) -> dict:
        text = data["text"]
        voice = data.get("voice", "default")
        model = data.get("model", "xtts-v2")
        language = data.get("language", "ru").split("-")[0].lower()

        sample_path = None
        speaker_object = data.get("speaker_object")
        if speaker_object:
            fd, sample_path = tempfile.mkstemp(suffix=".wav")
            os.close(fd)
            self._mc.fget_object(BUCKET, speaker_object, sample_path)
            voice = sample_path

        try:
            output_path = synthesize(text, voice=voice, model_name=model, language=language)
        finally:
            if sample_path:
                os.unlink(sample_path)
            if speaker_object:
                self._mc.remove_object(BUCKET, speaker_object)

        object_name = f"tts/{data['task_id']}.wav"
        with open(output_path, "rb") as f:
            self._mc.put_object(BUCKET, object_name, f, length=os.path.getsize(output_path))

        os.unlink(output_path)

        return {
            "audio_url": f"{os.environ.get('MINIO_ENDPOINT', 'minio:9000')}/{BUCKET}/{object_name}",
            "object_name": object_name,
        }


if __name__ == "__main__":
    TTSGPUWorker().start()
