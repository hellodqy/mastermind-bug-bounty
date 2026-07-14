---
description: >
  启动 Mastermind Bug Bounty 四阶段自主漏洞赏金工作流。
  用法: /mastermind-bug-bounty <target_domain_or_url>
  示例: /mastermind-bug-bounty example.com
---

# Mastermind Bug Bounty — Four-Phase Launcher

目标: $1

请加载并遵循当前安装的 Skill 指令：

1. 主 Skill: `skill(mastermind-bug-bounty)`
工作流细节从主 Skill 的相对资源按需加载；不要依赖另一个顶层 `mastermind-workflow` Skill 是否被 OpenCode 单独发现。

## Execution Contract

- Phase 0 | 资产侦察：摸清目标所有对外资产。
- Phase 1 | 攻击面分析：只分析，不动手；输出 `confidence`、`impact`、`exploitability`、`priority_score`。
- Phase 2 | 自主攻击：按优先级测试；`confidence < 0.4` 换方向，`0.4 <= confidence < 0.8` 补证，`confidence >= 0.8` 验证利用。
- Phase 3 | 报告生成：只报告 Verifier 确认过的漏洞。

## Non-Negotiable Lead Gate

- 硬编码 API Token/API Key 只是线索。必须继续定位所属 API、Header/参数和可调用接口，并验证是否能读取敏感数据或执行敏感操作。
- 少量内网 IP/域名、Swagger/OpenAPI、Druid 路径只是线索。必须在授权范围内尝试与上下文匹配的路径前缀、方法、Header、认证、路由和反向代理绕过。
- 无法转化为敏感数据、敏感操作、权限提升或其他可验证安全影响时，静默丢弃。
- 禁止给失败线索定级；禁止在正文、摘要、附录、“其他发现”或收尾说明中展示。
- 最终输出前逐条反问：证据证明的是实际影响，还是只证明字符串/路径存在？后者必须删除。
- 默认拒绝收录。每个最终漏洞必须证明跨越授权/用户/权限边界，并产生可复现的未授权敏感数据、敏感操作、账号控制、提权、代码执行、资金损失、显著跨用户影响或服务失陷。
- 微服务域名、网关/服务名、PageSpy/VConsole、sourcemap、URL 中的 Token、需要认证的解密接口都只是线索。仅有可见性、设计方式或接口存在性时必须删除。
- 不输出低价值清单凑数；没有达到 SRC 收录线的结果时，明确输出“未发现达到 SRC 收录标准的漏洞”，不要附带线索列表。

## Knowledge Loading

- 启动时只加载 Skill 元数据。
- Skill 命中后只加载对应指令层。
- 资源层通过 `references/INDEX.md` 按需读取，不预加载知识库全文。

## Output

- 所有用户可见输出使用中文。
- 结构化产出放入 `output/$1/`。
- 最终报告只包含可验证证据，不推测、不夸大。
