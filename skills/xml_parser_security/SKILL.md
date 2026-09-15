---
name: xml-parser-security
description: >
  Test XML, XInclude, XSLT, SVG, SOAP, SAML, and Office-document processing
  when parser features may cross file, network, transformation, or trust boundaries.
metadata:
  tags: "xml,xxe,xinclude,xslt,soap,parser"
---

# XML Parser Security

## Goal

识别真实解析器、输入载体和外部资源策略，用分层证据判断 XML/XSLT 处理是否能读取文件、发起服务端请求或执行危险扩展。

## Tools / Inputs

- XML/SOAP/SAML 请求、SVG/Office 上传、转换/预览功能、错误差分、受控 OOB 端点
- 资源索引：`references/INDEX.md`；候选资源：`xml-parser-security.md`、`ssrf-testing.md`

## Constraints

1. 先确认解析器和载体，再选择 DOCTYPE、XInclude 或 XSLT 假设。
2. 优先使用自控 OOB、无敏感标识文件和常量转换结果。
3. OOB 命中只证明外部解析或请求，不自动证明文件读取或代码执行。
4. 不读取无关文件，不使用危险 XSLT 扩展执行生产命令。
5. 压缩文档样本限制大小、层级和条目数量。

## Chain Questions

- 输入由哪个组件以何种模式解析，DOCTYPE、实体、XInclude 和扩展函数是否启用？
- 校验、签名和业务消费是否作用于同一棵 XML 树？
- 外部访问能否升级为受控文件读取、SSRF 或转换器权限滥用？
- SVG、Office、SOAP、SAML 与直接 XML 是否共享同一解析链？
