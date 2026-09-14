# Reference Resource Index

第三层资源索引。默认只读本文件；只有当 Phase 1/2 明确选择某个攻击方向时，才打开对应资源全文。

本目录里的知识模块，包括未来扩展到 96 个模块时，都属于第三层资源。它们不是启动 prompt，也不是 Skill 指令层；它们是 AI 在形成具体假设之后主动查询的参考库。

三层加载关系：

1. 元数据层：Skill 名称 + 一句话描述，Agent 启动时全部加载。
2. 指令层：目标描述 + 工具清单 + 不超过 5 条约束，Skill 被匹配后才加载。
3. 资源层：漏洞细节、payload、案例、方法论、报告模板，只有需要时从本索引跳转。

| Resource | One-line Use |
|---|---|
| `403-bypass-complete.md` | 401/403/405 访问控制绕过细节和变体。 |
| `ai-development-platforms.md` | 云 IDE、AI 编程台、工作区、RPC 与执行层授权边界。 |
| `ai-security-testing.md` | AI/RAG/Agent 安全测试方法。 |
| `ai-security-vulnforge.md` | AI 攻击面、工具调用滥用、RAG 污染和跨层攻击链。 |
| `api-fuzz-payloads.md` | API 参数语义对应的 payload 参考库。 |
| `api-testing-methodology.md` | API 测试方法论和接口行为判断。 |
| `artifact-layout.md` | 目标域目录、产物分类和文件命名规范。 |
| `authentication-flow-testing.md` | 登录、找回、验证码、MFA、刷新和账号绑定生命周期。 |
| `authorization-idor-testing.md` | IDOR/BOLA/BFLA、字段级授权与跨租户对象矩阵。 |
| `bug_classes.md` | 通用漏洞类别百科和具体利用参考。 |
| `bypass_techniques.md` | WAF/CDN/编码/协议绕过参考库。 |
| `business-logic-testing.md` | 状态机、票据绑定、金额权益和跨渠道业务不变量。 |
| `cache-poisoning-testing.md` | Cache key、unkeyed input、缓存投毒与缓存欺骗。 |
| `cloud-attack-surface.md` | OSS/S3/COS、云密钥和云资产攻击面。 |
| `compliance-rules.md` | SRC 合规边界、禁止行为和报告声明。 |
| `crypto-analysis.md` | 加密字段、签名机制、密钥利用判断。 |
| `cve-chains.md` | 常见组件 CVE 链路和安全验证方向。 |
| `deserialization-jndi-testing.md` | 对象流、多态解析、JNDI 查找与 gadget 可达性。 |
| `decision-trees.md` | 漏洞方向选择和影响升级决策树。 |
| `discovery-amplification.md` | 从端点、参数和值继续扩展攻击面的规则。 |
| `file-upload-testing.md` | 上传、存储、解析、转换和文件分发生命周期。 |
| `fingerprint-mapping.md` | 技术栈指纹到可测试攻击面的映射。 |
| `graphql-security-testing.md` | GraphQL schema、resolver、对象授权、batch 与订阅。 |
| `high-risk-probing.md` | 高风险探测的条件、边界和后处理。 |
| `hunt_methodology.md` | 端到端漏洞赏金方法论总览。 |
| `http-request-smuggling.md` | CL/TE、HTTP/2 降级、desync 证据与安全边界。 |
| `impact-escalation.md` | 单点发现升级为链式影响的方法。 |
| `injection-testing.md` | SQL/NoSQL/命令/模板/表达式等解释器差分测试。 |
| `js-analysis-source-leak.md` | JS 与源码泄露搜索、验证和回注。 |
| `js-analysis-vulnforge.md` | JS 深读、sourcemap、运行时 hook 和接口提取细节。 |
| `jwt-analysis.md` | JWT 解码、伪造、爆破和权限提升参考。 |
| `miniprogram-analysis.md` | 小程序解包、API 提取和 Web 侧反哺。 |
| `oauth-oidc-saml-testing.md` | OAuth/OIDC/SAML 票据绑定、回调与身份映射。 |
| `path-traversal-lfi-testing.md` | 路径规范化、任意文件读取与归档目录逃逸。 |
| `race-condition-testing.md` | Single-packet、同步方法和业务竞态不变量。 |
| `rating-standard.md` | 漏洞等级判定参考。 |
| `report_templates.md` | HackerOne/SRC/CVE 报告模板。 |
| `response-chaining.md` | 响应字段到后续请求参数的链式利用。 |
| `scm-and-artifact-exposure.md` | Git/SVN/构建产物、备份与部署文件暴露。 |
| `security-testing-methodology.md` | 通用安全测试流程参考。 |
| `ssrf-testing.md` | 服务端 URL 请求、重定向、云元数据与网络边界。 |
| `vue-spa-attacks.md` | Vue SPA 路由、store、auth guard 和隐藏 chunk 攻击面。 |
| `websocket-security-testing.md` | WS 握手、消息级授权、CSWSH、订阅和重放。 |
| `xss-testing.md` | Reflected/Stored/DOM XSS 上下文、sink 与跨用户影响。 |

## Loading Rule

1. Phase 0/1 默认只读本索引。
2. Phase 2 只在 AI 已选择具体方向后加载一个或少数相关资源。
3. 不要把多个大型资源同时塞入上下文；先读最相关章节。
4. 如果方向改变，停止继续加载旧方向资源。
5. 报告阶段只加载报告模板、评级标准和合规规则。
6. Skill 文件只能指向本索引和候选资源名，不能要求预加载资源全文。
