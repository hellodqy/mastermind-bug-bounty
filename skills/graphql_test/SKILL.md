---
name: graphql-test
description: >
  Treat GraphQL schemas and resolvers as expandable attack graphs.
metadata:
  tags: "graphql,api,idor"
---

# GraphQL Test

## Goal

从 schema、query、mutation、subscription 中找出对象关系、权限边界和可串联的数据路径。

## Tools / Inputs

- GraphQL endpoint、introspection、queries、fragments、tokens、schema hints
- 参考：`references/api-testing-methodology.md`

## Constraints

1. 不把 introspection 开启单独当高危，必须证明数据或动作影响。
2. 优先测试对象级授权和字段级授权。
3. mutation 只用测试账号和无害动作。
4. 发现 ID/edge/node 后回写值池。
5. 复杂查询要控制成本，避免 DoS。

## Chain Questions

- schema 暴露了哪些高价值对象和关系？
- 普通用户能否查询别人的 node/edge？
- mutation 能否执行越权动作？
- subscription 是否泄露跨用户事件？
