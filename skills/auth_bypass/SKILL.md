---
name: auth-bypass
description: >
  Reason about authorization barriers and whether blocked endpoints can
  lead to usable access.
metadata:
  tags: "auth,bypass,403,401"
---

# Auth Bypass

## Goal

把 401/403/405 当成权限边界线索，判断能不能换路径、方法、身份或上下文进入更高价值后端逻辑。

## Tools / Inputs

- Blocked endpoint queue、tokens、headers、methods、routes、gateway hints
- 资源索引：`references/INDEX.md`；候选资源：`403-bypass-complete.md`

## Constraints

1. 绕过必须服务于影响证明，不做无意义变体枚举。
2. 成功后验证实际数据或动作。
3. 优先低风险路径/方法/Header 推理，WAF 绕过最后。
4. 保留原始阻断证据和成功差异。
5. 不破坏真实数据。

## Chain Questions

- 阻断来自认证、授权、路由、方法还是网关？
- 换身份或 token 后边界是否变化？
- 成功访问后能否进入导出、配置、管理、任务执行？
- 是否该回到 JWT/OAuth/data linkage 扩大权限？
