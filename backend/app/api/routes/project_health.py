# -*- coding: utf-8 -*-
"""
API Routes برای تحلیل سلامت پروژه و مدیریت Roadmap/README
Project Health Analysis API

شامل:
1. تنظیمات تحلیل (prompts, مدل‌ها, زمان‌بندی)
2. اجرای تحلیل موازی
3. مدیریت Roadmap و README
4. دریافت نتایج و رنگ‌بندی
"""

import json
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel

from ...core.database import get_db
from ...models.project import Project, ProjectFile
from ...services.project_health_analyzer import get_project_health_analyzer
from ...services.report_validator import get_report_validator
from ...services.model_profiler import get_model_profiler

router = APIRouter(prefix="/api/projects", tags=["project-health"])


# =====================================
# Pydantic Models
# =====================================

class AnalysisSettingsRequest(BaseModel):
    """تنظیمات تحلیل سلامت"""
    instruction: str = "تمام پروژه را از ریز تا درشت بررسی کن"
    target_models: List[str] = ["all"]
    trigger_enabled: bool = True
    trigger_interval_minutes: int = 60
    trigger_interval_type: str = "minutes"  # minutes, hours, daily, weekly
    auto_analyze_on_import: bool = True
    criteria_weights: Optional[dict] = None


class RunAnalysisRequest(BaseModel):
    """درخواست اجرای تحلیل"""
    model_ids: Optional[List[str]] = None  # خالی = همه مدل‌های فعال
    full_analysis: bool = True  # بررسی همه فایل‌ها
    update_roadmap: bool = True  # به‌روزرسانی roadmap
    update_readme: bool = True  # به‌روزرسانی readme


# =====================================
# Helper Functions
# =====================================

def _get_score_color(score: float) -> str:
    """تبدیل نمره به رنگ"""
    if score >= 90:
        return "green"
    elif score >= 70:
        return "yellow"
    elif score >= 50:
        return "orange"
    else:
        return "red"


class RoadmapUpdateRequest(BaseModel):
    """به‌روزرسانی Roadmap"""
    content: Optional[str] = None  # محتوای جدید (اختیاری)
    auto_generate: bool = True  # تولید خودکار توسط AI


class AnalysisScheduleRequest(BaseModel):
    """تنظیم زمان‌بندی تحلیل"""
    enabled: bool = True
    interval_type: str = "daily"  # minutes, hours, daily, weekly
    interval_value: int = 1
    target_models: List[str] = ["all"]


# =====================================
# API Endpoints
# =====================================

@router.get("/debug/ai-status")
async def debug_ai_status():
    """
    بررسی وضعیت AI - برای تشخیص مشکلات

    این endpoint نشون میده:
    - چه provider هایی فعال هستند
    - چه مدل‌هایی در دسترس هستند
    - آیا API key ها درست تنظیم شدن
    """
    import os
    from ...services.ai_manager import get_ai_manager
    from ...core.config import settings

    # چک کردن API keys (فقط اینکه وجود دارن، نه مقدارشون)
    api_keys_status = {
        "OPENAI_API_KEY": bool(os.environ.get("OPENAI_API_KEY")),
        "CLAUDE_API_KEY": bool(os.environ.get("CLAUDE_API_KEY")),
        "GEMINI_API_KEY": bool(os.environ.get("GEMINI_API_KEY")),
        "DEEPSEEK_API_KEY": bool(os.environ.get("DEEPSEEK_API_KEY")),
        "PERPLEXITY_API_KEY": bool(os.environ.get("PERPLEXITY_API_KEY")),
        "GROQ_API_KEY": bool(os.environ.get("GROQ_API_KEY")),
    }

    # چک کردن از دیتابیس
    db_keys_status = {}
    try:
        from ...core.database import SessionLocal
        from ...models.setting import Setting
        db = SessionLocal()
        for db_key in ["api_key_openai", "api_key_claude", "api_key_deepseek", "api_key_gemini", "api_key_perplexity"]:
            value = Setting.get_value(db, db_key)
            db_keys_status[db_key] = bool(value)
        db.close()
    except Exception as e:
        db_keys_status["error"] = str(e)

    # دریافت AI manager
    try:
        ai_manager = get_ai_manager()
        available_providers = ai_manager.get_available_providers()
        available_models = [{"id": m.id, "provider": m.provider.value} for m in ai_manager.get_available_models()]

        # چک کردن وضعیت error هر سرویس
        services_status = {}
        for provider, service in ai_manager._services.items():
            services_status[provider.value] = {
                "initialized": True,
                "in_error_state": service.is_in_error_state()
            }
    except Exception as e:
        available_providers = []
        available_models = []
        services_status = {}
        error = str(e)
    else:
        error = None

    # خواندن از settings
    settings_providers = settings.get_available_providers()

    return {
        "success": True,
        "api_keys_in_env": api_keys_status,
        "api_keys_in_db": db_keys_status,
        "settings_providers": settings_providers,
        "ai_manager_providers": available_providers,
        "services_status": services_status,
        "available_models": available_models,
        "any_model_available": len(available_models) > 0,
        "models_count": len(available_models),
        "error": error,
        "hints": {
            "no_models": "اگر مدلی در دسترس نیست، API key ها را چک کنید",
            "only_openai": "اگر فقط GPT مدل‌ها هستند، کلیدهای Claude/DeepSeek را وارد کنید",
            "db_vs_env": "کلیدهای دیتابیس در startup به environment منتقل می‌شوند"
        }
    }


