"""
shared/utils.py — Shared utilities for Mastermind Bug Bounty.

Pure functions with zero external dependencies.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Time
# ---------------------------------------------------------------------------

def now_iso() -> str:
    """Return current UTC time as ISO-8601 string."""
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


# ---------------------------------------------------------------------------
# ID generation
# ---------------------------------------------------------------------------

def gen_id(prefix: str = "") -> str:
    """Generate a short unique ID, optionally prefixed."""
    uid = uuid.uuid4().hex[:8]
    return f"{prefix}_{uid}" if prefix else uid


def finding_id() -> str:
    return gen_id("find")


def hunt_id() -> str:
    return gen_id("hunt")


def session_id() -> str:
    return gen_id("sess")


# ---------------------------------------------------------------------------
# Host / URL helpers
# ---------------------------------------------------------------------------

def extract_host(raw: str) -> str:
    """Best-effort hostname extraction from a URL or host string."""
    if not raw:
        return ""
    s = str(raw)
    # Strip protocol
    if "://" in s:
        s = s.split("://", 1)[1]
    # Strip path / query / fragment
    s = s.split("/")[0].split("?")[0].split("#")[0]
    # Strip port
    s = s.split(":")[0]
    return s.lower().strip()


def extract_host_from_dict(d: dict) -> str:
    """Extract host from common tool-argument keys."""
    for key in ("host", "url", "target", "domain", "u", "-u", "target_url", "target_host"):
        val = d.get(key)
        if val:
            return extract_host(str(val))
    return ""


# ---------------------------------------------------------------------------
# File I/O (safe, with fallbacks)
# ---------------------------------------------------------------------------

def read_json(path: str | Path) -> dict:
    """Read JSON file; return {} on any error."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError, PermissionError):
        return {}


def write_json(path: str | Path, data: dict, indent: int = 2) -> bool:
    """Write JSON file atomically. Returns True on success."""
    try:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        tmp = str(path) + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=indent, ensure_ascii=False)
        os.replace(tmp, str(path))
        return True
    except (PermissionError, OSError):
        return False


def read_lines(path: str | Path) -> list[str]:
    """Read file lines; return [] on error."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.readlines()
    except (FileNotFoundError, PermissionError):
        return []


def read_text(path: str | Path) -> str:
    """Read entire file; return '' on error."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except (FileNotFoundError, PermissionError):
        return ""


def append_line(path: str | Path, line: str) -> bool:
    """Append a line to a file. Creates parent dirs. Returns True on success."""
    try:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, "a", encoding="utf-8") as f:
            f.write(line + "\n")
        return True
    except (PermissionError, OSError):
        return False


# ---------------------------------------------------------------------------
# JSONL helpers
# ---------------------------------------------------------------------------

def append_jsonl(path: str | Path, entry: dict) -> bool:
    """Append a dict as a compact JSON line."""
    line = json.dumps(entry, separators=(",", ":"), ensure_ascii=False)
    return append_line(path, line)


def read_jsonl(path: str | Path) -> list[dict]:
    """Parse a JSONL file into a list of dicts."""
    entries: list[dict] = []
    for line in read_lines(path):
        line = line.strip()
        if not line:
            continue
        try:
            entries.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return entries


# ---------------------------------------------------------------------------
# Slug / safe filename
# ---------------------------------------------------------------------------

def slugify(text: str, max_len: int = 60) -> str:
    """Convert arbitrary text to a filesystem-safe slug."""
    s = text.lower().strip()
    s = re.sub(r"[^\w\-]", "_", s)
    s = re.sub(r"_+", "_", s)
    return s[:max_len].strip("_")


# ---------------------------------------------------------------------------
# Hash
# ---------------------------------------------------------------------------

def sha256_short(data: str) -> str:
    """Return first 12 hex chars of SHA-256."""
    return hashlib.sha256(data.encode()).hexdigest()[:12]
