---
name: oauth-sso
description: >
  Analyze OAuth/OIDC/SSO flows as identity-chain attack surfaces.
metadata:
  tags: "oauth,oidc,sso,identity"
---

# OAuth / SSO

## Goal

判断登录、授权、回调、token 交换和账号绑定流程是否能导致身份混淆、会话固定、越权登录或权限提升。

## Tools / Inputs

- login URL、authorize URL、redirect_uri、state、code、id_token、callback
- 资源索引：`references/INDEX.md`；候选资源：`decision-trees.md`

## Constraints

1. 只用测试账号验证身份链。
2. 不修改真实用户绑定状态。
3. 每个 OAuth 异常必须证明最终登录身份或权限变化。
4. state/redirect/token 问题要串到实际账号影响。
5. 发现新 token 后回注 API/JWT 测试。

## Chain Questions

- 谁控制 redirect_uri、state、code、token、account binding？
- 是否能把攻击者会话绑定给受害者？
- 是否能把普通身份升级到管理员或企业身份？
- token 能不能调用后端 API？
