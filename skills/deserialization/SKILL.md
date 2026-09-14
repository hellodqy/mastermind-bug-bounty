---
name: deserialization
description: >
  Test serialized objects, polymorphic payloads, message formats, and naming
  lookups when untrusted data may instantiate types or trigger dangerous behavior.
metadata:
  tags: "deserialization,jndi,polymorphic,rce,object-stream"
---

# Deserialization

## Goal

识别数据格式、运行库与可达 gadget，使用低风险证据判断不可信输入是否触发类型实例化、外部查找或代码路径。

## Tools / Inputs

- Content-Type、魔数、错误信息、依赖版本、类型字段、消息队列与 OOB 证据
- 资源索引：`references/INDEX.md`；候选资源：`deserialization-jndi-testing.md`、`cve-chains.md`

## Constraints

1. 先确认格式和解析库，再选择探针。
2. 优先无害类型差分、DNS/OOB 或异常证据，不执行破坏性 gadget。
3. JNDI 回连只证明查找行为；报告需说明可达影响和环境条件。
4. 不向生产目标投递公开武器化 gadget 链。
5. 版本指纹必须与入口、配置和可达性共同验证。

## Chain Questions

- 哪个解析器接受什么格式，类型信息由谁控制？
- 可控数据能否触发类加载、setter、回调、外部查找或模板执行？
- 认证、签名或加密是否在反序列化前真正验证？
- 最小证据能否区分解析、查找与实际执行？
