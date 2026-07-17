"""
workflow/executor.py — Executor v3.1

Drives the pipeline. Each step prints instructions for the Agent.
The Agent reads step.instruction, executes it, writes output to step.output_file.

Key improvements over v3.0:
1. _run_step verifies output_file exists before returning "ok"
2. run_phase runs Phase Gates (JS analysis completeness, Pair completeness)
3. Gate failures are reported to orchestrator for blocking decisions
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from pathlib import Path

from workflow.tasks import Task, TaskStep, get_tasks_for_phase, count_all_steps
from workflow.tools import ToolContext, default_registry


@dataclass
class StepResult:
    step: int
    tool: str
    status: str  # "ok" | "failed" | "skipped"
    output: str = ""


@dataclass
class TaskResult:
    task_id: str
    passed: bool
    step_results: list[StepResult] = field(default_factory=list)
    failures: list[str] = field(default_factory=list)


@dataclass
class GateResult:
    """Phase transition gate check result."""
    passed: bool
    gate_name: str
    summary: str = ""
    block: bool = False


@dataclass
class PhaseResult:
    phase: str
    completed: bool
    tasks_ok: int = 0
    tasks_fail: int = 0
    task_results: list[TaskResult] = field(default_factory=list)
    gate_results: list[GateResult] = field(default_factory=list)
    verified_findings: list = field(default_factory=list)


class TaskExecutor:
    """Prints step instructions sequentially. Verifies outputs. Runs gates."""

    def __init__(self, hunt_dir: Path, target_url: str):
        self.hunt_dir = hunt_dir
        self.target_url = target_url
        self.domain = target_url.split("://")[-1].split("/")[0].split(":")[0]
        self.state: dict = {}
        self.results: list[TaskResult] = []
        self.tool_context = ToolContext(hunt_dir=self.hunt_dir, target_url=self.target_url)
        self.tool_registry = default_registry()

    def run_phase(self, phase_name: str) -> PhaseResult:
        tasks = get_tasks_for_phase(phase_name)
        if not tasks:
            return PhaseResult(phase=phase_name, completed=True)

        tasks = sorted(tasks, key=lambda t: t.order)

        print(f"\n{'='*60}")
        print(f"PHASE: {phase_name.upper()} — {len(tasks)} tasks")
        print(f"{'='*60}")

        ok = 0
        fail = 0
        for task in tasks:
            tr = self._run_task(task)
            self.results.append(tr)
            if tr.passed:
                ok += 1
                print(f"  [OK] {task.task_id}: {task.title}")
            else:
                fail += 1
                print(f"  [FAIL] {task.task_id}: {'; '.join(tr.failures[:2])}")

        gate_results, verified_findings = self._run_phase_gates(phase_name)

        return PhaseResult(
            phase=phase_name,
            completed=(fail == 0),
            tasks_ok=ok,
            tasks_fail=fail,
            task_results=self.results,
            gate_results=gate_results,
            verified_findings=verified_findings,
        )

    def _run_task(self, task: Task) -> TaskResult:
        step_results = []
        failures = []

        for step in task.steps:
            sr = self._run_step(task, step)
            step_results.append(sr)
            if sr.status == "failed" and step.critical:
                failures.append(f"Step {step.step} ({step.tool}) failed: {sr.output}")

        return TaskResult(
            task_id=task.task_id,
            passed=(len(failures) == 0),
            step_results=step_results,
            failures=failures,
        )

    def _run_step(self, task: Task, step: TaskStep) -> StepResult:
        if step.adapter:
            return self._run_adapter_step(task, step)

        # Replace placeholders
        instruction = step.instruction.replace("{target}", self.target_url)
        instruction = instruction.replace("{domain}", self.domain)

        total = len(task.steps)
        crit = " [CRITICAL]" if step.critical else ""

        print(f"\n  {'─'*55}")
        print(f"  STEP {step.step}/{total} | TOOL: {step.tool}{crit}")
        print(f"  ACTION: {step.action}")
        print(f"  {'─'*55}")
        print(f"  {instruction}")
        if step.output_file:
            output_path = self._resolve_output_path(step.output_file)
            print(f"\n  >> Output: {output_path}")
            print(f"  >> After executing, verify the file exists before proceeding.")
        print()

        # The Agent reads this and executes.
        # We check if output_file exists as a post-condition signal.
        if step.output_file:
            output_path = self._resolve_output_path(step.output_file)
            if output_path.exists():
                return StepResult(step=step.step, tool=step.tool,
                                  status="ok", output=str(output_path))
            elif step.critical:
                return StepResult(step=step.step, tool=step.tool,
                                  status="failed",
                                  output=f"Output file not produced: {output_path}")
            else:
                # Non-critical: still warn but don't block
                return StepResult(step=step.step, tool=step.tool,
                                  status="skipped",
                                  output=f"Output file not found (non-critical): {output_path}")

        return StepResult(step=step.step, tool=step.tool, status="ok")

    def _run_adapter_step(self, task: Task, step: TaskStep) -> StepResult:
        total = len(task.steps)
        crit = " [CRITICAL]" if step.critical else ""
        print(f"\n  {'-'*55}")
        print(f"  STEP {step.step}/{total} | ADAPTER: {step.adapter}{crit}")
        print(f"  ACTION: {step.action}")
        print(f"  {'-'*55}")
        print(f"  {step.instruction}")

        try:
            result = self.tool_registry.execute(step.adapter, self.tool_context, step.params)
        except Exception as exc:
            return StepResult(
                step=step.step,
                tool=step.adapter,
                status="failed",
                output=f"Adapter error: {exc}",
            )

        for path in result.outputs:
            print(f"  >> Output: {path}")
        if result.summary:
            print(f"  >> {result.summary}")

        if result.success:
            if step.output_file:
                output_path = self._resolve_output_path(step.output_file)
                if output_path.exists():
                    return StepResult(step=step.step, tool=step.adapter,
                                      status="ok", output=str(output_path))
                if step.critical:
                    return StepResult(step=step.step, tool=step.adapter,
                                      status="failed",
                                      output=f"Adapter did not produce: {output_path}")
            return StepResult(step=step.step, tool=step.adapter,
                              status=result.status, output=result.summary)

        return StepResult(
            step=step.step,
            tool=step.adapter,
            status="failed" if step.critical else "skipped",
            output=result.summary or result.status,
        )

    def _resolve_output_path(self, output_file: str) -> Path:
        """Resolve an output file path relative to hunt_dir."""
        target_path = self.target_url.split("://")[-1].rstrip("/")
        # output_file may start with findings/..., js/..., scripts/..., reports/...
        # or use {target} placeholder which was already replaced
        return self.hunt_dir / "output" / target_path / output_file

    def _run_phase_gates(self, phase_name: str) -> tuple[list[GateResult], list]:
        """Run phase transition gate checks after a phase completes."""
        gates: list[GateResult] = []
        verified_findings = []

        if phase_name in ("asset_recon", "analyze", "recon"):
            gates.append(self._js_analysis_gate())
        elif phase_name == "attack_surface_analysis":
            gates.append(self._attack_surface_contract_gate())
        elif phase_name in ("autonomous_attack", "test", "api_fuzz"):
            gates.append(self._pair_completeness_gate())
            verifier_gate, verified_findings = self._verifier_gate()
            gates.append(verifier_gate)

        return gates, verified_findings

    def _artifact_path(self, relative: str) -> Path:
        target_path = self.target_url.split("://")[-1].rstrip("/")
        return self.hunt_dir / "output" / target_path / relative

    def _attack_surface_contract_gate(self) -> GateResult:
        from workflow.contracts import validate_attack_surfaces

        passed, summary = validate_attack_surfaces(
            self._artifact_path("findings/_attack_surfaces.json")
        )
        return GateResult(passed, "Attack Surface Contract", summary, not passed)

    def _verifier_gate(self) -> tuple[GateResult, list]:
        from workflow.contracts import verify_candidates

        approved, summary = verify_candidates(
            self._artifact_path("findings/_validated_candidates.json"),
            self._artifact_path("findings/_verified_findings.json"),
        )
        blocked = summary.startswith("Missing") or summary.startswith("Invalid")
        return GateResult(not blocked, "Finding Verifier", summary, blocked), approved

    def _js_analysis_gate(self) -> GateResult:
        """Check JS analysis completeness before proceeding to test phase."""
        try:
            sys.path.insert(0, str(self.hunt_dir.parent))
            from shared.linkage import check_js_analysis_completeness
            from shared.utils import read_json

            target_path = self.target_url.split("://")[-1].rstrip("/")
            ep_path = self.hunt_dir / "output" / target_path / "findings" / "_endpoint_params.json"

            if not ep_path.exists():
                return GateResult(
                    passed=False, gate_name="JS Analysis Completeness",
                    summary=f"BLOCKED: _endpoint_params.json not found at {ep_path}",
                    block=True,
                )

            data = read_json(ep_path)
            result = check_js_analysis_completeness(data)

            print(f"\n  {'─'*55}")
            print(f"  GATE: JS Analysis Completeness")
            print(f"  {'─'*55}")
            print(f"  {result.summary}")

            return GateResult(
                passed=result.passed,
                gate_name="JS Analysis Completeness",
                summary=result.summary,
                block=not result.passed,
            )
        except Exception as e:
            return GateResult(
                passed=False, gate_name="JS Analysis Completeness",
                summary=f"Gate error: {e}", block=True,
            )

    def _pair_completeness_gate(self) -> GateResult:
        """Check value pool consumption before proceeding beyond test phase."""
        try:
            sys.path.insert(0, str(self.hunt_dir.parent))
            from shared.linkage import (
                PairingEngine, EndpointRegistry, ValuePool,
                check_pair_completeness, load_linkage_state,
            )

            target_path = self.target_url.split("://")[-1].rstrip("/")
            hunt_output_dir = self.hunt_dir / "output" / target_path

            registry, pool = load_linkage_state(hunt_output_dir)

            if not registry.all_endpoints():
                return GateResult(
                    passed=True, gate_name="Pair Completeness",
                    summary="No endpoints registered — skipping pair completeness check.",
                    block=False,
                )

            engine = PairingEngine(registry, pool)
            engine.sync_consumption_state()
            pairs = engine.match(semantic_expand=True)

            check = check_pair_completeness(pairs, block_on_critical=True)

            print(f"\n  {'─'*55}")
            print(f"  GATE: Pair Completeness")
            print(f"  {'─'*55}")
            print(f"  {check.summary}")

            if check.block_transition:
                unconsumed_path = hunt_output_dir / "findings" / "_unconsumed_pairs.json"
                unconsumed_list = []
                for p in check.unconsumed:
                    unconsumed_list.append({
                        "endpoint": p.endpoint,
                        "param": p.param_name,
                        "value": p.value_entry.value,
                        "method": p.method,
                        "fallback_methods": p.fallback_methods,
                        "priority": p.priority,
                        "reason": p.reason,
                    })
                import json as _json
                unconsumed_path.parent.mkdir(parents=True, exist_ok=True)
                _json.dump(unconsumed_list, open(unconsumed_path, "w"), indent=2, ensure_ascii=False)
                print(f"  Unconsumed pairs written to: {unconsumed_path}")
                print(f"  BLOCKED: {len(check.critical_unconsumed)} HIGH/CRITICAL pairs not consumed.")
                print(f"  Re-run t3_linkage before proceeding.")

            return GateResult(
                passed=not check.block_transition,
                gate_name="Pair Completeness",
                summary=check.summary,
                block=check.block_transition,
            )
        except Exception as e:
            return GateResult(
                passed=False, gate_name="Pair Completeness",
                summary=f"Gate error: {e}", block=True,
            )


def execute_phase(hunt_dir, target_url, phase_name):
    return TaskExecutor(Path(hunt_dir), target_url).run_phase(phase_name)
