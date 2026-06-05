"""
🎬 Inspector Recording Processor — pipeline پردازش پس از stop.

ورودی: یک RecordingSession با فایل‌های frames/audio/interactions ذخیره‌شده
خروجی: session.transcript, session.visual_summary, session.prompt پر می‌شوند

Stages:
  1. assemble audio   → یک فایل واحد از audio_chunks/
  2. transcribe       → audio_transcribe.transcribe_audio()
  3. pick keyframes   → 6-12 frame از frames/ (mode A) یا extract از video (mode B)
  4. vision per frame → describe_screenshot_with_vision() (parallel)
  5. fetch logs       → /api/render/logs برای آن watched + console logs از payload
  6. synthesize       → AI text model با system prompt اختصاصی
  7. assemble final   → ساختار section 4.5 طراحی + ذخیره در session.prompt

این ماژول stateless است — همه state در RecordingSession.
"""
from __future__ import annotations

import asyncio
import json
import logging
import math
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Stage helpers
# ─────────────────────────────────────────────────────────────────────────────


def _assemble_audio(audio_dir: Path) -> Optional[bytes]:
    """تمام audio chunks را پشت سر هم concat می‌کند. webm clusters متوالی
    در یک فایل به‌صورت native قابل پخش هستند، پس به ffmpeg نیاز نداریم.
    """
    if not audio_dir.exists():
        return None
    chunks = sorted(audio_dir.glob("chunk_*.webm"))
    if not chunks:
        return None
    parts: List[bytes] = []
    for c in chunks:
        try:
            parts.append(c.read_bytes())
        except Exception as e:
            logger.warning(f"failed to read audio chunk {c.name}: {e}")
    if not parts:
        return None
    return b"".join(parts)


def _pick_keyframes(
    frames_dir: Path, target_count: int = 8, min_count: int = 6, max_count: int = 12
) -> List[Path]:
    """N keyframe با فاصله مساوی از frames موجود انتخاب می‌کند.

    اگر کل frames کمتر از min_count باشد، همه را برمی‌گرداند.
    """
    if not frames_dir.exists():
        return []
    all_frames = sorted(frames_dir.glob("frame_*.png")) + sorted(frames_dir.glob("frame_*.jpg"))
    n = len(all_frames)
    if n == 0:
        return []
    if n <= min_count:
        return all_frames
    pick_n = max(min_count, min(target_count, max_count, n))
    # spaced sampling: indexها در فاصله مساوی
    step = (n - 1) / (pick_n - 1) if pick_n > 1 else 1
    indices = [int(round(i * step)) for i in range(pick_n)]
    return [all_frames[i] for i in indices]


def _read_image_base64(path: Path) -> str:
    import base64
    data = path.read_bytes()
    return base64.b64encode(data).decode("ascii")


def _format_timestamp(ms: int) -> str:
    s = ms // 1000
    m, s = divmod(s, 60)
    return f"[{m:02d}:{s:02d}]"


# ─────────────────────────────────────────────────────────────────────────────
# Stage 1+2: Audio + Transcribe
# ─────────────────────────────────────────────────────────────────────────────


async def stage_transcribe(session) -> Dict[str, Any]:
    """audio chunks را assemble و transcribe می‌کند.

    Returns:
      {text, language, duration_sec, model_used, provider, success, fallback_reason}
    """
    audio_bytes = _assemble_audio(session.audio_dir)
    if audio_bytes is None or len(audio_bytes) < 1024:  # <1KB = empty
        return {
            "text": "",
            "language": "",
            "duration_sec": 0.0,
            "model_used": None,
            "provider": None,
            "success": False,
            "fallback_reason": "هیچ chunk صدای معتبری دریافت نشد",
        }
    from .audio_transcribe import transcribe_audio
    return await transcribe_audio(audio_bytes, mime_type="audio/webm", filename="recording.webm")


# ─────────────────────────────────────────────────────────────────────────────
# Stage 3+4: Vision per keyframe
# ─────────────────────────────────────────────────────────────────────────────


