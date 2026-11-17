"""Model identity as a FACT the server states (PM-INS-0023, 2026-11-17).

The inspector chat labelled a reply «deepseek-chat» while the text said «Claude 3.5 Sonnet از API ِ رسمیِ Anthropic» — a
model knows nothing about how it is being called and fills the gap with a guess. Every inspector-chat prompt now carries
this note (real model id + provider + route: the provider's API key or a subscription/OAuth token), with the instruction
to answer questions about identity with exactly that. A question that is ONLY about identity gets a light prompt (no repo
context — it used to cost ~12 800 tokens for one line).
"""

from __future__ import annotations

import re
from typing import Optional

_PROVIDER_FA = {
    "openai": "OpenAI", "claude": "Anthropic (Claude)", "gemini": "Google (Gemini)", "deepseek": "DeepSeek",
    "openrouter": "OpenRouter", "groq": "Groq", "perplexity": "Perplexity", "cloud_code": "Anthropic (Claude)",
}


def describe(model_id: str) -> dict:
    mid = (model_id or "").strip()
    base = mid.split(":", 1)[0]
    sub_model = mid.split(":", 1)[1] if ":" in mid else ""
    name, provider = mid, ""
    try:
        from ..core.models_registry import get_model
        m = get_model(base)
        if m is not None:
            name = m.name or mid
            provider = str(getattr(m.provider, "value", m.provider))
    except Exception:  # noqa: BLE001
        pass
    if base == "cloud_code" or provider == "cloud_code":
        route = "اشتراکِ Claude (توکنِ OAuth ِ Claude Code) — نه کلیدِ API"
        provider = "cloud_code"
    elif base.startswith("gemini_oauth") or "oauth" in base:
        route = "اشتراکِ حسابِ Google (OAuth) — نه کلیدِ API"
    else:
        route = f"API ِ {_PROVIDER_FA.get(provider, provider or 'نامشخص')} با کلیدِ API ِ همین برنامه"
    return {"id": mid, "name": name, "provider": provider, "provider_fa": _PROVIDER_FA.get(provider, provider),
            "route": route, "sub_model": sub_model}


def identity_note(model_id: str) -> str:
    d = describe(model_id)
    who = d["sub_model"] or d["id"]
    return (
        "## هویتِ تو (واقعیت — سرور تعیین کرده)\n"
        f"- این پاسخ را مدلِ «{d['name']}» با شناسهٔ `{who}` می‌دهد؛ سازنده/provider: {d['provider_fa'] or d['provider']}.\n"
        f"- مسیرِ فراخوانی: {d['route']}؛ از طریقِ برنامهٔ AI Creator.\n"
        "- اگر دربارهٔ هویت، مدل، نسخه یا مسیرت پرسیدند **فقط همین را بگو**؛ نامِ مدل یا نسخهٔ دیگری را حدس نزن و نگو "
        "(نه «Claude 3.5 Sonnet»، نه «GPT-4»، مگر همین بالا آمده باشد).\n"
    )


_IDENTITY_Q = re.compile(
    r"(چه|کدام|کدوم)\s*(مدل|هوش)|با\s*چه\s*مدل|مدلت|مدلِ\s*تو|تو\s*(کی|چی)\s*هستی|از\s*چه\s*مسیر|"
    r"which\s+model|what\s+model|who\s+are\s+you|what\s+are\s+you|your\s+model|model\s+are\s+you",
    re.I,
)


def is_identity_question(text: str) -> bool:
    """Short and about the model itself (not «which model should I use for X» inside a long request)."""
    t = (text or "").strip()
    return bool(t) and len(t) <= 160 and bool(_IDENTITY_Q.search(t))
