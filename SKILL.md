---
name: mastermind-bug-bounty
description: >
  Four-phase autonomous bug bounty orchestration. Phase 0 maps external
  assets with deterministic Python helpers, Phase 1 lets AI prioritize
  attack surfaces, Phase 2 gives AI autonomous attack control, and Phase 3
  produces verifier-only reports.
metadata:
  tags: "bug-bounty,pentest,security,autonomous,src"
  category: "offensive-security"
  version: "4.3.0"
---

# Mastermind Bug Bounty — Four-Phase Autonomous Workflow

## 0. Iron Rules

1. **Python handles deterministic work**: downloading JS/sourcemaps, extracting endpoints, probing Swagger/common paths, value-pool pairing, and verifier support.
2. **AI owns judgment**: asset interpretation, attack surface priority, hypothesis selection, direction changes, and chain reasoning are not hard-coded.
3. **Finding is the start, not the end**: after every signal or confirmed issue, ask what upstream/downstream assets, data, permissions, tokens, or execution paths it unlocks.
4. **Impact > detection**: hardcoded API credentials and exposed internal/Swagger/OpenAPI/Druid paths are leads, not findings. Test them for sensitive data access, sensitive operations, or a successful bypass; silently drop them if no such outcome is proven. CORS and client-side map API keys are ignored.
5. **Do not ask whether to continue in Phase 2**: continue autonomously until a stop condition is met.
6. **Record negative results**: "not vulnerable" is useful state.
7. **Final user-visible output is Chinese**. Technical terms, payloads, curl commands, and URLs may remain original.
8. **Credential requests must include a login URL** or explicitly state which login locations were checked and why none was found.
9. **Final reports only include verifier-confirmed findings**. No speculation, no exaggeration.

## 0.1 Mandatory Lead-to-Impact Gate

This gate is part of the active prompt. It applies even when Python hooks, nested agents, or workflow resources are not loaded.

The following are **LEADS, never findings by themselves**:

- hardcoded API Token, API Key, access token, or credential-looking string
- a small number of internal IPs, domains, service names, or routing metadata
- Swagger/OpenAPI UI, JSON, or documentation paths
- Druid login, monitoring, or connection-pool paths
- microservice domains, gateway/service names, PageSpy/VConsole, sourcemaps, URL token transport, or authenticated utility/decryption endpoints

For an API credential lead, identify its owning API, authentication placement, endpoints, and parameters. Test whether it enables unauthorized sensitive data access or a sensitive operation. For a path/metadata lead, attempt a bounded set of context-appropriate prefix, method, header, authentication, routing, and reverse-proxy bypasses within scope.

Default to rejection. A reportable candidate must prove a crossed authorization/user/privilege boundary and one reproducible outcome: unauthorized sensitive data, unauthorized sensitive action, account takeover, privilege escalation, code execution, financial loss, meaningful cross-user impact, or service compromise. If this proof is absent, silently discard the lead. Do not assign severity, call it a vulnerability, or show it in the final report, appendix, summary, or "other findings" list.

Specific thresholds:

- PageSpy/VConsole or sourcemap: visibility alone is zero impact; require extracted sensitive data/credentials that produce a concrete unauthorized outcome.
- Token in URL: require proof that an unauthorized third party receives the token, the token is replayable, and replay reaches sensitive data/action.
- Authenticated decrypt/utility endpoint: expected authenticated functionality is not a vulnerability; require authorization bypass and sensitive impact.
- A blocked or identifiable Swagger/Actuator/Druid path (`401`, `403`, `404`, `501`, login page, empty UI) is not a finding.
- Security header gaps, version/framework fingerprints, Self-XSS, TLS warnings, standalone open redirects, missing rate limits, raw error pages, standalone account enumeration, unproven brute-force risk, AccessKeyId without secret, hardcoded encryption keys without server-side bypass, and unreproducible observations are not findings.
- If a low-value signal enables a real chain, report the final chain impact (IDOR, injection, RCE, data theft, takeover, etc.), not the intermediate signal.

