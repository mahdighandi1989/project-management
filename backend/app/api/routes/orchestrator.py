"""
🎯 Smart Orchestrator API Routes
مسیرهای API برای هماهنگ‌کننده هوشمند
"""

from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Query, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import io
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/orchestrator", tags=["Smart Orchestrator"])


# =====================================
# Auto-Detection Helper Functions
# =====================================

def get_optimal_settings_for_file(filename: str, file_size: int) -> Dict[str, Any]:
    """
    تشخیص خودکار تنظیمات بهینه بر اساس نوع فایل و اندازه
    """
    extension = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
    size_mb = file_size / (1024 * 1024)

    # تنظیمات پیش‌فرض
    settings = {
        "max_tokens": 4000,
        "temperature": 0.7,
        "timeout": 120,
        "chunk_size": 50000,  # 50KB per chunk
        "recommended_model": "gpt-4o-mini",
        "analysis_type": "general",
        "file_category": "other"
    }

    # کد و برنامه‌نویسی
    code_extensions = {
        'py', 'js', 'ts', 'jsx', 'tsx', 'java', 'cpp', 'c', 'h', 'go', 'rs',
        'php', 'rb', 'swift', 'kt', 'mq4', 'mq5', 'mqh', 'sql', 'sh', 'bat',
        'vue', 'svelte', 'astro', 'graphql', 'proto'
    }
    if extension in code_extensions:
        settings.update({
            "max_tokens": 8000,
            "temperature": 0.2,  # کمتر برای کد
            "timeout": 180,
            "chunk_size": 100000,  # 100KB
            "recommended_model": "claude-3-5-sonnet-20241022" if size_mb > 1 else "gpt-4o",
            "analysis_type": "code_review",
            "file_category": "code"
        })

    # Trading/MetaTrader
    elif extension in {'mq4', 'mq5', 'mqh', 'ex4', 'ex5'}:
        settings.update({
            "max_tokens": 16000,  # بیشتر برای Expert Advisor ها
            "temperature": 0.1,
            "timeout": 300,
            "chunk_size": 150000,
            "recommended_model": "claude-3-5-sonnet-20241022",
            "analysis_type": "trading_code_analysis",
            "file_category": "trading"
        })

    # اسناد متنی
    elif extension in {'txt', 'md', 'rtf', 'tex'}:
        settings.update({
            "max_tokens": 4000,
            "temperature": 0.5,
            "timeout": 120,
            "recommended_model": "gpt-4o-mini",
            "analysis_type": "text_analysis",
            "file_category": "document"
        })

    # PDF و اسناد پیچیده
    elif extension in {'pdf', 'doc', 'docx', 'ppt', 'pptx'}:
        settings.update({
            "max_tokens": 8000,
            "temperature": 0.3,
            "timeout": 240,
            "recommended_model": "gpt-4o",  # برای اسناد پیچیده
            "analysis_type": "document_analysis",
            "file_category": "document"
        })

    # داده و JSON/YAML
    elif extension in {'json', 'yaml', 'yml', 'xml', 'csv'}:
        settings.update({
            "max_tokens": 8000,
            "temperature": 0.2,
            "timeout": 180,
            "recommended_model": "gpt-4o-mini",
            "analysis_type": "data_analysis",
            "file_category": "data"
        })

    # Excel
    elif extension in {'xlsx', 'xls'}:
        settings.update({
            "max_tokens": 16000,
            "temperature": 0.3,
            "timeout": 300,
            "recommended_model": "gpt-4o",
            "analysis_type": "spreadsheet_analysis",
            "file_category": "data"
        })

    # تصویر
    elif extension in {'jpg', 'jpeg', 'png', 'gif', 'webp', 'bmp', 'svg'}:
        settings.update({
            "max_tokens": 4000,
            "temperature": 0.5,
            "timeout": 120,
            "recommended_model": "gpt-4o",  # مدل با قابلیت vision
            "analysis_type": "image_analysis",
            "file_category": "image"
        })

    # صوت و ویدیو
    elif extension in {'mp3', 'wav', 'mp4', 'webm', 'avi', 'mov', 'mkv'}:
        settings.update({
            "max_tokens": 4000,
            "temperature": 0.5,
            "timeout": 300,
            "recommended_model": "whisper-1",  # برای صوت
            "analysis_type": "media_transcription",
            "file_category": "media"
        })

    # آرشیو
    elif extension in {'zip', 'tar', 'gz', 'rar', '7z'}:
        settings.update({
            "max_tokens": 2000,
            "temperature": 0.5,
            "timeout": 60,
            "recommended_model": "gpt-4o-mini",
            "analysis_type": "archive_listing",
            "file_category": "archive"
        })

    # تنظیم بر اساس حجم فایل
    if size_mb > 10:
        settings["timeout"] = max(settings["timeout"], 300)
        settings["max_tokens"] = max(settings["max_tokens"], 8000)
    if size_mb > 50:
        settings["timeout"] = 600
        settings["max_tokens"] = 16000
    if size_mb > 100:
        settings["max_tokens"] = 32000
        settings["recommended_model"] = "claude-3-5-sonnet-20241022"

    return settings


