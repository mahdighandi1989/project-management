"""
🎙 Audio Transcribe Service — تبدیل گفتار به متن با auto-select provider.

این ماژول دقیقاً الگوی `describe_screenshot_with_vision` در
`oversight_inspector_bridge.py` را دنبال می‌کند:
  1) لیست providerهای transcribe ممکن
  2) چک env vars برای کدام provider در دسترس است
  3) اولین در دسترس را انتخاب می‌کند
  4) فراخوانی API می‌کند
  5) اگر هیچ‌کدام پیکربندی نشده، graceful fallback با پیام واضح

Providers پشتیبانی‌شده (به ترتیب اولویت):
  1. Groq Whisper       (env: GROQ_API_KEY)  — سریع و ارزان
  2. OpenAI Whisper     (env: OPENAI_API_KEY)
  (Gemini audio هم پشتیبانی می‌شود ولی فعلاً off — pattern آماده برای
   فعال‌سازی آینده)

استفاده:
  result = await transcribe_audio(audio_bytes, mime_type="audio/webm")
  if result["text"]:
      print(result["text"], result["model_used"])
  else:
      print("transcribe failed:", result["fallback_reason"])
"""
from __future__ import annotations

import io
import logging
import os
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Provider registry — به‌ترتیب اولویت
# هر provider شامل: نام، env key، base URL، model پیش‌فرض
# ─────────────────────────────────────────────────────────────────────────────

PROVIDERS = [
    {
        "name": "groq",
        "env_keys": ["GROQ_API_KEY"],
        "base_url": "https://api.groq.com/openai/v1",
        "model": "whisper-large-v3-turbo",  # سریع‌ترین + ارزان‌ترین
        "fallback_model": "whisper-large-v3",
    },
    {
        "name": "openai",
        "env_keys": ["OPENAI_API_KEY"],
        "base_url": "https://api.openai.com/v1",
        "model": "whisper-1",
        "fallback_model": None,
    },
]

DEFAULT_MAX_DURATION_SEC = 7200  # ۲ ساعت — بیش‌تر از سقف ۶۰ دقیقه‌ای ضبط ما
DEFAULT_TIMEOUT_SEC = 120
MAX_AUDIO_BYTES = 25 * 1024 * 1024  # OpenAI Whisper API limit


# ─────────────────────────────────────────────────────────────────────────────
# Pick provider بر اساس env
# ─────────────────────────────────────────────────────────────────────────────


def _pick_available_provider() -> Optional[Dict[str, Any]]:
    """اولین provider که env key معتبر دارد را برمی‌گرداند."""
    for prov in PROVIDERS:
        for key in prov["env_keys"]:
            val = (os.environ.get(key) or "").strip()
            if val and val.lower() not in ("none", "null", "false"):
                return {**prov, "api_key": val}
    return None


# ─────────────────────────────────────────────────────────────────────────────
# Main entrypoint
# ─────────────────────────────────────────────────────────────────────────────


async def transcribe_audio(
    audio_bytes: bytes,
    *,
    mime_type: str = "audio/webm",
    filename: str = "audio.webm",
    language: Optional[str] = None,  # ISO 639-1 (e.g. "fa", "en") — None برای auto-detect
    prompt_hint: Optional[str] = None,  # رشته‌ای برای راهنمایی الگو/کلمات خاص
    timeout_sec: int = DEFAULT_TIMEOUT_SEC,
) -> Dict[str, Any]:
    """تبدیل audio bytes به متن با اولین provider در دسترس.

    Args:
      audio_bytes: محتوای کامل فایل صوتی (webm/mp3/wav/m4a/ogg)
      mime_type:   نوع MIME — برای انتخاب extension در API
      filename:    نام فایل (برای logs و دیباگ)
      language:    اختیاری — اگر می‌دانیم زبان چیست (fa، en، …)
      prompt_hint: راهنمای کوتاه برای transcriber (مثلاً کلمات تخصصی)
      timeout_sec: حداکثر زمان انتظار

    Returns: dict با کلیدهای زیر (طبق pattern describe_screenshot_with_vision):
      text:            متن transcribed (یا "" در صورت شکست)
      language:        کد زبان شناسایی‌شده (یا "")
      duration_sec:    مدت صوت (یا 0 اگر provider برنگرداند)
      model_used:      نام مدل (مثل "whisper-large-v3-turbo") یا None
      provider:        نام provider (مثل "groq") یا None
      success:         bool
      fallback_reason: در صورت شکست، توضیح برای کاربر/پرامپت
    """
    empty_result = {
        "text": "",
        "language": "",
        "duration_sec": 0.0,
        "model_used": None,
        "provider": None,
        "success": False,
        "fallback_reason": "",
    }

    if not audio_bytes:
        return {**empty_result, "fallback_reason": "audio_bytes خالی است"}

    if len(audio_bytes) > MAX_AUDIO_BYTES:
        return {
            **empty_result,
            "fallback_reason": (
                f"فایل صوتی بزرگ‌تر از سقف ۲۵ MB است "
                f"({len(audio_bytes) / 1024 / 1024:.1f}MB) — قبل از ارسال chunk کنید"
            ),
        }

    provider = _pick_available_provider()
    if provider is None:
        return {
            **empty_result,
            "fallback_reason": (
                "transcript صوت در دسترس نبود — هیچ provider برای transcribe "
                "پیکربندی نشده. می‌توانید GROQ_API_KEY (سریع و رایگان تا حد رایگان) "
                "یا OPENAI_API_KEY در Render environment اضافه کنید."
            ),
        }

    # تمام providerهای موجود OpenAI-compatible هستند → یک code path
    try:
        result = await _transcribe_openai_compatible(
            provider=provider,
            audio_bytes=audio_bytes,
            mime_type=mime_type,
            filename=filename,
            language=language,
            prompt_hint=prompt_hint,
            timeout_sec=timeout_sec,
        )
        logger.info(
            f"transcribe_audio: provider={provider['name']} "
            f"model={provider['model']} chars={len(result.get('text', ''))} "
            f"lang={result.get('language')}"
        )
        return result
    except Exception as e:
        # تلاش با fallback_model اگر provider داشت
        if provider.get("fallback_model"):
            try:
                fallback_prov = {**provider, "model": provider["fallback_model"]}
                logger.warning(
                    f"transcribe primary model {provider['model']} failed ({e}), "
                    f"retrying with fallback {provider['fallback_model']}"
                )
                result = await _transcribe_openai_compatible(
                    provider=fallback_prov,
                    audio_bytes=audio_bytes,
                    mime_type=mime_type,
                    filename=filename,
                    language=language,
                    prompt_hint=prompt_hint,
                    timeout_sec=timeout_sec,
                )
                return result
            except Exception as e2:
                logger.exception(
                    f"transcribe both primary and fallback failed: primary={e}, fallback={e2}"
                )
                return {
                    **empty_result,
                    "provider": provider["name"],
                    "fallback_reason": (
                        f"transcribe با provider {provider['name']} شکست خورد: "
                        f"{str(e2)[:200]}"
                    ),
                }
        logger.exception(f"transcribe failed with provider {provider['name']}")
        return {
            **empty_result,
            "provider": provider["name"],
            "fallback_reason": (
                f"transcribe با provider {provider['name']} شکست خورد: "
                f"{str(e)[:200]}"
            ),
        }


