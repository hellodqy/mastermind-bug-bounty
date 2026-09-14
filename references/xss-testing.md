# XSS Testing

XSS 的核心是 source 到 sink 的上下文与跨用户影响，而不是出现尖括号或弹窗。

## 1. 上下文建模

记录输入经过的存储、编码、模板、JSON 序列化、DOM API 和 sanitizer。区分 HTML 文本、属性、JavaScript、URL、CSS、SVG/Markdown 以及 DOM source/sink。

常见 DOM source：URL、fragment、postMessage、storage、WebSocket、API 响应。高风险 sink：HTML 解析、动态脚本/事件、危险 URL、模板编译和绕过 sanitizer 的框架 API。

## 2. 类型与证据

| 类型 | 必须证明 |
|---|---|
| Reflected | 请求输入进入可执行上下文并在受害者可达页面触发 |
| Stored | 数据持久化，另一个测试账号或更高权限视图会渲染 |
| DOM | 浏览器端 source 到 sink 的真实数据流 |
| Blind | 自控回调与具体输入、页面和测试用户可关联 |

使用无害标记证明执行。不得窃取 cookie、token 或真实用户数据。

## 3. 防护边界

分析框架默认转义、sanitizer、CSP、sandbox 和 Trusted Types。CSP 缺失不是漏洞；CSP 绕过只有在已经存在注入 sink 时才有意义。Self-XSS、开发者工具粘贴和仅攻击者本人可控页面不报告。

## 4. 影响升级

确定受影响角色、触发频率、页面权限以及脚本能调用的同源 API。用测试账号执行无害敏感动作证明链路；不要直接假设管理员接管。

## 5. 误判

HTML 源码中反射但被正确编码、JSON 中字符串出现、浏览器扩展注入、模板字面量显示、服务器返回 CSP 报告，都不构成可执行 XSS。
