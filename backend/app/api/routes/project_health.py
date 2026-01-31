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
import asyncio
import logging
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from ...core.database import get_db
from ...models.project import Project, ProjectFile
from ...services.project_health_analyzer import get_project_health_analyzer
from ...services.report_validator import get_report_validator
from ...services.model_profiler import get_model_profiler
from ...services.analysis_progress_manager import (
    AnalysisProgressManager,
    get_analysis_progress,
    pause_analysis as pause_analysis_helper,
    resume_analysis as resume_analysis_helper,
    stop_analysis as stop_analysis_helper
)

logger = logging.getLogger(__name__)

# ذخیره progress managers فعال برای کنترل pause/resume/stop
_active_progress_managers: dict = {}

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

@router.post("/{project_id}/debug/single-file-test")
async def debug_single_file_test(project_id: str, db=Depends(get_db)):
    """
    تست تحلیل یک فایل - دقیق‌ترین تست برای تشخیص مشکل

    این endpoint یک فایل واحد را تحلیل می‌کند و نتیجه دقیق برمی‌گرداند
    """
    import logging
    import time
    logger = logging.getLogger(__name__)

    result = {
        "steps": [],
        "timings": {},
        "error": None,
        "success": False
    }

    start_total = time.time()

    try:
        # Step 1: Get project
        result["steps"].append("1. Getting project...")
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            result["error"] = "Project not found"
            return result
        result["steps"][-1] += f" ✅ Found: {project.name}"

        # Step 2: Get one file with content
        result["steps"].append("2. Getting first file with content...")
        files = db.query(ProjectFile).filter(ProjectFile.project_id == project_id).all()

        test_file = None
        for f in files:
            content = f.content or ""
            if len(content) >= 50:  # At least 50 chars
                test_file = f
                break

        if not test_file:
            result["error"] = f"No file with content found! Total files: {len(files)}, all have empty or short content"
            result["debug"] = {
                "total_files": len(files),
                "file_sizes": [(f.file_path, len(f.content or "")) for f in files[:10]]
            }
            return result

        result["steps"][-1] += f" ✅ Using: {test_file.file_path} ({len(test_file.content)} chars)"

        # Step 3: Get AI manager
        result["steps"].append("3. Getting AI Manager...")
        from ...services.ai_manager import get_ai_manager
        ai_manager = get_ai_manager()

        available_models = ai_manager.get_available_models()
        if not available_models:
            result["error"] = "No AI models available!"
            result["init_errors"] = getattr(ai_manager, '_init_errors', {})
            return result

        test_model = available_models[0].id
        result["steps"][-1] += f" ✅ Models: {len(available_models)}, using: {test_model}"

        # Step 4: Build prompt
        result["steps"].append("4. Building analysis prompt...")
        prompt = f"""# تحلیل جزئی فایل (Micro Analysis)

## فایل: {test_file.file_path}

## محتوای فایل:
```
{test_file.content[:5000]}
```

## وظیفه تو:
1. بررسی کد و شناسایی مشکلات
2. نمره‌دهی 0-100

## فرمت خروجی (JSON):
```json
{{
    "scores": {{
        "code_quality": 0-100,
        "documentation": 0-100,
        "security": 0-100
    }},
    "issues": [],
    "summary": "خلاصه یک خطی"
}}
```

مهم: فقط JSON برگردان!
"""
        result["steps"][-1] += f" ✅ Prompt: {len(prompt)} chars"

        # Step 5: Make AI call
        result["steps"].append("5. Calling AI model...")
        from ...services.ai_base import Message

        start_ai = time.time()
        try:
            response = await ai_manager.generate(
                model_id=test_model,
                messages=[
                    Message(role="system", content="تو یک تحلیل‌گر حرفه‌ای کد هستی. فقط خروجی JSON برگردان."),
                    Message(role="user", content=prompt)
                ],
                max_tokens=2000,
                temperature=0.3
            )
            ai_time = time.time() - start_ai
            result["timings"]["ai_call"] = f"{ai_time:.2f}s"

            if response.content:
                result["steps"][-1] += f" ✅ Response: {len(response.content)} chars in {ai_time:.2f}s"
                result["ai_response_preview"] = response.content[:500]
            else:
                result["steps"][-1] += f" ⚠️ Empty response after {ai_time:.2f}s"
                result["error"] = "AI returned empty response"

        except Exception as ai_error:
            ai_time = time.time() - start_ai
            result["timings"]["ai_call"] = f"{ai_time:.2f}s (failed)"
            result["steps"][-1] += f" ❌ Failed: {str(ai_error)}"
            result["error"] = f"AI call failed: {str(ai_error)}"
            return result

        # Step 6: Parse response
        result["steps"].append("6. Parsing AI response...")
        import re
        import json as json_module

        try:
            # Find JSON in response
            json_match = re.search(r'\{[\s\S]*\}', response.content)
            if json_match:
                parsed = json_module.loads(json_match.group())
                result["steps"][-1] += f" ✅ Parsed JSON with keys: {list(parsed.keys())}"
                result["parsed_result"] = parsed

                # Check for scores
                if "scores" in parsed:
                    result["steps"].append("7. Extracting scores...")
                    scores = parsed["scores"]
                    result["steps"][-1] += f" ✅ Scores: {scores}"
                    result["extracted_scores"] = scores
                    result["success"] = True
                else:
                    result["steps"].append("7. ⚠️ No 'scores' key in response")
            else:
                result["steps"][-1] += f" ❌ No JSON found in response"
                result["error"] = "Could not find JSON in AI response"

        except json_module.JSONDecodeError as je:
            result["steps"][-1] += f" ❌ JSON parse error: {str(je)}"
            result["error"] = f"JSON parse error: {str(je)}"

        result["timings"]["total"] = f"{time.time() - start_total:.2f}s"

    except Exception as e:
        result["error"] = f"Unexpected error: {str(e)}"
        import traceback
        result["traceback"] = traceback.format_exc()

    return result


