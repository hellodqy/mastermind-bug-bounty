"""Structured artifact contracts for the four-phase pipeline."""

from __future__ import annotations

import json
import hashlib
from pathlib import Path

from shared.types import Finding, FindingStatus, Severity
from shared.utils import now_iso
from workflow.hooks.triage import validate


def validate_attack_surfaces(path: Path) -> tuple[bool, str]:
    if not path.exists():
        return False, f"Missing attack-surface plan: {path}"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return False, f"Invalid attack-surface JSON: {exc}"

    surfaces = data.get("attack_surfaces") if isinstance(data, dict) else None
    if not isinstance(surfaces, list):
        return False, "_attack_surfaces.json must contain an attack_surfaces list."

    required = {
        "id", "surface", "hypothesis", "evidence", "confidence", "impact",
        "exploitability", "priority_score", "planned_test", "chain_links",
    }
    for index, surface in enumerate(surfaces):
        if not isinstance(surface, dict):
            return False, f"Attack surface #{index + 1} must be an object."
        missing = sorted(required - surface.keys())
        if missing:
            return False, f"Attack surface #{index + 1} missing: {', '.join(missing)}"
        for field in ("confidence", "impact", "exploitability"):
            value = surface[field]
            if not isinstance(value, (int, float)) or not 0 <= value <= 1:
                return False, f"Attack surface #{index + 1} has invalid {field}."
        if not isinstance(surface["priority_score"], (int, float)):
            return False, f"Attack surface #{index + 1} has invalid priority_score."
        expected = (
            surface["impact"] * 0.4
            + surface["exploitability"] * 0.3
            + surface["confidence"] * 0.2
        ) / 0.9
        if abs(surface["priority_score"] - expected) > 0.02:
            return False, f"Attack surface #{index + 1} has inconsistent priority_score."

    scores = [item["priority_score"] for item in surfaces]
    if scores != sorted(scores, reverse=True):
        return False, "Attack surfaces must be sorted by descending priority_score."
    return True, f"Validated {len(surfaces)} ranked attack surfaces."


def verify_candidates(candidate_path: Path, verified_path: Path) -> tuple[list[Finding], str]:
    if not candidate_path.exists():
        return [], f"Missing candidate findings: {candidate_path}"
    try:
        data = json.loads(candidate_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [], f"Invalid candidate findings JSON: {exc}"

    candidates = data.get("candidates") if isinstance(data, dict) else None
    if not isinstance(candidates, list):
        return [], "Invalid candidate findings: expected a candidates list."

    approved: list[Finding] = []
    rejected: list[dict] = []
    for item in candidates:
        if not isinstance(item, dict):
            rejected.append({"candidate": item, "reasons": ["Candidate must be an object."]})
            continue
        try:
            stable_id = "finding-" + hashlib.sha256(
                json.dumps(item, sort_keys=True, ensure_ascii=False).encode("utf-8")
            ).hexdigest()[:12]
            confidence = float(item.get("confidence", 0.0))
            if not 0 <= confidence <= 1:
                raise ValueError("confidence must be between 0 and 1")
            finding = Finding(
                id=item.get("id") or stable_id,
                vuln_class=str(item.get("vuln_class", "")),
                target_url=str(item.get("target_url", "")),
                severity=Severity(item.get("severity", "medium")),
                confidence=confidence,
                evidence=str(item.get("evidence", "")),
                impact=str(item.get("impact", "")),
                poc_steps=list(item.get("poc_steps", [])),
                agent_id="verifier",
                timestamp=now_iso(),
            )
        except (TypeError, ValueError) as exc:
            rejected.append({"candidate": item, "reasons": [f"Invalid schema: {exc}"]})
            continue

        result = validate(finding, confidence_threshold=0.8)
        if result.approved:
            finding.status = FindingStatus.TRIAGE_APPROVED
            approved.append(finding)
        else:
            finding.status = FindingStatus.TRIAGE_REJECTED
            rejected.append({"candidate": item, "reasons": result.reasons})

    verified_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "approved": [
            {
                "id": f.id,
                "vuln_class": f.vuln_class,
                "target_url": f.target_url,
                "severity": f.severity.value,
                "confidence": f.confidence,
                "evidence": f.evidence,
                "impact": f.impact,
                "poc_steps": f.poc_steps,
                "status": f.status.value,
            }
            for f in approved
        ],
        "rejected": rejected,
    }
    verified_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return approved, f"Verifier approved {len(approved)} and rejected {len(rejected)} candidates."
