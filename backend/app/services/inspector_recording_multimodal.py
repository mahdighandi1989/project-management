"""
🎬🎙 Multimodal Recording Analyzer — یک call واحد به مدل multimodal
(مثل Gemini Flash 2.5) برای استخراج هم‌زمان transcript صوت + visual
analysis + intent extraction.

این روش بهتر از pipeline جداگانه است (Whisper جدا + vision per frame)
چون:
  - یک مدل صدا و تصویر را با هم می‌فهمد (همگام‌سازی بهتر)
  - timing بین صدا و آنچه روی صفحه می‌بیند طبیعی است
  - intent extraction از combination کامل صحیح‌تر است
  - کاربر صریحاً درخواست کرد: «همون مدلی که دیباگ بصری انجام میده خودش
    کار صوتی هم انجام بده ... پس نباید جداش کنی ... این باعث اختلال میشه»

استفاده از همان مکانیزم describe_screenshot_with_vision در زیرلایه:
  - auto-select model با AUDIO_UNDERSTANDING capability
  - استفاده از Message.inline_files برای audio (existing field)
  - استفاده از Message.images برای frames

اگر هیچ مدل multimodal با audio support در دسترس نبود (مثل وقتی فقط OpenAI
یا Claude config است که visual-only هستند)، graceful fallback به legacy
pipeline (audio_transcribe + describe_screenshot_with_vision per frame).
"""
from __future__ import annotations

import base64
import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# Gemini inline limit ~20MB total payload. ما 16MB را cap قرار می‌دهیم تا
# جای prompt + overhead باقی بماند.
MAX_INLINE_PAYLOAD_BYTES = 16 * 1024 * 1024
# هر تصویر منفرد در Gemini تا 7MB قابل قبول است، ولی برای ما 4MB کافی است
MAX_PER_IMAGE_BYTES = 4 * 1024 * 1024
# هر فایل صوتی تا 9.5MB inline (Gemini limit). برای ما 12MB cap هم OK است
MAX_AUDIO_BYTES = 12 * 1024 * 1024
# حداکثر تعداد keyframe در یک call
MAX_KEYFRAMES = 10


# ─────────────────────────────────────────────────────────────────────────────
# Model selection — مدل multimodal با audio support
# ─────────────────────────────────────────────────────────────────────────────


def _pick_multimodal_audio_model():
    """اولین مدل enabled با AUDIO_UNDERSTANDING که env key دارد را برمی‌گرداند.

    در حال حاضر این عمدتاً Gemini 2.5 Flash / 2.0 Flash هست.
    اگر در آینده OpenAI GPT-4o audio یا Claude با audio اضافه شد، خودکار
    پشتیبانی می‌شود (چون از capabilities استفاده می‌کنیم).
    """
    try:
        from ..core.models_registry import (
            get_enabled_models, ModelCapability,
        )
    except Exception as e:
        logger.warning(f"models_registry import failed: {e}")
        return None

    enabled = get_enabled_models() or []

    # env keys per provider
    env_keys = {
        "openai": ["OPENAI_API_KEY"],
        "claude": ["ANTHROPIC_API_KEY", "CLAUDE_API_KEY"],
        "anthropic": ["ANTHROPIC_API_KEY", "CLAUDE_API_KEY"],
        "gemini": ["GEMINI_API_KEY", "GOOGLE_API_KEY"],
        "google": ["GEMINI_API_KEY", "GOOGLE_API_KEY"],
    }
    with_key = set()
    for p, ks in env_keys.items():
        if any((os.environ.get(k) or "").strip() for k in ks):
            with_key.add(p.lower())

    # ترجیح: Gemini (تنها provider که full audio understanding دارد)
    candidates = []
    for m in enabled:
        try:
            caps = m.capabilities or []
            if ModelCapability.AUDIO_UNDERSTANDING not in caps:
                continue
            prov = m.provider
            prov_str = (prov.value if hasattr(prov, "value") else str(prov)).lower()
            if prov_str not in with_key:
                continue
            candidates.append(m)
        except Exception:
            continue

    if not candidates:
        return None

    # اولویت 1: Gemini 2.5 Flash (پایین‌ترین cost + سریع‌ترین)
    # اولویت 2: Gemini 2.5 Pro
    # اولویت 3: هر مدل دیگر با AUDIO_UNDERSTANDING
    preference_order = ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-2.5-pro"]
    for pref_id in preference_order:
        for m in candidates:
            if m.id == pref_id:
                return m
    # fallback: اولین مدل با priority پایین
    candidates.sort(key=lambda m: getattr(m, "priority", 99))
    return candidates[0] if candidates else None