@router.get("/{project_id}/debug/analysis-test")
async def debug_analysis_test(project_id: str, db=Depends(get_db)):
    """
    تست کامل تحلیل - نشون میده دقیقاً کجا مشکل هست
    """
    import logging
    logger = logging.getLogger(__name__)

    result = {
        "step": "start",
        "errors": [],
        "debug_info": {}
    }

    try:
        # Step 1: Check project exists
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            return {"error": "Project not found", "project_id": project_id}

        result["debug_info"]["project_name"] = project.name
        result["step"] = "project_found"

        # Step 2: Get files
        files = db.query(ProjectFile).filter(ProjectFile.project_id == project_id).all()
        result["debug_info"]["total_files_in_db"] = len(files)

        # Check file contents
        files_with_content = 0
        files_without_content = 0
        content_sizes = []

        for f in files:
            content = f.content or ""
            if len(content) >= 10:
                files_with_content += 1
                content_sizes.append({"path": f.file_path, "size": len(content)})
            else:
                files_without_content += 1

        result["debug_info"]["files_with_content"] = files_with_content
        result["debug_info"]["files_without_content"] = files_without_content
        result["debug_info"]["sample_content_sizes"] = content_sizes[:5]
        result["step"] = "files_checked"

        # Step 3: Check AI manager
        from ...services.ai_manager import get_ai_manager
        ai_manager = get_ai_manager()

        available_models = ai_manager.get_available_models()
        available_providers = ai_manager.get_available_providers()

        result["debug_info"]["ai_manager_exists"] = ai_manager is not None
        result["debug_info"]["available_providers"] = available_providers
        result["debug_info"]["available_models"] = [m.id for m in available_models]
        result["debug_info"]["models_count"] = len(available_models)
        result["step"] = "ai_manager_checked"

        if not available_models:
            result["errors"].append("No AI models available!")
            return result

        # Step 4: Test single AI call
        from ...services.ai_base import Message

        test_model = available_models[0].id
        result["debug_info"]["test_model"] = test_model

        try:
            import time
            start = time.time()

            response = await ai_manager.generate(
                model_id=test_model,
                messages=[
                    Message(role="system", content="You are a helpful assistant."),
                    Message(role="user", content="Say 'Hello, AI is working!' in exactly 5 words.")
                ],
                max_tokens=50,
                temperature=0.5
            )

            elapsed = time.time() - start
            result["debug_info"]["ai_test_time"] = f"{elapsed:.2f}s"
            result["debug_info"]["ai_test_response"] = response.content[:200] if response.content else "EMPTY"
            result["debug_info"]["ai_test_success"] = True
            result["step"] = "ai_call_success"

        except Exception as e:
            result["debug_info"]["ai_test_error"] = str(e)
            result["debug_info"]["ai_test_success"] = False
            result["errors"].append(f"AI call failed: {str(e)}")
            result["step"] = "ai_call_failed"

        # Step 5: Check DeepAnalysisService
        from ...services.deep_analysis_service import get_deep_analysis_service
        deep_analyzer = get_deep_analysis_service(ai_manager)

        result["debug_info"]["deep_analyzer_has_ai_manager"] = deep_analyzer.ai_manager is not None
        result["step"] = "deep_analyzer_checked"

        # Summary
        result["summary"] = {
            "can_run_analysis": (
                files_with_content > 0 and
                len(available_models) > 0 and
                result["debug_info"].get("ai_test_success", False) and
                deep_analyzer.ai_manager is not None
            ),
            "issues": []
        }

        if files_with_content == 0:
            result["summary"]["issues"].append("❌ No files have content (all empty)")
        if len(available_models) == 0:
            result["summary"]["issues"].append("❌ No AI models available")
        if not result["debug_info"].get("ai_test_success"):
            result["summary"]["issues"].append("❌ AI call test failed")
        if deep_analyzer.ai_manager is None:
            result["summary"]["issues"].append("❌ DeepAnalysisService has no AI manager")

        if not result["summary"]["issues"]:
            result["summary"]["issues"].append("✅ All checks passed - analysis should work")

    except Exception as e:
        result["errors"].append(f"Unexpected error: {str(e)}")
        import traceback
        result["traceback"] = traceback.format_exc()

    return result


@router.get("/{project_id}/debug/files-content")
async def debug_files_content(project_id: str, db=Depends(get_db)):
    """
    نمایش وضعیت محتوای فایل‌ها

    این endpoint نشون میده آیا فایل‌ها محتوا دارن یا خالی هستن
    """
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        return {"error": "Project not found", "project_id": project_id}

    files = db.query(ProjectFile).filter(ProjectFile.project_id == project_id).all()

    files_info = []
    total_with_content = 0
    total_empty = 0
    total_bytes = 0

    for f in files:
        content = f.content or ""
        size = len(content)
        total_bytes += size

        if size >= 10:
            total_with_content += 1
        else:
            total_empty += 1

        files_info.append({
            "path": f.file_path,
            "size": size,
            "has_content": size >= 10,
            "preview": content[:100] if size > 0 else "(empty)"
        })

    # Sort by size descending
    files_info.sort(key=lambda x: x["size"], reverse=True)

    return {
        "success": True,
        "project_id": project_id,
        "project_name": project.name,
        "summary": {
            "total_files": len(files),
            "files_with_content": total_with_content,
            "empty_files": total_empty,
            "total_bytes": total_bytes,
            "can_run_analysis": total_with_content > 0
        },
        "files": files_info[:20],  # First 20 files
        "note": "اگر همه فایل‌ها خالی هستند، باید پروژه را دوباره import کنید"
    }


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
    error = None
    init_errors = {}
    services_status = {}
    available_models = []
    available_providers = []

    try:
        ai_manager = get_ai_manager()
        available_providers = ai_manager.get_available_providers()
        init_errors = getattr(ai_manager, '_init_errors', {})

        # لیست مدل‌ها - با محافظت
        try:
            for m in ai_manager.get_available_models():
                provider_val = m.provider.value if hasattr(m.provider, 'value') else str(m.provider)
                available_models.append({"id": m.id, "provider": provider_val})
        except Exception as me:
            error = f"Model list error: {me}"

        # وضعیت سرویس‌ها - با محافظت
        for provider, service in ai_manager._services.items():
            provider_name = provider.value if hasattr(provider, 'value') else str(provider)
            try:
                services_status[provider_name] = {
                    "initialized": True,
                    "in_error_state": service.is_in_error_state()
                }
            except Exception as se:
                services_status[provider_name] = {"error": str(se)}

    except Exception as e:
        error = str(e)

    # خواندن از settings
    settings_providers = settings.get_available_providers()

    return {
        "success": True,
        "api_keys_in_env": api_keys_status,
        "api_keys_in_db": db_keys_status,
        "settings_providers": settings_providers,
        "ai_manager_providers": available_providers,
        "services_status": services_status,
        "init_errors": init_errors,
        "available_models": available_models,
        "any_model_available": len(available_models) > 0,
        "models_count": len(available_models),
        "services_count": len(services_status),
        "error": error,
        "hints": {
            "no_models": "اگر مدلی در دسترس نیست، init_errors را چک کنید",
            "init_errors": "خطاهای initialization سرویس‌ها",
            "db_vs_env": "کلیدهای دیتابیس در startup به environment منتقل می‌شوند"
        }
    }


