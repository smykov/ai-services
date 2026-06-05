import asyncio
import json
import os
import tempfile

import redis.asyncio as aioredis

from reader import extract_text

REDIS_URL = os.environ.get("REDIS_URL", "redis://redis:6379/0")
QUEUE_KEY = "surya:queue"
GROUP_NAME = "surya-workers"
CONSUMER_NAME = os.environ.get("HOSTNAME", "surya-worker-1")


async def process_task(message):
    data = json.loads(message["data"])
    task_id = data["task_id"]
    image_data = bytes.fromhex(data.get("data", ""))
    languages = data.get("languages", ["en", "ru"])

    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
        f.write(image_data)
        image_path = f.name

    try:
        result = extract_text(image_path, languages=languages)
        r = aioredis.from_url(REDIS_URL, decode_responses=True)
        await r.set(f"task:{task_id}", json.dumps(result), ex=3600)
        await r.publish(f"result:{task_id}", json.dumps(result))
        await r.xack(QUEUE_KEY, GROUP_NAME, message["id"])
        await r.close()
    finally:
        os.unlink(image_path)


async def main():
    r = aioredis.from_url(REDIS_URL, decode_responses=True)
    try:
        await r.xgroup_create(QUEUE_KEY, GROUP_NAME, id="0", mkstream=True)
    except aioredis.ResponseError:
        pass

    print(f"Surya worker {CONSUMER_NAME} started, waiting for tasks...")

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
