---
name: dependency-cve
description: >
  Map observed technologies to plausible CVE paths, then require safe
  verification before promotion.
metadata:
  tags: "dependency,cve,fingerprint"
---

# Dependency CVE

## Goal

把版本、框架、组件指纹转成可验证的漏洞假设，而不是直接按版本号报漏洞。

## Tools / Inputs

- Headers、cookies、JS libraries、error pages、default paths、source leak versions
- 资源索引：`references/INDEX.md`；候选资源：`cve-chains.md`、`fingerprint-mapping.md`

## Constraints

1. 版本命中不是漏洞，必须安全验证。
2. 不执行破坏性 PoC。
3. Unknown stack 不盲打高危 payload。
4. 能用低风险 OOB/只读证据时优先。
5. 验证失败记录为 INFO/PENDING。

## Chain Questions

- 这个组件是否暴露了对应入口？
- CVE 是否需要认证、特定配置或特定路径？
- 成功验证后能否导向数据读取、配置泄露、RCE 或凭据获取？
- 失败是否仍提供技术栈信息给其他攻击面？