async def stage_vision(session) -> List[Dict[str, Any]]:
    """vision را روی keyframeهای انتخاب‌شده اجرا می‌کند (parallel).

    در حالت A: page_url = URL واقعی iframe (در recording_metadata)
    در حالت B: page_url = "" چون چندصفحه‌ای است

    Returns: لیست {timestamp_ms, frame_path, scene, ocr_text, ui_elements,
                  error_signals, layout_hints, vision_model_used, …}
    """
    keyframes = _pick_keyframes(session.frames_dir)
    if not keyframes:
        return []

    from .oversight_inspector_bridge import describe_screenshot_with_vision

    duration_ms = int(session.duration_sec() * 1000)
    n = len(keyframes)
    # timestamp تقریبی هر keyframe بر اساس index و duration کل
    timestamps = [int(i * duration_ms / max(1, n - 1)) for i in range(n)]

    # user_context: راهنمای کوتاه برای vision
    user_context = (
        f"این یک فریم از ضبط در تب بازرس ویژه است "
        f"(حالت {session.mode}، پروژه {session.project_full_name or session.project_id}). "
        "محتوای صفحه را با ocr_text و ui_elements توصیف کن. اگر خطایی روی صفحه دیده "
        "می‌شود در error_signals بنویس."
    )
    page_url_hint = ""
    if session.mode == "A":
        # برای حالت A این بعداً از recording_metadata پر می‌شود
        page_url_hint = ""  # اختیاری

    async def _analyze_one(idx: int, frame_path: Path) -> Dict[str, Any]:
        try:
            b64 = _read_image_base64(frame_path)
            result = await describe_screenshot_with_vision(
                base64_img=b64,
                user_context=user_context,
                page_url=page_url_hint,
                dom_text="",
            )
            return {
                "timestamp_ms": timestamps[idx],
                "frame_path": str(frame_path.name),
                **result,
            }
        except Exception as e:
            logger.warning(f"vision failed for {frame_path.name}: {e}")
            return {
                "timestamp_ms": timestamps[idx],
                "frame_path": str(frame_path.name),
                "scene": f"(vision call failed: {str(e)[:120]})",
                "ocr_text": "",
                "ui_elements": "",
                "error_signals": "",
                "layout_hints": "",
                "vision_model_used": None,
            }

    # parallel با gather — limit نداریم چون keyframeها حداکثر ۱۲ تاست
    tasks = [_analyze_one(i, fp) for i, fp in enumerate(keyframes)]
    results = await asyncio.gather(*tasks, return_exceptions=False)
    return results


# ─────────────────────────────────────────────────────────────────────────────
# Stage 4b: Location classifier — فقط برای حالت B
# تشخیص chrome_tab / other_app / desktop + related_to_project
# ─────────────────────────────────────────────────────────────────────────────


def _build_location_classifier_prompt(project_full_name: str) -> str:
    """system prompt مخصوص تشخیص محل برای حالت B."""
    repo_hint = project_full_name or "(پروژهٔ inspector)"
    return f"""این یک فریم از ضبط آزاد چندصفحه‌ای است. ضبط یک کاربر در حال
inspect پروژه‌ی '{repo_hint}' است ولی ممکن است بین صفحات/برنامه‌های مختلف
جابجا شود. تشخیص بده در این فریم کاربر دقیقاً کجاست.

سه دستهٔ ممکن:

1. **chrome_tab** — اگر نوار آدرس مرورگر در فریم دیده می‌شود (URL/domain)
2. **other_app** — اگر یک پنجرهٔ برنامه دیگر دیده می‌شود (IDE، Slack، Terminal،
   FileManager، …) با title bar یا UI خاص
3. **desktop** — اگر فقط دسکتاپ خام دیده می‌شود (icons + wallpaper، یا
   جابجایی پنجره‌ها)

برای دستهٔ chrome_tab، URL را از نوار آدرس استخراج کن. اگر domain یا path
شامل '{repo_hint}' یا 'render.com' / 'onrender.com' است → related_to_project=true،
وگرنه → false.

برای دستهٔ other_app، نام برنامه را تشخیص بده. اگر در پنجره فایل‌های پروژه
(مثل '{repo_hint}.py' یا نام‌های مشابه) دیده می‌شود → related_to_project=true.

برای دستهٔ desktop، related_to_project=false.

همچنین activity کاربر را در یک جمله توصیف کن (مثلاً «در حال خواندن
ReadMe در github» یا «در حال ویرایش auth.py در VS Code»).

خروجی فقط JSON خالص (بدون ``` یا توضیح اضافی):
{{
  "category": "chrome_tab" | "other_app" | "desktop",
  "url_or_app_name": "string — URL کامل یا نام برنامه",
  "related_to_project": true | false,
  "activity_description": "یک جمله — چه می‌کند",
  "confidence": 0.0 to 1.0
}}

اگر مطمئن نیستی، confidence پایین بده ولی همیشه یک category انتخاب کن."""


