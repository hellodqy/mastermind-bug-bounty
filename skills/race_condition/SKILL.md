---
name: race-condition
description: >
  Identify business actions where concurrent execution can multiply value
  or bypass limits.
metadata:
  tags: "race,logic,concurrency"
---

# Race Condition

## Goal

判断某个业务动作是否因并发导致重复领取、重复消费、余额/库存/权限状态错乱。

## Tools / Inputs

- 测试账号、优惠券/积分/订单/提现/库存/签到接口
- 资源索引：`references/INDEX.md`；候选资源：`bug_classes.md`

## Constraints

1. 只用测试账号和可回滚/无害业务对象。
2. 不对真实资金、真实库存、真实用户造成影响。
3. 先证明单次正常行为，再比较并发差异。
4. 成功必须量化多拿了什么或绕过了什么限制。
5. 新状态或凭据变化继续回注攻击面。

## Chain Questions

- 这个动作是否有“只能一次”的业务语义？
- 并发前后余额、库存、权益、状态是否不一致？
- 竞态结果能不能解锁更高权限或二次利用？
- 是否已经足够证明经济/权限影响？
