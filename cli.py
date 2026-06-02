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
    print(f"Phases completed: {[p.value for p in state.completed_phases]}")
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
    print(f"Current phase: {state.current_phase.value}")
    print(f"Completed phases: {[p.value for p in state.completed_phases]}")

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
    print(f"Phase:       {state.current_phase.value}")
    print(f"Completed:   {[p.value for p in state.completed_phases] or 'None'}")
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
        if phase.depends_on:
            print(f"   Depends on: {[str(d) for d in phase.depends_on]}")
    return 0


# ---------------------------------------------------------------------------
# CLI setup
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="mastermind",
        description="Mastermind Bug Bounty — Autonomous Offensive Security Orchestration",
    )
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
    elif args.command == "phases":
        return cmd_list_phases(args)
    else:
        parser.print_help()
        return 0


if __name__ == "__main__":
    sys.exit(main())
