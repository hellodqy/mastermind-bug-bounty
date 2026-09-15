# Prototype Pollution Gadget Triage

本资源只在已证明污染 source 后加载。原型属性可见不是最终漏洞；需要找到应用实际读取的 gadget，并证明它改变授权、模板、DOM、请求、路径或进程行为。

## 1. 四段证据链

1. **Source**：用户输入进入深合并、路径赋值、query parser、配置更新或反序列化；
2. **Pollution**：无害随机属性出现在预期原型范围，且能清理或随请求结束；
3. **Gadget**：可识别代码读取该继承属性，并且没有 own-property/default 防护；
4. **Impact**：安全决策、渲染、DOM sink、外部请求、文件路径或子进程配置真实改变。

任一段缺失都标记 PENDING。

## 2. Server-side Node.js gadget 路由

| 家族 | 关注的继承属性/行为 | 安全证明 |
|---|---|---|
| `child_process` | shell、env、argv、cwd、stdio 等 options 被继承 | 用无害常量输出或测试环境参数差分 |
| Express/render | view options、engine、locals、layout 被继承 | 渲染自建模板中的可控常量 |
| EJS/Pug/Jade | compile/output/debug/client 等选项进入生成代码 | 比较编译输出，不执行系统命令 |
| Handlebars/Mustache | compiler/helper/lookup 选项改变属性访问 | 自建 helper/模板差分 |
| Nunjucks/Twig.js | loader、globals、autoescape 或 compile 配置 | 自建模板和无害输出 |
| Fastify/HTTP client | serializer、headers、method、URL/options | 请求到自控端点的无害差分 |
| CLI parsers | minimist/yargs/配置 merge 污染下游 options | 本地/测试任务的参数差分 |

框架存在并不代表对应 gadget 可达。必须确认版本、调用方式、属性名和从 source 到 sink 的数据流。

## 3. Client-side gadget 路由

重点检查：

- jQuery 深合并与 DOM/请求选项；
- Lodash `merge/defaultsDeep/set` 后进入模板或配置；
- DOMPurify/sanitizer allowlist、URI 和 hook 配置；
- AngularJS/Vue/React 周边库的 DOM 属性与动态组件配置；
- Webpack/runtime/public path/chunk 加载配置；
- `innerHTML`、事件、script URL、iframe/srcdoc 等最终 sink。

先用无害属性确认 gadget 读取，再在自有测试页面用常量 DOM 标记证明。不窃取 token、不触发真实用户。

## 4. 绕过 source 过滤时的判断

如果只过滤 `__proto__`，检查代码是否仍允许 `constructor.prototype`、数组/点号/bracket 路径或递归 merge。但不要机械投递所有变体；先确定 parser 的路径语法、危险 key 防护和 shallow/deep merge 行为。

JSON parser 本身通常不会污染原型，污染往往发生在解析后的 merge/assign/set。证据应明确是哪一个函数完成了危险写入。

## 5. 生命周期和范围

确认污染位于单个对象、请求上下文、进程全局、客户端页面还是持久化配置。服务端全局污染具有并发和可用性风险，验证应使用唯一无害属性并尽快停止；不得污染 `toString`、请求关键配置或会导致生产崩溃的属性。

## 6. 与其他 Skill 的连接

- 模板或命令 sink → `injection_test`；
- 浏览器 sink → `xss_test`；
- URL/HTTP options → `ssrf_test`；
- path/filename → `path_traversal`；
- role/tenant/default allow → `idor_test` 或 `auth_bypass`。

最终报告按实际 sink 命名影响，而不是只写“存在原型链污染”。
