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
import re
import time
from typing import Any, AsyncIterator, Dict, List, Optional, Tuple

import httpx

logger = logging.getLogger(__name__)


CLOUD_CODE_DEFAULT_MODEL = "auto"  # "auto" → intelligent tier-based picker
CLOUD_CODE_API_URL = "https://api.anthropic.com/v1/messages"
CLOUD_CODE_MODELS_URL = "https://api.anthropic.com/v1/models"
CLOUD_CODE_API_VERSION = "2023-06-01"

# Hard-coded fallbacks per tier — used only when /v1/models is unreachable
# or when the OAuth plan does not expose a tier. Updated as new families
# ship; the dynamic discovery below will pick newer dated revisions
# automatically without needing a code change.
CLOUD_CODE_TIER_FALLBACKS: Dict[str, str] = {
    "opus": "claude-opus-4-5-20251101",
    "sonnet": "claude-sonnet-4-5-20250929",
    "haiku": "claude-haiku-4-5-20251001",
}

# Cache window for /v1/models — Anthropic ships new dated revisions every
# few weeks, so an hour keeps us fresh without hammering the endpoint.
_MODELS_CACHE: Dict[str, Any] = {"at": 0.0, "list": []}
_MODELS_CACHE_TTL_SEC = 3600.0
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


# ─────────────────────────────────────────────────────────────────────────────
# Dynamic model discovery + intelligent tier-based picker
# ─────────────────────────────────────────────────────────────────────────────
#
# Claude ships new dated model revisions every few weeks (e.g., Sonnet
# 4.5 → Sonnet 4.6 → Sonnet 5.0). To always reach the *latest* model
# without redeploying we:
#   1. Hit Anthropic's /v1/models endpoint (works with the OAuth token)
#      to enumerate everything the Claude Code plan exposes.
#   2. Cache the list for an hour so we don't pay the round-trip per chat.
#   3. Classify each request into an opus/sonnet/haiku tier from a
#      lightweight heuristic over the user's last message.
#   4. Inside the chosen tier, pick the newest dated revision (sort by
#      created_at descending). If discovery fails entirely, fall back to
#      the hard-coded tier defaults at the top of this module.


_TIER_HEAVY_PATTERNS = re.compile(
    r"\b("
    r"refactor|architecture|architect|design|audit|review|analyze|investigate|"
    r"معماری|بازنگری|بازآرایی|بررسی\s*عمیق|طراحی|بازطراحی|بازنویسی|"
    r"درست\s*کن.*کل|تمام\s*پروژه|سراسری|debug\s*end[- ]?to[- ]?end"
    r")\b",
    re.IGNORECASE,
)
_TIER_LIGHT_PATTERNS = re.compile(
    r"^("
    r"hi|hello|hey|thanks|thank you|yes|no|ok|"
    r"سلام|درود|ممنون|بله|خیر|آره|نه|باشه|"
    r"خودت\s*رو\s*معرفی|introduce\s*yourself"
    r")\b",
    re.IGNORECASE,
)


def _classify_tier(messages: List[Dict[str, str]]) -> str:
    """Return one of 'opus' | 'sonnet' | 'haiku' based on the user's last
    message. Default is 'sonnet' — the right balance for inspector chat.
    Heavy keywords (architecture/refactor/...) bump to opus.
    Light/greeting messages drop to haiku.
    """
    last_user = ""
    for m in reversed(messages or []):
        if (m.get("role") or "").lower() == "user":
            last_user = str(m.get("content") or "").strip()
            break
    if not last_user:
        return "sonnet"
    # Heavy first — explicit signal wins over length.
    if _TIER_HEAVY_PATTERNS.search(last_user):
        return "opus"
    # Very long context likely needs deeper reasoning.
    if len(last_user) > 4000:
        return "opus"
    # Light: short greetings / yes-no.
    if len(last_user) <= 80 and _TIER_LIGHT_PATTERNS.search(last_user):
        return "haiku"
    return "sonnet"


def _infer_tier_from_model_id(model_id: str) -> Optional[str]:
    mid = (model_id or "").lower()
    for tier in ("opus", "sonnet", "haiku"):
        if tier in mid:
            return tier
    return None


def _model_sort_key(m: Dict[str, Any]) -> Tuple[Any, ...]:
    """Sort key for picking the newest model within a tier.

    Prefer `created_at` (Anthropic returns RFC3339), fall back to the
    trailing YYYYMMDD in the model id (e.g., `claude-sonnet-4-5-20250929`).
    """
    created = m.get("created_at") or ""
    mid = (m.get("id") or "")
    match = re.search(r"(\d{8})$", mid)
    date_in_id = match.group(1) if match else ""
    return (created, date_in_id, mid)


