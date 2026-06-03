"""Tests for the Cloud Code (Claude OAuth) inspector chat engine.

These tests cover:
- env-based availability detection
- header construction with the OAuth Bearer token + required beta header
- message coercion (role filtering, leading-non-user trim)
- end-to-end stream parsing (mocked HTTP server) — yields plain text chunks
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


# ---------------------------------------------------------------------------
# import target after path setup
# ---------------------------------------------------------------------------

from app.services.cloud_code_service import (  # noqa: E402
    CLOUD_CODE_API_URL,
    CLOUD_CODE_OAUTH_BETA,
    _build_headers,
    _coerce_messages,
    cloud_code_is_configured,
    cloud_code_stream_chat,
    get_cloud_code_token,
)


# ---------------------------------------------------------------------------
# Availability
# ---------------------------------------------------------------------------


def test_cloud_code_is_configured_returns_false_without_env(monkeypatch):
    monkeypatch.delenv("CLAUDE_CODE_OAUTH_TOKEN", raising=False)
    assert cloud_code_is_configured() is False
    assert get_cloud_code_token() is None


def test_cloud_code_is_configured_returns_true_with_env(monkeypatch):
    monkeypatch.setenv("CLAUDE_CODE_OAUTH_TOKEN", "sk-ant-oat01-xyz")
    assert cloud_code_is_configured() is True
    assert get_cloud_code_token() == "sk-ant-oat01-xyz"


def test_cloud_code_token_strips_whitespace(monkeypatch):
    monkeypatch.setenv("CLAUDE_CODE_OAUTH_TOKEN", "  sk-ant-oat01-abc  \n")
    assert get_cloud_code_token() == "sk-ant-oat01-abc"


def test_cloud_code_token_empty_is_unset(monkeypatch):
    monkeypatch.setenv("CLAUDE_CODE_OAUTH_TOKEN", "   ")
    assert cloud_code_is_configured() is False
    assert get_cloud_code_token() is None


# ---------------------------------------------------------------------------
# Headers
# ---------------------------------------------------------------------------


def test_build_headers_uses_bearer_and_oauth_beta():
    headers = _build_headers("sk-ant-oat01-secret")
    assert headers["Authorization"] == "Bearer sk-ant-oat01-secret"
    assert headers["anthropic-beta"] == CLOUD_CODE_OAUTH_BETA
    # Must NOT send x-api-key — OAuth and api key are mutually exclusive auth.
    assert "x-api-key" not in headers
    assert headers["anthropic-version"]
    assert headers["Content-Type"] == "application/json"


# ---------------------------------------------------------------------------
# Message coercion
# ---------------------------------------------------------------------------


def test_coerce_messages_drops_system_role():
    msgs = [
        {"role": "system", "content": "ignored"},
        {"role": "user", "content": "hi"},
    ]
    out = _coerce_messages(msgs)
    assert out == [{"role": "user", "content": "hi"}]


def test_coerce_messages_drops_empty_content():
    msgs = [
        {"role": "user", "content": ""},
        {"role": "user", "content": "   "},
        {"role": "user", "content": "hello"},
    ]
    assert _coerce_messages(msgs) == [{"role": "user", "content": "hello"}]


def test_coerce_messages_trims_leading_assistant():
    msgs = [
        {"role": "assistant", "content": "leftover"},
        {"role": "user", "content": "hi"},
        {"role": "assistant", "content": "hello"},
    ]
    out = _coerce_messages(msgs)
    assert out[0]["role"] == "user"
    assert len(out) == 2


def test_coerce_messages_unknown_roles_filtered():
    msgs = [
        {"role": "tool", "content": "x"},
        {"role": "user", "content": "ok"},
    ]
    assert _coerce_messages(msgs) == [{"role": "user", "content": "ok"}]


# ---------------------------------------------------------------------------
# Claude Code identity injection (anti-abuse requirement)
# ---------------------------------------------------------------------------


def test_build_system_blocks_always_starts_with_claude_code_identity():
    from app.services.cloud_code_service import _build_system_blocks

    # هیچ system prompt کاربر داده نشده → فقط identity block
    blocks = _build_system_blocks(None)
    assert len(blocks) == 1
    assert "Claude Code" in blocks[0]["text"]

    # system prompt خالی → باز هم فقط identity
    blocks = _build_system_blocks("   ")
    assert len(blocks) == 1

    # system prompt واقعی → identity سپس prompt کاربر
    blocks = _build_system_blocks("be helpful")
    assert len(blocks) == 2
    assert "Claude Code" in blocks[0]["text"]
    assert blocks[1]["text"] == "be helpful"


def test_build_headers_includes_cli_impersonation():
    """Anthropic OAuth tokens 429 می‌دهند اگر User-Agent و X-App ست نشود
    — این تست regression-guard است."""
    headers = _build_headers("sk-ant-oat01-test")
    assert headers["User-Agent"].startswith("claude-cli/")
    assert headers["X-App"] == "cli"
    # هر دو beta flag (oauth + claude-code) باید حضور داشته باشند
    assert "oauth-2025-04-20" in headers["anthropic-beta"]
    assert "claude-code-20250219" in headers["anthropic-beta"]


# ---------------------------------------------------------------------------
# Streaming end-to-end (mocked transport)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_stream_chat_raises_without_token(monkeypatch):
    monkeypatch.delenv("CLAUDE_CODE_OAUTH_TOKEN", raising=False)
    with pytest.raises(RuntimeError, match="CLAUDE_CODE_OAUTH_TOKEN"):
        async for _ in cloud_code_stream_chat(
            [{"role": "user", "content": "hi"}],
        ):
            break


def _make_sse_body(chunks):
    lines = []
    for c in chunks:
        payload = {
            "type": "content_block_delta",
            "delta": {"type": "text_delta", "text": c},
        }
        lines.append(f"data: {json.dumps(payload)}")
        lines.append("")
    lines.append("data: [DONE]")
    lines.append("")
    return ("\n".join(lines) + "\n").encode("utf-8")


@pytest.mark.asyncio
async def test_stream_chat_yields_text_chunks(monkeypatch):
    monkeypatch.setenv("CLAUDE_CODE_OAUTH_TOKEN", "sk-ant-oat01-test")

    captured = {}

    def _handler(request: httpx.Request) -> httpx.Response:
        captured["headers"] = dict(request.headers)
        captured["body"] = json.loads(request.content.decode("utf-8"))
        assert request.url == httpx.URL(CLOUD_CODE_API_URL)
        return httpx.Response(
            200,
            content=_make_sse_body(["سل", "ام ", "دنیا"]),
            headers={"content-type": "text/event-stream"},
        )

    transport = httpx.MockTransport(_handler)

    # Patch httpx.AsyncClient to use our MockTransport.
    real_client_cls = httpx.AsyncClient

    def _patched_client(*args, **kwargs):
        kwargs["transport"] = transport
        return real_client_cls(*args, **kwargs)

    monkeypatch.setattr("app.services.cloud_code_service.httpx.AsyncClient", _patched_client)

    pieces = []
    async for c in cloud_code_stream_chat(
        [{"role": "user", "content": "hi"}],
        system_prompt="you are helpful",
    ):
        pieces.append(c)

    assert "".join(pieces) == "سلام دنیا"
    # Authorization, beta and CLI-impersonation headers propagated.
    assert captured["headers"]["authorization"] == "Bearer sk-ant-oat01-test"
    assert captured["headers"]["anthropic-beta"] == CLOUD_CODE_OAUTH_BETA
    assert captured["headers"]["user-agent"].startswith("claude-cli/")
    assert captured["headers"]["x-app"] == "cli"
    # System prompt is wrapped in blocks; first block must be the Claude Code
    # identity (anti-abuse requirement), second block is user's prompt.
    system_blocks = captured["body"]["system"]
    assert isinstance(system_blocks, list)
    assert system_blocks[0]["type"] == "text"
    assert "Claude Code" in system_blocks[0]["text"]
    assert system_blocks[1]["text"] == "you are helpful"
    assert captured["body"]["stream"] is True
    assert captured["body"]["messages"] == [{"role": "user", "content": "hi"}]


@pytest.mark.asyncio
async def test_stream_chat_captures_actual_model_in_metadata(monkeypatch):
    """message_start.message.model را در metadata_sink بریزد تا UI بتواند
    مدل واقعی Anthropic (نه self-id آن) را نشان دهد."""
    monkeypatch.setenv("CLAUDE_CODE_OAUTH_TOKEN", "sk-ant-oat01-test")

    def _handler(request: httpx.Request) -> httpx.Response:
        body_parts = [
            'data: ' + json.dumps({
                "type": "message_start",
                "message": {
                    "id": "msg_abc",
                    "model": "claude-sonnet-4-5-20250929",
                    "usage": {"input_tokens": 12},
                },
            }),
            "",
            'data: ' + json.dumps({
                "type": "content_block_delta",
                "delta": {"type": "text_delta", "text": "hi"},
            }),
            "",
            'data: ' + json.dumps({
                "type": "message_delta",
                "delta": {"stop_reason": "end_turn"},
                "usage": {"output_tokens": 3},
            }),
            "",
            "data: [DONE]",
            "",
        ]
        return httpx.Response(
            200,
            content=("\n".join(body_parts) + "\n").encode("utf-8"),
            headers={"content-type": "text/event-stream"},
        )

    transport = httpx.MockTransport(_handler)
    real_client_cls = httpx.AsyncClient

    def _patched_client(*args, **kwargs):
        kwargs["transport"] = transport
        return real_client_cls(*args, **kwargs)

    monkeypatch.setattr("app.services.cloud_code_service.httpx.AsyncClient", _patched_client)

    sink: dict = {}
    pieces = []
    async for c in cloud_code_stream_chat(
        [{"role": "user", "content": "hi"}],
        metadata_sink=sink,
    ):
        pieces.append(c)

    assert "".join(pieces) == "hi"
    assert sink["actual_model"] == "claude-sonnet-4-5-20250929"
    assert sink["message_id"] == "msg_abc"
    assert sink["usage"]["output_tokens"] == 3
    assert sink["stop_reason"] == "end_turn"


@pytest.mark.asyncio
async def test_stream_chat_raises_on_http_error(monkeypatch):
    monkeypatch.setenv("CLAUDE_CODE_OAUTH_TOKEN", "sk-ant-oat01-test")

    def _handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, content=b'{"error":"unauthorized"}')

    transport = httpx.MockTransport(_handler)
    real_client_cls = httpx.AsyncClient

    def _patched_client(*args, **kwargs):
        kwargs["transport"] = transport
        return real_client_cls(*args, **kwargs)

    monkeypatch.setattr("app.services.cloud_code_service.httpx.AsyncClient", _patched_client)

    with pytest.raises(RuntimeError, match="401"):
        async for _ in cloud_code_stream_chat(
            [{"role": "user", "content": "hi"}],
        ):
            pass


# ---------------------------------------------------------------------------
# InspectorAgentService façade
# ---------------------------------------------------------------------------


def test_inspector_agent_service_availability_reflects_env(monkeypatch):
    from app.services.inspector_agent_service import InspectorAgentService

    monkeypatch.delenv("CLAUDE_CODE_OAUTH_TOKEN", raising=False)
    assert InspectorAgentService.cloud_code_available() is False

    monkeypatch.setenv("CLAUDE_CODE_OAUTH_TOKEN", "sk-ant-oat01-test")
    assert InspectorAgentService.cloud_code_available() is True


@pytest.mark.asyncio
async def test_inspector_agent_service_chat_streams(monkeypatch):
    from app.services.inspector_agent_service import InspectorAgentService

    monkeypatch.setenv("CLAUDE_CODE_OAUTH_TOKEN", "sk-ant-oat01-test")

    def _handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            content=_make_sse_body(["یک ", "دو ", "سه"]),
            headers={"content-type": "text/event-stream"},
        )

    transport = httpx.MockTransport(_handler)
    real_client_cls = httpx.AsyncClient

    def _patched_client(*args, **kwargs):
        kwargs["transport"] = transport
        return real_client_cls(*args, **kwargs)

    monkeypatch.setattr("app.services.cloud_code_service.httpx.AsyncClient", _patched_client)

    stream_gen = await InspectorAgentService.chat_with_cloud_code(
        [{"role": "user", "content": "hi"}],
        system_prompt="be terse",
        stream=True,
    )
    pieces = [p async for p in stream_gen]
    assert "".join(pieces) == "یک دو سه"


@pytest.mark.asyncio
async def test_inspector_agent_service_chat_non_stream(monkeypatch):
    from app.services.inspector_agent_service import InspectorAgentService

    monkeypatch.setenv("CLAUDE_CODE_OAUTH_TOKEN", "sk-ant-oat01-test")

    def _handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            content=_make_sse_body(["پاسخ ", "کامل"]),
            headers={"content-type": "text/event-stream"},
        )

    transport = httpx.MockTransport(_handler)
    real_client_cls = httpx.AsyncClient

    def _patched_client(*args, **kwargs):
        kwargs["transport"] = transport
        return real_client_cls(*args, **kwargs)

    monkeypatch.setattr("app.services.cloud_code_service.httpx.AsyncClient", _patched_client)

    text = await InspectorAgentService.chat_with_cloud_code(
        [{"role": "user", "content": "hi"}],
        stream=False,
    )
    assert text == "پاسخ کامل"


# ---------------------------------------------------------------------------
# Dynamic model discovery + intelligent picker
# ---------------------------------------------------------------------------


def test_classify_tier_default_sonnet():
    from app.services.cloud_code_service import _classify_tier

    tier, reason = _classify_tier([{"role": "user", "content": "این کد را برام بنویس"}])
    assert tier == "sonnet"
    assert "sonnet" in reason
    tier, _ = _classify_tier([])
    assert tier == "sonnet"


def test_classify_tier_heavy_keywords_route_to_opus():
    from app.services.cloud_code_service import _classify_tier

    for txt in [
        "refactor کل پروژه را",
        "architecture این سیستم را بازنگری کن",
        "audit کن همه ماژول‌ها را",
        "investigate the failing test suite end-to-end",
        "معماری پروژه را بازطراحی کن",
        "optimize performance of the scheduler",
        "security audit on the auth flow",
        "race condition در worker queue",
        "بهینه‌سازی کلی پروژه",
        "تحلیل عمیق این سیستم",
    ]:
        tier, reason = _classify_tier([{"role": "user", "content": txt}])
        assert tier == "opus", f"{txt!r} → {tier} (reason: {reason})"
        assert reason  # human-readable reason populated


def test_classify_tier_very_long_routes_to_opus():
    from app.services.cloud_code_service import _classify_tier

    long_msg = "x" * 4000
    tier, reason = _classify_tier([{"role": "user", "content": long_msg}])
    assert tier == "opus"
    assert "long message" in reason


def test_classify_tier_deep_ongoing_convo_routes_to_opus():
    from app.services.cloud_code_service import _classify_tier

    # 6 turns, lots of code context → opus
    messages = []
    for i in range(6):
        messages.append({"role": "user", "content": "fix the error in def foo(): " + ("x" * 1500)})
        messages.append({"role": "assistant", "content": "ok"})
    tier, reason = _classify_tier(messages)
    assert tier == "opus"
    assert "ongoing" in reason or "deep" in reason


def test_classify_tier_greeting_routes_to_haiku():
    from app.services.cloud_code_service import _classify_tier

    for txt in ["سلام", "hi", "ممنون", "yes", "ok", "thanks", "خداحافظ", "مرسی"]:
        tier, reason = _classify_tier([{"role": "user", "content": txt}])
        assert tier == "haiku", f"{txt!r} → {tier} (reason: {reason})"


def test_classify_tier_short_factual_question_routes_to_haiku():
    from app.services.cloud_code_service import _classify_tier

    # short question, no code keywords → haiku (saves Sonnet/Opus for real work)
    tier, _ = _classify_tier([{"role": "user", "content": "نسخهٔ پایتون پروژه چنده؟"}])
    assert tier == "haiku"
    tier, _ = _classify_tier([{"role": "user", "content": "آخرین commit کی بود"}])
    assert tier == "haiku"


def test_classify_tier_code_keyword_stays_sonnet_not_haiku():
    """short message ولی شامل کد → نباید به haiku افت کند."""
    from app.services.cloud_code_service import _classify_tier

    tier, _ = _classify_tier([{"role": "user", "content": "fix this bug"}])
    assert tier == "sonnet"
    tier, _ = _classify_tier([{"role": "user", "content": "این error را درست کن"}])
    assert tier == "sonnet"
    tier, _ = _classify_tier([{"role": "user", "content": "endpoint /foo اضافه کن"}])
    assert tier == "sonnet"


def test_classify_tier_distributes_across_all_three_tiers():
    """مهم‌ترین تست — اطمینان از اینکه هر سه tier در زمان مناسب انتخاب می‌شوند."""
    from app.services.cloud_code_service import _classify_tier

    cases = [
        ("سلام", "haiku"),
        ("نسخه فعلی چیه", "haiku"),
        ("fix the login bug", "sonnet"),
        ("این component رو refactor کن سراسری", "opus"),
        ("performance رو بهینه کن", "opus"),
    ]
    seen = {tier for _, tier in cases}
    assert seen == {"haiku", "sonnet", "opus"}
    for msg, expected in cases:
        tier, _ = _classify_tier([{"role": "user", "content": msg}])
        assert tier == expected, f"{msg!r} → {tier}, expected {expected}"


def test_infer_tier_from_model_id():
    from app.services.cloud_code_service import _infer_tier_from_model_id

    assert _infer_tier_from_model_id("claude-opus-4-5-20251101") == "opus"
    assert _infer_tier_from_model_id("claude-sonnet-4-5-20250929") == "sonnet"
    assert _infer_tier_from_model_id("claude-haiku-4-5-20251001") == "haiku"
    assert _infer_tier_from_model_id("unknown-model") is None


def test_model_sort_key_prefers_newer_date():
    from app.services.cloud_code_service import _model_sort_key

    older = {"id": "claude-sonnet-4-5-20250929", "created_at": "2025-09-29"}
    newer = {"id": "claude-sonnet-4-6-20251115", "created_at": "2025-11-15"}
    sorted_ids = sorted([older, newer], key=_model_sort_key, reverse=True)
    assert sorted_ids[0]["id"] == "claude-sonnet-4-6-20251115"


@pytest.mark.asyncio
async def test_pick_best_model_uses_tier_hint(monkeypatch):
    """tier_hint should override message-based classification."""
    from app.services import cloud_code_service as ccs

    monkeypatch.setenv("CLAUDE_CODE_OAUTH_TOKEN", "sk-ant-oat01-test")

    async def fake_list(force_refresh=False):
        return [
            {"id": "claude-opus-4-5-20251101", "created_at": "2025-11-01"},
            {"id": "claude-opus-5-0-20260301", "created_at": "2026-03-01"},
            {"id": "claude-sonnet-4-5-20250929", "created_at": "2025-09-29"},
        ]

    monkeypatch.setattr(ccs, "list_available_models", fake_list)

    # tier_hint=opus → باید جدیدترین opus را برگرداند
    model_id, tier, _reason = await ccs.pick_best_model(
        [{"role": "user", "content": "سلام"}],  # خودش haiku می‌داد
        tier_hint="opus",
    )
    assert tier == "opus"
    assert model_id == "claude-opus-5-0-20260301"


@pytest.mark.asyncio
async def test_pick_best_model_auto_routes_heavy_to_opus(monkeypatch):
    from app.services import cloud_code_service as ccs

    monkeypatch.setenv("CLAUDE_CODE_OAUTH_TOKEN", "sk-ant-oat01-test")

    async def fake_list(force_refresh=False):
        return [
            {"id": "claude-opus-4-5-20251101", "created_at": "2025-11-01"},
            {"id": "claude-sonnet-4-5-20250929", "created_at": "2025-09-29"},
        ]

    monkeypatch.setattr(ccs, "list_available_models", fake_list)

    model_id, tier, _reason = await ccs.pick_best_model(
        [{"role": "user", "content": "refactor کل architecture این پروژه"}],
    )
    assert tier == "opus"
    assert model_id == "claude-opus-4-5-20251101"


@pytest.mark.asyncio
async def test_pick_best_model_falls_back_when_discovery_empty(monkeypatch):
    """وقتی /v1/models هیچ مدلی برنگرداند، باید به CLOUD_CODE_TIER_FALLBACKS برگردد."""
    from app.services import cloud_code_service as ccs

    monkeypatch.setenv("CLAUDE_CODE_OAUTH_TOKEN", "sk-ant-oat01-test")

    async def fake_list(force_refresh=False):
        return []

    monkeypatch.setattr(ccs, "list_available_models", fake_list)
    model_id, tier, _reason = await ccs.pick_best_model(
        [{"role": "user", "content": "hello"}],
        tier_hint="sonnet",
    )
    assert tier == "sonnet"
    assert model_id == ccs.CLOUD_CODE_TIER_FALLBACKS["sonnet"]


@pytest.mark.asyncio
async def test_list_available_models_caches(monkeypatch):
    """دومین فراخوانی باید از cache برگردد (بدون HTTP call)."""
    from app.services import cloud_code_service as ccs

    monkeypatch.setenv("CLAUDE_CODE_OAUTH_TOKEN", "sk-ant-oat01-test")
    # cache را پاک کن
    ccs._MODELS_CACHE["at"] = 0.0
    ccs._MODELS_CACHE["list"] = []

    call_count = {"n": 0}

    def _handler(request: httpx.Request) -> httpx.Response:
        call_count["n"] += 1
        return httpx.Response(
            200,
            json={"data": [
                {"id": "claude-sonnet-4-5-20250929", "created_at": "2025-09-29", "display_name": "Sonnet 4.5"},
            ]},
        )

    transport = httpx.MockTransport(_handler)
    real_client_cls = httpx.AsyncClient

    def _patched_client(*args, **kwargs):
        kwargs["transport"] = transport
        return real_client_cls(*args, **kwargs)

    monkeypatch.setattr(ccs.httpx, "AsyncClient", _patched_client)

    first = await ccs.list_available_models()
    second = await ccs.list_available_models()
    assert call_count["n"] == 1  # دومی از cache
    assert first[0]["id"] == "claude-sonnet-4-5-20250929"
    assert second[0]["id"] == "claude-sonnet-4-5-20250929"

    # force_refresh باید دوباره call بزند
    third = await ccs.list_available_models(force_refresh=True)
    assert call_count["n"] == 2
    assert third[0]["id"] == "claude-sonnet-4-5-20250929"


@pytest.mark.asyncio
async def test_stream_chat_auto_picks_model_and_reports_in_sink(monkeypatch):
    """model='auto' باید pick_best_model را صدا بزند و picked_model را در sink بریزد."""
    from app.services import cloud_code_service as ccs

    monkeypatch.setenv("CLAUDE_CODE_OAUTH_TOKEN", "sk-ant-oat01-test")

    captured_payload: dict = {}

    def _handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content.decode("utf-8"))
        captured_payload.update(body)
        return httpx.Response(
            200,
            content=_make_sse_body(["ok"]),
            headers={"content-type": "text/event-stream"},
        )

    transport = httpx.MockTransport(_handler)
    real_client_cls = httpx.AsyncClient

    def _patched_client(*args, **kwargs):
        kwargs["transport"] = transport
        return real_client_cls(*args, **kwargs)

    monkeypatch.setattr(ccs.httpx, "AsyncClient", _patched_client)

    async def fake_pick(messages, tier_hint=None):
        return "claude-opus-4-5-20251101", "opus", "heavy keyword → opus"

    monkeypatch.setattr(ccs, "pick_best_model", fake_pick)

    sink: dict = {}
    pieces = []
    async for c in ccs.cloud_code_stream_chat(
        [{"role": "user", "content": "refactor everything"}],
        model="auto",
        metadata_sink=sink,
    ):
        pieces.append(c)

    assert "".join(pieces) == "ok"
    assert sink["requested_model"] == "auto"
    assert sink["picked_model"] == "claude-opus-4-5-20251101"
    assert sink["picked_tier"] == "opus"
    assert sink["pick_reason"]  # human-readable reason populated
    # درخواست واقعی به Anthropic باید مدل picked را داشته باشد
    assert captured_payload["model"] == "claude-opus-4-5-20251101"


# ---------------------------------------------------------------------------
# Settings integration
# ---------------------------------------------------------------------------


def test_settings_exposes_cloud_code_token_field(monkeypatch):
    """Settings class باید CLAUDE_CODE_OAUTH_TOKEN را به‌عنوان field رسمی داشته باشد
    (نه فقط reads مستقیم از os.environ) — این requirement spec کاربر بود."""
    from app.core.config import Settings

    monkeypatch.setenv("CLAUDE_CODE_OAUTH_TOKEN", "sk-ant-oat01-from-settings")
    fresh = Settings()
    assert fresh.CLAUDE_CODE_OAUTH_TOKEN == "sk-ant-oat01-from-settings"
    # EXTERNAL_TOOL_TOKEN هم باید باشد
    assert hasattr(fresh, "EXTERNAL_TOOL_TOKEN")
