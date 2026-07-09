---
name: source-leak
description: >
  Search public code and metadata for credentials, identifiers, internal
  routes, and business context that can feed later testing.
metadata:
  tags: "source-leak,github,gitee,credentials"
---

# Source Leak

## Goal

从公开代码、提交记录、Issue、PR 和缓存中找能回注目标系统的标识符、凭据、内部路径和业务语义。

## Tools / Inputs

- GitHub/Gitee/search engine/cache、domain、company name、emails、repo metadata
- 参考：`references/js-analysis-source-leak.md`

## Constraints

1. 不下载或扩散敏感仓库，只记录最小证据。
2. 凭据必须验证有效性后才升级。
3. 发现邮箱/工号/手机号要回注 API/JWT/登录链路。
4. 不能验证的泄露作为 PENDING/INFO。
5. 请求凭据时必须附登录入口。

## Chain Questions

- 泄露信息能否登录、签名、解密、访问云资源或定位内部 API？
- 是否能和当前端点参数匹配？
- commit/issue 是否暴露测试账号、环境域名、接口文档？
- 新标识符应该回到哪个攻击面？
