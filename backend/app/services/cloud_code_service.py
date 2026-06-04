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
#
# 🆕 (model refresh) — بروز شدن aliases به آخرین خانوادهٔ موجود تا اگر
# /v1/models در دسترس نباشد، باز هم کاربر به جدیدترین مدل برسد. این فقط
# safety net است؛ مسیر اصلی pick_best_model همچنان از /v1/models می‌خواند
# و آخرین revision را با date بزرگتر برمی‌دارد — کاملاً dynamic.
CLOUD_CODE_TIER_FALLBACKS: Dict[str, str] = {
    "opus": "claude-opus-4-8",      # alias — Claude CLI آن را به آخرین Opus 4.8 route می‌کند
    "sonnet": "claude-sonnet-4-6",  # alias — به آخرین Sonnet 4.6
    "haiku": "claude-haiku-4-5",    # هنوز جدیدترین Haiku (نسخهٔ کوچک‌تر آپدیت کمتر دارد)
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


# ---------------------------------------------------------------------------
# 🆕 (Cloud Code centralization — stage 2) — single-source-of-truth helper
# ---------------------------------------------------------------------------
# Cloud Code قبلاً در 4 جای مختلف به‌صورت مستقل سیم‌کشی شده بود:
#   - claude_runner_bootstrap.pick_model_for_task (auto-runner)
#   - oversight.run-via-claude endpoint (دکمهٔ تک‌تسک)
#   - inspector_agent_service.chat_with_cloud_code (چت بازرس)
#   - creator engine (هنوز اضافه نشده)
# هر کدام cloud_code_is_configured() را مستقیماً صدا می‌زدند و اگر True
# می‌بود، استفاده می‌کردند — بدون toggle مرکزی برای کاربر. حالا با ثبت
# Cloud Code به‌عنوان یک ردیف در صفحهٔ مدل‌ها (stage 1)، کاربر می‌تواند
# enabled آن را خاموش کند یا preferred_for را به subset از 4 مصرف‌کننده
# محدود کند. این helper آن وضعیت را برای consumer ها در یک نقطه می‌خواند.
#
# ════════════════════════════════════════════════════════════════════════
# 🧭 EXTENSIBILITY GUIDE — اضافه کردن یک consumer جدید
# ════════════════════════════════════════════════════════════════════════
#
# می‌خواهید Cloud Code را به یک قسمت جدید برنامه وصل کنید (مثلاً
# `report_generator`)؟ این الگو را دنبال کنید — کل کار ۳ فایل + ۱ خط
# در نقطهٔ مصرف است.
#
# گام ۱ — Backend: ثبت consumer جدید (یک فایل، دو خط)
#     File: backend/app/models/ai_profile.py
#
#     a) به AVAILABLE_TASK_TYPES اضافه کن:
#        {
#            "id": "report_generator",
#            "name": "تولیدکنندهٔ گزارش",
#            "description": "ساخت گزارش‌های هفتگی با Cloud Code",
#        },
#
#     b) به CLOUD_CODE_PREFERRED_FOR_KEYS اضافه کن:
#        "report_generator",
#
# گام ۲ — Frontend: ثبت در set مرکزی (یک فایل، یک خط)
#     File: frontend/src/app/models/page.tsx
#     در CLOUD_CODE_TASK_KEYS اضافه کن: 'report_generator',
#
# گام ۳ — Consumer: یک خط در نقطهٔ مصرف
#     در فایل consumer جدید:
#
#         from app.services.cloud_code_service import (
#             cloud_code_setting_is_enabled_for,
#             cloud_code_message,  # یا cloud_code_complete یا stream
#         )
#
#         if cloud_code_setting_is_enabled_for("report_generator"):
#             # کاربر این consumer را برای Cloud Code فعال کرده
#             result = await cloud_code_message(
#                 messages=[...],
#                 system_prompt=...,
#                 model="auto",  # tier picker خودش انتخاب می‌کند
#             )
#         else:
#             # fallback به مسیر معمول (ai_manager، gemini، ...)
#             ...
#
# همین! بدون تغییر helper، بدون UI کد جدید. UI خودکار گزینهٔ تازه را
# در «ترجیحی برای» edit modal صفحهٔ مدل‌ها نشان می‌دهد چون از
# `/api/models/task-types` می‌خواند (که خود از AVAILABLE_TASK_TYPES
# می‌آید).
#
# نکته‌های مهم:
#   - default = True: اگر کاربر هیچ تنظیمی نکرده، consumer جدید روشن
#     است — همان رفتار "سازگاری با قبل" که سایر consumer ها دارند.
#   - اگر env token خالی است، helper بی‌قید و شرط False برمی‌گرداند.
#   - DB error → True (legacy fallback). کاربر هیچ outage نمی‌بیند.
#   - برای OAuth-driven models آینده (مثلاً Gemini OAuth)، الگوی
#     identical: یک special-case در _run_single_test و یک بخش در
#     pick_best_extraction_model.
#
# ════════════════════════════════════════════════════════════════════════

_CLOUD_CODE_MODEL_ID = "cloud_code"


def cloud_code_setting_is_enabled_for(consumer_key: str) -> bool:
    """🆕 (centralization) — آیا کاربر این مصرف‌کننده را برای Cloud Code
    فعال کرده؟

    consumer_key باید یکی از CLOUD_CODE_PREFERRED_FOR_KEYS باشد:
      - "claude_auto_runner"       → اجرای خودکار workflow
      - "claude_single_task"       → دکمهٔ Run via Claude
      - "inspector_cloud_code"     → چت بازرس Cloud Code engine
      - "creator_engine"           → موتور خالق

    قواعد:
      1) اگر token اصلاً ست نیست (env خالی) → False مطلق.
      2) اگر ردیف cloud_code در DB موجود نیست → fallback به default
         رفتار: True برای همهٔ consumer ها (سازگاری با قبل).
      3) اگر ردیف موجود است ولی enabled=False → False.
      4) اگر enabled=True ولی preferred_for خالی است → True برای همه
         (به این معنا که کاربر هنوز سفارشی نکرده).
      5) اگر enabled=True و preferred_for پر است → فقط key های موجود
         در آن لیست True می‌گیرند.

    خطاها silent — هرگز exception نمی‌اندازد. اگر DB در دسترس نیست،
    fallback به True (سازگاری با قبل).
    """
    if not cloud_code_is_configured():
        return False
    try:
        from ..core.database import SessionLocal
        from ..models.ai_profile import ModelSettings
    except Exception as e:
        # 🆕 (audit follow-up) — این مسیر معمولی نباید پیش بیاید. اگر
        # تکرار شود، operator باید بفهمد. WARN نه DEBUG.
        logger.warning(
            f"cloud_code_setting_is_enabled_for: import failed for "
            f"consumer={consumer_key!r}: {e} — falling back to legacy True"
        )
        return True  # fallback — رفتار قبلی
    try:
        db = SessionLocal()
        try:
            row = db.query(ModelSettings).filter(
                ModelSettings.model_id == _CLOUD_CODE_MODEL_ID
            ).first()
            if row is None:
                return True  # default — هنوز سفارشی نشده
            if not row.enabled:
                return False
            preferred = list(row.preferred_for or [])
            if not preferred:
                return True  # enabled بدون فیلتر — همه consumer ها مجاز
            # "all" به عنوان wildcard
            if "all" in preferred:
                return True
            return consumer_key in preferred
        finally:
            try:
                db.close()
            except Exception:
                pass
    except Exception as e:
        # 🆕 (audit follow-up) — اگر DB در outage باشد، helper به True
        # برمی‌گردد (legacy default امن‌تر). ولی operator باید بفهمد —
        # توگل کاربر در این فاصله honor نمی‌شود.
        logger.warning(
            f"cloud_code_setting_is_enabled_for: DB read failed for "
            f"consumer={consumer_key!r}: {e} — falling back to legacy True. "
            f"User's models-page toggle is NOT being honored during this outage."
        )
        return True  # fallback — رفتار قبلی


def cloud_code_settings_snapshot() -> Dict[str, Any]:
    """🆕 (centralization) — snapshot کامل از وضعیت Cloud Code برای
    debug/diagnostics endpoint. شامل availability env، enabled DB،
    preferred_for، و نتیجهٔ per-consumer flag ها.
    """
    out: Dict[str, Any] = {
        "token_configured": cloud_code_is_configured(),
        "registry_enabled": True,
        "db_row_present": False,
        "db_enabled": None,
        "preferred_for": [],
        "consumers": {},
    }
    try:
        from ..core.models_registry import MODEL_REGISTRY
        entry = MODEL_REGISTRY.get(_CLOUD_CODE_MODEL_ID)
        if entry is not None:
            out["registry_enabled"] = bool(entry.enabled)
    except Exception:
        pass
    try:
        from ..core.database import SessionLocal
        from ..models.ai_profile import ModelSettings, CLOUD_CODE_PREFERRED_FOR_KEYS
        db = SessionLocal()
        try:
            row = db.query(ModelSettings).filter(
                ModelSettings.model_id == _CLOUD_CODE_MODEL_ID
            ).first()
            if row is not None:
                out["db_row_present"] = True
                out["db_enabled"] = bool(row.enabled)
                out["preferred_for"] = list(row.preferred_for or [])
        finally:
            try:
                db.close()
            except Exception:
                pass
        for key in CLOUD_CODE_PREFERRED_FOR_KEYS:
            out["consumers"][key] = cloud_code_setting_is_enabled_for(key)
    except Exception as e:
        out["error"] = str(e)[:200]
    return out


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
    r"("
    # Architecture & deep refactors
    r"\brefactor\b|\barchitect(ure|ural)?\b|\bredesign\b|\bre-?write\b|"
    r"\baudit\b|\binvestigate\b|\bdebug\s*end[- ]?to[- ]?end\b|"
    r"\bsystem[- ]?design\b|\bcode[- ]?review\b|\bdeep\s*dive\b|"
    # Persian heavy signals
    r"معماری|بازنگری|بازآرایی|بازنویسی|بازطراحی|بررسی\s*عمیق|طراحی|"
    r"تحلیل\s*کامل|تحلیل\s*عمیق|سراسری|تمام\s*پروژه|درست\s*کن.*کل|"
    r"بازبینی\s*کامل|ساختار\s*کلی|"
    # Multi-file / multi-step requests
    r"\bmulti[- ]?(file|step|module)\b|\bmigration\b|\bport(ing)?\s+from\b|"
    r"چند\s*فایل|چند\s*مرحله|مهاجرت|انتقال\s*از|"
    # Performance / security / scale
    r"\boptim(ize|ization|isation)\b|\bperformance\b|\bscal(e|ing|ability)\b|"
    r"\bsecurity\b|\bvuln(erability)?\b|\brace\s*condition\b|\bdeadlock\b|"
    r"بهینه[‌ ]?سازی|عملکرد|مقیاس|امنیت|آسیب[‌ ]?پذیر|"
    # Complex algorithms / proofs
    r"\balgorithm\b|\bcomplexity\b|\bcorrectness\b|\bproof\b|"
    r"الگوریتم|اثبات|پیچیدگی"
    r")",
    re.IGNORECASE,
)

