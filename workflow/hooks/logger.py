"""
workflow/hooks/logger.py — Hook 4: Worklog Recorder

Trigger: After every tool call, agent action, finding, or error.
Dual-channel: JSONL (machine) + Obsidian markdown (human).
Pattern: WRITE-ONLY — never blocks execution.
"""

from __future__ import annotations

from pathlib import Path

from shared.types import Finding, WorklogEntry
from shared.utils import append_jsonl, now_iso


def record_tool_call(hunt_dir: str | Path, tool_name: str,
                     agent_id: str, target: str = "",
                     inputs: dict | None = None,
                     outputs: dict | None = None) -> dict:
    """Log a tool invocation to the worklog."""
    entry = {
        "timestamp": now_iso(),
        "agent_id": agent_id,
        "entry_type": "tool_call",
        "data": {
            "tool_name": tool_name,
            "target": target,
            "inputs": inputs or {},
            "outputs": outputs or {},
        },
    }
    _persist(hunt_dir, entry)
    return entry


def record_finding(hunt_dir: str | Path, finding: Finding,
                   agent_id: str) -> dict:
    """Log a vulnerability finding to the worklog."""
    entry = {
        "timestamp": now_iso(),
        "agent_id": agent_id,
        "entry_type": "finding",
        "data": {
            "finding_id": finding.id,
            "vuln_class": finding.vuln_class,
            "target_url": finding.target_url,
            "severity": finding.severity.value,
            "confidence": finding.confidence,
            "evidence": finding.evidence[:200],
            "status": finding.status.value,
        },
    }
    _persist(hunt_dir, entry)
    return entry


def record_agent_spawn(hunt_dir: str | Path, agent_id: str,
                       agent_type: str, task: str) -> dict:
    """Log agent creation."""
    entry = {
        "timestamp": now_iso(),
        "agent_id": agent_id,
        "entry_type": "agent_spawn",
        "data": {
            "agent_type": agent_type,
            "task": task,
        },
    }
    _persist(hunt_dir, entry)
    return entry


def record_agent_conclusion(hunt_dir: str | Path, agent_id: str,
                            success: bool, summary: str) -> dict:
    """Log agent completion."""
    entry = {
        "timestamp": now_iso(),
        "agent_id": agent_id,
        "entry_type": "agent_conclusion",
        "data": {
            "success": success,
            "summary": summary[:500],
        },
    }
    _persist(hunt_dir, entry)
    return entry


def record_error(hunt_dir: str | Path, agent_id: str,
                 error: str) -> dict:
    """Log an error."""
    entry = {
        "timestamp": now_iso(),
        "agent_id": agent_id,
        "entry_type": "error",
        "data": {"error": error[:500]},
    }
    _persist(hunt_dir, entry)
    return entry


def record_phase(hunt_dir: str | Path, phase: str,
                 status: str, agent_id: str = "orchestrator") -> dict:
    """Log phase transition."""
    entry = {
        "timestamp": now_iso(),
        "agent_id": agent_id,
        "entry_type": "phase_transition",
        "data": {"phase": phase, "status": status},
    }
    _persist(hunt_dir, entry)
    return entry


# ---------------------------------------------------------------------------
# Internal
# ---------------------------------------------------------------------------

def _persist(hunt_dir: str | Path, entry: dict) -> None:
    """Append to JSONL worklog."""
    base = Path(hunt_dir)
    base.mkdir(parents=True, exist_ok=True)
    append_jsonl(base / "worklog.jsonl", entry)