# =====================================
# Request/Response Models
# =====================================

class SmartSetupRequest(BaseModel):
    """درخواست راه‌اندازی هوشمند"""
    request: str  # درخواست کاربر به زبان ساده


class TaskExecuteRequest(BaseModel):
    """درخواست اجرای وظیفه"""
    project_id: str
    task: str
    category: str = "code_generation"  # TaskCategory


class EvaluateRequest(BaseModel):
    """درخواست ارزیابی"""
    task: str
    model_id: str
    output: str


class CompareModelsRequest(BaseModel):
    """درخواست مقایسه مدل‌ها"""
    task: str
    outputs: Dict[str, str]  # model_id -> output


class ModelSelectRequest(BaseModel):
    """درخواست انتخاب مدل"""
    category: str
    exclude: List[str] = []


class FileAnalysisRequest(BaseModel):
    """درخواست تحلیل فایل"""
    project_id: Optional[str] = None
    debate_id: Optional[str] = None
    analysis_type: str = "full"  # full, summary, code_review


# =====================================
# Helper Functions
# =====================================

def get_orchestrator():
    """دریافت instance هماهنگ‌کننده"""
    from ...services.smart_orchestrator import get_smart_orchestrator
    orchestrator = get_smart_orchestrator()

    if not orchestrator.is_initialized():
        # مقداردهی اولیه
        try:
            from ...services.ai_manager import get_ai_manager
            from ...services.project_service import get_project_service
            from ...services.creator_engine import get_creator_engine

            ai_manager = get_ai_manager()
            project_service = get_project_service()
            creator_engine = get_creator_engine()
            creator_engine.initialize(ai_manager)

            orchestrator.initialize(ai_manager, project_service, creator_engine)
        except Exception as e:
            logger.error(f"Failed to initialize orchestrator: {e}")
            raise HTTPException(status_code=500, detail=f"خطا در مقداردهی سیستم: {str(e)}")

    return orchestrator


def get_github_storage():
    """دریافت سرویس GitHub"""
    from ...services.github_storage import get_github_storage as _get_github
    return _get_github()


# =====================================
# Smart Setup Endpoints
# =====================================

@router.post("/smart-setup")
async def smart_project_setup(request: SmartSetupRequest):
    """
    راه‌اندازی هوشمند پروژه از یک درخواست ساده

    از یک توضیح ساده، پروژه را با فازها، تکنولوژی‌ها و ساختار کامل ایجاد می‌کند.
    """
    try:
        orchestrator = get_orchestrator()
        result = await orchestrator.smart_setup(request.request)
        return result
    except Exception as e:
        logger.error(f"Error in smart setup: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/execute-task")
