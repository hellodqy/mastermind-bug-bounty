---
name: cache-poisoning
description: >
  Analyze cache key confusion as a path to stored impact.
metadata:
  tags: "cache,poisoning,cdn"
---

# Cache Poisoning

## Goal

判断未进入 cache key 的 Header/参数是否能改变缓存响应，并产生可验证的持久影响。

## Tools / Inputs

- CDN/cache headers、Host/X-Forwarded-*、query params、static/dynamic responses
- 参考：`references/bypass_techniques.md`

## Constraints

1. 不向生产用户投递恶意内容。
2. 使用自控无害标记证明污染。
3. 必须证明缓存命中和跨请求可见。
4. 不把 header reflection 单独当漏洞。
5. 成功后追问 XSS、redirect、credential leakage、DoS 风险。

## Chain Questions

- 哪些输入影响响应但不影响 cache key？
- 污染是否可被其他用户命中？
- 影响能否升级为脚本执行、跳转、敏感信息暴露？
- 是否存在更安全的证明方式？
