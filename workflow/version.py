"""Version helpers for CLI and release checks."""

from __future__ import annotations

import os
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SEMVER_RE = re.compile(r"^v?(\d+\.\d+\.\d+)")


def package_version() -> str:
    return (ROOT / "VERSION").read_text(encoding="utf-8").strip()


def release_version(raw: str | None = None) -> str:
    candidate = raw or os.environ.get("MASTERMIND_RELEASE_VERSION", "")
    match = SEMVER_RE.match(candidate.strip())
    return match.group(1) if match else package_version()