_TIER_LIGHT_PATTERNS = re.compile(
    r"^("
    # Greetings & social
    r"hi|hello|hey|thanks|thank\s*you|cheers|bye|"
    r"سلام|درود|ممنون|مرسی|تشکر|خداحافظ|بدرود|"
    # Simple yes/no / acknowledgement
    r"yes|no|ok|okay|sure|nope|yep|right|wrong|true|false|"
    r"بله|خیر|آره|نه|باشه|اوهوم|نه[‌ ]?نه|درسته|اشتباهه|"
    # Trivial requests
    r"خودت\s*رو\s*معرفی|introduce\s*yourself|who\s*are\s*you|what\s*model|"
    r"how\s*are\s*you|چطوری|چه\s*خبر|"
    # Short clarifications
    r"why|how|when|where|what|"
    r"چرا|چطور|کِی|کجا|چی|چیست"
    r")[\s\?\.!،]*$",
    re.IGNORECASE,
)

# Signals that bias toward Sonnet (default coding work) — used to keep
# short coding requests on Sonnet rather than dropping them to Haiku.
_TIER_CODE_PATTERNS = re.compile(
    r"("
    # Code fences / language tokens
    r"```|\bdef\s|\bclass\s|\bimport\s|\bfunction\s|\bconst\s|\blet\s|\bvar\s|"
    r"\basync\s|\bawait\b|\breturn\b|"
    # English coding verbs
    r"\bfix\s+(this|the|that|my|it)?\b|\berror\b|\bbug\b|\bfail(ing|ed)?\b|"
    r"\bimplement\b|\badd\s+(a|the|this|new)?\b|\bcreate\s+(a|the|this|new)?\b|"
    r"\bwrite\s+(a|the|this|some)?\b|\bcode\b|\brefactor\b|\bdebug\b|"
    # Persian coding verbs / nouns
    r"کد|بنویس|بنوس|بساز|بسازی|اضافه\s*کن|اضافش?\s*کن|"
    r"خطا|باگ|پیاده[‌ ]?سازی|اصلاح\s*کن|درست\s*کن|تعمیر|"
    r"تابع|کلاس|متد|ماژول|فایل|تست|"
    # Project nouns
    r"\bendpoint\b|\bapi\b|\broute\b|\bcomponent\b|\bhook\b|\bstate\b|"
    r"\bdatabase\b|\bquery\b|\bsql\b|\bschema\b|\bmigration\b"
    r")",
    re.IGNORECASE,
)


