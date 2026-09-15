import importlib.util
import json
from pathlib import Path
import stat


ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "skills" / "mail_code" / "scripts" / "mail_code.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("mail_code", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_extract_code_prefers_keyword_context():
    module = _load_module()
    text = "Order 123456 was created. Your verification code is 654321."
    assert module.extract_code(text) == "654321"


def test_html_parser_extracts_text_and_verification_link():
    module = _load_module()
    text, links = module._html_content(
        '<p>Verify account</p><a href="https://example.test/verify?t=abc&amp;x=1">Continue</a>'
    )
    assert "Verify account" in text
    assert links == ["https://example.test/verify?t=abc&x=1"]


def test_extract_links_rejects_non_http_schemes():
    module = _load_module()
    links = module.extract_links(
        "Fallback https://example.test/verify?t=abc",
        ["javascript:alert(1)", "https://example.test/from-anchor"],
    )
    assert links == [
        "https://example.test/from-anchor",
        "https://example.test/verify?t=abc",
    ]


def test_account_file_is_private_and_round_trips(tmp_path: Path):
    module = _load_module()
    path = tmp_path / "runtime" / "mail-account.json"
    account = {
        "id": "account-id",
        "address": "test@example.test",
        "password": "secret",
        "token": "token",
    }
    module.save_account(path, account)
    assert module.load_account(path) == account
    assert stat.S_IMODE(path.stat().st_mode) == 0o600


def test_create_retries_address_conflict(monkeypatch):
    module = _load_module()
    responses = iter(
        [
            (409, {"detail": "address already used"}),
            (201, {"id": "new-id"}),
        ]
    )
    monkeypatch.setattr(module, "get_domain", lambda: "example.test")
    monkeypatch.setattr(module, "_request", lambda *args, **kwargs: next(responses))
    monkeypatch.setattr(module, "login", lambda address, password: "new-token")
    account = module.create_account()
    assert account["id"] == "new-id"
    assert account["address"].endswith("@example.test")
    assert account["token"] == "new-token"


def test_list_messages_applies_sender_and_subject_filters(monkeypatch):
    module = _load_module()
    payload = {
        "hydra:member": [
            {"from": {"address": "auth@example.com"}, "subject": "Verify account"},
            {"from": {"address": "news@example.com"}, "subject": "Newsletter"},
        ]
    }
    monkeypatch.setattr(module, "_request", lambda *args, **kwargs: (200, payload))
    messages = module.list_messages("token", sender="auth@", subject="verify")
    assert len(messages) == 1
    assert messages[0]["subject"] == "Verify account"
