"""Stage 10 — end-to-end integration tests.

ست‌اپ:
- یک repo کوچک با کد واقعی
- یک HTTP server محلی برای API probe (با aiohttp)
- یک pytest dummy
- mix از AC ها با verify_methods مختلف
- اجرای run_probes_for_acs و چک نتایج

این تست‌ها بدون Playwright اجرا می‌شوند (UI probe خودکار skip می‌شود).
"""

import asyncio
import tempfile
from pathlib import Path

import pytest

from app.services.verify_runtime import (
    build_probe_context,
    run_probes_for_acs,
    get_breaker,
    PROBE_STATUS_PASSED,
    PROBE_STATUS_FAILED,
    PROBE_STATUS_SKIPPED,
)


@pytest.fixture
def known_good_repo():
    """repo که AC های static باید pass شوند."""
    with tempfile.TemporaryDirectory() as td:
        p = Path(td)
        (p / "backend").mkdir()
        (p / "backend" / "app.py").write_text(
            'from fastapi import FastAPI\n'
            'app = FastAPI()\n\n'
            '@app.get("/api/health")\n'
            'def health():\n    return {"ok": True, "version": "1.0"}\n\n'
            'class AuthService:\n'
            '    def __init__(self):\n        self.secret = "x"\n',
            encoding="utf-8",
        )
        (p / "tests").mkdir()
        (p / "tests" / "test_smoke.py").write_text(
            "def test_two_plus_two():\n    assert 2 + 2 == 4\n"
        )
        yield p


@pytest.fixture
def known_bad_repo():
    """repo که AC های static باید fail شوند (هیچ کلیدواژه‌ای پیدا نمی‌شود)."""
    with tempfile.TemporaryDirectory() as td:
        p = Path(td)
        (p / "main.py").write_text("# empty\npass\n")
        yield p


@pytest.fixture(autouse=True)
def reset_breaker():
    """قبل و بعد از هر تست، circuit breaker را ریست کن."""
    get_breaker().reset()
    yield
    get_breaker().reset()


# ---------------------------------------------------------------------------
# Known-good scenario
# ---------------------------------------------------------------------------

class TestKnownGood:
    @pytest.mark.asyncio
    async def test_static_acs_all_pass(self, known_good_repo):
        ctx = build_probe_context(task_id="t1", repo_path=str(known_good_repo))
        acs = [
            {"text": "AuthService class وجود دارد", "verify_method": "static",
             "verify_plan": {"grep_patterns": ["AuthService"]}},
            {"text": "endpoint /api/health تعریف شده", "verify_method": "static",
             "verify_plan": {"grep_patterns": ["api/health"]}},
        ]
        results = await run_probes_for_acs(acs, ctx)
        assert len(results) == 2
        assert all(r.status == PROBE_STATUS_PASSED for r in results)

    @pytest.mark.asyncio
    async def test_pytest_probe_passes(self, known_good_repo):
        ctx = build_probe_context(task_id="t1", repo_path=str(known_good_repo))
        acs = [{"text": "test_two_plus_two pass شود", "verify_method": "backend_test",
                "verify_plan": {"test_node": "tests/test_smoke.py::test_two_plus_two",
                                "timeout_seconds": 30}}]
        results = await run_probes_for_acs(acs, ctx)
        assert results[0].status == PROBE_STATUS_PASSED

    @pytest.mark.asyncio
    async def test_api_probe_no_base_url_skips(self, known_good_repo):
        """بدون backend_base_url، API probe باید skip شود (graceful)."""
        ctx = build_probe_context(task_id="t1", repo_path=str(known_good_repo))
        acs = [{"text": "/api/health → 200", "verify_method": "api_response",
                "verify_plan": {"path": "/api/health"}}]
        results = await run_probes_for_acs(acs, ctx)
        assert results[0].status == PROBE_STATUS_SKIPPED


# ---------------------------------------------------------------------------
# Known-bad scenario
# ---------------------------------------------------------------------------

class TestKnownBad:
    @pytest.mark.asyncio
    async def test_static_ac_fails(self, known_bad_repo):
        ctx = build_probe_context(task_id="t1", repo_path=str(known_bad_repo))
        acs = [{"text": "AuthService وجود دارد", "verify_method": "static",
                "verify_plan": {"grep_patterns": ["AuthService"]}}]
        results = await run_probes_for_acs(acs, ctx)
        assert results[0].status == PROBE_STATUS_FAILED

    @pytest.mark.asyncio
    async def test_pytest_failing_test(self, known_bad_repo):
        # نوشتن یک تست fail
        test_file = known_bad_repo / "test_bad.py"
        test_file.write_text("def test_bad():\n    assert 1 == 2\n")
        ctx = build_probe_context(task_id="t1", repo_path=str(known_bad_repo))
        acs = [{"text": "test_bad pass شود", "verify_method": "backend_test",
                "verify_plan": {"test_node": "test_bad.py::test_bad",
                                "timeout_seconds": 30}}]
        results = await run_probes_for_acs(acs, ctx)
        assert results[0].status == PROBE_STATUS_FAILED


# ---------------------------------------------------------------------------
# Mixed scenario — ground truth
# ---------------------------------------------------------------------------

class TestMixedScenario:
    @pytest.mark.asyncio
    async def test_mixed_static_pass_and_fail(self, known_good_repo):
        """ترکیبی از AC هایی که باید pass و fail شوند."""
        ctx = build_probe_context(task_id="t1", repo_path=str(known_good_repo))
        acs = [
            {"text": "AuthService وجود دارد", "verify_method": "static",
             "verify_plan": {"grep_patterns": ["AuthService"]}},
            {"text": "RedisCache وجود دارد", "verify_method": "static",
             "verify_plan": {"grep_patterns": ["RedisCache"]}},  # fail
            {"text": "test pass", "verify_method": "backend_test",
             "verify_plan": {"test_node": "tests/test_smoke.py::test_two_plus_two"}},
            {"text": "manual ac", "verify_method": "manual_only", "verify_plan": {}},
        ]
        results = await run_probes_for_acs(acs, ctx)
        assert len(results) == 4
        assert results[0].status == PROBE_STATUS_PASSED
        assert results[1].status == PROBE_STATUS_FAILED
        assert results[2].status == PROBE_STATUS_PASSED
        assert results[3].status == PROBE_STATUS_SKIPPED

    @pytest.mark.asyncio
    async def test_legacy_str_acs_with_ai_inferred_patterns(self, known_good_repo):
        """AC قدیمی (string) → patterns auto-derived → باید pass شود اگر CamelCase symbol موجود."""
        ctx = build_probe_context(task_id="t1", repo_path=str(known_good_repo))
        acs = ["AuthService واقعی پیاده شده"]  # AuthService در کد هست
        results = await run_probes_for_acs(acs, ctx)
        assert len(results) == 1
        assert results[0].status == PROBE_STATUS_PASSED
        assert results[0].method == "static"


# ---------------------------------------------------------------------------
# Probe summary helper
# ---------------------------------------------------------------------------

class TestSummary:
    @pytest.mark.asyncio
    async def test_results_have_summary_strings(self, known_good_repo):
        ctx = build_probe_context(task_id="t1", repo_path=str(known_good_repo))
        acs = [{"text": "AuthService", "verify_method": "static",
                "verify_plan": {"grep_patterns": ["AuthService"]}}]
        results = await run_probes_for_acs(acs, ctx)
        s = results[0].summary()
        assert "✅" in s
        assert "static" in s
