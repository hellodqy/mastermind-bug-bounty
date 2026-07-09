---
name: prototype-pollution
description: >
  Reason about object merge behavior and whether pollution reaches an
  exploitable gadget.
metadata:
  tags: "prototype-pollution,node,client-side"
---

# Prototype Pollution

## Goal

判断用户可控对象是否能污染原型，并进一步到达鉴权绕过、配置篡改、XSS 或 RCE gadget。

## Tools / Inputs

- JSON body、query parser、merge/clone/update functions、client state
- 资源索引：`references/INDEX.md`；候选资源：`bug_classes.md`

## Constraints

1. 污染存在不等于漏洞，必须找到 gadget 或安全影响。
2. 用无害属性验证，不破坏运行状态。
3. 区分服务端、客户端、构建时污染。
4. 成功后追问能控制哪些配置、模板、权限或路径。
5. 不能证明 gadget 时标记 PENDING。

## Chain Questions

- 污染能否持久化到后续请求或其他用户？
- 哪些代码读取了被污染属性？
- 是否能影响 sanitizer、模板、权限、命令或路径？
- 是否能和 XSS/SSRF/RCE 串联？
