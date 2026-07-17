import asyncio
from pathlib import Path

import pytest

from workflow.async_queue import DurableAsyncQueue
from workflow.persistence import QueueFull, SQLiteStateStore


def test_queue_dedupes_and_ack_is_idempotent(tmp_path: Path):
    store = SQLiteStateStore(tmp_path, max_pending_jobs=10)
    first = store.enqueue_job("hunt", "same", {"n": 1})
    second = store.enqueue_job("hunt", "same", {"n": 2})
    assert first.job_id == second.job_id

    leased = store.acquire_job("hunt", "worker", lease_seconds=30)
    assert leased is not None
    assert leased.state == "leased"
    store.ack_job(leased.job_id, {"ok": True})
    store.ack_job(leased.job_id, {"ok": True})
    assert store.stats()["queue"]["done"] == 1


def test_queue_backpressure(tmp_path: Path):
    store = SQLiteStateStore(tmp_path, max_pending_jobs=1)
    store.enqueue_job("hunt", "one", {"n": 1})
    with pytest.raises(QueueFull):
        store.enqueue_job("hunt", "two", {"n": 2})


def test_async_queue_timeout_and_completion(tmp_path: Path):
    async def scenario():
        queue = DurableAsyncQueue(tmp_path, hunt_id="hunt", max_pending_jobs=2, poll_interval=0.01)
        await queue.put({"n": 1}, "one")
        job = await queue.get("worker", timeout=0.1)
        assert job is not None
        await queue.task_done(job.job_id, {"ok": True})
        assert await queue.get("worker", timeout=0.01) is None
        await queue.close()

    asyncio.run(scenario())
