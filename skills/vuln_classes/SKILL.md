---
name: vuln-classes
description: >
  A compact routing skill for choosing vulnerability hypotheses; detailed
  payloads live in references, not here.
metadata:
  tags: "vulnerability-classes,routing"
---

# Vulnerability Classes

## Goal

根据参数、接口、响应和权限上下文选择最值得测试的漏洞方向，并持续追问能否串成更高影响。

## Tools / Inputs

- Endpoint signatures、parameters、responses、tokens、business actions
- 资源索引：`references/INDEX.md`；候选资源：`bug_classes.md`、`decision-trees.md`

## Constraints

1. 不按清单机械扫描；只测与上下文匹配的方向。
2. 优先能证明影响的漏洞类。
3. 同一个信号要考虑上下游链路，而不是单点结论。
4. Payload 细节按需从 references 加载。
5. 不能证明影响则不进入报告正文。

## Chain Questions

- 这个输入是数据选择器、文件路径、URL、模板、命令、金额、角色还是状态？
- 它连接到的数据/动作有多敏感？
- 能不能从读到写、从单用户到多用户、从普通权限到管理权限？
- 当前方向是否仍值得继续？