@router.delete("/{project_id}/health/clear")
async def clear_analysis_data(project_id: str, db=Depends(get_db)):
    """
    پاک کردن همه داده‌های تحلیل یک پروژه

    برای شروع از صفر و رفع سردرگمی درباره داده‌های قدیمی
    """
    import logging
    logger = logging.getLogger(__name__)

    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="پروژه یافت نشد")

    # پاک کردن همه داده‌های تحلیل
    old_data = {
        "health_scores": project.health_scores,
        "file_health_map": project.file_health_map,
        "issues_found": project.issues_found,
        "last_analysis_at": str(project.last_analysis_at) if project.last_analysis_at else None
    }

    project.health_scores = None
    project.file_health_map = None
    project.issues_found = None
    project.ideal_state = None
    project.last_analysis_id = None
    project.last_analysis_at = None
    project.last_analysis_models = None

    db.commit()

    logger.info(f"🗑️ Cleared all analysis data for project {project_id}")

    return {
        "success": True,
        "message": "همه داده‌های تحلیل پاک شدند",
        "project_id": project_id,
        "cleared_data_existed": bool(old_data.get("health_scores") or old_data.get("file_health_map"))
    }


@router.get("/{project_id}/health/status")
async def get_analysis_status(project_id: str, db=Depends(get_db)):
    """
    وضعیت دقیق تحلیل پروژه

    نشون میده:
    - آیا داده‌ای وجود داره یا نه
    - آخرین تحلیل کی بوده
    - چه مدل‌هایی استفاده شدن
    """
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="پروژه یافت نشد")

    has_health_scores = bool(project.health_scores)
    has_file_map = bool(project.file_health_map)
    has_issues = bool(project.issues_found)

    # پارس داده‌ها
    file_count = 0
    issues_count = 0
    try:
        if project.file_health_map:
            file_map = json.loads(project.file_health_map)
            file_count = len(file_map)
        if project.issues_found:
            issues = json.loads(project.issues_found)
            issues_count = len(issues)
    except:
        pass

    return {
        "success": True,
        "project_id": project_id,
        "has_analysis_data": has_health_scores or has_file_map,
        "data_status": {
            "health_scores": has_health_scores,
            "file_health_map": has_file_map,
            "files_analyzed": file_count,
            "issues_found": has_issues,
            "issues_count": issues_count,
        },
        "last_analysis": {
            "id": project.last_analysis_id,
            "at": project.last_analysis_at.isoformat() if project.last_analysis_at else None,
            "models": json.loads(project.last_analysis_models) if project.last_analysis_models else [],
            "how_long_ago": str(datetime.utcnow() - project.last_analysis_at) if project.last_analysis_at else None
        },
        "ideal_state_exists": bool(project.ideal_state),
        "note": "اگر has_analysis_data=false باشه، یعنی هیچ تحلیلی انجام نشده"
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

    model_ids = [m.id for m in available_models]  # همه مدل‌های در دسترس

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
            # 🔴 رفع محدودیت - تمام ایرادات ذخیره می‌شوند
            project.issues_found = json.dumps(
                analysis_result.get("issues", []),
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


@router.post("/{project_id}/health/analyze-stream")
async def run_streaming_analysis(
    project_id: str,
    request: RunAnalysisRequest = None,
    db=Depends(get_db)
):
    """
    تحلیل با استریم پیشرفت (Server-Sent Events)

    این endpoint پیشرفت تحلیل را به صورت Real-time ارسال می‌کند
    """
    logger.info(f"🔬 Starting STREAMING analysis for project {project_id}")

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

    # بررسی مدل‌های در دسترس
    from ...services.ai_manager import get_ai_manager
    from ...services.deep_analysis_service import DeepAnalysisService

    ai_manager = get_ai_manager()
    available_models = ai_manager.get_available_models()

    if not available_models:
        raise HTTPException(status_code=400, detail="هیچ مدل AI در دسترس نیست")

    # انتخاب مدل‌ها
    if request and request.model_ids:
        model_ids = request.model_ids
    else:
        model_ids = [m.id for m in available_models]

    # صف برای ارسال رویدادها
    progress_queue: asyncio.Queue = asyncio.Queue()

    async def progress_callback(progress_data: dict):
        """callback برای دریافت رویدادهای پیشرفت"""
        await progress_queue.put(progress_data)

    async def generate_events():
        """ژنراتور رویدادهای SSE"""
        final_result = None

        async def run_analysis_task():
            nonlocal final_result
            try:
                # ساخت DeepAnalysisService با progress callback
                deep_analyzer = DeepAnalysisService(
                    ai_manager=ai_manager,
                    progress_callback=progress_callback
                )

                # اجرای تحلیل
                final_result = await deep_analyzer.run_full_analysis(
                    project_id=project_id,
                    files=files_data,
                    roadmap_content=project.roadmap_content or "",
                    readme_content=project.readme_content or "",
                    model_ids=model_ids,
                    instruction="تحلیل کامل پروژه"
                )

                # ذخیره نتایج
                if final_result.get("status") == "completed":
                    # باز کردن session جدید برای ذخیره
                    from ...core.database import SessionLocal
                    new_db = SessionLocal()
                    try:
                        proj = new_db.query(Project).filter(Project.id == project_id).first()
                        if proj:
                            proj.health_scores = json.dumps(
                                final_result.get("overall_scores", {}),
                                ensure_ascii=False
                            )
                            proj.file_health_map = json.dumps(
                                final_result.get("file_health_map", {}),
                                ensure_ascii=False
                            )
                            # 🔴 رفع محدودیت - تمام ایرادات بدون محدودیت عددی ذخیره می‌شوند
                            proj.issues_found = json.dumps(
                                final_result.get("issues", []),
                                ensure_ascii=False
                            )
                            proj.last_analysis_at = datetime.utcnow()
                            proj.last_analysis_models = json.dumps(model_ids, ensure_ascii=False)
                            new_db.commit()
                            logger.info(f"✅ Streaming analysis completed and saved!")
                    finally:
                        new_db.close()

            except Exception as e:
                logger.error(f"Streaming analysis failed: {e}", exc_info=True)
                await progress_queue.put({
                    "event": "error",
                    "message": str(e),
                    "error": True
                })
            finally:
                # سیگنال اتمام
                await progress_queue.put({
                    "event": "done",
                    "has_result": final_result is not None,
                    "overall_score": final_result.get("overall_scores", {}).get("total", 0) if final_result else 0
                })

        # شروع تحلیل
        analysis_task = asyncio.create_task(run_analysis_task())

        try:
            while True:
                try:
                    # دریافت رویداد با timeout
                    progress_data = await asyncio.wait_for(
                        progress_queue.get(),
                        timeout=2.0
                    )

                    # ارسال رویداد SSE
                    event_type = progress_data.get("event", "progress")
                    data = json.dumps(progress_data, ensure_ascii=False, default=str)
                    yield f"event: {event_type}\ndata: {data}\n\n"

                    # اگر تحلیل تمام شد
                    if event_type == "done" or event_type == "analysis_completed":
                        break

                except asyncio.TimeoutError:
                    # ارسال heartbeat
                    yield f"event: heartbeat\ndata: {{}}\n\n"

                    # بررسی وضعیت task
                    if analysis_task.done():
                        break

        except Exception as e:
            logger.error(f"Error in SSE stream: {e}")
            yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"

        finally:
            if not analysis_task.done():
                analysis_task.cancel()

    return StreamingResponse(
        generate_events(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
            "Access-Control-Allow-Origin": "*"
        }
    )


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
                    "code_quality": health_scores.get("code_quality", health_scores.get("micro", 0)),
                    "documentation": health_scores.get("documentation", 0),  # 🆕 از 50 به 0 تغییر کرد
                    "security": health_scores.get("security", 0),            # 🆕 از 50 به 0 تغییر کرد
                    "cooperation": health_scores.get("cooperation", health_scores.get("macro", 0)),  # 🆕 اول cooperation چک میشه
                    "roadmap_compliance": health_scores.get("roadmap_compliance", health_scores.get("roadmap_score", 0)),  # 🆕 از 50 به 0
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

    # 🔴 جلوگیری از دور باطل - بررسی تحلیل تکراری
    try:
        from .project_journal import check_cycle_prevention
        if not check_cycle_prevention(
            db=db,
            project_id=project_id,
            activity_type="health_analysis",
            minutes_threshold=5  # حداقل 5 دقیقه بین تحلیل‌ها
        ):
            raise HTTPException(
                status_code=429,
                detail="تحلیل سلامت اخیراً اجرا شده است. لطفاً چند دقیقه صبر کنید."
            )
    except ImportError:
        pass

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

    # فیلتر کردن "all" از لیست
    if model_ids:
        model_ids = [m for m in model_ids if m != "all"]

    # اگر بعد از فیلتر خالی شد، یعنی فقط "all" بوده - همه مدل‌ها
    if not model_ids:
        model_ids = [m.id for m in available_models]
    else:
        # اطمینان از اینکه مدل‌های انتخابی واقعاً در دسترس هستند
        available_ids = [m.id for m in available_models]
        model_ids = [m for m in model_ids if m in available_ids]

        # اگر هیچکدام از مدل‌های انتخابی در دسترس نبود
        if not model_ids:
            model_ids = [m.id for m in available_models]

    logger.info(f"📊 Selected models for analysis: {model_ids}")

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

        # ایجاد progress manager برای ذخیره وضعیت
        progress_manager = AnalysisProgressManager(project_id, db)
        progress_manager.start_analysis(
            analysis_id=f"analysis_{project_id[:8]}",
            total_files=len(files_data),
            model_ids=model_ids
        )
        _active_progress_managers[project_id] = progress_manager

        try:
            analysis_result = await deep_analyzer.run_full_analysis(
                project_id=project_id,
                files=files_data,
                roadmap_content=roadmap_content,
                readme_content=readme_content,
                model_ids=model_ids,
                instruction=instruction,
                db_session=db,
                progress_manager=progress_manager
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
            # 🔴 رفع محدودیت - تمام ایرادات ذخیره می‌شوند
            # 🆕 ادغام ایرادات مشابه قبل از ذخیره برای کاهش حجم
            raw_issues = analysis_result.get("issues", [])
            if len(raw_issues) > 100:
                # ادغام اولیه در زمان ذخیره
                merged_issues = _merge_similar_issues(raw_issues, aggressive=len(raw_issues) > 500)
                logger.info(f"[Health Analysis] Merged {len(raw_issues)} issues to {len(merged_issues)} before storing")
                project.issues_found = json.dumps(merged_issues, ensure_ascii=False)
            else:
                project.issues_found = json.dumps(raw_issues, ensure_ascii=False)

            # ذخیره حالت ایده‌آل
            if analysis_result.get("ideal_state"):
                project.ideal_state = analysis_result["ideal_state"]

            logger.info(f"✅ Analysis completed for project {project_id}. Score: {analysis_result.get('overall_scores', {}).get('total', 0):.1f}")

            # به‌روزرسانی progress manager
            if project_id in _active_progress_managers:
                _active_progress_managers[project_id].complete_analysis(
                    overall_score=analysis_result.get('overall_scores', {}).get('total', 0),
                    total_issues=len(analysis_result.get("issues", []))
                )
        else:
            logger.warning(f"⚠️ Analysis did not complete successfully: {analysis_result.get('status')}")
            if analysis_result.get("error"):
                logger.error(f"❌ Analysis error: {analysis_result.get('error')}")
                # علامت‌گذاری خطا در progress manager
                if project_id in _active_progress_managers:
                    _active_progress_managers[project_id].fail_analysis(analysis_result.get("error", "Unknown error"))

        db.commit()
        logger.info(f"💾 Results saved to database for project {project_id}")

        # 🆕 ثبت فعالیت تحلیل سلامت در ژورنال
        try:
            from .project_journal import ActivityLog
            import uuid as uuid_module

            overall_score = analysis_result.get('overall_scores', {}).get('total', 0)
            issues_count = len(analysis_result.get("issues", []))
            files_analyzed = len(analysis_result.get("file_health_map", {}))

            activity_log = ActivityLog(
                id=f"log_{uuid_module.uuid4().hex[:12]}",
                project_id=project_id,
                model_id=",".join(model_ids) if model_ids else "unknown",
                model_provider="multi",
                activity_type="health_analysis",
                prompt=f"تحلیل سلامت پروژه با {len(model_ids)} مدل",
                response=f"نمره کلی: {overall_score:.1f}% | {issues_count} ایراد | {files_analyzed} فایل",
                tokens_used=0,
                latency_ms=0,
                success=analysis_result.get("status") == "completed",
                error_message=analysis_result.get("error"),
                field_id=analysis_result.get("analysis_id"),
                field_name=f"تحلیل سلامت - {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}",
                extra_data=json.dumps({
                    "analysis_id": analysis_result.get("analysis_id"),
                    "models_used": model_ids,
                    "overall_score": overall_score,
                    "issues_count": issues_count,
                    "files_analyzed": files_analyzed,
                    "scores": analysis_result.get('overall_scores', {}),
                }, ensure_ascii=False),
                created_at=datetime.utcnow(),
            )
            db.add(activity_log)
            db.commit()
            logger.info(f"📝 Activity logged to journal for health analysis")
        except Exception as log_error:
            logger.warning(f"Could not log activity to journal: {log_error}")

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
        # پاک کردن از active progress managers
        if project_id in _active_progress_managers:
            del _active_progress_managers[project_id]
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


class RoadmapItemUpdateRequest(BaseModel):
    """به‌روزرسانی آیتم نقشه راه"""
    completed: bool


@router.patch("/{project_id}/roadmap/items/{item_id}")
async def update_roadmap_item(
    project_id: str,
    item_id: str,
    request: RoadmapItemUpdateRequest,
    db=Depends(get_db)
):
    """به‌روزرسانی وضعیت یک آیتم نقشه راه (چک‌باکس)"""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="پروژه یافت نشد")

    # پارس کردن roadmap موجود
    roadmap_content = project.roadmap_content or ""
    lines = roadmap_content.split('\n')

    # استخراج شماره خط از item_id (مثلاً roadmap_5 -> خط 5)
    try:
        line_index = int(item_id.replace('roadmap_', ''))
    except ValueError:
        raise HTTPException(status_code=400, detail="شناسه آیتم نامعتبر است")

    # به‌روزرسانی خط مورد نظر
    if 0 <= line_index < len(lines):
        line = lines[line_index]
        trimmed = line.strip()

        # اگر خط یک آیتم لیست است
        import re
        if trimmed.startswith('- ') or trimmed.startswith('* ') or re.match(r'^\d+\.', trimmed):
            # حذف علامت‌های قبلی
            clean_line = trimmed.replace('[x]', '').replace('[✓]', '').replace('[✅]', '').replace('✅', '').replace('✓', '')

            if request.completed:
                # اضافه کردن علامت تیک
                if clean_line.startswith('- '):
                    lines[line_index] = line.replace(trimmed, f"- [x] {clean_line[2:].strip()}")
                elif clean_line.startswith('* '):
                    lines[line_index] = line.replace(trimmed, f"* [x] {clean_line[2:].strip()}")
            else:
                # حذف علامت تیک
                lines[line_index] = line.replace(trimmed, clean_line)

            # ذخیره
            project.roadmap_content = '\n'.join(lines)
            db.commit()

            return {
                "success": True,
                "item_id": item_id,
                "completed": request.completed,
                "message": "آیتم به‌روزرسانی شد"
            }

    return {
        "success": False,
        "message": "آیتم پیدا نشد"
    }


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


def _merge_similar_issues(issues: list, aggressive: bool = False) -> list:
    """
    🔴 ادغام ایرادات مشابه - نسخه بهبود یافته
    - مرحله 1: ادغام دقیق (فایل + نوع یکسان)
    - مرحله 2: ادغام براساس نوع و severity مشابه
    - مرحله 3: ادغام براساس شباهت پیام (>50%)
    - مرحله 4 (aggressive): ادغام براساس دسته‌بندی کلی (max 100 نتیجه)
    """
    if len(issues) <= 1:
        return issues

    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"[Merge Issues] Starting with {len(issues)} issues, aggressive={aggressive}")

    # مرحله 1: گروه‌بندی براساس فایل + نوع
    file_type_groups = {}
    for issue in issues:
        key = f"{issue.get('file', '')}|{issue.get('type', '')}"
        if key not in file_type_groups:
            file_type_groups[key] = []
        file_type_groups[key].append(issue)

    # تبدیل گروه‌ها به ایرادات ادغام شده
    step1_merged = []
    for key, group in file_type_groups.items():
        if len(group) == 1:
            step1_merged.append(group[0])
        else:
            # ادغام گروه
            merged_issue = group[0].copy()
            merged_issue["merged_count"] = len(group)
            merged_issue["merged_messages"] = [g.get("message", "") for g in group[:5]]
            merged_issue["merged_lines"] = [g.get("line") for g in group if g.get("line")]
            merged_issue["message"] = f"[{len(group)} مورد] " + merged_issue.get("message", "")
            step1_merged.append(merged_issue)

    logger.info(f"[Merge Issues] After step 1 (file+type): {len(step1_merged)} issues")

    # مرحله 2: ادغام براساس نوع + severity
    type_severity_groups = {}
    for issue in step1_merged:
        key = f"{issue.get('type', '')}|{issue.get('severity', 'medium')}"
        if key not in type_severity_groups:
            type_severity_groups[key] = []
        type_severity_groups[key].append(issue)

    step2_merged = []
    for key, group in type_severity_groups.items():
        # اگر گروه بزرگ باشد، ادغام کن
        if len(group) > 10:
            # ادغام با نگه داشتن نمونه‌های مهم
            merged_issue = group[0].copy()
            total = sum(g.get("merged_count", 1) for g in group)
            merged_issue["merged_count"] = total
            merged_issue["sub_groups"] = len(group)
            merged_issue["affected_files"] = list(set(g.get("file", "") for g in group))[:10]
            merged_issue["message"] = f"[{total} ایراد در {len(group)} محل] " + merged_issue.get("type", "ایراد")
            step2_merged.append(merged_issue)
        else:
            step2_merged.extend(group)

    logger.info(f"[Merge Issues] After step 2 (type+severity): {len(step2_merged)} issues")

    # مرحله 3: ادغام براساس شباهت پیام
    merged = []
    used_indices = set()

    for i, issue in enumerate(step2_merged):
        if i in used_indices:
            continue

        merged_issue = issue.copy()
        current_count = issue.get("merged_count", 1)

        for j in range(i + 1, len(step2_merged)):
            if j in used_indices:
                continue

            other = step2_merged[j]

            # بررسی شباهت پیام
            msg1 = issue.get("type", "") + " " + issue.get("message", "")[:80]
            msg2 = other.get("type", "") + " " + other.get("message", "")[:80]
            msg1 = msg1.lower()
            msg2 = msg2.lower()

            common_words = set(msg1.split()) & set(msg2.split())
            all_words = set(msg1.split()) | set(msg2.split())
            similarity = len(common_words) / max(len(all_words), 1)

            if similarity > 0.5:
                current_count += other.get("merged_count", 1)
                used_indices.add(j)

        merged_issue["merged_count"] = current_count
        if current_count > 1:
            merged_issue["message"] = f"[{current_count} ایراد مشابه] " + merged_issue.get("message", "")
        merged.append(merged_issue)

    logger.info(f"[Merge Issues] After step 3 (similarity): {len(merged)} issues")

    # مرحله 4 (aggressive): اگر هنوز بیش از 100 تاست، فقط دسته‌بندی کلی نگه دار
    if aggressive and len(merged) > 100:
        category_groups = {}
        for issue in merged:
            category = issue.get("type", "other")
            if category not in category_groups:
                category_groups[category] = {"count": 0, "issues": [], "severity": issue.get("severity", "medium")}
            category_groups[category]["count"] += issue.get("merged_count", 1)
            if len(category_groups[category]["issues"]) < 3:
                category_groups[category]["issues"].append(issue)

        merged = []
        for category, data in category_groups.items():
            summary_issue = {
                "type": category,
                "severity": data["severity"],
                "merged_count": data["count"],
                "message": f"[{data['count']} ایراد از نوع {category}]",
                "sample_issues": data["issues"][:3],
                "is_summary": True
            }
            merged.append(summary_issue)

        # مرتب‌سازی براساس تعداد
        merged.sort(key=lambda x: x.get("merged_count", 0), reverse=True)
        logger.info(f"[Merge Issues] After step 4 (aggressive): {len(merged)} categories")

    return merged


@router.get("/{project_id}/health/issues")
async def get_project_issues(
    project_id: str,
    merge_similar: bool = True,  # 🔴 ادغام ایرادات مشابه
    aggressive_merge: bool = False,  # 🆕 ادغام تهاجمی (برای >100 ایراد)
    db=Depends(get_db)
):
    """
    دریافت لیست ایرادات شناسایی شده

    پارامترها:
    - merge_similar: اگر True باشد، ایرادات مشابه ادغام می‌شوند (پیش‌فرض: True)
    - aggressive_merge: اگر True باشد، ادغام تهاجمی انجام می‌شود (برای لیست‌های بزرگ)
    """
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="پروژه یافت نشد")

    issues = []
    original_count = 0
    try:
        if project.issues_found:
            issues = json.loads(project.issues_found)
            original_count = len(issues)

            # 🔴 ادغام ایرادات مشابه
            if merge_similar and len(issues) > 1:
                # اگر بیش از 200 ایراد باشد، ادغام تهاجمی خودکار فعال شود
                auto_aggressive = original_count > 200
                issues = _merge_similar_issues(issues, aggressive=aggressive_merge or auto_aggressive)
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
        "original_count": original_count,  # 🔴 تعداد قبل از ادغام
        "merged_count": original_count - len(issues) if merge_similar else 0,  # 🔴 تعداد ادغام شده
        "grouped": grouped,
        "counts": {k: len(v) for k, v in grouped.items()}
    }


