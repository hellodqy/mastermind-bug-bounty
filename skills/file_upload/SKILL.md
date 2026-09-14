---
name: file-upload
description: >
  Analyze upload, conversion, preview, archive, and storage pipelines when
  file content or metadata may cross execution, parsing, or authorization boundaries.
metadata:
  tags: "file-upload,parser,storage,archive,execution"
---

# File Upload

## Goal

跟踪文件从接收、校验、存储到解析和分发的完整生命周期，验证内容、元数据或访问控制是否造成实际影响。

## Tools / Inputs

- 上传入口、允许类型、响应 URL、对象存储、预览/转换任务、下载权限
- 资源索引：`references/INDEX.md`；候选资源：`file-upload-testing.md`、`path-traversal-lfi-testing.md`

## Constraints

1. 只上传无害标记文件，不部署持久化后门。
2. 分别判断扩展名、MIME、magic bytes 和实际解析器。
3. 不把“上传成功”单独当漏洞，必须证明执行、解析、覆盖或越权访问。
4. 压缩包测试限制大小、层级和文件数量。
5. 使用自建对象验证覆盖、下载和删除边界。

## Chain Questions

- 文件最终存在哪里，由谁解析，使用哪个域名和 Content-Type 返回？
- 校验与实际解析是否基于不同信息？
- 文件名、路径、压缩条目或元数据能否越过目录/租户边界？
- 上传结果能否连接到 XSS、XXE、路径穿越、凭据泄露或代码执行？
