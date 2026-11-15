"""PM-INS-0006 — inspector chat must not dead-end on one failing model.

- cloud_code: a 400 «Claude Code X does not support this model; version Y or later» upgrades the CLI
  identity once (in-process) instead of failing forever.
- _FallbackAIManager: a failing model call is retried on the next usable model, the working one is
  sticky, and when everything fails the error is a MODEL error (never shown as a GitHub error).
"""
import asyncio

import pytest

from app.services import cloud_code_service as cc
from app.api.routes import render_logs as rl


def test_unsupported_model_error_is_detected():
    msg = '{"type":"invalid_request_error","message":"Claude Code 1.0.110 does not support this model; version 2.0.14 or later is required"}'
    assert cc._is_unsupported_model_error(msg)
    assert not cc._is_unsupported_model_error('{"message":"temperature is deprecated"}')


def test_cli_version_upgrades_only_to_newer(monkeypatch):
    monkeypatch.setattr(cc, "CLOUD_CODE_CLI_VERSION", "1.0.110")
    assert cc._maybe_upgrade_cli_version("does not support this model; version 2.0.14 or later") is True
    assert cc.CLOUD_CODE_CLI_VERSION == "2.0.14"
    assert "claude-cli/2.0.14" in cc._build_headers("t")["User-Agent"]
    # an older or absent version never downgrades
    assert cc._maybe_upgrade_cli_version("version 1.9.0") is False
    assert cc._maybe_upgrade_cli_version("does not support this model") is False
    assert cc.CLOUD_CODE_CLI_VERSION == "2.0.14"


class _Resp:
    def __init__(self, model_id):
        self.model_id = model_id
        self.content = "ok"


class _Inner:
    def __init__(self, failing):
        self.failing = set(failing)
        self.calls = []
        self.other_attr = 42

    async def generate(self, model_id, messages, *a, **kw):
        self.calls.append(model_id)
        if model_id in self.failing:
            raise RuntimeError(f"{model_id} boom")
        return _Resp(model_id)


def test_fallback_manager_moves_to_next_model_and_sticks(monkeypatch):
    monkeypatch.setattr(rl, "_inspector_fallback_chain",
                        lambda db, exclude, limit=4: [m for m in ["gemini-2.5-flash", "deepseek-chat"] if m not in exclude])
    inner = _Inner(failing={"cloud_code"})
    fm = rl._FallbackAIManager(inner, db=None)
    r = asyncio.run(fm.generate("cloud_code", []))
    assert r.model_id == "gemini-2.5-flash"
    notes = fm.drain_notes()
    assert notes and "cloud_code" in notes[0] and "gemini-2.5-flash" in notes[0]
    assert fm.drain_notes() == []
    # sticky: the next call for the same model goes straight to the one that worked
    inner.calls.clear()
    r2 = asyncio.run(fm.generate("cloud_code", []))
    assert r2.model_id == "gemini-2.5-flash" and inner.calls == ["gemini-2.5-flash"]
    # other attributes pass through
    assert fm.other_attr == 42


def test_fallback_manager_all_fail_is_a_model_error(monkeypatch):
    monkeypatch.setattr(rl, "_inspector_fallback_chain",
                        lambda db, exclude, limit=4: [m for m in ["gemini-2.5-flash"] if m not in exclude])
    fm = rl._FallbackAIManager(_Inner(failing={"cloud_code", "gemini-2.5-flash"}), db=None)
    with pytest.raises(rl.InspectorModelError):
        asyncio.run(fm.generate("cloud_code", []))


def test_smart_select_prefers_api_models_over_oauth():
    import inspect
    src = inspect.getsource(rl._smart_select_model)
    assert "for allow_oauth in (False, True)" in src
