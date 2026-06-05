import json
import uuid

import redis.asyncio as aioredis

from .config import settings

redis_client: aioredis.Redis | None = None


async def init_redis():
    global redis_client
    redis_client = aioredis.from_url(
        settings.redis_url, decode_responses=True
    )
    await redis_client.ping()


async def close_redis():
    global redis_client
    if redis_client:
        await redis_client.aclose()
        redis_client = None


def get_redis() -> aioredis.Redis:
    if redis_client is None:
        raise RuntimeError("Redis not initialized")
    return redis_client


async def push_task(queue: str, payload: dict) -> str:
    r = get_redis()
    task_id = str(uuid.uuid4())
    payload["task_id"] = task_id
    await r.xadd(queue, payload, maxlen=1000)
    return task_id


async def publish_result(channel: str, result: dict):
    r = get_redis()
    await r.publish(channel, json.dumps(result))


async def subscribe_result(channel: str):
    r = get_redis()
    pubsub = r.pubsub()
    await pubsub.subscribe(channel)
    return pubsub


async def set_task_result(task_id: str, result: dict, ttl: int | None = None):
    r = get_redis()
    key = f"task:{task_id}"
    await r.set(key, json.dumps(result), ex=ttl or settings.task_result_ttl)


async def get_task_result(task_id: str) -> dict | None:
    r = get_redis()
    data = await r.get(f"task:{task_id}")
    if data is None:
        return None
    return json.loads(data)