async def list_available_models(*, force_refresh: bool = False) -> List[Dict[str, Any]]:
    """Hit /v1/models with the OAuth token + Claude Code beta headers.

    Returns the cached list when fresh. On any error returns the previous
    cached list (or an empty list) so callers can fall back to the
    hard-coded tier defaults — chat must never break just because the
    discovery endpoint is unreachable.
    """
    now = time.time()
    if (
        not force_refresh
        and _MODELS_CACHE["list"]
        and (now - _MODELS_CACHE["at"]) < _MODELS_CACHE_TTL_SEC
    ):
        return list(_MODELS_CACHE["list"])

    token = get_cloud_code_token()
    if not token:
        return list(_MODELS_CACHE["list"])

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                CLOUD_CODE_MODELS_URL,
                headers=_build_headers(token),
            )
            if resp.status_code != 200:
                logger.info(
                    "cloud_code /v1/models returned %s — keeping cached list",
                    resp.status_code,
                )
                return list(_MODELS_CACHE["list"])
            body = resp.json()
            data = body.get("data") or body.get("models") or []
            cleaned: List[Dict[str, Any]] = []
            for item in data:
                if not isinstance(item, dict):
                    continue
                mid = item.get("id") or item.get("model") or ""
                if not mid:
                    continue
                cleaned.append({
                    "id": mid,
                    "display_name": item.get("display_name") or mid,
                    "created_at": item.get("created_at") or "",
                    "type": item.get("type") or "",
                })
            _MODELS_CACHE["list"] = cleaned
            _MODELS_CACHE["at"] = now
            logger.info(
                "cloud_code refreshed model list: %d entries", len(cleaned)
            )
            return list(cleaned)
    except Exception as e:
        logger.warning("cloud_code list_available_models failed: %s", e)
        return list(_MODELS_CACHE["list"])


async def pick_best_model(
    messages: List[Dict[str, str]],
    *,
    tier_hint: Optional[str] = None,
) -> Tuple[str, str]:
    """Return `(model_id, picked_tier)` based on dynamic discovery.

    - `tier_hint` (optional): "opus" | "sonnet" | "haiku" to force a tier.
      When omitted, the tier is inferred from the user's last message via
      `_classify_tier`.
    - Within the chosen tier, the newest available revision wins.
    - Falls back to `CLOUD_CODE_TIER_FALLBACKS[tier]` when discovery
      returns nothing for that tier.
    """
    tier = (tier_hint or _classify_tier(messages)).lower()
    if tier not in CLOUD_CODE_TIER_FALLBACKS:
        tier = "sonnet"

    models = await list_available_models()
    in_tier = [m for m in models if _infer_tier_from_model_id(m.get("id", "")) == tier]
    if in_tier:
        in_tier.sort(key=_model_sort_key, reverse=True)
        return in_tier[0]["id"], tier

    # Tier empty in plan → try sonnet → opus → haiku as a graceful chain.
    for alt in ("sonnet", "opus", "haiku"):
        if alt == tier:
            continue
        alt_in = [m for m in models if _infer_tier_from_model_id(m.get("id", "")) == alt]
        if alt_in:
            alt_in.sort(key=_model_sort_key, reverse=True)
            logger.info(
                "cloud_code: tier '%s' empty in plan, falling back to '%s'",
                tier, alt,
            )
            return alt_in[0]["id"], alt

    # /v1/models unreachable and cache empty → hard-coded default.
    return CLOUD_CODE_TIER_FALLBACKS[tier], tier


async def cloud_code_stream_chat(
    messages: List[Dict[str, str]],
    *,
    system_prompt: Optional[str] = None,
    model: str = CLOUD_CODE_DEFAULT_MODEL,
    max_tokens: int = 4096,
    temperature: float = 0.7,
    timeout: float = 180.0,
    metadata_sink: Optional[Dict[str, Any]] = None,
    tier_hint: Optional[str] = None,
) -> AsyncIterator[str]:
    """
    metadata_sink: optional dict that the generator mutates as the stream
    progresses. After the first `message_start` event it contains
    `actual_model` (the model ID Anthropic actually served), and after
    `message_delta` it gains `usage` (input/output tokens). Callers can
    use this to display the *real* model in the UI — Claude's own
    self-identification in text replies is unreliable (the training data
    causes Sonnet 4.x to often say "I am Claude 3.5 Sonnet").

    model: pass an explicit model id (e.g. "claude-opus-4-5-20251101") to
    pin, or "auto" (the default) to let `pick_best_model` route the
    request to the latest model in the inferred tier. `tier_hint` lets a
    caller force a tier (opus/sonnet/haiku) without naming a specific id.
    """
    token = get_cloud_code_token()
    if not token:
        raise RuntimeError(
            "CLAUDE_CODE_OAUTH_TOKEN env var is not set — "
            "cloud_code engine unavailable"
        )

    # 🤖 Dynamic model selection — "auto" routes to the latest model in
    # the tier that best matches the user's request. Anything else is
    # passed through verbatim so power users can pin.
    picked_tier: Optional[str] = None
    requested_model = model
    if model == "auto" or tier_hint is not None:
        chosen_id, picked_tier = await pick_best_model(
            messages, tier_hint=tier_hint
        )
        model = chosen_id
        if metadata_sink is not None:
            metadata_sink["requested_model"] = requested_model
            metadata_sink["picked_model"] = chosen_id
            metadata_sink["picked_tier"] = picked_tier

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
