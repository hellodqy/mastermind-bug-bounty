---
name: websocket-test
description: >
  Explore WebSocket state, authentication, subscriptions, and replay as
  chained attack surfaces.
metadata:
  tags: "websocket,ws,csrf,idor,replay"
---

# WebSocket Test

## Goal

判断 WebSocket 是否在握手、消息、订阅、重放或 Origin 校验中暴露越权能力。

## Tools / Inputs

- WS/WSS URL、Socket.IO/STOMP hints、tokens、room/channel/user IDs
- 参考：`references/decision-trees.md`

## Constraints

1. 不做连接耗尽或破坏性 DoS。
2. 用测试账号验证跨用户订阅或消息动作。
3. 每条消息都关注 userId、roomId、tenantId、role 等可控字段。
4. 成功后证明实际接收或执行了不该发生的事件。
5. 新 ID/channel/token 回写值池。

## Chain Questions

- 认证发生在握手还是消息体？
- 换 token 或 userId 后订阅边界是否变化？
- 消息是否可重放、篡改或跨房间发送？
- WS 泄露的数据能否反哺 HTTP API？
