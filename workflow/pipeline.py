"""
workflow/pipeline.py — Four-phase autonomous pipeline.

Phase 0: ASSET_RECON
Phase 1: ATTACK_SURFACE_ANALYSIS
Phase 2: AUTONOMOUS_ATTACK
Phase 3: REPORT_GENERATION
"""

from dataclasses import dataclass, field


@dataclass
class Phase:
    name: str
    agent: str
    description: str = ""
    skills: list[str] = field(default_factory=list)
    depends_on: list[str] = field(default_factory=list)
    optional: bool = False
    ai_directive: str = ""


PIPELINE: list[Phase] = [
    Phase(
        name="asset_recon",
        agent="recon",
        description=(
            "Phase 0 | 资产侦察: 摸清目标所有对外资产。Python执行确定性采集: "
            "JS/sourcemap下载、API端点提取、Swagger暴露探测、常见路径字典。"
        ),
        skills=["js_analysis", "source_leak", "passive_recon", "dependency_cve"],
        ai_directive=(
            "摸清这个目标所有对外资产。可使用 DNS解析、子域名枚举、JS下载、"
            "代码泄露搜索等工具；方法和顺序由AI自行决定。"
        ),
    ),
    Phase(
        name="attack_surface_analysis",
        agent="analyst",
        description=(
            "Phase 1 | 攻击面分析: 基于侦察结果排序攻击面、说明原因、设计测试方向、"
            "判断是否能串成攻击链。本阶段只分析，不动手测试。"
        ),
        skills=[
            "data_linkage", "api_fuzz", "crypto_attack", "jwt_attack",
            "auth_bypass", "vuln_classes", "graphql_test",
        ],
        depends_on=["asset_recon"],
        ai_directive=(
            "基于侦察结果，自主排序最高价值攻击面，说明优先级、测试假设、"
            "预计证据和可能攻击链。每个假设必须给出confidence、impact、"
            "exploitability和priority_score。本阶段禁止实际攻击。"
        ),
    ),
    Phase(
        name="autonomous_attack",
        agent="attacker",
        description=(
            "Phase 2 | 自主攻击: 按优先级循环测试。AI自主决定继续、换方向或收手；"
            "测完所有面、确认高危、或连续五次无进展才停止。"
        ),
        skills=[
            "api_fuzz", "data_linkage", "crypto_attack", "jwt_attack",
            "auth_bypass", "oauth_sso", "race_condition", "websocket_test",
            "http_smuggling", "cache_poisoning", "prototype_pollution",
            "vuln_classes",
        ],
        depends_on=["attack_surface_analysis"],
        ai_directive=(
            "按优先级逐个测，每测完一个自己判断继续、换方向还是收手；"
            "confidence低于0.4换方向，0.4到0.8之间补证，达到0.8验证利用；"
            "不要询问是否继续。只有测完所有攻击面、找到确定高危、或连续五次没进展才停。"
        ),
    ),
    Phase(
        name="report_generation",
        agent="report",
        description=(
            "Phase 3 | 报告生成: 固定模板输出。只报告 Verifier 确认过的漏洞；"
            "证据必须可验证，不推测不夸大。"
        ),
        skills=["report", "vuln_classes"],
        depends_on=["autonomous_attack"],
        ai_directive=(
            "按固定模板生成报告: 标题、漏洞类型、危害等级、URL、复现步骤、"
            "证据、修复建议。只写已验证项。"
        ),
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
