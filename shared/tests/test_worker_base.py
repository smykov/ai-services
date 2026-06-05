from shared.worker_base import WorkerBase


class TestWorker(WorkerBase):
    queue_key = "test:queue"
    group_name = "test-workers"

    async def process(self, data: dict) -> dict:
        return {"echo": data.get("value", "")}


def test_worker_base_instantiation():
    w = TestWorker()
    assert w.queue_key == "test:queue"
    assert w.group_name == "test-workers"
    assert w.consumer_name == "TestWorker-1"


def test_worker_base_consumer_name_from_env(monkeypatch):
    monkeypatch.setenv("HOSTNAME", "custom-pod")
    w = TestWorker()
    assert w.consumer_name == "custom-pod"