class MarkIssueConvertedRequest(BaseModel):
    """درخواست علامت‌گذاری issue به عنوان تبدیل شده"""
    field_id: str


@router.post("/{project_id}/health/issues/{issue_id}/mark-converted")
async def mark_issue_as_converted(
    project_id: str,
    issue_id: str,
    request: MarkIssueConvertedRequest,
    db=Depends(get_db)
):
    """علامت‌گذاری یک issue به عنوان تبدیل شده به فیلد پویا"""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="پروژه یافت نشد")

    issues = []
    try:
        if project.issues_found:
            issues = json.loads(project.issues_found)
    except:
        pass

    # پیدا کردن و بروزرسانی issue
    found = False
    for i, issue in enumerate(issues):
        # تطبیق با id یا با index
        current_id = issue.get("id") or f"issue_{i}"
        if current_id == issue_id or f"issue_{i}" == issue_id:
            issues[i]["id"] = issue_id
            issues[i]["converted_to_field"] = True
            issues[i]["converted_field_id"] = request.field_id
            issues[i]["converted_at"] = datetime.utcnow().isoformat()
            found = True
            break

    if not found:
        raise HTTPException(status_code=404, detail="ایراد یافت نشد")

    project.issues_found = json.dumps(issues, ensure_ascii=False)
    db.commit()

    return {
        "success": True,
        "message": "ایراد به عنوان تبدیل شده علامت‌گذاری شد",
        "issue_id": issue_id,
        "field_id": request.field_id
    }


