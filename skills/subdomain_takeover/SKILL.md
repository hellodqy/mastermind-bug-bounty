---
name: subdomain-takeover
description: >
  Verify dangling DNS delegations and deprovisioned third-party bindings when
  a scoped subdomain may be claimable and create a trusted-origin impact.
metadata:
  tags: "subdomain-takeover,dns,cname,delegation,cloud"
---

# Subdomain Takeover

## Goal

沿完整 DNS 链确认目标子域是否指向已释放且可重新绑定的资源，并在不实际抢占生产名称的前提下证明可接管性与业务影响。

## Tools / Inputs

- 作用域内子域、DNS CNAME/NS/MX 链、HTTP/TLS 指纹、云服务归属和历史记录
- 资源索引：`references/INDEX.md`；候选资源：`subdomain-takeover-testing.md`、`cloud-attack-surface.md`

## Constraints

1. CNAME、NXDOMAIN 或供应商错误页单独都不构成确认。
2. 默认不注册、绑定或接管第三方资源；优先使用非占用式证据。
3. 必须验证供应商仍允许该精确名称或自定义域绑定。
4. 分离 CNAME、子区 NS、MX 和弹性 IP 等不同信任边界。
5. 影响评估只使用已观察到的 cookie、OAuth、CSP、邮件或可信域关系。

## Chain Questions

- DNS 链最终指向谁，资源是未配置、已删除还是仅不可公开访问？
- 供应商有哪些所有权验证、保留名称或域名验证机制？
- 是否存在二阶 CNAME、子区 NS 或邮件委派？
- 可接管域是否真实处于 cookie、OAuth、CSP、邮件或品牌信任链中？
