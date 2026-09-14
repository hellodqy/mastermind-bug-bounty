# GraphQL Security Testing

把 schema、resolver、node 和 subscription 看作对象关系图，优先检查授权而不是把 introspection 当漏洞。

## 1. 恢复操作面

从 introspection、前端 query、错误建议、持久化查询和移动端流量恢复 Query、Mutation、Subscription、输入类型与对象关系。关闭 introspection 时，不应以大规模拼错字段代替正常证据来源。

## 2. 授权矩阵

- 同一 node/global ID 在 A/B 测试账号下的读取差分；
- edge、nested resolver 与顶层 resolver 是否采用相同授权；
- 字段级敏感信息是否只在某些 query path 泄露；
- mutation 是否验证对象所有权和角色；
- subscription 是否限制 room/user/tenant；
- batch/alias 中每个操作是否独立鉴权。

## 3. 解析与传输差异

比较 GET/POST、JSON/graphql Content-Type、单操作/批量数组、变量/内联参数、fragment、alias 和 persisted query。差异只有在造成授权、限速或敏感动作影响时才报告。

## 4. 成本控制

深度、复杂度和 alias amplification 只做小规模、可控验证，不执行 DoS。观察服务端是否有深度/成本限制即可，不以资源耗尽证明。

## 5. 证据

保存最小 query、变量、身份和返回字段。Introspection、字段建议、错误堆栈都是线索；必须连接到跨用户数据、越权 mutation 或订阅泄露。
