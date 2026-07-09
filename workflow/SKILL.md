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
- 每个优先级的原因
- 计划测试的漏洞方向
- 可能串联成攻击链的位置
- 需要凭据时，必须给出已发现的登录入口或说明未发现入口

## Phase 2 | 自主攻击

核心规则只有一句：

> 按优先级逐个测，每测完一个自己判断继续还是换方向还是收手，不要问用户要不要继续，只有测完所有面、找到确定高危、或者连续五次没进展才停。

执行循环：

1. 取一个攻击面
2. AI 提出一个可能漏洞方向
3. AI 自己设计测试方案并调用工具
4. 观察结果并判断是否为漏洞
5. 不确定就换角度继续试
6. 确定不是就记录负结果并换下一个
7. 发现新攻击面就追加进列表
8. 发现漏洞后提取新数据、权限、token、路由、配置和上下游系统，重新进入攻击面队列
9. 循环直到满足停止条件

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