async def execute_monitored_task(request: TaskExecuteRequest):
    """
    اجرای وظیفه با نظارت و بازخورد

    - انتخاب هوشمند مدل
    - اجرای وظیفه
    - ارزیابی توسط مدل ناظر
    - بررسی انحراف از هدف
    - تلاش مجدد در صورت نیاز
    """
    try:
        from ...services.smart_orchestrator import TaskCategory

        orchestrator = get_orchestrator()
        category = TaskCategory(request.category)

        result = await orchestrator.execute_task(
            request.project_id,
            request.task,
            category
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"دسته نامعتبر: {request.category}")
    except Exception as e:
        logger.error(f"Error executing task: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =====================================
# Evaluation Endpoints
# =====================================

@router.post("/evaluate")
async def evaluate_output(request: EvaluateRequest):
    """
    ارزیابی خروجی یک مدل

    معیارها:
    - صحت (accuracy)
    - کامل بودن (completeness)
    - مرتبط بودن (relevance)
    - وضوح (clarity)
    - عملی بودن (feasibility)
    """
    try:
        orchestrator = get_orchestrator()
        evaluation = await orchestrator.evaluate(
            request.task,
            request.model_id,
            request.output
        )

        return {
            "success": True,
            "evaluation": {
                "task_id": evaluation.task_id,
                "model_id": evaluation.model_id,
                "evaluator": evaluation.evaluator_model_id,
                "scores": evaluation.scores,
                "overall_score": evaluation.overall_score,
                "feedback": evaluation.feedback,
                "suggestions": evaluation.suggestions,
                "is_acceptable": evaluation.is_acceptable
            }
        }
    except Exception as e:
        logger.error(f"Error evaluating: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/compare-models")
async def compare_model_outputs(request: CompareModelsRequest):
    """
    مقایسه خروجی چند مدل و رتبه‌بندی

    - ارزیابی هر خروجی
    - رتبه‌بندی مدل‌ها
    - انتخاب بهترین
    """
    try:
        orchestrator = get_orchestrator()
        result = await orchestrator.compare_models(request.task, request.outputs)
        return result
    except Exception as e:
        logger.error(f"Error comparing: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =====================================
# Model Selection Endpoints
# =====================================

@router.post("/select-model")
async def select_best_model(request: ModelSelectRequest):
    """
    انتخاب بهترین مدل برای یک وظیفه

    بر اساس:
    - نوع وظیفه
    - تاریخچه عملکرد
    - در دسترس بودن
    """
    try:
        from ...services.smart_orchestrator import TaskCategory

        orchestrator = get_orchestrator()
        category = TaskCategory(request.category)

        model_id, confidence = orchestrator.select_model(category, request.exclude)

        return {
            "success": True,
            "model_id": model_id,
            "confidence": confidence,
            "category": request.category
        }
    except ValueError:
        raise HTTPException(status_code=400, detail=f"دسته نامعتبر: {request.category}")
    except Exception as e:
        logger.error(f"Error selecting model: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/model-categories")
async def get_task_categories():
    """لیست دسته‌بندی‌های وظایف"""
    from ...services.smart_orchestrator import TaskCategory

    return {
        "categories": [
            {"id": cat.value, "name": cat.name}
            for cat in TaskCategory
        ]
    }


# =====================================
# File Upload & Analysis
# =====================================

@router.post("/upload-for-analysis")
async def upload_file_for_analysis(
    file: UploadFile = File(...),
    project_id: Optional[str] = Form(default=None),
    debate_id: Optional[str] = Form(default=None),
    analysis_type: str = Form(default="full"),
    store_in_github: bool = Form(default=True)
):
    """
    آپلود فایل برای تحلیل با AI

    - ذخیره در storage محلی یا GitHub
    - تقسیم فایل‌های بزرگ
    - تحلیل محتوا با مدل مناسب
    """
    try:
        from ...services.storage_service import get_storage_service
        from ...services.smart_orchestrator import FileChunker, TaskCategory

        content = await file.read()
        filename = file.filename
        extension = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''

        # بررسی نیاز به تقسیم
        needs_chunking = FileChunker.should_chunk(len(content), f".{extension}")

        # ذخیره محلی
        storage = get_storage_service()
        category = "debates" if debate_id else "projects" if project_id else "attachments"
        subcategory = debate_id or project_id

        local_meta = await storage.save_file(
            content=content,
            original_name=filename,
            category=category,
            subcategory=subcategory,
            tags=["uploaded", "for_analysis"]
        )

        # تشخیص خودکار تنظیمات بهینه
        optimal_settings = get_optimal_settings_for_file(filename, len(content))

        result = {
            "success": True,
            "file_id": local_meta.id,
            "filename": filename,
            "size": len(content),
            "size_mb": round(len(content) / (1024 * 1024), 2),
            "needs_chunking": needs_chunking,
            "local_path": local_meta.relative_path,
            "optimal_settings": optimal_settings
        }

        # ذخیره در GitHub
        if store_in_github:
            github = get_github_storage()
            connection = await github.check_connection()

            if connection.get("success"):
                if needs_chunking:
                    gh_result = await github.upload_large_file(
                        content,
                        f"{category}/{subcategory}/uploaded/{filename}"
                    )
                else:
                    if debate_id:
                        gh_result = await github.save_debate_file(
                            debate_id, content, filename, "uploaded"
                        )
                    elif project_id:
                        gh_result = await github.save_project_file(
                            project_id, content, filename, "source"
                        )
                    else:
                        gh_result = await github.upload_file(
                            content, f"uploads/{filename}"
                        )

                result["github"] = gh_result

        # تحلیل اولیه
        if analysis_type != "none":
            orchestrator = get_orchestrator()

            # انتخاب دسته مناسب
            if extension in ['py', 'js', 'ts', 'java', 'cpp', 'go']:
                task_category = TaskCategory.CODE_REVIEW
            elif extension in ['jpg', 'png', 'gif', 'webp']:
                task_category = TaskCategory.IMAGE_ANALYSIS
            else:
                task_category = TaskCategory.FILE_ANALYSIS

            model_id, _ = orchestrator.select_model(task_category)
            result["suggested_model"] = model_id
            result["analysis_category"] = task_category.value

        return result

    except Exception as e:
        logger.error(f"Error uploading file: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/analyze-file/{file_id}")
async def analyze_uploaded_file(
    file_id: str,
    analysis_prompt: str = Form(default="این فایل را کامل تحلیل کن"),
    project_id: Optional[str] = Form(default=None)
):
    """تحلیل فایل آپلود شده"""
    try:
        from ...services.storage_service import get_storage_service
        from ...services.smart_orchestrator import TaskCategory

        storage = get_storage_service()
        file_data = await storage.get_file(file_id)

        if not file_data:
            raise HTTPException(status_code=404, detail="فایل یافت نشد")

        content, meta = file_data
        orchestrator = get_orchestrator()

        # تعیین نوع تحلیل
        extension = meta.original_name.rsplit('.', 1)[-1].lower() if '.' in meta.original_name else ''

        if extension in ['py', 'js', 'ts', 'java']:
            category = TaskCategory.CODE_REVIEW
            prompt = f"""کد زیر را کامل بررسی کن:

نام فایل: {meta.original_name}

```
{content.decode('utf-8', errors='replace')[:8000]}
```

{analysis_prompt}

موارد زیر را بررسی کن:
1. کیفیت کد
2. باگ‌های احتمالی
3. پیشنهادات بهبود
4. امنیت
5. کارایی"""
        else:
            category = TaskCategory.FILE_ANALYSIS
            prompt = f"""فایل زیر را تحلیل کن:

نام: {meta.original_name}
نوع: {meta.mime_type}
سایز: {meta.size} bytes

محتوا:
{content.decode('utf-8', errors='replace')[:8000]}

{analysis_prompt}"""

        if project_id:
            result = await orchestrator.execute_task(project_id, prompt, category)
        else:
            model_id, _ = orchestrator.select_model(category)

            from ...services.ai_manager import get_ai_manager
            ai_manager = get_ai_manager()

            response = await ai_manager.generate(
                model_id=model_id,
                prompt=prompt,
                max_tokens=4000
            )

            if response.get("success"):
                result = {
                    "success": True,
                    "analysis": response.get("content"),
                    "model_used": model_id
                }
            else:
                result = {"success": False, "error": response.get("error")}

        return {
            "success": True,
            "file_id": file_id,
            "filename": meta.original_name,
            "analysis_result": result
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error analyzing file: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =====================================
# GitHub Integration
# =====================================

@router.get("/github/status")
async def github_connection_status():
    """وضعیت اتصال به GitHub"""
    try:
        github = get_github_storage()
        return await github.check_connection()
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.post("/github/setup-folders")
async def setup_github_folders(
    entity_type: str = Form(...),  # debates, projects
    entity_id: str = Form(...)
):
    """ایجاد ساختار پوشه در GitHub"""
    try:
        github = get_github_storage()
        connection = await github.check_connection()

        if not connection.get("success"):
            raise HTTPException(status_code=400, detail="اتصال به GitHub برقرار نیست")

        result = await github.create_folder_structure(entity_type, entity_id)
        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error setting up folders: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/github/files/{entity_type}/{entity_id}")
async def get_github_files(entity_type: str, entity_id: str):
    """لیست فایل‌های یک موجودیت در GitHub"""
    try:
        github = get_github_storage()

        if entity_type == "debates":
            return await github.get_debate_files(entity_id)
        elif entity_type == "projects":
            return await github.get_project_files(entity_id)
        else:
            raise HTTPException(status_code=400, detail="نوع نامعتبر")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting files: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/github/save-output")
async def save_output_to_github(
    entity_type: str = Form(...),
    entity_id: str = Form(...),
    filename: str = Form(...),
    content: str = Form(...),
    file_type: str = Form(default="generated")
):
    """ذخیره خروجی در GitHub"""
    try:
        github = get_github_storage()
        connection = await github.check_connection()

        if not connection.get("success"):
            raise HTTPException(status_code=400, detail="اتصال به GitHub برقرار نیست")

        content_bytes = content.encode('utf-8')

        if entity_type == "debates":
            result = await github.save_debate_file(
                entity_id, content_bytes, filename, file_type
            )
        elif entity_type == "projects":
            result = await github.save_project_file(
                entity_id, content_bytes, filename, file_type
            )
        else:
            raise HTTPException(status_code=400, detail="نوع نامعتبر")

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error saving output: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =====================================
# Performance & Stats
# =====================================

@router.get("/performance/models")
async def get_model_performance():
    """عملکرد مدل‌ها"""
    try:
        orchestrator = get_orchestrator()

        if not orchestrator.model_selector:
            return {"success": False, "error": "سیستم مقداردهی نشده"}

        performance = {}
        for model_id, perf in orchestrator.model_selector.performance_history.items():
            performance[model_id] = {
                "total_tasks": perf.total_tasks,
                "successful_tasks": perf.successful_tasks,
                "success_rate": round(perf.successful_tasks / perf.total_tasks * 100, 1) if perf.total_tasks > 0 else 0,
                "average_score": round(perf.average_score, 1),
                "scores_by_category": perf.scores_by_category,
                "last_used": perf.last_used
            }

        return {
            "success": True,
            "models": performance
        }

    except Exception as e:
        logger.error(f"Error getting performance: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_orchestrator_stats():
    """آمار کلی سیستم"""
    try:
        orchestrator = get_orchestrator()

        stats = {
            "initialized": orchestrator.is_initialized(),
            "model_count": len(orchestrator.model_selector.MODEL_SPECIALTIES) if orchestrator.model_selector else 0,
            "evaluations_count": len(orchestrator.supervisor.evaluation_history) if orchestrator.supervisor else 0,
            "active_workflows": len(orchestrator.integrator.active_workflows) if orchestrator.integrator else 0
        }

        return {"success": True, "stats": stats}

    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        return {"success": False, "error": str(e)}
