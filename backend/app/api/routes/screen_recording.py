# -*- coding: utf-8 -*-
"""
🎬 API Routes برای ضبط صفحه (Screen Recording) در بازرس ویژه.

جریان:
1. POST /screen-recording/start  → ساخت رکورد metadata (status=recording)
2. POST /screen-recording/{id}/upload → آپلود فایل ویدئو/صدا (multipart)
3. POST /screen-recording/{id}/finalize → ثبت لاگ‌ها/تعاملات/transcript و
   بستن رکورد (status=ready/transcribed)
4. GET  /screen-recording/{id}  → خواندن metadata
5. GET  /screen-recording/file/{file_id} → دانلود فایل ذخیره‌شده

ضبط واقعی صدا/ویدئو در فرانت‌اند (MediaRecorder) انجام می‌شود؛ بک‌اند
صرفاً ذخیره، transcription و آماده‌سازی برای ساخت پرامپت قوی را برعهده
دارد.
"""

import json
import logging
from typing import List, Optional, Dict, Any

from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ...core.database import get_db
from ...core.logging_utils import StructuredLogger
from ...models.screen_recording import ScreenRecording
from ...services.storage_service import get_storage_service

slog = StructuredLogger(__name__, "SCREEN-REC")
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/screen-recording", tags=["ScreenRecording"])


class StartRecordingRequest(BaseModel):
    project_id: str
    inspector_session_id: Optional[str] = None
    audio_source: str = "mic"  # mic | system | both | none
    handsfree: bool = False


class FinalizeRecordingRequest(BaseModel):
    duration_ms: Optional[int] = None
    transcript: Optional[str] = None
    console_logs: Optional[List[Dict[str, Any]]] = None
    backend_logs: Optional[List[Dict[str, Any]]] = None
    user_interactions: Optional[List[Dict[str, Any]]] = None
    # اگر transcript ست نشده ولی audio_file_id موجود است و این True باشد،
    # سرویس transcription روی فایل صدا اجرا می‌شود.
    auto_transcribe: bool = True


_VALID_AUDIO_SOURCES = {"mic", "system", "both", "none"}


@router.post("/start")
async def start_recording(payload: StartRecordingRequest, db: Session = Depends(get_db)):
    """شروع یک جلسهٔ ضبط — یک رکورد metadata می‌سازد."""
    if not (payload.project_id or "").strip():
        raise HTTPException(status_code=400, detail="project_id خالی است")
    audio_source = payload.audio_source if payload.audio_source in _VALID_AUDIO_SOURCES else "mic"

    rec = ScreenRecording(
        project_id=payload.project_id,
        inspector_session_id=payload.inspector_session_id,
        audio_source=audio_source,
        handsfree=("true" if payload.handsfree else "false"),
        status="recording",
    )
    db.add(rec)
    db.commit()
    db.refresh(rec)

    slog.info(
        "🎬 شروع ضبط ویدئو از بازرس ویژه",
        project_id=payload.project_id,
        recording_id=rec.id,
        audio_source=audio_source,
        handsfree=payload.handsfree,
    )
    return {"success": True, "recording": rec.to_dict()}