@router.get("/{project_id}/health/issues/unconverted-count")
async def get_unconverted_issues_count(project_id: str, db=Depends(get_db)):
    """دریافت تعداد ایرادات تبدیل نشده"""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="پروژه یافت نشد")

    issues = []
    try:
        if project.issues_found:
            issues = json.loads(project.issues_found)
    except:
        pass

    total = len(issues)
    converted = sum(1 for i in issues if i.get("converted_to_field"))
    unconverted = total - converted

    return {
        "success": True,
        "total": total,
        "converted": converted,
        "unconverted": unconverted
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


# =====================================
# Analysis Progress & Control Endpoints
# برای Pause/Resume/Stop و Polling
# =====================================

@router.get("/{project_id}/health/progress")
async def get_analysis_progress_endpoint(project_id: str, db=Depends(get_db)):
    """
    دریافت وضعیت فعلی تحلیل (برای Polling)

    این endpoint به جای SSE استفاده میشه تا با جابجایی صفحه قطع نشه

    Returns:
        - status: idle, running, paused, completed, failed, stopped
        - phase: preparing, micro, macro, structural, completed
        - progress: درصد پیشرفت
        - current_file: فایل در حال تحلیل
        - current_model: مدل در حال کار
        - analyzed_files: تعداد فایل‌های تحلیل شده
        - total_files: تعداد کل فایل‌ها
        - issues_found: تعداد مشکلات یافت شده
        - elapsed_time: زمان سپری شده (ثانیه)
        - model_statuses: وضعیت هر مدل
    """
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="پروژه یافت نشد")

    # بارگذاری progress از دیتابیس
    progress_manager = AnalysisProgressManager(project_id, db)
    progress = progress_manager.load_progress()

    # محاسبه درصد پیشرفت
    progress_percentage = progress_manager.get_progress_percentage()

    return {
        "success": True,
        "project_id": project_id,
        "progress": {
            "status": progress.get("status", "idle"),
            "phase": progress.get("phase", "preparing"),
            "percentage": progress_percentage,
            "total_files": progress.get("total_files", 0),
            "analyzed_files": progress.get("analyzed_files", 0),
            "current_file": progress.get("current_file", ""),
            "current_model": progress.get("current_model", ""),
            "model_statuses": progress.get("model_statuses", {}),
            "issues_found": progress.get("issues_found", 0),
            "elapsed_time": progress.get("elapsed_time", 0),
            "started_at": progress.get("started_at"),
            "last_update": progress.get("last_update"),
            "message": progress.get("message", ""),
            "error": progress.get("error"),
            "can_resume": progress_manager.can_resume()
        }
    }


