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
  version: "4.7.0"
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

## 0.2 Skill and Reference Routing

Use progressive disclosure:

1. At startup, use Skill names and descriptions only.
2. After selecting a concrete direction, load the matching `skills/*/SKILL.md`.
3. For deeper detail, read `references/INDEX.md` and open only the smallest relevant resource set.

Do not preload the knowledge base, payload catalogs, or unrelated Skills. Keep
deterministic procedures and detailed attack material in child Skills or
references rather than expanding this orchestrator.

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

Available capabilities include DNS and subdomain enumeration, JS/sourcemap
collection, source-leak search, Swagger/OpenAPI probing, and common-path
discovery. AI chooses the order.

Python handles batch collection, endpoint/method/parameter/auth/login extraction,
deterministic probes, and artifact emission under `output/{target_domain}/` in
`recon/`, `assets/`, `analysis/`, `evidence/`, `reports/`, or `runtime/`.

Read [references/artifact-layout.md](references/artifact-layout.md) before
writing any process or result file. The normalized hostname is the only target
directory key; URL paths and query strings never create directories.

AI interprets those outputs, correlates assets and framework-specific exposure
clusters, and promotes meaningful candidates into Phase 1 attack surfaces.

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

Base confidence on fingerprint and vulnerability-pattern matches, response
specificity, and contextual consistency. Unique paths or keywords carry more
weight than generic 404/403 responses.

Confidence thresholds:

- `< 0.4`: low confidence; switch direction unless new evidence appears for free
- `0.4 <= confidence < 0.8`: medium confidence; collect more evidence before exploit/verification
- `>= 0.8`: high confidence; move directly into verification and exploitation

When multiple attack surfaces are queued, sort by:

`priority_score = (impact * 0.4 + exploitability * 0.3 + confidence * 0.2) / 0.9`

Do not add novelty or cleverness as a scoring factor. The score is a rough steering aid, not an authority.

Impact anchors: RCE `1.0`; proven sensitive-data leakage `0.8`;
authorization bypass/IDOR `0.7`; XSS `0.3`; non-exploitable metadata is
excluded. Exploitability anchors: unauthenticated `1.0`; weak/default credential
`0.6`; specific conditions `0.4`.

Example: a heapdump that is downloaded and proven to contain reusable credentials or sensitive records may score roughly `0.9`. A visible Swagger path has no score until an endpoint produces a concrete unauthorized outcome.

## Phase 2 | 自主攻击

Core rule:

> 按优先级逐个测，每测完一个自己判断继续还是换方向还是收手，不要问我要不要继续，自己拿主意，只有测完所有面、找到确定高危、或者连续五次没进展才停。

Autonomous loop:

1. Pick the highest-priority surface and form a scored hypothesis.
2. Design and execute a test, then interpret the result.
3. Below `0.4`, log why and change direction; from `0.4` to `<0.8`, gather evidence; at `>=0.8`, verify and exploit.
4. If uncertain, change angle; if disproven, log the negative result and continue.
5. Score and enqueue newly discovered attack surfaces.
6. Stop only when all surfaces are tested, a confirmed high-risk issue is found, or five consecutive attempts produce no progress.

Lead conversion is mandatory inside this loop:

- API credential found -> map owner/API/auth placement -> test relevant endpoints and parameters -> keep only a proven sensitive outcome
- Swagger/OpenAPI/Druid/internal route found -> enumerate useful targets -> try bounded bypass variants -> keep only a proven sensitive outcome
- no conversion after reasonable attempts -> record privately as a negative result and omit from every user-visible finding list

Python supports blind probing, response mining, `_endpoint_params.json ×
_leaked_values.json` linkage, method/Content-Type fallback, the Pair Completeness
Gate, and verifier-ready evidence capture.

## Phase 3 | 报告生成

For every request to draft, rewrite, polish, format, or generate a vulnerability
report, load and follow `skills/vuln_report_writing/SKILL.md`. Do not load it
during recon or attack work.

Only verifier-confirmed findings may enter a report. PENDING, INFO, lead-only,
suppressed, failed, and negative-result items stay private. Evidence must be
reproducible, and impact and severity must not exceed what was proven.

## Hooks

Hooks restore context, record work, detect premature stopping, enforce pair
completeness, persist handoff state, and apply the Triage Gate before reporting.
Their implementation details belong to `workflow/SKILL.md` and the scripts.

## Reference Loading

Never load `references/*.md` at startup. Use `references/INDEX.md` only after a
concrete hypothesis exists, stop loading a direction when it is abandoned, and
select Skills as follows:

| Direction | Skill routing |
|---|---|
| JS/API discovery | `skills/js_analysis/SKILL.md`, `skills/data_linkage/SKILL.md`, or `skills/api_fuzz/SKILL.md` |
| JWT, signature, crypto | `skills/jwt_attack/SKILL.md` or `skills/crypto_attack/SKILL.md` |
| Object or route authorization | `skills/idor_test/SKILL.md` or `skills/auth_bypass/SKILL.md` |
| Login, recovery, binding | `skills/account_takeover/SKILL.md`; use `skills/mail_code/SKILL.md` only for an authorized disposable test identity |
| Gateway or dangling DNS | `skills/api_gateway/SKILL.md` or `skills/subdomain_takeover/SKILL.md` |
| XML or type coercion | `skills/xml_parser_security/SKILL.md` or `skills/type_confusion/SKILL.md` |
| Parser and input flaws | Load only the matching injection, SSRF, upload, traversal, deserialization, XSS, GraphQL, WebSocket, smuggling, or prototype-pollution Skill |
| Verified report | `skills/vuln_report_writing/SKILL.md` |
