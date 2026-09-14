---
name: injection-test
description: >
  Test parser and interpreter boundaries when user-controlled values reach
  database queries, templates, commands, expressions, headers, or downstream protocols.
metadata:
  tags: "injection,sqli,nosql,command,ssti,expression"
---

# Injection Test

## Goal

依据参数语义、技术栈和响应差分选择解释器假设，并把最小执行证据连接到数据、权限或代码执行影响。

## Tools / Inputs

- 参数、Content-Type、错误/布尔/时间差分、技术栈、模板与命令上下文
- 资源索引：`references/INDEX.md`；候选资源：`injection-testing.md`、`api-fuzz-payloads.md`

## Constraints

1. 先确认输入进入哪个解释器，不对所有参数喷洒同一 payload。
2. 优先无副作用的错误、布尔或可控标记证明。
3. 时间差必须有重复基线和对照组。
4. 不读取无关数据、不执行破坏性命令。
5. 只有稳定、可复现且具实际影响的结果才进入 verifier。

## Chain Questions

- 输入经过哪些解码、拼接、类型转换和二次解析？
- 同一字段换位置或 Content-Type 是否进入不同处理器？
- 能否从语法控制升级到认证绕过、数据访问、文件读取或执行？
- 哪个最小对照最能排除缓存、WAF 和网络抖动？