async def _call_vision_with_custom_prompt(
    base64_img: str, prompt_text: str, max_tokens: int = 800
) -> Dict[str, Any]:
    """vision call با system prompt اختصاصی — همان pattern auto-select از
    describe_screenshot_with_vision (بدون modify کردن آن تابع).
    """
    from .ai_manager import get_ai_manager
    from .ai_base import Message
    from ..core.models_registry import get_vision_models
    import os as _os

    vision_models = get_vision_models() or []
    env_keys = {
        "openai": ["OPENAI_API_KEY"],
        "claude": ["ANTHROPIC_API_KEY", "CLAUDE_API_KEY"],
        "anthropic": ["ANTHROPIC_API_KEY", "CLAUDE_API_KEY"],
        "gemini": ["GEMINI_API_KEY", "GOOGLE_API_KEY"],
        "google": ["GEMINI_API_KEY", "GOOGLE_API_KEY"],
        # 🆕 cloud_code supports image content blocks via the OAuth API
        "cloud_code": ["CLAUDE_CODE_OAUTH_TOKEN"],
    }
    with_key = set()
    for p, ks in env_keys.items():
        if any((_os.environ.get(k) or "").strip() for k in ks):
            with_key.add(p.lower())

    picked = None
    for m in vision_models:
        prov = m.provider
        prov_str = (prov.value if hasattr(prov, "value") else str(prov)).lower()
        if prov_str in with_key:
            picked = m
            break

    if not picked:
        return {
            "category": "unknown",
            "url_or_app_name": "",
            "related_to_project": False,
            "activity_description": "(vision model در دسترس نیست)",
            "confidence": 0.0,
        }

    ai_mgr = get_ai_manager()
    msg = Message(role="user", content=prompt_text, images=[base64_img])
    try:
        response = await ai_mgr.generate(
            model_id=picked.id,
            messages=[msg],
            max_tokens=max_tokens,
            temperature=0.1,  # خیلی پایین برای classification
        )
        txt = (response.content or "").strip()
        if txt.startswith("```"):
            txt = txt.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
        start = txt.find("{")
        end = txt.rfind("}")
        if start != -1 and end > start:
            try:
                parsed = json.loads(txt[start:end + 1])
                cat = str(parsed.get("category", "unknown")).strip().lower()
                if cat not in ("chrome_tab", "other_app", "desktop"):
                    cat = "unknown"
                return {
                    "category": cat,
                    "url_or_app_name": str(parsed.get("url_or_app_name", ""))[:300],
                    "related_to_project": bool(parsed.get("related_to_project", False)),
                    "activity_description": str(parsed.get("activity_description", ""))[:300],
                    "confidence": float(parsed.get("confidence", 0.5)),
                    "vision_model_used": picked.id,
                }
            except Exception as _je:
                logger.debug(f"classify_location: JSON parse failed: {_je}")
        # JSON parse fail
        return {
            "category": "unknown",
            "url_or_app_name": "",
            "related_to_project": False,
            "activity_description": txt[:300],
            "confidence": 0.3,
            "vision_model_used": picked.id,
        }
    except Exception as e:
        logger.warning(f"classify_location vision call failed: {e}")
        return {
            "category": "unknown",
            "url_or_app_name": "",
            "related_to_project": False,
            "activity_description": f"(error: {str(e)[:120]})",
            "confidence": 0.0,
        }


async def stage_location_timeline(session) -> List[Dict[str, Any]]:
    """فقط برای حالت B — تحلیل location هر keyframe.

    Returns: لیست {ts_ms, category, url_or_app_name, related_to_project,
                  activity_description, confidence}
    """
    if session.mode != "B":
        return []
    keyframes = _pick_keyframes(session.frames_dir, target_count=12)
    # در حالت B، frontend احتمالاً frames را در /frame upload نمی‌کند بلکه
    # video chunks می‌فرستد. اگر frames خالی است، از video chunks
    # extract نمی‌کنیم در commit 4 (نیازمند ffmpeg). در commit 5/6 frontend
    # یا keyframes را خودش extract می‌کند و آپلود می‌کند، یا ffmpeg در
    # backend اضافه می‌شود.
    if not keyframes:
        # video_dir را چک می‌کنیم — اگر chunk هست، یک placeholder timeline
        # برمی‌گردانیم تا synthesis بداند اطلاعات ناقص است
        if session.video_dir.exists() and any(session.video_dir.iterdir()):
            return [{
                "ts_ms": 0,
                "category": "unknown",
                "url_or_app_name": "",
                "related_to_project": False,
                "activity_description": (
                    "(keyframes برای حالت B از frontend extract نشده — "
                    "video chunks موجود است ولی frame extraction در commit 6 "
                    "اضافه می‌شود. در این فاز فقط transcript + interactions "
                    "برای synthesis استفاده می‌شود.)"
                ),
                "confidence": 0.0,
            }]
        return []

    duration_ms = int(session.duration_sec() * 1000)
    n = len(keyframes)
    timestamps = [int(i * duration_ms / max(1, n - 1)) for i in range(n)]
    classifier_prompt = _build_location_classifier_prompt(
        session.project_full_name or ""
    )

    async def _classify_one(idx: int, fp: Path) -> Dict[str, Any]:
        b64 = _read_image_base64(fp)
        result = await _call_vision_with_custom_prompt(b64, classifier_prompt)
        result["ts_ms"] = timestamps[idx]
        result["frame_path"] = str(fp.name)
        return result

    tasks = [_classify_one(i, fp) for i, fp in enumerate(keyframes)]
    return await asyncio.gather(*tasks, return_exceptions=False)


