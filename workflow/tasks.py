"""
Task declarations for the four-phase pipeline.

This file describes what should happen. Deterministic local work is delegated
to typed adapters in workflow.tools; open-ended security judgment remains with
the AI and available tools.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class TaskStep:
    step: int
    tool: str
    action: str
    instruction: str
    output_file: str = ""
    critical: bool = False
    adapter: str = ""
    params: dict[str, Any] = field(default_factory=dict)


@dataclass
class Task:
    task_id: str
    phase: str
    order: int
    title: str
    steps: list[TaskStep] = field(default_factory=list)
    gate_check: str = ""


ASSET_RECON_TASKS = [
    Task(
        "c0_browser_recon",
        "asset_recon",
        1,
        "Capture browser evidence and script inventory",
        [TaskStep(
            1,
            "browser",
            "Navigate, screenshot, and list JS requests",
            (
                "Open {target}, capture a screenshot, collect network script URLs, "
                "and save them to js/_js_urls.txt. Record only observations; do not "
                "classify vulnerabilities in Phase 0."
            ),
            "js/_js_urls.txt",
            True,
        )],
    ),
    Task(
        "c0_external_assets",
        "asset_recon",
        2,
        "Resolve DNS and enumerate authorized external assets",
        [TaskStep(
            1,
            "dns/subdomain",
            "Collect in-scope externally visible assets",
            (
                "Resolve A/AAAA/CNAME/MX/TXT records for {domain}. Use passive "
                "subdomain sources available in the environment, keep only authorized "
                "scope, and write hostname, record type, value, source, and in_scope."
            ),
            "findings/_external_assets.json",
            True,
        )],
    ),
    Task(
        "c0_download_js",
        "asset_recon",
        3,
        "Download JS and sourcemaps",
        [TaskStep(
            1,
            "http",
            "Download script artifacts",
            (
                "Read js/_js_urls.txt plus HTML script references, download in-scope "
                "JavaScript files and referenced sourcemaps, then write a sourcemap "
                "index. Keep errors in the artifact rather than stopping early."
            ),
            "findings/_sourcemaps.json",
            True,
        )],
    ),
    Task(
        "c0_source_and_exposure",
        "asset_recon",
        4,
        "Search code leaks and probe exposure paths as leads",
        [TaskStep(
            1,
            "source-search",
            "Search public code for target-specific leaks",
            (
                "Search public code sources for {domain}, secrets, config fragments, "
                "API hosts, and deployment metadata. Save raw leads only."
            ),
            "findings/_source_leaks.txt",
        ), TaskStep(
            2,
            "http",
            "Probe common diagnostic and API documentation paths",
            (
                "Probe bounded Swagger/OpenAPI, Actuator, Druid, and common diagnostic "
                "paths on in-scope HTTP assets. Record URL, status, marker, content "
                "type, and redirect. A visible or blocked path is a lead, not a finding."
            ),
            "findings/_exposure_probe.json",
            True,
        )],
    ),
    Task(
        "a1_analyze_js",
        "asset_recon",
        5,
        "Deep-read JS and trace API call signatures",
        [TaskStep(
            1,
            "ai/read",
            "Extract endpoint, parameter, auth, secret, and login-link evidence",
            (
                "Read every relevant JS file under output/{target}/js. Trace API "
                "wrappers back to call sites, extract method, content type, auth hints, "
                "required and optional params, secrets, interceptors, and login links. "
                "Write one findings/_analysis_<filename>.json per analyzed file. Use "
                "references/INDEX.md only if deeper JS analysis guidance is needed."
            ),
            "findings/_analysis_summary.md",
            True,
        )],
    ),
    Task(
        "a2_build_params",
        "asset_recon",
        99,
        "Aggregate endpoint analysis",
        [TaskStep(
            1,
            "adapter",
            "Build _endpoint_params.json and _login_links.json",
            "Aggregate per-file JS analysis artifacts into the Phase 0 contract.",
            "findings/_endpoint_params.json",
            True,
            adapter="aggregate_endpoint_analysis",
        )],
    ),
]


ATTACK_SURFACE_TASKS = [
    Task(
        "p1_attack_surface_plan",
        "attack_surface_analysis",
        1,
        "Produce ranked attack-surface plan",
        [TaskStep(
            1,
            "ai",
            "Rank surfaces without active testing",
            (
                "Read Phase 0 outputs and write findings/_attack_surfaces.json. "
                "Each surface must include id, surface, hypothesis, evidence, "
                "confidence, impact, exploitability, priority_score, planned_test, "
                "chain_links, and stop_or_continue criteria. Sort by priority_score. "
                "Do not send attack requests in Phase 1."
            ),
            "findings/_attack_surfaces.json",
            True,
        )],
    )
]


AUTONOMOUS_ATTACK_TASKS = [
    Task(
        "t0_baseurl",
        "autonomous_attack",
        1,
        "Determine base URL",
        [TaskStep(
            1,
            "adapter",
            "Resolve API base URL",
            "Infer a usable base URL from endpoint artifacts or fall back to target.",
            "findings/_base_url.txt",
            True,
            adapter="determine_base_url",
        )],
    ),
    Task(
        "t1_probe_plan",
        "autonomous_attack",
        2,
        "Build probe plan for AI-directed testing",
        [TaskStep(
            1,
            "adapter",
            "Create deterministic probe definitions",
            "Generate a bounded local probe plan from known endpoints.",
            "findings/_probe_plan.json",
            True,
            adapter="build_probe_plan",
        ), TaskStep(
            2,
            "ai/tools",
            "Execute only the probes worth testing by current priority",
            (
                "Use findings/_attack_surfaces.json and findings/_probe_plan.json as "
                "inputs. Execute tests autonomously according to Phase 2 confidence "
                "rules, then save findings/_probe_results.json with method, URL, "
                "status, response marker/body preview, hypothesis id, and decision."
            ),
            "findings/_probe_results.json",
            True,
        )],
    ),
    Task(
        "t2_mine",
        "autonomous_attack",
        3,
        "Mine probe responses into a value pool",
        [TaskStep(
            1,
            "adapter",
            "Extract reusable values from successful responses",
            "Convert structured probe results into _leaked_values.json.",
            "findings/_leaked_values.json",
            True,
            adapter="mine_probe_results",
        )],
    ),
    Task(
        "t3_linkage_queue",
        "autonomous_attack",
        4,
        "Build durable linkage queue",
        [TaskStep(
            1,
            "adapter",
            "Pair leaked values with compatible endpoints and enqueue jobs",
            "Create _linkage_pairs.json and durable idempotent queue jobs.",
            "findings/_linkage_pairs.json",
            True,
            adapter="build_linkage_queue",
        ), TaskStep(
            2,
            "ai/tools",
            "Consume queued linkage tests under Phase 2 stop rules",
            (
                "Lease queued linkage jobs, execute context-appropriate tests, and "
                "write findings/_linkage_results.json. Mark each tested value/endpoint "
                "pair as consumed in _leaked_values.json. Add new attack surfaces if "
                "results reveal a better chain."
            ),
            "findings/_linkage_results.json",
            True,
        )],
    ),
    Task(
        "t4_candidates",
        "autonomous_attack",
        5,
        "Aggregate and validate reportable candidates",
        [TaskStep(
            1,
            "adapter",
            "Aggregate candidate signals",
            "Create _candidate_findings.json from probe and linkage artifacts.",
            "findings/_candidate_findings.json",
            True,
            adapter="aggregate_candidates",
        ), TaskStep(
            2,
            "ai/verifier-prep",
            "Convert only proven-impact leads into validated candidates",
            (
                "Read candidates, source leaks, exposure probes, external assets, "
                "endpoint params, and attack surfaces. Write _validated_candidates.json. "
                "Drop unsuccessful API credentials, internal metadata, Swagger/OpenAPI, "
                "Druid, CORS, map API keys, sourcemaps, debug tools, and blocked paths "
                "unless they prove unauthorized sensitive data/action or stronger impact."
            ),
            "findings/_validated_candidates.json",
            True,
        )],
    ),
    Task(
        "t5_gate",
        "autonomous_attack",
        99,
        "Pair completeness gate",
        [TaskStep(
            1,
            "adapter",
            "Verify high-priority value pairs were consumed",
            "Run the pair-completeness gate before Phase 3.",
            "findings/_unconsumed_pairs.json",
            False,
            adapter="check_pair_completeness",
        )],
    ),
]


REPORT_TASKS = [
    Task(
        "p3_verified_report",
        "report_generation",
        1,
        "Generate verifier-only report",
        [TaskStep(
            1,
            "report",
            "Render fixed evidence-based report",
            (
                "Read findings/_verified_findings.json only. Generate reports/final_report.md "
                "with title, vulnerability type, severity, URL, reproduction steps, evidence, "
                "and remediation. If none are approved, write a short no-confirmed-findings "
                "report. Never include leads, suppressed items, negative results, or candidates."
            ),
            "reports/final_report.md",
            True,
        )],
    )
]


PHASE_TASKS = {
    "asset_recon": ASSET_RECON_TASKS,
    "attack_surface_analysis": ATTACK_SURFACE_TASKS,
    "autonomous_attack": AUTONOMOUS_ATTACK_TASKS,
    "report_generation": REPORT_TASKS,
}

# Backward-compatible lookup aliases for older saved hunt states only.
PHASE_TASKS["recon"] = ASSET_RECON_TASKS
PHASE_TASKS["collect"] = ASSET_RECON_TASKS
PHASE_TASKS["analyze"] = ASSET_RECON_TASKS
PHASE_TASKS["test"] = AUTONOMOUS_ATTACK_TASKS
PHASE_TASKS["api_fuzz"] = AUTONOMOUS_ATTACK_TASKS


def get_tasks_for_phase(name: str) -> list[Task]:
    """Get tasks for a phase."""
    return PHASE_TASKS.get(name, [])


def count_all_steps() -> int:
    canonical = (
        "asset_recon",
        "attack_surface_analysis",
        "autonomous_attack",
        "report_generation",
    )
    return sum(len(t.steps) for name in canonical for t in PHASE_TASKS[name])
