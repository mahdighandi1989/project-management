"""
🎬 Inspector Recording API — endpoint های REST برای جلسات ضبط ویدئو
از تب بازرس ویژه.

Commit 1 — Foundation: تمام endpoint ها با حداقل منطق state. processing
واقعی (Playwright، vision، transcribe، Telegram) در commits بعدی اضافه
می‌شود.

Endpoints (همگی زیر prefix /api/recording/inspector):
  POST /start                              شروع جلسه
  POST /{sid}/audio-chunk                  آپلود chunk صدا
  POST /{sid}/video-chunk                  آپلود chunk ویدئو (فقط mode B)
  POST /{sid}/interactions                 ارسال events تعاملات
  POST /{sid}/stop                         پایان ضبط — گذار به processing
  GET  /{sid}/status                       وضعیت فعلی session
  GET  /{sid}/preview                      preview داده‌های پردازش‌شده
  POST /{sid}/regenerate-prompt            دوباره پرامپت بساز با transcript ویرایش‌شده
  POST /{sid}/finalize                     ارسال به Telegram + ساخت تسک یا چت
  POST /{sid}/cancel                       لغو + حذف disk
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field

from ...services.inspector_recording_service import (
    get_inspector_recording_service,
    RecordingMode,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/recording/inspector", tags=["Inspector Recording"])


# ─────────────────────────────────────────────────────────────────────────────
# Request models
# ─────────────────────────────────────────────────────────────────────────────


class StartRecordingRequest(BaseModel):
    project_id: str = Field(..., description="watched_id یا hint پروژهٔ iframe")
    project_full_name: Optional[str] = Field(
        None, description="نام repo (e.g. owner/repo) برای caption تلگرام"
    )
    mode: str = Field(..., description="'A' (iframe) یا 'B' (free)")
    audio_mic: bool = True
    audio_system: bool = False
    mic_device_id: Optional[str] = None
    target_fps: Optional[int] = Field(
        None, description="اختیاری — پیش‌فرض: 2 برای A، 15 برای B"
    )


class InteractionsRequest(BaseModel):
    events: List[Dict[str, Any]] = Field(default_factory=list)


class RegeneratePromptRequest(BaseModel):
    edited_transcript: Optional[str] = None


class FinalizeRequest(BaseModel):
    user_note: str = ""
    send_to_oversight: bool = False
    edited_transcript: Optional[str] = None


# ─────────────────────────────────────────────────────────────────────────────
# Endpoints
# ─────────────────────────────────────────────────────────────────────────────


@router.post("/start")
async def start_recording(payload: StartRecordingRequest):
    """شروع یک جلسهٔ ضبط جدید. برمی‌گرداند session_id که در همهٔ call های
    بعدی استفاده می‌شود.
    """
    if payload.mode not in ("A", "B"):
        raise HTTPException(status_code=400, detail="mode باید 'A' یا 'B' باشد")
    svc = get_inspector_recording_service()
    try:
        session = await svc.start_session(
            project_id=payload.project_id,
            project_full_name=payload.project_full_name,
            mode=payload.mode,  # type: ignore[arg-type]
            audio_mic=payload.audio_mic,
            audio_system=payload.audio_system,
            mic_device_id=payload.mic_device_id,
            target_fps=payload.target_fps,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("start_recording failed")
        raise HTTPException(status_code=500, detail=f"start failed: {str(e)[:200]}")
    return {
        "success": True,
        "session": session.to_status_dict(),
    }


@router.post("/{session_id}/audio-chunk")
async def append_audio_chunk(
    session_id: str,
    seq: int = Form(...),
    chunk: UploadFile = File(...),
):
    """آپلود یک chunk صدا (سمت کلاینت از MediaRecorder)."""
    svc = get_inspector_recording_service()
    try:
        chunk_bytes = await chunk.read()
        if not chunk_bytes:
            raise HTTPException(status_code=400, detail="chunk خالی است")
        await svc.append_audio_chunk(session_id, seq=seq, chunk_bytes=chunk_bytes)
        return {"ok": True, "seq": seq, "size": len(chunk_bytes)}
    except KeyError:
        raise HTTPException(status_code=404, detail="session_not_found")
    except RuntimeError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.post("/{session_id}/video-chunk")
async def append_video_chunk(
    session_id: str,
    seq: int = Form(...),
    chunk: UploadFile = File(...),
):
    """آپلود یک chunk ویدئو (فقط در حالت B — getDisplayMedia سمت کلاینت)."""
    svc = get_inspector_recording_service()
    try:
        chunk_bytes = await chunk.read()
        if not chunk_bytes:
            raise HTTPException(status_code=400, detail="chunk خالی است")
        await svc.append_video_chunk(session_id, seq=seq, chunk_bytes=chunk_bytes)
        return {"ok": True, "seq": seq, "size": len(chunk_bytes)}
    except KeyError:
        raise HTTPException(status_code=404, detail="session_not_found")
    except RuntimeError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.post("/{session_id}/interactions")
async def append_interactions(session_id: str, payload: InteractionsRequest):
    """ارسال یک batch از events تعاملات کاربر (postMessage bridge یا inferred)."""
    svc = get_inspector_recording_service()
    try:
        await svc.append_interactions(session_id, payload.events)
        return {"ok": True, "count": len(payload.events)}
    except KeyError:
        raise HTTPException(status_code=404, detail="session_not_found")


@router.post("/{session_id}/stop")
async def stop_recording(session_id: str):
    """گذار از recording → processing. کاربر منتظر می‌ماند تا preview آماده
    شود.
    """
    svc = get_inspector_recording_service()
    try:
        session = await svc.stop_session(session_id)
        return {"ok": True, "session": session.to_status_dict()}
    except KeyError:
        raise HTTPException(status_code=404, detail="session_not_found")
    except RuntimeError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.get("/{session_id}/status")
async def get_status(session_id: str):
    """وضعیت جاری جلسه — برای polling از سمت کلاینت."""
    svc = get_inspector_recording_service()
    session = svc.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="session_not_found")
    return {"ok": True, "session": session.to_status_dict()}


@router.get("/{session_id}/preview")
async def get_preview(session_id: str):
    """داده‌های پردازش‌شده برای modal preview — شامل transcript، visual_summary،
    prompt تولیدشده، خلاصهٔ logs و interactions.
    """
    svc = get_inspector_recording_service()
    session = svc.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="session_not_found")
    if session.phase not in ("ready_for_preview", "completed"):
        raise HTTPException(
            status_code=409,
            detail=f"preview آماده نیست (phase={session.phase})",
        )
    return {
        "ok": True,
        "session": session.to_status_dict(),
        "transcript": session.transcript,
        "transcript_language": session.transcript_language,
        "visual_summary": session.visual_summary,
        "location_timeline": session.location_timeline,
        "interactions": [
            {"ts_ms": ev.ts_ms, "type": ev.type, "details": ev.details, "source": ev.source}
            for ev in session.interactions
        ],
        "console_logs_count": len(session.console_logs),
        "backend_logs_count": len(session.backend_logs),
        "prompt": session.prompt,
    }


@router.post("/{session_id}/regenerate-prompt")
async def regenerate_prompt(session_id: str, payload: RegeneratePromptRequest):
    """دوباره پرامپت تولید کن (پس از اصلاح transcript توسط کاربر)."""
    svc = get_inspector_recording_service()
    try:
        session = await svc.regenerate_prompt(
            session_id, edited_transcript=payload.edited_transcript
        )
        return {"ok": True, "prompt": session.prompt}
    except KeyError:
        raise HTTPException(status_code=404, detail="session_not_found")


@router.post("/{session_id}/finalize")
async def finalize_recording(session_id: str, payload: FinalizeRequest):
    """ارسال نهایی — ویدئو به Telegram، ساخت تسک (اگر send_to_oversight=true)
    یا ارسال به چت، سپس حذف disk.
    """
    svc = get_inspector_recording_service()
    try:
        result = await svc.finalize(
            session_id,
            user_note=payload.user_note,
            send_to_oversight=payload.send_to_oversight,
            edited_transcript=payload.edited_transcript,
        )
        return result
    except KeyError:
        raise HTTPException(status_code=404, detail="session_not_found")
    except RuntimeError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.post("/{session_id}/cancel")
async def cancel_recording(session_id: str):
    """لغو کامل — حذف disk + drop از RAM."""
    svc = get_inspector_recording_service()
    await svc.cancel_session(session_id)
    return {"ok": True}