# ─────────────────────────────────────────────────────────────────────────────
# OpenAI-compatible transcription (works for OpenAI + Groq)
# ─────────────────────────────────────────────────────────────────────────────


async def _transcribe_openai_compatible(
    *,
    provider: Dict[str, Any],
    audio_bytes: bytes,
    mime_type: str,
    filename: str,
    language: Optional[str],
    prompt_hint: Optional[str],
    timeout_sec: int,
) -> Dict[str, Any]:
    """فراخوانی API به فرمت OpenAI Whisper (Groq هم همین format را پشتیبانی می‌کند).

    Endpoint: {base_url}/audio/transcriptions
    Method: POST multipart/form-data
    Fields: file, model, [language], [prompt], response_format=verbose_json
    """
    import aiohttp

    url = f"{provider['base_url']}/audio/transcriptions"
    api_key = provider["api_key"]
    model = provider["model"]

    # برای fastapi هم aiohttp مهیا است
    timeout = aiohttp.ClientTimeout(total=timeout_sec)

    # multipart form
    form = aiohttp.FormData()
    form.add_field(
        "file",
        io.BytesIO(audio_bytes),
        filename=filename,
        content_type=mime_type,
    )
    form.add_field("model", model)
    form.add_field("response_format", "verbose_json")
    if language:
        form.add_field("language", language)
    if prompt_hint:
        form.add_field("prompt", prompt_hint[:1000])  # safety cap

    headers = {"Authorization": f"Bearer {api_key}"}

    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.post(url, data=form, headers=headers) as resp:
            text_body = await resp.text()
            if resp.status != 200:
                # log و raise برای catch بالاتر
                logger.warning(
                    f"transcribe API {provider['name']} returned {resp.status}: "
                    f"{text_body[:300]}"
                )
                raise RuntimeError(
                    f"transcribe API status={resp.status}: {text_body[:200]}"
                )
            import json as _json
            data = _json.loads(text_body)
    return {
        "text": (data.get("text") or "").strip(),
        "language": (data.get("language") or "") or (language or ""),
        "duration_sec": float(data.get("duration") or 0.0),
        "model_used": model,
        "provider": provider["name"],
        "success": True,
        "fallback_reason": "",
    }


# ─────────────────────────────────────────────────────────────────────────────
# Helper for callers — formatting transcript with timestamps
# ─────────────────────────────────────────────────────────────────────────────


def format_transcript_with_timestamps(verbose_response: Dict[str, Any]) -> str:
    """اگر provider segments برگرداند (Whisper این کار را می‌کند)، transcript را
    با timestamp فرمت می‌کند. اگر نه، فقط text را برمی‌گرداند.

    این تابع اختیاری است — برای ساخت بخش "🎙 Transcript صوت با timestamp"
    در پرامپت قوی.
    """
    segments = verbose_response.get("segments") or []
    if not segments:
        return verbose_response.get("text", "")
    lines = []
    for seg in segments:
        try:
            start = float(seg.get("start", 0))
            m, s = divmod(int(start), 60)
            ts = f"[{m:02d}:{s:02d}]"
            txt = (seg.get("text") or "").strip()
            if txt:
                lines.append(f"{ts} {txt}")
        except Exception:
            continue
    return "\n".join(lines) or verbose_response.get("text", "")