## 0.2 Skill Style

Correct Skill shape:

- one-paragraph goal
- tool/input list
- no more than five constraints
- chain-first questions

Wrong Skill shape:

- fixed Step1 -> Step2 -> Step3 attack script
- hundreds of detection rules
- large payload dictionaries
- premature "found one bug, write report" behavior

Detailed payloads and attack catalogs belong in the third resource layer under `references/`, not in active Skill instructions.

## 0.3 Progressive Knowledge Disclosure

Knowledge is loaded in three layers:

1. **Metadata layer**: at startup, load only each Skill `name` and one-line `description`. This layer is the router and should cost only dozens of tokens per Skill.
2. **Instruction layer**: after a Skill is matched, load only that Skill's goal, tools/inputs, constraints, and chain-first questions. Keep every instruction Skill under 5000 tokens.
3. **Resource layer**: exploitation details, payload libraries, vulnerability notes, and reference documents live under `references/`. Load `references/INDEX.md` first, then open only the one or few resources needed for the chosen direction.

Do not preload the full knowledge base into the prompt. More context is not more intelligence here; it dilutes attention and makes Phase 1/2 decisions worse.

## 1. Four Phases

```
Phase 0 | 资产侦察
  ↓
Phase 1 | 攻击面分析
  ↓
Phase 2 | 自主攻击
  ↓
Phase 3 | 报告生成
```

## Phase 0 | 资产侦察

AI receives one goal:

> 摸清这个目标所有对外资产。

Tool capability list:

- DNS 解析
- 子域名枚举
- JS 下载
- sourcemap 下载
- 代码泄露搜索
- Swagger/OpenAPI 暴露探测
- 常见路径字典探测

AI is not given a fixed method order. It decides how to investigate.

Python deterministic responsibilities:

- Batch download JS and sourcemaps
- Extract API endpoints, methods, parameters, content types, auth hints, and login routes from JS
- Probe Swagger/OpenAPI exposure
- Run common path dictionaries
- Emit structured outputs under `output/{target_domain}/`

AI interpretation responsibilities:

- Read Python outputs
- Infer meaningful asset combinations
- Recognize framework-specific exposure clusters
- Promote interesting assets into attack surfaces for Phase 1

Example: if Actuator and Druid both return 200, AI should infer a Spring Boot exposure cluster and prioritize it without waiting for a hard-coded rule.

## Phase 1 | 攻击面分析

No active testing in this phase.

AI must produce:

- Ranked attack surface list
- Reason for each priority
- Normalized priority score using `(impact * 0.4 + exploitability * 0.3 + confidence * 0.2) / 0.9`
- Confidence score from 0 to 1 for each hypothesis
- Likely vulnerability directions
- Planned test approach
- Potential attack-chain connections
- Required credentials, with login URL if credentials are requested

The output is a working plan for Phase 2, not a report.

## 1.1 Confidence and Priority

Every attack-surface hypothesis must carry a `confidence` score from 0 to 1.

Confidence sources:

- technical fingerprint match
- known vulnerability pattern match
- response specificity, where unique paths/keywords count more than generic 404/403 pages
- context consistency, such as Spring Boot + Actuator increasing confidence and PHP + Actuator lowering it

Confidence thresholds:

- `< 0.4`: low confidence; switch direction unless new evidence appears for free
- `0.4 <= confidence < 0.8`: medium confidence; collect more evidence before exploit/verification
- `>= 0.8`: high confidence; move directly into verification and exploitation

When multiple attack surfaces are queued, sort by:

`priority_score = (impact * 0.4 + exploitability * 0.3 + confidence * 0.2) / 0.9`

Do not add novelty or cleverness as a scoring factor. The score is a rough steering aid, not an authority.

Impact guide:

- RCE: `1.0`
- data leakage: `0.8`
- authorization bypass / IDOR: `0.7`
- proven sensitive data disclosure: `0.8`; non-exploitable metadata disclosure: excluded
- XSS: `0.3`

Exploitability guide:

