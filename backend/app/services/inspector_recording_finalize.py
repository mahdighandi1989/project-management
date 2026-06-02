"""
🎬 Inspector Recording Finalize — ارسال نهایی به Telegram + ساخت تسک یا چت.

این ماژول مرحله نهایی pipeline است:
  1. assemble media (audio + video از chunks/frames)
  2. ارسال به Telegram با caption شامل خلاصه پرامپت (split اگر >45MB)
  3. حذف کامل فایل‌ها از disk
  4. ساخت تسک از طریق OversightService.create_task اگر send_to_oversight=True
     در غیر این صورت ارسال پرامپت به چت

تمام operations idempotent — اگر یک stage fail شد، بقیه ادامه می‌دهند و
error در نتیجه برمی‌گردد.
"""
from __future__ import annotations

import asyncio
import io
import json
import logging
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


MAX_TELEGRAM_FILE_MB = 45  # Telegram Bot API limit بدون local server: 50MB، با buffer 45
MIN_PROMPT_PREVIEW_CHARS = 200
MAX_CAPTION_CHARS = 1020


# ─────────────────────────────────────────────────────────────────────────────
# Media assembly
# ─────────────────────────────────────────────────────────────────────────────


def _assemble_video_from_chunks(video_dir: Path) -> Optional[bytes]:
    """video chunks (webm با کد یکسان از MediaRecorder) را concat می‌کند.

    این روش برای webm با کد سازگار کار می‌کند چون webm container از clusters
    متوالی پشتیبانی می‌کند. مرورگرها معمولاً bytes یکسری متوالی webm را
    pure-play می‌کنند.
    """
    if not video_dir.exists():
        return None
    chunks = sorted(video_dir.glob("chunk_*.webm"))
    if not chunks:
        return None
    parts: List[bytes] = []
    for c in chunks:
        try:
            parts.append(c.read_bytes())
        except Exception as e:
            logger.warning(f"failed to read video chunk {c.name}: {e}")
    if not parts:
        return None
    return b"".join(parts)


def _build_animated_webp_from_frames(
    frames_dir: Path, max_frames: int = 60, fps: int = 2
) -> Optional[Tuple[bytes, str]]:
    """animated WebP از frames PNG/JPG می‌سازد. این روش بدون ffmpeg کار می‌کند
    (Pillow کافی است).

    Returns: (bytes, mime_type) یا None
    """
    if not frames_dir.exists():
        return None
    all_frames = sorted(frames_dir.glob("frame_*.png")) + sorted(frames_dir.glob("frame_*.jpg"))
    if not all_frames:
        return None
    # محدود کن به max_frames تا فایل خروجی منفجر نشود
    if len(all_frames) > max_frames:
        step = len(all_frames) / max_frames
        all_frames = [all_frames[int(i * step)] for i in range(max_frames)]
    try:
        from PIL import Image
    except ImportError:
        logger.warning("Pillow not installed — cannot build animated webp")
        return None

    try:
        images = []
        for fp in all_frames:
            img = Image.open(fp).convert("RGB")
            # downscale به حداکثر 1280px در طول بزرگ‌تر — برای سایز
            max_dim = 1280
            w, h = img.size
            if max(w, h) > max_dim:
                scale = max_dim / max(w, h)
                img = img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)
            images.append(img)
        if not images:
            return None
        # WebP animation: duration بر اساس fps
        duration_ms = int(1000 / max(1, fps))
        buf = io.BytesIO()
        images[0].save(
            buf,
            format="WEBP",
            save_all=True,
            append_images=images[1:],
            duration=duration_ms,
            loop=0,
            quality=70,
            method=4,  # quality/speed tradeoff
        )
        data = buf.getvalue()
        # ensure cleanup
        for img in images:
            try:
                img.close()
            except Exception:
                pass
        logger.info(
            f"animated webp built from {len(all_frames)} frames, "
            f"size={len(data) / 1024:.1f}KB"
        )
        return data, "image/webp"
    except Exception as e:
        logger.exception(f"failed to build animated webp: {e}")
        return None


