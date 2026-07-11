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
    assert len(payload["rejected"]) == 0
    assert payload["suppressed"]["count"] == 1


def test_src_policy_suppresses_non_reportable_classes_even_with_high_scores(tmp_path):
    candidates = tmp_path / "_candidate_findings.json"
    verified = tmp_path / "_verified_findings.json"
    candidates.write_text(json.dumps({"candidates": [
        {
            "vuln_class": "敏感信息泄露 / 内网架构暴露",
            "target_url": "https://example.test/app.js",
            "severity": "high",
            "confidence": 1.0,
            "evidence": "JavaScript contains internal network architecture and service routing names.",
            "impact": "The internal architecture and service routing metadata are visible.",
            "poc_steps": ["Download app.js.", "Read the internal service names."],
        },
        {
            "vuln_class": "百度地图 API Key 泄露",
            "target_url": "https://example.test/app.js",
            "severity": "high",
            "confidence": 1.0,
            "evidence": "A client-side Baidu Map API key is embedded in JavaScript.",
            "impact": "The public browser key can be copied from the application bundle.",
            "poc_steps": ["Download app.js.", "Locate the Baidu Map API key."],
        },
        {
            "vuln_class": "CORS misconfiguration",
            "target_url": "https://example.test/api/public",
            "severity": "high",
            "confidence": 1.0,
            "evidence": "Access-Control-Allow-Origin reflects an arbitrary origin.",
            "impact": "A cross-origin response can be read from a test origin.",
            "poc_steps": ["Send an Origin header.", "Observe the reflected CORS header."],
        },
        {
            "vuln_class": "Generic information disclosure",
            "target_url": "https://example.test/error",
            "severity": "high",
            "confidence": 1.0,
            "evidence": "The error response exposes a framework version and a local file path.",
            "impact": "The response provides implementation metadata but no direct security outcome.",
            "poc_steps": ["Open the error endpoint.", "Read the framework version."],
        },
    ]}), encoding="utf-8")

    approved, _ = verify_candidates(candidates, verified)
    payload = json.loads(verified.read_text(encoding="utf-8"))
    assert approved == []
    assert payload["approved"] == []
    assert payload["rejected"] == []
    assert payload["suppressed"]["count"] == 4


def test_api_credential_requires_proven_sensitive_use(tmp_path):
    candidates = tmp_path / "candidates.json"
    verified = tmp_path / "verified.json"
    base = {
        "vuln_class": "Hardcoded API Token exposure",
        "target_url": "https://example.test/app.js",
        "severity": "high",
        "confidence": 0.95,
        "evidence": "A hardcoded API token was found and tested against the owning API.",
        "impact": "The credential permits access to private customer support records.",
        "poc_steps": ["Use the redacted token in the API header.", "Request one authorized proof record."],
    }
    candidates.write_text(json.dumps({"candidates": [base]}), encoding="utf-8")
    approved, _ = verify_candidates(candidates, verified)
    assert approved == []

    base["credential_validation"] = {
        "tested": True,
        "usable": True,
        "sensitive_outcome": True,
        "endpoint": "https://example.test/api/private/tickets",
        "request_evidence": "Authorization header redacted; response returned one private test record.",
        "outcome_type": "sensitive_data",
    }
    candidates.write_text(json.dumps({"candidates": [base]}), encoding="utf-8")
    approved, _ = verify_candidates(candidates, verified)
    assert len(approved) == 1


def test_documentation_path_requires_successful_sensitive_bypass(tmp_path):
    candidates = tmp_path / "candidates.json"
    verified = tmp_path / "verified.json"
    base = {
        "vuln_class": "Swagger/OpenAPI path exposure",
        "target_url": "https://example.test/swagger-ui",
        "severity": "high",
        "confidence": 0.95,
        "evidence": "The Swagger path exists but initially returns an authorization response.",
        "impact": "A bypass exposed private administrative endpoint definitions and test data.",
        "poc_steps": ["Request the documented path.", "Apply the verified routing bypass."],
    }
    candidates.write_text(json.dumps({"candidates": [base]}), encoding="utf-8")
    approved, _ = verify_candidates(candidates, verified)
    assert approved == []

    base["exposure_validation"] = {
        "bypass_attempted": True,
        "access_achieved": True,
        "sensitive_outcome": True,
        "endpoint": "https://example.test/internal/v3/api-docs",
        "request_evidence": "A redacted request/response pair proves access to protected admin API data.",
        "outcome_type": "sensitive_data",
    }
    candidates.write_text(json.dumps({"candidates": [base]}), encoding="utf-8")
    approved, _ = verify_candidates(candidates, verified)
    assert len(approved) == 1