# ─────────────────────────────────────────────────────────────────────────────
# Stage 5: Fetch backend logs
# ─────────────────────────────────────────────────────────────────────────────


async def stage_fetch_backend_logs(session) -> List[Dict[str, Any]]:
    """اگر در inspector logs.console قبلاً sync شده بودند، آن‌ها در
    session.console_logs و session.backend_logs ذخیره شده‌اند (توسط client
    در /stop). اینجا یک fetch نهایی هم از Render API می‌زنیم برای ثبت لاگ‌های
    آخرین لحظات (اگر هنوز sync نشده).

    Returns: لیست backend logs مرتبط با مدت ضبط
    """
    # session_dir را برای resolve watched نیاز نداریم — backend logs مستقیماً
    # از Render service ID خوانده می‌شوند. این مرحله اختیاری است — اگر در
    # سمت client قبلاً sync شده بود، فقط همان را برمی‌گرداند.
    # برای سادگی commit 3، فقط آنچه که قبلاً در session.backend_logs هست را
    # برمی‌گرداند. در commit 6 (UI) frontend می‌تواند logs را در /stop ارسال
    # کند یا backend مستقیم Render API را صدا بزند.
    return list(session.backend_logs)


# ─────────────────────────────────────────────────────────────────────────────
# Stage 6: AI synthesis — strong prompt builder
# ─────────────────────────────────────────────────────────────────────────────


SYNTHESIS_SYSTEM_PROMPT_MODE_A = """تو یک پرامپت‌نویس قوی و دقیق هستی. کاربر یک ضبط ویدئویی از تب بازرس ویژه گرفته که محتوای داخل iframe پروژه‌اش را نشان می‌دهد. ورودی‌های زیر را دریافت می‌کنی:

1. یادداشت اولیه کاربر (دست‌نخورده — این نقطه شروع است)
2. Transcript صدای کاربر در حین ضبط
3. خلاصه‌های بصری هر keyframe (با timestamp)
4. لیست تعاملات کاربر در iframe (کلیک، اسکرول، navigation)
5. console logs frontend iframe
6. backend logs (Render) در همان دوره
7. نام پروژه و repo

**وظیفه تو:**

الف) **استخراج intent**: دقیقاً کاربر چه می‌گوید، چه می‌خواهد، چه را رد می‌کند، کجاها منظورش است. این مهم‌ترین بخش است — نه فقط transcribe خام، بلکه فهم منظور.

ب) **فیلتر بی‌ربط**: کاربر فقط داخل iframe بود — اگر در صدا به چیزی **خارج از iframe** اشاره کرد (مثلاً «این تب IMDB رو ببین»)، آن را **بی‌ربط** تشخیص بده و در پرامپت لحاظ نکن. این یک قاعدهٔ مطلق است.

ج) **تولید پرامپت قوی**: خروجی نهایی باید:
   - شامل intent اصلی کاربر باشد در یک پاراگراف بالای متن
   - فایل‌ها/URLs/کامپوننت‌هایی که کاربر به آن‌ها اشاره کرده یا در logs دیده شده را در یک لیست بدهد
   - خطاهای مهم از logs را نقل قول کند
   - تعاملات کاربر را به زبان طبیعی توصیف کند («کاربر روی دکمهٔ X کلیک کرد و سپس اسکرول کرد به ...»)
   - actionable باشد: یک agent دیگر باید بتواند با فقط این پرامپت کار را پیش ببرد
   - **بدون محدودیت طول** — هر اندازه‌ای که نیاز است

خروجی فقط متن Markdown ساختاریافته. هیچ کد JSON یا code-block بیرونی نده. ساختار:

# 🎯 خواستهٔ اصلی کاربر
{یک پاراگراف کوتاه و دقیق}

# 🔍 جزئیات و context
{چند پاراگراف}

# 🖱 تعاملات کلیدی
{لیست با bullet}

# 📋 خطاها/پیام‌های log مرتبط
{اگر هست — code block با خطاها}

# 🔗 منابع شناسایی‌شده
{لیست با bullet — files, URLs, components}

# 💡 پرامپت قابل اجرا برای agent
{متن کامل جامع}
"""