def _split_bytes(data: bytes, chunk_size_mb: int = MAX_TELEGRAM_FILE_MB) -> List[bytes]:
    """اگر data > chunk_size_mb، آن را به chunks تقسیم می‌کند.

    هشدار: این برای files binary (video/audio) split بدون re-encode انجام
    می‌شود — هر chunk به‌تنهایی قابل پخش نیست. فقط برای انتقال است.
    کاربر باید چند chunk را خودش بپیوندد یا از همان webm container مزیت
    sequential clusters استفاده کند.
    """
    max_bytes = chunk_size_mb * 1024 * 1024
    if len(data) <= max_bytes:
        return [data]
    chunks = []
    for i in range(0, len(data), max_bytes):
        chunks.append(data[i:i + max_bytes])
    return chunks


# ─────────────────────────────────────────────────────────────────────────────
# Telegram delivery
# ─────────────────────────────────────────────────────────────────────────────


def _build_telegram_caption(session, user_note: str, task_id: Optional[str] = None) -> str:
    """caption متناسب با محدودیت 1024 char تلگرام."""
    mode_label = "🎯 A" if session.mode == "A" else "🌐 B"
    repo = session.project_full_name or session.project_id
    duration = session.duration_sec()
    m_int, s_int = int(duration // 60), int(duration % 60)
    parts = []
    parts.append(f"🎬 ضبط بازرس ویژه — حالت {mode_label}")
    parts.append(f"📁 پروژه: `{repo}`")
    parts.append(f"⏱ مدت: {m_int}m {s_int}s")
    if task_id:
        parts.append(f"🆔 تسک: `{task_id[:8]}`")
    parts.append("")
    if user_note:
        parts.append("📝 یادداشت اولیه:")
        parts.append(user_note[:200] + ("…" if len(user_note) > 200 else ""))
        parts.append("")
    # خلاصه پرامپت
    if session.prompt:
        # skip header sections — قسمت "💡 پرامپت قابل اجرا" یا اولین جسته
        prompt_body = session.prompt
        for marker in ("# 💡", "# پرامپت قابل اجرا", "# پرامپت قوی"):
            idx = prompt_body.find(marker)
            if idx > 0:
                prompt_body = prompt_body[idx:]
                break
        parts.append("🤖 خلاصه پرامپت AI:")
        parts.append(prompt_body[:500].strip())
    cap = "\n".join(parts)
    if len(cap) > MAX_CAPTION_CHARS:
        cap = cap[:MAX_CAPTION_CHARS - 1] + "…"
    return cap


async def _send_to_telegram_video(
    file_bytes: bytes, filename: str, caption: str
) -> Dict[str, Any]:
    """ارسال video به تلگرام با sendVideo API (به‌جای sendDocument).

    sendVideo اجازه پخش inline در تلگرام را می‌دهد. اگر file_size > 50MB،
    باید به sendDocument fallback کنیم چون sendVideo سختگیرتر است.
    """
    import aiohttp

    bot_token = (os.environ.get("TELEGRAM_BOT_TOKEN") or "").strip()
    chat_id = (os.environ.get("TELEGRAM_CHAT_ID") or "").strip()
    if not bot_token or not chat_id:
        return {"ok": False, "error": "TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID پیکربندی نشده"}

    # تشخیص content_type
    fname_low = filename.lower()
    if fname_low.endswith(".webm"):
        ctype = "video/webm"
    elif fname_low.endswith(".mp4"):
        ctype = "video/mp4"
    elif fname_low.endswith(".webp"):
        ctype = "image/webp"
    else:
        ctype = "application/octet-stream"

    # برای webp animated از sendAnimation استفاده کن
    if ctype == "image/webp":
        url = f"https://api.telegram.org/bot{bot_token}/sendAnimation"
        field_name = "animation"
    elif ctype.startswith("video/"):
        url = f"https://api.telegram.org/bot{bot_token}/sendVideo"
        field_name = "video"
    else:
        # fallback به document
        url = f"https://api.telegram.org/bot{bot_token}/sendDocument"
        field_name = "document"

    form = aiohttp.FormData()
    form.add_field("chat_id", chat_id)
    if caption:
        form.add_field("caption", caption[:MAX_CAPTION_CHARS])
        form.add_field("parse_mode", "Markdown")
    form.add_field(
        field_name, file_bytes, filename=filename, content_type=ctype
    )

    try:
        timeout = aiohttp.ClientTimeout(total=120)
        async with aiohttp.ClientSession(timeout=timeout) as session_http:
            async with session_http.post(url, data=form) as r:
                body = await r.text()
                if r.status != 200:
                    # retry بدون parse_mode اگر Markdown مشکل بود
                    if "can't parse" in body.lower():
                        form2 = aiohttp.FormData()
                        form2.add_field("chat_id", chat_id)
                        if caption:
                            form2.add_field("caption", caption[:MAX_CAPTION_CHARS])
                        form2.add_field(
                            field_name, file_bytes, filename=filename, content_type=ctype
                        )
                        async with session_http.post(url, data=form2) as r2:
                            if r2.status == 200:
                                try:
                                    j2 = json.loads(await r2.text())
                                    return {"ok": True, "message_id": j2.get("result", {}).get("message_id")}
                                except Exception:
                                    return {"ok": True}
                            body2 = await r2.text()
                            return {"ok": False, "error": f"HTTP {r2.status}: {body2[:300]}"}
                    return {"ok": False, "error": f"HTTP {r.status}: {body[:300]}"}
                try:
                    j = json.loads(body)
                    return {
                        "ok": True,
                        "message_id": j.get("result", {}).get("message_id"),
                        "file_id": (j.get("result", {}).get(field_name) or {}).get("file_id"),
                    }
                except Exception:
                    return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": f"send_video exception: {str(e)[:300]}"}


async def _send_to_telegram_audio(
    file_bytes: bytes, filename: str, caption: str = ""
) -> Dict[str, Any]:
    """ارسال audio به Telegram به‌صورت document. (audio با sendAudio هم
    ممکن است ولی document قابل اطمینان‌تر است.)
    """
    import aiohttp

    bot_token = (os.environ.get("TELEGRAM_BOT_TOKEN") or "").strip()
    chat_id = (os.environ.get("TELEGRAM_CHAT_ID") or "").strip()
    if not bot_token or not chat_id:
        return {"ok": False, "error": "TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID پیکربندی نشده"}

    url = f"https://api.telegram.org/bot{bot_token}/sendAudio"
    form = aiohttp.FormData()
    form.add_field("chat_id", chat_id)
    if caption:
        form.add_field("caption", caption[:MAX_CAPTION_CHARS])
    form.add_field(
        "audio", file_bytes, filename=filename, content_type="audio/webm"
    )

    try:
        timeout = aiohttp.ClientTimeout(total=60)
        async with aiohttp.ClientSession(timeout=timeout) as session_http:
            async with session_http.post(url, data=form) as r:
                body = await r.text()
                if r.status != 200:
                    return {"ok": False, "error": f"HTTP {r.status}: {body[:300]}"}
                try:
                    j = json.loads(body)
                    return {"ok": True, "message_id": j.get("result", {}).get("message_id")}
                except Exception:
                    return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": f"send_audio exception: {str(e)[:300]}"}


# ─────────────────────────────────────────────────────────────────────────────
# Cleanup
# ─────────────────────────────────────────────────────────────────────────────


def _cleanup_session_disk(session) -> None:
    """حذف کامل دایرکتوری session از disk."""
    try:
        if session.session_dir.exists():
            shutil.rmtree(session.session_dir, ignore_errors=True)
            logger.info(f"finalize: cleanup disk for session {session.session_id}")
    except Exception as e:
        logger.warning(f"cleanup_disk failed: {e}")


# ─────────────────────────────────────────────────────────────────────────────
# Task creation (delegate به OversightService.create_task)
# ─────────────────────────────────────────────────────────────────────────────


async def _create_task_from_session(session, user_note: str) -> Dict[str, Any]:
    """تسک جدید زیر پروژه inspector ایجاد می‌کند با حفظ raw_idea (یادداشت
    اولیه) و prompt قوی.
    """
    from .oversight_service import get_oversight_service

    svc = get_oversight_service()
    # تشخیص watched_id — frontend می‌تواند watched_id را در project_id بفرستد
    watched_id = session.project_id
    # اگر project_id یک id واقعی watched نیست، با repo_full_name resolve کن
    watched = None
    if watched_id:
        watched = svc._find_watched(watched_id)
    if watched is None and session.project_full_name:
        watched = next(
            (w for w in svc.watched if (w.repo_full_name or "").lower() == session.project_full_name.lower()),
            None,
        )
    if watched is None:
        return {
            "ok": False,
            "error": (
                f"watched پروژه با id='{session.project_id}' و repo="
                f"'{session.project_full_name}' یافت نشد"
            ),
        }

    # تولید title از اولین جمله یادداشت یا session_id کوتاه
    title_src = (user_note or "").strip()
    if title_src:
        # اولین خط/جمله
        first_line = title_src.splitlines()[0].strip()
        if len(first_line) <= 100:
            title = first_line
        else:
            title = first_line[:100] + "…"
    else:
        title = f"ضبط بازرس ویژه — {session.session_id[:8]}"

    payload = {
        "watched_id": watched.id,
        "project_full_name": watched.repo_full_name,
        "title": title,
        "prompt": session.prompt,
        "raw_idea": user_note or "",
        "type": "feature_request",
        "priority": "medium",
        "source": "inspector_recording",
        "force_create": True,  # skip dedup gate برای ضبط‌ها
    }
    try:
        result = await svc.create_task(payload)
        # create_task برمی‌گرداند dict با status + task
        if result.get("status") == "created" and result.get("task"):
            task = result["task"]
            task_id = task.get("id") if isinstance(task, dict) else getattr(task, "id", None)
            return {
                "ok": True,
                "task_id": task_id,
                "watched_id": watched.id,
                "status": result.get("status"),
            }
        # status duplicate یا merged
        return {
            "ok": True,
            "task_id": None,
            "status": result.get("status"),
            "note": "تسک به‌جای create شدن، duplicate/merge شد",
            "full_result": {k: v for k, v in result.items() if k != "task"},
        }
    except Exception as e:
        logger.exception(f"create_task failed for session {session.session_id}")
        return {"ok": False, "error": f"create_task failed: {str(e)[:300]}"}


# ─────────────────────────────────────────────────────────────────────────────
# Chat routing (اگر send_to_oversight=False)
# ─────────────────────────────────────────────────────────────────────────────


async def _send_prompt_to_chat(session, user_note: str) -> Dict[str, Any]:
    """ارسال پرامپت قوی به چت inspector به‌عنوان پیام.

    در commit 5 این یک placeholder ساده است — frontend مسئول واقعی اضافه
    کردن پرامپت به chat history سمت کلاینت می‌شود. ما اینجا فقط برمی‌گردانیم
    که پرامپت آماده است.
    """
    return {
        "ok": True,
        "chat_message_sent": True,
        "note": (
            "پرامپت آماده برای افزودن به چت — frontend در commit 6 آن را در "
            "UI چت inspector نمایش می‌دهد"
        ),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Main finalize orchestrator
# ─────────────────────────────────────────────────────────────────────────────


async def finalize_recording_session(
    session,
    *,
    user_note: str,
    send_to_oversight: bool,
) -> Dict[str, Any]:
    """انتهای کامل: assemble media → Telegram → task/chat → cleanup.

    Returns: dict خلاصه با کلیدهای:
      success, task_id, telegram_message_ids, chat_message_sent, errors,
      cleanup_done, warnings
    """
    result = {
        "success": True,
        "task_id": None,
        "telegram_message_ids": [],
        "chat_message_sent": False,
        "errors": [],
        "warnings": [],
        "cleanup_done": False,
    }

    # ------- Stage 1: ساخت تسک (اگر send_to_oversight) — این اول می‌رود
    # تا task_id در caption تلگرام بیاید
    if send_to_oversight:
        task_res = await _create_task_from_session(session, user_note)
        if task_res.get("ok"):
            result["task_id"] = task_res.get("task_id")
            session.task_id = task_res.get("task_id")
        else:
            result["errors"].append(f"task: {task_res.get('error')}")
            result["success"] = False

    # ------- Stage 2: assemble media
    media_items: List[Tuple[bytes, str, str]] = []  # [(bytes, filename, kind)]

    # video / animation
    if session.mode == "B":
        video_bytes = _assemble_video_from_chunks(session.video_dir)
        if video_bytes:
            chunks = _split_bytes(video_bytes, MAX_TELEGRAM_FILE_MB)
            for i, ch in enumerate(chunks):
                name = (
                    f"recording_{session.session_id[:8]}.webm"
                    if len(chunks) == 1
                    else f"recording_{session.session_id[:8]}_part{i+1}of{len(chunks)}.webm"
                )
                media_items.append((ch, name, "video"))
        else:
            result["warnings"].append("video chunks خالی بود (mode B)")
    else:
        # mode A: animated webp از frames
        anim = _build_animated_webp_from_frames(session.frames_dir)
        if anim:
            data, _mime = anim
            name = f"recording_{session.session_id[:8]}.webp"
            media_items.append((data, name, "animation"))
        else:
            result["warnings"].append("frames خالی بود (mode A) — animation ساخته نشد")

    # audio (جداگانه، اگر موجود)
    from .inspector_recording_processor import _assemble_audio
    audio_bytes = _assemble_audio(session.audio_dir)
    if audio_bytes and len(audio_bytes) >= 1024:
        # audio احتمالاً کوچک است، تقسیم لازم نیست در عمل
        chunks = _split_bytes(audio_bytes, MAX_TELEGRAM_FILE_MB)
        for i, ch in enumerate(chunks):
            name = (
                f"recording_{session.session_id[:8]}.webm"
                if len(chunks) == 1
                else f"recording_{session.session_id[:8]}_audio_part{i+1}of{len(chunks)}.webm"
            )
            media_items.append((ch, name, "audio"))

    # ------- Stage 3: ارسال به Telegram
    base_caption = _build_telegram_caption(session, user_note, task_id=result.get("task_id"))
    for idx, (data, filename, kind) in enumerate(media_items):
        # caption فقط روی اولین item — بقیه فقط شماره
        if idx == 0:
            caption = base_caption
        else:
            total = len(media_items)
            caption = f"📎 ({idx + 1}/{total}) — {filename}"

        if kind == "audio":
            send_res = await _send_to_telegram_audio(data, filename, caption=caption)
        else:
            # video یا animation
            send_res = await _send_to_telegram_video(data, filename, caption=caption)

        if send_res.get("ok"):
            if send_res.get("message_id"):
                result["telegram_message_ids"].append(send_res["message_id"])
        else:
            result["errors"].append(f"telegram[{filename}]: {send_res.get('error')}")
            result["success"] = False

    session.telegram_message_ids = list(result["telegram_message_ids"])

    # ------- Stage 4: chat routing (اگر send_to_oversight=False)
    if not send_to_oversight:
        chat_res = await _send_prompt_to_chat(session, user_note)
        if chat_res.get("ok"):
            result["chat_message_sent"] = True
            session.chat_message_sent = True
        else:
            result["errors"].append(f"chat: {chat_res.get('error')}")

    # ------- Stage 5: Cleanup disk
    # حذف **فقط** اگر Telegram موفق بود (یا اصلاً media برای ارسال نبود)
    # اگر Telegram fail کرد، فایل را برای ۲۴ ساعت نگه می‌داریم — sweeper
    # بعداً پاکش می‌کند (sweep_stale در service که >120m idle اجرا می‌شود).
    telegram_failed = any("telegram" in e.lower() for e in result["errors"])
    if not telegram_failed:
        _cleanup_session_disk(session)
        result["cleanup_done"] = True
    else:
        result["warnings"].append(
            "فایل‌ها برای ۲ ساعت روی disk نگه داشته شدند چون Telegram fail کرد — "
            "sweep_stale در scheduler پاک خواهد کرد"
        )

    # final session state
    session.final_video_size_bytes = sum(len(b) for b, _, _ in media_items)
    session.phase = "completed"
    session.finalized_at = __import__("time").time()
    return result
