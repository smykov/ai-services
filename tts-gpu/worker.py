import asyncio
import json
import os
import io

import redis.asyncio as aioredis
from minio import Minio

from synthesizer import synthesize

REDIS_URL = os.environ.get("REDIS_URL", "redis://redis:6379/0")
MINIO_ENDPOINT = os.environ.get("MINIO_ENDPOINT", "minio:9000")
MINIO_ACCESS_KEY = os.environ.get("MINIO_ACCESS_KEY", "minioadmin")
MINIO_SECRET_KEY = os.environ.get("MINIO_SECRET_KEY", "minioadmin")
MINIO_BUCKET = os.environ.get("MINIO_BUCKET", "ai-services")
QUEUE_KEY = "tts:queue"
GROUP_NAME = "tts-workers"
CONSUMER_NAME = os.environ.get("HOSTNAME", "tts-worker-1")

mc = Minio(MINIO_ENDPOINT, access_key=MINIO_ACCESS_KEY, secret_key=MINIO_SECRET_KEY, secure=False)


async def process_task(message):
    data = json.loads(message["data"])
    task_id = data["task_id"]
    text = data["text"]
    voice = data.get("voice", "default")
    model = data.get("model", "xtts-v2")

    output_path = synthesize(text, voice=voice, model_name=model)

    object_name = f"tts/{task_id}.wav"
    with open(output_path, "rb") as f:
        mc.put_object(MINIO_BUCKET, object_name, f, length=os.path.getsize(output_path))

    os.unlink(output_path)

    result = {"audio_url": f"{MINIO_ENDPOINT}/{MINIO_BUCKET}/{object_name}", "object_name": object_name}

    r = aioredis.from_url(REDIS_URL, decode_responses=True)
    await r.set(f"task:{task_id}", json.dumps(result), ex=3600)
    await r.publish(f"result:{task_id}", json.dumps(result))
    await r.xack(QUEUE_KEY, GROUP_NAME, message["id"])
    await r.close()


async def main():
    r = aioredis.from_url(REDIS_URL, decode_responses=True)
    try:
        await r.xgroup_create(QUEUE_KEY, GROUP_NAME, id="0", mkstream=True)
    except aioredis.ResponseError:
        pass

    if not mc.bucket_exists(MINIO_BUCKET):
        mc.make_bucket(MINIO_BUCKET)

    print(f"TTS worker {CONSUMER_NAME} started, waiting for tasks...")

    while True:
        try:
            messages = await r.xreadgroup(
                GROUP_NAME, CONSUMER_NAME, {QUEUE_KEY: ">"}, count=1, block=5000
            )
            if messages:
                for _, msgs in messages:
                    for msg in msgs:
                        await process_task(msg)
        except asyncio.CancelledError:
            break
        except Exception as e:
            print(f"Error: {e}")
            await asyncio.sleep(1)

    await r.close()


if __name__ == "__main__":
    asyncio.run(main())