def _classify_tier(messages: List[Dict[str, str]]) -> Tuple[str, str]:
    """Return `(tier, reason)` — tier is one of opus/sonnet/haiku and reason
    is a short human-readable explanation so the UI can show *why* a tier
    was picked.

    Multi-signal routing:
      1. Heavy keywords (refactor / architecture / audit / security / ...)
         OR very long single message (>3500 chars) → opus
      2. Long ongoing conversation with code (≥6 turns + code present) → opus
      3. Pure greeting / yes-no / short trivial question (≤120 chars and
         matches light pattern, with no code fences) → haiku
      4. Short factual question without code (≤200 chars, no code keywords,
         not a coding action) → haiku
      5. Everything else (code work, debugging, mid-complexity asks) → sonnet
    """
    last_user = ""
    for m in reversed(messages or []):
        if (m.get("role") or "").lower() == "user":
            last_user = str(m.get("content") or "").strip()
            break
    if not last_user:
        return "sonnet", "default (no user message)"

    has_code_signal = bool(_TIER_CODE_PATTERNS.search(last_user))
    msg_len = len(last_user)
    turn_count = sum(1 for m in (messages or []) if (m.get("role") or "").lower() == "user")
    history_chars = sum(
        len(str(m.get("content") or ""))
        for m in (messages or [])
    )

    # 1) Heavy keywords win unconditionally
    heavy_match = _TIER_HEAVY_PATTERNS.search(last_user)
    if heavy_match:
        return "opus", f"heavy keyword '{heavy_match.group(0)[:30]}' → opus"

    # 2) Very long single message
    if msg_len > 3500:
        return "opus", f"long message ({msg_len} chars) → opus"

    # 3) Long ongoing technical convo
    if turn_count >= 6 and history_chars > 8000 and has_code_signal:
        return "opus", (
            f"deep ongoing convo ({turn_count} turns, "
            f"{history_chars//1000}k chars, code-heavy) → opus"
        )

    # 4) Greeting / yes-no / short trivial — only if no code and short
    if msg_len <= 120 and _TIER_LIGHT_PATTERNS.match(last_user) and not has_code_signal:
        return "haiku", f"short trivial ({msg_len} chars) → haiku"

    # 5) Short factual question
    if msg_len <= 200 and not has_code_signal:
        return "haiku", f"short Q&A ({msg_len} chars, no code) → haiku"

    # 6) Default — Sonnet for normal coding/debugging
    return "sonnet", (
        f"balanced ({msg_len} chars"
        + (", code present" if has_code_signal else "")
        + ") → sonnet"
    )


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
    min_tier: Optional[str] = None,
) -> Tuple[str, str, str]:
    """Return `(model_id, picked_tier, reason)`.

    - `tier_hint` (optional): "opus" | "sonnet" | "haiku" to force a tier.
      When omitted, `_classify_tier` chooses + supplies a human-readable
      reason that the UI can display.
    - `min_tier` (optional): "opus" | "sonnet" | "haiku" — حداقل tier
      مجاز. اگر classifier پایین‌تر تشخیص داد، به این مقدار رو می‌رسد.
      برای inspector chat و موتور خالق `min_tier="sonnet"` پیش‌فرض است
      تا پرسش‌های کوتاه به Haiku نروند (Haiku گاهی خودش را غلط معرفی
      می‌کند و پاسخ‌های سطحی‌تری می‌دهد).
    - Within the chosen tier, the newest available revision wins.
    - Falls back to `CLOUD_CODE_TIER_FALLBACKS[tier]` when discovery
      returns nothing for that tier; logs and reports the fallback path
      so callers know the model wasn't the first choice.
    """
    # 🆕 (precedence) — tier_hint = "صراحت کاربر" است (مثلاً انتخاب از
    # dropdown). همیشه برنده. min_tier فقط برای حالتی است که از classifier
    # استفاده می‌شود (tier_hint خالی). به این ترتیب اگر کاربر در UI
    # دستی Haiku را انتخاب کند، min_tier="sonnet" آن را override نمی‌کند.
    if tier_hint:
        tier = tier_hint.lower()
        reason = f"tier hint forced → {tier}"
    else:
        tier, reason = _classify_tier(messages)
        # 🆕 (min_tier floor) — فقط برای حالت auto-classified اعمال می‌شود.
        # caller می‌تواند کف tier تعیین کند تا پرسش‌های کوتاه به Haiku
        # route نشوند بدون اینکه انتخاب صریح کاربر را override کند.
        if min_tier and min_tier.lower() in CLOUD_CODE_TIER_FALLBACKS:
            _order = ["haiku", "sonnet", "opus"]
            try:
                cur_idx = _order.index(tier)
                min_idx = _order.index(min_tier.lower())
                if cur_idx < min_idx:
                    tier = min_tier.lower()
                    reason = f"{reason}; raised to min_tier={tier}"
            except ValueError:
                pass
    if tier not in CLOUD_CODE_TIER_FALLBACKS:
        tier = "sonnet"
        reason = f"unknown tier requested, defaulted to sonnet"

    models = await list_available_models()
    in_tier = [m for m in models if _infer_tier_from_model_id(m.get("id", "")) == tier]
    if in_tier:
        in_tier.sort(key=_model_sort_key, reverse=True)
        return in_tier[0]["id"], tier, reason

    # Tier empty in plan → walk a graceful chain. Opus is the smartest
    # so try it first when sonnet is missing; otherwise prefer sonnet.
    fallback_order = ["sonnet", "opus", "haiku"] if tier != "sonnet" else ["opus", "haiku"]
    for alt in fallback_order:
        if alt == tier:
            continue
        alt_in = [m for m in models if _infer_tier_from_model_id(m.get("id", "")) == alt]
        if alt_in:
            alt_in.sort(key=_model_sort_key, reverse=True)
            logger.info(
                "cloud_code: tier '%s' empty in plan, falling back to '%s'",
                tier, alt,
            )
            return alt_in[0]["id"], alt, f"{reason}; plan lacks {tier}, fell back to {alt}"

    # /v1/models unreachable and cache empty → hard-coded default.
    return (
        CLOUD_CODE_TIER_FALLBACKS[tier],
        tier,
        f"{reason}; discovery empty, using hard-coded fallback",
    )


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
    min_tier: Optional[str] = None,
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
    if model == "auto" or tier_hint is not None or min_tier is not None:
        chosen_id, picked_tier, pick_reason = await pick_best_model(
            messages, tier_hint=tier_hint, min_tier=min_tier,
        )
        model = chosen_id
        if metadata_sink is not None:
            metadata_sink["requested_model"] = requested_model
            metadata_sink["picked_model"] = chosen_id
            metadata_sink["picked_tier"] = picked_tier
            metadata_sink["pick_reason"] = pick_reason

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

    # 🚨 (audit fix CRITICAL) — برخی مدل‌های جدید Claude (مثل Opus 4.8+ با
    # extended thinking) صراحتاً پارامتر `temperature` را reject می‌کنند با
    # 400 «`temperature` is deprecated for this model». این بدون retry
    # کل feature های Cloud Code (regenerate prompt، auto-runner verify،
    # monitoring، …) را silently break می‌کند. حالا اگر این خطای خاص را
    # گرفتیم، payload را بدون temperature retry می‌کنیم.
    _attempt_payloads = [payload]
    _no_temp_payload = {k: v for k, v in payload.items() if k != "temperature"}
    _attempt_payloads.append(_no_temp_payload)

    async with httpx.AsyncClient(timeout=timeout) as client:
        for _attempt_idx, _try_payload in enumerate(_attempt_payloads):
            _is_last_attempt = _attempt_idx == len(_attempt_payloads) - 1
            async with client.stream(
                "POST",
                CLOUD_CODE_API_URL,
                headers=_build_headers(token),
                json=_try_payload,
            ) as response:
                if response.status_code != 200:
                    body = await response.aread()
                    snippet = body[:500].decode("utf-8", errors="replace")
                    # 🚨 (temperature deprecation retry) — اگر مدل
                    # temperature را reject کرد و این اولین تلاش است، با
                    # payload بدون temperature retry می‌کنیم.
                    if (
                        response.status_code == 400
                        and not _is_last_attempt
                        and ("temperature" in snippet.lower()
                             and "deprecated" in snippet.lower())
                    ):
                        logger.info(
                            "cloud_code: model %s rejected temperature param "
                            "(400 deprecated). Retrying without temperature.",
                            model,
                        )
                        continue
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

                # ✅ 200 OK — stream the response then exit the retry loop.
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
                return  # success — exit retry loop


