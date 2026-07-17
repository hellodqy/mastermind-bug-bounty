"""
Typed tool adapters for deterministic workflow operations.

The AI still decides what to test and how to reason about results. These
adapters only perform repeatable local transformations over hunt artifacts.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol
from urllib.parse import urlparse

from shared.utils import now_iso, read_json, read_text, sha256_short, write_json


@dataclass(frozen=True)
class ToolContext:
    hunt_dir: Path
    target_url: str

    @property
    def domain(self) -> str:
        parsed = urlparse(self.target_url)
        host = parsed.netloc or self.target_url.split("/")[0]
        return host.split(":")[0]

    @property
    def target_key(self) -> str:
        return self.target_url.split("://")[-1].rstrip("/")

    @property
    def output_dir(self) -> Path:
        return self.hunt_dir / "output" / self.target_key

    @property
    def findings_dir(self) -> Path:
        return self.output_dir / "findings"

    def artifact(self, relative: str) -> Path:
        return self.output_dir / relative


@dataclass
class ToolResult:
    success: bool
    status: str
    summary: str = ""
    outputs: list[str] = field(default_factory=list)
    data: dict[str, Any] = field(default_factory=dict)


class ToolAdapter(Protocol):
    name: str

    def execute(self, context: ToolContext, params: dict[str, Any] | None = None) -> ToolResult:
        ...


class ToolRegistry:
    def __init__(self) -> None:
        self._adapters: dict[str, ToolAdapter] = {}

    def register(self, adapter: ToolAdapter) -> None:
        self._adapters[adapter.name] = adapter

    def get(self, name: str) -> ToolAdapter:
        if name not in self._adapters:
            raise KeyError(f"Unknown tool adapter: {name}")
        return self._adapters[name]

    def execute(self, name: str, context: ToolContext,
                params: dict[str, Any] | None = None) -> ToolResult:
        return self.get(name).execute(context, params or {})


class AggregateEndpointAnalysis:
    name = "aggregate_endpoint_analysis"

    def execute(self, context: ToolContext, params: dict[str, Any] | None = None) -> ToolResult:
        findings = context.findings_dir
        js_files = list((context.output_dir / "js").glob("*.js"))
        analysis_files = sorted(findings.glob("_analysis_*.json"))

        endpoints: dict[str, dict[str, Any]] = {}
        secrets: list[dict[str, Any]] = []
        login_links: list[dict[str, Any]] = []
        files_detail: dict[str, dict[str, Any]] = {}
        analyzed_count = 0

        for path in analysis_files:
            data = read_json(path)
            fname = data.get("filename") or path.name
            if not data.get("analyzed"):
                continue
            analyzed_count += 1
            files_detail[fname] = {
                "analyzed": True,
                "api_calls_found": len(data.get("endpoints", [])),
                "classification": data.get("classification", "unknown"),
                "priority": data.get("priority", "P1"),
                "notes": data.get("notes", ""),
            }
            for ep in data.get("endpoints", []):
                url = ep.get("url")
                if not url:
                    continue
                current = endpoints.setdefault(url, {
                    "method": ep.get("method") or "GET",
                    "content_type": ep.get("content_type", ""),
                    "auth": ep.get("auth", ""),
                    "params_required": [],
                    "params_optional": [],
                    "source_files": [],
                    "notes": ep.get("notes", ""),
                })
                for key in ("params_required", "params_optional", "source_files"):
                    for value in ep.get(key, []):
                        if value not in current[key]:
                            current[key].append(value)
            secrets.extend(data.get("secrets", []))
            for link in data.get("login_links", []):
                if link not in login_links:
                    login_links.append(link)

        output = {
            "_meta": {
                "js_files_collected": len(js_files),
                "js_files_analyzed": analyzed_count,
                "js_files_skipped": [],
                "skipped_reason": "",
                "analysis_completeness": round(analyzed_count / max(len(js_files), 1), 2),
                "files_detail": files_detail,
                "total_endpoints_extracted": len(endpoints),
                "total_secrets_found": len(secrets),
                "total_routes_found": 0,
                "warnings": [],
                "generated_at": now_iso(),
            },
            "endpoints": endpoints,
        }

        ep_path = findings / "_endpoint_params.json"
        login_path = findings / "_login_links.json"
        write_json(ep_path, output)
        write_json(login_path, {"login_links": login_links})
        return ToolResult(
            success=True,
            status="ok",
            summary=f"Aggregated {len(endpoints)} endpoints from {analyzed_count} JS analysis files.",
            outputs=[str(ep_path), str(login_path)],
            data={"endpoints": len(endpoints), "js_analyzed": analyzed_count},
        )


class DetermineBaseURL:
    name = "determine_base_url"

    def execute(self, context: ToolContext, params: dict[str, Any] | None = None) -> ToolResult:
        endpoints = read_json(context.findings_dir / "_endpoint_params.json")
        base = endpoints.get("_meta", {}).get("base_url", "")
        if not base:
            for url in endpoints.get("endpoints", {}):
                if isinstance(url, str) and url.startswith(("http://", "https://")):
                    parsed = urlparse(url)
                    base = f"{parsed.scheme}://{parsed.netloc}"
                    break
        base = base or context.target_url
        path = context.findings_dir / "_base_url.txt"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(base, encoding="utf-8")
        return ToolResult(True, "ok", f"Base URL set to {base}", [str(path)], {"base_url": base})


class BuildProbePlan:
    name = "build_probe_plan"

    BODY_VARIANTS = [
        ("POST_empty", {}),
        ("POST_pageNum", {"pageNum": 1, "pageSize": 10}),
        ("POST_page", {"page": 1, "size": 10}),
        ("POST_current", {"current": 1, "pageSize": 10}),
        ("POST_pageNo", {"pageNo": 1, "pageSize": 10}),
    ]

    def execute(self, context: ToolContext, params: dict[str, Any] | None = None) -> ToolResult:
        base = read_text(context.findings_dir / "_base_url.txt").strip() or context.target_url
        endpoint_doc = read_json(context.findings_dir / "_endpoint_params.json")
        probes: list[dict[str, Any]] = []
        for url, info in endpoint_doc.get("endpoints", {}).items():
            endpoint = _normalize_endpoint(url)
            content_type = info.get("content_type") or "application/json"
            for label, body in self.BODY_VARIANTS:
                probes.append({
                    "idempotency_key": sha256_short(f"{base}|POST|{endpoint}|{label}"),
                    "label": label,
                    "method": "POST",
                    "url": base.rstrip("/") + endpoint,
                    "content_type": content_type,
                    "body": body,
                })
            probes.append({
                "idempotency_key": sha256_short(f"{base}|GET|{endpoint}|uid"),
                "label": "GET_uid",
                "method": "GET",
                "url": base.rstrip("/") + endpoint,
                "query": {"uid": "test"},
            })
        path = context.findings_dir / "_probe_plan.json"
        write_json(path, {"probes": probes, "generated_at": now_iso()})
        return ToolResult(True, "ok", f"Built {len(probes)} probe definitions.", [str(path)])


class MineProbeResults:
    name = "mine_probe_results"

    SENSITIVE = (
        "uid", "userid", "user_id", "token", "accesstoken", "refreshtoken",
        "password", "pwd", "secret", "apikey", "api_key", "privatekey",
        "role", "isadmin", "phone", "mobile", "email", "orgid", "org_id",
        "tenantid", "orderid",
    )

    def execute(self, context: ToolContext, params: dict[str, Any] | None = None) -> ToolResult:
        results = _load_probe_results(context.findings_dir)
        pool: dict[str, dict[str, list[dict[str, Any]]]] = {}
        for result in results:
            if int(result.get("status", 0) or 0) < 200 or int(result.get("status", 0) or 0) >= 300:
                continue
            body = result.get("body") or result.get("body_preview") or ""
            for key, value in _extract_json_values(str(body)):
                lower = key.lower()
                priority = "HIGH" if any(marker in lower for marker in self.SENSITIVE) else "MEDIUM"
                bucket = pool.setdefault(key, {"values": []})
                if not any(str(v.get("value")) == str(value) for v in bucket["values"]):
                    bucket["values"].append({
                        "value": str(value),
                        "status": "pending",
                        "discovered_at": now_iso(),
                        "source_endpoint": result.get("url") or result.get("endpoint", ""),
                        "source_param": key,
                        "priority": priority,
                        "consumed_endpoints": [],
                        "unconsumed_endpoints": [],
                    })
        path = context.findings_dir / "_leaked_values.json"
        write_json(path, pool)
        return ToolResult(True, "ok", f"Mined {sum(len(v['values']) for v in pool.values())} values.", [str(path)])


class BuildLinkageQueue:
    name = "build_linkage_queue"

    def execute(self, context: ToolContext, params: dict[str, Any] | None = None) -> ToolResult:
        from shared.linkage import EndpointRegistry, PairingEngine, ValuePool
        from workflow.persistence import SQLiteStateStore

        ep_path = context.findings_dir / "_endpoint_params.json"
        pool_path = context.findings_dir / "_leaked_values.json"
        if not ep_path.exists() or not pool_path.exists():
            return ToolResult(False, "failed", "Missing endpoint params or value pool.")

        registry = EndpointRegistry.from_file(str(ep_path))
        pool = ValuePool.from_file(str(pool_path))
        engine = PairingEngine(registry, pool)
        engine.sync_consumption_state()
        pairs = engine.match(semantic_expand=True)

        pairs_json = []
        state = read_json(context.hunt_dir / "state.json")
        hunt_id = state.get("hunt_id") or "default"
        store = SQLiteStateStore(context.hunt_dir)
        enqueued = 0
        for pair in pairs:
            payload = {
                "kind": "linkage_probe",
                "endpoint": pair.endpoint,
                "param": pair.param_name,
                "value": pair.value_entry.value,
                "method": pair.method,
                "fallback_methods": pair.fallback_methods,
                "priority": pair.priority,
                "reason": pair.reason,
            }
            key = sha256_short(json.dumps(payload, sort_keys=True, ensure_ascii=False))
            job = store.enqueue_job(hunt_id, key, payload, priority=_priority_num(pair.priority))
            if job.state == "queued":
                enqueued += 1
            pairs_json.append(payload | {"idempotency_key": key, "queue_state": job.state})

        path = context.findings_dir / "_linkage_pairs.json"
        write_json(path, pairs_json)
        return ToolResult(True, "ok", f"Prepared {len(pairs)} linkage pairs; {enqueued} queued.", [str(path)])


class AggregateCandidates:
    name = "aggregate_candidates"

    def execute(self, context: ToolContext, params: dict[str, Any] | None = None) -> ToolResult:
        findings = context.findings_dir
        results = _load_probe_results(findings)
        linkage = read_json(findings / "_linkage_results.json")
        if isinstance(linkage, dict):
            linkage_rows = linkage.get("results", [])
        else:
            linkage_rows = linkage if isinstance(linkage, list) else []

        candidates: list[dict[str, Any]] = []
        for result in results:
            body = str(result.get("body") or result.get("body_preview") or "")
            status = int(result.get("status", 0) or 0)
            if 200 <= status < 300 and _looks_like_sensitive_data(body):
                candidates.append({
                    "vuln_class": "Potential Unauthorized Data Access",
                    "target_url": result.get("url", ""),
                    "evidence": body[:300],
                    "impact": "",
                    "poc_steps": [],
                    "confidence": 0.55,
                    "severity": "medium",
                    "src_eligibility": {"boundary_crossed": False, "reproducible": False},
                })
        for row in linkage_rows:
            if row.get("hit"):
                candidates.append({
                    "vuln_class": "Potential IDOR/Data Leak",
                    "target_url": row.get("ep") or row.get("endpoint") or "",
                    "evidence": row.get("preview", ""),
                    "impact": "",
                    "poc_steps": [],
                    "confidence": 0.6,
                    "severity": "medium",
                    "context": row,
                    "src_eligibility": {"boundary_crossed": False, "reproducible": False},
                })

        path = findings / "_candidate_findings.json"
        write_json(path, {"candidates": candidates, "generated_at": now_iso()})
        return ToolResult(True, "ok", f"Aggregated {len(candidates)} candidate signals.", [str(path)])


class CheckPairCompleteness:
    name = "check_pair_completeness"

    def execute(self, context: ToolContext, params: dict[str, Any] | None = None) -> ToolResult:
        from shared.linkage import (
            EndpointRegistry,
            PairingEngine,
            ValuePool,
            check_pair_completeness,
            save_linkage_state,
        )

        ep_path = context.findings_dir / "_endpoint_params.json"
        pool_path = context.findings_dir / "_leaked_values.json"
        if not ep_path.exists() or not pool_path.exists():
            return ToolResult(True, "skipped", "Missing endpoint params or value pool; gate skipped.")

        registry = EndpointRegistry.from_file(str(ep_path))
        pool = ValuePool.from_file(str(pool_path))
        engine = PairingEngine(registry, pool)
        engine.sync_consumption_state()
        check = check_pair_completeness(engine.match(semantic_expand=True), block_on_critical=True)
        save_linkage_state(str(context.output_dir), pool)

        if check.block_transition:
            rows = [{
                "endpoint": p.endpoint,
                "param": p.param_name,
                "value": p.value_entry.value,
                "method": p.method,
                "fallback_methods": p.fallback_methods,
                "priority": p.priority,
                "reason": p.reason,
            } for p in check.unconsumed]
            path = context.findings_dir / "_unconsumed_pairs.json"
            write_json(path, rows)
            return ToolResult(False, "failed", check.summary, [str(path)])
        return ToolResult(True, "ok", check.summary)


def default_registry() -> ToolRegistry:
    registry = ToolRegistry()
    for adapter in (
        AggregateEndpointAnalysis(),
        DetermineBaseURL(),
        BuildProbePlan(),
        MineProbeResults(),
        BuildLinkageQueue(),
        AggregateCandidates(),
        CheckPairCompleteness(),
    ):
        registry.register(adapter)
    return registry


def _normalize_endpoint(url: str) -> str:
    if url.startswith(("http://", "https://")):
        parsed = urlparse(url)
        return parsed.path or "/"
    return url if url.startswith("/") else "/" + url


def _load_probe_results(findings_dir: Path) -> list[dict[str, Any]]:
    structured = read_json(findings_dir / "_probe_results.json")
    if isinstance(structured.get("results"), list):
        return structured["results"]

    text = read_text(findings_dir / "_blind_results.txt")
    rows: list[dict[str, Any]] = []
    current: dict[str, Any] = {}
    chunks: list[str] = []
    for line in text.splitlines():
        if line.startswith(">>>"):
            if current:
                current["body_preview"] = "\n".join(chunks)[-1000:]
                rows.append(current)
            current = {"label": line[3:].strip(), "status": 0}
            chunks = []
            continue
        if "HTTP_CODE:" in line:
            before, _, after = line.partition("HTTP_CODE:")
            chunks.append(before)
            code = re.sub(r"\D.*$", "", after.strip())
            current["status"] = int(code) if code.isdigit() else 0
        else:
            chunks.append(line)
    if current:
        current["body_preview"] = "\n".join(chunks)[-1000:]
        rows.append(current)
    return rows


def _extract_json_values(body: str) -> list[tuple[str, Any]]:
    try:
        data = json.loads(body)
    except json.JSONDecodeError:
        return []

    values: list[tuple[str, Any]] = []

    def walk(obj: Any) -> None:
        if isinstance(obj, dict):
            for key, value in obj.items():
                if isinstance(value, (dict, list)):
                    walk(value)
                elif value is not None:
                    values.append((str(key), value))
        elif isinstance(obj, list):
            for item in obj[:5]:
                walk(item)

    walk(data)
    return values


def _looks_like_sensitive_data(body: str) -> bool:
    markers = ('"token"', '"phone"', '"mobile"', '"email"', '"records"', '"total"', '"userId"', '"uid"')
    return any(marker.lower() in body.lower() for marker in markers)


def _priority_num(priority: str) -> int:
    return {"CRITICAL": 0, "HIGH": 10, "MEDIUM": 50, "LOW": 100}.get(priority.upper(), 50)
