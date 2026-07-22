import json
from pathlib import Path

from shared.types import Finding, FindingStatus
from workflow.contracts import validate_attack_surfaces, verify_candidates
from workflow.hooks.triage import validate
from workflow.pipeline import PIPELINE
from workflow.tasks import get_tasks_for_phase


ROOT = Path(__file__).resolve().parents[1]


def src_eligibility(outcome_type="unauthorized_sensitive_data"):
    return {
        "boundary_crossed": True,
        "reproducible": True,
        "outcome_type": outcome_type,
        "affected_asset": "authorized test target",
        "evidence": "A redacted request/response pair proves the concrete outcome.",
    }


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
    assert not validate(finding, confidence_threshold=0.8).approved
    assert validate(
        finding,
        confidence_threshold=0.8,
        enforce_reportability=False,
    ).approved

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
            "src_eligibility": src_eligibility(),
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
        "src_eligibility": src_eligibility(),
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
        "src_eligibility": src_eligibility(),
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


def test_opencode_entrypoints_contain_the_lead_to_impact_gate():
    root_skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
    command = (ROOT / "commands" / "mastermind-bug-bounty.md").read_text(encoding="utf-8")

    assert "Mandatory Lead-to-Impact Gate" in root_skill
    assert "Default to rejection" in root_skill
    assert "PageSpy/VConsole or sourcemap" in root_skill
    assert "Swagger exposure: roughly `0.7`" not in root_skill
    assert "Non-Negotiable Lead Gate" in command
    assert "禁止在正文、摘要、附录" in command
    assert "skill(mastermind-workflow)" not in command


def test_loaded_resources_do_not_promote_path_visibility_to_a_finding():
    fingerprint = (ROOT / "references" / "fingerprint-mapping.md").read_text(encoding="utf-8")
    druid = (ROOT / "references" / "cve-chains.md").read_text(encoding="utf-8")

    assert "the entire API surface is exposed" not in fingerprint
    assert "任意请求返回 Druid 页面/JSON → 未授权" not in druid
    assert "普通页面、登录页、空监控页" in druid


def test_common_non_src_observations_are_suppressed(tmp_path):
    candidates = tmp_path / "candidates.json"
    verified = tmp_path / "verified.json"
    observations = [
        ("微服务架构信息泄露", "前端 JS 暴露 13 个后端微服务域名"),
        ("PageSpy/VConsole 暴露", "预发布环境加载远程调试工具"),
        ("网关信息泄露", "404 错误包含内部服务名 css-oms-order-svc"),
        ("Sourcemap 可下载", "app.126ab986.js.map 可公开下载"),
        ("Token URL 传输", "下载接口使用 ?token= 传递凭证"),
        ("内网 IP 泄露", "域名解析到 10.128.25.187"),
        ("解密 API 暴露", "POST /api/common/security/decrypt 需要正常认证"),
        ("敏感路径暴露", "Swagger/Actuator 返回 501 但路径可识别"),
    ]
    payload = {"candidates": [
        {
            "vuln_class": vuln_class,
            "target_url": "https://example.test/lead",
            "severity": "high",
            "confidence": 1.0,
            "evidence": detail,
            "impact": "This reveals implementation detail but proves no unauthorized outcome.",
            "poc_steps": ["Request the resource.", "Observe the implementation detail."],
        }
        for vuln_class, detail in observations
    ]}
    candidates.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    approved, _ = verify_candidates(candidates, verified)
    result = json.loads(verified.read_text(encoding="utf-8"))
    assert approved == []
    assert result["approved"] == []
    assert result["suppressed"]["count"] == len(observations)


def test_expanded_garbage_findings_are_suppressed(tmp_path):
    candidates = tmp_path / "candidates.json"
    verified = tmp_path / "verified.json"
    observations = [
        ("Missing HTTP security headers", "X-Frame-Options, CSP and HSTS are absent."),
        ("Version disclosure", "The response exposes nginx version and X-Powered-By framework fingerprint."),
        ("Self-XSS", "The payload only executes in the attacker's own console session."),
        ("TLS warning", "The server supports a weak cipher suite but no downgrade attack is proven."),
        ("Standalone open redirect", "The redirect stays within owned subdomains and no chain is proven."),
        ("Missing rate limiting", "The login endpoint has no rate limit but no password was cracked."),
        ("Stack trace disclosure", "The error page exposes SQL error, Java class name and package path."),
        ("Origin IP disclosure", "The source IP is visible but WAF bypass and unauthorized access are not proven."),
        ("Account enumeration", "Login errors differ for existing and non-existing accounts."),
        ("Can be brute forced", "The report claims brute force is possible but no password was obtained."),
        ("AccessKeyId leak", "Only AccessKeyId is present; no AccessKeySecret exists."),
        ("Hardcoded encryption key", "The client encryption key is hardcoded but the server does not require it."),
        ("No reproducible PoC", "The observation cannot reproduce on a clean session."),
    ]
    payload = {"candidates": [
        {
            "vuln_class": vuln_class,
            "target_url": "https://example.test/lead",
            "severity": "high",
            "confidence": 1.0,
            "evidence": detail,
            "impact": "This is a low-value signal and does not prove unauthorized impact.",
            "poc_steps": ["Observe the signal.", "No exploitable outcome is reproduced."],
            "src_eligibility": src_eligibility(),
        }
        for vuln_class, detail in observations
    ]}
    candidates.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    approved, _ = verify_candidates(candidates, verified)
    result = json.loads(verified.read_text(encoding="utf-8"))
    assert approved == []
    assert result["approved"] == []
    assert result["suppressed"]["count"] == len(observations)


def test_low_value_chain_context_reports_only_final_impact(tmp_path):
    candidates = tmp_path / "candidates.json"
    verified = tmp_path / "verified.json"
    candidate = {
        "vuln_class": "Account takeover via verified password spraying chain",
        "final_vuln_class": "account takeover",
        "target_url": "https://example.test/login",
        "severity": "high",
        "confidence": 0.9,
        "evidence": "A redacted login attempt proves one authorized test account was taken over.",
        "impact": "The chain crosses the user boundary and produces account takeover on a test account.",
        "poc_steps": ["Use the verified credential pair.", "Open the account profile as the victim user."],
        "src_eligibility": src_eligibility("account_takeover"),
    }
    candidates.write_text(json.dumps({"candidates": [candidate]}, ensure_ascii=False), encoding="utf-8")

    approved, _ = verify_candidates(candidates, verified)
    assert len(approved) == 1
    assert approved[0].vuln_class == candidate["vuln_class"]
