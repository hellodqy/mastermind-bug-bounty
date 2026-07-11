import json

from shared.types import Finding, FindingStatus
from workflow.contracts import validate_attack_surfaces, verify_candidates
from workflow.hooks.triage import validate
from workflow.pipeline import PIPELINE
from workflow.tasks import get_tasks_for_phase


def test_pipeline_has_four_connected_phases():
    names = [phase.name for phase in PIPELINE]
    assert names == [
        "asset_recon",
        "attack_surface_analysis",
        "autonomous_attack",
        "report_generation",
    ]
    assert all(get_tasks_for_phase(name) for name in names)
    assert PIPELINE[1].depends_on == [names[0]]
    assert PIPELINE[2].depends_on == [names[1]]
    assert PIPELINE[3].depends_on == [names[2]]


def test_attack_surface_contract_requires_ranked_normalized_scores(tmp_path):
    path = tmp_path / "_attack_surfaces.json"
    path.write_text(json.dumps({"attack_surfaces": [{
        "id": "surface-1",
        "surface": "Swagger",
        "hypothesis": "An export endpoint may lack object authorization",
        "evidence": ["/swagger-ui returned 200"],
        "confidence": 0.8,
        "impact": 0.7,
        "exploitability": 1.0,
        "priority_score": (0.7 * 0.4 + 1.0 * 0.3 + 0.8 * 0.2) / 0.9,
        "planned_test": "Compare two authorized test users",
        "chain_links": ["export", "IDOR"],
    }]}), encoding="utf-8")

    passed, _ = validate_attack_surfaces(path)
    assert passed


def test_triage_requires_impact_and_reproduction():
    finding = Finding(
        id="finding-1",
        vuln_class="idor",
        target_url="https://example.test/api/orders/2",
        confidence=0.9,
        evidence="A second authorized test account received another user's order.",
        impact="Cross-account access exposes private order records.",
        poc_steps=["Login as test user A.", "Request test user B's order ID."],
    )
    assert validate(finding, confidence_threshold=0.8).approved

    finding.poc_steps = []
    assert not validate(finding, confidence_threshold=0.8).approved


def test_verifier_writes_only_approved_findings(tmp_path):
    candidates = tmp_path / "_candidate_findings.json"
    verified = tmp_path / "_verified_findings.json"
    candidates.write_text(json.dumps({"candidates": [
        {
            "vuln_class": "idor",
            "target_url": "https://example.test/api/orders/2",
            "severity": "high",
            "confidence": 0.9,
            "evidence": "A second authorized test account received another user's order.",
            "impact": "Cross-account access exposes private order records.",
            "poc_steps": ["Login as test user A.", "Request test user B's order ID."],
        },
        {
            "vuln_class": "swagger exposure",
            "target_url": "https://example.test/swagger-ui",
            "severity": "low",
            "confidence": 0.6,
            "evidence": "Swagger UI returned HTTP 200.",
            "impact": "",
            "poc_steps": [],
        },
    ]}), encoding="utf-8")

    approved, _ = verify_candidates(candidates, verified)
    payload = json.loads(verified.read_text(encoding="utf-8"))
    assert len(approved) == 1
    assert approved[0].status is FindingStatus.TRIAGE_APPROVED
    assert len(payload["approved"]) == 1
    assert len(payload["rejected"]) == 1
