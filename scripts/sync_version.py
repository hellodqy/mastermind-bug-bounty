#!/usr/bin/env python3
"""Synchronize VERSION and SKILL.md metadata.version."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VERSION_FILE = ROOT / "VERSION"
SKILL_FILES = (
    ROOT / "SKILL.md",
    ROOT / "workflow" / "SKILL.md",
)
SEMVER_RE = re.compile(r"^v?(\d+\.\d+\.\d+)")


def read_version() -> str:
    return VERSION_FILE.read_text(encoding="utf-8").strip()


def read_skill_versions() -> dict[Path, str]:
    versions: dict[Path, str] = {}
    for skill_file in SKILL_FILES:
        if not skill_file.exists():
            continue
        text = skill_file.read_text(encoding="utf-8")
        match = re.search(r'^\s*version:\s*"([^"]+)"\s*$', text, re.M)
        if not match:
            raise SystemExit(f"{skill_file.relative_to(ROOT)} metadata.version not found")
        versions[skill_file] = match.group(1)
    return versions


def read_skill_version() -> str:
    versions = read_skill_versions()
    return versions[ROOT / "SKILL.md"]


def _update_skill_file(skill_file: Path, version: str) -> None:
    text = skill_file.read_text(encoding="utf-8")
    match = re.search(r'^\s*version:\s*"([^"]+)"\s*$', text, re.M)
    if not match:
        raise SystemExit(f"{skill_file.relative_to(ROOT)} metadata.version not found")
    updated = re.sub(
        r'^(\s*version:\s*")[^"]+("\s*)$',
        rf'\g<1>{version}\2',
        text,
        count=1,
        flags=re.M,
    )
    skill_file.write_text(updated, encoding="utf-8")


def normalize_tag(tag: str) -> str:
    match = SEMVER_RE.match(tag.strip())
    if not match:
        raise SystemExit(f"Release tag does not start with a semantic version: {tag}")
    return match.group(1)


def write_version(version: str) -> None:
    if not SEMVER_RE.match(version):
        raise SystemExit(f"Version must be semantic x.y.z: {version}")
    version = normalize_tag(version)
    VERSION_FILE.write_text(version + "\n", encoding="utf-8")
    for skill_file in SKILL_FILES:
        if skill_file.exists():
            _update_skill_file(skill_file, version)


def check(expected_tag: str | None = None) -> int:
    version = read_version()
    skill_versions = read_skill_versions()
    errors: list[str] = []
    for skill_file, skill_version in skill_versions.items():
        if version != skill_version:
            errors.append(
                f"VERSION={version} but {skill_file.relative_to(ROOT)}={skill_version}"
            )
    if expected_tag and normalize_tag(expected_tag) != version:
        errors.append(f"release tag {expected_tag} does not match VERSION {version}")
    if errors:
        for error in errors:
            print("ERROR:", error)
        return 1
    print(f"version ok: {version}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("version", nargs="?", help="Version to write, e.g. 4.3.0")
    parser.add_argument("--check", action="store_true", help="Check files are synchronized")
    parser.add_argument("--tag", help="Expected release tag, e.g. v4.3.0-four-phase")
    args = parser.parse_args()

    if args.version:
        write_version(args.version)
    if args.check or not args.version:
        return check(args.tag)
    return 0


if __name__ == "__main__":
    sys.exit(main())
