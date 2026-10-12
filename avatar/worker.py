import asyncio
import json
import os
import tempfile
import time

from engine import Engine, FaceOptions
from weights import ensure_weights

from shared.minio_uploader import create_minio_client, ensure_bucket
from shared.worker_base import WorkerBase

BUCKET = os.environ.get("MINIO_BUCKET", "ai-services")
CACHE_DIR = os.environ.get("AVATAR_CACHE_DIR", "/cache")
# Models leave the GPU after this many idle seconds, so the card is shared with the other workers.
IDLE_UNLOAD_S = int(os.environ.get("AVATAR_IDLE_UNLOAD_S", "300"))
# Long renders outlive the default hour of result retention while the client is still polling.
RESULT_TTL_S = int(os.environ.get("AVATAR_RESULT_TTL_S", str(24 * 3600)))


def _bool(v, default=True) -> bool:
    if v is None or v == "":
        return default
    return str(v).lower() in ("1", "true", "yes")


class AvatarWorker(WorkerBase):
    queue_key = "avatar:queue"
    group_name = "avatar-workers"
    result_ttl = RESULT_TTL_S

    def __init__(self):
        super().__init__()
        self._mc = create_minio_client()
        ensure_bucket(self._mc, BUCKET)
        self._engine = Engine(CACHE_DIR)
        self._gpu_lock = asyncio.Lock()
        self._last_used = time.monotonic()

    async def run(self):
        ensure_weights()
        reaper = asyncio.create_task(self._unload_when_idle())
        try:
            await super().run()
        finally:
            reaper.cancel()

    async def _unload_when_idle(self):
        while True:
            await asyncio.sleep(30)
            idle = time.monotonic() - self._last_used
            if self._engine.loaded and idle > IDLE_UNLOAD_S and not self._gpu_lock.locked():
                async with self._gpu_lock:
                    await asyncio.to_thread(self._engine.unload)
                print("models unloaded after idle", flush=True)

    async def process(self, data: dict) -> dict:
        loop = asyncio.get_running_loop()
        task_id = data["task_id"]

        def report(p: dict):
            asyncio.run_coroutine_threadsafe(
                self._r.set(f"task:{task_id}:progress", json.dumps(p), ex=self.result_ttl), loop)

        # One render at a time: two would double the GPU memory and slow each other down.
        async with self._gpu_lock:
            try:
                return await asyncio.to_thread(self._render, data, report)
            finally:
                self._last_used = time.monotonic()

    def _fetch(self, object_name: str, suffix: str) -> str:
        fd, path = tempfile.mkstemp(suffix=suffix)
        os.close(fd)
        self._mc.fget_object(BUCKET, object_name, path)
        self._mc.remove_object(BUCKET, object_name)
        return path

    def _render(self, data: dict, report) -> dict:
        opts = FaceOptions(
            max_side=int(data.get("max_side") or 720),
            extra_margin=int(data.get("extra_margin") or 10),
            parsing_mode=data.get("parsing_mode") or "jaw",
            left_cheek_width=int(data.get("left_cheek_width") or 90),
            right_cheek_width=int(data.get("right_cheek_width") or 90),
        )
        temp = []
        try:
            if data.get("face_object"):
                face_path = self._fetch(data["face_object"], os.path.splitext(data["face_object"])[1] or ".mp4")
                temp.append(face_path)
                report({"stage": "preparing face"})
                face = self._engine.prepare(face_path, opts)
            else:
                face = self._engine.load_face(data["face_id"])

            audio_path = self._fetch(data["audio_object"], os.path.splitext(data["audio_object"])[1] or ".wav")
            temp.append(audio_path)
            fd, out_path = tempfile.mkstemp(suffix=".mp4")
            os.close(fd)
            temp.append(out_path)

            report({"stage": "rendering"})
            stats = self._engine.render(
                face, audio_path, out_path,
                restore=_bool(data.get("restore")),
                restore_weight=float(data.get("restore_weight") or 0.5),
                progress=lambda p: report({"stage": "rendering", **p}),
            )
            object_name = f"avatar/{data['task_id']}.mp4"
            self._mc.fput_object(BUCKET, object_name, out_path, content_type="video/mp4")
            return {"object_name": object_name, "face_id": face.face_id, **stats}
        except KeyError as e:
            return {"error": str(e).strip("'")}
        finally:
            for p in temp:
                if os.path.exists(p):
                    os.unlink(p)


if __name__ == "__main__":
    AvatarWorker().start()
