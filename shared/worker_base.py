import asyncio
import json
import os
import signal

import redis.asyncio as aioredis


class WorkerBase:
    queue_key: str
    group_name: str
    consumer_name: str
    redis_url: str
    poll_timeout: int = 5000
    result_ttl: int = 3600

    def __init__(self):
        self.redis_url = os.environ.get("REDIS_URL", "redis://redis:6379/0")
        self.consumer_name = os.environ.get("HOSTNAME", f"{self.__class__.__name__}-1")
        self._shutdown_event = asyncio.Event()
        self._r: aioredis.Redis | None = None

    async def connect(self):
        self._r = aioredis.from_url(self.redis_url, decode_responses=True)
        await self._r.ping()
        try:
            await self._r.xgroup_create(self.queue_key, self.group_name, id="0", mkstream=True)
        except aioredis.ResponseError:
            pass

    async def disconnect(self):
        if self._r:
            await self._r.aclose()

    async def process(self, message: dict) -> dict:
        raise NotImplementedError

    async def on_task(self, message_id: str, data: dict):
        task_id = data["task_id"]
        try:
            result = await self.process(data)
        except Exception as e:
            print(f"Task {task_id} failed: {e}", flush=True)
            result = {"error": str(e)}
        try:
            await self._r.set(f"task:{task_id}", json.dumps(result), ex=self.result_ttl)
            await self._r.publish(f"result:{task_id}", json.dumps(result))
        finally:
            await self._r.xack(self.queue_key, self.group_name, message_id)

    async def run(self):
        await self.connect()
        loop = asyncio.get_event_loop()
        for sig in (signal.SIGTERM, signal.SIGINT):
            try:
                loop.add_signal_handler(sig, self._shutdown_event.set)
            except NotImplementedError:
                pass

        print(f"{self.consumer_name} started, waiting for tasks on {self.queue_key}...", flush=True)

        while not self._shutdown_event.is_set():
            try:
                messages = await self._r.xreadgroup(
                    self.group_name, self.consumer_name,
                    {self.queue_key: ">"},
                    count=1, block=self.poll_timeout,
                )
                if messages:
                    for _, msgs in messages:
                        for msg_id, msg_data in msgs:
                            asyncio.create_task(self.on_task(msg_id, msg_data))
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Error in main loop: {e}", flush=True)
                await asyncio.sleep(1)

        print(f"{self.consumer_name} shutting down...", flush=True)
        await self.disconnect()

    def start(self):
        asyncio.run(self.run())
