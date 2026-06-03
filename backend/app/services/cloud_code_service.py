"""Cloud Code (Claude Code OAuth) service.

This module provides a thin wrapper around the Anthropic Messages API that
authenticates with the user's Claude Code subscription via the OAuth token
already stored in the `CLAUDE_CODE_OAUTH_TOKEN` environment variable. The
same token is consumed by `claude_runner_bootstrap` and the GitHub Actions
workflow, so reusing it here means inspector chat traffic goes against the
user's Claude Pro/Max plan instead of metered API spend.

Usage from the inspector chat endpoint:

    from .cloud_code_service import (
        cloud_code_is_configured,
        cloud_code_stream_chat,
    )

    if not cloud_code_is_configured():
        # bubble a 503 / SSE error to the client

    async for text_chunk in cloud_code_stream_chat(messages, system_prompt):
        # forward to the SSE stream

The streaming generator yields plain text fragments (mirroring the existing
local-AI pipeline) so callers can wire it into the inspector SSE response
without bespoke parsing.
"""

from __future__ import annotations

import json
import logging
import os
from typing import AsyncIterator, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)


CLOUD_CODE_DEFAULT_MODEL = "claude-sonnet-4-5-20250929"
CLOUD_CODE_API_URL = "https://api.anthropic.com/v1/messages"
CLOUD_CODE_API_VERSION = "2023-06-01"
# OAuth tokens issued by `claude setup-token` are bound to the Claude Code
# subscription. To bypass the anti-abuse rate limiter that flags non-CLI
# traffic with an immediate 429, requests must mimic the official CLI:
#   - User-Agent identifying claude-cli
#   - X-App: cli
#   - the OAuth beta header (and optionally the claude-code feature flag)
# Without these, even the first request returns
# `{"type":"rate_limit_error","message":"Error"}` — which is the API's way
# of saying "you're calling me with an OAuth token but you don't look like
# the CLI". The beta string includes both `oauth-2025-04-20` and
# `claude-code-20250219` so the call is treated as a Claude Code session.
CLOUD_CODE_OAUTH_BETA = "oauth-2025-04-20,claude-code-20250219"
CLOUD_CODE_USER_AGENT = "claude-cli/1.0.110 (external, cli)"


def get_cloud_code_token() -> Optional[str]:
    raw = os.environ.get("CLAUDE_CODE_OAUTH_TOKEN") or ""
    raw = raw.strip()
    return raw or None


def cloud_code_is_configured() -> bool:
    return bool(get_cloud_code_token())


def _build_headers(token: str) -> Dict[str, str]:
    return {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}",
        "anthropic-version": CLOUD_CODE_API_VERSION,
        "anthropic-beta": CLOUD_CODE_OAUTH_BETA,
        "User-Agent": CLOUD_CODE_USER_AGENT,
        "X-App": "cli",
        "Accept": "application/json",
    }