# ─────────────────────────────────────────────────────────────────────────────
# Read media as base64
# ─────────────────────────────────────────────────────────────────────────────


def _read_keyframes_base64(session, max_count: int = MAX_KEYFRAMES) -> List[Tuple[str, str, int]]:
    """keyframes را به‌صورت (mime, b64, size_bytes) برمی‌گرداند با sampling مساوی."""
    from .inspector_recording_processor import _pick_keyframes

    keyframes = _pick_keyframes(session.frames_dir, target_count=max_count, max_count=max_count)
    out: List[Tuple[str, str, int]] = []
    for fp in keyframes:
        try:
            data = fp.read_bytes()
            if len(data) > MAX_PER_IMAGE_BYTES:
                # skip فریم خیلی بزرگ
                logger.debug(f"skip oversized frame {fp.name} ({len(data)}B)")
                continue
            b64 = base64.b64encode(data).decode("ascii")
            mime = "image/png" if fp.suffix.lower() == ".png" else "image/jpeg"
            out.append((mime, b64, len(data)))
        except Exception as e:
            logger.warning(f"failed to read keyframe {fp.name}: {e}")
    return out


def _read_audio_base64(session) -> Optional[Tuple[str, str, int]]:
    """audio assembled bytes را به base64 برمی‌گرداند (mime, b64, size_bytes)."""
    from .inspector_recording_processor import _assemble_audio

    audio = _assemble_audio(session.audio_dir)
    if audio is None or len(audio) < 1024:
        return None
    if len(audio) > MAX_AUDIO_BYTES:
        logger.info(
            f"audio too large ({len(audio)}B > {MAX_AUDIO_BYTES}B) — "
            f"multimodal inline rejects, will fallback"
        )
        return None
    b64 = base64.b64encode(audio).decode("ascii")
    return ("audio/webm", b64, len(audio))


def _read_video_base64(session) -> Optional[Tuple[str, str, int]]:
    """video assembled bytes را به base64 برمی‌گرداند (mode B)."""
    from .inspector_recording_finalize import _assemble_video_from_chunks

    video = _assemble_video_from_chunks(session.video_dir)
    if video is None:
        return None
    if len(video) > MAX_INLINE_PAYLOAD_BYTES // 2:
        logger.info(
            f"video too large ({len(video)}B) for inline multimodal — will fallback"
        )
        return None
    b64 = base64.b64encode(video).decode("ascii")
    return ("video/webm", b64, len(video))


# ─────────────────────────────────────────────────────────────────────────────
# System prompts for unified output
# ─────────────────────────────────────────────────────────────────────────────


