"""
Async facade over the durable SQLite queue.

It supplies backpressure, dedupe through idempotency keys, leases, and
idempotent completion while keeping the storage layer dependency-free.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from workflow.persistence import QueueFull, QueueJob, SQLiteStateStore


class DurableAsyncQueue:
    def __init__(self, hunt_dir: str | Path, hunt_id: str = "default",
                 max_pending_jobs: int = 1000, poll_interval: float = 0.25) -> None:
        self.store = SQLiteStateStore(hunt_dir, max_pending_jobs=max_pending_jobs)
        self.hunt_id = hunt_id
        self.max_pending_jobs = max_pending_jobs
        self.poll_interval = poll_interval
        self._closed = False

    async def put(self, payload: dict[str, Any], idempotency_key: str,
                  priority: int = 50, timeout: float | None = None) -> QueueJob:
        loop = asyncio.get_running_loop()
        deadline = None if timeout is None else loop.time() + timeout
        while True:
            if self._closed:
                raise RuntimeError("queue is closed")
            try:
                return self.store.enqueue_job(
                    self.hunt_id,
                    idempotency_key,
                    payload,
                    priority=priority,
                    max_pending_jobs=self.max_pending_jobs,
                )
            except QueueFull:
                if deadline is not None and loop.time() >= deadline:
                    raise
                await asyncio.sleep(self.poll_interval)

    async def get(self, worker_id: str, lease_seconds: float = 300,
                  timeout: float | None = None) -> QueueJob | None:
        loop = asyncio.get_running_loop()
        deadline = None if timeout is None else loop.time() + timeout
        while True:
            if self._closed:
                return None
            job = self.store.acquire_job(self.hunt_id, worker_id, lease_seconds)
            if job:
                return job
            if deadline is not None and loop.time() >= deadline:
                return None
            await asyncio.sleep(self.poll_interval)

    async def task_done(self, job_id: int, result: dict[str, Any] | None = None) -> None:
        self.store.ack_job(job_id, result)

    async def fail(self, job_id: int, error: str, retry_delay: float = 60,
                   max_attempts: int = 3) -> None:
        self.store.fail_job(job_id, error, retry_delay, max_attempts)

    async def close(self) -> None:
        self._closed = True