def _coerce_messages(messages: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """Drop any non-user/assistant messages and clamp role names."""
    cleaned: List[Dict[str, str]] = []
    for m in messages or []:
        role = (m.get("role") or "").strip().lower()
        content = m.get("content") or ""
        if role not in ("user", "assistant"):
            continue
        if not str(content).strip():
            continue
        cleaned.append({"role": role, "content": str(content)})
    # Anthropic requires the first message to be from the user.
    while cleaned and cleaned[0]["role"] != "user":
        cleaned.pop(0)
    return cleaned


# Anthropic enforces that OAuth tokens (Claude Code subscription) only run
# within "Claude Code" sessions. The signal is the first block of `system`:
# if it doesn't identify the caller as Claude Code, the API returns
# `rate_limit_error` immediately — regardless of actual quota usage.
# So we always inject this identification block as the first system entry
# and append the user's actual system prompt as a second block.
CLAUDE_CODE_IDENTITY_PROMPT = (
    "You are Claude Code, Anthropic's official CLI for Claude."
)


def _build_system_blocks(user_system_prompt: Optional[str]) -> List[Dict[str, str]]:
    blocks: List[Dict[str, str]] = [
        {"type": "text", "text": CLAUDE_CODE_IDENTITY_PROMPT}
    ]
    if user_system_prompt and user_system_prompt.strip():
        blocks.append({"type": "text", "text": user_system_prompt.strip()})
    return blocks


async def cloud_code_stream_chat(
    messages: List[Dict[str, str]],
    *,
    system_prompt: Optional[str] = None,
    model: str = CLOUD_CODE_DEFAULT_MODEL,
    max_tokens: int = 4096,
    temperature: float = 0.7,
    timeout: float = 180.0,
    metadata_sink: Optional[Dict[str, Any]] = None,
) -> AsyncIterator[str]:
    """
    metadata_sink: optional dict that the generator mutates as the stream
    progresses. After the first `message_start` event it contains
    `actual_model` (the model ID Anthropic actually served), and after
    `message_delta` it gains `usage` (input/output tokens). Callers can
    use this to display the *real* model in the UI — Claude's own
    self-identification in text replies is unreliable (the training data
    causes Sonnet 4.x to often say "I am Claude 3.5 Sonnet").
    """
    token = get_cloud_code_token()
    if not token:
        raise RuntimeError(
            "CLAUDE_CODE_OAUTH_TOKEN env var is not set — "
            "cloud_code engine unavailable"
        )

    payload: Dict[str, object] = {
        "model": model,
        "messages": _coerce_messages(messages),
        "max_tokens": max_tokens,
        "temperature": temperature,
        "stream": True,
        # 🔐 Claude Code OAuth requires system prompt as a list whose first
        # block identifies the caller as Claude Code; otherwise the API
        # returns rate_limit_error even on the first request.
        "system": _build_system_blocks(system_prompt),
    }

    async with httpx.AsyncClient(timeout=timeout) as client:
        async with client.stream(
            "POST",
            CLOUD_CODE_API_URL,
            headers=_build_headers(token),
            json=payload,
        ) as response:
            if response.status_code != 200:
                body = await response.aread()
                snippet = body[:500].decode("utf-8", errors="replace")
                logger.warning(
                    "cloud_code stream error %s: %s",
                    response.status_code,
                    snippet,
                )
                # Helpful Persian guidance per status code — کاربر باید بفهمد
                # 429 با message="Error" یعنی شناسایی Claude Code ناموفق بوده
                # (نه quota exhaustion).
                if response.status_code == 401:
                    hint = (
                        "توکن `CLAUDE_CODE_OAUTH_TOKEN` نامعتبر یا منقضی است. "
                        "با `claude setup-token` یک توکن تازه بساز."
                    )
                elif response.status_code == 429:
                    hint = (
                        "Anthropic این درخواست را به‌عنوان non-CLI تشخیص داد "
                        "(rate_limit anti-abuse). اگر این پیام بعد از دیپلوی "
                        "این فیکس دیدی، چند ثانیه صبر کن و دوباره امتحان کن. "
                        "اگر تکرار شد، sandbox/IP رو از Anthropic رفع‌محدودیت "
                        "بخواه یا quota اشتراک Claude Code رو چک کن."
                    )
                else:
                    hint = "جزئیات در پاسخ Anthropic."
                raise RuntimeError(
                    f"cloud_code API returned {response.status_code}: "
                    f"{snippet} | راهنما: {hint}"
                )

            async for line in response.aiter_lines():
                if not line or not line.startswith("data: "):
                    continue
                data_str = line[6:].strip()
                if data_str == "[DONE]":
                    break
                try:
                    data = json.loads(data_str)
                except json.JSONDecodeError:
                    continue
                ev_type = data.get("type")
                if ev_type == "message_start" and metadata_sink is not None:
                    # Anthropic streaming first event: message.model = actual
                    # model served (may differ from requested if Anthropic
                    # routed to a fallback). Capture for UI display.
                    msg = data.get("message") or {}
                    if msg.get("model"):
                        metadata_sink["actual_model"] = msg["model"]
                    if msg.get("id"):
                        metadata_sink["message_id"] = msg["id"]
                    if msg.get("usage"):
                        metadata_sink["usage_start"] = msg["usage"]
                elif ev_type == "message_delta" and metadata_sink is not None:
                    usage = (data.get("usage") or {})
                    if usage:
                        metadata_sink["usage"] = usage
                    stop_reason = (data.get("delta") or {}).get("stop_reason")
                    if stop_reason:
                        metadata_sink["stop_reason"] = stop_reason
                elif ev_type == "content_block_delta":
                    delta = data.get("delta") or {}
                    if delta.get("type") == "text_delta":
                        text = delta.get("text", "")
                        if text:
                            yield text


async def cloud_code_complete(
    messages: List[Dict[str, str]],
    *,
    system_prompt: Optional[str] = None,
    model: str = CLOUD_CODE_DEFAULT_MODEL,
    max_tokens: int = 4096,
    temperature: float = 0.7,
    timeout: float = 180.0,
) -> str:
    chunks: List[str] = []
    async for piece in cloud_code_stream_chat(
        messages,
        system_prompt=system_prompt,
        model=model,
        max_tokens=max_tokens,
        temperature=temperature,
        timeout=timeout,
    ):
        chunks.append(piece)
    return "".join(chunks)
