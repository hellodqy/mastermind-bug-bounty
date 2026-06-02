"""
workflow/hooks/retry.py — Hook 5: Retry Detector

Trigger: After every specialist agent conclusion.
Detects premature surrender patterns and injects bypass strategies.
Pattern: WRITE-ONLY + retry signal. Max 3 retries per agent.
"""

from __future__ import annotations

import re

from shared.types import RetryResult


# ---------------------------------------------------------------------------
# Surrender pattern database
# ---------------------------------------------------------------------------

SURRENDER_PATTERNS: list[tuple[str, str, str]] = [
    # (regex, category, severity)
    # WAF / CDN
    (r"waf\s+detected", "waf", "high"),
    (r"blocked\s+by\s+(?:the\s+)?waf", "waf", "high"),
    (r"protected\s+by\s+(?:a\s+)?waf", "waf", "high"),
    (r"cloudflare", "cdn", "medium"),
    (r"akamai", "cdn", "medium"),
    (r"imperva", "cdn", "medium"),
    # Negative assertions
    (r"no\s+vulnerability\s+found", "negative", "high"),
    (r"appears?\s+(?:to\s+be\s+)?secure", "negative", "high"),
    (r"seems?\s+(?:to\s+be\s+)?safe", "negative", "high"),
    (r"nothing\s+(?:interesting|suspicious)\s+found", "negative", "high"),
    # Access control
    (r"403\s+forbidden", "access_control", "medium"),
    (r"401\s+unauthorized", "access_control", "medium"),
    (r"access\s+denied", "access_control", "medium"),
    # Explicit surrender
    (r"gave\s+up", "surrender", "critical"),
    (r"unable\s+to\s+(?:bypass|exploit|proceed|continue)", "surrender", "critical"),
    (r"could\s+not\s+(?:bypass|exploit|find|identify)", "surrender", "critical"),
    # Rate limit
    (r"rate[-\\s]?limit(?:ed|ing)", "rate_limit", "medium"),
    (r"too\s+many\s+requests", "rate_limit", "medium"),
    # Generic block
    (r"blocked", "blocked", "low"),
]


# ---------------------------------------------------------------------------
# Bypass strategy database: vuln_class × defense_type → strategies
# ---------------------------------------------------------------------------

BYPASS_DB: dict[str, dict[str, list[str]]] = {
    "sqli": {
        "waf": [
            "Comment obfuscation: /*!50000SELECT*/",
            "Case randomization: SeLeCt, UnIoN",
            "Unicode normalization: %C0%A0 for spaces",
            "HTTP parameter pollution: id=1&id=UNION SELECT",
            "JSON content-type bypass: Content-Type: application/json",
            "Tamper scripts: space2comment, charencode, randomcase",
        ],
        "cdn": [
            "Target origin IP directly (Shodan/Censys)",
            "Use DNS history (SecurityTrails) for unprotected origin",
            "Test via IPv6 if CDN only covers IPv4",
        ],
        "access_control": [
            "Try POST/PUT/PATCH instead of GET",
            "Add X-HTTP-Method-Override / X-Original-URL headers",
            "Path traversal: /./admin, admin../, %2e%2e%2f",
        ],
        "rate_limit": [
            "Rotate source IP via proxy pool",
            "Add random delays (2-7 seconds)",
            "Distribute across multiple sessions",
        ],
    },
    "xss": {
        "waf": [
            "Polyglot payloads",
            "HTML entity encoding: &#x3C;script&#x3E;",
            "SVG vectors: <svg onload=alert(1)>",
            "Event handlers: onpointerenter, ontoggle",
            "JavaScript template literals: ${alert(1)}",
        ],
        "access_control": [
            "Try parameter reflection in error pages",
            "Use open redirect as XSS vector",
        ],
    },
    "ssrf": {
        "waf": [
            "DNS rebinding",
            "URL encoding: %32%31%37%2e%30%2e%30%2e%31",
            "IPv6 localhost: [::1], [::ffff:127.0.0.1]",
            "Protocol smuggling: gopher://, dict://",
            "302 redirect from external server",
        ],
        "access_control": [
            "DNS-based exfiltration even if HTTP blocked",
            "IDN homograph attacks for whitelist bypass",
        ],
    },
    "idor": {
        "access_control": [
            "GUID/UUID manipulation",
            "Bulk ID enumeration: /api/users?id[]=1&id[]=2",
            "Replace numeric IDs with emails/usernames",
            "GraphQL over-fetching",
        ],
    },
    "lfi": {
        "waf": [
            "Double encoding: %252fetc%252fpasswd",
            "Unicode traversal: ..%c0%af..%c0%afetc/passwd",
            "PHP wrappers: php://filter/...",
            "Null-byte truncation (legacy PHP)",
        ],
    },
    "rce": {
        "waf": [
            "Command substitution: $(cmd) or `cmd`",
            "Concatenation: c'a't /e't'c/pa's's'wd",
            "Wildcards: /???/??t /???/p??s??",
        ],
    },
    "_default": {
        "waf": [
            "Change User-Agent to Googlebot",
            "Use HTTP/1.0 and remove unusual headers",
            "Add X-Forwarded-For: 127.0.0.1",
            "Try Content-Type switching",
        ],
        "cdn": [
            "Discover origin IP via Shodan/Censys/DNS history",
            "Test IPv6 endpoints",
            "Check SSL certificate transparency logs",
        ],
        "access_control": [
            "Try alternative HTTP verbs: POST, PUT, PATCH, OPTIONS",
            "Use X-HTTP-Method-Override header",
            "Access via API gateway if web UI restricted",
            "Path manipulation: / Admin, /admin/, /./admin, //admin",
        ],
        "rate_limit": [
            "Exponential backoff with jitter",
            "Rotate exit nodes",
            "Distribute requests across time",
        ],
        "blocked": [
            "Change User-Agent",
            "Add internal IP headers",
            "Try mobile API endpoints (less protected)",
            "Test at different times of day",
        ],
    },
}


