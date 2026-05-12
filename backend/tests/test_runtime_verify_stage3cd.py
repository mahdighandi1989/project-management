"""Stage 3c/d — api_probe + test_probe tests."""

import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.verify_runtime.base import (
    PROBE_STATUS_PASSED,
    PROBE_STATUS_FAILED,
    PROBE_STATUS_SKIPPED,
    PROBE_STATUS_ERROR,
    ProbeContext,
)
from app.services.verify_runtime.api_probe import (
    run_api_probe,
    _check_required_fields,
    _check_json_contains,
    _build_auth_headers,
)
from app.services.verify_runtime.test_probe import run_test_probe


# ---------------------------------------------------------------------------
# API probe — pure helper tests
# ---------------------------------------------------------------------------

class TestRequiredFields:
    def test_all_present(self):
        assert _check_required_fields({"a": 1, "b": 2}, ["a", "b"]) == []

    def test_some_missing(self):
        assert _check_required_fields({"a": 1}, ["a", "b"]) == ["b"]

    def test_dot_path_present(self):
        assert _check_required_fields({"u": {"e": 1}}, ["u.e"]) == []

    def test_dot_path_missing(self):
        assert _check_required_fields({"u": {}}, ["u.e"]) == ["u.e"]

    def test_non_dict_data_returns_all(self):
        assert _check_required_fields([1, 2], ["a"]) == ["a"]

    def test_empty_required_returns_empty(self):
        assert _check_required_fields({"a": 1}, []) == []


class TestJsonContains:
    def test_all_match(self):
        assert _check_json_contains({"a": 1, "b": 2}, {"a": 1}) == []

    def test_value_mismatch(self):
        r = _check_json_contains({"a": 1}, {"a": 2})
        assert len(r) == 1

    def test_missing_key(self):
        r = _check_json_contains({"a": 1}, {"b": 2})
        assert "missing key 'b'" in r[0]


class TestAuthHeaders:
    def test_bearer(self):
        ctx = ProbeContext(task_id="t", run_id="r", auth_type="bearer", auth_value="tok123")
        h = _build_auth_headers(ctx)
        assert h["Authorization"] == "Bearer tok123"

    def test_cookie(self):
        ctx = ProbeContext(task_id="t", run_id="r", auth_type="cookie", auth_value="session=abc")
        h = _build_auth_headers(ctx)
        assert h["Cookie"] == "session=abc"

    def test_no_auth(self):
        ctx = ProbeContext(task_id="t", run_id="r")
        assert _build_auth_headers(ctx) == {}


# ---------------------------------------------------------------------------
# API probe — async, mocked httpx
# ---------------------------------------------------------------------------