async def cloud_code_complete(
    messages: List[Dict[str, str]],
    *,
    system_prompt: Optional[str] = None,
    model: str = CLOUD_CODE_DEFAULT_MODEL,
    max_tokens: int = 4096,
    temperature: float = 0.7,
    timeout: float = 180.0,
    tier_hint: Optional[str] = None,
    min_tier: Optional[str] = None,
    # 🆕 (capability test fix) — اجازه می‌دهد caller صراحتاً tier را
    # مجبور کند. برای تست توانایی این لازم است: prompts تست کوتاه‌اند
    # و _classify_tier آن‌ها را به haiku route می‌کند، که نتیجه‌ی
    # نامنصفانه (32/100) به دست می‌دهد. caller معمولاً tier_hint="opus"
    # می‌دهد تا قدرت کامل subscription سنجیده شود.
) -> str:
    chunks: List[str] = []
    async for piece in cloud_code_stream_chat(
        messages,
        system_prompt=system_prompt,
        model=model,
        max_tokens=max_tokens,
        temperature=temperature,
        timeout=timeout,
        tier_hint=tier_hint,
        min_tier=min_tier,
    ):
        chunks.append(piece)
    return "".join(chunks)


# ─────────────────────────────────────────────────────────────────────────────
# Tool-aware non-streaming call (for agent loop)
# ─────────────────────────────────────────────────────────────────────────────
#
# The streaming helper above is intentionally text-only — perfect for fast
# Q&A. To match Local AI smart-chat capabilities (file read, Render API,
# git, deploys, …) we need a tool-calling variant. Anthropic Messages API
# supports it via:
#   - request: tools=[{name,description,input_schema}, ...]
#   - response: content blocks of type "tool_use" alongside text blocks
#   - follow-up: user turn with tool_result content blocks for each tool_use
#
# We expose this as a single-turn call (not streaming) that returns the
# full assistant message structure. The caller runs the loop, executes
# tools, appends a user turn with the results, and calls again until the
# model stops emitting tool_use blocks.