@router.post("/{project_id}/health/pause")
async def pause_project_analysis(project_id: str, db=Depends(get_db)):
    """
    توقف موقت تحلیل

    تحلیل در نقطه فعلی متوقف میشه و میتونه ادامه پیدا کنه
    """
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="پروژه یافت نشد")

    progress_manager = AnalysisProgressManager(project_id, db)
    progress = progress_manager.load_progress()

    if progress.get("status") != "running":
        return {
            "success": False,
            "message": "تحلیل در حال اجرا نیست",
            "current_status": progress.get("status")
        }

    # علامت‌گذاری برای توقف
    progress_manager.pause_analysis()

    # همچنین به active manager سیگنال بده
    if project_id in _active_progress_managers:
        _active_progress_managers[project_id].pause_analysis()

    logger.info(f"⏸️ Analysis paused for project {project_id}")

    return {
        "success": True,
        "message": "تحلیل متوقف شد",
        "project_id": project_id,
        "analyzed_files": progress.get("analyzed_files", 0),
        "can_resume": True
    }


@router.post("/{project_id}/health/resume")
async def resume_project_analysis(
    project_id: str,
    background_tasks: BackgroundTasks,
    db=Depends(get_db)
):
    """
    ادامه تحلیل متوقف شده

    از جایی که متوقف شده ادامه میده
    """
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="پروژه یافت نشد")

    progress_manager = AnalysisProgressManager(project_id, db)
    progress = progress_manager.load_progress()

    if not progress_manager.can_resume():
        return {
            "success": False,
            "message": "امکان ادامه تحلیل وجود ندارد",
            "current_status": progress.get("status"),
            "hint": "تحلیل باید در وضعیت paused یا failed باشد و حداقل یک فایل تحلیل شده باشد"
        }

    # دریافت فایل‌های پروژه
    files = db.query(ProjectFile).filter(ProjectFile.project_id == project_id).all()
    all_files = [f.file_path for f in files]

    # فایل‌های باقیمانده
    remaining_files = progress_manager.get_remaining_files(all_files)

    if not remaining_files:
        # همه فایل‌ها تحلیل شدن
        progress_manager.complete_analysis()
        return {
            "success": True,
            "message": "همه فایل‌ها قبلاً تحلیل شده‌اند",
            "status": "completed"
        }

    # ادامه تحلیل
    progress_manager.resume_analysis()

    # دریافت تنظیمات قبلی
    model_ids = list(progress.get("model_statuses", {}).keys())
    if not model_ids:
        from ...services.ai_manager import get_ai_manager
        ai_manager = get_ai_manager()
        model_ids = [m.id for m in ai_manager.get_available_models()]

    # اجرای ادامه تحلیل در background
    asyncio.create_task(
        _run_resumed_analysis_task(
            project_id=project_id,
            remaining_files=remaining_files,
            model_ids=model_ids,
            progress_manager=progress_manager
        )
    )

    logger.info(f"▶️ Analysis resumed for project {project_id}, {len(remaining_files)} files remaining")

    return {
        "success": True,
        "message": "تحلیل ادامه یافت",
        "project_id": project_id,
        "remaining_files": len(remaining_files),
        "completed_files": len(progress.get("completed_files", []))
    }


