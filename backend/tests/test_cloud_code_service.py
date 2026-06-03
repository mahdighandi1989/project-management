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
    # Authorization & beta header propagated.
    assert captured["headers"]["authorization"] == "Bearer sk-ant-oat01-test"
    assert captured["headers"]["anthropic-beta"] == CLOUD_CODE_OAUTH_BETA
    # System prompt + stream + messages present.
    assert captured["body"]["system"] == "you are helpful"
    assert captured["body"]["stream"] is True
    assert captured["body"]["messages"] == [{"role": "user", "content": "hi"}]


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
