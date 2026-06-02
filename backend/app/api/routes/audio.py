# -*- coding: utf-8 -*-
"""
🎙 API Routes برای تبدیل گفتار به متن (Audio Transcription).

endpoint مستقل که یک فایل صوتی می‌گیرد و transcript برمی‌گرداند.
هم توسط ضبط صفحه و هم به‌صورت standalone (مثلاً پیام صوتی در چت)
قابل استفاده است.
"""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, UploadFile, File, Form

from ...core.logging_utils import StructuredLogger

slog = StructuredLogger(__name__, "AUDIO-API")
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/audio", tags=["Audio"])

# سقف امن برای آپلود inline (هماهنگ با سرویس transcription)
_MAX_UPLOAD_BYTES = 18 * 1024 * 1024


@router.post("/transcribe")
async def transcribe(
    file: UploadFile = File(...),
    context_hint: str = Form(""),
    model_id: Optional[str] = Form(None),
):
    """تبدیل یک فایل صوتی آپلودشده به متن."""
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="فایل صوتی خالی است")
    if len(content) > _MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"فایل صوتی بزرگ‌تر از حد مجاز ({_MAX_UPLOAD_BYTES // (1024*1024)}MB) است",
        )

    mime = file.content_type or "audio/webm"
    from ...services.audio_transcription_service import transcribe_audio
    try:
        text = await transcribe_audio(
            content,
            mime_type=mime,
            context_hint=context_hint,
            model_id=(model_id or None),
        )
    except ValueError as e:
        # نبود مدل/کلید مناسب
        raise HTTPException(status_code=422, detail=str(e)[:300])
    except Exception as e:
        logger.error(f"transcription failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"خطا در transcription: {str(e)[:200]}")

    slog.info("🎙 transcription انجام شد", size=len(content), chars=len(text))
    return {"success": True, "transcript": text, "chars": len(text)}
