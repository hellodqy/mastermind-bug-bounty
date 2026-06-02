"""
tests/test_linkage.py — Pairing Engine & Value Pool Tests

Tests cover the core data linkage methodology that's at the heart
of the framework. If these break, the whole framework is broken.
"""

import json, sys, tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from shared.linkage import (
    ValuePool, EndpointRegistry, PairingEngine,
    check_pair_completeness, build_method_fallback_matrix,
    check_js_analysis_completeness, is_known_third_party,
    canonical_param_name, PARAM_ALIASES,
    load_linkage_state, save_linkage_state
)
from shared.types import ValueStatus, ValueEntry


class TestValuePool:
    """ValuePool with consumption queue."""

    def test_add_and_dedup(self):
        pool = ValuePool()
        e1 = pool.add_value("uid", "admin", source_endpoint="/user/list", priority="HIGH")
        e2 = pool.add_value("uid", "admin")  # duplicate
        assert len(pool.get_values("uid")) == 1
        assert e1.value == "admin"
        assert e1.status == ValueStatus.PENDING
        assert e1.priority == "HIGH"

    def test_status_flow(self):
        pool = ValuePool()
        pool.add_value("uid", "admin")
        entry = pool.get_values("uid")[0]
        assert entry.status == ValueStatus.PENDING

        pool.set_unconsumed_endpoints("uid", "admin", ["/user/detail", "/user/edit"])
        entry = pool.get_values("uid")[0]
        assert entry.status == ValueStatus.CONSUMING
        assert len(entry.unconsumed_endpoints) == 2

        pool.mark_consumed("uid", "admin", "/user/detail")
        entry = pool.get_values("uid")[0]
        assert "/user/detail" in entry.consumed_endpoints
        assert "/user/detail" not in entry.unconsumed_endpoints
        assert entry.status == ValueStatus.CONSUMING  # still has /user/edit

        pool.mark_consumed("uid", "admin", "/user/edit")
        entry = pool.get_values("uid")[0]
        assert entry.status == ValueStatus.CONSUMED

    def test_has_pending(self):
        pool = ValuePool()
        assert not pool.has_pending()

        pool.add_value("uid", "admin")
        assert pool.has_pending()

        pool.set_unconsumed_endpoints("uid", "admin", [])
        assert not pool.has_pending()

    def test_serialization_roundtrip(self):
        pool = ValuePool()
        pool.add_value("uid", "admin", source_endpoint="/user/list", priority="HIGH")
        pool.add_value("uid", "huizhang43")
        pool.set_unconsumed_endpoints("uid", "admin", ["/user/detail"])
        pool.mark_consumed("uid", "admin", "/user/detail")

        data = pool.to_dict()
        pool2 = ValuePool.from_dict(data)

        entries = pool2.get_values("uid")
        assert len(entries) == 2
        admin_entry = [e for e in entries if e.value == "admin"][0]
        assert admin_entry.status == ValueStatus.CONSUMED
        assert "/user/detail" in admin_entry.consumed_endpoints

    def test_canonical_names(self):
        """uid, userId, user_id should all map to 'uid'."""
        pool = ValuePool()
        pool.add_value("userId", 10086)
        pool.add_value("user_id", 10087)
        pool.add_value("uid", "admin")

        # All should be retrievable under 'uid'
        values = [e.value for e in pool.get_values("uid")]
        assert "10086" in values
        assert "10087" in values
        assert "admin" in values


