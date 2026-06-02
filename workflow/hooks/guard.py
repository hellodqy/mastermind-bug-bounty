"""
workflow/hooks/guard.py — Hook 2: Coordinator Guard

Trigger: Before every tool call / agent dispatch.
Checks: rate-limiting, delegation enforcement.
Gate: SOFT WARN — warns but never blocks execution.
"""

from __future__ import annotations

from collections import deque
from datetime import datetime, timezone
from typing import Any

from shared.types import GuardLevel, GuardResult
from shared.utils import extract_host


# ---------------------------------------------------------------------------
# Rate-limit store (ring buffer)
# ---------------------------------------------------------------------------

class RateLimitStore:
    """Sliding-window request tracker."""

    def __init__(self, window_seconds: int = 60, max_entries: int = 500) -> None:
        self._history: deque[dict] = deque(maxlen=max_entries)
        self._window_seconds = window_seconds

    def record(self, host: str, tool: str) -> None:
        self._history.append({
            "ts": datetime.now(timezone.utc).timestamp(),
            "host": host,
            "tool": tool,
        })

    def count(self, host: str) -> int:
        now = datetime.now(timezone.utc).timestamp()
        cutoff = now - self._window_seconds
        return sum(1 for e in self._history
                   if e["host"] == host and e["ts"] >= cutoff)

    def recent_tools(self, host: str) -> list[str]:
        now = datetime.now(timezone.utc).timestamp()
        cutoff = now - self._window_seconds
        return [e["tool"] for e in self._history
                if e["host"] == host and e["ts"] >= cutoff]


# ---------------------------------------------------------------------------
# Specialist tool list (tools that should be delegated)
# ---------------------------------------------------------------------------

SPECIALIST_TOOLS: set[str] = {
    "nmap", "ffuf", "gobuster", "sqlmap", "nikto",
    "dalfox", "commix", "xsstrike", "wpscan",
    "amass", "subfinder", "httpx", "katana", "hakrawler",
    "gau", "waybackurls", "dnsrecon", "theHarvester",
    "nuclei", "burp_scan", "zap_scan",
}

COORDINATOR_TOOLS: set[str] = {
    "read_file", "write_file", "edit_file", "list_files",
    "web_search", "shell", "bash",
}


# ---------------------------------------------------------------------------
# Checks
# ---------------------------------------------------------------------------

def check(deployed_tool: str, target_host: str,
          store: RateLimitStore | None = None,
          rate_threshold: int = 3) -> GuardResult:
    """Evaluate a proposed tool call.

    Args:
        deployed_tool: Name of the tool being called.
        target_host: Target hostname or URL.
        store: Rate-limit store (created fresh if None).
        rate_threshold: Max requests per host in window.

    Returns:
        GuardResult with approval status and nudges.
    """
    if store is None:
        store = RateLimitStore()

    host = extract_host(target_host)
    warnings: list[str] = []
    nudges: list[str] = []
    level = GuardLevel.NUDGE

    # 1. Rate-limit check
    if host:
        count = store.count(host)
        if count >= 6:
            level = GuardLevel.ALERT
            warnings.append(
                f"RATE LIMIT CRITICAL: {count} requests to {host} "
                f"(threshold: {rate_threshold}). Rotate or pause."
            )
        elif count >= 4:
            level = GuardLevel.WARN
            warnings.append(
                f"Rate limit warning: {count} requests to {host}. "
                "Consider slowing down."
            )
        elif count >= rate_threshold:
            level = GuardLevel.NUDGE
            nudges.append(
                f"{count} requests to {host}. "
                "Consider delegating to a specialist agent."
            )

    # 2. Delegation check
    tool_lower = deployed_tool.strip().lower()
    if tool_lower in SPECIALIST_TOOLS:
        if level.value < GuardLevel.WARN.value:
            level = GuardLevel.WARN
        nudges.append(
            f"'{deployed_tool}' is a specialist tool. "
            "Delegate to a specialist agent instead of running directly."
        )

    # Always allowed (soft gate)
    return GuardResult(
        allowed=True,
        warning="\n".join(warnings) if warnings else None,
        nudge="\n".join(nudges) if nudges else None,
        level=level,
    )


def format_nudge(result: GuardResult) -> str:
    """Format a GuardResult as a human-readable nudge message."""
    if not result.warning and not result.nudge:
        return ""

    prefix = {
        GuardLevel.NUDGE: "[NUDGE]",
        GuardLevel.WARN: "[WARN]",
        GuardLevel.ALERT: "[ALERT]",
    }.get(result.level, "")

    parts = [f"{prefix} Coordinator Guard"]
    if result.warning:
        parts.append(f"\n{result.warning}")
    if result.nudge:
        parts.append(f"\n{result.nudge}")
    return "".join(parts)
