"""
shared/types.py — Core data types for Mastermind Bug Bounty.

All state, findings, and configuration flow through these types.
Zero external dependencies.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class Severity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class HuntStatus(str, Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"


class PhaseName(str, Enum):
    ASSET_RECON = "asset_recon"
    ATTACK_SURFACE_ANALYSIS = "attack_surface_analysis"
    AUTONOMOUS_ATTACK = "autonomous_attack"
    REPORT_GENERATION = "report_generation"
    # Legacy v3.1 phase names kept so existing state.json files still load.
    RECON = "recon"
    DEPENDENCY_SCAN = "dependency_scan"
    API_FUZZ = "api_fuzz"
    CRYPTO_ATTACK = "crypto_attack"
    BYPASS = "bypass"
    EXPLOIT = "exploit"
    AI_SECURITY = "ai_security"


class FindingStatus(str, Enum):
    DETECTED = "detected"
    TRIAGE_PENDING = "triage_pending"
    TRIAGE_APPROVED = "triage_approved"
    TRIAGE_REJECTED = "triage_rejected"
    POC_GENERATED = "poc_generated"
    REPORTED = "reported"


class GuardLevel(str, Enum):
    """Severity levels for Coordinator Guard nudges."""
    NUDGE = "nudge"
    WARN = "warn"
    ALERT = "alert"


class ValueStatus(str, Enum):
    """Consumption status for a value in the leaked values pool."""
    PENDING = "pending"         # discovered, not yet tried on any endpoint
    CONSUMING = "consuming"     # being tested on one or more endpoints
    CONSUMED = "consumed"       # fully tested on all matching endpoints
    SKIPPED = "skipped"         # intentionally not tested (rate-limited, etc.)


class MethodFallback(str, Enum):
    """HTTP method fallback strategies when primary method fails."""
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    PATCH = "PATCH"
    DELETE = "DELETE"
    OPTIONS = "OPTIONS"
    HEAD = "HEAD"


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class Target:
    """A single target under test."""
    url: str
    scope: list[str] = field(default_factory=list)
    tech_stack: dict[str, str] = field(default_factory=dict)
    waf_cdn: str = ""                     # detected WAF/CDN vendor
    endpoints_discovered: list[str] = field(default_factory=list)
    js_files: list[str] = field(default_factory=list)


@dataclass
class Finding:
    """A vulnerability finding tracked through the triage pipeline."""
    id: str
    vuln_class: str                       # xss, sqli, ssrf, idor, ssti, ...
    target_url: str
    severity: Severity = Severity.MEDIUM
    confidence: float = 0.0
    evidence: str = ""
    impact: str = ""
    poc_steps: list[str] = field(default_factory=list)
    status: FindingStatus = FindingStatus.DETECTED
    agent_id: str = ""
    timestamp: str = ""


@dataclass
class AgentState:
    """Tracked state of a specialist agent."""
    agent_id: str
    agent_type: str                       # recon, api_fuzz, bypass, exploit, ...
    task: str = ""
    status: str = "idle"                  # idle, active, working, completed, failed
    retry_count: int = 0
    max_retries: int = 3
    last_output: str = ""
    spawned_at: str = ""
    concluded_at: str = ""


@dataclass
class WorklogEntry:
    """A single entry in the hunt worklog."""
    timestamp: str
    session_id: str
    agent_id: str
    entry_type: str                       # tool_call, finding, agent_spawn, ...
    data: dict[str, Any] = field(default_factory=dict)


@dataclass
class HuntState:
    """Complete hunt session state — serialized across sessions."""
    hunt_id: str
    target: Target
    status: HuntStatus = HuntStatus.ACTIVE
    current_phase: PhaseName = PhaseName.ASSET_RECON
    findings: list[Finding] = field(default_factory=list)
    completed_phases: list[PhaseName] = field(default_factory=list)
    agents: dict[str, AgentState] = field(default_factory=dict)
    worklog: list[WorklogEntry] = field(default_factory=list)
    custom_instructions: str = ""
    created_at: str = ""
    updated_at: str = ""

    def touch(self) -> None:
        self.updated_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


# ---------------------------------------------------------------------------
# Hook result types
# ---------------------------------------------------------------------------

@dataclass
class GuardResult:
    """Output of Coordinator Guard check."""
    allowed: bool
    warning: str | None = None
    nudge: str | None = None
    level: GuardLevel = GuardLevel.NUDGE


@dataclass
class TriageResult:
    """Output of Triage Gate validation."""
    approved: bool
    finding_id: str
    checks: dict[str, bool] = field(default_factory=dict)
    reasons: list[str] = field(default_factory=list)
    confidence: float = 0.0
    threshold: float = 0.7


@dataclass
class RetryResult:
    """Output of Retry Detector analysis."""
    surrender_detected: bool
    matched_patterns: list[str] = field(default_factory=list)
    category: str = ""
    bypass_suggestions: list[str] = field(default_factory=list)
    retry_prompt: str = ""
    should_retry: bool = False


@dataclass
class HandoffResult:
    """Output of Handoff Saver."""
    saved: bool
    path: str = ""
    summary: str = ""


# ---------------------------------------------------------------------------
# Value Pool & Linkage types (v2.4 — consumption queue)
# ---------------------------------------------------------------------------

@dataclass
class ValueEntry:
    """A single value in the leaked values pool with consumption tracking."""
    value: str
    status: ValueStatus = ValueStatus.PENDING
    discovered_at: str = ""
    source_endpoint: str = ""
    source_param: str = ""
    priority: str = "MEDIUM"         # CRITICAL / HIGH / MEDIUM / LOW
    consumed_endpoints: list[str] = field(default_factory=list)
    unconsumed_endpoints: list[str] = field(default_factory=list)


@dataclass
class EndpointParamRequirement:
    """What a specific endpoint requires in terms of parameters."""
    endpoint: str
    method: str                        # primary method from JS
    content_type: str = ""
    auth: str = ""
    params_required: list[str] = field(default_factory=list)
    params_optional: list[str] = field(default_factory=list)
    source_files: list[str] = field(default_factory=list)
    notes: str = ""


@dataclass
class UnconsumedPair:
    """A value-endpoint pair that still needs to be tested."""
    value_entry: ValueEntry
    endpoint: str
    param_name: str
    method: str
    fallback_methods: list[str] = field(default_factory=list)
    priority: str = "MEDIUM"
    reason: str = ""


@dataclass
class LinkageCheckResult:
    """Output of the pair completeness check (phase transition gate)."""
    passed: bool
    total_pairs: int = 0
    consumed_pairs: int = 0
    unconsumed_pairs: int = 0
    unconsumed: list[UnconsumedPair] = field(default_factory=list)
    critical_unconsumed: list[UnconsumedPair] = field(default_factory=list)
    block_transition: bool = False
    summary: str = ""


# ---------------------------------------------------------------------------
# JS Analysis Completeness types (v2.4)
# ---------------------------------------------------------------------------

@dataclass
class JSFileDetail:
    """Per-file analysis status."""
    filename: str
    size_kb: int = 0
    analyzed: bool = False               # 是否已完整读取
    api_calls_found: int = 0             # 发现的 API 调用数
    classification: str = "unknown"      # app / chunk / admin / vendor / config / login / unknown
    priority: str = "P1"                 # P0(管理API) / P1(用户API) / P2(工具库) / P3(已知第三方)
    notes: str = ""


@dataclass
class JSAnalysisMeta:
    """Self-reported completeness metadata for JS analysis phase."""
    js_files_collected: int = 0          # 下载的 JS 文件总数
    js_files_analyzed: int = 0           # 已完成深度读取的文件数
    js_files_skipped: list[str] = field(default_factory=list)  # 跳过的文件名
    skipped_reason: str = ""             # 为什么跳过（如"确认为第三方库: lodash, moment"）
    analysis_completeness: float = 0.0   # analyzed / (collected - legitimately_skipped)
    files_detail: dict[str, dict] = field(default_factory=dict)  # filename → JSFileDetail fields
    total_endpoints_extracted: int = 0
    total_secrets_found: int = 0
    total_routes_found: int = 0
    warnings: list[str] = field(default_factory=list)
    generated_at: str = ""


@dataclass
class JSAnalysisCheckResult:
    """Output of JS analysis completeness gate (Phase 0→1 transition)."""
    passed: bool
    meta: JSAnalysisMeta | None = None
    failures: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    summary: str = ""