SYNTHESIS_SYSTEM_PROMPT_MODE_B = """تو یک پرامپت‌نویس قوی هستی. کاربر یک ضبط آزاد چندصفحه‌ای گرفته که می‌تواند شامل: تب‌های مختلف کروم، برنامه‌های دیگر دسکتاپ، یا دسکتاپ خام باشد.

ورودی‌ها:
1. یادداشت اولیه کاربر
2. Transcript صدای کاربر
3. خلاصه‌های بصری هر keyframe — شامل تشخیص محل (chrome_tab / other_app / desktop) و related_to_project (bool)
4. لاگ‌های پروژهٔ inspector (در صورت موجود)
5. نام پروژهٔ inspector که کاربر در ضبط ممکن است به آن اشاره کرده باشد

**وظیفه:**

الف) **استخراج intent** — مثل حالت A.

ب) **رفتار با محتوای خارج از پروژه**:
   - اگر کاربر به جایی خارج از پروژه رفت ولی در صدا به آن **اشاره نکرد** → از بدنهٔ پرامپت **حذف** کن (بی‌ربط)
   - اگر کاربر به جایی خارج رفت **و در صدا به آن اشاره کرد** (مثل «این UI رو می‌خوام مثل این بسازم») → آن را به‌عنوان «مرجع/الهام» در پرامپت **نگه دار**

ج) **توالی زمانی** — ترتیب جابجایی کاربر بین صفحات را در پرامپت به زبان طبیعی توصیف کن.

خروجی Markdown با همان ساختار حالت A، با یک بخش اضافه:

# 🌐 توالی فعالیت کاربر
{جدول یا لیست با timestampهای جابجایی}
"""


