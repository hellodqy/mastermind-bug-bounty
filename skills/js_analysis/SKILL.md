---
name: js-analysis
description: >
  Extract client-side attack surface from JS and sourcemaps without
  dictating the order of investigation.
metadata:
  tags: "js,spa,endpoint-extraction,sourcemap"
---

# JS Analysis

## Goal

从前端代码里恢复真实业务接口、参数、认证入口、路由、状态管理和隐藏功能，为后续攻击面分析提供结构化材料。

## Tools / Inputs

- JS、sourcemap、HTML、Network 请求、SPA 路由、localStorage/sessionStorage
- 输出：`_endpoint_params.json`、`_login_links.json`、`_secrets_found.json`
- 参考：`references/js-analysis-vulnforge.md`、`references/vue-spa-attacks.md`

## Constraints

1. 必须落盘并结构化输出，不能只口头总结。
2. 提取粒度到 method、Content-Type、参数、auth、source file。
3. 登录入口必须单独记录。
4. 不把前端鉴权当后端鉴权。
5. 发现新路由/chunk 后追加为新攻击面。

## Chain Questions

- 这个接口需要什么参数，参数值能从哪里来？
- 这个路由或 meta.auth 是否只在前端控制？
- Store 里有没有 token、角色、菜单、权限、用户标识？
- sourcemap 是否暴露源码、注释、内部 API 或 key？
- 新发现能否喂给 data linkage、JWT、bypass 或 exploit？
