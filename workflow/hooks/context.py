"""
workflow/hooks/context.py — Hook 1: Context Injector

Trigger: Session start / resume.
Loads hunt state + recent worklog + previous handoff,
formats as structured context for AI consumption.
"""

from __future__ import annotations

from pathlib import Path

from shared.types import HuntState
from shared.utils import now_iso, read_text
from workflow.state import load_hunt, load_recent_worklog


def _phase_value(phase) -> str:
    return phase.value if hasattr(phase, "value") else str(phase)


def inject_context(hunt_dir: str | Path, target_url: str | None = None) -> str:
    """Compose the full session context for AI consumption.

    Args:
        hunt_dir: Path to hunt-data directory.
        target_url: If provided, creates a new hunt; otherwise loads existing.

    Returns:
        Formatted markdown string suitable for injection into system prompt.
    """
    from workflow.state import create_hunt

    state = load_hunt(hunt_dir)

    # New hunt
    if state is None and target_url:
        state = create_hunt(target_url, hunt_dir=hunt_dir)
        is_resume = False
    elif state is not None:
        is_resume = True
    else:
        return _format_error("No existing hunt found and no target provided.")

    recent = load_recent_worklog(hunt_dir, minutes=30)
    handoff_content = _load_handoff(hunt_dir)

    return _format_context(state, recent, handoff_content, is_resume)


def _load_handoff(hunt_dir: str | Path) -> str:
    """Load the most recent handoff document."""
    vault = Path(hunt_dir) / "vault"
    latest = vault / "handoff_latest.md"
    if latest.exists():
        return read_text(latest)

    # Fallback: find most recent timestamped handoff
    if vault.is_dir():
        handoffs = sorted(vault.glob("handoff_*.md"), reverse=True)
        if handoffs:
            return read_text(handoffs[0])
    return ""


def _format_context(state: HuntState, recent_worklog: list[dict],
                    handoff: str, is_resume: bool) -> str:
    """Format hunt state as structured markdown context block."""

    meta = state.target
    agents_active = [a for a in state.agents.values()
                     if a.status in ("active", "working")]
    findings_approved = [f for f in state.findings
                         if f.status.value in ("triage_approved", "poc_generated")]
    findings_pending = [f for f in state.findings
                        if f.status.value in ("detected", "triage_pending")]

    lines = [
        "=" * 60,
        f"MASTERMIND BUG BOUNTY — {'Session Resume' if is_resume else 'New Hunt'}",
        f"Session Start: {now_iso()}",
        f"Hunt ID: {state.hunt_id}",
        "=" * 60,
        "",
        "## Target",
        f"- **URL**: {meta.url}",
        f"- **Scope**: {', '.join(meta.scope) if meta.scope else 'N/A'}",
        f"- **WAF/CDN**: {meta.waf_cdn or 'Not yet identified'}",
        f"- **Tech Stack**: {_fmt_tech(meta.tech_stack)}",
        f"- **Endpoints Discovered**: {len(meta.endpoints_discovered)}",
        f"- **JS Files Collected**: {len(meta.js_files)}",
        "",
        "## Hunt Progress",
        f"- **Status**: {state.status.value}",
        f"- **Current Phase**: {_phase_value(state.current_phase)}",
        f"- **Completed Phases**: {[_phase_value(p) for p in state.completed_phases] or 'None yet'}",
        "",
    ]

    # Active agents
    if agents_active:
        lines.append("## Active Agents")
        for a in agents_active:
            lines.append(f"- **{a.agent_id}** ({a.agent_type}): {a.status} — {a.task[:80]}")
        lines.append("")

    # Approved findings
    if findings_approved:
        lines.append(f"## Approved Findings ({len(findings_approved)})")
        for f in findings_approved:
            lines.append(f"- [{f.severity.upper()}] {f.vuln_class} @ {f.target_url} "
                         f"(confidence: {f.confidence:.0%})")
        lines.append("")

    # Pending findings
    if findings_pending:
        lines.append(f"## Pending Findings ({len(findings_pending)})")
        for f in findings_pending:
            lines.append(f"- [{f.severity.upper()}] {f.vuln_class} @ {f.target_url} "
                         f"(confidence: {f.confidence:.0%})")
        lines.append("")

    # Recent activity
    if recent_worklog:
        lines.append(f"## Recent Activity (last 30 min, {len(recent_worklog)} entries)")
        for e in recent_worklog[:5]:
            ts = e.get("timestamp", "")[:19]
            et = e.get("entry_type", "?")
            agent = e.get("agent_id", "?")
            lines.append(f"- `{ts}` [{et}] {agent}")
        lines.append("")

    # Handoff
    if handoff:
        lines.append("## Previous Session Handoff")
        lines.append(handoff[:600])
        if len(handoff) > 600:
            lines.append("...(truncated)")
        lines.append("")

    # Next phase hint
    lines.append("## Next Action")
    lines.append(f"Continue with phase: **{_phase_value(state.current_phase)}**")
    lines.append("")
    lines.append("=" * 60)
    lines.append("End of Session Context")
    lines.append("=" * 60)

    return "\n".join(lines)


def _fmt_tech(tech: dict) -> str:
    if not tech:
        return "Not yet fingerprinted"
    return ", ".join(f"{k}: {v}" for k, v in tech.items())


def _format_error(msg: str) -> str:
    return f"[CONTEXT INJECTOR ERROR] {msg}"
