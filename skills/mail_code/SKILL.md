---
name: mail-code
description: >
  Create and monitor a disposable test mailbox when an authorized registration,
  recovery, email-verification, or magic-link flow requires an isolated email identity.
metadata:
  tags: "email,verification,otp,magic-link,account-testing"
---

# Mail Code

## Goal

用独立临时邮箱打通授权测试中的注册、激活、找回、登录发码和换绑流程，并把收到的验证码或验证链接交还认证测试链路。

## Tools / Inputs

- 脚本（相对项目根目录）：`skills/mail_code/scripts/mail_code.py`
- Python 3 标准库、可访问 `https://api.mail.tm` 的网络、目标站测试账号

## Constraints

1. 仅用于自有测试账号和已授权目标，不用于批量养号或真实用户账号。
2. 临时邮箱服务可看到邮件内容，不接收生产秘密、个人数据或高价值账号重置邮件。
3. 凭据优先写入权限为 `0600` 的 account file，不在对话、报告或工作日志展示 token/password。
4. 使用 sender、subject 和触发时间筛选邮件，不能把任意数字直接视为目标验证码。
5. 接码只是流程辅助；只有后续认证、授权或业务边界被突破才进入 verifier。

## Workflow

从项目根目录运行：

```bash
# 创建邮箱并将凭据安全写入 runtime 文件
python3 skills/mail_code/scripts/mail_code.py create \
  --account-file runtime/mail-account.json

# 在目标站触发邮件后，按发件人/主题轮询验证码或验证链接
python3 skills/mail_code/scripts/mail_code.py poll \
  --account-file runtime/mail-account.json \
  --sender example.com --subject verify --extract both --timeout 300

# 查看匹配邮件摘要
python3 skills/mail_code/scripts/mail_code.py list \
  --account-file runtime/mail-account.json

# 使用完成后删除临时邮箱账号
python3 skills/mail_code/scripts/mail_code.py delete \
  --account-file runtime/mail-account.json
```

若 account file 不可用，脚本仍支持 `--address` 与 `--password`，但命令行参数可能进入 shell 历史，应避免在持久环境使用。

## Chain Questions

- 邮件挑战绑定的是哪个账号、会话、动作和有效期？
- 验证码或链接能否重放、跨账号、跨用途或跨流程使用？
- 最终服务端登录主体、绑定邮箱和权限是否符合预期？
- 结果应回到 `account_takeover`、`oauth_sso`、`idor_test` 还是 `business_logic`？
