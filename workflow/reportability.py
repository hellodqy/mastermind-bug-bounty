"""SRC-oriented reportability policy applied before vulnerability triage."""

from __future__ import annotations

from shared.types import Finding


SRC_OUTCOME_TYPES = {
    "unauthorized_sensitive_data",
    "unauthorized_sensitive_action",
    "account_takeover",
    "privilege_escalation",
    "code_execution",
    "financial_loss",
    "meaningful_cross_user_impact",
    "service_compromise",
}


MAP_KEY_MARKERS = (
    "baidu map", "baidu maps", "amap", "google maps", "mapbox",
    "tencent map", "map api", "地图 api", "地图api", "百度地图", "高德地图",
    "腾讯地图",
)
CORS_MARKERS = (
    "cors", "cross-origin", "cross origin", "access-control-allow-origin",
    "acao", "acac", "跨域",
)
SECURITY_HEADER_MARKERS = (
    "missing security header", "security headers", "x-frame-options", "csp",
    "content-security-policy", "hsts", "strict-transport-security",
    "x-content-type-options", "referrer-policy", "安全头", "安全响应头",
)
FINGERPRINT_MARKERS = (
    "version disclosure", "version leak", "framework fingerprint",
    "middleware fingerprint", "server banner", "x-powered-by", "server version",
    "版本号", "框架指纹", "中间件", "服务端指纹", "组件版本",
)
SELF_XSS_MARKERS = (
    "self-xss", "self xss", "self triggered xss", "自我xss", "自触发xss",
)
TLS_WARNING_MARKERS = (
    "ssl warning", "tls warning", "weak cipher", "cipher suite",
    "certificate warning", "ssl/tls", "tls 配置", "ssl 配置", "弱加密套件",
)
OPEN_REDIRECT_MARKERS = (
    "open redirect", "url redirect", "redirect vulnerability", "开放重定向",
    "url跳转", "url 跳转", "任意跳转", "域内跳转",
)
RATE_LIMIT_MARKERS = (
    "rate limit", "rate limiting", "no rate limit", "missing rate limit",
    "缺少频率限制", "频率限制缺失", "未限制请求频率",
)
INTERNAL_METADATA_MARKERS = (
    "internal network architecture", "internal architecture", "service routing",
    "internal ip", "internal domain", "microservice architecture",
    "microservice domain", "backend service domain", "gateway information",
    "internal service name", "source ip", "origin ip", "real ip", "egress ip",
    "server origin", "内网架构", "服务路由", "内网 ip", "内网ip", "内网域名",
    "内部网络架构", "微服务架构", "微服务域名", "后端微服务", "网关信息",
    "内部服务名", "源站 ip", "源站ip", "出口 ip", "出口ip", "真实 ip", "真实ip",
)
DOCUMENTATION_EXPOSURE_MARKERS = (
    "swagger", "openapi", "api documentation", "api docs", "druid",
    "database pool monitor", "actuator", "接口文档", "接口路径暴露",
    "数据库连接池监控",
)
API_CREDENTIAL_MARKERS = (
    "api key", "apikey", "api token", "access token", "hardcoded token",
    "hard-coded token", "hardcoded api", "硬编码 token", "硬编码token",
    "api 密钥", "api密钥",
)
DEBUG_ARTIFACT_MARKERS = (
    "pagespy", "vconsole", "eruda", "remote debug", "debug console",
    "调试工具", "远程调试", "调试控制台",
)
SOURCE_ARTIFACT_MARKERS = (
    "sourcemap", "source map", ".js.map", "source comment", "source code comment",
    "path disclosure", "源码映射", "源码注释", "路径泄露",
)
TOKEN_TRANSPORT_MARKERS = (
    "token url", "token in url", "token query", "?token=", "url token",
    "url 传输", "url传输", "url 中传递", "url中传递",
)
AUTHENTICATED_UTILITY_MARKERS = (
    "decrypt api", "decryption api", "security/decrypt", "utility api",
    "authenticated utility", "解密 api", "解密接口", "工具类 api",
)
ERROR_PAGE_MARKERS = (
    "stack trace", "sql error", "debug information", "debug info",
    "exception page", "java class", "package path", "internal class name",
    "internal package", "报错页面", "堆栈", "sql 错误", "sql错误", "调试信息",
    "异常页面", "java 类名", "java类名", "包路径",
)
ACCOUNT_ENUMERATION_MARKERS = (
    "account enumeration", "username enumeration", "user enumeration",
    "differential error", "账号枚举", "用户名枚举", "差异化错误",
)
BRUTE_FORCE_MARKERS = (
    "brute force", "bruteforce", "password guessing", "can be brute forced",
    "可爆破", "爆破", "弱口令猜测",
)
ACCESS_KEY_ID_ONLY_MARKERS = (
    "accesskeyid", "access key id", "access_key_id", "akid", "单独 accesskeyid",
)
ACCESS_KEY_SECRET_MARKERS = (
    "accesskeysecret", "access key secret", "access_key_secret", "secretaccesskey",
)
NO_SECRET_MARKERS = (
    "no accesskeysecret", "without accesskeysecret", "no access key secret",
    "without access key secret", "no secret", "without secret", "missing secret",
    "无 accesskeysecret", "没有 accesskeysecret", "无 secret", "没有 secret",
)
CRYPTO_LAYER_MARKERS = (
    "hardcoded encryption key", "hard-coded encryption key", "client encryption key",
    "encryption key hardcoded", "加密密钥硬编码", "硬编码加密密钥", "前端加密密钥",
)
NO_REPRO_MARKERS = (
    "no reproducible poc", "not reproducible", "cannot reproduce", "unreproducible",
    "无可重现 poc", "无可复现 poc", "不能重现", "无法复现", "不可复现",
)
NON_EXPLOITABLE_MARKERS = (
    "not exploitable", "cannot be exploited", "no demonstrated impact",
    "non-exploitable", "无法利用", "不可利用", "无实际影响", "未证明影响",
)
INFORMATION_DISCLOSURE_MARKERS = (
    "information disclosure", "information leak", "data exposure",
    "信息泄露", "信息泄漏", "数据泄露", "资料泄露",
)
SECURITY_SENSITIVE_MARKERS = (
    "password", "credential", "private key", "secret key", "session token",
    "access token", "jwt", "cookie", "personal data", "identity", "id card",
    "phone number", "bank", "payment", "order record", "database record",
    "source code", "database dump", "密码", "凭据", "私钥", "密钥", "会话",
    "令牌", "身份证", "手机号", "银行卡", "支付", "订单数据", "数据库记录",
    "源代码",
)


