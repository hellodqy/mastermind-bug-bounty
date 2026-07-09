# Reference Resource Index

第三层资源索引。默认只读本文件；只有当 Phase 1/2 明确选择某个攻击方向时，才打开对应资源全文。

| Resource | One-line Use |
|---|---|
| `403-bypass-complete.md` | 401/403/405 访问控制绕过细节和变体。 |
| `ai-security-testing.md` | AI/RAG/Agent 安全测试方法。 |
| `ai-security-vulnforge.md` | AI 攻击面、工具调用滥用、RAG 污染和跨层攻击链。 |
| `api-fuzz-payloads.md` | API 参数语义对应的 payload 参考库。 |
| `api-testing-methodology.md` | API 测试方法论和接口行为判断。 |
| `bug_classes.md` | 通用漏洞类别百科和具体利用参考。 |
| `bypass_techniques.md` | WAF/CDN/编码/协议绕过参考库。 |
| `cloud-attack-surface.md` | OSS/S3/COS、云密钥和云资产攻击面。 |
| `compliance-rules.md` | SRC 合规边界、禁止行为和报告声明。 |
| `crypto-analysis.md` | 加密字段、签名机制、密钥利用判断。 |
| `cve-chains.md` | 常见组件 CVE 链路和安全验证方向。 |
| `decision-trees.md` | 漏洞方向选择和影响升级决策树。 |
| `discovery-amplification.md` | 从端点、参数和值继续扩展攻击面的规则。 |
| `fingerprint-mapping.md` | 技术栈指纹到可测试攻击面的映射。 |
| `high-risk-probing.md` | 高风险探测的条件、边界和后处理。 |
| `hunt_methodology.md` | 端到端漏洞赏金方法论总览。 |
| `impact-escalation.md` | 单点发现升级为链式影响的方法。 |
| `js-analysis-source-leak.md` | JS 与源码泄露搜索、验证和回注。 |
| `js-analysis-vulnforge.md` | JS 深读、sourcemap、运行时 hook 和接口提取细节。 |
| `jwt-analysis.md` | JWT 解码、伪造、爆破和权限提升参考。 |
| `miniprogram-analysis.md` | 小程序解包、API 提取和 Web 侧反哺。 |
| `rating-standard.md` | 漏洞等级判定参考。 |
| `report_templates.md` | HackerOne/SRC/CVE 报告模板。 |
| `response-chaining.md` | 响应字段到后续请求参数的链式利用。 |
| `security-testing-methodology.md` | 通用安全测试流程参考。 |
| `vue-spa-attacks.md` | Vue SPA 路由、store、auth guard 和隐藏 chunk 攻击面。 |

## Loading Rule

1. Phase 0/1 默认只读本索引。
2. Phase 2 只在 AI 已选择具体方向后加载一个或少数相关资源。
3. 不要把多个大型资源同时塞入上下文；先读最相关章节。
4. 如果方向改变，停止继续加载旧方向资源。
5. 报告阶段只加载报告模板、评级标准和合规规则。