class TestEndpointRegistry:
    """Endpoint → parameter requirements registry."""

    def test_add_and_get(self):
        reg = EndpointRegistry()
        reg.add("/api/user/list", "POST", content_type="application/json",
                auth="Bearer", params_required=["page", "pageSize"])

        req = reg.get("/api/user/list")
        assert req is not None
        assert req.method == "POST"
        assert req.params_required == ["page", "pageSize"]
        assert "page" in reg.get_all_param_names()

    def test_from_file(self):
        data = {
            "/api/user/info": {
                "method": "POST", "content_type": "application/json",
                "auth": "Bearer", "params_required": ["userId"],
                "source_files": ["app.js"], "notes": ""
            }
        }
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(data, f)
            path = f.name

        reg = EndpointRegistry.from_file(path)
        req = reg.get("/api/user/info")
        assert req.method == "POST"
        assert req.params_required == ["userId"]

        Path(path).unlink()

    def test_from_file_v2_4_format(self):
        """v2.4 nested format: _meta + endpoints wrapper."""
        data = {
            "_meta": {
                "js_files_collected": 3,
                "js_files_analyzed": 3,
                "analysis_completeness": 1.0,
                "total_endpoints_extracted": 3,
            },
            "endpoints": {
                "/api/user/list": {
                    "method": "POST", "content_type": "application/json",
                    "auth": "none", "params_required": ["pageNum", "pageSize"],
                    "source_files": ["app.js"], "notes": ""
                },
                "/api/user/detail": {
                    "method": "GET", "content_type": "",
                    "auth": "none", "params_required": ["uid"],
                    "source_files": ["layout.js"], "notes": ""
                },
                "/api/user/info": {
                    "method": "POST", "content_type": "application/json",
                    "auth": "Bearer", "params_required": ["userId"],
                    "source_files": ["app.js"], "notes": ""
                },
            }
        }
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(data, f)
            path = f.name

        reg = EndpointRegistry.from_file(path)

        # Should NOT contain _meta as an endpoint
        assert reg.get("_meta") is None
        assert reg.get("endpoints") is None

        # Should contain the 3 real endpoints
        assert len(reg.all_endpoints()) == 3

        req = reg.get("/api/user/list")
        assert req.method == "POST"
        assert req.params_required == ["pageNum", "pageSize"]

        req2 = reg.get("/api/user/detail")
        assert req2.method == "GET"
        assert req2.params_required == ["uid"]

        req3 = reg.get("/api/user/info")
        assert req3.method == "POST"
        assert req3.params_required == ["userId"]

        Path(path).unlink()


class TestPairingEngine:
    """The core formula: _endpoint_params.json x _leaked_values.json."""

    def setup_method(self):
        self.registry = EndpointRegistry()
        self.registry.add("/api/user/detail", "GET", params_required=["uid"])
        self.registry.add("/api/user/info", "POST", content_type="application/json",
                          auth="Bearer", params_required=["userId"])

        self.pool = ValuePool()
        self.pool.add_value("uid", "admin", source_endpoint="/api/user/list",
                           source_param="uid", priority="HIGH")
        self.pool.add_value("uid", "huizhang43", source_endpoint="/api/user/list",
                           source_param="uid", priority="MEDIUM")

        self.engine = PairingEngine(self.registry, self.pool)

    def test_sync_and_match(self):
        self.engine.sync_consumption_state()

        # uid=admin should have /user/detail as unconsumed
        entries = self.pool.get_values("uid")
        admin = [e for e in entries if e.value == "admin"][0]
        assert "/api/user/detail" in admin.unconsumed_endpoints

    def test_match_generates_pairs(self):
        self.engine.sync_consumption_state()
        pairs = self.engine.match()

        # uid=admin → /user/detail (exact match + HIGH) + semantic match to /user/info
        # uid=huizhang43 → same but MEDIUM
        detail_pairs = [p for p in pairs if p.endpoint == "/api/user/detail"]
        assert len(detail_pairs) >= 1
        assert detail_pairs[0].method == "GET"
        assert detail_pairs[0].param_name == "uid"
        assert detail_pairs[0].value_entry.value == "admin"

    def test_pair_completeness_check(self):
        self.engine.sync_consumption_state()
        pairs = self.engine.match()
        check = check_pair_completeness(pairs)
        assert not check.passed  # admin is CRITICAL unconsumed
        assert len(check.critical_unconsumed) >= 1

        # Mark all as consumed
        for p in pairs:
            self.pool.mark_consumed(
                p.param_name, p.value_entry.value, p.endpoint
            )

        pairs2 = self.engine.match()
        check2 = check_pair_completeness(pairs2)
        assert check2.passed

    def test_semantic_matching(self):
        """userId in registry should match uid in pool via semantic expansion."""
        self.engine.sync_consumption_state()
        pairs = self.engine.match(semantic_expand=True)

        # uid from pool should match userId in /api/user/info via semantic group
        info_pairs = [p for p in pairs if p.endpoint == "/api/user/info"]
        assert len(info_pairs) >= 1, \
            f"Expected semantic match uid→userId on /api/user/info, got {len(info_pairs)} pairs"


class TestMethodFallback:
    """Method fallback matrix builder."""

    def test_trigger_codes(self):
        m1 = build_method_fallback_matrix("/api/user/detail", "POST", 500)
        assert len(m1) >= 8  # GET + PUTx3 + PATCHx3 + DELETE

        m2 = build_method_fallback_matrix("/api/user/detail", "POST", 200)
        assert len(m2) == 0  # 200 should NOT trigger

        m3 = build_method_fallback_matrix("/api/user/detail", "POST", 401)
        assert len(m3) == 0  # 401 should NOT trigger

    def test_content_type_matrix(self):
        matrix = build_method_fallback_matrix("/api/user/detail", "POST", 405)
        ct_methods = [m for m in matrix if m["content_type"] is not None]
        # PUT with 3 content types, PATCH with 3
        assert len(ct_methods) >= 6