@router.post("/{project_id}/health/analyze-direct")
async def run_direct_analysis(project_id: str, db=Depends(get_db)):
    """
    تحلیل مستقیم (بدون background task) برای تست

    این endpoint تحلیل را به صورت همزمان اجرا می‌کند
    و نتیجه را مستقیم برمی‌گرداند
    """
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"🔬 Starting DIRECT analysis for project {project_id}")

    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="پروژه یافت نشد")

    # دریافت فایل‌های پروژه
    files = db.query(ProjectFile).filter(ProjectFile.project_id == project_id).all()
    files_data = [
        {
            "path": f.file_path,
            "content": f.content or "",
            "file_type": f.file_type
        }
        for f in files
    ]

    if not files_data:
        return {
            "success": False,
            "error": "پروژه فایلی ندارد"
        }

    # بررسی مدل‌های در دسترس
    from ...services.ai_manager import get_ai_manager
    ai_manager = get_ai_manager()
    available_models = ai_manager.get_available_models()
    available_providers = ai_manager.get_available_providers()

    logger.info(f"📊 Available providers: {available_providers}")
    logger.info(f"📊 Available models: {[m.id for m in available_models]}")

    if not available_models:
        return {
            "success": False,
            "error": "هیچ مدل AI در دسترس نیست",
            "available_providers": available_providers,
            "hint": "لطفا کلیدهای API را در تنظیمات یا متغیرهای محیطی وارد کنید"
        }

    model_ids = [m.id for m in available_models[:2]]  # حداکثر 2 مدل برای تست

    # اجرای تحلیل مستقیم
    try:
        from ...services.deep_analysis_service import get_deep_analysis_service

        deep_analyzer = get_deep_analysis_service(ai_manager)
        logger.info(f"✅ Deep analyzer initialized, AI manager: {deep_analyzer.ai_manager is not None}")

        analysis_result = await deep_analyzer.run_full_analysis(
            project_id=project_id,
            files=files_data,
            roadmap_content=project.roadmap_content or "",
            readme_content=project.readme_content or "",
            model_ids=model_ids,
            instruction="تحلیل کامل پروژه",
            db_session=db
        )

        # ذخیره نتایج
        if analysis_result.get("status") == "completed":
            project.health_scores = json.dumps(
                analysis_result.get("overall_scores", {}),
                ensure_ascii=False
            )
            project.file_health_map = json.dumps(
                analysis_result.get("file_health_map", {}),
                ensure_ascii=False
            )
            project.issues_found = json.dumps(
                analysis_result.get("issues", [])[:100],
                ensure_ascii=False
            )
            project.last_analysis_at = datetime.utcnow()
            project.last_analysis_models = json.dumps(model_ids, ensure_ascii=False)
            db.commit()
            logger.info(f"✅ Direct analysis completed and saved!")

        return {
            "success": True,
            "message": "تحلیل مستقیم انجام شد",
            "analysis_result": analysis_result,
            "models_used": model_ids,
            "files_analyzed": len(files_data)
        }

    except Exception as e:
        logger.error(f"❌ Direct analysis failed: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "models_attempted": model_ids
        }