# ---------------------------------------------------------------------------
# Detection
# ---------------------------------------------------------------------------

def detect(conclusion: str) -> RetryResult:
    """Analyze an agent conclusion for premature surrender patterns.

    Args:
        conclusion: Free-text conclusion from a specialist agent.

    Returns:
        RetryResult with detection status and bypass suggestions.
    """
    text = conclusion.lower()
    matched: list[str] = []
    categories: dict[str, int] = {}

    for pattern, category, severity in SURRENDER_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            matched.append(pattern)
            categories[category] = categories.get(category, 0) + 1

    if not matched:
        return RetryResult(surrender_detected=False)

    # Primary category = most frequently matched
    primary = max(categories, key=categories.get) if categories else "blocked"

    return RetryResult(
        surrender_detected=True,
        matched_patterns=matched,
        category=primary,
    )


# ---------------------------------------------------------------------------
# Bypass suggestion engine
# ---------------------------------------------------------------------------

def suggest_bypasses(vuln_class: str, defense_category: str) -> list[str]:
    """Return bypass strategies for a given vuln class and defense type.

    Args:
        vuln_class: e.g. 'sqli', 'xss', 'ssrf', 'idor'
        defense_category: e.g. 'waf', 'cdn', 'access_control', 'rate_limit'
    """
    canonical = _normalize_class(vuln_class)
    class_strategies = BYPASS_DB.get(canonical, BYPASS_DB["_default"])
    return class_strategies.get(defense_category) or \
        class_strategies.get("blocked") or \
        BYPASS_DB["_default"].get(defense_category, [])


def _normalize_class(vuln_class: str) -> str:
    """Map free-text vuln class labels to canonical keys."""
    mapping = {
        "sqli": "sqli", "sql_injection": "sqli", "sql injection": "sqli",
        "xss": "xss", "cross-site scripting": "xss",
        "ssrf": "ssrf", "server-side request forgery": "ssrf",
        "idor": "idor", "insecure direct object reference": "idor",
        "lfi": "lfi", "local file inclusion": "lfi",
        "path_traversal": "lfi", "path traversal": "lfi",
        "rce": "rce", "remote code execution": "rce",
        "command_injection": "rce", "command injection": "rce",
        "ssti": "rce", "template injection": "rce",
    }
    return mapping.get(vuln_class.lower().strip(), "_default")


# ---------------------------------------------------------------------------
# Retry prompt builder
# ---------------------------------------------------------------------------

def build_retry_prompt(conclusion: str, suggestions: list[str],
                       retry_count: int) -> str:
    """Build a retry prompt for the agent that surrendered.

    Args:
        conclusion: The agent's surrender conclusion.
        suggestions: Bypass strategies from suggest_bypasses().
        retry_count: Current retry number (1-3).
    """
    urgency = {
        1: "Attempt each bypass strategy systematically.",
        2: "CRITICAL: You have 1 more retry. Be exhaustive.",
    }.get(retry_count, "FINAL ATTEMPT. Document everything.")

    lines = [
        "# ⚠️ RETRY REQUIRED — Premature Surrender Detected",
        "",
        "## Your Conclusion Was",
        f"> {conclusion[:300]}",
        "",
        f"**Retry #{retry_count}/3**",
        "",
        "## Bypass Strategies to Attempt",
    ]

    for i, s in enumerate(suggestions, 1):
        lines.append(f"{i}. {s}")

    lines.extend([
        "",
        "## Instructions",
        f"1. {urgency}",
        "2. Document every attempt with request/response.",
        "3. If one fails, move to the next — do NOT stop.",
        "4. Report IMPACT, not just detection.",
        "5. If ALL strategies fail, document why each failed with evidence.",
        "",
        "**You are not done until impact is demonstrated or every "
        "strategy is exhaustively attempted.**",
    ])

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def analyze(conclusion: str, vuln_class: str = "",
            retry_count: int = 0) -> RetryResult:
    """Full retry analysis: detect + suggest + build prompt.

    Args:
        conclusion: Agent's conclusion text.
        vuln_class: Vulnerability class being tested.
        retry_count: How many retries already attempted.

    Returns:
        RetryResult with surrender_detected, suggestions, and retry_prompt.
    """
    result = detect(conclusion)

    if not result.surrender_detected:
        return result

    result.bypass_suggestions = suggest_bypasses(vuln_class, result.category)
    result.should_retry = retry_count < 3
    result.retry_prompt = build_retry_prompt(
        conclusion, result.bypass_suggestions, retry_count + 1
    )

    return result
