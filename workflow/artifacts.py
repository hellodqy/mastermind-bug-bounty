"""Canonical artifact layout for a target hunt."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from urllib.parse import urlparse


def target_domain(target_url: str) -> str:
    """Return a filesystem-safe hostname without URL path, query, or port."""
    value = target_url.strip()
    parsed = urlparse(value if "://" in value else f"//{value}")
    host = parsed.hostname or ""
    if not host:
        host = value.split("/", 1)[0].split(":", 1)[0]
    host = host.rstrip(".").lower()
    try:
        host = host.encode("idna").decode("ascii")
    except UnicodeError:
        pass
    safe = re.sub(r"[^a-z0-9._-]+", "_", host).strip("._")
    return safe or "unknown-target"


@dataclass(frozen=True)
class ArtifactLayout:
    """Typed paths for process artifacts and final results."""

    hunt_dir: Path
    target_url: str

    @property
    def domain(self) -> str:
        return target_domain(self.target_url)

    @property
    def root(self) -> Path:
        return self.hunt_dir / "output" / self.domain

    @property
    def recon(self) -> Path:
        return self.root / "recon"

    @property
    def assets(self) -> Path:
        return self.root / "assets"

    @property
    def js(self) -> Path:
        return self.assets / "js"

    @property
    def sourcemaps(self) -> Path:
        return self.assets / "sourcemaps"

    @property
    def screenshots(self) -> Path:
        return self.assets / "screenshots"

    @property
    def analysis(self) -> Path:
        return self.root / "analysis"

    @property
    def evidence(self) -> Path:
        return self.root / "evidence"

    @property
    def reports(self) -> Path:
        return self.root / "reports"

    @property
    def runtime(self) -> Path:
        return self.root / "runtime"

    @property
    def scripts(self) -> Path:
        return self.runtime / "scripts"

    @property
    def logs(self) -> Path:
        return self.runtime / "logs"

    @property
    def queue(self) -> Path:
        return self.runtime / "queue"

    def resolve(self, relative: str | Path) -> Path:
        """Resolve a declared artifact path while preventing directory escape."""
        normalized = str(relative).replace("\\", "/")
        candidate = PurePosixPath(normalized)
        if candidate.is_absolute() or ".." in candidate.parts:
            raise ValueError(f"Artifact path must stay below the target directory: {relative}")
        return self.root.joinpath(*candidate.parts)

    def ensure(self) -> Path:
        """Create the classified tree and its machine-readable layout manifest."""
        categories = {
            "recon": self.recon,
            "assets/js": self.js,
            "assets/sourcemaps": self.sourcemaps,
            "assets/screenshots": self.screenshots,
            "analysis": self.analysis,
            "evidence": self.evidence,
            "reports": self.reports,
            "runtime/scripts": self.scripts,
            "runtime/logs": self.logs,
            "runtime/queue": self.queue,
        }
        for path in categories.values():
            path.mkdir(parents=True, exist_ok=True)

        manifest = self.root / "artifact-manifest.json"
        payload = {
            "schema_version": 1,
            "target": self.target_url,
            "domain": self.domain,
            "categories": {
                name: path.relative_to(self.root).as_posix()
                for name, path in categories.items()
            },
        }
        manifest.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        return manifest
