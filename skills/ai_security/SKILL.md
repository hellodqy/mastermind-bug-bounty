---
name: ai-security
description: >
  Treat AI systems as chains of prompt, retrieval, memory, tools, and
  permissions.
metadata:
  tags: "ai,llm,rag,agentic"
---

# AI Security

## Goal

判断用户或外部内容能否影响 AI 的数据访问、工具调用、记忆、检索结果或后端动作。

## Tools / Inputs

- Chat/RAG/Agent/MCP/tool-call/code-sandbox surfaces
- 参考：`references/ai-security-testing.md`、`references/ai-security-vulnforge.md`

## Constraints

1. Prompt injection 本身不是漏洞，必须证明越权影响。
2. 工具调用 abuse 用无害动作证明。
3. 区分模型输出污染、数据泄露和实际后端动作。
4. 间接注入必须证明被检索或执行。
5. 新 token/key/file/path 回注传统 Web 攻击面。

## Chain Questions

- 输入能否控制工具参数或检索上下文？
- 是否能读取系统提示、其他用户数据、内部文档或凭据？
- AI 动作能否触发 Web/API 层漏洞？
- 当前影响是否可验证？
