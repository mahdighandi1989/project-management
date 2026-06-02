# -*- coding: utf-8 -*-
"""
سرویس تبدیل گفتار به متن (Speech-to-Text) برای صداهای ضبط‌شده در
«بازرس ویژه».

به‌جای وابستگی به یک API اختصاصی (Whisper/...) از همان زیرساخت
multimodal موجود (ai_manager + Gemini با کانال inline_files) استفاده
می‌کند که فایل صوتی را با MIME صریح به مدل می‌دهد و transcript کامل
می‌خواهد. مدل پیش‌فرض از `pick_best_extraction_model` انتخاب می‌شود
(کاربر در gemini-2.5-flash تأیید کرده) و با env var قابل بازنویسی است.

محدودیت توکن: عمداً max_tokens بالا انتخاب شده تا transcript کوتاه
نشود (الزام کاربر: «هیچ محدودیت توکنی»).
"""

import base64
import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

# سقف inline برای Gemini ~20MB. فایل‌های بزرگ‌تر باید پیش از این تابع
# chunk شوند (در این نسخه خطا برمی‌گردانیم تا silent truncation نشود).
_INLINE_LIMIT_BYTES = 18 * 1024 * 1024

TRANSCRIPTION_SYSTEM_PROMPT = (
    "تو یک سیستم دقیق تبدیل گفتار به متن (ASR) هستی. فایل صوتی پیوست را "
    "کلمه‌به‌کلمه و کامل به متن تبدیل کن. قواعد:\n"
    "- زبان اصلی گوینده را حفظ کن (فارسی را فارسی بنویس).\n"
    "- چیزی را خلاصه یا حذف نکن؛ تمام جملات را بیاور.\n"
    "- اگر چند گوینده تشخیص دادی، با برچسب «گوینده ۱/۲» جدا کن.\n"
    "- timestamp تقریبی [mm:ss] ابتدای هر پاراگراف را اگر ممکن بود اضافه کن.\n"
    "- فقط متن transcript را خروجی بده، بدون توضیح اضافه یا ```."
)


def _default_model_id() -> str:
    return (os.environ.get("AUDIO_TRANSCRIPTION_MODEL") or "").strip() or "gemini-2.5-flash"


async def transcribe_audio(
    audio_bytes: bytes,
    mime_type: str = "audio/webm",
    *,
    context_hint: str = "",
    model_id: Optional[str] = None,
    max_tokens: int = 32000,
) -> str:
    """تبدیل بایت‌های صوتی به متن.

    خروجی: متن transcript (string). در صورت نبود مدل/کلید مناسب،
    ValueError پرتاب می‌شود تا caller بتواند graceful degrade کند
    (مثلاً فقط با لاگ‌ها و متن تایپ‌شده پرامپت بسازد).
    """
    if not audio_bytes:
        return ""
    if len(audio_bytes) > _INLINE_LIMIT_BYTES:
        raise ValueError(
            f"audio too large for inline transcription ({len(audio_bytes)} bytes). "
            f"حداکثر ~18MB. برای فایل بزرگ‌تر chunking لازم است."
        )

    from .ai_manager import get_ai_manager
    from .ai_base import Message
    from ..core.models_registry import pick_best_extraction_model

    picked_id = (model_id or "").strip() or _default_model_id()
    # تأیید قابلیت AUDIO + در دسترس بودن کلید provider؛ اگر نه، بهترین
    # مدل صوتی enabled را انتخاب کن.
    try:
        best = pick_best_extraction_model(
            mime_type or "audio/webm",
            preferred_model_id=picked_id,
            require_api_key=True,
        )
        if best:
            picked_id = best.id
        elif not (os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")):
            raise ValueError(
                "هیچ مدل صوتی enabled با API key در دسترس نیست "
                "(GEMINI_API_KEY تنظیم نشده)."
            )
    except ValueError:
        raise
    except Exception as e:
        logger.warning(f"transcription model pick fell back to default: {e}")

    b64 = base64.b64encode(audio_bytes).decode("ascii")
    user_text = (
        "متن کامل این فایل صوتی را استخراج کن."
        + (f"\n\nزمینه (برای کمک به املای اصطلاحات فنی): {context_hint[:500]}" if context_hint else "")
        + f"\n\n[فایل صوتی به‌صورت base64 با mime={mime_type}؛ حجم={len(audio_bytes)} bytes]"
    )

    mgr = get_ai_manager()
    messages = [
        Message(role="system", content=TRANSCRIPTION_SYSTEM_PROMPT),
        Message(role="user", content=user_text, inline_files=[(mime_type, b64)]),
    ]
    resp = await mgr.generate(
        model_id=picked_id,
        messages=messages,
        max_tokens=max_tokens,
        temperature=0.1,
        allow_fallback=False,
    )
    return (resp.content or "").strip()