def _has_src_eligible_outcome(candidate: dict | None) -> bool:
    eligibility = (candidate or {}).get("src_eligibility", {})
    return bool(
        isinstance(eligibility, dict)
        and eligibility.get("boundary_crossed") is True
        and eligibility.get("reproducible") is True
        and eligibility.get("outcome_type") in SRC_OUTCOME_TYPES
        and eligibility.get("affected_asset")
        and eligibility.get("evidence")
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


def _artifact_has_proven_outcome(candidate: dict | None) -> bool:
    validation = (candidate or {}).get("artifact_validation", {})
    return bool(
        isinstance(validation, dict)
        and validation.get("inspected") is True
        and validation.get("sensitive_outcome") is True
        and validation.get("request_evidence")
        and validation.get("outcome_type") in {"sensitive_data", "sensitive_action"}
    )


def _token_transport_has_proven_outcome(candidate: dict | None) -> bool:
    validation = (candidate or {}).get("token_transport_validation", {})
    return bool(
        isinstance(validation, dict)
        and validation.get("third_party_exposure_proven") is True
        and validation.get("token_replayable") is True
        and validation.get("sensitive_outcome") is True
        and validation.get("request_evidence")
    )


def _contains_any(text: str, markers: tuple[str, ...]) -> bool:
    return any(marker in text for marker in markers)


def _chain_result_is_reported_as_real_vuln(candidate: dict | None) -> bool:
    """Allow chain context only when the final class is the real impact."""
    if not _has_src_eligible_outcome(candidate):
        return False
    final_class = str((candidate or {}).get("final_vuln_class", "")).lower()
    if not final_class:
        return False
    return _contains_any(
        final_class,
        (
            "idor", "authorization", "auth bypass", "privilege", "rce",
            "code execution", "injection", "ssrf", "account takeover",
            "data leak", "sensitive data", "越权", "提权", "注入", "代码执行",
            "账号接管", "敏感数据", "数据窃取",
        ),
    )


def exclusion_reason(finding: Finding, candidate: dict | None = None) -> str | None:
    """Return a suppression reason for classes that are not SRC findings."""
    text = " ".join((
        finding.vuln_class,
        finding.target_url,
        finding.evidence,
        finding.impact,
    )).lower()

    if _contains_any(text, CORS_MARKERS):
        return "CORS configuration findings are excluded unless reported as a proven data-theft chain result."
    if _contains_any(text, MAP_KEY_MARKERS):
        return "Client-side map API keys are expected public identifiers and are excluded."
    if _contains_any(text, SECURITY_HEADER_MARKERS):
        return "Missing HTTP security headers are theoretical hardening issues and are excluded."
    if _contains_any(text, FINGERPRINT_MARKERS):
        return "Version, middleware, and framework fingerprints are reconnaissance context and are excluded."
    if _contains_any(text, SELF_XSS_MARKERS):
        return "Self-XSS without a real victim path is excluded."
    if _contains_any(text, TLS_WARNING_MARKERS):
        return "SSL/TLS configuration warnings without a proven downgrade or sensitive impact are excluded."
    if _contains_any(text, OPEN_REDIRECT_MARKERS) and not _chain_result_is_reported_as_real_vuln(candidate):
        return "Standalone open redirects are excluded unless the final reportable chain impact is proven."
    if _contains_any(text, RATE_LIMIT_MARKERS):
        return "Missing rate limiting by itself is a product hardening suggestion and is excluded."
    if _contains_any(text, ACCOUNT_ENUMERATION_MARKERS) and not _chain_result_is_reported_as_real_vuln(candidate):
        return "Standalone account enumeration is excluded unless it forms a proven takeover chain."
    if _contains_any(text, BRUTE_FORCE_MARKERS) and not _chain_result_is_reported_as_real_vuln(candidate):
        return "Brute-force risk without a successfully verified credential compromise is excluded."
    has_access_key_secret = (
        _contains_any(text, ACCESS_KEY_SECRET_MARKERS)
        and not _contains_any(text, NO_SECRET_MARKERS)
    )
    if _contains_any(text, ACCESS_KEY_ID_ONLY_MARKERS) and not has_access_key_secret:
        return "AccessKeyId without AccessKeySecret cannot call cloud APIs and is excluded."
    if _contains_any(text, CRYPTO_LAYER_MARKERS) and not _chain_result_is_reported_as_real_vuln(candidate):
        return "Hardcoded encryption keys without a server-side enforcement bypass or added attack surface are excluded."
    if _contains_any(text, NO_REPRO_MARKERS):
        return "Findings without a reproducible PoC are excluded."
    if not _has_src_eligible_outcome(candidate):
        return "No reproducible SRC-eligible authorization boundary and concrete security outcome were proven."
    if _contains_any(text, API_CREDENTIAL_MARKERS):
        if not _credential_has_proven_outcome(candidate):
            return "API credentials without verified sensitive data access or a sensitive operation are excluded."
    if _contains_any(text, INTERNAL_METADATA_MARKERS + DOCUMENTATION_EXPOSURE_MARKERS):
        if not _exposure_has_proven_outcome(candidate):
            return "Internal metadata or exposed documentation/monitoring paths without a successful sensitive bypass are excluded."
    if _contains_any(text, DEBUG_ARTIFACT_MARKERS + SOURCE_ARTIFACT_MARKERS):
        if not _artifact_has_proven_outcome(candidate):
            return "Debug tooling, source maps, comments, or path visibility without extracted sensitive impact are excluded."
    if _contains_any(text, TOKEN_TRANSPORT_MARKERS):
        if not _token_transport_has_proven_outcome(candidate):
            return "A token in a URL without proven third-party disclosure, replay, and sensitive impact is excluded."
    if _contains_any(text, AUTHENTICATED_UTILITY_MARKERS):
        return "An authenticated utility/decryption endpoint without authorization bypass is excluded."
    if _contains_any(text, ERROR_PAGE_MARKERS) and not _chain_result_is_reported_as_real_vuln(candidate):
        return "Error pages, stack traces, SQL errors, Java class names, and package paths are excluded without a working PoC."
    if _contains_any(text, NON_EXPLOITABLE_MARKERS):
        return "Non-exploitable information disclosure is excluded."
    if (
        _contains_any(text, INFORMATION_DISCLOSURE_MARKERS)
        and not _contains_any(text, SECURITY_SENSITIVE_MARKERS)
    ):
        return "Generic information disclosure without security-sensitive data or demonstrated exploitation is excluded."
    return None
