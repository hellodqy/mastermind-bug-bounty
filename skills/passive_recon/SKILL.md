---
name: passive-recon
description: >
  Collect external context without touching the target aggressively.
metadata:
  tags: "passive-recon,dns,wayback,ct"
---

# Passive Recon

## Goal

用被动来源建立目标画像，并找出值得后续主动验证的资产。

## Tools / Inputs

- DNS、证书透明度、wayback、favicon、公开搜索、历史 JS

## Constraints

1. 被动信息不是漏洞，只是线索。
2. 历史资产需要验证是否仍在线。
3. 发现历史 JS/API 后交给 JS analysis。
4. 发现子域名要按业务价值排序。
5. 避免大规模主动探测。

## Chain Questions

- 哪些历史资产可能仍指向现网后端？
- 哪些子域名像管理、测试、导出、API、SSO？
- 历史 JS 是否暴露已删除但未下线接口？
- 哪些线索值得进入 Phase 1 排序？
