---
name: xss-test
description: >
  Test reflected, stored, DOM, and client-rendered injection when untrusted
  data reaches an executable browser context and may affect another user.
metadata:
  tags: "xss,dom,stored,client-side,csp"
---

# XSS Test

## Goal

追踪输入到浏览器 sink 的编码与上下文变化，并证明脚本能力是否能跨用户或进入敏感会话动作。

## Tools / Inputs

- 输入点、输出上下文、DOM source/sink、前端框架、CSP、测试账号与无害回调
- 资源索引：`references/INDEX.md`；候选资源：`xss-testing.md`、`vue-spa-attacks.md`

## Constraints

1. Self-XSS 和纯文本反射不报告。
2. 使用无害标记证明执行，不窃取真实会话或数据。
3. 先判断 HTML、属性、JS、URL、CSS 或 DOM 上下文。
4. 存储型验证只影响自有测试内容和测试账号。
5. 必须说明受影响用户、触发条件和可达安全影响。

## Chain Questions

- 数据从哪个 source 经过哪些编码进入哪个 sink？
- 执行发生在攻击者本人、普通用户还是高权限用户上下文？
- CSP、sandbox、Trusted Types 或框架转义改变了哪些能力？
- 是否能连接到敏感操作、令牌访问或持久化管理界面影响？
