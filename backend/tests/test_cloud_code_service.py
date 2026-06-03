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