@router.post("/{project_id}/health/stop")
async def stop_project_analysis(project_id: str, db=Depends(get_db)):
    """
    توقف کامل تحلیل

    تحلیل متوقف میشه و نتایج جزئی ذخیره میشه
    """
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="پروژه یافت نشد")

    progress_manager = AnalysisProgressManager(project_id, db)
    progress = progress_manager.load_progress()

    if progress.get("status") not in ["running", "paused"]:
        return {
            "success": False,
            "message": "تحلیلی برای توقف وجود ندارد",
            "current_status": progress.get("status")
        }

    # توقف کامل
    progress_manager.stop_analysis()

    # سیگنال به active manager
    if project_id in _active_progress_managers:
        _active_progress_managers[project_id].stop_analysis()

    # ذخیره نتایج جزئی
    partial_results = progress.get("partial_results", {})
    if partial_results:
        try:
            # استخراج نمرات از نتایج جزئی
            micro_results = partial_results.get("micro_analysis", {}).get("files", {})
            if micro_results:
                # محاسبه میانگین نمرات
                total_score = 0
                count = 0
                for file_result in micro_results.values():
                    if isinstance(file_result, dict) and "score" in file_result:
                        total_score += file_result.get("score", 0)
                        count += 1

                if count > 0:
                    avg_score = total_score / count
                    project.health_scores = json.dumps({
                        "total": avg_score,
                        "micro": avg_score,
                        "partial": True,
                        "files_analyzed": count
                    }, ensure_ascii=False)

                    project.file_health_map = json.dumps(micro_results, ensure_ascii=False)
                    db.commit()
        except Exception as e:
            logger.error(f"Error saving partial results: {e}")

    logger.info(f"⏹️ Analysis stopped for project {project_id}")

    return {
        "success": True,
        "message": "تحلیل متوقف شد",
        "project_id": project_id,
        "analyzed_files": progress.get("analyzed_files", 0),
        "partial_results_saved": bool(partial_results)
    }


@router.post("/{project_id}/health/clear-progress")
async def clear_analysis_progress(project_id: str, db=Depends(get_db)):
    """
    پاک کردن وضعیت تحلیل

    برای شروع تحلیل از صفر
    """
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="پروژه یافت نشد")

    progress_manager = AnalysisProgressManager(project_id, db)
    progress_manager.clear_progress()

    # پاک کردن از active managers
    if project_id in _active_progress_managers:
        del _active_progress_managers[project_id]

    logger.info(f"🗑️ Analysis progress cleared for project {project_id}")

    return {
        "success": True,
        "message": "وضعیت تحلیل پاک شد",
        "project_id": project_id
    }


async def _run_resumed_analysis_task(
    project_id: str,
    remaining_files: List[str],
    model_ids: List[str],
    progress_manager: AnalysisProgressManager
):
    """
    تسک ادامه تحلیل از نقطه توقف
    """
    from ...core.database import SessionLocal
    from ...services.deep_analysis_service import get_deep_analysis_service
    from ...services.ai_manager import get_ai_manager

    logger.info(f"📂 Resuming analysis for {project_id} with {len(remaining_files)} remaining files")

    db = SessionLocal()

    try:
        # ذخیره progress manager در دیکشنری فعال
        _active_progress_managers[project_id] = progress_manager

        ai_manager = get_ai_manager()

        # دریافت محتوای فایل‌های باقیمانده
        files = db.query(ProjectFile).filter(
            ProjectFile.project_id == project_id,
            ProjectFile.file_path.in_(remaining_files)
        ).all()

        files_data = [
            {
                "path": f.file_path,
                "content": f.content or "",
                "file_type": f.file_type
            }
            for f in files
        ]

        project = db.query(Project).filter(Project.id == project_id).first()

        # ساخت deep analyzer با progress callback
        async def progress_callback(data: dict):
            progress_manager._progress.update(data)
            progress_manager.save_progress()

        from ...services.deep_analysis_service import DeepAnalysisService
        deep_analyzer = DeepAnalysisService(
            ai_manager=ai_manager,
            progress_callback=progress_callback
        )

        # اجرای تحلیل
        analysis_result = await deep_analyzer.run_full_analysis(
            project_id=project_id,
            files=files_data,
            roadmap_content=project.roadmap_content or "",
            readme_content=project.readme_content or "",
            model_ids=model_ids,
            instruction="ادامه تحلیل",
            db_session=db,
            progress_manager=progress_manager
        )

        # ذخیره نتایج نهایی
        if analysis_result.get("status") == "completed":
            project.health_scores = json.dumps(
                analysis_result.get("overall_scores", {}),
                ensure_ascii=False
            )
            project.file_health_map = json.dumps(
                analysis_result.get("file_health_map", {}),
                ensure_ascii=False
            )
            # 🔴 رفع محدودیت - تمام ایرادات ذخیره می‌شوند
            project.issues_found = json.dumps(
                analysis_result.get("issues", []),
                ensure_ascii=False
            )
            project.last_analysis_at = datetime.utcnow()
            project.last_analysis_models = json.dumps(model_ids, ensure_ascii=False)
            db.commit()

            progress_manager.complete_analysis(
                overall_score=analysis_result.get("overall_scores", {}).get("total", 0),
                total_issues=len(analysis_result.get("issues", []))
            )

            logger.info(f"✅ Resumed analysis completed for {project_id}")

    except Exception as e:
        logger.error(f"❌ Resumed analysis failed for {project_id}: {e}", exc_info=True)
        progress_manager.fail_analysis(str(e))

    finally:
        # پاک کردن از active managers
        if project_id in _active_progress_managers:
            del _active_progress_managers[project_id]
        db.close()


