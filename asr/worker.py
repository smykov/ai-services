import asyncio
import json
import os
import tempfile

import redis.asyncio as aioredis

from transcriber import transcribe

REDIS_URL = os.environ.get("REDIS_URL", "redis://redis:6379/0")
QUEUE_KEY = "asr:queue"
GROUP_NAME = "asr-workers"
CONSUMER_NAME = os.environ.get("HOSTNAME", "asr-worker-1")


async def process_task(message):
    data = json.loads(message["data"])
    task_id = data["task_id"]
    audio_data = bytes.fromhex(data.get("data", ""))
    language = data.get("language", "auto")
    model_name = data.get("model", "turbo")

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        f.write(audio_data)
        audio_path = f.name

    try:
        result = transcribe(audio_path, language=language, model_name=model_name)
        r = aioredis.from_url(REDIS_URL, decode_responses=True)
        await r.set(f"task:{task_id}", json.dumps(result), ex=3600)
        await r.publish(f"result:{task_id}", json.dumps(result))
        await r.xack(QUEUE_KEY, GROUP_NAME, message["id"])
        await r.close()
    finally:
        os.unlink(audio_path)


async def main():
    r = aioredis.from_url(REDIS_URL, decode_responses=True)
    try:
        await r.xgroup_create(QUEUE_KEY, GROUP_NAME, id="0", mkstream=True)
    except aioredis.ResponseError:
        pass

    print(f"ASR worker {CONSUMER_NAME} started, waiting for tasks...")

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
