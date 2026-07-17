import re
from pathlib import Path

from workflow.version import package_version, release_version


ROOT = Path(__file__).resolve().parent.parent


def test_version_files_are_synchronized():
    for skill_path in (ROOT / "SKILL.md", ROOT / "workflow" / "SKILL.md"):
        skill = skill_path.read_text(encoding="utf-8")
        match = re.search(r'^\s*version:\s*"([^"]+)"\s*$', skill, re.M)
        assert match
        assert match.group(1) == package_version()


def test_release_version_accepts_descriptive_tags():
    assert release_version("v4.3.0-four-phase-durable-queue") == "4.3.0"