def _build_multimodal_prompt(
    *,
    mode: str,
    user_note: str,
    project_full_name: str,
) -> str:
    """system prompt برای استخراج هم‌زمان transcript + visual + (mode B) location.

    خروجی JSON خالص.
    """
    repo_hint = project_full_name or "(پروژهٔ inspector)"

    base = f"""تو یک تحلیل‌گر چندرسانه‌ای دقیق هستی. کاربر یک ضبط از تب «بازرس ویژه»
گرفته که شامل:
- صدای کاربر در حال توضیح آنچه می‌بیند یا می‌خواهد
- {'فریم‌های متعدد از iframe پروژه (پروژه: ' + repo_hint + ')' if mode == 'A' else 'ویدئوی آزاد چندصفحه‌ای (پروژهٔ مرجع: ' + repo_hint + ')'}

{('یادداشت اولیه کاربر: ' + user_note.strip()[:500]) if user_note else 'یادداشت اولیه: (خالی)'}

**وظیفه:** خروجی unified JSON برای یک agent دیگر بساز که هم transcript صدا،
هم تحلیل بصری، هم intent استخراج‌شده را همراه با timestamp ها داشته باشد.

⚠️ نکات حیاتی:
- صدا را با تصاویر **هم‌زمان** تحلیل کن — وقتی کاربر می‌گوید «این رو ببین»،
  آن چیزی که در همان لحظه روی صفحه است را در توضیح ذکر کن.
- **استخراج intent** مهم‌تر از transcribe خام است: بفهم «دقیقاً چه می‌گوید،
  چه می‌خواهد، چه را رد می‌کند، کجاها منظورش است».
"""

    if mode == "A":
        base += f"""
- کاربر در iframe پروژهٔ '{repo_hint}' بوده. اگر در صدا به چیزی **خارج از این
  پروژه/iframe** اشاره کرد (مثلاً «اون تب IMDB رو ببین»)، در پرامپت لحاظ
  **نکن**. این یک قاعدهٔ مطلق است.
"""
    else:  # mode B
        base += f"""
- ضبط آزاد است: کاربر بین چند تب کروم، برنامه‌های دیگر دسکتاپ، یا دسکتاپ
  خام جابجا شده. در هر مقطع تشخیص بده کاربر کجاست (chrome_tab / other_app
  / desktop) و آیا مرتبط با پروژهٔ '{repo_hint}' است.
- اگر کاربر به جایی **خارج از پروژه** رفت ولی در صدا **به آن اشاره نکرد**،
  در پرامپت لحاظ نکن (بی‌ربط).
- اگر به جایی خارج رفت **و در صدا به آن اشاره کرد** (مثل «این UI رو
  می‌خوام مثل این بسازم»)، آن را به‌عنوان **مرجع/الهام** نگه دار.
"""

    output_schema = """
**خروجی فقط JSON خالص** (بدون ``` یا توضیح اضافی). ساختار:

```
{
  "transcript": "متن کامل صدا با timestamp در ابتدای هر بخش، مثلاً '[00:00] ... [00:15] ...'",
  "transcript_language": "fa | en | ...",
  "intent_extracted": "یک پاراگراف: کاربر دقیقاً چه می‌خواهد، چه می‌گوید، چه را رد می‌کند",
  "visual_summary": [
    {
      "timestamp_ms": <int approximate ms>,
      "scene": "توصیف کلی صحنه در ۲-۳ جمله — فقط چیزی که می‌بینی",
      "ocr_text": "متن قابل مشاهده در فریم (همه کلمات، دکمه‌ها)",
      "ui_elements": "لیست عناصر UI (دکمه، فرم، nav، panel)",
      "error_signals": "هر نشانه خطا/warning/state غیرعادی روی صفحه",
      "user_voice_at_this_moment": "اگر در همین مقطع زمانی صدا چیزی گفته، اینجا نقل کن"
    },
    ...
  ],
"""

    if mode == "B":
        output_schema += """  "location_timeline": [
    {
      "ts_ms": <int>,
      "category": "chrome_tab | other_app | desktop",
      "url_or_app_name": "string — URL کامل (chrome_tab) یا نام برنامه",
      "related_to_project": true | false,
      "activity_description": "یک جمله — چه می‌کند",
      "user_referenced_in_voice": true | false
    },
    ...
  ],
"""

    output_schema += """  "key_references": ["لیست URL/فایل/کامپوننت که AI تشخیص داد مرتبط هستند"],
  "important_log_signals": ["هر errors یا warnings مرتبط که از روی صفحه دیدی"]
}
```

اگر transcript کم است (صدا کم بود یا کاربر کم حرف زد)، فیلد transcript را
کوتاه و دقیق نگه دار. اگر visual frames خیلی شبیه هم بودند، می‌توانی
visual_summary را خلاصه (مثلاً ۳-۴ آیتم) بدهی.

اطمینان حاصل کن که خروجی JSON valid است (بدون trailing comma، با escape
صحیح quotes درون strings)."""

    return base + output_schema


# ─────────────────────────────────────────────────────────────────────────────
# Main entry
# ─────────────────────────────────────────────────────────────────────────────


