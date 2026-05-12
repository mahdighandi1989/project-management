"""Stage 9 — safety/flags/circuit breaker tests."""

import pytest

from app.services.verify_runtime.safety import (
    CircuitBreaker,
    is_runtime_enabled,
    is_ui_probe_enabled,
    _CIRCUIT_ERROR_THRESHOLD,
)
from app.services.verify_runtime.runner import run_probes_for_acs, build_probe_context
from app.services.verify_runtime.base import (
    PROBE_STATUS_SKIPPED,
    PROBE_STATUS_PASSED,
    PROBE_STATUS_FAILED,
    PROBE_STATUS_ERROR,
)


# ---------------------------------------------------------------------------
# Env flags
# ---------------------------------------------------------------------------

class TestEnvFlags:
    def test_runtime_enabled_default_true(self, monkeypatch):
        monkeypatch.delenv("RUNTIME_VERIFY_ENABLED", raising=False)
        assert is_runtime_enabled() is True

    def test_runtime_enabled_false(self, monkeypatch):
        monkeypatch.setenv("RUNTIME_VERIFY_ENABLED", "false")
        assert is_runtime_enabled() is False

    def test_runtime_enabled_FALSE_case_insensitive(self, monkeypatch):
        monkeypatch.setenv("RUNTIME_VERIFY_ENABLED", "False")
        assert is_runtime_enabled() is False

    def test_ui_disabled_when_runtime_disabled(self, monkeypatch):
        monkeypatch.setenv("RUNTIME_VERIFY_ENABLED", "false")
        monkeypatch.delenv("RUNTIME_VERIFY_UI_ENABLED", raising=False)
        assert is_ui_probe_enabled() is False

    def test_ui_can_be_disabled_alone(self, monkeypatch):
        monkeypatch.setenv("RUNTIME_VERIFY_ENABLED", "true")
        monkeypatch.setenv("RUNTIME_VERIFY_UI_ENABLED", "false")
        assert is_runtime_enabled() is True
        assert is_ui_probe_enabled() is False


# ---------------------------------------------------------------------------
# Circuit breaker
# ---------------------------------------------------------------------------

class TestCircuitBreaker:
    def test_starts_closed(self):
        b = CircuitBreaker()
        assert b.is_open("static") is False

    def test_opens_after_threshold_errors(self):
        b = CircuitBreaker()
        for _ in range(_CIRCUIT_ERROR_THRESHOLD):
            b.record_result("ui_interaction", "error")
        assert b.is_open("ui_interaction") is True

    def test_below_threshold_stays_closed(self):
        b = CircuitBreaker()
        for _ in range(_CIRCUIT_ERROR_THRESHOLD - 1):
            b.record_result("api_response", "error")
        assert b.is_open("api_response") is False

    def test_passed_resets_counter(self):
        b = CircuitBreaker()
        b.record_result("static", "error")
        b.record_result("static", "error")
        b.record_result("static", "passed")
        b.record_result("static", "error")
        b.record_result("static", "error")
        # 4 errors total but 1 reset → only 2 consecutive → not open
        assert b.is_open("static") is False

    def test_failed_also_resets(self):
        b = CircuitBreaker()
        b.record_result("static", "error")
        b.record_result("static", "error")
        b.record_result("static", "failed")
        assert b.is_open("static") is False

    def test_skipped_neutral(self):
        b = CircuitBreaker()
        for _ in range(_CIRCUIT_ERROR_THRESHOLD - 1):
            b.record_result("static", "error")
        b.record_result("static", "skipped")
        # skipped neither resets nor advances
        b.record_result("static", "error")
        # now we hit threshold
        assert b.is_open("static") is True

    def test_per_method_independent(self):
        b = CircuitBreaker()
        for _ in range(_CIRCUIT_ERROR_THRESHOLD):
            b.record_result("ui_interaction", "error")
        assert b.is_open("ui_interaction") is True
        assert b.is_open("api_response") is False

    def test_snapshot(self):
        b = CircuitBreaker()
        for _ in range(_CIRCUIT_ERROR_THRESHOLD):
            b.record_result("static", "error")
        s = b.snapshot()
        assert "static" in s["open_methods"]
        assert s["open_methods"]["static"] > 0


# ---------------------------------------------------------------------------
# Runner integration
# ---------------------------------------------------------------------------

class TestRunnerSafetyIntegration:
    @pytest.mark.asyncio
    async def test_skip_all_when_disabled(self, monkeypatch):
        monkeypatch.setenv("RUNTIME_VERIFY_ENABLED", "false")
        ctx = build_probe_context(task_id="t1")
        acs = [
            {"text": "a", "verify_method": "static", "verify_plan": {"grep_patterns": ["x"]}},
            {"text": "b", "verify_method": "api_response", "verify_plan": {}},
        ]
        r = await run_probes_for_acs(acs, ctx)
        assert len(r) == 2
        assert all(p.status == PROBE_STATUS_SKIPPED for p in r)
        assert all("RUNTIME_VERIFY_ENABLED=false" in p.evidence.get("reason", "") for p in r)

    @pytest.mark.asyncio
    async def test_skip_ui_when_ui_disabled(self, monkeypatch):
        monkeypatch.setenv("RUNTIME_VERIFY_ENABLED", "true")
        monkeypatch.setenv("RUNTIME_VERIFY_UI_ENABLED", "false")
        ctx = build_probe_context(task_id="t1", frontend_base_url="http://x")
        acs = [{"text": "ui x", "verify_method": "ui_interaction",
                "verify_plan": {"ui_steps": [{"action": "navigate", "url": "/"}]}}]
        r = await run_probes_for_acs(acs, ctx)
        assert r[0].status == PROBE_STATUS_SKIPPED
        assert "RUNTIME_VERIFY_UI_ENABLED" in r[0].evidence.get("reason", "")
