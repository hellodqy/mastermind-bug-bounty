import re
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
KNOWLEDGE_ROOTS = (
    ROOT / "references",
    ROOT / "agents",
    ROOT / "skills",
    ROOT / "workflow",
    ROOT / "commands",
)


def _knowledge_files():
    yield ROOT / "SKILL.md"
    for directory in KNOWLEDGE_ROOTS:
        if directory.exists():
            yield from directory.rglob("*.md")


def test_knowledge_uses_only_the_current_four_phase_vocabulary():
    legacy_patterns = (
        re.compile(r"\bphase\s*(?:[4-9]|[1-9]\d+)\b", re.IGNORECASE),
        re.compile(r"\bphase\s*\d+\.\d+\b", re.IGNORECASE),
        re.compile(r"\b(?:six|seven)[ -]phase\b", re.IGNORECASE),
        re.compile(r"(?:六|七)阶段"),
    )
    violations = []

    for path in _knowledge_files():
        text = path.read_text(encoding="utf-8")
        for line_number, line in enumerate(text.splitlines(), start=1):
            if any(pattern.search(line) for pattern in legacy_patterns):
                violations.append(f"{path.relative_to(ROOT)}:{line_number}: {line.strip()}")

    assert violations == [], "Legacy phase vocabulary found:\n" + "\n".join(violations)


def test_pipeline_and_skill_publish_the_same_phase_names():
    from workflow.pipeline import PIPELINE

    expected = [
        "asset_recon",
        "attack_surface_analysis",
        "autonomous_attack",
        "report_generation",
    ]
    assert [phase.name for phase in PIPELINE] == expected

    root_skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
    for number in range(4):
        assert f"Phase {number} |" in root_skill
