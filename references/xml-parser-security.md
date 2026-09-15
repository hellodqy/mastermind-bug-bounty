# XML, XXE and XSLT Parser Security

用于直接 XML、SOAP、SAML、SVG、Office/OpenXML、上传转换、PDF 生成和 XSLT 服务。先确认输入确实到达 XML 解析器，再区分实体、包含、网络访问与转换扩展。

## 1. 解析链清单

记录：载体、解包组件、XML 库、解析模式、schema validation、DOCTYPE/实体策略、XInclude、XSLT processor、URI resolver、网络/文件权限和业务消费节点。压缩文档可能包含多份 XML，不应默认入口文件就是实际被解析的部件。

## 2. 分层验证

| 层 | 最小证据 | 不能直接推断 |
|---|---|---|
| XML 可达 | 格式良好/畸形 XML 产生解析器特有差分 | 外部实体已启用 |
| DTD/实体处理 | 自控实体标记或受控 DNS/HTTP 命中 | 本地文件可读 |
| 文件访问 | 返回无敏感标识文件的稳定内容 | 任意文件/RCE |
| 网络访问 | 唯一 OOB 请求与输入关联 | 可访问云元数据或内网敏感服务 |
| XInclude | include 结果进入可见或可验证业务输出 | DTD 也可用 |
| XSLT | 常量变换或自控资源读取 | 危险扩展函数/RCE |

OOB 请求要排除安全扫描器、客户端预取和异步重试。

## 3. 常见载体

- SOAP/XML API、REST 中的 XML Content-Type；
- SAML Response/metadata 与签名验证前后的解析；
- SVG 图片、图像处理与服务端缩略图；
- DOCX/XLSX/PPTX 等 ZIP 内 XML 部件；
- RSS/Atom、配置导入、发票和行业 XML；
- XSLT 模板上传、报表和 XML→HTML/PDF 转换。

使用最小、结构合法的自建样本，限制压缩包大小、条目和嵌套，避免实体扩展或压缩炸弹。

## 4. XXE、XInclude 与 SSRF

优先用自控外部资源确认解析器能力；如需文件证据，选择应用自建或无秘密标识文件。网络访问的进一步判断转到 `ssrf-testing.md`，不进行内网大规模探测。

DOCTYPE 被禁用后，只有在目标 schema/处理链确实使用 XInclude 或 XSLT 时才切换方向。不要把所有 XML 防护都假设成可绕过。

## 5. XSLT 专项

判断 stylesheet 是攻击者可控、部分可控还是固定模板；确认 processor 及版本、扩展函数、document/include/import、URI resolver 与输出位置。使用常量变换、读取自控资源或无害 OOB 证明，不执行系统命令。

XSLT 产生不同输出只有在用户控制了模板语义时才有意义；正常的模板功能或允许读取公开资源不是漏洞。

## 6. SAML 与签名边界

区分原始字节、解析树和业务代码最终消费的节点。检查签名覆盖 Response 还是 Assertion、是否选择了未签名重复节点、Audience/Destination/Recipient/InResponseTo 是否验证。身份影响交给 `oauth-oidc-saml-testing.md`；单独的解析错误不构成认证绕过。

## 7. 报告门槛

报告需要给出载体、解析器行为、外部资源/文件证据、网络身份与实际影响。错误堆栈、DOCTYPE 被接受、一次 DNS 请求或公开文件内容只能作为线索。
