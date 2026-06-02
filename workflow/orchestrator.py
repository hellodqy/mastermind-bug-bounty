"""
workflow/orchestrator.py — Orchestrator v3.1

Drives the pipeline phases. Handles phase dependencies and gate blocking.
When a gate fails, the phase is NOT marked complete and pipeline halts.
"""

from pathlib import Path
from workflow.executor import TaskExecutor
from workflow.pipeline import PIPELINE, get_next_phase
from workflow.state import create_hunt, load_hunt, save_hunt, log_event
from workflow.hooks import context, handoff


class Orchestrator:
    """Orchestrates the pipeline with gate-aware phase transitions."""

    def __init__(self, hunt_dir: str | Path = "./hunt-data"):
        self.hunt_dir = Path(hunt_dir)
        self.state = None

    def run(self, target_url: str, scope: list[str] | None = None):
        existing = load_hunt(self.hunt_dir)
        if existing:
            self.state = existing
            print(context.inject_context(self.hunt_dir))
        else:
            self.state = create_hunt(target_url, scope, hunt_dir=self.hunt_dir)
            print(context.inject_context(self.hunt_dir, target_url))

        save_hunt(self.state, self.hunt_dir)
        log_event(self.hunt_dir, "session_start", "orchestrator", {"target": target_url})

        halted = False
        halted_reason = ""

        for phase in PIPELINE:
            if halted:
                print(f"\n  [HALTED] Pipeline stopped before {phase.name.upper()} — {halted_reason}")
                break

            print(f"\n{'='*60}")
            print(f"PHASE: {phase.name.upper()} — {phase.description}")
            print(f"{'='*60}")

            # Check dependencies
            dep_missing = False
            for dep in phase.depends_on:
                if dep not in self.state.completed_phases:
                    print(f"  [!] Dependency '{dep}' not done. Skipping.")
                    dep_missing = True
                    break
            if dep_missing:
                continue

            if phase.name in self.state.completed_phases:
                print(f"  Already completed.")
                continue

            executor = TaskExecutor(self.hunt_dir, self.state.target.url)
            result = executor.run_phase(phase.name)

            # --- Check gates before marking complete ---
            gate_blocked = False
            for gate in result.gate_results:
                if gate.block:
                    gate_blocked = True
                    halted = True
                    halted_reason = f"Gate '{gate.gate_name}' blocked: {gate.summary[:120]}"
                    print(f"\n  *** GATE BLOCKED ***")
                    print(f"  Gate: {gate.gate_name}")
                    print(f"  {gate.summary}")
                    print(f"  Fix the issues above and re-run before proceeding.")

            if gate_blocked:
                save_hunt(self.state, self.hunt_dir)
                continue

            if result.completed:
                self.state.completed_phases.append(phase.name)
                print(f"\n  [OK] {phase.name.upper()} complete")
            else:
                print(f"\n  [WARN] {phase.name.upper()} has {result.tasks_fail} failures")

            save_hunt(self.state, self.hunt_dir)

        handoff_path = handoff.save(self.hunt_dir, self.state)
        print(f"\n[OK] Pipeline done. Handoff: {handoff_path}")
        return self.state
