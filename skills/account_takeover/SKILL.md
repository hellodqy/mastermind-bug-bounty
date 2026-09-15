---
name: account-takeover
description: >
  Analyze login, recovery, verification, MFA, session refresh, and account
  binding flows when a weakness may let one user assume another identity.
metadata:
  tags: "authentication,account-takeover,recovery,mfa,session"
---

# Account Takeover

## Goal

判断认证生命周期中的身份、挑战、票据与账号绑定是否错位，并用测试账号证明最终登录身份发生了非预期变化。

## Tools / Inputs

- 登录/找回/验证码/MFA/换绑入口、测试账号、会话与票据、OAuth/OIDC 回调
- 需要隔离测试邮箱时路由到 `skills/mail_code/SKILL.md`，不要在认证 Skill 中预加载接码脚本
- 资源索引：`references/INDEX.md`；候选资源：`authentication-flow-testing.md`、`oauth-oidc-saml-testing.md`

## Constraints

1. 仅使用自有测试账号和可恢复的绑定信息。
2. 不注销、吊销或锁死现有会话，不改动真实用户凭据。
3. 验证码、票据或状态参数异常必须落到最终身份变化才算成立。
4. 优先做身份绑定差分，不做无意义口令喷洒。
5. 记录正常流与异常流的主体、受众、用途和生命周期差异。

## Chain Questions

- 当前挑战绑定的是账号、会话、设备、客户端还是一次具体动作？
- 回调、刷新、换绑后服务端认定的主体是谁？
- 是否能把攻击者控制的验证材料应用到另一个测试账号？
- 新身份能否进入敏感数据、管理操作或令牌链？
