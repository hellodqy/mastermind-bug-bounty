---
name: data-linkage
description: >
  Connect response values to later request parameters and keep expanding
  the attack graph after each finding.
metadata:
  tags: "data-linkage,response-chaining,value-pool"
---

# Data Linkage

## Goal

把“一个响应里出现的值”变成“另一个接口的输入”，持续扩大攻击面。

## Tools / Inputs

- `_endpoint_params.json`
- `_leaked_values.json`
- Response mining、PairingEngine、method fallback
- 资源索引：`references/INDEX.md`；候选资源：`response-chaining.md`、`discovery-amplification.md`

## Constraints

1. 每个有意义响应都要提取字段和值。
2. 高价值值优先：token、ID、key、role、org、tenant、email、phone。
3. 每次值池增长后重新检查可注入接口。
4. 已消费/未消费状态必须记录。
5. 不把单次命中当终点；命中后继续看它打开了什么新门。

## Chain Questions

- 这个值能喂给哪些参数名相同或语义相近的接口？
- 它能否扩大查询范围、越权范围或角色权限？
- 新响应是否产生了新的 token、ID、key 或路径？
- 三轮无新增价值后是否该换方向？