async def analyze_recording_multimodal(
    session,
    *,
    user_note: str = "",
) -> Dict[str, Any]:
    """analyze full recording (audio + visual + location for mode B) با یک call
    multimodal به Gemini (یا هر مدل دیگر با AUDIO_UNDERSTANDING).

    Returns:
      {
        "success": bool,
        "transcript": str,
        "transcript_language": str,
        "intent_extracted": str,
        "visual_summary": List[Dict],
        "location_timeline": List[Dict] (mode B only),
        "key_references": List[str],
        "important_log_signals": List[str],
        "model_used": str,
        "provider": str,
        "fallback_reason": str,  # empty if success
      }
    """
    empty: Dict[str, Any] = {
        "success": False,
        "transcript": "",
        "transcript_language": "",
        "intent_extracted": "",
        "visual_summary": [],
        "location_timeline": [],
        "key_references": [],
        "important_log_signals": [],
        "model_used": None,
        "provider": None,
        "fallback_reason": "",
    }

    # Step 1: pick model
    model = _pick_multimodal_audio_model()
    if model is None:
        return {
            **empty,
            "fallback_reason": (
                "هیچ مدل multimodal با audio understanding پیکربندی نشده. "
                "برای دریافت آنالیز یکپارچه، GEMINI_API_KEY اضافه کنید. "
                "در غیر این صورت pipeline قدیمی (Whisper جدا + vision per frame) "
                "استفاده می‌شود."
            ),
        }

    # Step 2: media جمع‌آوری کن
    audio = _read_audio_base64(session)
    media_items: List[Tuple[str, str]] = []  # (mime, b64)

    if audio:
        media_items.append((audio[0], audio[1]))

    if session.mode == "A":
        # frames به‌عنوان images
        frames = _read_keyframes_base64(session, max_count=MAX_KEYFRAMES)
        # cumulative size cap
        total = sum(s for _, _, s in frames) + (audio[2] if audio else 0)
        kept_frames: List[Tuple[str, str]] = []
        for mime, b64, size in frames:
            if total > MAX_INLINE_PAYLOAD_BYTES:
                logger.info(
                    f"multimodal payload would exceed cap "
                    f"({total} > {MAX_INLINE_PAYLOAD_BYTES}) — dropping later frames"
                )
                break
            kept_frames.append((mime, b64))
        if not kept_frames and not audio:
            return {
                **empty,
                "fallback_reason": "هیچ media برای آنالیز نبود (frames خالی + audio خالی)",
            }
        images_b64 = [b64 for _, b64 in kept_frames]
        # frames به‌صورت inline_files با MIME صریح (برای ضمانت)
        # ولی Message.images هم کار می‌کند (Gemini از prefix base64 MIME را
        # تشخیص می‌دهد). برای دقت بیشتر در inline_files قرار می‌دهیم.
        inline_files: List[Tuple[str, str]] = []
        if audio:
            inline_files.append((audio[0], audio[1]))
    else:  # mode B
        # ترجیح video file (شامل audio embedded)
        video = _read_video_base64(session)
        if video is None:
            # fallback: keyframes از frames_dir + audio جدا (frames معمولاً در
            # mode B خالی است چون frontend از video extract می‌کند)
            frames = _read_keyframes_base64(session, max_count=MAX_KEYFRAMES)
            if not frames and not audio:
                return {
                    **empty,
                    "fallback_reason": (
                        "حالت B: video chunks یا خیلی بزرگ بودند یا خالی، و keyframe جداگانه "
                        "هم extract نشده. legacy pipeline استفاده شود."
                    ),
                }
            images_b64 = [b64 for _, b64, _ in frames[:MAX_KEYFRAMES]]
            inline_files = []
            if audio:
                inline_files.append((audio[0], audio[1]))
        else:
            # video inline — Gemini خودش audio و visual را extract می‌کند
            images_b64 = []
            inline_files = [(video[0], video[1])]
            if audio and video[2] + audio[2] < MAX_INLINE_PAYLOAD_BYTES:
                # اگر audio جداگانه هم هست (mic لوکال در سمت client)، اضافه کن
                # — Gemini می‌تواند چند audio track را با هم پردازش کند
                inline_files.append((audio[0], audio[1]))

    # Step 3: build prompt + message
    prompt_text = _build_multimodal_prompt(
        mode=session.mode,
        user_note=user_note,
        project_full_name=session.project_full_name or "",
    )

    try:
        from .ai_manager import get_ai_manager
        from .ai_base import Message
    except Exception as e:
        return {**empty, "fallback_reason": f"AI imports failed: {e}"}

    msg = Message(
        role="user",
        content=prompt_text,
        images=images_b64 or None,
        inline_files=inline_files or None,
    )

    # Step 4: call AI manager
    ai_mgr = get_ai_manager()
    try:
        response = await ai_mgr.generate(
            model_id=model.id,
            messages=[msg],
            max_tokens=8000,
            temperature=0.2,
        )
        raw_text = (response.content or "").strip()
        if not raw_text:
            return {**empty, "fallback_reason": "AI returned empty content"}
    except Exception as e:
        logger.exception(f"multimodal analyze with {model.id} failed: {e}")
        return {**empty, "fallback_reason": f"multimodal call failed: {str(e)[:200]}"}

    # Step 5: parse JSON
    parsed = _parse_unified_output(raw_text)
    if parsed is None:
        return {
            **empty,
            "model_used": model.id,
            "fallback_reason": "AI خروجی JSON قابل پارس نداد",
        }

    # Step 6: structure result
    return {
        "success": True,
        "transcript": str(parsed.get("transcript", "") or "")[:500_000],
        "transcript_language": str(parsed.get("transcript_language", "") or "")[:20],
        "intent_extracted": str(parsed.get("intent_extracted", "") or "")[:5000],
        "visual_summary": _normalize_visual_summary(parsed.get("visual_summary", [])),
        "location_timeline": _normalize_location_timeline(parsed.get("location_timeline", []))
        if session.mode == "B"
        else [],
        "key_references": _normalize_str_list(parsed.get("key_references", []))[:50],
        "important_log_signals": _normalize_str_list(parsed.get("important_log_signals", []))[:50],
        "model_used": model.id,
        "provider": (model.provider.value if hasattr(model.provider, "value") else str(model.provider)),
        "fallback_reason": "",
    }