async def stage_synthesize(session, *, user_note: str = "") -> Dict[str, Any]:
    """ورودی‌های stage 1-5 را به AI text model می‌دهد و پرامپت قوی می‌سازد.

    Returns: {prompt: str, model_used: str | None, fallback: bool}
    """
    from .ai_manager import get_ai_manager
    from .ai_base import Message
    from ..core.models_registry import get_enabled_models, ModelProvider
    import os as _os

    # ساخت ورودی ساختاریافته برای AI
    sections: List[str] = []
    if user_note:
        sections.append(f"## یادداشت اولیه کاربر\n{user_note.strip()}")
    sections.append(
        f"## context پروژه\n"
        f"- repo: {session.project_full_name or '?'}\n"
        f"- watched_id: {session.project_id}\n"
        f"- مدت ضبط: {session.duration_sec():.1f}s\n"
        f"- حالت: {session.mode}"
    )
    if session.transcript:
        sections.append(f"## Transcript صدای کاربر\n{session.transcript}")
    if session.visual_summary:
        vs_lines = []
        for v in session.visual_summary:
            ts = _format_timestamp(v.get("timestamp_ms", 0))
            scene = v.get("scene") or ""
            ocr = (v.get("ocr_text") or "")[:500]
            ui = (v.get("ui_elements") or "")[:300]
            err = (v.get("error_signals") or "")[:300]
            vs_lines.append(
                f"{ts}\n  - scene: {scene}\n  - ocr: {ocr}\n  - ui: {ui}\n  - errors: {err}"
            )
        sections.append("## خلاصه‌های بصری keyframes\n" + "\n\n".join(vs_lines))
    if session.interactions:
        int_lines = []
        for ev in session.interactions:
            ts = _format_timestamp(ev.ts_ms)
            int_lines.append(f"{ts} {ev.type} — {json.dumps(ev.details, ensure_ascii=False)[:200]}")
        sections.append("## تعاملات کاربر\n" + "\n".join(int_lines[:200]))  # cap at 200
    if session.console_logs:
        cl_lines = [
            f"[{l.get('level','log')}] {l.get('message','')[:200]}"
            for l in session.console_logs[-50:]  # آخرین ۵۰
        ]
        sections.append("## Console logs frontend\n" + "\n".join(cl_lines))
    if session.backend_logs:
        bl_lines = [
            f"[{l.get('level','info')}] {l.get('message','')[:200]}"
            for l in session.backend_logs[-50:]
        ]
        sections.append("## Backend logs\n" + "\n".join(bl_lines))
    if session.mode == "B" and session.location_timeline:
        lt = [
            f"{_format_timestamp(item.get('ts_ms',0))} {item.get('category','?')}: "
            f"{item.get('url_or_app_name','?')} — {'مرتبط' if item.get('related_to_project') else 'خارج'}"
            for item in session.location_timeline
        ]
        sections.append("## نقشهٔ زمانی فعالیت\n" + "\n".join(lt))

    # 🆕 (Multimodal context) — اگر multimodal call قبلاً intent extracted،
    # key references، و log signals را برگردانده، آن‌ها را prepend کن.
    # این کار جلوگیری می‌کند که AI text model دوباره کار analyzer را تکرار کند
    # و کیفیت پرامپت نهایی را بالا می‌برد.
    extra = getattr(session, "extra_context", None) or {}
    if extra.get("intent_extracted"):
        sections.insert(0, "## intent استخراج‌شده (از multimodal analysis)\n" + str(extra["intent_extracted"])[:5000])
    if extra.get("key_references"):
        refs = extra["key_references"]
        if isinstance(refs, list) and refs:
            sections.append("## منابع شناسایی‌شده توسط AI\n" + "\n".join(f"- {r}" for r in refs[:30]))
    if extra.get("important_log_signals"):
        sigs = extra["important_log_signals"]
        if isinstance(sigs, list) and sigs:
            sections.append("## سیگنال‌های مهم از logs (به‌انتخاب AI)\n" + "\n".join(f"- {s}" for s in sigs[:30]))

    structured_input = "\n\n".join(sections)
    system_prompt = (
        SYNTHESIS_SYSTEM_PROMPT_MODE_A if session.mode == "A"
        else SYNTHESIS_SYSTEM_PROMPT_MODE_B
    )

    # انتخاب مدل: اولین مدل enabled با provider که env key دارد
    env_keys = {
        "openai": ["OPENAI_API_KEY"],
        "claude": ["ANTHROPIC_API_KEY", "CLAUDE_API_KEY"],
        "anthropic": ["ANTHROPIC_API_KEY", "CLAUDE_API_KEY"],
        "gemini": ["GEMINI_API_KEY", "GOOGLE_API_KEY"],
        "google": ["GEMINI_API_KEY", "GOOGLE_API_KEY"],
        "deepseek": ["DEEPSEEK_API_KEY"],
        "groq": ["GROQ_API_KEY"],
        "openrouter": ["OPENROUTER_API_KEY"],
        # 🆕 (cloud_code parity) — Claude OAuth subscription also counts
        # as a "key configured" provider. Without this, the synthesis
        # fallback skips cloud_code entirely even when the user only has
        # CLAUDE_CODE_OAUTH_TOKEN set (no API keys).
        "cloud_code": ["CLAUDE_CODE_OAUTH_TOKEN"],
    }
    with_key = set()
    for p, ks in env_keys.items():
        if any((_os.environ.get(k) or "").strip() for k in ks):
            with_key.add(p.lower())
    enabled = get_enabled_models()
    picked = None
    # ترجیح: مدل‌های context-طولانی (Claude، Gemini) → text-only.
    # cloud_code جلوی anthropic API direct نگه می‌داریم چون subscription-based
    # است (هزینهٔ token صفر) و کاربر مدل پیش‌فرض monitoring اش است.
    preferred_order = [
        "cloud_code", "anthropic", "claude", "gemini", "google",
        "openai", "deepseek", "groq", "openrouter",
    ]
    for target_prov in preferred_order:
        if target_prov not in with_key:
            continue
        for m in enabled:
            prov = m.provider
            prov_str = (prov.value if hasattr(prov, "value") else str(prov)).lower()
            if prov_str == target_prov:
                picked = m
                break
        if picked:
            break

    if not picked:
        # fallback: template-only assembly بدون AI
        return {
            "prompt": _template_only_fallback(session, user_note, structured_input),
            "model_used": None,
            "fallback": True,
            "fallback_reason": (
                "هیچ مدل AI متنی برای سنتز پرامپت در دسترس نبود — "
                "از template ساده استفاده شد. می‌توانید ANTHROPIC_API_KEY یا "
                "OPENAI_API_KEY در Render env اضافه کنید."
            ),
        }

    ai_mgr = get_ai_manager()
    msg_user = (
        f"{system_prompt}\n\n"
        f"---\n\n"
        f"# ورودی‌های ساختاریافته\n\n"
        f"{structured_input}\n\n"
        f"---\n\n"
        "حالا خروجی Markdown قوی را تولید کن:"
    )
    try:
        response = await ai_mgr.generate(
            model_id=picked.id,
            messages=[Message(role="user", content=msg_user)],
            max_tokens=8000,  # بزرگ برای پرامپت قوی، ولی بدون truncation در ذخیره
            temperature=0.3,
        )
        ai_text = (response.content or "").strip()
        if not ai_text:
            raise RuntimeError("AI returned empty text")
        return {
            "prompt": ai_text,
            "model_used": picked.id,
            "fallback": False,
            "fallback_reason": "",
        }
    except Exception as e:
        logger.exception(f"prompt synthesis failed with {picked.id}: {e}")
        return {
            "prompt": _template_only_fallback(session, user_note, structured_input),
            "model_used": None,
            "fallback": True,
            "fallback_reason": f"AI synthesis failed ({str(e)[:150]}) — استفاده از template ساده",
        }


