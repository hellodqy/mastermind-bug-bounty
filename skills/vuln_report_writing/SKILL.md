---
name: vuln-report-writing
description: >
  Write submission-ready vulnerability reports from verifier-confirmed findings.
  Use whenever Mastermind enters Phase 3 or is otherwise asked to draft, rewrite,
  polish, or format a vulnerability report; do not use during recon or testing.
metadata:
  tags: "report,src,reproduction,evidence,remediation"
  category: "offensive-security"
---

# Vulnerability Report Writing

## Goal

把 Verifier 确认的漏洞整理成审核人员仅凭报告即可独立复现、证据链完整且不夸大影响的提交稿。

## Required Inputs

- 已确认漏洞及其授权边界、根因和实际影响
- 具体资产、端点、完整 raw HTTP 请求和关键响应证据
- 从资产/接口来源到影响验证的完整轨迹
- 截图或截图占位说明、合规边界及修复方向

## Workflow

1. 先从 findings、evidence、worklog 和现有产物补齐输入；未知内容保留明确的 `[待补充]`，不得编造。
2. 必读 `references/vuln-report-writing.md`，按其中的黄金攻击链、raw 数据包、图位和文风规范成稿。
3. 使用 `skills/vuln_report_writing/templates/report_template.md` 作为默认结构；目标平台有官方章节名时映射到官方模板，但仍保留本 Skill 的证据与复现要求。
4. 最终执行证据、影响、脱敏、可复现性和合规边界检查。

## Constraints

1. 只为 Verifier 确认且已证明实际安全影响的漏洞生成报告；PENDING、INFO、失败线索和负面结果不得进入正文或附录。
2. 最终 PoC 优先给完整 Burp/raw HTTP 请求，不用 curl 替代；关键请求头和 body 不得省略，响应以关键回显摘录或截图证据呈现。
3. 复现过程必须从资产或接口来源开始，按“动作 → 结果 → 证据”写到影响验证，第三方应能顺序复现。
4. 每项影响必须有证据支持；不得推测数据规模、权限、可利用性或危害等级。
5. 敏感数据必须脱敏，并明确只读/最小化验证、未执行动作及还原情况。

## Output Contract

默认输出：标题、漏洞摘要、受影响资产、复现手册、附件 POC、风险影响评估、修复建议。正文使用中文；HTTP 数据包、字段名、路径和技术术语保持原样。