@router.post("/{recording_id}/upload")
async def upload_recording_file(
    recording_id: int,
    file: UploadFile = File(...),
    kind: str = Form("video"),  # video | audio
    db: Session = Depends(get_db),
):
    """آپلود فایل ضبط‌شده (ویدئو یا صدا) و اتصال به رکورد."""
    rec = db.query(ScreenRecording).filter(ScreenRecording.id == recording_id).first()
    if not rec:
        raise HTTPException(status_code=404, detail="رکورد ضبط یافت نشد")
    if kind not in ("video", "audio"):
        raise HTTPException(status_code=400, detail="kind باید 'video' یا 'audio' باشد")

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="فایل خالی است")

    storage = get_storage_service()
    try:
        meta = await storage.save_file(
            content=content,
            original_name=file.filename or f"recording-{recording_id}-{kind}.webm",
            category="attachments",
            subcategory="screen-recordings",
            tags=["screen-recording", kind],
            metadata={"recording_id": recording_id, "project_id": rec.project_id},
        )
    except Exception as e:
        logger.error(f"save recording file failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"خطا در ذخیره فایل: {str(e)[:200]}")

    if kind == "video":
        rec.video_file_id = meta.id
    else:
        rec.audio_file_id = meta.id
    db.commit()
    db.refresh(rec)

    slog.info(
        "📤 فایل ضبط آپلود شد",
        recording_id=recording_id,
        kind=kind,
        file_id=meta.id,
        size=len(content),
    )
    return {"success": True, "file_id": meta.id, "kind": kind, "recording": rec.to_dict()}


@router.post("/{recording_id}/finalize")
async def finalize_recording(
    recording_id: int,
    payload: FinalizeRecordingRequest,
    db: Session = Depends(get_db),
):
    """بستن ضبط: ثبت لاگ‌ها/تعاملات/transcript. در صورت نبود transcript و
    وجود فایل صدا، تلاش برای تبدیل گفتار به متن.
    """
    rec = db.query(ScreenRecording).filter(ScreenRecording.id == recording_id).first()
    if not rec:
        raise HTTPException(status_code=404, detail="رکورد ضبط یافت نشد")

    if payload.duration_ms is not None:
        rec.duration_ms = payload.duration_ms
    if payload.console_logs is not None:
        rec.console_logs = json.dumps(payload.console_logs, ensure_ascii=False)
    if payload.backend_logs is not None:
        rec.backend_logs = json.dumps(payload.backend_logs, ensure_ascii=False)
    if payload.user_interactions is not None:
        rec.user_interactions = json.dumps(payload.user_interactions, ensure_ascii=False)

    transcript = (payload.transcript or "").strip()
    transcription_error: Optional[str] = None

    if not transcript and payload.auto_transcribe and rec.audio_file_id and rec.audio_source != "none":
        transcript, transcription_error = await _maybe_transcribe(rec)

    if transcript:
        rec.transcript = transcript
        rec.status = "transcribed"
    else:
        rec.status = "ready"

    db.commit()
    db.refresh(rec)

    slog.info(
        "✅ ضبط بسته شد",
        recording_id=recording_id,
        status=rec.status,
        has_transcript=bool(transcript),
        transcription_error=transcription_error,
    )
    result = {"success": True, "recording": rec.to_dict()}
    if transcription_error:
        result["transcription_error"] = transcription_error
    return result


async def _maybe_transcribe(rec: ScreenRecording):
    """تلاش best-effort برای transcription فایل صدای رکورد."""
    try:
        storage = get_storage_service()
        got = await storage.get_file(rec.audio_file_id)
        if not got:
            return "", "فایل صدا برای transcription یافت نشد"
        content, meta = got
        from ...services.audio_transcription_service import transcribe_audio
        text = await transcribe_audio(
            content,
            mime_type=meta.mime_type or "audio/webm",
        )
        return text, None
    except ValueError as e:
        # نبود مدل/کلید — graceful: ضبط بدون transcript قابل استفاده است
        return "", str(e)[:300]
    except Exception as e:
        logger.warning(f"auto-transcribe failed: {e}", exc_info=True)
        return "", f"خطا در transcription: {str(e)[:200]}"


@router.get("/{recording_id}")
async def get_recording(recording_id: int, db: Session = Depends(get_db)):
    """خواندن metadata کامل یک رکورد ضبط."""
    rec = db.query(ScreenRecording).filter(ScreenRecording.id == recording_id).first()
    if not rec:
        raise HTTPException(status_code=404, detail="رکورد ضبط یافت نشد")
    return {"success": True, "recording": rec.to_dict()}


@router.get("/list/{project_id}")
async def list_recordings(project_id: str, db: Session = Depends(get_db)):
    """لیست ضبط‌های یک پروژه (جدیدترین اول)."""
    recs = (
        db.query(ScreenRecording)
        .filter(ScreenRecording.project_id == project_id)
        .order_by(ScreenRecording.id.desc())
        .limit(100)
        .all()
    )
    return {"success": True, "recordings": [r.to_dict() for r in recs], "count": len(recs)}


@router.get("/file/{file_id}")
async def get_recording_file(file_id: str):
    """دانلود فایل ذخیره‌شدهٔ ضبط (ویدئو/صدا) برای نمایش در چت."""
    storage = get_storage_service()
    got = await storage.get_file(file_id)
    if not got:
        raise HTTPException(status_code=404, detail="فایل یافت نشد")
    content, meta = got
    return Response(
        content=content,
        media_type=meta.mime_type or "application/octet-stream",
        headers={"Content-Disposition": f'inline; filename="{meta.original_name}"'},
    )
