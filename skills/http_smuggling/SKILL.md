---
name: http-smuggling
description: >
  Consider request smuggling only when architecture hints make it relevant,
  and connect confirmation to downstream impact.
metadata:
  tags: "http-smuggling,proxy,waf"
---

# HTTP Smuggling

## Goal

判断前后端解析差异是否能绕过 WAF、劫持请求、污染缓存或影响其他用户请求。

## Tools / Inputs

- Proxy/CDN/WAF headers、HTTP/1.1 support、keep-alive behavior、edge/backend hints
- 资源索引：`references/INDEX.md`；候选资源：`bypass_techniques.md`

## Constraints

1. 只在有代理/网关架构线索时测试。
2. 使用无害探针，不影响其他用户。
3. 单纯延迟异常不是报告结论，必须连接到影响。
4. 成功后优先追问 WAF bypass、cache poisoning、credential hijack。
5. 有生产风险时停止并记录 PENDING。

## Chain Questions

- 前端和后端是否解析不同？
- 是否能让后端看到前端没看到的请求？
- 能否绕过访问控制或污染缓存？
- 是否值得继续还是应保守报告风险？
