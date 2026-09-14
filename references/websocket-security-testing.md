# WebSocket Security Testing

用于原生 WS/WSS、Socket.IO、STOMP 和 GraphQL subscription。分别验证握手认证、消息级授权、订阅边界和重放。

## 1. 建立协议状态

从 JS 和正常流量记录 URL、子协议、cookie/token/query 认证、连接后的初始化消息、heartbeat、room/channel/topic、user/tenant ID 和消息 schema。

## 2. 授权矩阵

| 层 | 差分 |
|---|---|
| 握手 | 无 cookie、过期 token、另一测试账号、Origin 变化 |
| 初始化 | token 在 connect 消息中缺失/替换/重放 |
| 订阅 | A 订阅 B 的自建 room/topic/object |
| 发布 | 修改 sender/user/tenant/role/object 字段 |
| 重放 | 重放旧消息、改变顺序、跨连接使用 message ID |
| HTTP 联动 | WS 获得的 ID/token 回注 REST/GraphQL |

## 3. CSWSH

Origin 缺失或宽松只是一项前提。必须同时证明浏览器会自动携带有效认证、攻击页面能建立连接，并能读取敏感消息或执行动作。

## 4. 安全边界

使用两个测试账号和自建频道；不做连接耗尽、消息洪泛或向真实频道发布。二进制协议先恢复 schema，再进行最小字段差分。

## 5. 证据

保存握手、初始化消息、正常订阅、跨界订阅/动作和业务结果。连接成功本身不是漏洞；需要证明跨主体数据或动作。
