---
name: idor-test
description: >
  Test object- and function-level authorization when identifiers, tenants,
  ownership fields, or nested resources may cross an access boundary.
metadata:
  tags: "idor,bola,bfla,authorization,tenant"
---

# IDOR Test

## Goal

建立主体—对象—动作矩阵，判断可控标识符能否造成跨用户、跨租户或跨角色的数据访问与敏感操作。

## Tools / Inputs

- 两个测试账号、对象 ID、tenant/org/user 字段、列表与详情接口、角色差异
- 资源索引：`references/INDEX.md`；候选资源：`authorization-idor-testing.md`、`response-chaining.md`

## Constraints

1. 优先只读差分；写操作只使用自建且可回滚的测试对象。
2. 不批量枚举真实用户对象。
3. HTTP 200 不是结论，必须证明返回或执行了不属于当前主体的内容。
4. 同时检查对象级、字段级、函数级和租户级边界。
5. 新 ID 与关系字段回写值池，供相关端点复测。

## Chain Questions

- 授权绑定的是路径 ID、body 字段、token claim 还是服务端关系？
- 列表、详情、附件、导出和写接口是否使用同一边界？
- 一个泄露对象能否解锁子资源、令牌、文件或管理动作？
- 当前证据跨越了哪一个明确的主体或租户边界？