@router.get("/{project_id}/health")
async def get_project_health(project_id: str, db=Depends(get_db)):
    """
    دریافت وضعیت سلامت پروژه

    شامل:
    - نمرات کلی
    - رنگ‌بندی فایل‌ها
    - آخرین تحلیل
    - ایرادات شناسایی شده
    """
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="پروژه یافت نشد")

    # پارس داده‌ها
    health_scores = {}
    file_health_map = {}
    issues_found = []
    analysis_settings = {}

    try:
        if project.health_scores:
            health_scores = json.loads(project.health_scores)
        if project.file_health_map:
            file_health_map = json.loads(project.file_health_map)
        if project.issues_found:
            issues_found = json.loads(project.issues_found)
        if project.analysis_settings:
            analysis_settings = json.loads(project.analysis_settings)
    except:
        pass

    return {
        "success": True,
        "project_id": project_id,
        "health": {
            "scores": {
                # تبدیل نام کلیدها به فرمت مورد انتظار frontend
                "overall": health_scores.get("total", health_scores.get("overall", 0)),
                "overall_color": _get_score_color(health_scores.get("total", 0)),
                "structure_score": health_scores.get("structural", 0),
                "file_scores": {
                    "code_quality": health_scores.get("micro", 0),
                    "documentation": health_scores.get("documentation", 50),
                    "security": health_scores.get("security", 50),
                    "cooperation": health_scores.get("macro", 0),
                    "roadmap_compliance": health_scores.get("roadmap_compliance", 50),
                }
            },
            "overall_score": health_scores.get("total", health_scores.get("overall", 0)),
            "overall_color": _get_score_color(health_scores.get("total", 0)),
            "file_health_map": file_health_map,
            "issues_found": issues_found,
            "issues_count": len(issues_found),
        },
        "last_analysis": {
            "id": project.last_analysis_id,
            "at": project.last_analysis_at.isoformat() if project.last_analysis_at else None,
            "models": json.loads(project.last_analysis_models) if project.last_analysis_models else []
        },
        "roadmap_exists": bool(project.roadmap_content),
        "readme_exists": bool(project.readme_content),
        "ideal_state": project.ideal_state,
        "analysis_settings": analysis_settings
    }


@router.get("/{project_id}/health/settings")
async def get_analysis_settings(project_id: str, db=Depends(get_db)):
    """دریافت تنظیمات تحلیل پروژه"""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="پروژه یافت نشد")

    settings = {}
    try:
        if project.analysis_settings:
            settings = json.loads(project.analysis_settings)
    except:
        pass

    # مقادیر پیش‌فرض
    default_settings = {
        "instruction": "تمام پروژه را از ریز تا درشت بررسی کن و ساختار کامل آن را استخراج کن",
        "target_models": ["all"],
        "trigger_enabled": True,
        "trigger_interval_minutes": 60,
        "trigger_interval_type": "minutes",
        "auto_analyze_on_import": True,
        "criteria_weights": {
            "code_quality": 0.25,
            "documentation": 0.15,
            "security": 0.20,
            "structure": 0.20,
            "roadmap_compliance": 0.20
        }
    }

    # ترکیب با مقادیر ذخیره‌شده
    for key, value in default_settings.items():
        if key not in settings:
            settings[key] = value

    return {
        "success": True,
        "project_id": project_id,
        "settings": settings
    }


