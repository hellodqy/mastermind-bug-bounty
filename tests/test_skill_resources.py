import re
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
SKILLS = ROOT / "skills"
REFERENCES = ROOT / "references"


def test_every_skill_has_discriminating_frontmatter_and_bounded_constraints():
    violations = []
    for path in sorted(SKILLS.glob("*/SKILL.md")):
        text = path.read_text(encoding="utf-8")
        frontmatter = text.split("---", 2)
        if len(frontmatter) < 3 or "name:" not in frontmatter[1] or "description:" not in frontmatter[1]:
            violations.append(f"{path.relative_to(ROOT)}: missing name/description frontmatter")
        match = re.search(r"## Constraints\n(.*?)(?:\n## |\Z)", text, re.S)
        if not match:
            violations.append(f"{path.relative_to(ROOT)}: missing Constraints section")
            continue
        constraints = re.findall(r"^\d+\. ", match.group(1), re.M)
        if not 1 <= len(constraints) <= 5:
            violations.append(
                f"{path.relative_to(ROOT)}: expected 1-5 constraints, found {len(constraints)}"
            )
    assert violations == [], "Invalid Skill shape:\n" + "\n".join(violations)


def test_skill_markdown_resource_links_exist():
    broken = []
    for path in sorted(SKILLS.glob("*/SKILL.md")):
        for name in re.findall(r"`([^`]+\.md)`", path.read_text(encoding="utf-8")):
            target = ROOT / name if "/" in name else REFERENCES / name
            if not target.exists():
                broken.append(f"{path.relative_to(ROOT)} -> {name}")
    assert broken == [], "Broken Skill resource links:\n" + "\n".join(broken)


def test_reference_index_covers_every_top_level_resource():
    index = (REFERENCES / "INDEX.md").read_text(encoding="utf-8")
    missing = [
        path.name
        for path in sorted(REFERENCES.glob("*.md"))
        if path.name != "INDEX.md" and f"`{path.name}`" not in index
    ]
    assert missing == [], "References missing from INDEX.md: " + ", ".join(missing)


def test_all_report_entrypoints_route_through_report_writing_skill():
    route = "skills/vuln_report_writing/SKILL.md"
    entrypoints = (
        ROOT / "SKILL.md",
        ROOT / "workflow" / "SKILL.md",
        ROOT / "agents" / "report" / "SKILL.md",
    )
    missing = [
        str(path.relative_to(ROOT))
        for path in entrypoints
        if route not in path.read_text(encoding="utf-8")
    ]
    assert missing == [], "Report entrypoints missing mandatory routing: " + ", ".join(missing)

    template = SKILLS / "vuln_report_writing" / "templates" / "report_template.md"
    assert template.is_file()
