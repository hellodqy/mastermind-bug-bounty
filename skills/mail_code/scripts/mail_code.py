#!/usr/bin/env python3
"""Disposable test-mailbox helper backed by the public mail.tm API.

Pure standard library. Prefer --account-file so credentials do not appear in
shell history. Use only with test identities in an authorized workflow.
"""

from __future__ import annotations

import argparse
import html
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import re
import secrets
import string
import sys
import time
from typing import Any
import urllib.error
import urllib.request

BASE = "https://api.mail.tm"
USER_AGENT = "mastermind-mail-code/1.0"
DEFAULT_CODE_RE = r"\b\d{4,8}\b"
URL_RE = re.compile(r"https?://[^\s<>\"']+", re.IGNORECASE)


class MailCodeError(RuntimeError):
    pass


class _MailHTMLParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.text: list[str] = []
        self.links: list[str] = []

    def handle_data(self, data: str) -> None:
        self.text.append(data)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "a":
            return
        for name, value in attrs:
            if name.lower() == "href" and value:
                self.links.append(html.unescape(value))


def _raw_request(
    method: str,
    path: str,
    token: str | None = None,
    body: dict[str, Any] | None = None,
) -> tuple[int, dict[str, Any]]:
    url = BASE + path
    data = json.dumps(body).encode("utf-8") if body is not None else None
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": USER_AGENT,
    }
    if token:
        headers["Authorization"] = "Bearer " + token
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            raw = response.read().decode("utf-8", "replace")
            payload = json.loads(raw) if raw else {}
            return response.status, payload if isinstance(payload, dict) else {"data": payload}
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", "replace")
        try:
            payload = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            payload = {"raw": raw[:500]}
        return exc.code, payload if isinstance(payload, dict) else {"data": payload}
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        return -1, {"error": str(exc)}


def _request(
    method: str,
    path: str,
    token: str | None = None,
    body: dict[str, Any] | None = None,
    retries: int = 3,
) -> tuple[int, dict[str, Any]]:
    wait = 1.0
    last: tuple[int, dict[str, Any]] = (-1, {"error": "request not attempted"})
    for attempt in range(retries):
        last = _raw_request(method, path, token=token, body=body)
        status, _ = last
        if status not in (-1, 429) and status < 500:
            return last
        if attempt + 1 < retries:
            time.sleep(wait)
            wait = min(wait * 2, 8.0)
    return last


