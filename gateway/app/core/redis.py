import asyncio
import json
import uuid

from .config import settings
from .container import container


async def push_task(queue: str, payload: dict) -> str:
    r = await container.redis
    task_id = str(uuid.uuid4())
    payload["task_id"] = task_id
    await r.xadd(queue, payload, maxlen=1000)
    return task_id


async def push_and_wait(queue: str, payload: dict, timeout: int | None = None) -> dict | None:
    r = await container.redis
    task_id = str(uuid.uuid4())
    payload["task_id"] = task_id
    channel = f"result:{task_id}"

    pubsub = r.pubsub()
    await pubsub.subscribe(channel)

    try:
        await r.xadd(queue, payload, maxlen=1000)
        result = await asyncio.wait_for(
            _wait_for_message(pubsub),
            timeout=timeout or settings.task_timeout,
        )
        if result:
            return json.loads(result["data"])
        return None
    except TimeoutError:
        return None
    finally:
        await pubsub.unsubscribe(channel)
        await pubsub.aclose()


async def _wait_for_message(pubsub):
    while True:
        message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
        if message:
            return message


async def set_task_result(task_id: str, result: dict, ttl: int | None = None):
    r = await container.redis
    await r.set(f"task:{task_id}", json.dumps(result), ex=ttl or settings.task_result_ttl)


async def get_task_result(task_id: str) -> dict | None:
    r = await container.redis
    data = await r.get(f"task:{task_id}")
    if data is None:
        return None
    return json.loads(data)
