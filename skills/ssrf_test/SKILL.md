---
name: ssrf-test
description: >
  Test server-side URL retrieval, callback, proxy, import, and preview features
  for network-boundary crossing and credential or metadata access.
metadata:
  tags: "ssrf,url-fetch,callback,metadata,internal-network"
---

# SSRF Test

## Goal

判断服务端请求能力是否允许跨越预期的协议、主机、解析或云网络边界，并证明可访问的敏感能力。

## Tools / Inputs

- URL/host/callback 参数、重定向链、DNS/OOB 证据、云与内网指纹
- 资源索引：`references/INDEX.md`；候选资源：`ssrf-testing.md`、`cloud-attack-surface.md`

## Constraints

1. 先使用自控回连或无害目标确认服务端请求。
2. 不进行内网大范围扫描。
3. DNS 命中本身只证明请求线索，需继续证明可读取或调用的敏感结果。
4. 分开验证解析、重定向、协议和响应回显边界。
5. 获取的凭据只做最小权限与影响验证。

## Chain Questions

- 请求由哪个网络位置、身份和协议栈发出？
- 校验发生在解析、重定向之前还是之后？
- 是否能读取响应、命中云元数据或调用内部管理接口？
- 得到的新 URL、token 或服务名应回注哪个攻击面？