def _members(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if not isinstance(payload, dict):
        return []
    values = payload.get("hydra:member") or payload.get("member") or []
    return [item for item in values if isinstance(item, dict)]


def _fail(action: str, status: int, payload: dict[str, Any]) -> MailCodeError:
    detail = json.dumps(payload, ensure_ascii=False)[:300]
    return MailCodeError(f"{action}失败({status}): {detail}")


def get_domain() -> str:
    status, payload = _request("GET", "/domains")
    domains = [item for item in _members(payload) if item.get("isActive", True)]
    if status != 200 or not domains:
        raise _fail("拉取可用域名", status, payload)
    domain = domains[0].get("domain")
    if not isinstance(domain, str) or not domain:
        raise MailCodeError("mail.tm 未返回有效域名")
    return domain


def login(address: str, password: str) -> str:
    status, payload = _request(
        "POST", "/token", body={"address": address, "password": password}
    )
    token = payload.get("token")
    if status != 200 or not isinstance(token, str) or not token:
        raise _fail("邮箱登录", status, payload)
    return token


def _secure_random(alphabet: str, length: int) -> str:
    return "".join(secrets.choice(alphabet) for _ in range(length))


def create_account() -> dict[str, str]:
    domain = get_domain()
    alphabet = string.ascii_lowercase + string.digits
    password_alphabet = string.ascii_letters + string.digits + "-_"
    last_status = -1
    last_payload: dict[str, Any] = {}
    for _ in range(4):
        address = f"user_{_secure_random(alphabet, 12)}@{domain}"
        password = _secure_random(password_alphabet, 24)
        status, payload = _request(
            "POST", "/accounts", body={"address": address, "password": password}
        )
        last_status, last_payload = status, payload
        if status in (200, 201):
            token = login(address, password)
            return {
                "id": str(payload.get("id") or ""),
                "address": address,
                "password": password,
                "token": token,
                "domain": domain,
            }
        if status != 409:
            break
    raise _fail("创建邮箱账号", last_status, last_payload)


def save_account(path: Path, account: dict[str, str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC
    fd = os.open(temporary, flags, 0o600)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(account, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
        os.replace(temporary, path)
        os.chmod(path, 0o600)
    finally:
        if temporary.exists():
            temporary.unlink()


def load_account(path: Path) -> dict[str, str]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise MailCodeError(f"读取 account file 失败: {exc}") from exc
    if not isinstance(payload, dict):
        raise MailCodeError("account file 必须是 JSON object")
    address = payload.get("address")
    password = payload.get("password")
    if not isinstance(address, str) or not isinstance(password, str):
        raise MailCodeError("account file 缺少 address/password")
    return {str(key): str(value) for key, value in payload.items() if value is not None}


def identity(args: argparse.Namespace) -> tuple[dict[str, str], str]:
    if args.account_file:
        account = load_account(Path(args.account_file))
    elif args.address and args.password:
        account = {"address": args.address, "password": args.password}
    else:
        raise MailCodeError("请提供 --account-file，或同时提供 --address 与 --password")
    # Refresh on every invocation instead of trusting a token persisted by an
    # earlier run; mail.tm tokens can expire while the mailbox remains valid.
    token = login(account["address"], account["password"])
    return account, token


def _html_content(value: Any) -> tuple[str, list[str]]:
    fragments = value if isinstance(value, list) else [value or ""]
    parser = _MailHTMLParser()
    for fragment in fragments:
        parser.feed(str(fragment))
    return " ".join(parser.text), parser.links


def extract_code(text: str, regex: str = DEFAULT_CODE_RE) -> str | None:
    keyword = re.search(
        r"(?:verification\s*code|security\s*code|one[- ]time\s*(?:code|password)|"
        r"otp|验证码|校验码|动态码)\D{0,32}(\d{4,8})",
        text,
        re.IGNORECASE,
    )
    if keyword:
        return keyword.group(1)
    match = re.search(regex, text)
    if not match:
        return None
    return match.group(1) if match.lastindex else match.group(0)


def extract_links(text: str, links: list[str]) -> list[str]:
    found = links + URL_RE.findall(text)
    unique: list[str] = []
    for value in found:
        cleaned = html.unescape(value).rstrip(".,);]")
        if cleaned.lower().startswith(("http://", "https://")) and cleaned not in unique:
            unique.append(cleaned)
    return unique


def _matches(message: dict[str, Any], sender: str, subject: str) -> bool:
    from_address = str((message.get("from") or {}).get("address") or "").lower()
    actual_subject = str(message.get("subject") or "").lower()
    return (not sender or sender.lower() in from_address) and (
        not subject or subject.lower() in actual_subject
    )


def list_messages(token: str, sender: str = "", subject: str = "") -> list[dict[str, Any]]:
    status, payload = _request("GET", "/messages", token=token)
    if status != 200:
        raise _fail("读取收件箱", status, payload)
    return [item for item in _members(payload) if _matches(item, sender, subject)]


def message_detail(token: str, message_id: str) -> dict[str, Any]:
    status, payload = _request("GET", f"/messages/{message_id}", token=token)
    if status != 200:
        raise _fail("读取邮件", status, payload)
    return payload


def cmd_create(args: argparse.Namespace) -> None:
    account = create_account()
    if args.account_file:
        path = Path(args.account_file)
        save_account(path, account)
        print(json.dumps({"address": account["address"], "account_file": str(path)}, ensure_ascii=False, indent=2))
    else:
        print(json.dumps(account, ensure_ascii=False, indent=2))


def cmd_list(args: argparse.Namespace) -> None:
    _, token = identity(args)
    messages = list_messages(token, args.sender, args.subject)
    output = [
        {
            "created_at": item.get("createdAt"),
            "from": (item.get("from") or {}).get("address"),
            "subject": item.get("subject"),
            "message_id": item.get("id"),
        }
        for item in messages
    ]
    print(json.dumps(output, ensure_ascii=False, indent=2))


def cmd_poll(args: argparse.Namespace) -> None:
    re.compile(args.regex)
    _, token = identity(args)
    deadline = time.monotonic() + args.timeout
    wait = 3.0
    inspected: set[str] = set()
    while time.monotonic() < deadline:
        messages = list_messages(token, args.sender, args.subject)
        for message in messages:
            message_id = str(message.get("id") or "")
            if not message_id or message_id in inspected:
                continue
            inspected.add(message_id)
            detail = message_detail(token, message_id)
            html_text, html_links = _html_content(detail.get("html"))
            text = "\n".join(
                str(value or "")
                for value in (
                    detail.get("text"),
                    detail.get("intro"),
                    message.get("subject"),
                    html_text,
                )
            )
            result: dict[str, Any] = {
                "from": (message.get("from") or {}).get("address", ""),
                "subject": message.get("subject", ""),
                "message_id": message_id,
            }
            if args.extract in ("code", "both"):
                result["code"] = extract_code(text, args.regex)
            if args.extract in ("link", "both"):
                result["links"] = extract_links(text, html_links)
            if result.get("code") or result.get("links"):
                print(json.dumps(result, ensure_ascii=False, indent=2))
                return
        time.sleep(wait)
        wait = min(wait * 1.5, 15.0)
    raise MailCodeError(f"等待 {args.timeout}s 未收到匹配的验证码或验证链接")


def cmd_delete(args: argparse.Namespace) -> None:
    account, token = identity(args)
    account_id = account.get("id")
    if not account_id:
        status, payload = _request("GET", "/me", token=token)
        if status != 200 or not payload.get("id"):
            raise _fail("获取邮箱账号 ID", status, payload)
        account_id = str(payload["id"])
    status, payload = _request("DELETE", f"/accounts/{account_id}", token=token)
    if status not in (200, 202, 204):
        raise _fail("删除邮箱账号", status, payload)
    if args.account_file:
        Path(args.account_file).unlink(missing_ok=True)
    print(json.dumps({"deleted": True, "address": account["address"]}, ensure_ascii=False))


def add_identity_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--account-file")
    parser.add_argument("--address")
    parser.add_argument("--password")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="mail.tm 临时测试邮箱助手")
    commands = parser.add_subparsers(dest="cmd", required=True)

    create = commands.add_parser("create", help="创建临时邮箱")
    create.add_argument("--account-file", help="以 0600 权限保存邮箱凭据")
    create.set_defaults(func=cmd_create)

    listing = commands.add_parser("list", help="查看收件箱摘要")
    add_identity_arguments(listing)
    listing.add_argument("--sender", default="")
    listing.add_argument("--subject", default="")
    listing.set_defaults(func=cmd_list)

    poll = commands.add_parser("poll", help="轮询验证码或验证链接")
    add_identity_arguments(poll)
    poll.add_argument("--timeout", type=int, default=180)
    poll.add_argument("--regex", default=DEFAULT_CODE_RE)
    poll.add_argument("--sender", default="")
    poll.add_argument("--subject", default="")
    poll.add_argument("--extract", choices=("code", "link", "both"), default="code")
    poll.set_defaults(func=cmd_poll)

    delete = commands.add_parser("delete", help="删除临时邮箱账号")
    add_identity_arguments(delete)
    delete.set_defaults(func=cmd_delete)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        args.func(args)
    except (MailCodeError, re.error) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