@router.put("/{project_id}/health/settings")
async def update_analysis_settings(
    project_id: str,
    request: AnalysisSettingsRequest,
    db=Depends(get_db)
):
    """به‌روزرسانی تنظیمات تحلیل پروژه"""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="پروژه یافت نشد")

    settings = {
        "instruction": request.instruction,
        "target_models": request.target_models,
        "trigger_enabled": request.trigger_enabled,
        "trigger_interval_minutes": request.trigger_interval_minutes,
        "trigger_interval_type": request.trigger_interval_type,
        "auto_analyze_on_import": request.auto_analyze_on_import,
        "criteria_weights": request.criteria_weights or {
            "code_quality": 0.25,
            "documentation": 0.15,
            "security": 0.20,
            "structure": 0.20,
            "roadmap_compliance": 0.20
        },
        "updated_at": datetime.utcnow().isoformat()
    }

    project.analysis_settings = json.dumps(settings, ensure_ascii=False)
    db.commit()

    return {
        "success": True,
        "message": "تنظیمات ذخیره شد",
        "settings": settings
    }


@router.post("/{project_id}/health/analyze")
async def run_health_analysis(
    project_id: str,
    request: RunAnalysisRequest,
    background_tasks: BackgroundTasks,
    db=Depends(get_db)
):
    """
    اجرای تحلیل سلامت پروژه

    - تحلیل موازی توسط مدل‌های انتخابی
    - بررسی هر فایل به صورت جداگانه
    - بررسی ساختار و سیم‌کشی
    - به‌روزرسانی roadmap و readme
    - نمره‌گذاری و رنگ‌بندی
    """
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="پروژه یافت نشد")

    # دریافت فایل‌های پروژه
    files = db.query(ProjectFile).filter(ProjectFile.project_id == project_id).all()
    files_data = [
        {
            "path": f.file_path,
            "content": f.content or "",
            "file_type": f.file_type
        }
        for f in files
    ]

    if not files_data:
        raise HTTPException(status_code=400, detail="پروژه فایلی ندارد")

    # اطلاعات پروژه
    project_info = {
        "name": project.name,
        "description": project.description,
        "type": project.project_type
    }

    # تعیین مدل‌ها
    from ...services.ai_manager import get_ai_manager
    ai_manager = get_ai_manager()
    available_models = ai_manager.get_available_models()
    available_providers = ai_manager.get_available_providers()

    model_ids = request.model_ids
    if not model_ids or "all" in model_ids:
        # دریافت همه مدل‌های فعال
        model_ids = [m.id for m in available_models[:3]]  # حداکثر 3 مدل

    # اگر هیچ مدلی در دسترس نیست، خطا بده (نه fallback!)
    if not model_ids and not available_models:
        return {
            "success": False,
            "error": "هیچ مدل AI در دسترس نیست",
            "hint": "لطفا کلیدهای API را در تنظیمات وارد کنید",
            "available_providers": available_providers,
            "project_id": project_id
        }

    if not model_ids:
        model_ids = [available_models[0].id] if available_models else []

    # اجرای تحلیل در background
    import asyncio
    # اطمینان از اجرای صحیح async task
    asyncio.create_task(
        _run_analysis_task(
            project_id=project_id,
            files_data=files_data,
            project_info=project_info,
            model_ids=model_ids,
            request=request
        )
    )

    return {
        "success": True,
        "message": "تحلیل شروع شد",
        "project_id": project_id,
        "models": model_ids,
        "available_models": [m.id for m in available_models],
        "available_providers": available_providers,
        "files_count": len(files_data),
        "status": "running"
    }


