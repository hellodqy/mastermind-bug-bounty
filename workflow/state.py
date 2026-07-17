"""
workflow/state.py — Hunt state persistence layer.

Manages the full lifecycle of a hunt: create, load, save, update.
State is stored as JSON on disk for cross-session continuity.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from shared.types import (
    AgentState,
    Finding,
    FindingStatus,
    HuntState,
    HuntStatus,
    PhaseName,
    Severity,
    Target,
    WorklogEntry,
)
from shared.utils import (
    append_jsonl,
    now_iso,
    read_json,
    read_jsonl,
    write_json,
)


# ---------------------------------------------------------------------------
# Hunt directory structure
# ---------------------------------------------------------------------------
# hunt-data/
#   state.json          # Full hunt state
#   worklog.jsonl       # Append-only action log
#   vault/
#     handoff_latest.md # Most recent handoff


def _default_hunt_dir() -> Path:
    return Path.cwd() / "hunt-data"


def _ensure_hunt_dir(hunt_dir: str | Path) -> Path:
    p = Path(hunt_dir)
    p.mkdir(parents=True, exist_ok=True)
    (p / "vault").mkdir(parents=True, exist_ok=True)
    return p


# ---------------------------------------------------------------------------
# State file paths
# ---------------------------------------------------------------------------

def _state_path(hunt_dir: Path) -> Path:
    return hunt_dir / "state.json"


def _worklog_path(hunt_dir: Path) -> Path:
    return hunt_dir / "worklog.jsonl"


# ---------------------------------------------------------------------------
# Create / Load / Save
# ---------------------------------------------------------------------------

def create_hunt(target_url: str, scope: list[str] | None = None,
                hunt_dir: str | Path | None = None) -> HuntState:
    """Initialize a brand-new hunt for the given target."""
    from shared.utils import hunt_id as gen_hunt_id

    state = HuntState(
        hunt_id=gen_hunt_id(),
        target=Target(url=target_url, scope=scope or [target_url]),
        created_at=now_iso(),
        updated_at=now_iso(),
    )

    if hunt_dir:
        _ensure_hunt_dir(hunt_dir)
        _persist_state(hunt_dir, state)

    return state


def load_hunt(hunt_dir: str | Path) -> HuntState | None:
    """Load an existing hunt state from disk."""
    base = _ensure_hunt_dir(hunt_dir)
    sp = _state_path(base)
    raw = read_json(sp) if sp.exists() else {}
    if not raw:
        try:
            from workflow.persistence import SQLiteStateStore
            raw = SQLiteStateStore(base).load_latest_snapshot() or {}
        except Exception:
            raw = {}
    if not raw:
        return None
    return _deserialize_state(raw)


def save_hunt(state: HuntState, hunt_dir: str | Path) -> bool:
    """Persist the hunt state to disk."""
    state.touch()
    base = _ensure_hunt_dir(hunt_dir)
    return _persist_state(base, state)


# ---------------------------------------------------------------------------
# Internal serialization
# ---------------------------------------------------------------------------

def _serialize_state(state: HuntState) -> dict:
    def _phase_value(phase) -> str:
        return phase.value if hasattr(phase, "value") else str(phase)

    return {
        "hunt_id": state.hunt_id,
        "target": {
            "url": state.target.url,
            "scope": state.target.scope,
            "tech_stack": state.target.tech_stack,
            "waf_cdn": state.target.waf_cdn,
            "endpoints_discovered": state.target.endpoints_discovered,
            "js_files": state.target.js_files,
        },
        "status": state.status.value,
        "current_phase": _phase_value(state.current_phase),
        "findings": [
            {
                "id": f.id,
                "vuln_class": f.vuln_class,
                "target_url": f.target_url,
                "severity": f.severity.value,
                "confidence": f.confidence,
                "evidence": f.evidence,
                "impact": f.impact,
                "poc_steps": f.poc_steps,
                "status": f.status.value,
                "agent_id": f.agent_id,
                "timestamp": f.timestamp,
            }
            for f in state.findings
        ],
        "completed_phases": [_phase_value(p) for p in state.completed_phases],
        "agents": {
            aid: {
                "agent_id": a.agent_id,
                "agent_type": a.agent_type,
                "task": a.task,
                "status": a.status,
                "retry_count": a.retry_count,
                "max_retries": a.max_retries,
                "last_output": a.last_output,
                "spawned_at": a.spawned_at,
                "concluded_at": a.concluded_at,
            }
            for aid, a in state.agents.items()
        },
        "custom_instructions": state.custom_instructions,
        "created_at": state.created_at,
        "updated_at": state.updated_at,
    }


def _deserialize_state(raw: dict) -> HuntState:
    target_raw = raw.get("target", {})
    target = Target(
        url=target_raw.get("url", ""),
        scope=target_raw.get("scope", []),
        tech_stack=target_raw.get("tech_stack", {}),
        waf_cdn=target_raw.get("waf_cdn", ""),
        endpoints_discovered=target_raw.get("endpoints_discovered", []),
        js_files=target_raw.get("js_files", []),
    )

    findings = [
        Finding(
            id=f["id"],
            vuln_class=f["vuln_class"],
            target_url=f["target_url"],
            severity=Severity(f["severity"]),
            confidence=f.get("confidence", 0.0),
            evidence=f.get("evidence", ""),
            impact=f.get("impact", ""),
            poc_steps=f.get("poc_steps", []),
            status=FindingStatus(f.get("status", "detected")),
            agent_id=f.get("agent_id", ""),
            timestamp=f.get("timestamp", ""),
        )
        for f in raw.get("findings", [])
    ]

    agents = {
        aid: AgentState(
            agent_id=a["agent_id"],
            agent_type=a["agent_type"],
            task=a.get("task", ""),
            status=a.get("status", "idle"),
            retry_count=a.get("retry_count", 0),
            max_retries=a.get("max_retries", 3),
            last_output=a.get("last_output", ""),
            spawned_at=a.get("spawned_at", ""),
            concluded_at=a.get("concluded_at", ""),
        )
        for aid, a in raw.get("agents", {}).items()
    }

    return HuntState(
        hunt_id=raw["hunt_id"],
        target=target,
        status=HuntStatus(raw.get("status", "active")),
        current_phase=PhaseName(raw.get("current_phase", "asset_recon")),
        findings=findings,
        completed_phases=[PhaseName(p) for p in raw.get("completed_phases", [])],
        agents=agents,
        custom_instructions=raw.get("custom_instructions", ""),
        created_at=raw.get("created_at", ""),
        updated_at=raw.get("updated_at", ""),
    )


def _persist_state(hunt_dir: Path, state: HuntState) -> bool:
    payload = _serialize_state(state)
    json_ok = write_json(_state_path(hunt_dir), payload)
    try:
        from workflow.persistence import SQLiteStateStore
        SQLiteStateStore(hunt_dir).save_snapshot(state.hunt_id, payload)
    except Exception:
        return json_ok
    return json_ok


# ---------------------------------------------------------------------------
# Worklog
# ---------------------------------------------------------------------------

def log_event(hunt_dir: str | Path, entry_type: str,
              agent_id: str, data: dict | None = None) -> WorklogEntry:
    """Record a worklog event (dual: JSONL + in-memory)."""
    entry = WorklogEntry(
        timestamp=now_iso(),
        session_id="",  # set by caller if needed
        agent_id=agent_id,
        entry_type=entry_type,
        data=data or {},
    )

    base = _ensure_hunt_dir(hunt_dir)
    append_jsonl(_worklog_path(base), {
        "timestamp": entry.timestamp,
        "agent_id": entry.agent_id,
        "entry_type": entry.entry_type,
        "data": entry.data,
    })
    try:
        from workflow.persistence import SQLiteStateStore
        state = load_hunt(base)
        hunt_id = state.hunt_id if state else ""
        SQLiteStateStore(base).record_event(hunt_id, entry_type, agent_id, entry.data)
    except Exception:
        pass
    return entry


def load_recent_worklog(hunt_dir: str | Path, minutes: int = 30) -> list[dict]:
    """Load worklog entries from the last N minutes."""
    from datetime import timedelta

    base = _ensure_hunt_dir(hunt_dir)
    entries = read_jsonl(_worklog_path(base))
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=minutes)

    recent: list[dict] = []
    for e in entries:
        ts_raw = e.get("timestamp", "")
        if not ts_raw:
            continue
        try:
            ts_raw_clean = ts_raw.replace("Z", "+00:00")
            ts = datetime.fromisoformat(ts_raw_clean)
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            if ts >= cutoff:
                recent.append(e)
        except (ValueError, TypeError):
            continue

    recent.sort(key=lambda e: e.get("timestamp", ""), reverse=True)
    return recent


# ---------------------------------------------------------------------------
# Finding helpers
# ---------------------------------------------------------------------------

def add_finding(state: HuntState, vuln_class: str, target_url: str,
                severity: str = "medium", confidence: float = 0.0,
                evidence: str = "", agent_id: str = "") -> Finding:
    """Create a new finding and append to hunt state."""
    from shared.utils import finding_id as gen_finding_id

    f = Finding(
        id=gen_finding_id(),
        vuln_class=vuln_class,
        target_url=target_url,
        severity=severity,
        confidence=confidence,
        evidence=evidence,
        agent_id=agent_id,
        timestamp=now_iso(),
    )
    state.findings.append(f)
    return f


def get_pending_findings(state: HuntState) -> list[Finding]:
    """Findings that need triage."""
    return [f for f in state.findings
            if f.status in (FindingStatus.DETECTED, FindingStatus.TRIAGE_PENDING)]


def get_approved_findings(state: HuntState) -> list[Finding]:
    """Findings that passed triage."""
    return [f for f in state.findings
            if f.status in (FindingStatus.TRIAGE_APPROVED, FindingStatus.POC_GENERATED)]
