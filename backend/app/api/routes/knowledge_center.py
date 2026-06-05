# -*- coding: utf-8 -*-
"""
📚 Knowledge Center API — مرکز دانش

Endpoints:
  GET  /api/knowledge-center/entries           — لیست فهرست‌بندی‌شده + TOC + دسته‌بندی
  GET  /api/knowledge-center/entries/{id}       — یک تجربهٔ خاص
  POST /api/knowledge-center/sync               — سینک پوشه‌های experiences همهٔ پروژه‌ها
  POST /api/knowledge-center/ensure-folders     — ساخت پوشهٔ experiences برای همهٔ پروژه‌ها
  POST /api/knowledge-center/import             — ایمپورت فایل چت (txt/md/html/pdf) + استخراج
"""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, UploadFile, File

from ...services.knowledge_center_service import get_knowledge_center_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/knowledge-center", tags=["Knowledge Center"])


@router.get("/entries")
async def list_entries(category: Optional[str] = None):
    """لیست فهرست‌بندی‌شدهٔ تجربیات همراه با TOC و دسته‌بندی."""
    svc = get_knowledge_center_service()
    return svc.get_entries(category=category)


@router.get("/entries/{entry_id}")
async def get_entry(entry_id: str):
    """جزئیات یک تجربهٔ خاص."""
    svc = get_knowledge_center_service()
    entry = svc.get_entry(entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail="تجربه یافت نشد")
    return entry


@router.post("/sync")
async def sync_experiences():
    """سینک محتوای پوشه‌های experiences همهٔ پروژه‌های تحت نظارت با دانشنامه."""
    svc = get_knowledge_center_service()
    try:
        return await svc.sync_experiences()
    except Exception as e:
        logger.error(f"knowledge-center sync failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ensure-folders")
async def ensure_folders():
    """ساخت idempotent پوشهٔ experiences در مخزن همهٔ پروژه‌های تحت نظارت."""
    svc = get_knowledge_center_service()
    try:
        return await svc.ensure_all_experiences_folders()
    except Exception as e:
        logger.error(f"knowledge-center ensure-folders failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/import")
async def import_chat(file: UploadFile = File(...)):
    """ایمپورت یک فایل چت (txt/md/html/pdf) و استخراج تجربیات با AI + merge/dedup."""
    svc = get_knowledge_center_service()
    try:
        content = await file.read()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"خواندن فایل ناموفق بود: {e}")
    if not content:
        raise HTTPException(status_code=400, detail="فایل خالی است")
    result = await svc.import_chat(
        filename=file.filename or "chat.txt",
        content=content,
        mime=file.content_type or "",
    )
    if not result.get("success"):
        raise HTTPException(status_code=422, detail=result.get("error", "ایمپورت ناموفق"))
    return result