async def _run_analysis_task(
    project_id: str,
    files_data: list,
    project_info: dict,
    model_ids: list,
    request: RunAnalysisRequest
):
    """
    تسک پس‌زمینه برای اجرای تحلیل عمیق سه‌مرحله‌ای

    مراحل:
    1. Micro Analysis: بررسی تک‌تک فایل‌ها
    2. Macro Analysis: بررسی همکاری و جایگاه
    3. Structural Analysis: بررسی سیم‌کشی و ساختار
    """
    from ...core.database import SessionLocal
    from ...services.deep_analysis_service import get_deep_analysis_service
    from ...services.ai_manager import get_ai_manager
    import logging

    logger = logging.getLogger(__name__)
    logger.info(f"🚀 Starting analysis task for project {project_id}")
    logger.info(f"📁 Files count: {len(files_data)}, Models: {model_ids}")

    db = SessionLocal()

    try:
        # دریافت AI manager برای فراخوانی مدل‌ها
        ai_manager = get_ai_manager()

        # چک کردن وضعیت AI manager
        available_providers = ai_manager.get_available_providers()
        available_models = ai_manager.get_available_models()

        logger.info(f"🤖 Available providers: {available_providers}")
        logger.info(f"🤖 Available models: {[m.id for m in available_models]}")

        if not available_models:
            logger.error("❌ No AI models available! Check API keys in .env file")
            # ذخیره خطا در پروژه
            project = db.query(Project).filter(Project.id == project_id).first()
            if project:
                project.health_scores = json.dumps({
                    "error": "No AI models available",
                    "overall": 0,
                    "overall_color": "red"
                })
                project.issues_found = json.dumps([{
                    "severity": "critical",
                    "message": "هیچ مدل AI در دسترس نیست. کلیدهای API در فایل .env را بررسی کنید.",
                    "type": "config"
                }])
                db.commit()
            return

        # دریافت سرویس تحلیل عمیق
        deep_analyzer = get_deep_analysis_service(ai_manager)
        logger.info(f"✅ Deep analyzer initialized with AI manager: {deep_analyzer.ai_manager is not None}")

        # دریافت پروژه
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            logger.error(f"Project {project_id} not found")
            return

        # دریافت محتوای roadmap و readme
        roadmap_content = project.roadmap_content or ""
        readme_content = project.readme_content or ""

        # دریافت تنظیمات تحلیل
        analysis_settings = {}
        try:
            if project.analysis_settings:
                analysis_settings = json.loads(project.analysis_settings)
        except:
            pass

        instruction = analysis_settings.get("instruction", "تحلیل کامل پروژه را انجام بده")

        # 1. بررسی و به‌روزرسانی Roadmap (اختیاری)
        if request.update_roadmap:
            try:
                analyzer = get_project_health_analyzer()
                analyzer.initialize()

                roadmap_result = await analyzer.check_and_manage_roadmap(
                    project_id=project_id,
                    files=files_data,
                    project_info=project_info,
                    model_id=model_ids[0] if model_ids else None
                )
                roadmap_content = roadmap_result.get("roadmap_content", "")
                project.roadmap_content = roadmap_content
                project.ideal_state = roadmap_result.get("ideal_state", "")
            except Exception as e:
                logger.warning(f"Roadmap update failed: {e}")

        # 2. بررسی و به‌روزرسانی README (اختیاری)
        if request.update_readme:
            try:
                analyzer = get_project_health_analyzer()
                analyzer.initialize()

                readme_result = await analyzer.check_and_manage_readme(
                    project_id=project_id,
                    files=files_data,
                    project_info=project_info,
                    roadmap_content=roadmap_content,
                    model_id=model_ids[0] if model_ids else None
                )
                readme_content = readme_result.get("readme_content", "")
                project.readme_content = readme_content
            except Exception as e:
                logger.warning(f"README update failed: {e}")

        # 3. اجرای تحلیل عمیق سه‌مرحله‌ای
        logger.info(f"🔬 Starting deep analysis for project {project_id} with models: {model_ids}")

        try:
            analysis_result = await deep_analyzer.run_full_analysis(
                project_id=project_id,
                files=files_data,
                roadmap_content=roadmap_content,
                readme_content=readme_content,
                model_ids=model_ids,
                instruction=instruction,
                db_session=db
            )
            logger.info(f"📊 Analysis result status: {analysis_result.get('status')}")
            logger.info(f"📊 Files analyzed: {analysis_result.get('analyzed_files', 0)}")
            logger.info(f"📊 Overall scores: {analysis_result.get('overall_scores', {})}")
        except Exception as analysis_error:
            logger.error(f"❌ Deep analysis failed: {analysis_error}", exc_info=True)
            # ذخیره خطا
            project.health_scores = json.dumps({
                "error": str(analysis_error),
                "overall": 0,
                "overall_color": "red"
            })
            project.issues_found = json.dumps([{
                "severity": "critical",
                "message": f"خطا در تحلیل: {str(analysis_error)}",
                "type": "error"
            }])
            db.commit()
            return

        # 4. ذخیره نتایج
        if analysis_result.get("status") == "completed":
            project.health_scores = json.dumps(
                analysis_result.get("overall_scores", {}),
                ensure_ascii=False
            )
            project.file_health_map = json.dumps(
                analysis_result.get("file_health_map", {}),
                ensure_ascii=False
            )
            project.last_analysis_id = analysis_result.get("analysis_id")
            project.last_analysis_at = datetime.utcnow()
            project.last_analysis_models = json.dumps(model_ids, ensure_ascii=False)

            # ذخیره مشکلات
            project.issues_found = json.dumps(
                analysis_result.get("issues", [])[:100],
                ensure_ascii=False
            )

            # ذخیره حالت ایده‌آل
            if analysis_result.get("ideal_state"):
                project.ideal_state = analysis_result["ideal_state"]

            logger.info(f"✅ Analysis completed for project {project_id}. Score: {analysis_result.get('overall_scores', {}).get('total', 0):.1f}")
        else:
            logger.warning(f"⚠️ Analysis did not complete successfully: {analysis_result.get('status')}")
            if analysis_result.get("error"):
                logger.error(f"❌ Analysis error: {analysis_result.get('error')}")

        db.commit()
        logger.info(f"💾 Results saved to database for project {project_id}")

    except Exception as e:
        logger.error(f"❌ Analysis task error for {project_id}: {e}", exc_info=True)
        db.rollback()

        # ذخیره خطا در پروژه
        try:
            project = db.query(Project).filter(Project.id == project_id).first()
            if project:
                project.health_scores = json.dumps({
                    "error": str(e),
                    "overall": 0,
                    "overall_color": "red"
                })
                project.issues_found = json.dumps([{
                    "severity": "critical",
                    "message": f"خطای سیستمی در تحلیل: {str(e)}",
                    "type": "system_error"
                }])
                db.commit()
        except:
            pass

    finally:
        db.close()


