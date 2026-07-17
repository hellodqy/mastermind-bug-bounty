"""
SQLite-backed persistence primitives for hunts and durable jobs.

JSON files remain the compatibility surface. SQLite provides stable snapshots,
events, and an idempotent queue with leases for resumable work.
"""

from __future__ import annotations

import json
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from shared.utils import now_iso


@dataclass(frozen=True)
class QueueJob:
    job_id: int
    hunt_id: str
    idempotency_key: str
    payload: dict[str, Any]
    priority: int
    state: str
    attempts: int
    available_at: float
    lease_until: float


class QueueFull(RuntimeError):
    pass


class SQLiteStateStore:
    def __init__(self, hunt_dir: str | Path, max_pending_jobs: int = 1000) -> None:
        self.hunt_dir = Path(hunt_dir)
        self.hunt_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = self.hunt_dir / "hunt.db"
        self.max_pending_jobs = max_pending_jobs
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=10, isolation_level=None)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=5000")
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS snapshots (
                    hunt_id TEXT PRIMARY KEY,
                    payload TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    hunt_id TEXT,
                    ts TEXT NOT NULL,
                    agent_id TEXT,
                    entry_type TEXT NOT NULL,
                    payload TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS queue_jobs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    hunt_id TEXT NOT NULL,
                    idempotency_key TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    priority INTEGER NOT NULL DEFAULT 50,
                    state TEXT NOT NULL DEFAULT 'queued',
                    attempts INTEGER NOT NULL DEFAULT 0,
                    available_at REAL NOT NULL DEFAULT 0,
                    lease_until REAL NOT NULL DEFAULT 0,
                    result TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    UNIQUE(hunt_id, idempotency_key)
                );
                CREATE INDEX IF NOT EXISTS idx_queue_ready
                ON queue_jobs(hunt_id, state, available_at, priority, id);
                """
            )

    def save_snapshot(self, hunt_id: str, payload: dict[str, Any]) -> None:
        encoded = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO snapshots(hunt_id, payload, updated_at)
                VALUES(?, ?, ?)
                ON CONFLICT(hunt_id) DO UPDATE SET
                    payload=excluded.payload,
                    updated_at=excluded.updated_at
                """,
                (hunt_id, encoded, now_iso()),
            )

    def load_latest_snapshot(self) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT payload FROM snapshots ORDER BY updated_at DESC LIMIT 1"
            ).fetchone()
        if not row:
            return None
        return json.loads(row["payload"])

    def record_event(self, hunt_id: str, entry_type: str, agent_id: str,
                     payload: dict[str, Any]) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO events(hunt_id, ts, agent_id, entry_type, payload) VALUES(?, ?, ?, ?, ?)",
                (hunt_id, now_iso(), agent_id, entry_type,
                 json.dumps(payload, ensure_ascii=False, separators=(",", ":"))),
            )

    def enqueue_job(self, hunt_id: str, idempotency_key: str, payload: dict[str, Any],
                    priority: int = 50, delay_seconds: float = 0,
                    max_pending_jobs: int | None = None) -> QueueJob:
        limit = self.max_pending_jobs if max_pending_jobs is None else max_pending_jobs
        now = time.time()
        encoded = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        with self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            pending = conn.execute(
                "SELECT COUNT(*) AS n FROM queue_jobs WHERE hunt_id=? AND state IN ('queued','leased')",
                (hunt_id,),
            ).fetchone()["n"]
            existing = conn.execute(
                "SELECT * FROM queue_jobs WHERE hunt_id=? AND idempotency_key=?",
                (hunt_id, idempotency_key),
            ).fetchone()
            if existing:
                conn.execute("COMMIT")
                return _job_from_row(existing)
            if pending >= limit:
                conn.execute("ROLLBACK")
                raise QueueFull(f"Queue backpressure: {pending} pending jobs >= {limit}")
            cur = conn.execute(
                """
                INSERT INTO queue_jobs(
                    hunt_id, idempotency_key, payload, priority, state,
                    available_at, created_at, updated_at
                ) VALUES(?, ?, ?, ?, 'queued', ?, ?, ?)
                """,
                (hunt_id, idempotency_key, encoded, priority, now + delay_seconds, now_iso(), now_iso()),
            )
            row = conn.execute("SELECT * FROM queue_jobs WHERE id=?", (cur.lastrowid,)).fetchone()
            conn.execute("COMMIT")
        return _job_from_row(row)

    def acquire_job(self, hunt_id: str, worker_id: str,
                    lease_seconds: float = 300) -> QueueJob | None:
        now = time.time()
        with self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute(
                """
                SELECT * FROM queue_jobs
                WHERE hunt_id=?
                  AND (
                    (state='queued' AND available_at <= ?)
                    OR (state='leased' AND lease_until <= ?)
                  )
                ORDER BY priority ASC, available_at ASC, id ASC
                LIMIT 1
                """,
                (hunt_id, now, now),
            ).fetchone()
            if not row:
                conn.execute("COMMIT")
                return None
            conn.execute(
                """
                UPDATE queue_jobs
                SET state='leased', attempts=attempts+1, lease_until=?, updated_at=?
                WHERE id=?
                """,
                (now + lease_seconds, now_iso(), row["id"]),
            )
            leased = conn.execute("SELECT * FROM queue_jobs WHERE id=?", (row["id"],)).fetchone()
            conn.execute("COMMIT")
        return _job_from_row(leased)

    def ack_job(self, job_id: int, result: dict[str, Any] | None = None) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE queue_jobs
                SET state='done', lease_until=0, result=?, updated_at=?
                WHERE id=? AND state!='done'
                """,
                (json.dumps(result or {}, ensure_ascii=False, separators=(",", ":")), now_iso(), job_id),
            )

    def fail_job(self, job_id: int, error: str, retry_delay: float = 60,
                 max_attempts: int = 3) -> None:
        now = time.time()
        with self._connect() as conn:
            row = conn.execute("SELECT attempts FROM queue_jobs WHERE id=?", (job_id,)).fetchone()
            if not row:
                return
            state = "failed" if row["attempts"] >= max_attempts else "queued"
            conn.execute(
                """
                UPDATE queue_jobs
                SET state=?, lease_until=0, available_at=?, result=?, updated_at=?
                WHERE id=?
                """,
                (state, now + retry_delay,
                 json.dumps({"error": error}, ensure_ascii=False, separators=(",", ":")),
                 now_iso(), job_id),
            )

    def stats(self) -> dict[str, Any]:
        with self._connect() as conn:
            queue_rows = conn.execute(
                "SELECT state, COUNT(*) AS n FROM queue_jobs GROUP BY state"
            ).fetchall()
            event_rows = conn.execute(
                "SELECT entry_type, COUNT(*) AS n FROM events GROUP BY entry_type"
            ).fetchall()
            snapshots = conn.execute("SELECT COUNT(*) AS n FROM snapshots").fetchone()["n"]
        return {
            "snapshots": snapshots,
            "queue": {row["state"]: row["n"] for row in queue_rows},
            "events": {row["entry_type"]: row["n"] for row in event_rows},
        }


def _job_from_row(row: sqlite3.Row) -> QueueJob:
    return QueueJob(
        job_id=row["id"],
        hunt_id=row["hunt_id"],
        idempotency_key=row["idempotency_key"],
        payload=json.loads(row["payload"]),
        priority=row["priority"],
        state=row["state"],
        attempts=row["attempts"],
        available_at=row["available_at"],
        lease_until=row["lease_until"],
    )