class TestApiProbeAsync:
    @pytest.mark.asyncio
    async def test_skipped_when_no_base_url(self):
        ctx = ProbeContext(task_id="t", run_id="r")
        ac = {"text": "X", "verify_method": "api_response",
              "verify_plan": {"path": "/health"}}
        r = await run_api_probe(ac, ctx, "ac1")
        assert r.status == PROBE_STATUS_SKIPPED

    @pytest.mark.asyncio
    async def test_status_match_passes(self, monkeypatch):
        ctx = ProbeContext(task_id="t", run_id="r", backend_base_url="http://x.test")
        ac = {"text": "GET /health", "verify_method": "api_response",
              "verify_plan": {"method": "GET", "path": "/health", "expected_status": 200}}
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = '{"ok": true}'
        mock_resp.json = MagicMock(return_value={"ok": True})
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.request = AsyncMock(return_value=mock_resp)
        with patch("httpx.AsyncClient", return_value=mock_client):
            r = await run_api_probe(ac, ctx, "ac1")
        assert r.status == PROBE_STATUS_PASSED

    @pytest.mark.asyncio
    async def test_status_mismatch_fails(self):
        ctx = ProbeContext(task_id="t", run_id="r", backend_base_url="http://x.test")
        ac = {"text": "X", "verify_method": "api_response",
              "verify_plan": {"path": "/", "expected_status": 200}}
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_resp.text = "error"
        mock_resp.json = MagicMock(side_effect=Exception("not json"))
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.request = AsyncMock(return_value=mock_resp)
        with patch("httpx.AsyncClient", return_value=mock_client):
            r = await run_api_probe(ac, ctx, "ac1")
        assert r.status == PROBE_STATUS_FAILED
        assert r.evidence["actual_status"] == 500

    @pytest.mark.asyncio
    async def test_missing_required_field_fails(self):
        ctx = ProbeContext(task_id="t", run_id="r", backend_base_url="http://x.test")
        ac = {"text": "X", "verify_method": "api_response",
              "verify_plan": {"path": "/u", "expected_status": 200,
                              "required_fields": ["email", "id"]}}
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = '{"id": 1}'
        mock_resp.json = MagicMock(return_value={"id": 1})
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.request = AsyncMock(return_value=mock_resp)
        with patch("httpx.AsyncClient", return_value=mock_client):
            r = await run_api_probe(ac, ctx, "ac1")
        assert r.status == PROBE_STATUS_FAILED
        assert "email" in r.evidence["missing_fields"]

    @pytest.mark.asyncio
    async def test_network_error_returns_error(self):
        ctx = ProbeContext(task_id="t", run_id="r", backend_base_url="http://x.test")
        ac = {"text": "X", "verify_method": "api_response",
              "verify_plan": {"path": "/"}}
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.request = AsyncMock(side_effect=ConnectionError("refused"))
        with patch("httpx.AsyncClient", return_value=mock_client):
            r = await run_api_probe(ac, ctx, "ac1")
        assert r.status == PROBE_STATUS_ERROR


# ---------------------------------------------------------------------------
# Test probe (pytest subprocess)
# ---------------------------------------------------------------------------

class TestTestProbe:
    @pytest.mark.asyncio
    async def test_skipped_without_test_node(self):
        ctx = ProbeContext(task_id="t", run_id="r")
        ac = {"text": "X", "verify_method": "backend_test", "verify_plan": {}}
        r = await run_test_probe(ac, ctx, "ac1")
        assert r.status == PROBE_STATUS_SKIPPED

    @pytest.mark.asyncio
    async def test_passes_for_passing_test(self):
        """یک تست واقعی pytest می‌سازد و آن را اجرا می‌کند."""
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            test_file = tdp / "test_x.py"
            test_file.write_text("def test_ok():\n    assert 1 + 1 == 2\n")
            ctx = ProbeContext(task_id="t", run_id="r", repo_path=td)
            ac = {"text": "test_ok pass شود", "verify_method": "backend_test",
                  "verify_plan": {"test_node": "test_x.py::test_ok", "timeout_seconds": 30}}
            r = await run_test_probe(ac, ctx, "ac1")
        assert r.status == PROBE_STATUS_PASSED, r.evidence

    @pytest.mark.asyncio
    async def test_fails_for_failing_test(self):
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            test_file = tdp / "test_y.py"
            test_file.write_text("def test_bad():\n    assert 1 == 2\n")
            ctx = ProbeContext(task_id="t", run_id="r", repo_path=td)
            ac = {"text": "X", "verify_method": "backend_test",
                  "verify_plan": {"test_node": "test_y.py::test_bad", "timeout_seconds": 30}}
            r = await run_test_probe(ac, ctx, "ac1")
        assert r.status == PROBE_STATUS_FAILED

    @pytest.mark.asyncio
    async def test_error_for_invalid_cwd(self):
        ctx = ProbeContext(task_id="t", run_id="r", repo_path="/nonexistent/xyz123")
        ac = {"text": "X", "verify_method": "backend_test",
              "verify_plan": {"test_node": "test_x.py::test_ok"}}
        r = await run_test_probe(ac, ctx, "ac1")
        assert r.status == PROBE_STATUS_ERROR
