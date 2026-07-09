"""
workflow/hooks/handoff.py — Hook 6: Handoff Saver

Trigger: Session end / compaction.
Serializes full hunt state as an Obsidian-compatible markdown document
for cross-session continuity.
Pattern: WRITE-ONLY.
"""

from __future__ import annotations

from pathlib import Path

from shared.types import AgentState, Finding, HuntState
from shared.utils import now_iso, write_json


def _phase_value(phase) -> str:
    return phase.value if hasattr(phase, "value") else str(phase)


def save(hunt_dir: str | Path, state: HuntState,
         custom_instructions: str = "") -> str:
    """Serialize full hunt state and save as handoff document.

    Args:
        hunt_dir: Path to hunt-data directory.
        state: Current HuntState.
        custom_instructions: Optional user notes for next session.

    Returns:
        Path to the saved handoff file.
    """
    base = Path(hunt_dir)
    vault = base / "vault"
    vault.mkdir(parents=True, exist_ok=True)

    document = _build_document(state, custom_instructions)

    # Save timestamped handoff
    ts_slug = now_iso().replace(":", "-")[:19]
    path = vault / f"handoff_{ts_slug}.md"
    path.write_text(document, encoding="utf-8")

    # Update latest symlink/copy
    latest = vault / "handoff_latest.md"
    try:
        if latest.exists() or latest.is_symlink():
            latest.unlink()
        latest.symlink_to(path.name)
    except OSError:
        import shutil
        shutil.copy2(str(path), str(latest))

    return str(path)


def _build_document(state: HuntState, custom: str) -> str:
    """Build the handoff markdown document."""
    meta = state.target

    lines = [
        "---",
        f"session_date: {now_iso()}",
        f"hunt_id: {state.hunt_id}",
        f"target: {meta.url}",
        f"status: {state.status.value}",
        f"current_phase: {_phase_value(state.current_phase)}",
        f"findings_total: {len(state.findings)}",
        "---",
        "",
        f"# Hunt Handoff — {meta.url}",
        f"*Generated: {now_iso()}*",
        "",
        "## Executive Summary",
        "",
        f"- **Target**: {meta.url}",
        f"- **Scope**: {', '.join(meta.scope) if meta.scope else 'N/A'}",
        f"- **Status**: {state.status.value}",
        f"- **Current Phase**: {_phase_value(state.current_phase)}",
        f"- **Completed Phases**: {[_phase_value(p) for p in state.completed_phases] or 'None'}",
        f"- **WAF/CDN**: {meta.waf_cdn or 'Not yet identified'}",
        f"- **Tech Stack**: {_fmt_tech(meta.tech_stack)}",
        f"- **Endpoints Discovered**: {len(meta.endpoints_discovered)}",
        f"- **Total Findings**: {len(state.findings)}",
        f"- **Active Agents**: {sum(1 for a in state.agents.values() if a.status in ('active', 'working'))}",
        "",
    ]

    # Targets
    lines.append("## Target State")
    lines.append("")
    lines.append(f"- **URL**: {meta.url}")
    lines.append(f"- **Discovered Endpoints** ({len(meta.endpoints_discovered)}):")
    for ep in meta.endpoints_discovered[:20]:
        lines.append(f"  - `{ep}`")
    if len(meta.endpoints_discovered) > 20:
        lines.append(f"  - ... and {len(meta.endpoints_discovered) - 20} more")
    lines.append(f"- **JS Files** ({len(meta.js_files)}):")
    for js in meta.js_files[:10]:
        lines.append(f"  - `{js}`")
    lines.append("")

    # Findings
    approved = [f for f in state.findings
                if f.status.value in ("triage_approved", "poc_generated")]
    pending = [f for f in state.findings
               if f.status.value in ("detected", "triage_pending")]
    rejected = [f for f in state.findings
                if f.status.value == "triage_rejected"]

    if approved:
        lines.append(f"## Approved Findings ({len(approved)})")
        lines.append("")
        lines.append("| ID | Class | Target | Severity | Confidence |")
        lines.append("|----|-------|--------|----------|------------|")
        for f in approved:
            lines.append(
                f"| {f.id} | {f.vuln_class} | {f.target_url[:40]} | "
                f"{f.severity.upper()} | {f.confidence:.0%} |"
            )
        lines.append("")

    if pending:
        lines.append(f"## Pending Findings ({len(pending)})")
        lines.append("")
        for f in pending:
            lines.append(f"### [{f.id}] {f.vuln_class} @ {f.target_url}")
            lines.append(f"- **Severity**: {f.severity.upper()}")
            lines.append(f"- **Confidence**: {f.confidence:.0%}")
            lines.append(f"- **Evidence**: {f.evidence[:120]}")
            lines.append("")

    if rejected:
        lines.append(f"## Rejected Findings ({len(rejected)})")
        lines.append("")
        for f in rejected:
            lines.append(f"- [{f.id}] {f.vuln_class} @ {f.target_url} "
                         f"(confidence: {f.confidence:.0%})")
        lines.append("")

    # Agents
    if state.agents:
        lines.append("## Agent Status")
        lines.append("")
        lines.append("| Agent | Type | Status | Retries | Task |")
        lines.append("|-------|------|--------|---------|------|")
        for a in state.agents.values():
            lines.append(
                f"| {a.agent_id} | {a.agent_type} | {a.status} | "
                f"{a.retry_count}/{a.max_retries} | {a.task[:40]} |"
            )
        lines.append("")

    # Next steps
    lines.append("## Next Steps (Priority Order)")
    lines.append("")
    if approved:
        lines.append("- [ ] Generate POC chain for approved findings")
        lines.append("- [ ] Draft HackerOne reports")
    if pending:
        lines.append("- [ ] Complete triage for pending findings")
        lines.append("- [ ] Retry failed agents with bypass strategies")
    lines.append(f"- [ ] Continue from phase: **{_phase_value(state.current_phase)}**")
    lines.append("- [ ] Rotate to untested endpoints")
    lines.append("")

    # Custom instructions
    if custom:
        lines.append("## Custom Instructions")
        lines.append("")
        lines.append(f"> {custom}")
        lines.append("")

    return "\n".join(lines)


def _fmt_tech(tech: dict) -> str:
    if not tech:
        return "N/A"
    return ", ".join(f"{k}: {v}" for k, v in tech.items())
