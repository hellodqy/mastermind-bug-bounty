#!/usr/bin/env python3
"""
cli.py — Mastermind Bug Bounty unified CLI.

One-command full-auto bug bounty pipeline:
    python cli.py run --target https://example.com
    python cli.py resume --hunt-dir ./hunt-data
    python cli.py status --hunt-dir ./hunt-data

Zero external dependencies. Pure Python stdlib.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Ensure the package root is on sys.path
_PKG_ROOT = Path(__file__).resolve().parent
if str(_PKG_ROOT) not in sys.path:
    sys.path.insert(0, str(_PKG_ROOT))


def _phase_value(phase) -> str:
    return phase.value if hasattr(phase, "value") else str(phase)


def _load_store_stats(hunt_dir: str) -> dict:
    try:
        from workflow.persistence import SQLiteStateStore
        return SQLiteStateStore(hunt_dir).stats()
    except Exception:
        return {"snapshots": 0, "queue": {}, "events": {}}


def _phase_progress(completed: list[str], current: str) -> str:
    phases = [
        "asset_recon",
        "attack_surface_analysis",
        "autonomous_attack",
        "report_generation",
    ]
    completed_set = set(completed)
    marks = []
    for phase in phases:
        if phase in completed_set:
            marks.append(f"{phase}:done")
        elif phase == current:
            marks.append(f"{phase}:current")
        else:
            marks.append(f"{phase}:pending")
    return " | ".join(marks)


def cmd_run(args: argparse.Namespace) -> int:
    """Execute the full bug bounty pipeline against a target."""
    from workflow.orchestrator import Orchestrator

    print(f"\n{'='*60}")
    print(f"MASTERMIND BUG BOUNTY")
    print(f"Target: {args.target}")
    print(f"Hunt Dir: {args.hunt_dir}")
    print(f"Depth: {args.depth}")
    print(f"{'='*60}\n")

    orch = Orchestrator(hunt_dir=args.hunt_dir)
    state = orch.run(args.target, scope=args.scope)

    # Summary
    print(f"\n{'='*60}")
    print(f"HUNT SUMMARY")
    print(f"{'='*60}")
    print(f"Hunt ID: {state.hunt_id}")
    print(f"Target: {state.target.url}")
    print(f"Status: {state.status.value}")
    print(f"Phases completed: {[_phase_value(p) for p in state.completed_phases]}")
    print(f"Total findings: {len(state.findings)}")

    approved = [f for f in state.findings
                if f.status.value == "triage_approved"]
    if approved:
        print(f"\nApproved Findings ({len(approved)}):")
        for f in approved:
            print(f"  [{f.severity.upper()}] {f.vuln_class} @ {f.target_url}")

    pending = [f for f in state.findings
               if f.status.value in ("detected", "triage_pending")]
    if pending:
        print(f"\nPending Findings ({len(pending)}):")
        for f in pending:
            print(f"  [{f.severity.upper()}] {f.vuln_class} @ {f.target_url}")

    print(f"\nWorklog: {args.hunt_dir}/worklog.jsonl")
    print(f"Handoff: {args.hunt_dir}/vault/handoff_latest.md")

    return 0


def cmd_resume(args: argparse.Namespace) -> int:
    """Resume an existing hunt from its hunt directory."""
    from workflow.orchestrator import Orchestrator
    from workflow.state import load_hunt

    state = load_hunt(args.hunt_dir)
    if state is None:
        print(f"[ERROR] No hunt found in {args.hunt_dir}")
        print("Use 'python cli.py run --target <URL>' to start a new hunt.")
        return 1

    print(f"\nResuming hunt: {state.hunt_id}")
    print(f"Target: {state.target.url}")
    print(f"Current phase: {_phase_value(state.current_phase)}")
    print(f"Completed phases: {[_phase_value(p) for p in state.completed_phases]}")
    print(f"Recovery source: {Path(args.hunt_dir) / 'state.json'} or hunt.db snapshot")

    orch = Orchestrator(hunt_dir=args.hunt_dir)
    state = orch.run(state.target.url, scope=state.target.scope)
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    """Show the status of an existing hunt."""
    from workflow.state import load_hunt, load_recent_worklog

    state = load_hunt(args.hunt_dir)
    if state is None:
        print(f"[ERROR] No hunt found in {args.hunt_dir}")
        return 1

    print(f"\n{'='*60}")
    print(f"HUNT STATUS: {state.hunt_id}")
    print(f"{'='*60}")
    print(f"Target:      {state.target.url}")
    print(f"Scope:       {', '.join(state.target.scope)}")
    print(f"Status:      {state.status.value}")
    print(f"Phase:       {_phase_value(state.current_phase)}")
    completed = [_phase_value(p) for p in state.completed_phases]
    print(f"Progress:    {_phase_progress(completed, _phase_value(state.current_phase))}")
    print(f"Completed:   {completed or 'None'}")
    print(f"Findings:    {len(state.findings)} total")
    print(f"  Approved:  {sum(1 for f in state.findings if f.status.value == 'triage_approved')}")
    print(f"  Pending:   {sum(1 for f in state.findings if f.status.value in ('detected', 'triage_pending'))}")
    print(f"  Rejected:  {sum(1 for f in state.findings if f.status.value == 'triage_rejected')}")
    print(f"Agents:      {len(state.agents)}")
    for a in state.agents.values():
        print(f"  - {a.agent_id}: {a.status} ({a.agent_type})")
    print(f"Endpoints:   {len(state.target.endpoints_discovered)}")
    print(f"JS Files:    {len(state.target.js_files)}")
    print(f"Tech Stack:  {state.target.tech_stack or 'Not fingerprinted'}")
    print(f"WAF/CDN:     {state.target.waf_cdn or 'Unknown'}")
    print(f"Created:     {state.created_at[:19] if state.created_at else 'N/A'}")
    print(f"Updated:     {state.updated_at[:19] if state.updated_at else 'N/A'}")
    stats = _load_store_stats(args.hunt_dir)
    queue = stats.get("queue", {})
    print(f"Snapshots:   {stats.get('snapshots', 0)}")
    print(f"Queue:       queued={queue.get('queued', 0)} leased={queue.get('leased', 0)} done={queue.get('done', 0)} failed={queue.get('failed', 0)}")

    recent = load_recent_worklog(args.hunt_dir, minutes=30)
    if recent:
        print(f"\nRecent Activity ({len(recent)} entries, last 30 min):")
        for e in recent[:5]:
            ts = e.get("timestamp", "")[:19]
            et = e.get("entry_type", "?")
            agent = e.get("agent_id", "?")
            print(f"  {ts} [{et}] {agent}")

    return 0


def cmd_list_phases(_args: argparse.Namespace) -> int:
    """List all pipeline phases."""
    from workflow.pipeline import PIPELINE

    print(f"\n{'='*60}")
    print("PIPELINE PHASES")
    print(f"{'='*60}")
    for i, phase in enumerate(PIPELINE):
        marker = " (optional)" if phase.optional else ""
        print(f"\n{i+1}. {str(phase.name).upper()}{marker}")
        print(f"   Agent: {phase.agent}")
        print(f"   Skills: {phase.skills or 'none'}")
        print(f"   {phase.description}")
        if getattr(phase, "ai_directive", ""):
            print(f"   AI Directive: {phase.ai_directive}")
        if phase.depends_on:
            print(f"   Depends on: {[str(d) for d in phase.depends_on]}")
    return 0


def cmd_stats(args: argparse.Namespace) -> int:
    """Show aggregate hunt and persistence statistics."""
    from workflow.state import load_hunt

    state = load_hunt(args.hunt_dir)
    if state is None:
        print(f"[ERROR] No hunt found in {args.hunt_dir}")
        return 1

    store_stats = _load_store_stats(args.hunt_dir)
    completed = [_phase_value(p) for p in state.completed_phases]
    severities: dict[str, int] = {}
    statuses: dict[str, int] = {}
    for finding in state.findings:
        severities[finding.severity.value] = severities.get(finding.severity.value, 0) + 1
        statuses[finding.status.value] = statuses.get(finding.status.value, 0) + 1

    print(f"\n{'='*60}")
    print(f"HUNT STATS: {state.hunt_id}")
    print(f"{'='*60}")
    print(f"Target:      {state.target.url}")
    print(f"Progress:    {_phase_progress(completed, _phase_value(state.current_phase))}")
    print(f"Findings:    {len(state.findings)} total")
    print(f"By severity: {severities or {}}")
    print(f"By status:   {statuses or {}}")
    print(f"Endpoints:   {len(state.target.endpoints_discovered)}")
    print(f"JS files:    {len(state.target.js_files)}")
    print(f"Snapshots:   {store_stats.get('snapshots', 0)}")
    print(f"Queue:       {store_stats.get('queue', {})}")
    print(f"Events:      {store_stats.get('events', {})}")
    return 0


def cmd_history(args: argparse.Namespace) -> int:
    """Show recent worklog entries."""
    from workflow.state import load_recent_worklog

    recent = load_recent_worklog(args.hunt_dir, minutes=args.minutes)
    if not recent:
        print(f"No worklog entries in the last {args.minutes} minutes.")
        return 0
    print(f"\nRecent Activity ({len(recent)} entries, last {args.minutes} min):")
    for e in recent[:args.limit]:
        ts = e.get("timestamp", "")[:19]
        et = e.get("entry_type", "?")
        agent = e.get("agent_id", "?")
        print(f"  {ts} [{et}] {agent} {e.get('data', {})}")
    return 0


# ---------------------------------------------------------------------------
# CLI setup
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    from workflow.version import package_version

    parser = argparse.ArgumentParser(
        prog="mastermind",
        description="Mastermind Bug Bounty — Autonomous Offensive Security Orchestration",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {package_version()}")
    sub = parser.add_subparsers(dest="command", help="Available commands")

    # run
    p_run = sub.add_parser("run", help="Start a new hunt against a target")
    p_run.add_argument("--target", "-t", required=True,
                       help="Target URL to test")
    p_run.add_argument("--scope", "-s", nargs="*",
                       help="Scope URLs/domains (default: derived from target)")
    p_run.add_argument("--hunt-dir", "-d", default="./hunt-data",
                       help="Hunt data directory (default: ./hunt-data)")
    p_run.add_argument("--depth", choices=["standard", "aggressive", "stealth"],
                       default="standard", help="Hunt depth (default: standard)")

    # resume
    p_resume = sub.add_parser("resume", help="Resume an existing hunt")
    p_resume.add_argument("--hunt-dir", "-d", default="./hunt-data",
                          help="Hunt data directory (default: ./hunt-data)")

    # status
    p_status = sub.add_parser("status", help="Show hunt status")
    p_status.add_argument("--hunt-dir", "-d", default="./hunt-data",
                          help="Hunt data directory (default: ./hunt-data)")

    # stats
    p_stats = sub.add_parser("stats", help="Show hunt statistics")
    p_stats.add_argument("--hunt-dir", "-d", default="./hunt-data",
                         help="Hunt data directory (default: ./hunt-data)")

    # history
    p_history = sub.add_parser("history", help="Show recent worklog activity")
    p_history.add_argument("--hunt-dir", "-d", default="./hunt-data",
                           help="Hunt data directory (default: ./hunt-data)")
    p_history.add_argument("--minutes", "-m", type=int, default=30,
                           help="Lookback window in minutes (default: 30)")
    p_history.add_argument("--limit", "-n", type=int, default=20,
                           help="Maximum entries to show (default: 20)")

    # phases
    sub.add_parser("phases", help="List all pipeline phases")

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "run":
        return cmd_run(args)
    elif args.command == "resume":
        return cmd_resume(args)
    elif args.command == "status":
        return cmd_status(args)
    elif args.command == "stats":
        return cmd_stats(args)
    elif args.command == "history":
        return cmd_history(args)
    elif args.command == "phases":
        return cmd_list_phases(args)
    else:
        parser.print_help()
        return 0


if __name__ == "__main__":
    sys.exit(main())
