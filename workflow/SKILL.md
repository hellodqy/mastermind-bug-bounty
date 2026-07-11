---
name: mastermind-workflow
description: >
  Four-phase autonomous bug bounty workflow. Python handles deterministic
  collection and verifier support; AI owns prioritization, attack reasoning,
  and autonomous direction changes.
metadata:
  tags: "bug-bounty,workflow,autonomous-security,four-phase"
  version: "4.0.0"
---

# Mastermind Workflow — Four-Phase Orchestrator

## Knowledge Loading

Use progressive disclosure:

1. **Metadata layer**: load only Skill names and one-line descriptions at startup.
2. **Instruction layer**: after matching a Skill, load that Skill's goal, tools/inputs, constraints, and chain-first questions; keep this under 5000 tokens.
3. **Resource layer**: load exploit details, payload libraries, and reference docs only through `references/INDEX.md`, and only when Phase 1/2 has selected a concrete direction.

Do not preload all reference modules. The workflow should preserve AI attention for prioritization, chaining, and verifier-backed decisions.

## Pipeline

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

AI directive:

> 摸清这个目标所有对外资产。

给 AI 的工具清单只描述能力，不规定顺序：

- DNS 解析
- 子域名枚举
- JS 下载
- sourcemap 下载
- 代码泄露搜索
- Swagger/API 文档暴露探测
- 常见路径字典探测

Python 负责确定性执行：

- 批量下载 JS 和 sourcemap
- 从 JS 中提取 API 端点、HTTP 方法、参数、认证方式
- 探测 Swagger/OpenAPI 暴露
- 跑常见路径字典
- 输出 `_endpoint_params.json`、`_source_leaks.txt`、`_headers.txt` 等结构化结果

AI 拿到 Python 输出后自行做开放判断。例如 Actuator 和 Druid 同时 200 时，AI 应主动联想到 Spring Boot 暴露面组合，而不是等待写死规则触发。

## Phase 1 | 攻击面分析

本阶段不动手，只分析。

AI 必须基于 Phase 0 结果输出：

- 攻击面清单
- 优先级排序
- 每个假设的 `confidence`、`impact`、`exploitability`、`priority_score`
- 每个优先级的原因
- 计划测试的漏洞方向
- 可能串联成攻击链的位置
- 需要凭据时，必须给出已发现的登录入口或说明未发现入口

## Decision Scoring

每个漏洞假设都必须带 0 到 1 的置信度：

- `< 0.4`：低信度，直接换方向，除非新证据几乎零成本可获得。
- `0.4 <= confidence < 0.8`：中信度，继续收集证据。
- `>= 0.8`：高信度，进入验证和利用。

置信度来自：

- 技术栈指纹匹配度
- 已知漏洞模式匹配度
- 响应内容特异性
- 上下文一致性

多个攻击面排队时使用：

`priority_score = (impact * 0.4 + exploitability * 0.3 + confidence * 0.2) / 0.9`

影响程度参考：RCE `1.0`，已证明的敏感数据泄露 `0.8`，越权/IDOR `0.7`，XSS `0.3`。硬编码 API 凭据和内网/Swagger/OpenAPI/Druid 路径先作为线索验证；只有成功访问敏感数据、执行敏感操作或完成有效绕过后，才按实际影响评分。失败线索不展示。CORS、地图 API Key 直接忽略。

可利用性参考：未授权 `1.0`，需要弱口令 `0.6`，需要特定条件 `0.4`。

## Phase 2 | 自主攻击

核心规则只有一句：

> 按优先级逐个测，每测完一个自己判断继续还是换方向还是收手，不要问用户要不要继续，只有测完所有面、找到确定高危、或者连续五次没进展才停。

执行循环：

1. 取一个攻击面
2. AI 提出一个可能漏洞方向，并给出 `confidence`、`impact`、`exploitability`、`priority_score`
3. AI 自己设计测试方案并调用工具
4. 观察结果并判断是否为漏洞
5. 置信度低于 0.4 就记录原因并换方向
6. 置信度大于等于 0.4 且低于 0.8 就补证
7. 置信度达到 0.8 就进入验证和利用
8. 不确定就换角度继续试
9. 确定不是就记录负结果并换下一个
10. 发现新攻击面就打分后追加进列表
11. 发现漏洞后提取新数据、权限、token、路由、配置和上下游系统，重新进入攻击面队列
12. 循环直到满足停止条件

Python 在本阶段只提供确定性支撑：

- blind probe
- 响应值池挖掘
- `_endpoint_params.json × _leaked_values.json` 联动注入
- 方法/Content-Type fallback
- Pair Completeness Gate

## Phase 3 | 报告生成

本阶段不需要 AI 发挥。

只报告 Verifier 确认过的漏洞，固定模板如下：

- 标题
- 漏洞类型
- 危害等级
- URL
- 复现步骤
- 证据
- 修复建议

原则：

- 证据必须可验证
- 不推测
- 不夸大
- 检测信号不等于漏洞
- PENDING/INFO 只能进附录，不能进正文

## Hooks

- Context Injector: 恢复目标、阶段、日志和 handoff
- Coordinator Guard: 只做软提醒，不打断 AI 自主决策
- Triage Gate: 报告前硬门，只允许已证明影响的漏洞进入报告
- Pair Completeness Gate: 自主攻击阶段后确认高价值值池已消费
- Worklog Recorder: 记录工具调用、发现、负结果和阶段判断
- Retry Detector: 识别过早放弃并注入绕过/换角度建议
- Handoff Saver: 保存下次继续所需的状态
