---
name: api-gateway
description: >
  Analyze gateway/backend parsing, routing, authentication, versioning, and
  batch-operation differences when an API edge may enforce a weaker boundary than its services.
metadata:
  tags: "api-gateway,reverse-proxy,routing,normalization,authorization"
---

# API Gateway

## Goal

建立客户端—网关—后端服务的解析与信任链，判断路径、方法、身份、版本或批量语义差异能否跨越实际授权边界。

## Tools / Inputs

- 网关/代理指纹、同功能路由、API 版本、methods、headers、OpenAPI/JS 线索、测试身份
- 资源索引：`references/INDEX.md`；候选资源：`api-gateway-security.md`、`api-testing-methodology.md`

## Constraints

1. 先建立正常路由和阻断基线，再改变一个解析维度。
2. 文档、网关指纹、状态码差异只是线索，必须证明数据或动作影响。
3. 路径、方法和参数差分使用无害只读接口或自建测试对象。
4. 不用批量接口影响真实用户、配额、库存或服务可用性。
5. 将后端 ID、服务名、版本和认证上下文回写攻击面队列。

## Chain Questions

- 网关和后端分别如何规范化路径、方法、重复参数和身份头？
- 同一业务能力是否存在旧版本、直连服务或批量入口？
- 授权发生在路由前还是路由后，后端是否重新验证主体和对象？
- 成功差分能否落到跨用户数据、管理动作或内部服务能力？
