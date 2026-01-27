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
            "scores": health_scores,
            "overall_score": health_scores.get("overall", 0),
            "overall_color": health_scores.get("overall_color", "gray"),
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
    model_ids = request.model_ids
    if not model_ids or "all" in model_ids:
        # دریافت همه مدل‌های فعال
        from ...services.ai_manager import get_ai_manager
        ai_manager = get_ai_manager()
        available = ai_manager.get_available_models()
        model_ids = [m.id for m in available[:3]]  # حداکثر 3 مدل

    if not model_ids:
        model_ids = ["claude"]  # پیش‌فرض

    # اجرای تحلیل در background
    background_tasks.add_task(
        _run_analysis_task,
        project_id=project_id,
        files_data=files_data,
        project_info=project_info,
        model_ids=model_ids,
        request=request
    )

    return {
        "success": True,
        "message": "تحلیل شروع شد",
        "project_id": project_id,
        "models": model_ids,
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
    """تسک پس‌زمینه برای اجرای تحلیل"""
    from ...core.database import SessionLocal

    db = SessionLocal()
    try:
        analyzer = get_project_health_analyzer()
        analyzer.initialize()

        # دریافت پروژه
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            return

        # 1. بررسی و مدیریت Roadmap
        roadmap_content = project.roadmap_content or ""
        if request.update_roadmap:
            roadmap_result = await analyzer.check_and_manage_roadmap(
                project_id=project_id,
                files=files_data,
                project_info=project_info,
                model_id=model_ids[0] if model_ids else None
            )
            roadmap_content = roadmap_result.get("roadmap_content", "")
            project.roadmap_content = roadmap_content
            project.ideal_state = roadmap_result.get("ideal_state", "")

            # ذخیره ایرادات
            if roadmap_result.get("issues_found"):
                project.issues_found = json.dumps(
                    roadmap_result["issues_found"],
                    ensure_ascii=False
                )

        # 2. بررسی و مدیریت README
        if request.update_readme:
            readme_result = await analyzer.check_and_manage_readme(
                project_id=project_id,
                files=files_data,
                project_info=project_info,
                roadmap_content=roadmap_content,
                model_id=model_ids[0] if model_ids else None
            )
            project.readme_content = readme_result.get("readme_content", "")

        # 3. تحلیل موازی سلامت پروژه
        analysis_result = await analyzer.analyze_project_parallel(
            project_id=project_id,
            files=files_data,
            project_info=project_info,
            model_ids=model_ids,
            roadmap_content=roadmap_content,
            full_analysis=request.full_analysis
        )

        # 4. ذخیره نتایج
        project.health_scores = json.dumps(
            analysis_result.get("overall_scores", {}),
            ensure_ascii=False
        )
        project.file_health_map = json.dumps(
            analysis_result.get("color_map", {}),
            ensure_ascii=False
        )
        project.last_analysis_id = analysis_result.get("analysis_id")
        project.last_analysis_at = datetime.utcnow()
        project.last_analysis_models = json.dumps(model_ids, ensure_ascii=False)

        # ترکیب ایرادات
        existing_issues = []
        try:
            if project.issues_found:
                existing_issues = json.loads(project.issues_found)
        except:
            pass

        # اضافه کردن ایرادات از تحلیل فایل‌ها
        for fa in analysis_result.get("file_analyses", []):
            for model_id, model_result in fa.get("model_results", {}).items():
                if isinstance(model_result, dict):
                    for issue in model_result.get("issues", []):
                        existing_issues.append({
                            "file": fa.get("file_path"),
                            "model": model_id,
                            **issue
                        })

        project.issues_found = json.dumps(existing_issues[:100], ensure_ascii=False)

        db.commit()

    except Exception as e:
        import logging
        logging.error(f"Analysis task error: {e}", exc_info=True)
        db.rollback()
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
