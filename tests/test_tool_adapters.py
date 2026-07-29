from pathlib import Path

from workflow.tools import ToolContext, default_registry


def test_endpoint_aggregation_and_base_url(tmp_path: Path):
    target = "https://example.com"
    context = ToolContext(tmp_path, target)
    analysis = context.layout.analysis
    js_dir = context.layout.js
    js_dir.mkdir(parents=True)
    analysis.mkdir(parents=True)
    (js_dir / "app.js").write_text("console.log(1)", encoding="utf-8")
    (analysis / "_analysis_app.json").write_text(
        """
        {
          "analyzed": true,
          "filename": "app.js",
          "classification": "app",
          "priority": "P1",
          "endpoints": [
            {
              "url": "https://api.example.com/user/list",
              "method": "POST",
              "content_type": "application/json",
              "auth": "Bearer",
              "params_required": ["pageNum"],
              "params_optional": ["pageSize"],
              "source_files": ["app.js"]
            }
          ],
          "login_links": [{"url": "/login", "type": "route"}]
        }
        """,
        encoding="utf-8",
    )

    registry = default_registry()
    result = registry.execute("aggregate_endpoint_analysis", context)
    assert result.success
    assert (analysis / "_endpoint_params.json").exists()

    base = registry.execute("determine_base_url", context)
    assert base.success
    assert (analysis / "_base_url.txt").read_text(encoding="utf-8") == "https://api.example.com"


def test_probe_plan_and_candidate_aggregation(tmp_path: Path):
    context = ToolContext(tmp_path, "https://example.com")
    analysis = context.layout.analysis
    evidence = context.layout.evidence
    analysis.mkdir(parents=True)
    evidence.mkdir(parents=True)
    (analysis / "_base_url.txt").write_text("https://example.com", encoding="utf-8")
    (analysis / "_endpoint_params.json").write_text(
        '{"endpoints": {"/api/users": {"method": "POST", "content_type": "application/json"}}}',
        encoding="utf-8",
    )
    registry = default_registry()
    plan = registry.execute("build_probe_plan", context)
    assert plan.success

    (evidence / "_probe_results.json").write_text(
        '{"results": [{"url": "https://example.com/api/users", "status": 200, "body": "{\\"records\\":[{\\"email\\":\\"a@example.com\\"}]}"}]}',
        encoding="utf-8",
    )
    mined = registry.execute("mine_probe_results", context)
    assert mined.success
    candidates = registry.execute("aggregate_candidates", context)
    assert candidates.success
    assert (evidence / "_candidate_findings.json").exists()
