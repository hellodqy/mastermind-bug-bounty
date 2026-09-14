---
name: path-traversal
description: >
  Test file and archive path resolution when user-controlled names or paths
  may escape an intended storage root or select unintended local resources.
metadata:
  tags: "path-traversal,lfi,file-read,archive,zip-slip"
---

# Path Traversal

## Goal

比较代理、框架、文件系统和归档工具的规范化结果，证明用户输入是否能越过预期目录或对象边界。

## Tools / Inputs

- 下载/预览/模板/日志/归档参数、基准文件、平台与框架指纹
- 资源索引：`references/INDEX.md`；候选资源：`path-traversal-lfi-testing.md`

## Constraints

1. 优先读取无敏感性的已知文件或自建标记文件。
2. 分离 URL 解码、路由规范化和文件系统规范化。
3. 不把错误堆栈或路径回显单独当任意文件读取。
4. 写入/覆盖仅在隔离测试目录中验证。
5. 证明结果必须包含越过的根目录或授权边界。

## Chain Questions

- 路径在哪些层被解码、拼接、清理和重新解析？
- 绝对路径、分隔符、编码和归档条目是否产生不同规范化？
- 文件读取能否获得配置、源码或凭据并导向实际影响？
- 是否存在下载、上传、模板或日志端点共享同一解析器？