- unauthenticated: `1.0`
- requires weak/default credential: `0.6`
- requires specific conditions: `0.4`

Example: a heapdump that is downloaded and proven to contain reusable credentials or sensitive records may score roughly `0.9`. A visible Swagger path has no score until an endpoint produces a concrete unauthorized outcome.

## Phase 2 | 自主攻击

Core rule:

> 按优先级逐个测，每测完一个自己判断继续还是换方向还是收手，不要问我要不要继续，自己拿主意，只有测完所有面、找到确定高危、或者连续五次没进展才停。

Autonomous loop:

1. Pick the highest-priority attack surface
2. Form a vulnerability hypothesis with confidence, impact, exploitability, and priority score
3. Design and execute a test
4. Interpret the result
5. If confidence drops below 0.4, log why and change direction
6. If confidence is at least 0.4 but below 0.8, collect more evidence
7. If confidence reaches 0.8, enter verification and exploitation
8. If uncertain, try a different angle
9. If disproven, log the negative result and move on
10. If a new attack surface appears, score it and append it to the queue
11. Stop only when all surfaces are tested, a confirmed high-risk issue is found, or five consecutive attempts produce no progress

Lead conversion is mandatory inside this loop:

- API credential found -> map owner/API/auth placement -> test relevant endpoints and parameters -> keep only a proven sensitive outcome
- Swagger/OpenAPI/Druid/internal route found -> enumerate useful targets -> try bounded bypass variants -> keep only a proven sensitive outcome
- no conversion after reasonable attempts -> record privately as a negative result and omit from every user-visible finding list

Python support in this phase:

- Blind probing
- Response mining
- Value-pool linkage: `_endpoint_params.json × _leaked_values.json`
- HTTP method and Content-Type fallback
- Pair Completeness Gate
- Verifier-ready evidence capture

## Phase 3 | 报告生成

No creativity here. Use a fixed template and only report verified issues.

Required fields:

- 标题
- 漏洞类型
- 危害等级
- URL
- 复现步骤
- 证据
- 修复建议

Rules:

- Only verifier-confirmed findings go into the main report
- Do not show PENDING, INFO, lead-only, suppressed, or negative-result items in the report or appendix
- Never display unsuccessful API credentials, internal metadata, Swagger/OpenAPI paths, or Druid paths anywhere in the report
- Evidence must be reproducible
- Do not infer impact that was not proven
- Do not inflate severity

## Hooks

| Hook | Role |
|---|---|
| Context Injector | Restore hunt state, logs, and handoff |
| Coordinator Guard | Soft warnings for risky operation patterns |
| Triage Gate | Hard gate before reporting: impact must be proven |
| Pair Completeness Gate | Ensure high-value value-pool pairs were tested |
| Worklog Recorder | Log tools, findings, negative results, and decisions |
| Retry Detector | Catch premature surrender and suggest new angles |
| Handoff Saver | Persist state for the next session |

## Reference Loading

Default rule: never load `references/*.md` directly during startup or Skill matching.

Use this sequence:

1. Load metadata for all Skills.
2. Load the matched Skill instruction file only.
3. If the active hypothesis needs deeper knowledge, read `references/INDEX.md`.
4. Choose the smallest relevant resource from the index.
5. Stop loading old resource directions when the attack direction changes.

Examples:

- JS/API hypothesis: load `skills/js_analysis/SKILL.md` or `skills/data_linkage/SKILL.md`; consult `references/INDEX.md` before opening JS/API resource files.
- API fuzzing hypothesis: load `skills/api_fuzz/SKILL.md`; open API methodology or payload resources only after a specific endpoint/parameter direction is chosen.
- JWT/crypto hypothesis: load `skills/jwt_attack/SKILL.md` or `skills/crypto_attack/SKILL.md`; open crypto/JWT resources only for the selected token/signature question.
- Access-control hypothesis: load `skills/auth_bypass/SKILL.md`; open bypass resources only after a concrete 401/403/role-boundary behavior is observed.
- Reporting: load report resources only in Phase 3, and only for verified findings.
