---
name: crypto-attack
description: >
  Interpret encryption, signing, encoding, and key material as leverage
  for later attack-chain expansion.
metadata:
  tags: "crypto,signing,encryption,key"
---

# Crypto Attack

## Goal

判断加密/签名机制能否被理解、重放、重签、解密或绕过，并把获得的新能力连接到 API、JWT、IDOR 或报告证据。

## Tools / Inputs

- JS 加密函数、密文、签名字段、key/iv/secret、编码字段
- 参考：`references/crypto-analysis.md`

## Constraints

1. Key 要按用途分类：签名、加密、JWT、云、Cookie/session。
2. 只有可验证利用才升级为漏洞。
3. 解密出的明文必须回写值池。
4. 重新签名后的参数变更必须用无害样本证明。
5. 不把“算法弱”当漏洞，除非证明影响。

## Chain Questions

- 这个 key 能让哪些原本不可改的参数变得可控？
- 解密后是否出现账号、ID、token、内部接口或连接串？
- 重新加密/签名能否绕过后端校验？
- 新能力应该回到哪个攻击面继续扩展？
