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
2. 工作流 Skill: `skill(mastermind-workflow)`

所有执行以 `SKILL.md` 和 `workflow/SKILL.md` 中的四阶段定义为准，不在本命令中重复维护旧版流水线。

## Execution Contract

- Phase 0 | 资产侦察：摸清目标所有对外资产。
- Phase 1 | 攻击面分析：只分析，不动手；输出 `confidence`、`impact`、`exploitability`、`priority_score`。
- Phase 2 | 自主攻击：按优先级测试；`confidence < 0.4` 换方向，`0.4-0.7` 补证，`> 0.8` 验证利用。
- Phase 3 | 报告生成：只报告 Verifier 确认过的漏洞。

## Knowledge Loading

- 启动时只加载 Skill 元数据。
- Skill 命中后只加载对应指令层。
- 资源层通过 `references/INDEX.md` 按需读取，不预加载知识库全文。

## Output

- 所有用户可见输出使用中文。
- 结构化产出放入 `output/$1/`。
- 最终报告只包含可验证证据，不推测、不夸大。