def _template_only_fallback(session, user_note: str, structured_input: str) -> str:
    """اگر AI fail کرد، یک پرامپت template-only تولید می‌کند که حداقل
    ورودی‌ها را به‌صورت ساختاریافته نگه می‌دارد.
    """
    return (
        f"# 🎯 یادداشت اولیه کاربر\n\n{user_note.strip() or '(یادداشت اولیه‌ای ارائه نشد)'}\n\n"
        f"---\n\n"
        f"# 📦 ورودی‌های خام (AI synthesis در دسترس نبود — این متن template-only است)\n\n"
        f"{structured_input}\n\n"
        f"---\n\n"
        f"# 💡 توصیه\n\n"
        f"برای دریافت پرامپت قوی AI، یکی از این env varها را پیکربندی کنید:\n"
        f"- ANTHROPIC_API_KEY (پیشنهادی برای پرامپت‌های طولانی)\n"
        f"- OPENAI_API_KEY\n"
        f"- GEMINI_API_KEY\n"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Final structured prompt — راپر template + AI output + source attribution
# ─────────────────────────────────────────────────────────────────────────────


def build_final_prompt(
    session,
    *,
    user_note: str,
    ai_generated_body: str,
    telegram_info: Optional[str] = None,
) -> str:
    """ساختار نهایی طبق طراحی section 4.5:
       یادداشت اولیه (در heading اول) → بلوک منشأ → AI-generated body
    """
    mode_label = "🎯 A — iframe-focused" if session.mode == "A" else "🌐 B — free-multi-screen"
    now_iso = datetime.now(timezone.utc).isoformat()
    duration = session.duration_sec()
    m_int, s_int = int(duration // 60), int(duration % 60)

    parts = []
    # 1) یادداشت اولیه — heading اول
    parts.append("# " + (user_note.strip() or "ضبط بازرس ویژه"))
    parts.append("")
    parts.append("---")
    parts.append("")
    # 2) بلوک منشأ
    parts.append("## 📍 منشأ این پرامپت")
    parts.append("")
    parts.append(f"- **منبع**: ضبط در تب بازرس ویژه — حالت {mode_label}")
    parts.append(f"- **پروژه**: `{session.project_full_name or session.project_id}`")
    parts.append(f"- **تاریخ ضبط**: {now_iso}")
    parts.append(f"- **مدت**: {m_int}m {s_int}s")
    if telegram_info:
        parts.append(f"- **ویدئو**: {telegram_info}")
    else:
        parts.append("- **ویدئو**: (در حال آماده‌سازی — در commit آینده ارسال به تلگرام)")
    parts.append(f"- **session_id**: `{session.session_id}` (موقت — حذف می‌شود)")
    parts.append("")
    parts.append("---")
    parts.append("")
    # 3) AI-generated body
    parts.append(ai_generated_body)
    return "\n".join(parts)


# ─────────────────────────────────────────────────────────────────────────────
# Orchestrator: تمام stages با progress callback
# ─────────────────────────────────────────────────────────────────────────────


async def process_session(
    session,
    *,
    user_note: str = "",
    progress_callback: Optional[Any] = None,
) -> Dict[str, Any]:
    """اجرای تمام stages روی session. خروجی‌ها در session ذخیره می‌شوند.

    Args:
      session: RecordingSession
      user_note: یادداشت اولیه کاربر (raw_idea)
      progress_callback: تابع اختیاری(stage, percent, message)

    Returns: dict خلاصه‌ای از نتیجه
    """
    async def _emit(stage: str, pct: int, msg: str = ""):
        if progress_callback:
            try:
                if asyncio.iscoroutinefunction(progress_callback):
                    await progress_callback(stage, pct, msg)
                else:
                    progress_callback(stage, pct, msg)
            except Exception:
                pass

    started = time.time()
    summary = {
        "session_id": session.session_id,
        "multimodal": None,
        "transcribe": None,
        "vision_count": 0,
        "logs_count": 0,
        "synthesize": None,
        "elapsed_sec": 0.0,
    }

    # 🆕 (Unified Multimodal) — اولویت اول: یک call واحد به Gemini Flash 2.5
    # که هم transcribe صوت + هم visual analysis + (mode B) location را همزمان
    # برمی‌گرداند. این روش کاربر صریحاً درخواست کرد ("همون مدلی که دیباگ
    # بصری انجام می‌دهد خودش کار صوتی هم انجام بدهد").
    # اگر multimodal model در دسترس نبود یا payload بزرگ بود، به legacy
    # pipeline (Whisper جدا + vision per frame) fallback می‌کنیم.
    await _emit("multimodal", 0, "تلاش برای آنالیز یکپارچه با Gemini...")
    multimodal_used = False
    try:
        from .inspector_recording_multimodal import analyze_recording_multimodal
        mm = await analyze_recording_multimodal(session, user_note=user_note)
        if mm.get("success"):
            multimodal_used = True
            session.transcript = mm.get("transcript", "")
            session.transcript_language = mm.get("transcript_language", "")
            session.transcript_model = mm.get("model_used") or ""
            session.visual_summary = mm.get("visual_summary") or []
            if session.mode == "B":
                session.location_timeline = mm.get("location_timeline") or []
            summary["multimodal"] = {
                "success": True,
                "model": mm.get("model_used"),
                "provider": mm.get("provider"),
                "transcript_chars": len(session.transcript),
                "visual_items": len(session.visual_summary),
                "location_items": len(session.location_timeline),
                "intent_chars": len(mm.get("intent_extracted", "")),
            }
            # intent_extracted را در session بگذار تا stage_synthesize از آن
            # به‌عنوان context استفاده کند
            session.extra_context = {
                "intent_extracted": mm.get("intent_extracted", ""),
                "key_references": mm.get("key_references", []),
                "important_log_signals": mm.get("important_log_signals", []),
            }
            await _emit(
                "multimodal", 100,
                f"unified با {mm.get('model_used')}: "
                f"{len(session.transcript)} char transcript + "
                f"{len(session.visual_summary)} visual"
            )
        else:
            summary["multimodal"] = {
                "success": False,
                "fallback_reason": mm.get("fallback_reason", ""),
            }
            logger.info(
                f"multimodal not used for {session.session_id}: "
                f"{mm.get('fallback_reason')}"
            )
    except Exception as e:
        logger.warning(f"multimodal call crashed (will fallback to legacy): {e}")
        summary["multimodal"] = {"success": False, "fallback_reason": f"crashed: {str(e)[:200]}"}

    # ───── Legacy pipeline fallback (separate transcribe + vision per frame)
    if not multimodal_used:
        # Stage 1+2: Transcribe (Whisper-style separate call)
        await _emit("transcribe", 0, "آنالیز جداگانه — transcribe صوت با Whisper...")
        tr = await stage_transcribe(session)
        session.transcript = tr.get("text", "")
        session.transcript_language = tr.get("language", "")
        session.transcript_model = tr.get("model_used") or ""
        summary["transcribe"] = {
            "success": tr.get("success"),
            "chars": len(session.transcript),
            "language": session.transcript_language,
            "model": session.transcript_model,
            "fallback_reason": tr.get("fallback_reason", ""),
        }
        await _emit("transcribe", 100, f"{len(session.transcript)} char transcribed")

        # Stage 3+4: Vision per keyframe
        await _emit("vision", 0, "آنالیز جداگانه — vision per keyframe...")
        visual = await stage_vision(session)
        session.visual_summary = visual
        summary["vision_count"] = len(visual)
        await _emit("vision", 100, f"{len(visual)} keyframe analyzed")

        # Stage 4b (mode B only): Location classifier
        if session.mode == "B":
            await _emit("location", 0, "تشخیص محل و فعالیت در فریم‌ها...")
            timeline = await stage_location_timeline(session)
            session.location_timeline = timeline
            summary["location_timeline_count"] = len(timeline)
            await _emit("location", 100, f"{len(timeline)} location frame analyzed")

    # Stage 5: Logs (sync if not already)
    await _emit("logs", 0, "جمع‌آوری لاگ‌ها...")
    logs = await stage_fetch_backend_logs(session)
    summary["logs_count"] = len(logs)
    await _emit("logs", 100, "")

    # Stage 6: AI synthesis
    await _emit("synthesize", 0, "سنتز پرامپت قوی توسط AI...")
    syn = await stage_synthesize(session, user_note=user_note)
    ai_body = syn.get("prompt") or ""
    session.prompt_model = syn.get("model_used") or ""
    summary["synthesize"] = {
        "model": session.prompt_model,
        "fallback": syn.get("fallback"),
        "fallback_reason": syn.get("fallback_reason", ""),
    }
    await _emit("synthesize", 80, "ترکیب نهایی...")

    # Stage 7: Final prompt assembly
    session.prompt = build_final_prompt(session, user_note=user_note, ai_generated_body=ai_body)
    await _emit("synthesize", 100, f"prompt: {len(session.prompt)} chars")

    summary["elapsed_sec"] = round(time.time() - started, 2)
    summary["prompt_chars"] = len(session.prompt)
    return summary
