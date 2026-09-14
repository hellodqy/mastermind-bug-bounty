# OAuth, OIDC and SAML Testing

用于授权码、token、回调和联邦身份映射。每个异常都必须落到最终会话主体、租户或权限变化。

## 1. 流程账本

记录 client、issuer/IdP、redirect URI/ACS、state、nonce、PKCE、code、access token、ID token/assertion、subject、audience 和最终本地账号。标明每个值的生成者、验证者和一次性约束。

## 2. OAuth/OIDC 假设

- redirect URI 的解析、注册和最终跳转不一致；
- state 未绑定发起会话或可跨流程复用；
- PKCE 未验证、降级或 verifier 与 code 未绑定；
- code/token 可在不同 client、redirect URI 或 issuer 间替换；
- OIDC nonce、issuer、audience、azp 未验证；
- 外部 subject 到本地账号的映射只依赖可变 email/用户名；
- 登录与账号绑定流程混用同一回调或票据。

## 3. SAML 假设

确认签名覆盖 Response 还是 Assertion、验证器实际消费哪个节点、Destination/Recipient/InResponseTo/Audience 是否绑定、IdP/SP initiated 流是否混淆。解析差异与 XML 问题只有在改变最终身份时才进入认证报告。

## 4. 安全测试

仅使用自有 IdP/测试账号和可恢复绑定。不得把真实用户引向测试回调、保留他人 code 或修改第三方绑定。以最终 `/me`、租户和角色确认结果。

## 5. 拒绝条件

开放跳转但拿不到 code/token、缺少 state 但不能形成登录 CSRF、可读 JWT、公开 metadata/JWKS、错误信息，均不足以报告账号接管。
