# Cache Poisoning and Cache Deception Testing

用于 CDN、反向代理和应用缓存存在时的 key confusion。必须证明输入影响响应、未进入 cache key，并被独立请求命中。

## 1. 建立缓存基线

重复请求并记录 `Age`、cache status、ETag、Vary、Cache-Control、响应体标记和 TTL。使用唯一、不可预测的测试 URL，避免污染正常用户路径。

## 2. Cache key 假设

依次比较：Host/X-Forwarded-*、路径规范化、query 参数、重复参数、Content-Type、方法、cookie 和设备/语言头。每次只改变一个输入，确认它是否同时影响后端响应与缓存对象选择。

## 3. 高价值模式

- **Unkeyed input**：输入改变资源、跳转或内容，但缓存忽略该输入；
- **Parameter cloaking**：缓存与后端对分隔符/重复参数的理解不同；
- **Fat GET / method confusion**：缓存忽略 body 或方法差异，后端却处理；
- **Cache deception**：缓存把个性化动态响应误认为静态资源；
- **Path normalization**：CDN 与源站对后缀、分号、编码或路由边界解析不同。

## 4. 安全证明

只使用自控无害标记，随后用不含投毒输入的独立请求确认命中。优先测试专用路径、自有内容或极短 TTL。不得注入脚本、跳转真实用户或缓存敏感生产页面。

## 5. 报告门槛

Header 反射、一次响应变化、存在缓存头都不是漏洞。需要给出 cache key 差异、投毒请求、受害请求、缓存命中证据和可说明的跨用户影响。
