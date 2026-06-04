"""🆕 Cloud Code as a fully usable monitoring model.

User selected cloud_code in the "مدل‌های نظارت (انتخاب چندتایی)" picker
on the oversight page and asked: "if I pick this, will all scan/verify/
monitor work go through Cloud Code, like DeepSeek does today?"

The honest answer was: not yet. The 19 production call sites of
`OversightService._ai_generate` (used by deep_scan, verify, consensus
mode, monitor, etc.) routed through `ai_manager.generate`, which only
knows about API-key-backed providers. cloud_code uses OAuth and isn't
in `ai_manager._services`, so:

  - `_ai_generate(model_id="cloud_code")` would silently fall back to
    `models[0]` (the first available API-key model) — user thinks
    Cloud Code is running but DeepSeek/Gemini is actually answering.
  - `_ai_generate_multi(model_ids=["cloud_code", ...])` would drop
    cloud_code from `targets` because it isn't in `available`, then
    fall back to "first available" — same silent substitution.

That meant the user's monthly OAuth subscription was being wasted
while their metered API keys (DeepSeek, Gemini) were getting charged
for monitoring work — exactly the opposite of what they wanted.

Fix:
  - `_ai_generate` short-circuits to `cloud_code_complete` when
    model_id == "cloud_code"
  - `_ai_generate_multi` accepts "cloud_code" as a valid target when
    the env token is set, then dispatches each call site to the
    correct backend (cloud_code_complete vs ai_manager.generate)

After this, every site that calls `_ai_generate` or `_ai_generate_multi`
works transparently with cloud_code as just another model id.

This file pins:
  - both helpers route cloud_code through cloud_code_complete
  - other model ids still go through ai_manager
  - cc_ok gate respects the env token
  - graceful behavior when ai_manager has no other models but cloud_code is configured
"""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


# ---------------------------------------------------------------------------
# Source-level pins — both helpers handle cloud_code
# ---------------------------------------------------------------------------


def _read(rel: str) -> str:
    return (
        Path(__file__).resolve().parents[1] / rel
    ).read_text(encoding="utf-8")


def test_ai_generate_short_circuits_cloud_code():
    """🚨 The central fix. `_ai_generate` must route to
    `cloud_code_complete` when model_id == "cloud_code", instead of
    silently falling back to the first available ai_manager model."""
    src = _read("app/services/oversight_service.py")
    idx = src.find("async def _ai_generate(")
    assert idx != -1
    rest = src[idx + 1:]
    # next async def
    nxt = rest.find("\n    async def ")
    body = rest if nxt == -1 else rest[:nxt]
    assert 'model_id == "cloud_code"' in body, (
        "_ai_generate must check model_id == 'cloud_code' to short-circuit"
    )
    assert "cloud_code_complete" in body, (
        "_ai_generate must call cloud_code_complete on the short-circuit"
    )
    # The legacy ai_manager path must remain for other model ids.
    assert "manager.generate" in body, (
        "legacy ai_manager path must remain for non-cloud_code models"
    )


def test_ai_generate_multi_handles_cloud_code_target():
    """`_ai_generate_multi` is the consensus-mode entry point. It must
    accept "cloud_code" as a valid target (not silently drop it) and
    dispatch the per-target call to the right backend."""
    src = _read("app/services/oversight_service.py")
    idx = src.find("async def _ai_generate_multi(")
    assert idx != -1
    rest = src[idx + 1:]
    nxt = rest.find("\n    @staticmethod")
    if nxt == -1:
        nxt = rest.find("\n    async def ")
    if nxt == -1:
        nxt = rest.find("\n    def ")
    body = rest if nxt == -1 else rest[:nxt]
    assert 'mid == "cloud_code"' in body, (
        "_ai_generate_multi must accept cloud_code as a valid target"
    )
    assert "cloud_code_complete" in body, (
        "_ai_generate_multi must dispatch cloud_code targets to "
        "cloud_code_complete (not ai_manager.generate)"
    )


def test_ai_generate_multi_accepts_cloud_code_when_no_other_models():
    """Edge case the source must handle: if ai_manager has zero
    available models but cloud_code is configured, we should still
    work instead of raising 'هیچ مدل AI فعالی نیست'."""
    src = _read("app/services/oversight_service.py")
    idx = src.find("async def _ai_generate_multi(")
    rest = src[idx + 1:]
    nxt = rest.find("\n    @staticmethod")
    if nxt == -1:
        nxt = rest.find("\n    async def ")
    body = rest if nxt == -1 else rest[:nxt]
    # The "no models" check must factor cloud_code availability
    assert "if not available and not cc_ok" in body, (
        "the no-models check must factor in cloud_code availability"
    )


# ---------------------------------------------------------------------------
# Behavioral tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_ai_generate_calls_cloud_code_complete_for_cloud_code_model(
    monkeypatch,
):
    """When model_id='cloud_code', the helper must call cloud_code_complete
    with the user prompt and NOT call ai_manager.generate."""
    from app.services.oversight_service import OversightService

    svc = OversightService.__new__(OversightService)

    called_with = {}

    async def _fake_cc_complete(messages, *, model, max_tokens, temperature):
        called_with["messages"] = messages
        called_with["model"] = model
        called_with["max_tokens"] = max_tokens
        return "RESPONSE FROM CLOUD CODE"

    monkeypatch.setattr(
        "app.services.cloud_code_service.cloud_code_complete",
        _fake_cc_complete,
    )
    monkeypatch.setattr(
        "app.services.cloud_code_service.cloud_code_is_configured",
        lambda: True,
    )

    # If the legacy path were taken, ai_manager would be invoked — set
    # a sentinel that explodes if it gets called.
    def _explode():
        raise AssertionError(
            "ai_manager.get_ai_manager() called for cloud_code — fix failed"
        )
    monkeypatch.setattr("app.services.ai_manager.get_ai_manager", _explode)

    result = await svc._ai_generate(
        prompt="test prompt",
        model_id="cloud_code",
        max_tokens=500,
        temperature=0.5,
    )
    assert result == "RESPONSE FROM CLOUD CODE"
    assert called_with["messages"] == [
        {"role": "user", "content": "test prompt"}
    ]
    assert called_with["model"] == "auto"
    assert called_with["max_tokens"] == 500


@pytest.mark.asyncio
async def test_ai_generate_raises_when_cloud_code_token_missing(monkeypatch):
    """Without the OAuth token, the helper must raise a clear Persian
    error — not silently fall through to ai_manager."""
    from app.services.oversight_service import OversightService

    svc = OversightService.__new__(OversightService)

    monkeypatch.setattr(
        "app.services.cloud_code_service.cloud_code_is_configured",
        lambda: False,
    )

    with pytest.raises(RuntimeError, match="CLAUDE_CODE_OAUTH_TOKEN"):
        await svc._ai_generate(prompt="x", model_id="cloud_code")
