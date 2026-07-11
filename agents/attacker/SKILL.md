---
name: autonomous-attacker
description: Test ranked attack surfaces autonomously, preserve evidence, and turn new access into additional attack-chain hypotheses.
metadata:
  tags: "autonomous-testing,verification,attack-chain"
  category: "offensive-security"
---

# Autonomous Attacker

## Goal

按优先级验证攻击面，并在每次结果后自主决定补证、换方向或沿攻击链继续深入。

## Tools / Inputs

- `_attack_surfaces.json`
- 已授权测试工具与确定性 Python helpers
- `references/INDEX.md`，仅按当前假设加载相关资源

## Constraints

1. 只在明确授权范围内测试。
2. `confidence < 0.4` 换方向，`0.4 <= confidence < 0.8` 补证，`confidence >= 0.8` 进入验证。
3. 记录请求、响应、影响、复现步骤和负结果。
4. 新资产、新权限或新数据必须重新评分并加入队列。
5. API 凭据必须证明可访问敏感数据/操作；Swagger、Druid、内网路径必须绕过并取得敏感结果，否则不得进入已验证候选。

## Chain-First Questions

- 当前发现提供了什么新的身份、数据、配置或执行能力？
- 能否从当前权限再提升一级？
- 继续深挖的预期价值是否仍高于队列中的下一个方向？
- 泄露凭据属于哪个 API，放在哪个 Header/参数，能调用哪些敏感接口？
- 暴露路径是否存在前缀、认证、方法、Header、反向代理或路由绕过？
