---
name: api-fuzz
description: >
  Explore API behavior using real parameters and values before generic
  fuzzing.
metadata:
  tags: "api,fuzz,semantic"
---

# API Fuzz

## Goal

理解接口行为、参数语义和响应差异，找出能继续串联的异常。

## Tools / Inputs

- Endpoint signatures、auth hints、value pool、response diffs
- 参考：`references/api-testing-methodology.md`、`references/api-fuzz-payloads.md`

## Constraints

1. 真实参数和真实值优先，payload 字典最后用。
2. 区分正常业务返回和越权返回。
3. 每次异常都要问它能否导向更高影响。
4. 控制速率，避免因探测破坏后续机会。
5. 负结果必须记录。

## Chain Questions

- 参数能否影响数据范围、角色、租户或导出？
- 响应差异是否泄露权限边界？
- 新字段能否进入 value pool？
- 当前异常更像漏洞、配置问题，还是正常业务？
