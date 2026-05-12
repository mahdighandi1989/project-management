"""Stage 3e — runner orchestrator tests."""

import tempfile
from pathlib import Path

import pytest

from app.services.verify_runtime.base import (
    PROBE_STATUS_PASSED,
    PROBE_STATUS_FAILED,
    PROBE_STATUS_SKIPPED,
    PROBE_STATUS_ERROR,
    ProbeContext,
)
from app.services.verify_runtime.runner import (
    _ac_id_for,
    build_probe_context,
    run_probes_for_acs,
)


class TestAcIdFor:
    def test_stable_for_same_text(self):
        ac = {"text": "hello"}
        a = _ac_id_for(ac, 0)
        b = _ac_id_for(ac, 0)
        assert a == b
        assert a.startswith("ac00_")

    def test_different_for_different_index(self):
        ac = {"text": "hello"}
        a = _ac_id_for(ac, 0)
        b = _ac_id_for(ac, 1)
        assert a != b


class TestBuildProbeContext:
    def test_run_id_generated_when_missing(self):
        ctx = build_probe_context(task_id="t1")
        assert ctx.task_id == "t1"
        assert ctx.run_id.startswith("run_")

    def test_explicit_run_id_kept(self):
        ctx = build_probe_context(task_id="t1", run_id="custom_run")
        assert ctx.run_id == "custom_run"


class TestRunProbesForAcs:
    @pytest.fixture
    def repo(self):
        with tempfile.TemporaryDirectory() as td:
            (Path(td) / "x.py").write_text("def UniqueSymbol(): pass\n")
            yield td

    @pytest.mark.asyncio
    async def test_empty_acs_returns_empty(self):
        ctx = build_probe_context(task_id="t1")
        r = await run_probes_for_acs([], ctx)
        assert r == []

    @pytest.mark.asyncio
    async def test_static_passes(self, repo):
        ctx = build_probe_context(task_id="t1", repo_path=repo)
        acs = [{"text": "UniqueSymbol exists", "verify_method": "static",
                "verify_plan": {"grep_patterns": ["UniqueSymbol"]}}]
        results = await run_probes_for_acs(acs, ctx)
        assert len(results) == 1
        assert results[0].status == PROBE_STATUS_PASSED

    @pytest.mark.asyncio
    async def test_mixed_methods(self, repo):
        """static + manual_only + api_response (no base_url → skip)"""
        ctx = build_probe_context(task_id="t1", repo_path=repo)
        acs = [
            {"text": "static one", "verify_method": "static",
             "verify_plan": {"grep_patterns": ["UniqueSymbol"]}},
            {"text": "manual", "verify_method": "manual_only", "verify_plan": {}},
            {"text": "api one", "verify_method": "api_response",
             "verify_plan": {"path": "/x"}},
        ]
        results = await run_probes_for_acs(acs, ctx)
        assert len(results) == 3
        assert results[0].status == PROBE_STATUS_PASSED
        assert results[1].status == PROBE_STATUS_SKIPPED
        assert results[2].status == PROBE_STATUS_SKIPPED  # no base_url

    @pytest.mark.asyncio
    async def test_unknown_method_returns_error(self, repo):
        ctx = build_probe_context(task_id="t1", repo_path=repo)
        acs = [{"text": "x", "verify_method": "static",
                "verify_plan": {"grep_patterns": ["x"]}}]
        # حتی اگر method صریح "bogus" بدهیم، normalize آن را به static برمی‌گرداند
        # برای تست واقعی method ناشناخته باید normalize را دور بزنیم.
        from app.services.verify_runtime.base import ProbeContext
        from app.services.verify_runtime.runner import _run_single_probe
        import asyncio
        bogus_ac = {"text": "x", "verify_method": "totally_bogus", "verify_plan": {}}
        semaphore = asyncio.Semaphore(1)
        r = await _run_single_probe(bogus_ac, ctx, "ac0", semaphore)
        assert r.status == PROBE_STATUS_ERROR

    @pytest.mark.asyncio
    async def test_legacy_str_acs_normalized(self, repo):
        ctx = build_probe_context(task_id="t1", repo_path=repo)
        acs = ["UniqueSymbol وجود دارد"]
        results = await run_probes_for_acs(acs, ctx)
        assert len(results) == 1
        # auto-derived pattern از کلمه UniqueSymbol → باید pass شود
        assert results[0].status == PROBE_STATUS_PASSED
