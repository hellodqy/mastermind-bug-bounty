"""
workflow/pipeline.py — 6-Phase Pipeline (v3.1)

Aligned with SKILL.md §1.2 and shared/types.py PhaseName enum.
Phase 0: RECON (collect+analyze tasks) → Phase 1: DEPENDENCY_SCAN
→ Phase 2: API_FUZZ (test tasks) → Phase 3: CRYPTO_ATTACK
→ Phase 4: BYPASS → Phase 5: EXPLOIT
Optional: AI_SECURITY
"""

from shared.types import PhaseName
from dataclasses import dataclass, field


@dataclass
class Phase:
    name: str           # Must match PhaseName enum values
    agent: str
    description: str = ""
    skills: list[str] = field(default_factory=list)
    depends_on: list[str] = field(default_factory=list)
    optional: bool = False


PIPELINE: list[Phase] = [
    # ── Phase 0: RECON ──
    Phase(
        name="recon", agent="recon",
        description="RECON: chrome-devtools navigate + snow_eyes + download JS + fingerprint + source leak + deep-read JS + build _endpoint_params.json with completeness gate",
        skills=["js_analysis", "source_leak", "passive_recon"],
    ),
    # ── Phase 1: DEPENDENCY_SCAN ──
    Phase(
        name="dependency_scan", agent="recon",
        description="DEPENDENCY_SCAN: extract versions from JS/headers/cookies/error-pages → match CVE (Log4j/Shiro/Fastjson/Spring Boot) → OOB verify",
        skills=["dependency_cve"],
        depends_on=["recon"],
    ),
    # ── Phase 2: API_FUZZ ──
    Phase(
        name="api_fuzz", agent="api_fuzz",
        description="API_FUZZ: blind probe ALL endpoints → mine 200 responses → value pool linkage with PairingEngine (41 aliases) + method fallback matrix → pair completeness gate",
        skills=["api_fuzz", "data_linkage", "graphql_test"],
        depends_on=["recon"],
    ),
    # ── Phase 3: CRYPTO_ATTACK ──
    Phase(
        name="crypto_attack", agent="crypto_attack",
        description="CRYPTO_ATTACK: extract AES/DES/RSA keys from JS → decrypt captured ciphertext → JWT attack (alg:none, key brute, kid inject, RS256→HS256) → inject plaintext into value pool",
        skills=["crypto_attack", "jwt_attack", "http_smuggling", "cache_poisoning", "prototype_pollution"],
        depends_on=["api_fuzz"],
    ),
    # ── Phase 4: BYPASS ──
    Phase(
        name="bypass", agent="bypass",
        description="BYPASS: 401/403 bypass (path manipulation, method switch, header injection, protocol downgrade) + OAuth/SSO attack + CDN/cache poisoning",
        skills=["auth_bypass", "oauth_sso"],
        depends_on=["api_fuzz"],
    ),
    # ── Phase 5: EXPLOIT ──
    Phase(
        name="exploit", agent="exploit",
        description="EXPLOIT: P0 CVE/JWT admin/IDOR value pool/SSRF/race condition → P1 SQLi/SSTI/RCE/upload → P2 XSS/CSRF/CORS → report generation",
        skills=["vuln_classes", "race_condition", "websocket_test"],
        depends_on=["crypto_attack", "bypass"],
    ),
    # ── Optional: AI_SECURITY ──
    Phase(
        name="ai_security", agent="ai_security",
        description="AI_SECURITY (optional): prompt injection, jailbreak, MCP abuse, RAG poisoning — only triggered for AI/LLM targets",
        skills=["ai_security"],
        depends_on=["recon"],
        optional=True,
    ),
]


def get_phase(name: str) -> Phase | None:
    for p in PIPELINE:
        if p.name == name:
            return p
    return None


def get_next_phase(current: str) -> Phase | None:
    names = [p.name for p in PIPELINE]
    try:
        idx = names.index(current)
        return PIPELINE[idx + 1] if idx + 1 < len(PIPELINE) else None
    except ValueError:
        return None
