# API Gateway Security

用于 Kong、Nginx、Envoy、APISIX、云 API Gateway、Ingress 和自研网关。重点是比较网关与后端对同一请求的路由、规范化、身份和业务语义，而不是按产品名套绕过清单。

## 1. 建立两层模型

先记录一条正常请求和一条被阻断请求，并分别推断：

| 层 | 需要确认 |
|---|---|
| 客户端到网关 | scheme、host、path、method、query/body、Content-Type、认证材料 |
| 网关 | 路由匹配、路径重写、方法策略、认证插件、限速 key、身份头注入 |
| 后端 | 最终 path/method、重复参数选择、对象授权、信任的身份来源 |
| 返回链 | 错误由哪一层生成、缓存/重试/转换是否改变结果 |

通过 Server/Via、错误模板、trace/request ID、响应头和行为差分区分网关拒绝与后端拒绝。

## 2. 高价值差分

### 2.1 路径规范化

只在已知受保护路径的相邻无害资源上比较点段、重复分隔符、编码、矩阵参数、尾部斜杠和平台分隔符。必须证明网关检查的是一种路径，而后端最终进入另一条受保护路由；单独的 200/404 变化不足以成立。

### 2.2 方法与覆盖

比较直接 method 与应用支持的 method-override 机制。网关允许 GET/POST 而后端执行更新/删除语义时，用自建对象或 dry-run 能力证明。不要对真实对象测试危险方法。

### 2.3 参数解析

对重复 query、数组/标量、重复 JSON key、query 与 body 同名字段进行单变量差分，恢复网关与后端的 first/last/all-value 行为。只有参数选择差异跨越对象或权限边界时才升级。

### 2.4 身份传播

识别网关注入或清理的 `X-User-*`、consumer、tenant、role、original URI 等身份/路由头。判断后端是否只信任来自可信网关的重写值，以及外部同名头是否被覆盖。不得把任意反射身份头直接认定为伪造身份。

### 2.5 版本与等价入口

从 JS、OpenAPI、移动端和历史流量恢复同一业务能力的版本、前缀和批量入口。比较认证、字段校验和对象授权，而不是机械枚举 `v1` 到 `vN`。旧接口可访问只有在产生敏感数据或动作时才报告。

## 3. 批量接口

批量/导入/聚合接口可能：逐项授权不完整、只验证第一个对象、共享一个限速单位或返回跨租户部分结果。用两个自建对象和最小数组验证逐项边界；禁止大数组、批量删除和配额消耗。

## 4. 文档与指纹

Swagger/OpenAPI、GraphQL schema、网关管理路径、Lambda/插件错误只是攻击面材料。提取 route、method、auth scheme、参数和服务名后回注队列；遵循 lead-to-impact gate，不把文档可见性本身写入报告。

## 5. 产品差异如何使用

- Nginx/Ingress：关注 location、rewrite、`proxy_pass` 与 slash 语义。
- Kong/APISIX/Envoy：关注插件执行顺序、route/service 映射和 consumer 身份传播。
- 云网关/Lambda authorizer：关注缓存 key、stage/version、authorizer 输出与后端二次授权。

产品指纹只帮助选择假设；结论必须来自当前部署的请求差分。

## 6. 证据与链路

保存原始阻断、单变量变体、最终后端行为和自建对象结果。成功后将后端服务名、内部路径、版本、对象 ID 与 token 回注 IDOR、认证、注入、请求走私或数据联动。