# ─────────────────────────────────────────────────────────────────────────────
# Parsing helpers
# ─────────────────────────────────────────────────────────────────────────────


def _parse_unified_output(text: str) -> Optional[Dict[str, Any]]:
    """JSON رو parse می‌کند — با cleanup برای ``` و text قبل/بعد."""
    if not text:
        return None
    cleaned = text.strip()
    if cleaned.startswith("```"):
        # حذف ``` lang line + ``` پایانی
        cleaned = cleaned.split("\n", 1)[-1]
        if "```" in cleaned:
            cleaned = cleaned.rsplit("```", 1)[0].strip()
    # پیدا کردن { تا } اصلی
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start == -1 or end <= start:
        return None
    try:
        return json.loads(cleaned[start:end + 1])
    except json.JSONDecodeError as e:
        logger.warning(f"multimodal JSON parse failed: {e}; first 300 chars: {cleaned[:300]}")
        return None


def _normalize_visual_summary(items: Any) -> List[Dict[str, Any]]:
    if not isinstance(items, list):
        return []
    out: List[Dict[str, Any]] = []
    for it in items[:30]:
        if not isinstance(it, dict):
            continue
        out.append({
            "timestamp_ms": int(it.get("timestamp_ms") or it.get("ts_ms") or 0),
            "scene": str(it.get("scene") or "")[:1500],
            "ocr_text": str(it.get("ocr_text") or "")[:3000],
            "ui_elements": str(it.get("ui_elements") or "")[:1500],
            "error_signals": str(it.get("error_signals") or "")[:800],
            "user_voice_at_this_moment": str(
                it.get("user_voice_at_this_moment") or ""
            )[:600],
        })
    return out


def _normalize_location_timeline(items: Any) -> List[Dict[str, Any]]:
    if not isinstance(items, list):
        return []
    out: List[Dict[str, Any]] = []
    for it in items[:50]:
        if not isinstance(it, dict):
            continue
        cat = str(it.get("category") or "unknown").strip().lower()
        if cat not in ("chrome_tab", "other_app", "desktop", "unknown"):
            cat = "unknown"
        out.append({
            "ts_ms": int(it.get("ts_ms") or it.get("timestamp_ms") or 0),
            "category": cat,
            "url_or_app_name": str(it.get("url_or_app_name") or "")[:500],
            "related_to_project": bool(it.get("related_to_project", False)),
            "activity_description": str(it.get("activity_description") or "")[:500],
            "user_referenced_in_voice": bool(it.get("user_referenced_in_voice", False)),
        })
    return out


def _normalize_str_list(items: Any) -> List[str]:
    if not isinstance(items, list):
        return []
    return [str(x)[:500] for x in items if x]
