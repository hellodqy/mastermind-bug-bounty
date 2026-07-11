"""SRC-oriented reportability policy applied before vulnerability triage."""

from __future__ import annotations

from shared.types import Finding


MAP_KEY_MARKERS = (
    "baidu map", "baidu maps", "百度地图", "amap", "高德地图",
    "google maps", "mapbox", "腾讯地图", "map api", "地图 api",
)
CORS_MARKERS = (
    "cors", "cross-origin", "cross origin", "跨域", "access-control-allow-origin",
)
INTERNAL_METADATA_MARKERS = (
    "internal network architecture", "internal architecture", "service routing",
    "internal ip", "internal domain", "内网架构", "服务路由", "内网 ip",
    "内网ip", "内网域名", "内部网络架构",
)
DOCUMENTATION_EXPOSURE_MARKERS = (
    "swagger", "openapi", "api documentation", "接口文档", "接口路径暴露",
    "druid", "database pool monitor", "数据库连接池监控",
)
API_CREDENTIAL_MARKERS = (
    "api key", "apikey", "api token", "access token", "hardcoded token",
    "hard-coded token", "硬编码 token", "硬编码token", "api 密钥", "api密钥",
)
NON_EXPLOITABLE_MARKERS = (
    "not exploitable", "cannot be exploited", "no demonstrated impact",
    "无法利用", "不可利用", "无实际影响", "未证明影响",
)
INFORMATION_DISCLOSURE_MARKERS = (
    "information disclosure", "information leak", "data exposure",
    "信息泄露", "信息洩露", "数据泄露", "資料洩露",
)
SECURITY_SENSITIVE_MARKERS = (
    "password", "credential", "private key", "secret key", "session token",
    "access token", "jwt", "cookie", "personal data", "identity", "id card",
    "phone number", "bank", "payment", "order record", "database record",
    "source code", "database dump", "密码", "凭据", "私钥", "密钥",
    "会话", "令牌", "身份证", "手机号", "银行卡", "支付", "订单数据",
    "数据库记录", "源代码",
)


def _credential_has_proven_outcome(candidate: dict | None) -> bool:
    validation = (candidate or {}).get("credential_validation", {})
    return bool(
        isinstance(validation, dict)
        and validation.get("tested") is True
        and validation.get("usable") is True
        and validation.get("sensitive_outcome") is True
        and validation.get("endpoint")
        and validation.get("request_evidence")
        and validation.get("outcome_type") in {"sensitive_data", "sensitive_action"}
    )


def _exposure_has_proven_outcome(candidate: dict | None) -> bool:
    validation = (candidate or {}).get("exposure_validation", {})
    return bool(
        isinstance(validation, dict)
        and validation.get("bypass_attempted") is True
        and validation.get("access_achieved") is True
        and validation.get("sensitive_outcome") is True
        and validation.get("endpoint")
        and validation.get("request_evidence")
        and validation.get("outcome_type") in {"sensitive_data", "sensitive_action"}
    )


def exclusion_reason(finding: Finding, candidate: dict | None = None) -> str | None:
    """Return a suppression reason for classes that are not SRC findings."""
    text = " ".join((
        finding.vuln_class,
        finding.target_url,
        finding.evidence,
        finding.impact,
    )).lower()

    if any(marker in text for marker in CORS_MARKERS):
        return "CORS configuration findings are excluded by the active SRC policy."
    if any(marker in text for marker in MAP_KEY_MARKERS):
        return "Client-side map API keys are expected public identifiers and are excluded."
    if any(marker in text for marker in API_CREDENTIAL_MARKERS):
        if not _credential_has_proven_outcome(candidate):
            return "API credentials without verified sensitive data access or a sensitive operation are excluded."
    if any(marker in text for marker in INTERNAL_METADATA_MARKERS + DOCUMENTATION_EXPOSURE_MARKERS):
        if not _exposure_has_proven_outcome(candidate):
            return "Internal metadata or exposed documentation/monitoring paths without a successful sensitive bypass are excluded."
    if any(marker in text for marker in NON_EXPLOITABLE_MARKERS):
        return "Non-exploitable information disclosure is excluded."
    if (
        any(marker in text for marker in INFORMATION_DISCLOSURE_MARKERS)
        and not any(marker in text for marker in SECURITY_SENSITIVE_MARKERS)
    ):
        return "Generic information disclosure without security-sensitive data or demonstrated exploitation is excluded."
    return None
