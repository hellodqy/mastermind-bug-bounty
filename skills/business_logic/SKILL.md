---
name: business-logic
description: >
  Test multi-step business workflows when server-side state, value, ownership,
  or transition invariants may be bypassed without a conventional injection flaw.
metadata:
  tags: "business-logic,state-machine,payment,workflow,invariant"
---

# Business Logic

## Goal

恢复业务状态机与价值守恒条件，判断步骤跳过、重放、参数信任或跨渠道差异能否突破服务端约束。

## Tools / Inputs

- 正常业务流、状态字段、金额/数量/权益参数、接口顺序、测试订单与账号
- 资源索引：`references/INDEX.md`；候选资源：`business-logic-testing.md`、`race-condition-testing.md`

## Constraints

1. 仅使用测试资产，不制造真实资损、库存或第三方影响。
2. 先记录正常状态转换，再改变一个变量。
3. 客户端显示异常不是结论，必须验证服务端最终状态。
4. 可疑优惠或余额结果不得提现、转移或消费真实资源。
5. 并发假设交给 race-condition，身份假设交给 IDOR/account-takeover。

## Chain Questions

- 哪些状态、价格、数量、角色或顺序应该由服务端保持不变量？
- 是否能跳步、逆序、重放或从另一渠道继续流程？
- 中间票据是否绑定用户、商品、金额、动作和有效期？
- 异常状态能否转化为持久权益、权限或跨用户影响？