@router.get("/{project_id}/health/file-map")
async def get_file_health_map(project_id: str, db=Depends(get_db)):
    """
    دریافت نقشه رنگی فایل‌ها برای دیاگرام

    هر فایل شامل:
    - score: نمره 0-100
    - color: نام رنگ (green, yellow, orange, red)
    - hex: کد رنگ برای CSS
    - models_analyzed: تعداد مدل‌های تحلیل‌کننده
    - analyzed_at: تاریخ آخرین تحلیل
    - model_scores: نمرات هر مدل
    """
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="پروژه یافت نشد")

    file_health_map = {}
    try:
        if project.file_health_map:
            file_health_map = json.loads(project.file_health_map)
    except:
        pass

    return {
        "success": True,
        "project_id": project_id,
        "file_map": file_health_map,
        "files_count": len(file_health_map),
        "last_analysis_at": project.last_analysis_at.isoformat() if project.last_analysis_at else None
    }


@router.get("/{project_id}/roadmap")
async def get_project_roadmap(project_id: str, db=Depends(get_db)):
    """دریافت محتوای Roadmap پروژه"""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="پروژه یافت نشد")

    issues = []
    try:
        if project.issues_found:
            issues = json.loads(project.issues_found)
    except:
        pass

    return {
        "success": True,
        "project_id": project_id,
        "roadmap_exists": bool(project.roadmap_content),
        "roadmap_content": project.roadmap_content or "",
        "ideal_state": project.ideal_state or "",
        "issues_found": issues
    }


