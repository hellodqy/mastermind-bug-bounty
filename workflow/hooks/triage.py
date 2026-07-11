"""
workflow/hooks/triage.py — Hook 3: Triage Gate

Trigger: Before any finding is promoted to reportable status.
Gate: HARD GATE — blocks findings without demonstrated IMPACT.
4-stage validation: target → class → evidence → impact → confidence.
"""

from __future__ import annotations

from shared.types import Finding, FindingStatus, TriageResult


# ---------------------------------------------------------------------------
# Validation checks
# ---------------------------------------------------------------------------

def validate(finding: Finding, confidence_threshold: float = 0.7) -> TriageResult:
    """Run 4-stage validation on a finding.

    Stages:
        1. Has target URL
        2. Has vulnerability class
        3. Has detection evidence
        4. Has impact demonstrated (HARD GATE)
        5. Confidence >= threshold
    """
    checks: dict[str, bool] = {}
    reasons: list[str] = []

    # Stage 1: Target present
    checks["has_target"] = bool(finding.target_url and len(finding.target_url) > 0)
    if not checks["has_target"]:
        reasons.append("Missing target URL or endpoint.")

    # Stage 2: Vulnerability class identified
    checks["has_vuln_class"] = bool(finding.vuln_class and len(finding.vuln_class) > 0)
    if not checks["has_vuln_class"]:
        reasons.append("Vulnerability class not identified.")

    # Stage 3: Detection evidence
    checks["has_evidence"] = bool(finding.evidence and len(finding.evidence) >= 20)
    if not checks["has_evidence"]:
        reasons.append("Insufficient detection evidence (need at least 20 chars).")

    # Stage 4: Impact demonstrated — HARD GATE
    checks["impact_demonstrated"] = _check_impact(finding)
    if not checks["impact_demonstrated"]:
        reasons.append(
            "IMPACT NOT DEMONSTRATED. Detection alone is insufficient. "
            "Provide proof of exploitable impact: data exposure, "
            "privilege escalation, RCE demo, etc."
        )

    # Stage 5: Confidence
    checks["confidence_passed"] = finding.confidence >= confidence_threshold
    if not checks["confidence_passed"]:
        reasons.append(
            f"Confidence {finding.confidence:.0%} below threshold "
            f"{confidence_threshold:.0%}."
        )

    approved = all(checks.values())

    return TriageResult(
        approved=approved,
        finding_id=finding.id,
        checks=checks,
        reasons=reasons,
        confidence=finding.confidence,
        threshold=confidence_threshold,
    )


def _check_impact(f: Finding) -> bool:
    """HARD GATE: Does the finding demonstrate exploitable impact?

    Impact is demonstrated when the finding proves the vulnerability
    can be exploited to produce a tangible security outcome.
    """
    has_impact = bool(f.impact and len(f.impact.strip()) >= 20)
    has_reproduction = bool(
        len(f.poc_steps) >= 2
        and all(isinstance(step, str) and step.strip() for step in f.poc_steps)
    )
    return has_impact and has_reproduction


# ---------------------------------------------------------------------------
# POC chain trigger
# ---------------------------------------------------------------------------

def generate_poc_chain(finding: Finding) -> dict:
    """Generate the POC evidence chain for an approved finding."""
    vuln = finding.vuln_class.lower()

    steps = [
        "1. Re-confirm the vulnerability with a clean session",
        "2. Document the exact request/response pair",
        "3. Demonstrate maximum impact",
        "4. Capture screenshot or video evidence",
        "5. Test on a secondary endpoint if applicable",
        "6. Document any bypass attempts",
    ]

    # Customize step 3 per vulnerability class
    impact_hints = {
        "sqli": "Extract database schema or sample data via UNION/boolean/time-based",
        "sql_injection": "Extract database schema or sample data via UNION/boolean/time-based",
        "xss": "Demonstrate cookie theft, keylogging, or DOM manipulation",
        "ssrf": "Probe internal services; access cloud metadata endpoints",
        "idor": "Access other users' resources by modifying object references",
        "ssti": "Execute template expression: {{7*7}} or achieve RCE",
        "rce": "Execute benign command (id, whoami) and capture output",
        "lfi": "Read sensitive files: /etc/passwd, application config",
        "path_traversal": "Read sensitive files: /etc/passwd, application config",
        "xxe": "Read /etc/passwd via external entity or perform SSRF",
    }

    for key, hint in impact_hints.items():
        if key in vuln:
            steps[2] = f"3. {hint}"
            break

    return {
        "steps": steps,
        "proof_required": ["screenshot", "curl_command", "http_response"],
        "caido_recording_recommended": any(
            k in vuln for k in ("rce", "ssrf", "sqli", "sql")
        ),
    }
