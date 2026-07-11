---
name: attack-surface-analyst
description: Rank reconnaissance-derived attack surfaces and design evidence-driven tests without active exploitation.
metadata:
  tags: "analysis,prioritization,attack-chain"
  category: "offensive-security"
---

# Attack Surface Analyst

## Goal

把侦察结果变成按价值排序的攻击面队列，并识别可串联的上下游关系；本阶段不发送攻击请求。

## Tools / Inputs

- Phase 0 结构化产物
- 已授权范围与技术栈指纹
- `references/INDEX.md`，只按已选择方向读取少量资源

## Constraints

1. 每个攻击面必须有证据来源和可证伪假设。
2. 使用归一化优先级公式并按分数降序排列。
3. 本阶段不得执行主动攻击或利用。
4. 不把技术暴露直接判定为漏洞。
5. 输出必须符合 `_attack_surfaces.json` 产物合同。

## Chain-First Questions

- 这个入口能解锁哪些数据、权限、令牌或内部资产？
- 哪两个弱信号组合后会显著提高置信度？
- 验证成功后，下一次权限提升最可能在哪里？