@router.put("/{project_id}/roadmap")
async def update_project_roadmap(
    project_id: str,
    request: RoadmapUpdateRequest,
    db=Depends(get_db)
):
    """به‌روزرسانی Roadmap پروژه"""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="پروژه یافت نشد")

    if request.content:
        # ذخیره محتوای دستی
        project.roadmap_content = request.content
        db.commit()

        return {
            "success": True,
            "message": "Roadmap ذخیره شد",
            "source": "manual"
        }

    elif request.auto_generate:
        # تولید خودکار
        files = db.query(ProjectFile).filter(ProjectFile.project_id == project_id).all()
        files_data = [{"path": f.file_path, "content": f.content or ""} for f in files]

        project_info = {
            "name": project.name,
            "description": project.description,
            "type": project.project_type
        }

        analyzer = get_project_health_analyzer()
        analyzer.initialize()

        result = await analyzer.check_and_manage_roadmap(
            project_id=project_id,
            files=files_data,
            project_info=project_info
        )

        project.roadmap_content = result.get("roadmap_content", "")
        project.ideal_state = result.get("ideal_state", "")

        if result.get("issues_found"):
            project.issues_found = json.dumps(result["issues_found"], ensure_ascii=False)

        db.commit()

        return {
            "success": True,
            "message": "Roadmap تولید شد",
            "source": "auto",
            "action": result.get("action_taken")
        }

    return {"success": False, "message": "محتوا یا auto_generate لازم است"}


@router.get("/{project_id}/readme")
async def get_project_readme(project_id: str, db=Depends(get_db)):
    """دریافت محتوای README پروژه"""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="پروژه یافت نشد")

    return {
        "success": True,
        "project_id": project_id,
        "readme_exists": bool(project.readme_content),
        "readme_content": project.readme_content or ""
    }


@router.put("/{project_id}/readme")
async def update_project_readme(
    project_id: str,
    request: RoadmapUpdateRequest,
    db=Depends(get_db)
):
    """به‌روزرسانی README پروژه"""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="پروژه یافت نشد")

    if request.content:
        project.readme_content = request.content
        db.commit()

        return {
            "success": True,
            "message": "README ذخیره شد",
            "source": "manual"
        }

    elif request.auto_generate:
        files = db.query(ProjectFile).filter(ProjectFile.project_id == project_id).all()
        files_data = [{"path": f.file_path, "content": f.content or ""} for f in files]

        project_info = {
            "name": project.name,
            "description": project.description,
            "type": project.project_type
        }

        analyzer = get_project_health_analyzer()
        analyzer.initialize()

        result = await analyzer.check_and_manage_readme(
            project_id=project_id,
            files=files_data,
            project_info=project_info,
            roadmap_content=project.roadmap_content
        )

        project.readme_content = result.get("readme_content", "")
        db.commit()

        return {
            "success": True,
            "message": "README تولید شد",
            "source": "auto"
        }

    return {"success": False, "message": "محتوا یا auto_generate لازم است"}


@router.get("/{project_id}/health/issues")
async def get_project_issues(project_id: str, db=Depends(get_db)):
    """دریافت لیست ایرادات شناسایی شده"""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="پروژه یافت نشد")

    issues = []
    try:
        if project.issues_found:
            issues = json.loads(project.issues_found)
    except:
        pass

    # گروه‌بندی بر اساس severity
    grouped = {"critical": [], "high": [], "medium": [], "low": []}
    for issue in issues:
        severity = issue.get("severity", "medium")
        if severity in grouped:
            grouped[severity].append(issue)
        else:
            grouped["medium"].append(issue)

    return {
        "success": True,
        "project_id": project_id,
        "issues": issues,
        "total_count": len(issues),
        "grouped": grouped,
        "counts": {k: len(v) for k, v in grouped.items()}
    }


@router.get("/{project_id}/health/ideal-state")
async def get_ideal_state(project_id: str, db=Depends(get_db)):
    """دریافت توضیحات حالت ایده‌آل پروژه"""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="پروژه یافت نشد")

    return {
        "success": True,
        "project_id": project_id,
        "ideal_state": project.ideal_state or "هنوز تحلیلی انجام نشده",
        "has_content": bool(project.ideal_state)
    }


# =====================================
# Model Profiles & Validation Endpoints
# =====================================

