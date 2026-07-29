import json
from pathlib import Path

import pytest

from workflow.artifacts import ArtifactLayout, target_domain


@pytest.mark.parametrize(
    ("target", "expected"),
    [
        ("https://Example.COM/app/login?next=/admin", "example.com"),
        ("example.com:8443/api", "example.com"),
        ("https://sub.example.com./", "sub.example.com"),
        ("https://127.0.0.1:9443/test", "127.0.0.1"),
    ],
)
def test_target_domain_uses_only_normalized_hostname(target: str, expected: str):
    assert target_domain(target) == expected


def test_layout_classifies_artifacts_below_domain_root(tmp_path: Path):
    layout = ArtifactLayout(tmp_path, "https://Example.com:8443/a?b=1")
    manifest_path = layout.ensure()

    assert layout.root == tmp_path / "output" / "example.com"
    assert layout.js == layout.root / "assets" / "js"
    assert layout.analysis == layout.root / "analysis"
    assert layout.evidence == layout.root / "evidence"
    assert layout.reports == layout.root / "reports"
    assert layout.resolve("evidence/result.json") == layout.evidence / "result.json"

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["domain"] == "example.com"
    assert manifest["categories"]["assets/js"] == "assets/js"


@pytest.mark.parametrize("relative", ["../escape.txt", "analysis/../../escape.txt", "/tmp/x"])
def test_layout_rejects_paths_outside_target_root(tmp_path: Path, relative: str):
    layout = ArtifactLayout(tmp_path, "https://example.com")
    with pytest.raises(ValueError):
        layout.resolve(relative)
