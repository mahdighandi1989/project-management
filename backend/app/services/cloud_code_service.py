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
# OAuth tokens issued by `claude setup-token` require this beta header to be
# accepted by the Messages API. Keep in sync with claude_runner_bootstrap.
CLOUD_CODE_OAUTH_BETA = "oauth-2025-04-20"


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


async def cloud_code_stream_chat(
    messages: List[Dict[str, str]],
    *,
    system_prompt: Optional[str] = None,
    model: str = CLOUD_CODE_DEFAULT_MODEL,
    max_tokens: int = 4096,
    temperature: float = 0.7,
    timeout: float = 180.0,
) -> AsyncIterator[str]:
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
    }
    if system_prompt:
        payload["system"] = system_prompt

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
                raise RuntimeError(
                    f"cloud_code API returned {response.status_code}: {snippet}"
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
                if data.get("type") == "content_block_delta":
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
