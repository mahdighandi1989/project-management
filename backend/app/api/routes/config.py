"""
⚙️ Configuration API Routes - مسیرهای تنظیمات
"""

from fastapi import APIRouter, HTTPException, Form
from pydantic import BaseModel
from typing import Dict, List, Optional, Any
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/config", tags=["Configuration"])


# =====================================
# Request Models
# =====================================

class ProcessingConfigUpdate(BaseModel):
    """بروزرسانی تنظیمات پردازش"""
    max_prompt_length: Optional[int] = None
    max_tokens_per_model: Optional[int] = None
    max_tokens_scoring: Optional[int] = None
    max_tokens_judge: Optional[int] = None
    max_tokens_summary: Optional[int] = None
    max_model_time: Optional[int] = None
    request_timeout: Optional[int] = None
    max_concurrent_requests: Optional[int] = None
    auto_retry: Optional[bool] = None
    retry_count: Optional[int] = None


class StorageConfigUpdate(BaseModel):
    """بروزرسانی تنظیمات ذخیره‌سازی"""
    max_upload_size_mb: Optional[int] = None
    max_chunk_size_mb: Optional[int] = None
    github_enabled: Optional[bool] = None


class ModelConfigUpdate(BaseModel):
    """بروزرسانی تنظیمات مدل"""
    max_tokens: Optional[int] = None
    max_context: Optional[int] = None
    timeout: Optional[int] = None
    temperature: Optional[float] = None
    enabled: Optional[bool] = None
    priority: Optional[int] = None


class AutoAdjustRequest(BaseModel):
    """درخواست تنظیم خودکار"""
    task_type: str
    content_length: int = 0
    file_count: int = 0
    complexity: str = "medium"


# =====================================
# Helper
# =====================================

def get_config_service():
    from ...services.dynamic_config import get_config_service as _get
    return _get()


# =====================================
# Endpoints
# =====================================

@router.get("")
@router.get("/")
async def get_full_config():
    """دریافت کل تنظیمات"""
    try:
        service = get_config_service()
        return {
            "success": True,
            "config": service.get_full_config()
        }
    except Exception as e:
        logger.error(f"Error getting config: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/processing")
async def get_processing_config():
    """دریافت تنظیمات پردازش"""
    try:
        from dataclasses import asdict
        service = get_config_service()
        config = service.get_processing_config()
        return {
            "success": True,
            "processing": asdict(config)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/processing")
async def update_processing_config(update: ProcessingConfigUpdate):
    """بروزرسانی تنظیمات پردازش"""
    try:
        from dataclasses import asdict
        service = get_config_service()

        # فقط مقادیر غیر None
        updates = {k: v for k, v in update.dict().items() if v is not None}

        if not updates:
            return {"success": False, "error": "هیچ تنظیمی برای بروزرسانی ارسال نشده"}

        config = service.update_processing_config(**updates)

        return {
            "success": True,
            "message": f"{len(updates)} تنظیم بروز شد",
            "processing": asdict(config)
        }
    except Exception as e:
        logger.error(f"Error updating processing config: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/storage")
async def get_storage_config():
    """دریافت تنظیمات ذخیره‌سازی"""
    try:
        from dataclasses import asdict
        service = get_config_service()
        config = service.get_storage_config()
        return {
            "success": True,
            "storage": asdict(config)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/storage")
async def update_storage_config(update: StorageConfigUpdate):
    """بروزرسانی تنظیمات ذخیره‌سازی"""
    try:
        from dataclasses import asdict
        service = get_config_service()

        updates = {k: v for k, v in update.dict().items() if v is not None}

        if not updates:
            return {"success": False, "error": "هیچ تنظیمی ارسال نشده"}

        config = service.update_storage_config(**updates)

        return {
            "success": True,
            "message": f"{len(updates)} تنظیم بروز شد",
            "storage": asdict(config)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/models")
async def get_all_model_configs():
    """دریافت تنظیمات همه مدل‌ها"""
    try:
        from dataclasses import asdict
        service = get_config_service()
        models = service.get_all_model_configs()
        return {
            "success": True,
            "models": {k: asdict(v) for k, v in models.items()}
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/models/{model_id}")
async def get_model_config(model_id: str):
    """دریافت تنظیمات یک مدل"""
    try:
        from dataclasses import asdict
        service = get_config_service()
        config = service.get_model_config(model_id)

        if not config:
            raise HTTPException(status_code=404, detail="مدل یافت نشد")

        return {
            "success": True,
            "model": asdict(config)
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/models/{model_id}")
async def update_model_config(model_id: str, update: ModelConfigUpdate):
    """بروزرسانی تنظیمات یک مدل"""
    try:
        from dataclasses import asdict
        service = get_config_service()

        updates = {k: v for k, v in update.dict().items() if v is not None}

        if not updates:
            return {"success": False, "error": "هیچ تنظیمی ارسال نشده"}

        config = service.update_model_config(model_id, **updates)

        return {
            "success": True,
            "message": f"تنظیمات {model_id} بروز شد",
            "model": asdict(config)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/auto-adjust")
async def auto_adjust_config(request: AutoAdjustRequest):
    """
    دریافت تنظیمات پیشنهادی بر اساس نوع وظیفه

    نوع‌های وظیفه:
    - code_generation
    - analysis
    - debate
    - creative
    - research
    - file_analysis
    """
    try:
        service = get_config_service()

        suggested = service.auto_adjust_for_task(
            task_type=request.task_type,
            content_length=request.content_length,
            file_count=request.file_count,
            complexity=request.complexity
        )

        return {
            "success": True,
            "task_type": request.task_type,
            "complexity": request.complexity,
            "suggested_config": suggested
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/recommended-models")
async def get_recommended_models(
    task_type: str = "code_generation"
):
    """دریافت مدل‌های پیشنهادی برای یک وظیفه"""
    try:
        from ...services.ai_manager import get_ai_manager

        service = get_config_service()
        ai_manager = get_ai_manager()
        available = ai_manager.get_available_providers()

        recommended = service.get_recommended_models(task_type, available)

        return {
            "success": True,
            "task_type": task_type,
            "recommended_models": recommended
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history")
async def get_config_history(limit: int = 20):
    """دریافت تاریخچه تغییرات"""
    try:
        service = get_config_service()
        history = service.get_history(limit)

        return {
            "success": True,
            "history": history
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/reset")
async def reset_to_defaults():
    """بازگشت به تنظیمات پیش‌فرض"""
    try:
        service = get_config_service()
        service.reset_to_defaults()

        return {
            "success": True,
            "message": "تنظیمات به حالت پیش‌فرض بازگشت"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
