#!/usr/bin/env python3
"""
shared/linkage.py — Value Pool × Endpoint Params Pairing Engine (v2.4)

Core formula:
    _endpoint_params.json (endpoint → required/optional params)
        ×
    _leaked_values.json (param_name → [ValueEntry with consumption status])
        =
    Unconsumed Pairs Queue → automate: "A 返回的值 → B 请求的输入"

Key improvement over v2.3:
    1. Value pool entries track CONSUMPTION STATUS (pending/consuming/consumed)
    2. Auto-generates unconsumed pairs: (endpoint, param, value, method)
    3. Semantic param matching (uid ↔ userId ↔ user_id ↔ userNo)
    4. Method fallback enumeration (POST 500 → try GET/PUT/PATCH)
    5. Pair completeness check for phase transition gating
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from shared.types import (
    EndpointParamRequirement,
    JSAnalysisCheckResult,
    JSAnalysisMeta,
    LinkageCheckResult,
    MethodFallback,
    UnconsumedPair,
    ValueEntry,
    ValueStatus,
)
from shared.utils import now_iso, read_json, write_json


# ---------------------------------------------------------------------------
# Parameter name semantic matching
# ---------------------------------------------------------------------------

# Maps: param name variants → canonical name
PARAM_ALIASES: dict[str, str] = {
    # uid variants
    "uid": "uid", "userId": "uid", "user_id": "uid", "userid": "uid",
    "userNo": "uid", "userno": "uid", "memberId": "uid", "member_id": "uid",
    # org ID variants
    "orgId": "orgId", "org_id": "orgId", "orgid": "orgId",
    "tenantId": "orgId", "tenant_id": "orgId",
    # order ID variants
    "orderId": "orderId", "order_id": "orderId", "orderid": "orderId",
    "tradeNo": "orderId", "tradeno": "orderId",
    # token variants
    "token": "token", "accessToken": "token", "access_token": "token",
    "apiKey": "token", "apikey": "token", "api_key": "token",
    "secretKey": "token", "secret_key": "token",
    # email
    "email": "email", "mail": "email", "eMail": "email",
    # phone
    "phone": "phone", "mobile": "phone", "tel": "phone",
    "phoneNumber": "phone", "phone_number": "phone",
    # name / username
    "username": "username", "userName": "username", "account": "username",
    "nickname": "username", "nickName": "username",
    # page / pagination
    "page": "page", "pageNum": "page", "pageNo": "page", "pageIndex": "page",
    "pageSize": "pageSize", "page_size": "pageSize", "limit": "pageSize",
}

# Semantic groups: params that are likely interchangeable
SEMANTIC_GROUPS: dict[str, list[str]] = {
    "id_like": ["uid", "orgId", "orderId", "id", "userId", "user_id",
                "org_id", "order_id", "memberId", "tenantId", "buyerId"],
    "string_like": ["username", "email", "phone", "accountName", "name",
                    "nickname", "keyword", "search", "query"],
    "auth_like": ["token", "apiKey", "api_key", "accessToken", "secretKey",
                  "csrfToken", "Authorization", "X-API-Key"],
    "url_like": ["url", "redirect", "redirect_uri", "callback", "file_url",
                 "image_url", "path", "file"],
}


def canonical_param_name(raw: str) -> str:
    """Map any param name variant to its canonical form."""
    return PARAM_ALIASES.get(raw, raw.lower())


# ---------------------------------------------------------------------------
# Method fallback enumeration
# ---------------------------------------------------------------------------

# Ordered fallback methods to try when primary method returns non-2xx
METHOD_FALLBACK_ORDER: list[str] = ["GET", "POST", "PUT", "PATCH", "DELETE"]

# Content-Type variants to try for POST/PUT/PATCH
CONTENT_TYPE_VARIANTS: list[str] = [
    "application/json",
    "application/x-www-form-urlencoded",
    "multipart/form-data",
]

# Status codes that SHOULD trigger method fallback
# (was: only 405; now: any non-2xx, non-404)
METHOD_FALLBACK_TRIGGER_CODES: set[int] = {
    405,  # Method Not Allowed (original trigger)
    500,  # Internal Server Error (often wrong method/content-type)
    415,  # Unsupported Media Type (wrong Content-Type)
    400,  # Bad Request (could be wrong method)
    501,  # Not Implemented
    503,  # Service Unavailable (could be intermittent)
}
# 401/403/404/429 are NOT in this set — those have their own handling


def get_fallback_methods(primary_method: str,
                         status_code: int | None = None) -> list[str]:
    """Return ordered list of alternative HTTP methods to try.

    If status_code is a trigger code, return full fallback list.
    Otherwise, return empty list.
    """
    if status_code is not None and status_code not in METHOD_FALLBACK_TRIGGER_CODES:
        return []

    primary = primary_method.upper()
    return [m for m in METHOD_FALLBACK_ORDER if m != primary]


def get_content_type_variants() -> list[str]:
    """Return Content-Type variants to try for POST/PUT/PATCH."""
    return CONTENT_TYPE_VARIANTS[:]


# ---------------------------------------------------------------------------
# Value Pool with Consumption Tracking
# ---------------------------------------------------------------------------

class ValuePool:
    """Enhanced value pool with per-value consumption tracking.

    Structure (serialized as _leaked_values.json):
    {
      "param_name": {
        "values": [
          {
            "value": "admin",
            "status": "pending",
            "discovered_at": "2026-05-19T...",
            "source_endpoint": "/user/list",
            "source_param": "uid",
            "priority": "HIGH",
            "consumed_endpoints": [],
            "unconsumed_endpoints": ["/user/detail", "/user/edit"]
          },
          ...
        ]
      },
      ...
    }
    """

    def __init__(self) -> None:
        self._pool: dict[str, list[ValueEntry]] = {}

    # -- Read/Write --

    def add_value(self, param_name: str, value: str,
                  source_endpoint: str = "",
                  source_param: str = "",
                  priority: str = "MEDIUM") -> ValueEntry:
        """Add a value to the pool. Returns the entry (new or existing)."""
        canonical = canonical_param_name(param_name)

        if canonical not in self._pool:
            self._pool[canonical] = []

        # Check for duplicate
        for entry in self._pool[canonical]:
            if entry.value == str(value):
                return entry

        entry = ValueEntry(
            value=str(value),
            status=ValueStatus.PENDING,
            discovered_at=now_iso(),
            source_endpoint=source_endpoint,
            source_param=param_name,
            priority=priority,
        )
        self._pool[canonical].append(entry)
        return entry

    def get_values(self, param_name: str,
                   status: ValueStatus | None = None) -> list[ValueEntry]:
        """Get all values for a param, optionally filtered by status."""
        canonical = canonical_param_name(param_name)
        if canonical not in self._pool:
            return []
        if status is None:
            return self._pool[canonical]
        return [e for e in self._pool[canonical] if e.status == status]

    def mark_consumed(self, param_name: str, value: str,
                      endpoint: str) -> None:
        """Mark a value as consumed for a specific endpoint."""
        canonical = canonical_param_name(param_name)
        for entry in self._pool.get(canonical, []):
            if entry.value == str(value):
                if endpoint not in entry.consumed_endpoints:
                    entry.consumed_endpoints.append(endpoint)
                if endpoint in entry.unconsumed_endpoints:
                    entry.unconsumed_endpoints.remove(endpoint)
                # Update global status
                if (not entry.unconsumed_endpoints
                        and entry.status == ValueStatus.CONSUMING):
                    entry.status = ValueStatus.CONSUMED
                break

    def set_unconsumed_endpoints(self, param_name: str, value: str,
                                  endpoints: list[str]) -> None:
        """Set the list of endpoints that still need this value."""
        canonical = canonical_param_name(param_name)
        for entry in self._pool.get(canonical, []):
            if entry.value == str(value):
                # Remove already-consumed endpoints
                remaining = [e for e in endpoints
                            if e not in entry.consumed_endpoints]
                entry.unconsumed_endpoints = remaining
                if remaining and entry.status == ValueStatus.PENDING:
                    entry.status = ValueStatus.CONSUMING
                elif not remaining:
                    entry.status = ValueStatus.CONSUMED
                break

    def has_pending(self) -> bool:
        """Check if any values are still pending/consuming."""
        for entries in self._pool.values():
            for e in entries:
                if e.status in (ValueStatus.PENDING, ValueStatus.CONSUMING):
                    return True
        return False

    def get_param_names(self) -> list[str]:
        """Return all canonical param names in the pool."""
        return list(self._pool.keys())

    def all_entries(self) -> list[tuple[str, ValueEntry]]:
        """Yield all (param_name, ValueEntry) pairs."""
        for param_name, entries in self._pool.items():
            for entry in entries:
                yield param_name, entry

    # -- Serialization --

    def to_dict(self) -> dict:
        """Serialize to dict for JSON storage."""
        result: dict[str, dict] = {}
        for param_name, entries in self._pool.items():
            result[param_name] = {
                "values": [
                    {
                        "value": e.value,
                        "status": e.status.value,
                        "discovered_at": e.discovered_at,
                        "source_endpoint": e.source_endpoint,
                        "source_param": e.source_param,
                        "priority": e.priority,
                        "consumed_endpoints": e.consumed_endpoints,
                        "unconsumed_endpoints": e.unconsumed_endpoints,
                    }
                    for e in entries
                ]
            }
        return result

    @classmethod
    def from_dict(cls, data: dict) -> "ValuePool":
        """Deserialize from dict."""
        pool = cls()
        for param_name, param_data in data.items():
            entries_raw = param_data.get("values", [])
            entries: list[ValueEntry] = []
            for raw in entries_raw:
                entry = ValueEntry(
                    value=raw.get("value", ""),
                    status=ValueStatus(raw.get("status", "pending")),
                    discovered_at=raw.get("discovered_at", ""),
                    source_endpoint=raw.get("source_endpoint", ""),
                    source_param=raw.get("source_param", param_name),
                    priority=raw.get("priority", "MEDIUM"),
                    consumed_endpoints=raw.get("consumed_endpoints", []),
                    unconsumed_endpoints=raw.get("unconsumed_endpoints", []),
                )
                entries.append(entry)
            pool._pool[param_name] = entries
        return pool

    @classmethod
    def from_file(cls, path: str | Path) -> "ValuePool":
        """Load from _leaked_values.json. Returns empty pool if not found."""
        data = read_json(path)
        if not data:
            return cls()
        return cls.from_dict(data)

    def to_file(self, path: str | Path) -> bool:
        """Save to _leaked_values.json."""
        return write_json(path, self.to_dict())


# ---------------------------------------------------------------------------
# Endpoint Parameter Requirements (from JS analysis)
# ---------------------------------------------------------------------------

class EndpointRegistry:
    """Registry of endpoint → parameter requirements (from _endpoint_params.json)."""

    def __init__(self) -> None:
        self._endpoints: dict[str, EndpointParamRequirement] = {}

    def add(self, endpoint: str,
            method: str,
            content_type: str = "",
            auth: str = "",
            params_required: list[str] | None = None,
            params_optional: list[str] | None = None,
            source_files: list[str] | None = None,
            notes: str = "") -> EndpointParamRequirement:
        """Register an endpoint with its parameter requirements."""
        req = EndpointParamRequirement(
            endpoint=endpoint,
            method=method.upper(),
            content_type=content_type,
            auth=auth,
            params_required=params_required or [],
            params_optional=params_optional or [],
            source_files=source_files or [],
            notes=notes,
        )
        self._endpoints[endpoint] = req
        return req

    def get(self, endpoint: str) -> EndpointParamRequirement | None:
        return self._endpoints.get(endpoint)

    def all_endpoints(self) -> list[str]:
        return list(self._endpoints.keys())

    def all_requirements(self) -> list[EndpointParamRequirement]:
        return list(self._endpoints.values())

    def get_all_param_names(self) -> set[str]:
        """Get all unique (canonical) parameter names across all endpoints."""
        params: set[str] = set()
        for req in self._endpoints.values():
            for p in req.params_required + req.params_optional:
                params.add(canonical_param_name(p))
        return params

    @classmethod
    def from_file(cls, path: str | Path) -> "EndpointRegistry":
        """Load from _endpoint_params.json (handles both v2.4 nested and old flat formats)."""
        data = read_json(path)
        reg = cls()

        # v2.4 format: {"_meta": {...}, "endpoints": {"/api/...": {...}, ...}}
        if "endpoints" in data:
            endpoints = data["endpoints"]
        else:
            # Old flat format: {"/api/...": {...}, ...} with optional _meta mixed in
            endpoints = {k: v for k, v in data.items()
                        if not k.startswith("_") and isinstance(v, dict)}

        for endpoint, info in endpoints.items():
            if not isinstance(info, dict):
                continue
            reg.add(
                endpoint=endpoint,
                method=info.get("method", "GET"),
                content_type=info.get("content_type", ""),
                auth=info.get("auth", ""),
                params_required=info.get("params_required", []),
                params_optional=info.get("params_optional", []),
                source_files=info.get("source_files", []),
                notes=info.get("notes", ""),
            )
        return reg


# ---------------------------------------------------------------------------
# Pairing Engine — the core formula
# ---------------------------------------------------------------------------

class PairingEngine:
    """Match value pool entries against endpoint parameter requirements.

    Core formula:
        _endpoint_params.json × _leaked_values.json → Unconsumed Pairs

    For each endpoint:
        1. Check which params it needs (required + optional)
        2. For each needed param, check if value pool has matching values
        3. If match found, generate (endpoint, param, value) test pair
        4. Track consumption status
        5. For each pair, enumerate method fallbacks if primary method fails
    """

    def __init__(self, registry: EndpointRegistry, pool: ValuePool):
        self.registry = registry
        self.pool = pool

    def match(self,
              semantic_expand: bool = True,
              include_optional: bool = True) -> list[UnconsumedPair]:
        """Generate all unconsumed (endpoint, param, value) pairs.

        Args:
            semantic_expand: If True, also match by semantic group
                             (e.g., uid → matches userId, user_id params)
            include_optional: If True, also match optional params

        Returns:
            List of UnconsumedPair sorted by priority (CRITICAL first).
        """
        pairs: list[UnconsumedPair] = []

        for req in self.registry.all_requirements():
            params_to_check = list(req.params_required)
            if include_optional:
                params_to_check.extend(req.params_optional)

            for param_name in params_to_check:
                canonical = canonical_param_name(param_name)

                # Exact match: value pool has this exact param
                matched_values = self._match_values(
                    canonical, req.endpoint, semantic_expand
                )

                for entry in matched_values:
                    pair = UnconsumedPair(
                        value_entry=entry,
                        endpoint=req.endpoint,
                        param_name=param_name,
                        method=req.method,
                        fallback_methods=get_fallback_methods(req.method),
                        priority=entry.priority,
                        reason=f"{entry.source_endpoint} → {req.endpoint} "
                               f"(参数 {param_name} = {entry.value})",
                    )
                    pairs.append(pair)

        # Sort: CRITICAL first, then HIGH, then MEDIUM, then LOW
        priority_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
        pairs.sort(key=lambda p: priority_order.get(p.priority, 2))

        return pairs

    def _match_values(self, canonical_param: str, endpoint: str,
                      semantic_expand: bool = False) -> list[ValueEntry]:
        """Find unconsumed values in pool matching the given canonical param.

        Returns only values not yet consumed on this endpoint.
        """
        results: list[ValueEntry] = []

        # 1. Exact canonical match
        for entry in self.pool.get_values(canonical_param):
            if (endpoint not in entry.consumed_endpoints
                    and entry.status != ValueStatus.SKIPPED):
                results.append(entry)

        # 2. Semantic group expansion
        if semantic_expand:
            group_key = self._find_semantic_group(canonical_param)
            if group_key:
                for related_param in SEMANTIC_GROUPS.get(group_key, []):
                    if related_param == canonical_param:
                        continue
                    for entry in self.pool.get_values(related_param):
                        if (endpoint not in entry.consumed_endpoints
                                and entry.status != ValueStatus.SKIPPED):
                            results.append(entry)

        # Deduplicate by value
        seen = set()
        unique: list[ValueEntry] = []
        for e in results:
            if e.value not in seen:
                seen.add(e.value)
                unique.append(e)
        return unique

    @staticmethod
    def _find_semantic_group(param: str) -> str | None:
        for group_key, members in SEMANTIC_GROUPS.items():
            if param in members:
                return group_key
        return None

    def sync_consumption_state(self) -> None:
        """Sync: for each value in pool, compute which endpoints still need it.

        After calling this, each ValueEntry.unconsumed_endpoints will be
        populated with the list of endpoints that require this value.
        """
        for param_name, entry in self.pool.all_entries():
            unconsumed: list[str] = []
            for req in self.registry.all_requirements():
                all_params = req.params_required + req.params_optional
                canonical_params = {canonical_param_name(p) for p in all_params}
                if param_name in canonical_params:
                    if req.endpoint not in entry.consumed_endpoints:
                        unconsumed.append(req.endpoint)
            self.pool.set_unconsumed_endpoints(param_name, entry.value, unconsumed)


# ---------------------------------------------------------------------------
# Pair Completeness Check (phase transition gate)
# ---------------------------------------------------------------------------

def check_pair_completeness(pairs: list[UnconsumedPair],
                            block_on_critical: bool = True) -> LinkageCheckResult:
    """Check if all value-endpoint pairs have been tested.

    Used as a phase transition gate: before moving from API_FUZZ to
    autonomous attack verification, ensure no high-priority pairs remain unconsumed.

    Args:
        pairs: List of UnconsumedPair from PairingEngine.match()
        block_on_critical: If True, any CRITICAL or HIGH unconsumed pair
                           will block phase transition.

    Returns:
        LinkageCheckResult with pass/fail and detailed listing.
    """
    total = len(pairs)
    consumed = sum(1 for p in pairs
                   if p.value_entry.status == ValueStatus.CONSUMED)
    unconsumed_list = [p for p in pairs
                       if p.value_entry.status != ValueStatus.CONSUMED]

    critical = [p for p in unconsumed_list
                if p.priority in ("CRITICAL", "HIGH")]

    block = False
    if block_on_critical and critical:
        block = True

    # Build summary
    lines = [
        f"Pair Completeness Check: {'PASSED' if not block else 'BLOCKED'}",
        f"  Total pairs: {total}",
        f"  Consumed: {consumed}",
        f"  Unconsumed: {len(unconsumed_list)}",
        f"  Critical/HIGH unconsumed: {len(critical)}",
    ]
    if critical:
        lines.append("  Critical unconsumed pairs:")
        for p in critical[:10]:
            lines.append(f"    - [{p.priority}] {p.reason}")
        if len(critical) > 10:
            lines.append(f"    ... and {len(critical) - 10} more")

    return LinkageCheckResult(
        passed=not block,
        total_pairs=total,
        consumed_pairs=consumed,
        unconsumed_pairs=len(unconsumed_list),
        unconsumed=unconsumed_list,
        critical_unconsumed=critical,
        block_transition=block,
        summary="\n".join(lines),
    )


# ---------------------------------------------------------------------------
# Convenience: load linkage state from hunt directory
# ---------------------------------------------------------------------------

def load_linkage_state(hunt_dir: str | Path) -> tuple[EndpointRegistry, ValuePool]:
    """Load both endpoint registry and value pool from hunt directory.

    Looks for:
        findings/_endpoint_params.json
        findings/_leaked_values.json

    Falls back to:
        downloaded/{domain}/_endpoint_params.json
        downloaded/{domain}/_leaked_values.json
    """
    base = Path(hunt_dir)

    # Try findings/ first, then downloaded/
    ep_paths = [
        base / "findings" / "_endpoint_params.json",
    ]
    vp_paths = [
        base / "findings" / "_leaked_values.json",
    ]

    # Also check downloaded/ subdirectories
    downloaded = base / "downloaded"
    if downloaded.is_dir():
        for domain_dir in downloaded.iterdir():
            if domain_dir.is_dir():
                ep_paths.append(domain_dir / "_endpoint_params.json")
                vp_paths.append(domain_dir / "_leaked_values.json")

    registry = EndpointRegistry()
    for p in ep_paths:
        if p.exists():
            registry = EndpointRegistry.from_file(p)
            break

    pool = ValuePool()
    for p in vp_paths:
        if p.exists():
            pool = ValuePool.from_file(p)
            break

    return registry, pool


def save_linkage_state(hunt_dir: str | Path,
                       pool: ValuePool) -> bool:
    """Save the value pool (with consumption state) to disk."""
    base = Path(hunt_dir)
    findings_dir = base / "findings"
    findings_dir.mkdir(parents=True, exist_ok=True)
    return pool.to_file(findings_dir / "_leaked_values.json")


# ---------------------------------------------------------------------------
# Method fallback test matrix builder
# ---------------------------------------------------------------------------

def build_method_fallback_matrix(endpoint: str,
                                 primary_method: str,
                                 status_code: int) -> list[dict[str, Any]]:
    """Build a test matrix of (method, content-type) pairs to try.

    Used when an endpoint returns a non-2xx status code that triggers
    method fallback (500, 405, 415, etc.).

    Returns:
        List of dicts with keys: method, content_type, description
    """
    fallback_methods = get_fallback_methods(primary_method, status_code)
    if not fallback_methods:
        return []

    matrix: list[dict] = []

    for method in fallback_methods:
        if method in ("GET", "DELETE", "OPTIONS", "HEAD"):
            # No body → only one variant
            matrix.append({
                "method": method,
                "content_type": None,
                "description": f"{method} {endpoint} (fallback from {primary_method} {status_code})",
            })
        else:
            # POST/PUT/PATCH → try each Content-Type
            for ct in CONTENT_TYPE_VARIANTS:
                matrix.append({
                    "method": method,
                    "content_type": ct,
                    "description": f"{method} {endpoint} Content-Type={ct} "
                                   f"(fallback from {primary_method} {status_code})",
                })

    return matrix


# ---------------------------------------------------------------------------
# JS Analysis Completeness Check (v2.4 — Phase 0→1 Gate)
# ---------------------------------------------------------------------------

# Filename patterns that are KNOWN 3rd-party libraries (safe to skip)
KNOWN_THIRD_PARTY_PATTERNS: list[str] = [
    "lodash", "moment", "jquery", "bootstrap", "vue.runtime",
    "react-dom", "react.production", "core-js", "regenerator",
    "polyfills", "webpack-runtime", "zone.js", "popper",
    "axios.min", "chart.js", "echarts", "d3.", "three.",
    "swiper", "dayjs", "marked", "highlight", "codemirror",
    "tinymce", "ckeditor", "quill", "prism", "mathjax",
    "socket.io.min", "firebase", "supabase",
]


def is_known_third_party(filename: str) -> bool:
    """Check if a JS filename matches known 3rd-party library patterns."""
    fn_lower = filename.lower()
    for pattern in KNOWN_THIRD_PARTY_PATTERNS:
        if pattern in fn_lower:
            return True
    return False


# Minimum required per-endpoint fields for the gate check
REQUIRED_ENDPOINT_FIELDS: list[str] = [
    "method",           # HTTP method (GET/POST/PUT/DELETE/PATCH)
    "source_files",     # which JS file(s) this endpoint came from
]


def extract_js_analysis_meta(endpoint_params: dict) -> JSAnalysisMeta:
    """Extract self-reported analysis completeness from _endpoint_params.json.

    Expects the new v2.4 format with a `_meta` key:
    ```json
    {
      "_meta": {
        "js_files_collected": 12,
        "js_files_analyzed": 10,
        "js_files_skipped": ["lodash.min.js", "moment.min.js"],
        "skipped_reason": "confirmed 3rd-party",
        "files_detail": {
          "app.js": {"analyzed": true, "api_calls_found": 15, ...},
          ...
        },
        "total_endpoints_extracted": 38,
        "warnings": []
      },
      "endpoints": { ... }
    }
    ```

    Returns JSAnalysisMeta with extracted values, or defaults if _meta missing.
    """
    meta_raw = endpoint_params.get("_meta", {})
    if not meta_raw:
        return JSAnalysisMeta(
            warnings=["_meta section missing — analysis tracking not enabled"]
        )

    files_detail = meta_raw.get("files_detail", {})
    # Convert nested dict to flat format if needed
    if isinstance(files_detail, dict):
        # It's already {filename: {analyzed: true, ...}}
        pass
    else:
        files_detail = {}

    return JSAnalysisMeta(
        js_files_collected=meta_raw.get("js_files_collected", 0),
        js_files_analyzed=meta_raw.get("js_files_analyzed", 0),
        js_files_skipped=meta_raw.get("js_files_skipped", []),
        skipped_reason=meta_raw.get("skipped_reason", ""),
        analysis_completeness=float(meta_raw.get("analysis_completeness", 0)),
        files_detail=files_detail,
        total_endpoints_extracted=meta_raw.get(
            "total_endpoints_extracted",
            len(endpoint_params.get("endpoints", endpoint_params)) - (1 if "_meta" in endpoint_params else 0)
        ),
        total_secrets_found=meta_raw.get("total_secrets_found", 0),
        total_routes_found=meta_raw.get("total_routes_found", 0),
        warnings=list(meta_raw.get("warnings", [])),
        generated_at=meta_raw.get("generated_at", ""),
    )


def check_js_analysis_completeness(endpoint_params: dict,
                                   min_endpoints: int = 3,
                                   min_completeness: float = 0.8) -> JSAnalysisCheckResult:
    """Validate that JS analysis was actually completed before proceeding.

    This is the Phase 0→1 HARD GATE. It checks:
        1. _endpoint_params.json exists and is not empty
        2. JS files were collected (js_files_collected > 0)
        3. JS files were actually READ (js_files_analyzed > 0)
        4. Analysis completeness >= threshold (0.8 by default)
        5. At least min_endpoints were extracted
        6. Each endpoint has required fields (method, source_files)
        7. No "unanalyzed" non-3rd-party files remain

    Args:
        endpoint_params: The parsed _endpoint_params.json dict.
        min_endpoints: Minimum number of endpoints that must be extracted.
        min_completeness: Minimum analysis completeness (0.0–1.0).

    Returns:
        JSAnalysisCheckResult with pass/fail and detailed failure reasons.
    """
    failures: list[str] = []
    warnings: list[str] = []

    # Extract endpoints from the new v2.4 format or fall back to old format
    endpoints = endpoint_params.get("endpoints", {})
    if not endpoints:
        # Old format: the dict itself IS the endpoints
        endpoints = {k: v for k, v in endpoint_params.items()
                    if not k.startswith("_")}
    if not endpoints and endpoint_params:
        # Check if maybe all keys are endpoints (no _meta)
        has_meta_keys = any(k.startswith("_") for k in endpoint_params)
        if not has_meta_keys:
            endpoints = dict(endpoint_params)

    meta = extract_js_analysis_meta(endpoint_params)

    # --- Check 1: File must exist and not be empty ---
    if not endpoint_params:
        failures.append("_endpoint_params.json is empty or missing")
        return JSAnalysisCheckResult(
            passed=False, meta=meta, failures=failures,
            summary="BLOCKED: _endpoint_params.json is empty"
        )
    if not endpoints:
        failures.append("No endpoints found in _endpoint_params.json")

    # --- Check 2: JS files must have been collected ---
    if meta.js_files_collected == 0:
        failures.append("js_files_collected = 0 — no JS files were downloaded")
    else:
        # --- Check 3: JS files must have been READ ---
        if meta.js_files_analyzed == 0:
            failures.append(
                f"js_files_analyzed = 0 — {meta.js_files_collected} JS files "
                f"were downloaded but NONE were deep-read"
            )
        else:
            # Check which files weren't analyzed
            unanalyzed: list[str] = []
            for fname, detail in meta.files_detail.items():
                if isinstance(detail, dict) and not detail.get("analyzed", False):
                    if not is_known_third_party(fname):
                        unanalyzed.append(fname)

            if unanalyzed:
                failures.append(
                    f"{len(unanalyzed)} non-3rd-party JS files were not analyzed: "
                    f"{unanalyzed[:5]}{' ...' if len(unanalyzed) > 5 else ''}"
                )

    # --- Check 4: completeness threshold ---
    if meta.analysis_completeness < min_completeness:
        failures.append(
            f"analysis_completeness = {meta.analysis_completeness:.0%} "
            f"< required {min_completeness:.0%}"
        )

    # --- Check 5: Minimum endpoints ---
    if meta.total_endpoints_extracted < min_endpoints:
        failures.append(
            f"total_endpoints_extracted = {meta.total_endpoints_extracted} "
            f"< min {min_endpoints}"
        )

    # --- Check 6: Each endpoint must have required fields ---
    missing_fields: list[str] = []
    for ep_name, ep_info in endpoints.items():
        if not isinstance(ep_info, dict):
            continue
        for field in REQUIRED_ENDPOINT_FIELDS:
            if not ep_info.get(field):
                missing_fields.append(f"{ep_name}: missing '{field}'")
    if missing_fields:
        failures.append(
            f"{len(missing_fields)} endpoints have missing required fields"
        )
        for mf in missing_fields[:5]:
            failures.append(f"  - {mf}")
        if len(missing_fields) > 5:
            failures.append(f"  ... and {len(missing_fields) - 5} more")

    # --- Aggregate ---
    passed = len(failures) == 0
    summary_lines = [
        f"JS Analysis Completeness: {'PASSED' if passed else 'BLOCKED'}",
        f"  Files: {meta.js_files_analyzed}/{meta.js_files_collected} analyzed "
        f"(completeness: {meta.analysis_completeness:.0%})",
        f"  Endpoints extracted: {meta.total_endpoints_extracted}",
    ]
    for f in failures:
        summary_lines.append(f"  FAIL: {f}")
    for w in meta.warnings + warnings:
        summary_lines.append(f"  WARN: {w}")

    return JSAnalysisCheckResult(
        passed=passed,
        meta=meta,
        failures=failures,
        warnings=meta.warnings + warnings,
        summary="\n".join(summary_lines),
    )


# ---------------------------------------------------------------------------
# CLI test (run directly for debugging)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # Demo: simulate the exact scenario from the bug report
    print("=" * 60)
    print("Pairing Engine Demo — Simulating uid linkage gap")
    print("=" * 60)

    # Step 1: Create endpoint registry (what JS analysis should have produced)
    registry = EndpointRegistry()
    registry.add(
        endpoint="/userCenter/userManager/user/list",
        method="POST",
        content_type="application/json",
        auth="none",
        params_required=["page", "limit"],
    )
    registry.add(
        endpoint="/userCenter/userManager/user/detail",
        method="GET",                          # ← JS said GET, not POST!
        content_type="",
        auth="none",
        params_required=["uid"],
        notes="从 JS 提取: GET /user/detail?uid=xxx",
    )

    # Step 2: Create value pool (what /user/list response produced)
    pool = ValuePool()
    pool.add_value("uid", "admin",
                   source_endpoint="/userCenter/userManager/user/list",
                   source_param="uid", priority="HIGH")
    pool.add_value("uid", "huizhang43",
                   source_endpoint="/userCenter/userManager/user/list",
                   source_param="uid", priority="MEDIUM")
    pool.add_value("uid", "medtest",
                   source_endpoint="/userCenter/userManager/user/list",
                   source_param="uid", priority="MEDIUM")

    # Step 3: Run pairing engine
    engine = PairingEngine(registry, pool)
    engine.sync_consumption_state()
    pairs = engine.match(semantic_expand=True)

    print(f"\nUnconsumed pairs: {len(pairs)}")
    for p in pairs:
        print(f"  [{p.priority}] {p.reason}")
        print(f"       method={p.method}, fallbacks={p.fallback_methods}")

    # Step 4: Check completeness
    check = check_pair_completeness(pairs)
    print(f"\n{check.summary}")

    # Step 5: Demonstrate method fallback matrix
    print("\n--- Method Fallback Matrix Demo ---")
    matrix = build_method_fallback_matrix(
        "/userCenter/userManager/user/detail",
        primary_method="POST",
        status_code=500,
    )
    for m in matrix:
        print(f"  {m['description']}")