# =====================================
# 🆕 API Endpoints برای زنجیره اعتبارسنجی
# Validation Chain Endpoints
# =====================================

@router.get("/{project_id}/health/rejected-issues")
async def get_rejected_issues_archive(
    project_id: str,
    page: int = 1,
    page_size: int = 20,
    db=Depends(get_db)
):
    """
    دریافت آرشیو ایرادات رد شده

    این ایرادات توسط مدل‌های health analysis شناسایی شده
    اما توسط مدل اعتبارسنج رد شده‌اند.
    """
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="پروژه یافت نشد")

    archive = []
    if project.rejected_issues_archive:
        try:
            archive = json.loads(project.rejected_issues_archive)
        except:
            pass

    # صفحه‌بندی
    total = len(archive)
    start = (page - 1) * page_size
    end = start + page_size
    paginated = archive[start:end]

    return {
        "success": True,
        "rejected_issues": paginated,
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total": total,
            "total_pages": (total + page_size - 1) // page_size if total > 0 else 0
        },
        "summary": {
            "total_rejected": total,
            "by_validator": {},
            "by_source_model": {}
        }
    }


@router.get("/{project_id}/health/validation-results")
async def get_validation_results(
    project_id: str,
    db=Depends(get_db)
):
    """
    دریافت آخرین نتایج اعتبارسنجی

    شامل:
    - تعداد ایرادات بررسی شده
    - تعداد تایید شده
    - تعداد رد شده
    - خلاصه اعتبارسنجی
    - لیست ایرادات تایید شده با مارکر
    """
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="پروژه یافت نشد")

    validation_results = {}
    if project.last_validation_results:
        try:
            validation_results = json.loads(project.last_validation_results)
        except:
            pass

    return {
        "success": True,
        "validation_results": validation_results,
        "has_validation": bool(validation_results)
    }


@router.delete("/{project_id}/health/rejected-issues/{issue_id}")
async def restore_rejected_issue(
    project_id: str,
    issue_id: str,
    db=Depends(get_db)
):
    """
    بازگرداندن یک ایراد رد شده به لیست ایرادات فعال

    اگر کاربر فکر می‌کند ایراد به اشتباه رد شده،
    می‌تواند آن را بازگرداند.
    """
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="پروژه یافت نشد")

    archive = []
    if project.rejected_issues_archive:
        try:
            archive = json.loads(project.rejected_issues_archive)
        except:
            pass

    # پیدا کردن ایراد
    restored_issue = None
    new_archive = []
    for item in archive:
        if item.get("id") == issue_id:
            restored_issue = item
        else:
            new_archive.append(item)

    if not restored_issue:
        raise HTTPException(status_code=404, detail="ایراد یافت نشد")

    # اضافه کردن به issues_found
    issues = []
    if project.issues_found:
        try:
            issues = json.loads(project.issues_found)
        except:
            pass

    original = restored_issue.get("original_issue", {})
    original["restored_from_archive"] = True
    original["restored_at"] = datetime.utcnow().isoformat()
    issues.append(original)

    # ذخیره
    project.rejected_issues_archive = json.dumps(new_archive, ensure_ascii=False)
    project.issues_found = json.dumps(issues, ensure_ascii=False)
    db.commit()

    return {
        "success": True,
        "message": "ایراد به لیست فعال بازگردانده شد",
        "restored_issue": original
    }


@router.get("/{project_id}/health/chain-status")
async def get_validation_chain_status(
    project_id: str,
    db=Depends(get_db)
):
    """
    دریافت وضعیت کامل زنجیره اعتبارسنجی

    نمایش یکپارچه:
    - وضعیت health analysis
    - وضعیت اعتبارسنجی
    - فیلدهای ایجاد شده با مارکر
    - ایرادات رد شده
    - حالت ایده‌آل
    """
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="پروژه یافت نشد")

    # Parse all relevant data
    health_scores = {}
    issues_found = []
    validation_results = {}
    rejected_archive = []
    dynamic_fields = []

    if project.health_scores:
        try:
            health_scores = json.loads(project.health_scores)
        except:
            pass

    if project.issues_found:
        try:
            issues_found = json.loads(project.issues_found)
        except:
            pass

    if project.last_validation_results:
        try:
            validation_results = json.loads(project.last_validation_results)
        except:
            pass

    if project.rejected_issues_archive:
        try:
            rejected_archive = json.loads(project.rejected_issues_archive)
        except:
            pass

    if project.dynamic_fields:
        try:
            dynamic_fields = json.loads(project.dynamic_fields)
        except:
            pass

    # فیلدهای با مارکر اعتبارسنجی
    validated_fields = [
        f for f in dynamic_fields
        if f.get("validation_marker") == "validated" and not f.get("archived")
    ]

    # فیلدهای اجرا نشده
    unexecuted_fields = [
        f for f in dynamic_fields
        if not f.get("archived") and not f.get("executed") and f.get("field_type") == "temporary"
    ]

    return {
        "success": True,
        "chain_status": {
            # Health Analysis
            "health_analysis": {
                "scores": health_scores,
                "total_issues": len(issues_found),
                "last_analysis": project.last_analysis_at.isoformat() if project.last_analysis_at else None,
                "models_used": json.loads(project.last_analysis_models) if project.last_analysis_models else []
            },

            # Validation
            "validation": {
                "last_validated": validation_results.get("validated_at"),
                "validator_model": validation_results.get("validator_model"),
                "total_reviewed": validation_results.get("total_issues_reviewed", 0),
                "validated_count": validation_results.get("validated_count", 0),
                "rejected_count": validation_results.get("rejected_count", 0),
                "summary": validation_results.get("validation_summary", "")
            },

            # Dynamic Fields
            "fields": {
                "total_active": len([f for f in dynamic_fields if not f.get("archived")]),
                "validated_fields": len(validated_fields),
                "unexecuted_fields": len(unexecuted_fields),
                "archived_fields": len([f for f in dynamic_fields if f.get("archived")])
            },

            # Rejected Archive
            "rejected_archive": {
                "total": len(rejected_archive),
                "recent": rejected_archive[:5]  # 5 تای اخیر
            },

            # Ideal State
            "ideal_state": {
                "defined": bool(project.ideal_state),
                "preview": (project.ideal_state or "")[:500]
            },

            # Roadmap
            "roadmap": {
                "defined": bool(project.roadmap_content),
                "preview": (project.roadmap_content or "")[:500]
            }
        }
    }