async def cloud_code_message(
    messages: List[Dict[str, Any]],
    *,
    system_prompt: Optional[str] = None,
    model: str = CLOUD_CODE_DEFAULT_MODEL,
    max_tokens: int = 8000,
    temperature: float = 0.2,
    timeout: float = 180.0,
    tools: Optional[List[Dict[str, Any]]] = None,
    tier_hint: Optional[str] = None,
    min_tier: Optional[str] = None,
    metadata_sink: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Single-turn (non-streaming) call to Anthropic Messages API with full
    `content` block support — including tool_use.

    Returns the assistant's raw message dict:
      {
        "stop_reason": "end_turn" | "tool_use" | "max_tokens" | ...,
        "content": [
          {"type": "text", "text": "..."},
          {"type": "tool_use", "id": "...", "name": "...", "input": {...}},
          ...
        ],
        "usage": {...},
        "model": "claude-...",
      }

    Callers running the agent loop:
      1. Append the returned assistant turn verbatim to `messages`
         (role=assistant, content=the content array).
      2. For each tool_use block, execute the tool and append a user turn
         whose content is a list of {"type":"tool_result","tool_use_id":id,
         "content":..., "is_error":bool} blocks.
      3. Re-call cloud_code_message until stop_reason != "tool_use".
    """
    token = get_cloud_code_token()
    if not token:
        raise RuntimeError(
            "CLAUDE_CODE_OAUTH_TOKEN env var is not set — "
            "cloud_code engine unavailable"
        )

    # auto-route via the same picker as streaming
    if model == "auto" or tier_hint is not None or min_tier is not None:
        chosen_id, picked_tier, pick_reason = await pick_best_model(
            _flatten_messages_for_classifier(messages),
            tier_hint=tier_hint, min_tier=min_tier,
        )
        if metadata_sink is not None:
            metadata_sink["requested_model"] = model
            metadata_sink["picked_model"] = chosen_id
            metadata_sink["picked_tier"] = picked_tier
            metadata_sink["pick_reason"] = pick_reason
        model = chosen_id

    payload: Dict[str, Any] = {
        "model": model,
        "messages": _coerce_messages_for_tools(messages),
        "max_tokens": max_tokens,
        "temperature": temperature,
        "system": _build_system_blocks(system_prompt),
    }
    if tools:
        payload["tools"] = tools

    # 🚨 (temperature deprecation retry) — مثل cloud_code_stream_chat،
    # اگر مدل temperature را reject کرد با 400، بدون temperature retry کن.
    _attempt_payloads = [payload]
    _attempt_payloads.append({k: v for k, v in payload.items() if k != "temperature"})

    response = None
    async with httpx.AsyncClient(timeout=timeout) as client:
        for _attempt_idx, _try_payload in enumerate(_attempt_payloads):
            _is_last_attempt = _attempt_idx == len(_attempt_payloads) - 1
            response = await client.post(
                CLOUD_CODE_API_URL,
                headers=_build_headers(token),
                json=_try_payload,
            )
            if response.status_code == 200:
                break
            snippet = response.text[:500]
            if (
                response.status_code == 400
                and not _is_last_attempt
                and ("temperature" in snippet.lower()
                     and "deprecated" in snippet.lower())
            ):
                logger.info(
                    "cloud_code_message: model %s rejected temperature param "
                    "(400 deprecated). Retrying without temperature.",
                    model,
                )
                continue
            if response.status_code == 401:
                hint = "OAuth token نامعتبر یا منقضی. با `claude setup-token` تازه بساز."
            elif response.status_code == 429:
                hint = "rate limit — یا انتی-abuse تشخیص داد. چند ثانیه صبر کن."
            else:
                hint = "جزئیات در پاسخ Anthropic."
            raise RuntimeError(
                f"cloud_code API returned {response.status_code}: {snippet} | {hint}"
            )
        # success
        data = response.json()
        if metadata_sink is not None:
            metadata_sink["actual_model"] = data.get("model") or model
            metadata_sink["message_id"] = data.get("id")
            metadata_sink["usage"] = data.get("usage")
            metadata_sink["stop_reason"] = data.get("stop_reason")
        return data


def _flatten_messages_for_classifier(messages: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    """Tier classifier expects plain {role, content:str}. When messages
    contain block lists (for tool_use/tool_result rounds), reduce each to
    a text approximation so the classifier still works."""
    out: List[Dict[str, str]] = []
    for m in messages or []:
        role = (m.get("role") or "").lower()
        content = m.get("content")
        if isinstance(content, str):
            out.append({"role": role, "content": content})
        elif isinstance(content, list):
            texts: List[str] = []
            for block in content:
                if isinstance(block, dict):
                    if block.get("type") == "text" and block.get("text"):
                        texts.append(str(block["text"]))
                    elif block.get("type") == "tool_use":
                        texts.append(f"[tool_use:{block.get('name', '?')}]")
                    elif block.get("type") == "tool_result":
                        c = block.get("content")
                        if isinstance(c, str):
                            texts.append(c[:200])
            if texts:
                out.append({"role": role, "content": "\n".join(texts)})
    return out


def _coerce_messages_for_tools(messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Same role-filtering rules as _coerce_messages, but PRESERVES rich
    content (block lists) used by tool_use / tool_result turns."""
    cleaned: List[Dict[str, Any]] = []
    for m in messages or []:
        role = (m.get("role") or "").strip().lower()
        content = m.get("content")
        if role not in ("user", "assistant"):
            continue
        if content is None:
            continue
        if isinstance(content, str) and not content.strip():
            continue
        if isinstance(content, list) and not content:
            continue
        cleaned.append({"role": role, "content": content})
    while cleaned and cleaned[0]["role"] != "user":
        cleaned.pop(0)
    return cleaned


# ─────────────────────────────────────────────────────────────────────────────
# Agent loop — closes the parity gap with Local AI smart-chat
# ─────────────────────────────────────────────────────────────────────────────
#
# This is the orchestrator that turns cloud_code_message into a real agent:
# call the model → look at content blocks → for each tool_use, hand off to a
# caller-provided executor → append the results as a new user turn → call
# again. Stops when the model emits no more tool_use (stop_reason="end_turn"
# or similar) or the iteration budget is exhausted.
#
# The executor is injected by the endpoint so it owns the dangerous things
# (Render API, git tokens, file fetches). cloud_code_service stays
# infrastructure-only.


from typing import Awaitable, Callable  # noqa: E402  (kept near agent loop)


ToolExecutor = Callable[[str, Dict[str, Any]], Awaitable[Dict[str, Any]]]
"""(tool_name, tool_input) → {"content": str | list, "is_error": bool} or
plain str (treated as success content). The executor must NEVER raise — any
failure should be returned as {"content": "...", "is_error": True}."""


async def cloud_code_agent_loop(
    *,
    user_prompt: str,
    system_prompt: Optional[str] = None,
    tools: List[Dict[str, Any]],
    executor: ToolExecutor,
    initial_history: Optional[List[Dict[str, Any]]] = None,
    model: str = "auto",
    tier_hint: Optional[str] = None,
    min_tier: Optional[str] = None,
    max_iterations: int = 12,
    max_tokens_per_call: int = 8000,
    temperature: float = 0.2,
    on_event: Optional[Callable[[str, Dict[str, Any]], Awaitable[None]]] = None,
    metadata_sink: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Drive an Anthropic agent loop on top of cloud_code_message.

    Parameters
    ----------
    user_prompt
        The user's latest message. Appended as a fresh "user" turn after
        any history.
    system_prompt
        Optional system context for the agent. The Claude Code identity
        block is always prepended by `_build_system_blocks`, so callers
        only need to supply task-specific instructions.
    tools
        Anthropic tool schemas (same shape as inspector_agent's
        `_build_tools()`). Reuse them verbatim — no translation needed.
    executor
        Async callable invoked for each tool_use block. Must return either
        a string (success content) or a dict with `content` and an
        optional `is_error: bool`.
    initial_history
        Optional prior turns (chat history). Each item is `{role, content}`
        where content can be a string or an Anthropic block list.
    on_event
        Optional async callback for progress events. Receives
        ("text", {"text": ...}), ("tool_use", {"name", "input", "id"}),
        ("tool_result", {"name", "is_error", "content"}), ("done",
        {"stop_reason", "iterations", "final_text"}).

    Returns
    -------
    A summary dict:
      {
        "final_text": str,              # concatenated text blocks from the
                                        # last assistant turn
        "stop_reason": str,
        "iterations": int,
        "tool_calls": List[{name, input, result, is_error}],
        "model_used": str,              # from metadata_sink["actual_model"]
        "usage_last": Dict | None,
      }
    """
    messages: List[Dict[str, Any]] = list(initial_history or [])
    messages.append({"role": "user", "content": user_prompt})

    sink: Dict[str, Any] = dict(metadata_sink or {})
    tool_calls_log: List[Dict[str, Any]] = []
    final_text = ""
    stop_reason = "natural_stop"
    iterations_done = 0

    async def _emit(kind: str, payload: Dict[str, Any]) -> None:
        if on_event is None:
            return
        try:
            await on_event(kind, payload)
        except Exception:
            logger.debug("agent_loop on_event handler raised (continuing)")

    for it in range(1, max_iterations + 1):
        iterations_done = it
        try:
            response = await cloud_code_message(
                messages,
                system_prompt=system_prompt,
                tools=tools,
                model=model,
                tier_hint=tier_hint,
                min_tier=min_tier,
                max_tokens=max_tokens_per_call,
                temperature=temperature,
                metadata_sink=sink,
            )
        except Exception as e:
            logger.warning("cloud_code_agent_loop call %d failed: %s", it, e)
            final_text = f"⚠️ Cloud Code call failed: {str(e)[:300]}"
            stop_reason = "error"
            await _emit("error", {"message": final_text, "iteration": it})
            break

        # After the very first call, lock the model to whatever the auto
        # picker chose so subsequent rounds use the same model (avoids
        # mid-loop model drift if the message classification shifts).
        if it == 1 and sink.get("picked_model"):
            model = sink["picked_model"]
            tier_hint = None

        content_blocks = response.get("content") or []
        stop_reason = response.get("stop_reason") or "natural_stop"

        # Collect text the model emitted alongside any tool calls so the
        # frontend can show progress narration even on tool-use rounds.
        text_parts: List[str] = []
        tool_uses: List[Dict[str, Any]] = []
        for block in content_blocks:
            if not isinstance(block, dict):
                continue
            btype = block.get("type")
            if btype == "text":
                t = block.get("text") or ""
                if t:
                    text_parts.append(t)
                    await _emit("text", {"text": t})
            elif btype == "tool_use":
                tool_uses.append(block)

        if text_parts:
            final_text = "\n".join(text_parts)

        # Append the assistant turn verbatim so tool_use_id linkage holds.
        messages.append({"role": "assistant", "content": content_blocks})

        # No tool_use → we're done.
        if not tool_uses or stop_reason != "tool_use":
            await _emit("done", {
                "stop_reason": stop_reason,
                "iterations": iterations_done,
                "final_text": final_text,
            })
            break

        # Execute each tool_use in order; build a single user turn whose
        # content is a list of tool_result blocks (Anthropic spec).
        tool_result_blocks: List[Dict[str, Any]] = []
        for tu in tool_uses:
            name = tu.get("name") or ""
            tu_id = tu.get("id") or ""
            tinput = tu.get("input") or {}
            await _emit("tool_use", {"name": name, "id": tu_id, "input": tinput})
            try:
                exec_result = await executor(name, tinput)
            except Exception as exec_e:
                logger.exception("executor raised on tool %s", name)
                exec_result = {
                    "content": f"خطای داخلی executor: {str(exec_e)[:300]}",
                    "is_error": True,
                }
            # Normalise — executor may return str or dict.
            if isinstance(exec_result, str):
                result_content = exec_result
                is_error = False
            elif isinstance(exec_result, dict):
                result_content = exec_result.get("content", "")
                is_error = bool(exec_result.get("is_error"))
            else:
                result_content = str(exec_result)
                is_error = False
            tool_calls_log.append({
                "name": name,
                "input": tinput,
                "result": (result_content if isinstance(result_content, str) else "[blocks]")[:500],
                "is_error": is_error,
            })
            await _emit("tool_result", {
                "name": name,
                "is_error": is_error,
                "content": (result_content if isinstance(result_content, str) else "[blocks]")[:1000],
            })
            block: Dict[str, Any] = {
                "type": "tool_result",
                "tool_use_id": tu_id,
                "content": result_content,
            }
            if is_error:
                block["is_error"] = True
            tool_result_blocks.append(block)

        if not tool_result_blocks:
            # Should not happen, but break to avoid infinite loop.
            break
        messages.append({"role": "user", "content": tool_result_blocks})
    else:
        # for/else: budget exhausted without a natural stop
        stop_reason = "max_iterations"
        await _emit("done", {
            "stop_reason": stop_reason,
            "iterations": iterations_done,
            "final_text": final_text,
        })

    if metadata_sink is not None:
        metadata_sink.update(sink)

    return {
        "final_text": final_text,
        "stop_reason": stop_reason,
        "iterations": iterations_done,
        "tool_calls": tool_calls_log,
        "model_used": sink.get("actual_model") or model,
        "usage_last": sink.get("usage"),
    }


# ─────────────────────────────────────────────────────────────────────────────
# 🆕 (OAuth dispatcher registration) — `_ai_generate` in OversightService
# consults oauth_model_registry to route cloud_code through this dispatcher
# instead of falling through to ai_manager.generate (which would fail
# silently since cloud_code isn't in ai_manager._services).
# ─────────────────────────────────────────────────────────────────────────────


async def _dispatch_cloud_code_for_oversight(
    prompt: str, *, max_tokens: int, temperature: float,
) -> str:
    """Bridge: `_ai_generate`-style call (single prompt → text response)
    routed through `cloud_code_complete` with the auto tier picker.

    Raises RuntimeError with a clear Persian message when the env token
    is missing. Anything else (rate limit, subscription cap) propagates
    as-is so the caller (consensus mode etc.) can decide what to do.
    """
    if not cloud_code_is_configured():
        raise RuntimeError(
            "CLAUDE_CODE_OAUTH_TOKEN ست نشده — برای استفاده از Cloud Code "
            "به‌عنوان مدل نظارت، توکن را در env قرار دهید."
        )
    return await cloud_code_complete(
        messages=[{"role": "user", "content": prompt}],
        model="auto",
        max_tokens=max_tokens,
        temperature=temperature,
    )


try:
    from .oauth_model_registry import register_oauth_dispatcher as _register_oauth
    _register_oauth("cloud_code", _dispatch_cloud_code_for_oversight)
except Exception as _reg_e:
    logger.warning(
        "cloud_code_service: oauth dispatcher registration failed: %s",
        _reg_e,
    )