@router.post("/{project_id}/health/validate-reports")
async def validate_analysis_reports(
    project_id: str,
    background_tasks: BackgroundTasks,
    db=Depends(get_db)
):
    """
    اعتبارسنجی گزارش‌های مدل‌ها و به‌روزرسانی نمرات تجمعی

    این endpoint:
    1. گزارش‌های مدل‌ها رو بررسی می‌کنه
    2. موارد درست/اشتباه/پیدا نشده رو تشخیص میده
    3. نمرات تجمعی مدل‌ها رو به‌روز می‌کنه (هیچوقت صفر نمیشن)
    """
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="پروژه یافت نشد")

    # دریافت فایل‌های پروژه
    files = db.query(ProjectFile).filter(ProjectFile.project_id == project_id).all()
    files_content = {f.file_path: f.content or "" for f in files}

    # دریافت آخرین گزارش‌ها
    issues = []
    try:
        if project.issues_found:
            issues = json.loads(project.issues_found)
    except:
        pass

    # گروه‌بندی ایرادات بر اساس مدل
    model_reports = {}
    for issue in issues:
        model_id = issue.get("model", "unknown")
        if model_id not in model_reports:
            model_reports[model_id] = {"issues": []}
        model_reports[model_id]["issues"].append(issue)

    if not model_reports:
        return {
            "success": False,
            "message": "گزارشی برای اعتبارسنجی وجود ندارد",
            "hint": "ابتدا تحلیل سلامت را اجرا کنید"
        }

    # اجرای اعتبارسنجی در background
    background_tasks.add_task(
        _run_validation_task,
        project_id=project_id,
        files_content=files_content,
        model_reports=model_reports
    )

    return {
        "success": True,
        "message": "اعتبارسنجی شروع شد",
        "models_to_validate": list(model_reports.keys()),
        "total_issues": len(issues)
    }


async def _run_validation_task(
    project_id: str,
    files_content: dict,
    model_reports: dict
):
    """تسک پس‌زمینه برای اعتبارسنجی"""
    try:
        validator = get_report_validator()
        validator.initialize()

        result = await validator.validate_analysis_reports(
            project_id=project_id,
            files_content=files_content,
            model_reports=model_reports
        )

        import logging
        logging.info(f"Validation completed for {project_id}: {result.get('summary', {})}")

    except Exception as e:
        import logging
        logging.error(f"Validation task error: {e}", exc_info=True)


@router.get("/models/profiles")
async def get_all_model_profiles():
    """
    دریافت پروفایل همه مدل‌های AI

    نمرات تجمعی که هیچوقت صفر نمیشن
    """
    profiler = get_model_profiler()
    profiles = profiler.get_all_profiles()

    return {
        "success": True,
        "profiles": [p.model_dump() for p in profiles],
        "count": len(profiles)
    }


@router.get("/models/{model_id}/profile")
async def get_model_profile(model_id: str):
    """دریافت پروفایل یک مدل خاص"""
    profiler = get_model_profiler()
    profile = profiler.get_profile(model_id)

    if not profile:
        raise HTTPException(status_code=404, detail="پروفایل یافت نشد")

    return {
        "success": True,
        "profile": profile.model_dump()
    }


@router.get("/models/top")
async def get_top_models(n: int = 5, task_type: str = None):
    """
    دریافت مدل‌های برتر

    برای انتخاب مدل‌های مناسب کارهای مهم
    """
    profiler = get_model_profiler()
    top_models = profiler.get_top_models(n=n, task_type=task_type)

    return {
        "success": True,
        "top_models": [p.model_dump() for p in top_models],
        "count": len(top_models),
        "filter_task_type": task_type
    }


@router.get("/models/{model_id}/history")
async def get_model_score_history(model_id: str, limit: int = 100):
    """دریافت تاریخچه نمرات یک مدل"""
    profiler = get_model_profiler()
    history = profiler.get_score_history(model_id, limit=limit)

    return {
        "success": True,
        "model_id": model_id,
        "history": history,
        "count": len(history)
    }


@router.post("/models/compare")
async def compare_models(model_ids: List[str]):
    """
    مقایسه چند مدل با هم

    برای تصمیم‌گیری در انتخاب مدل
    """
    if len(model_ids) < 2:
        raise HTTPException(status_code=400, detail="حداقل 2 مدل لازم است")

    profiler = get_model_profiler()
    comparison = profiler.compare_models(model_ids)

    return {
        "success": True,
        "comparison": comparison
    }