class TestJSAnalysisCompleteness:
    """The Phase 0 gate check."""

    def test_empty_file_blocks(self):
        result = check_js_analysis_completeness({})
        assert not result.passed

    def test_full_analysis_passes(self):
        endpoints = {
            "_meta": {
                "js_files_collected": 5, "js_files_analyzed": 5,
                "analysis_completeness": 1.0,
                "files_detail": {
                    "app.js": {"analyzed": True, "api_calls_found": 12},
                    "admin.js": {"analyzed": True, "api_calls_found": 15},
                },
                "total_endpoints_extracted": 27,
                "generated_at": "2026-05-19T12:00:00Z"
            },
            "endpoints": {
                "/api/user/list": {"method": "POST", "source_files": ["app.js"]},
                "/api/user/info": {"method": "POST", "source_files": ["app.js"]},
                "/api/admin/config": {"method": "GET", "source_files": ["admin.js"]},
            }
        }
        result = check_js_analysis_completeness(endpoints)
        assert result.passed, f"Expected pass, got: {result.summary}"

    def test_download_only_blocks(self):
        endpoints = {
            "_meta": {
                "js_files_collected": 8, "js_files_analyzed": 0,
                "analysis_completeness": 0.0,
                "files_detail": {
                    "app.js": {"analyzed": False},
                    "admin.js": {"analyzed": False},
                },
                "total_endpoints_extracted": 0
            },
            "endpoints": {}
        }
        result = check_js_analysis_completeness(endpoints)
        assert not result.passed

    def test_missing_method_blocks(self):
        endpoints = {
            "_meta": {
                "js_files_collected": 3, "js_files_analyzed": 3,
                "analysis_completeness": 1.0,
                "files_detail": {"app.js": {"analyzed": True, "api_calls_found": 5}},
                "total_endpoints_extracted": 5
            },
            "endpoints": {
                "/api/user/list": {"method": "", "source_files": []},
                # method is empty!
            }
        }
        result = check_js_analysis_completeness(endpoints)
        assert not result.passed

    def test_known_third_party_detection(self):
        assert is_known_third_party("lodash.min.js")
        assert is_known_third_party("jquery-3.6.0.min.js")
        assert is_known_third_party("bootstrap.bundle.min.js")
        assert not is_known_third_party("app.js")
        assert not is_known_third_party("admin.js")
        assert not is_known_third_party("chunk-vendors.js")


class TestParamAliasNormalization:
    """Canonical param name mapping."""

    def test_all_aliases(self):
        test_cases = [
            ("userId", "uid"), ("user_id", "uid"), ("userid", "uid"),
            ("uid", "uid"), ("memberId", "uid"),
            ("orgId", "orgId"), ("org_id", "orgId"),
            ("token", "token"), ("accessToken", "token"),
            ("email", "email"), ("mail", "email"),
            ("phone", "phone"), ("mobile", "phone"),
        ]
        for raw, expected in test_cases:
            result = PARAM_ALIASES.get(raw, raw)
            assert result == expected, f"{raw} → expected {expected}, got {result}"


# ── Run all tests ──

if __name__ == "__main__":
    results = {"pass": 0, "fail": 0, "errors": []}
    test_classes = [
        TestValuePool, TestEndpointRegistry, TestPairingEngine,
        TestMethodFallback, TestJSAnalysisCompleteness, TestParamAliasNormalization
    ]

    for cls in test_classes:
        print(f"\n{'='*50}")
        print(f"  {cls.__name__}")
        print(f"{'='*50}")
        instance = cls()
        for name in dir(instance):
            if name.startswith("test_"):
                method = getattr(instance, name)
                try:
                    if hasattr(instance, 'setup_method') and name != 'setup_method':
                        instance.setup_method()
                    method()
                    results["pass"] += 1
                    print(f"  [PASS] {name}")
                except Exception as e:
                    results["fail"] += 1
                    results["errors"].append(f"{cls.__name__}.{name}: {e}")
                    print(f"  [FAIL] {name}: {e}")

    print(f"\n{'='*50}")
    print(f"  TOTAL: {results['pass']} passed, {results['fail']} failed")
    print(f"{'='*50}")

    if results["fail"] > 0:
        print("\nFailures:")
        for err in results["errors"]:
            print(f"  - {err}")
        sys.exit(1)
