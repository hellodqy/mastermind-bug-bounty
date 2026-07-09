---
name: jwt-attack
description: >
  Reason about JWT trust boundaries and whether token control can become
  privilege escalation.
metadata:
  tags: "jwt,auth,token,privilege-escalation"
---

# JWT Attack

## Goal

判断 JWT 是否能被伪造、篡改、替换或用于跨角色访问，并把成功结果回注到所有相关接口。

## Tools / Inputs

- JWT token、header/payload/signature、JS 关键字、泄露 secret、角色字段
- 资源索引：`references/INDEX.md`；候选资源：`jwt-analysis.md`

## Constraints

1. 不把“能解码 JWT”当漏洞。
2. 必须验证签名绕过、伪造或权限提升是否真实生效。
3. 成功拿到新身份后重测高价值接口。
4. 不爆破生产高风险目标；优先用已泄露或上下文词典。
5. 失败结果记录为认证边界证据。

## Chain Questions

- payload 里哪些字段控制身份、角色、租户或权限？
- secret 是否来自 JS、源码泄露或配置泄露？
- 伪造 token 能否访问管理、导出、配置或用户列表？
- 新 token 是否能扩大 value-pool linkage？
