---
name: type-confusion
description: >
  Analyze weak comparison, coercion, numeric precision, Unicode narrowing,
  and cross-language serialization differences when type conversion may alter a security decision.
metadata:
  tags: "type-confusion,type-juggling,coercion,unicode,precision"
---

# Type Confusion

## Goal

恢复各解析层的真实类型与转换顺序，判断弱比较、精度丢失、字符窄化或跨语言序列化能否改变认证、签名、路由或对象选择。

## Tools / Inputs

- 源码/错误指纹、JSON/form 参数、目标语言版本、签名/哈希比较、网关与后端类型差分
- 资源索引：`references/INDEX.md`；候选资源：`type-confusion-testing.md`、`crypto-analysis.md`

## Constraints

1. 必须按目标语言和版本本地复现转换语义，不能套用跨版本结论。
2. 每次只改变值、容器类型、编码或数值表示中的一个维度。
3. 哈希外形、异常或状态码差异只是线索，必须证明安全分支改变。
4. 高位字符和 Unicode 变体只用于自建对象与无害标记。
5. 将解析器、比较运算和最终授权结果作为完整证据链。

## Chain Questions

- 每一层看到的是字符串、数字、布尔、null、数组还是对象？
- 解析、规范化、哈希、比较和授权的先后顺序是什么？
- 精度、符号、Unicode 或窄化转换是否让不同输入变成同一安全标识？
- 结果能否实际绕过认证、签名、路径、文件名或对象边界？
