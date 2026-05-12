"""Stage 3a — static + manual probe tests."""

import tempfile
from pathlib import Path

import pytest

from app.services.verify_runtime.base import (
    PROBE_STATUS_PASSED,
    PROBE_STATUS_FAILED,
    PROBE_STATUS_SKIPPED,
    PROBE_STATUS_ERROR,
    ProbeContext,
    RuntimeProbeResult,
)
from app.services.verify_runtime.static_probe import (
    run_static_probe,
    _build_patterns,
)
from app.services.verify_runtime.manual_probe import run_manual_probe


# ---------------------------------------------------------------------------
# fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def temp_repo():
    """یک repo کوچک با چند فایل ساختگی."""
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "backend" / "app").mkdir(parents=True)
        (root / "backend" / "app" / "main.py").write_text(
            "from fastapi import FastAPI\n"
            "def hello_world():\n    return 'hello'\n"
            "class MyService:\n    pass\n",
            encoding="utf-8",
        )
        (root / "frontend").mkdir()
        (root / "frontend" / "page.tsx").write_text(
            "export function Button() { return <button>click</button> }\n",
            encoding="utf-8",
        )
        (root / "node_modules").mkdir()
        (root / "node_modules" / "x.js").write_text("should not be scanned", encoding="utf-8")
        yield root


@pytest.fixture
def ctx(temp_repo):
    return ProbeContext(
        task_id="t1",
        run_id="r1",
        repo_path=str(temp_repo),
    )


# ---------------------------------------------------------------------------
# tests
# ---------------------------------------------------------------------------

class TestBuildPatterns:
    def test_uses_explicit_grep_patterns(self):
        ac = {"text": "X", "verify_method": "static", "verify_plan": {"grep_patterns": ["foo", "bar"]}}
        assert _build_patterns(ac) == ["foo", "bar"]

    def test_derives_from_text_when_no_patterns(self):
        ac = {"text": "وقتی MyService ایجاد شد", "verify_method": "static", "verify_plan": {}}
        p = _build_patterns(ac)
        assert "MyService" in p

    def test_returns_empty_for_empty_text(self):
        ac = {"text": "", "verify_method": "static", "verify_plan": {}}
        assert _build_patterns(ac) == []


class TestStaticProbe:
    def test_passes_when_pattern_found(self, ctx):
        ac = {"text": "MyService class exists", "verify_method": "static",
              "verify_plan": {"grep_patterns": ["MyService"]}}
        r = run_static_probe(ac, ctx, "ac1")
        assert r.status == PROBE_STATUS_PASSED
        assert r.evidence["total_hits"] >= 1
        assert any("main.py" in f for f in r.evidence["sample_files"])

    def test_fails_when_pattern_not_found(self, ctx):
        ac = {"text": "X", "verify_method": "static",
              "verify_plan": {"grep_patterns": ["totally_unique_string_xyz123"]}}
        r = run_static_probe(ac, ctx, "ac2")
        assert r.status == PROBE_STATUS_FAILED
        assert r.evidence["total_hits"] == 0

    def test_skipped_when_no_patterns_derivable(self, ctx):
        ac = {"text": "X", "verify_method": "static", "verify_plan": {}}
        r = run_static_probe(ac, ctx, "ac3")
        assert r.status == PROBE_STATUS_SKIPPED

    def test_skipped_when_no_repo_path(self):
        ctx = ProbeContext(task_id="t", run_id="r", repo_path=None)
        ac = {"text": "X", "verify_method": "static",
              "verify_plan": {"grep_patterns": ["x"]}}
        r = run_static_probe(ac, ctx, "ac4")
        assert r.status == PROBE_STATUS_SKIPPED

    def test_error_when_repo_path_invalid(self):
        ctx = ProbeContext(task_id="t", run_id="r", repo_path="/nonexistent/path/xyz123")
        ac = {"text": "X", "verify_method": "static",
              "verify_plan": {"grep_patterns": ["x"]}}
        r = run_static_probe(ac, ctx, "ac5")
        assert r.status == PROBE_STATUS_ERROR

    def test_node_modules_excluded(self, ctx):
        ac = {"text": "X", "verify_method": "static",
              "verify_plan": {"grep_patterns": ["should not be scanned"]}}
        r = run_static_probe(ac, ctx, "ac6")
        # متن "should not be scanned" در node_modules است — باید fail شود
        assert r.status == PROBE_STATUS_FAILED

    def test_uses_files_hint(self, ctx):
        ac = {"text": "X", "verify_method": "static",
              "verify_plan": {"grep_patterns": ["hello_world"], "files_hint": ["backend/app/main.py"]}}
        r = run_static_probe(ac, ctx, "ac7")
        assert r.status == PROBE_STATUS_PASSED


class TestManualProbe:
    def test_always_skipped(self):
        ac = {"text": "ظاهر شیک‌تر شود", "verify_method": "manual_only",
              "verify_plan": {"reason": "نیاز به بازبینی"}}
        ctx = ProbeContext(task_id="t", run_id="r")
        r = run_manual_probe(ac, ctx, "ac1")
        assert r.status == PROBE_STATUS_SKIPPED
        assert "بازبینی" in r.evidence["reason"]


class TestRuntimeProbeResult:
    def test_to_dict(self):
        r = RuntimeProbeResult(
            ac_id="a", ac_text="x", method="static", status="passed",
            evidence={"hits": 5}, duration_ms=100,
        )
        d = r.to_dict()
        assert d["ac_id"] == "a"
        assert d["evidence"]["hits"] == 5

    def test_summary_format(self):
        r = RuntimeProbeResult(
            ac_id="a", ac_text="x", method="ui_interaction", status="passed",
            duration_ms=850,
        )
        s = r.summary()
        assert "✅" in s
        assert "ui_interaction" in s
        assert "850ms" in s

    def test_summary_with_error(self):
        r = RuntimeProbeResult(
            ac_id="a", ac_text="x", method="api_response", status="error",
            error_message="connection refused",
        )
        s = r.summary()
        assert "⚠️" in s
        assert "connection refused" in s
