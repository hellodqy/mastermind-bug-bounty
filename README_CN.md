# Mastermind Bug Bounty

四阶段自主漏洞赏金编排系统。

这个项目的定位不是传统扫描器，而是把 AI Agent 组织成一个有记忆、有门禁、有自主判断能力的漏洞赏金工作流。新版流程把原来的多阶段拆分收敛为四个更清晰的阶段：Python 做确定性采集和验证支撑，AI 做开放性判断和自主攻击决策。

## 四阶段流程

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

给 AI 的目标只有一句：

> 摸清这个目标所有对外资产。

给 AI 的只是工具清单，不限制方法和顺序：

- DNS 解析
- 子域名枚举
- JS 下载
- sourcemap 下载
- 代码泄露搜索
- Swagger/OpenAPI 暴露探测
- 常见路径字典探测

Python 负责确定性逻辑：

- 批量下载 JS 和 sourcemap
- 从 JS 中提取 API 端点、方法、参数、认证方式、登录入口
- 扫 Swagger/OpenAPI 暴露
- 跑常见路径字典
- 生成 `_endpoint_params.json` 等结构化结果

AI 拿到 Python 输出后自行判断。例如 Actuator 和 Druid 同时 200，AI 应该自己联想到 Spring Boot 暴露面组合。

## Phase 1 | 攻击面分析

这一阶段不动手测试，只分析。

AI 基于侦察结果输出：

- 攻击面清单
- 优先级排序
- 排序理由
- 准备测试的漏洞方向
- 是否能串成攻击链
- 需要凭据时附登录 URL，没找到入口时说明检查过的位置

## Phase 2 | 自主攻击

核心规则：

> 按优先级逐个测，每测完一个自己判断继续还是换方向还是收手，不要问我要不要继续，自己拿主意，只有测完所有面、找到确定高危、或者连续五次没进展才停。

执行循环：

1. 取一个攻击面
2. AI 想一个可能漏洞方向
3. 自己设计测试方案并调用工具
4. 看结果判断是不是漏洞
5. 不确定就换角度试
6. 确定不是就记录并换下一个
7. 发现新攻击面就追加进列表
8. 满足停止条件才停

Python 在这里提供工具化支撑：

- blind probe
- 响应值池挖掘
- `_endpoint_params.json × _leaked_values.json` 联动注入
- Method / Content-Type fallback
- Pair Completeness Gate

## Phase 3 | 报告生成

这一阶段不需要 AI 发挥。

固定模板：

- 标题
- 漏洞类型
- 危害等级
- URL
- 复现步骤
- 证据
- 修复建议

原则：

- 只报告 Verifier 确认过的漏洞
- 证据必须可验证
- 不推测
- 不夸大
- PENDING/INFO 不进入正文

## 知识库加载

知识库采用渐进式披露：

| 层级 | 什么时候加载 | 内容 |
|---|---|---|
| 元数据层 | Agent 启动时 | Skill 名字 + 一句话描述 |
| 指令层 | Skill 被匹配后 | 目标、工具/输入、约束、顺藤摸瓜问题 |
| 资源层 | AI 需要时 | 漏洞细节、payload 库、参考文档、报告模板 |

所有大型知识模块都放在 `references/`，并通过 `references/INDEX.md` 路由。不要把所有模块一次性塞进 prompt；Phase 1/2 形成具体假设后，只加载最相关的一个或少数资源。

## 快速使用

```bash
python cli.py phases
python cli.py run --target https://example.com --hunt-dir ./hunt-data
python cli.py status --hunt-dir ./hunt-data
python cli.py resume --hunt-dir ./hunt-data
```

## 核心目录

```text
SKILL.md                 四阶段主技能说明
workflow/pipeline.py     四阶段 pipeline 定义
workflow/tasks.py        Python 确定性任务库
shared/linkage.py        值池联动引擎
agents/                  AI 角色说明
skills/                  专项测试技能
references/              知识库与报告/合规参考
scripts/                 独立 Hook 脚本
tests/                   核心逻辑测试
```

## 验证

```bash
python tests/test_linkage.py
```
