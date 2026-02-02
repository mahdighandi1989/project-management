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
from ...core.logging_utils import StructuredLogger
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
from ...services.security_scanner import get_security_scanner
from ...services.test_coverage_analyzer import get_test_coverage_analyzer
from ...services.journal_service import get_journal_service

logger = logging.getLogger(__name__)
# لاگر ساختاریافته
slog = StructuredLogger(__name__, "HEALTH")
# سرویس ژورنال
journal = get_journal_service()

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
    depth: str = "standard"  # 🆕 عمق تحلیل: quick, standard, deep, thorough


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

    🔴 قبل از پاک کردن، همه داده‌ها در بایگانی عمومی ذخیره می‌شوند
    برای شروع از صفر و رفع سردرگمی درباره داده‌های قدیمی
    """
    import logging
    import uuid
    from datetime import datetime

    logger = logging.getLogger(__name__)
    logger.info(f"🗑️ [CLEAR] Starting clear analysis data for project {project_id}")

    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        logger.warning(f"🗑️ [CLEAR] Project not found: {project_id}")
        raise HTTPException(status_code=404, detail="پروژه یافت نشد")

    # ====================================
    # 🔴 مرحله ۱: ذخیره در بایگانی عمومی قبل از پاک کردن
    # ====================================
    logger.info(f"🗑️ [CLEAR] Step 1: Saving data to general archive...")

    # دریافت بایگانی فعلی
    general_archive = []
    try:
        if project.general_archive:
            general_archive = json.loads(project.general_archive) if isinstance(project.general_archive, str) else project.general_archive
    except:
        general_archive = []

    archive_timestamp = datetime.utcnow().isoformat()
    archived_items = []

    # 1. بایگانی health_scores
    if project.health_scores:
        try:
            health_data = json.loads(project.health_scores) if isinstance(project.health_scores, str) else project.health_scores
            archive_item = {
                "id": str(uuid.uuid4()),
                "type": "health_analysis",
                "category": "امتیازات سلامت",
                "title": f"تحلیل سلامت - {project.last_analysis_at.strftime('%Y/%m/%d %H:%M') if project.last_analysis_at else 'تاریخ نامشخص'}",
                "content": health_data,
                "summary": f"امتیاز کلی: {health_data.get('overall', 'نامشخص')}",
                "archived_at": archive_timestamp,
                "archived_reason": "clear_button",
                "archived_by": "user",
                "metadata": {
                    "original_created_at": project.last_analysis_at.isoformat() if project.last_analysis_at else None,
                    "models_used": json.loads(project.last_analysis_models) if project.last_analysis_models else []
                }
            }
            general_archive.append(archive_item)
            archived_items.append("health_scores")
            logger.info(f"🗑️ [CLEAR] Archived health_scores")
        except Exception as e:
            logger.warning(f"🗑️ [CLEAR] Could not archive health_scores: {e}")

    # 2. بایگانی file_health_map
    if project.file_health_map:
        try:
            file_map = json.loads(project.file_health_map) if isinstance(project.file_health_map, str) else project.file_health_map
            files_count = len(file_map) if isinstance(file_map, dict) else 0
            archive_item = {
                "id": str(uuid.uuid4()),
                "type": "file_health",
                "category": "نقشه سلامت فایل‌ها",
                "title": f"نقشه سلامت {files_count} فایل",
                "content": file_map,
                "summary": f"{files_count} فایل تحلیل شده",
                "archived_at": archive_timestamp,
                "archived_reason": "clear_button",
                "archived_by": "user",
                "metadata": {
                    "files_count": files_count,
                    "original_created_at": project.last_analysis_at.isoformat() if project.last_analysis_at else None
                }
            }
            general_archive.append(archive_item)
            archived_items.append("file_health_map")
            logger.info(f"🗑️ [CLEAR] Archived file_health_map ({files_count} files)")
        except Exception as e:
            logger.warning(f"🗑️ [CLEAR] Could not archive file_health_map: {e}")

    # 3. بایگانی issues_found
    if project.issues_found:
        try:
            issues = json.loads(project.issues_found) if isinstance(project.issues_found, str) else project.issues_found
            issues_count = len(issues) if isinstance(issues, list) else 0
            if issues_count > 0:
                # دسته‌بندی بر اساس severity
                severity_breakdown = {}
                for issue in issues:
                    sev = issue.get("severity", "unknown")
                    severity_breakdown[sev] = severity_breakdown.get(sev, 0) + 1

                archive_item = {
                    "id": str(uuid.uuid4()),
                    "type": "issues",
                    "category": "ایرادات شناسایی شده",
                    "title": f"{issues_count} ایراد شناسایی شده",
                    "content": issues,
                    "summary": f"ایرادات: {', '.join([f'{k}: {v}' for k, v in severity_breakdown.items()])}",
                    "archived_at": archive_timestamp,
                    "archived_reason": "clear_button",
                    "archived_by": "user",
                    "metadata": {
                        "issues_count": issues_count,
                        "severity_breakdown": severity_breakdown,
                        "original_created_at": project.last_analysis_at.isoformat() if project.last_analysis_at else None
                    }
                }
                general_archive.append(archive_item)
                archived_items.append("issues_found")
                logger.info(f"🗑️ [CLEAR] Archived issues_found ({issues_count} issues)")
        except Exception as e:
            logger.warning(f"🗑️ [CLEAR] Could not archive issues_found: {e}")

    # 4. بایگانی ideal_state
    if project.ideal_state:
        try:
            archive_item = {
                "id": str(uuid.uuid4()),
                "type": "ideal_state",
                "category": "وضعیت ایده‌آل",
                "title": "توضیحات وضعیت ایده‌آل پروژه",
                "content": {"text": project.ideal_state},
                "summary": project.ideal_state[:100] + "..." if len(project.ideal_state) > 100 else project.ideal_state,
                "archived_at": archive_timestamp,
                "archived_reason": "clear_button",
                "archived_by": "user",
                "metadata": {}
            }
            general_archive.append(archive_item)
            archived_items.append("ideal_state")
            logger.info(f"🗑️ [CLEAR] Archived ideal_state")
        except Exception as e:
            logger.warning(f"🗑️ [CLEAR] Could not archive ideal_state: {e}")

    # 5. بایگانی last_validation_results
    if project.last_validation_results:
        try:
            validation = json.loads(project.last_validation_results) if isinstance(project.last_validation_results, str) else project.last_validation_results
            archive_item = {
                "id": str(uuid.uuid4()),
                "type": "validation",
                "category": "نتایج اعتبارسنجی",
                "title": f"اعتبارسنجی - {validation.get('validated_at', 'تاریخ نامشخص')[:10]}",
                "content": validation,
                "summary": f"تایید: {validation.get('validated_count', 0)}, رد: {validation.get('rejected_count', 0)}",
                "archived_at": archive_timestamp,
                "archived_reason": "clear_button",
                "archived_by": "user",
                "metadata": {
                    "validator_model": validation.get("validator_model"),
                    "validated_count": validation.get("validated_count", 0),
                    "rejected_count": validation.get("rejected_count", 0)
                }
            }
            general_archive.append(archive_item)
            archived_items.append("last_validation_results")
            logger.info(f"🗑️ [CLEAR] Archived last_validation_results")
        except Exception as e:
            logger.warning(f"🗑️ [CLEAR] Could not archive last_validation_results: {e}")

    # ذخیره بایگانی عمومی
    if archived_items:
        project.general_archive = json.dumps(general_archive, ensure_ascii=False)
        logger.info(f"🗑️ [CLEAR] Saved {len(archived_items)} items to general archive")

    # ====================================
    # 🔴 مرحله ۲: پاک کردن داده‌ها
    # ====================================
    logger.info(f"🗑️ [CLEAR] Step 2: Clearing analysis data...")

    project.health_scores = None
    project.file_health_map = None
    project.issues_found = None
    project.ideal_state = None
    project.last_analysis_id = None
    project.last_analysis_at = None
    project.last_analysis_models = None
    # نکته: last_validation_results و rejected_issues_archive رو نگه میداریم چون بخش validation هستن

    db.commit()

    logger.info(f"🗑️ [CLEAR] ✅ Successfully cleared analysis data for project {project_id}")
    logger.info(f"🗑️ [CLEAR] Archived items: {archived_items}")

    return {
        "success": True,
        "message": "همه داده‌های تحلیل پاک شدند و در بایگانی ذخیره شدند",
        "project_id": project_id,
        "archived_items": archived_items,
        "archive_count": len(archived_items),
        "total_archive_size": len(general_archive)
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
                "structure_score": health_scores.get("structure_score", health_scores.get("structural", 0)),
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
    slog.api_request("POST", f"/{project_id}/health/analyze",
        depth=request.depth,
        models=request.model_ids
    )

    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        slog.error("Project not found", project_id=project_id)
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

    slog.info("Selected models for analysis",
        models=model_ids,
        files_count=len(files_data)
    )

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

    slog.start("Health analysis task",
        project_id=project_id,
        files_count=len(files_data),
        models=model_ids
    )

    db = SessionLocal()

    try:
        # دریافت AI manager برای فراخوانی مدل‌ها
        ai_manager = get_ai_manager()

        # چک کردن وضعیت AI manager
        available_providers = ai_manager.get_available_providers()
        available_models = ai_manager.get_available_models()

        slog.info("AI manager status",
            providers=available_providers,
            models=[m.id for m in available_models]
        )

        if not available_models:
            slog.error("No AI models available - check API keys")
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
        slog.success("Deep analyzer initialized")

        # دریافت پروژه
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            slog.error("Project not found in analysis task", project_id=project_id)
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
                slog.warning("Roadmap update failed", error=str(e)[:100])

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
                slog.warning("README update failed", error=str(e)[:100])

        # 3. اجرای تحلیل عمیق سه‌مرحله‌ای
        slog.step(1, "Starting deep analysis",
            project_id=project_id,
            models=model_ids
        )

        # ایجاد progress manager برای ذخیره وضعیت
        progress_manager = AnalysisProgressManager(project_id, db)
        progress_manager.start_analysis(
            analysis_id=f"analysis_{project_id[:8]}",
            total_files=len(files_data),
            model_ids=model_ids
        )
        _active_progress_managers[project_id] = progress_manager

        try:
            # 🆕 استفاده از عمق تحلیل از request
            depth = getattr(request, 'depth', 'standard')
            slog.info("Running full analysis", depth=depth)

            analysis_result = await deep_analyzer.run_full_analysis(
                project_id=project_id,
                files=files_data,
                roadmap_content=roadmap_content,
                readme_content=readme_content,
                model_ids=model_ids,
                instruction=instruction,
                db_session=db,
                progress_manager=progress_manager,
                depth=depth  # 🆕 پاس دادن عمق
            )
            slog.success("Analysis completed",
                status=analysis_result.get('status'),
                files_analyzed=analysis_result.get('analyzed_files', 0),
                overall_score=analysis_result.get('overall_scores', {}).get('overall', 0)
            )
        except Exception as analysis_error:
            slog.error("Deep analysis failed", exception=analysis_error)
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
            # 🆕 همیشه ادغام ایرادات قبل از ذخیره (رفع مشکل ۳ و ۴)
            raw_issues = analysis_result.get("issues", [])

            # همیشه ادغام انجام بشه (نه فقط وقتی > 100)
            if len(raw_issues) > 1:
                # تنظیم سطح ادغام بر اساس تعداد
                aggressive = len(raw_issues) > 200
                merged_issues = _merge_similar_issues(raw_issues, aggressive=aggressive)

                # علامت‌گذاری که ایرادات ادغام شده‌اند
                for issue in merged_issues:
                    issue["_merged_at_save"] = True  # جلوگیری از ادغام مجدد در زمان خواندن

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

    ایرادات مشابه را پیدا کرده و محتوای آنها را واقعاً ترکیب می‌کند
    به طوری که ایراد نهایی شامل تمام جزئیات باشد و AI بتواند آن را بفهمد.
    """
    if len(issues) <= 1:
        return issues

    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"[Merge Issues] Starting with {len(issues)} issues, aggressive={aggressive}")

    # گروه‌بندی براساس نوع + severity
    type_groups = {}
    for issue in issues:
        # کلید گروه‌بندی
        issue_type = issue.get('type', 'general')
        severity = issue.get('severity', 'medium')
        key = f"{issue_type}|{severity}"

        if key not in type_groups:
            type_groups[key] = []
        type_groups[key].append(issue)

    merged_issues = []

    for key, group in type_groups.items():
        if len(group) == 1:
            # فقط یک ایراد - بدون تغییر
            merged_issues.append(group[0])
        else:
            # چند ایراد مشابه - ادغام محتوا
            merged = _combine_issue_contents(group)
            merged_issues.append(merged)

    logger.info(f"[Merge Issues] Merged {len(issues)} issues into {len(merged_issues)}")

    # مرتب‌سازی براساس اهمیت
    severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    # 🔴 تبدیل امن برای جلوگیری از خطای NoneType comparison
    def safe_issue_sort(x):
        sev = x.get("severity") if x.get("severity") else "medium"
        merged_count = x.get("merged_count") if x.get("merged_count") is not None else 1
        return (severity_order.get(sev, 2), -merged_count)
    merged_issues.sort(key=safe_issue_sort)

    return merged_issues


def _combine_issue_contents(issues: list) -> dict:
    """
    ترکیب واقعی محتوای چند ایراد مشابه به یک ایراد جامع
    """
    if not issues:
        return {}

    base = issues[0].copy()
    issue_type = base.get("type", "ایراد")
    severity = base.get("severity", "medium")

    # جمع‌آوری تمام فایل‌های تحت تاثیر
    affected_files = {}
    all_suggestions = []
    all_descriptions = []

    for issue in issues:
        file_path = issue.get("file", "نامشخص")
        line = issue.get("line")
        message = issue.get("message", "")
        suggestion = issue.get("suggestion", "") or issue.get("fix", "")

        # گروه‌بندی براساس فایل
        if file_path not in affected_files:
            affected_files[file_path] = {"lines": [], "messages": []}

        if line:
            affected_files[file_path]["lines"].append(line)
        if message and message not in affected_files[file_path]["messages"]:
            affected_files[file_path]["messages"].append(message)

        if suggestion and suggestion not in all_suggestions:
            all_suggestions.append(suggestion)

        if message and message not in all_descriptions:
            all_descriptions.append(message)

    # ساخت توضیح جامع و خوانا برای AI
    combined_description = f"## {issue_type} ({severity})\n\n"
    combined_description += f"**تعداد کل:** {len(issues)} مورد در {len(affected_files)} فایل\n\n"

    # لیست فایل‌ها با جزئیات
    combined_description += "### فایل‌های تحت تاثیر:\n"
    for file_path, details in list(affected_files.items())[:20]:  # حداکثر 20 فایل
        lines_str = ""
        if details["lines"]:
            unique_lines = sorted(set(details["lines"]))[:10]
            lines_str = f" (خطوط: {', '.join(map(str, unique_lines))})"
        combined_description += f"- `{file_path}`{lines_str}\n"

        # اضافه کردن پیام‌های خاص این فایل
        for msg in details["messages"][:3]:
            if msg:
                combined_description += f"  - {msg[:200]}\n"

    if len(affected_files) > 20:
        combined_description += f"- ... و {len(affected_files) - 20} فایل دیگر\n"

    # توضیحات کلی (بدون تکرار)
    unique_descriptions = list(set(all_descriptions))[:10]
    if unique_descriptions:
        combined_description += "\n### توضیحات:\n"
        for desc in unique_descriptions:
            if desc:
                combined_description += f"- {desc[:300]}\n"

    # راه‌حل‌های پیشنهادی
    unique_suggestions = list(set(all_suggestions))[:5]
    if unique_suggestions:
        combined_description += "\n### راه‌حل‌های پیشنهادی:\n"
        for sug in unique_suggestions:
            if sug:
                combined_description += f"- {sug[:400]}\n"

    # ساخت ایراد ادغام شده
    merged_issue = {
        "id": base.get("id", f"merged_{len(issues)}"),
        "type": issue_type,
        "severity": severity,
        "message": combined_description,  # محتوای کامل و جامع
        "title": f"{issue_type}: {len(issues)} مورد در {len(affected_files)} فایل",
        "merged_count": len(issues),
        "affected_files": list(affected_files.keys())[:30],
        "affected_lines": {f: d["lines"][:20] for f, d in list(affected_files.items())[:10]},
        "suggestions": unique_suggestions,
        "is_merged": True,
        # برای سازگاری با UI
        "file": list(affected_files.keys())[0] if affected_files else None,
        "original_issues_count": len(issues)
    }

    return merged_issue


@router.get("/{project_id}/health/issues")
async def get_project_issues(
    project_id: str,
    merge_similar: bool = True,  # 🔴 ادغام ایرادات مشابه
    aggressive_merge: bool = False,  # 🆕 ادغام تهاجمی (برای >100 ایراد)
    persist_merge: bool = True,  # 🆕 ذخیره ادغام در دیتابیس (رفع ناپایداری)
    db=Depends(get_db)
):
    """
    دریافت لیست ایرادات شناسایی شده

    پارامترها:
    - merge_similar: اگر True باشد، ایرادات مشابه ادغام می‌شوند (پیش‌فرض: True)
    - aggressive_merge: اگر True باشد، ادغام تهاجمی انجام می‌شود (برای لیست‌های بزرگ)
    - persist_merge: اگر True باشد، نتیجه ادغام در دیتابیس ذخیره می‌شود (پیش‌فرض: True)
    """
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="پروژه یافت نشد")

    issues = []
    original_count = 0
    merge_persisted = False
    already_merged = False
    try:
        if project.issues_found:
            issues = json.loads(project.issues_found)
            original_count = len(issues)

            # 🆕 بررسی آیا قبلاً در زمان ذخیره ادغام شده (رفع مشکل ۴ - ناپایداری)
            already_merged = any(issue.get("_merged_at_save") for issue in issues)

            # 🔴 ادغام ایرادات مشابه - فقط اگر قبلاً ادغام نشده
            if merge_similar and len(issues) > 1 and not already_merged:
                # اگر بیش از 200 ایراد باشد، ادغام تهاجمی خودکار فعال شود
                auto_aggressive = original_count > 200
                merged_issues = _merge_similar_issues(issues, aggressive=aggressive_merge or auto_aggressive)

                # علامت‌گذاری ایرادات ادغام شده
                for issue in merged_issues:
                    issue["_merged_at_save"] = True

                # 🆕 ذخیره نتیجه ادغام در دیتابیس برای پایداری
                if persist_merge and len(merged_issues) < original_count:
                    project.issues_found = json.dumps(merged_issues, ensure_ascii=False)
                    db.commit()
                    merge_persisted = True
                    logger.info(f"🔀 Merged issues persisted: {original_count} -> {len(merged_issues)}")

                issues = merged_issues
    except Exception as e:
        logger.error(f"Error getting issues: {e}")
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
        "merged_count": original_count - len(issues) if merge_similar and not already_merged else 0,
        "merge_persisted": merge_persisted,  # 🆕 آیا ادغام ذخیره شد؟
        "already_merged": already_merged,  # 🆕 آیا قبلاً ادغام شده بود؟
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
# 🆕 API Endpoints برای بایگانی عمومی
# General Archive Endpoints
# =====================================

@router.get("/{project_id}/health/general-archive")
async def get_general_archive(
    project_id: str,
    type_filter: str = None,  # فیلتر بر اساس نوع: health_analysis, issues, file_health, validation, ideal_state
    page: int = 1,
    page_size: int = 20,
    db=Depends(get_db)
):
    """
    دریافت بایگانی عمومی پروژه

    شامل همه داده‌های پاک شده:
    - health_analysis: امتیازات سلامت
    - issues: ایرادات شناسایی شده
    - file_health: نقشه سلامت فایل‌ها
    - validation: نتایج اعتبارسنجی
    - ideal_state: وضعیت ایده‌آل
    """
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"📦 [ARCHIVE] Getting general archive for project {project_id}")

    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="پروژه یافت نشد")

    archive = []
    if project.general_archive:
        try:
            archive = json.loads(project.general_archive) if isinstance(project.general_archive, str) else project.general_archive
        except:
            pass

    # فیلتر بر اساس نوع
    if type_filter:
        archive = [item for item in archive if item.get("type") == type_filter]

    # مرتب‌سازی بر اساس تاریخ بایگانی (جدیدترین اول)
    archive.sort(key=lambda x: x.get("archived_at", ""), reverse=True)

    # صفحه‌بندی
    total = len(archive)
    start = (page - 1) * page_size
    end = start + page_size
    paginated = archive[start:end]

    # آمار دسته‌بندی
    type_breakdown = {}
    category_breakdown = {}
    for item in archive:
        t = item.get("type", "unknown")
        c = item.get("category", "نامشخص")
        type_breakdown[t] = type_breakdown.get(t, 0) + 1
        category_breakdown[c] = category_breakdown.get(c, 0) + 1

    logger.info(f"📦 [ARCHIVE] Found {total} archived items, returning page {page}")

    return {
        "success": True,
        "project_id": project_id,
        "archive": paginated,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size if page_size > 0 else 0,
        "type_breakdown": type_breakdown,
        "category_breakdown": category_breakdown
    }


@router.get("/{project_id}/health/general-archive/{item_id}")
async def get_archive_item_detail(
    project_id: str,
    item_id: str,
    db=Depends(get_db)
):
    """
    دریافت جزئیات کامل یک آیتم بایگانی شده
    """
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"📦 [ARCHIVE] Getting archive item detail: {item_id}")

    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="پروژه یافت نشد")

    archive = []
    if project.general_archive:
        try:
            archive = json.loads(project.general_archive) if isinstance(project.general_archive, str) else project.general_archive
        except:
            pass

    # پیدا کردن آیتم
    item = next((x for x in archive if x.get("id") == item_id), None)
    if not item:
        raise HTTPException(status_code=404, detail="آیتم بایگانی یافت نشد")

    logger.info(f"📦 [ARCHIVE] Found archive item: {item.get('title')}")

    return {
        "success": True,
        "item": item
    }


@router.delete("/{project_id}/health/general-archive/{item_id}")
async def delete_archive_item(
    project_id: str,
    item_id: str,
    db=Depends(get_db)
):
    """
    حذف دائمی یک آیتم از بایگانی
    """
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"📦 [ARCHIVE] Deleting archive item: {item_id}")

    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="پروژه یافت نشد")

    archive = []
    if project.general_archive:
        try:
            archive = json.loads(project.general_archive) if isinstance(project.general_archive, str) else project.general_archive
        except:
            pass

    # پیدا کردن و حذف آیتم
    original_count = len(archive)
    archive = [x for x in archive if x.get("id") != item_id]

    if len(archive) == original_count:
        raise HTTPException(status_code=404, detail="آیتم بایگانی یافت نشد")

    project.general_archive = json.dumps(archive, ensure_ascii=False)
    db.commit()

    logger.info(f"📦 [ARCHIVE] ✅ Deleted archive item: {item_id}")

    return {
        "success": True,
        "message": "آیتم از بایگانی حذف شد",
        "remaining_count": len(archive)
    }


@router.delete("/{project_id}/health/general-archive")
async def clear_general_archive(
    project_id: str,
    type_filter: str = None,  # اگر مشخص شد فقط آن نوع پاک شود
    db=Depends(get_db)
):
    """
    پاک کردن بایگانی عمومی (همه یا یک نوع خاص)
    """
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"📦 [ARCHIVE] Clearing general archive for project {project_id}, type_filter={type_filter}")

    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="پروژه یافت نشد")

    archive = []
    if project.general_archive:
        try:
            archive = json.loads(project.general_archive) if isinstance(project.general_archive, str) else project.general_archive
        except:
            pass

    original_count = len(archive)

    if type_filter:
        # فقط نوع مشخص شده رو پاک کن
        archive = [x for x in archive if x.get("type") != type_filter]
        deleted_count = original_count - len(archive)
        project.general_archive = json.dumps(archive, ensure_ascii=False)
        message = f"{deleted_count} آیتم از نوع {type_filter} حذف شد"
    else:
        # همه رو پاک کن
        project.general_archive = None
        deleted_count = original_count
        message = f"همه {deleted_count} آیتم بایگانی حذف شدند"

    db.commit()

    logger.info(f"📦 [ARCHIVE] ✅ Cleared archive: {deleted_count} items deleted")

    return {
        "success": True,
        "message": message,
        "deleted_count": deleted_count,
        "remaining_count": len(archive) if type_filter else 0
    }


@router.get("/{project_id}/health/general-archive/download")
async def download_archive(
    project_id: str,
    format: str = "json",
    type_filter: Optional[str] = None,
    db=Depends(get_db)
):
    """
    دانلود بایگانی گزارشات

    فرمت‌های پشتیبانی:
    - json: فرمت JSON
    - csv: فرمت CSV
    - txt: فرمت متنی
    """
    from fastapi.responses import Response
    import csv
    import io

    logger.info(f"📦 [ARCHIVE] Downloading archive for project {project_id}, format={format}")

    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="پروژه یافت نشد")

    # دریافت آرشیو
    archive = []
    if project.general_archive:
        try:
            archive = json.loads(project.general_archive) if isinstance(project.general_archive, str) else project.general_archive
        except:
            pass

    # فیلتر بر اساس نوع
    if type_filter:
        archive = [item for item in archive if item.get("type") == type_filter]

    # مرتب‌سازی بر اساس تاریخ
    archive.sort(key=lambda x: x.get("archived_at", ""), reverse=True)

    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    filename_base = f"archive_{project.name}_{timestamp}"

    # ثبت در ژورنال
    await journal.log_download(
        project_id=project_id,
        download_type="archive",
        format=format,
        items_count=len(archive),
        db=db
    )

    if format == "json":
        content = json.dumps({
            "project_id": project_id,
            "project_name": project.name,
            "export_date": datetime.utcnow().isoformat(),
            "total_items": len(archive),
            "type_filter": type_filter,
            "archive": archive
        }, ensure_ascii=False, indent=2)
        return Response(
            content=content,
            media_type="application/json",
            headers={"Content-Disposition": f'attachment; filename="{filename_base}.json"'}
        )

    elif format == "csv":
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "شناسه",
            "نوع",
            "دسته‌بندی",
            "عنوان",
            "خلاصه",
            "تاریخ بایگانی",
            "دلیل بایگانی"
        ])
        for item in archive:
            writer.writerow([
                item.get("id", ""),
                item.get("type", ""),
                item.get("category", ""),
                item.get("title", ""),
                item.get("summary", ""),
                item.get("archived_at", ""),
                item.get("archived_reason", "")
            ])
        content = output.getvalue()
        return Response(
            content=content.encode("utf-8-sig"),
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="{filename_base}.csv"'}
        )

    elif format == "txt":
        lines = [
            f"📦 بایگانی گزارشات پروژه: {project.name}",
            f"تاریخ خروجی: {datetime.utcnow().isoformat()}",
            f"تعداد آیتم‌ها: {len(archive)}",
            "=" * 60,
            ""
        ]
        for i, item in enumerate(archive, 1):
            lines.extend([
                f"📌 آیتم {i}: {item.get('title', 'بدون عنوان')}",
                f"   نوع: {item.get('type', '-')}",
                f"   دسته: {item.get('category', '-')}",
                f"   تاریخ بایگانی: {item.get('archived_at', '-')}",
                f"   دلیل: {item.get('archived_reason', '-')}",
                f"   خلاصه: {item.get('summary', '-')}",
                ""
            ])
            # محتوای کامل
            content_data = item.get("content", {})
            if content_data:
                lines.append("   📄 محتوا:")
                content_str = json.dumps(content_data, ensure_ascii=False, indent=6)
                for line in content_str.split("\n"):
                    lines.append(f"      {line}")
            lines.append("-" * 60)
            lines.append("")

        content = "\n".join(lines)
        return Response(
            content=content.encode("utf-8"),
            media_type="text/plain; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="{filename_base}.txt"'}
        )

    else:
        raise HTTPException(status_code=400, detail="فرمت نامعتبر. فرمت‌های مجاز: json, csv, txt")


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


# =====================================
# 🆕 نمایشگر فایل با هایلایت ایرادات
# =====================================

class FileIssue(BaseModel):
    """ایراد در یک فایل"""
    line: Optional[int] = None
    start_line: Optional[int] = None
    end_line: Optional[int] = None
    message: str
    severity: str = "medium"
    suggestion: Optional[str] = None
    fix_code: Optional[str] = None
    issue_type: str = "general"


@router.get("/{project_id}/health/file/{file_path:path}/view")
async def get_file_with_issues(
    project_id: str,
    file_path: str,
    include_suggestions: bool = True,
    db=Depends(get_db)
):
    """
    دریافت محتوای فایل با ایرادات هایلایت شده

    - محتوای کامل فایل
    - لیست ایرادات با شماره خط
    - پیشنهادات AI به صورت کامنت
    - نمره سلامت فایل
    """
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="پروژه یافت نشد")

    # دریافت فایل
    file_record = db.query(ProjectFile).filter(
        ProjectFile.project_id == project_id,
        ProjectFile.file_path == file_path
    ).first()

    if not file_record:
        raise HTTPException(status_code=404, detail="فایل یافت نشد")

    content = file_record.content or ""

    # دریافت ایرادات مربوط به این فایل
    issues = []
    file_health = None
    try:
        if project.issues_found:
            all_issues = json.loads(project.issues_found)
            issues = [i for i in all_issues if i.get("file") == file_path]

        # دریافت نمره سلامت فایل
        if project.health_scores:
            health_data = json.loads(project.health_scores)
            file_scores = health_data.get("file_scores", {})
            file_health = file_scores.get(file_path, {})
    except:
        pass

    # ساخت محتوای با کامنت‌های پیشنهادی
    annotated_content = content
    if include_suggestions and issues:
        annotated_content = _add_issue_comments_to_content(
            content,
            issues,
            file_path
        )

    # تشخیص زبان برنامه‌نویسی
    language = _detect_language(file_path)

    return {
        "success": True,
        "file_path": file_path,
        "language": language,
        "original_content": content,
        "annotated_content": annotated_content,
        "line_count": len(content.split('\n')),
        "issues": issues,
        "issues_count": len(issues),
        "health": file_health,
        "validation_stamp": file_health.get("validated") if file_health else None
    }


def _detect_language(file_path: str) -> str:
    """تشخیص زبان برنامه‌نویسی از پسوند فایل"""
    ext_map = {
        '.py': 'python',
        '.js': 'javascript',
        '.ts': 'typescript',
        '.tsx': 'tsx',
        '.jsx': 'jsx',
        '.html': 'html',
        '.css': 'css',
        '.json': 'json',
        '.yaml': 'yaml',
        '.yml': 'yaml',
        '.md': 'markdown',
        '.sql': 'sql',
        '.sh': 'bash',
        '.go': 'go',
        '.rs': 'rust',
        '.java': 'java',
        '.cpp': 'cpp',
        '.c': 'c',
        '.rb': 'ruby',
        '.php': 'php',
    }
    import os
    ext = os.path.splitext(file_path)[1].lower()
    return ext_map.get(ext, 'text')


def _get_comment_syntax(language: str) -> tuple:
    """دریافت سینتکس کامنت برای هر زبان"""
    comment_styles = {
        'python': ('#', '"""', '"""'),
        'javascript': ('//', '/*', '*/'),
        'typescript': ('//', '/*', '*/'),
        'tsx': ('//', '{/*', '*/}'),
        'jsx': ('//', '{/*', '*/}'),
        'html': ('<!--', '<!--', '-->'),
        'css': ('/*', '/*', '*/'),
        'sql': ('--', '/*', '*/'),
        'bash': ('#', ': \'', '\''),
        'go': ('//', '/*', '*/'),
        'rust': ('//', '/*', '*/'),
        'java': ('//', '/*', '*/'),
        'cpp': ('//', '/*', '*/'),
        'c': ('//', '/*', '*/'),
        'ruby': ('#', '=begin', '=end'),
        'php': ('//', '/*', '*/'),
    }
    return comment_styles.get(language, ('#', '/*', '*/'))


def _create_validation_stamp_comment(
    file_path: str,
    model_id: str,
    score: int,
    validation_passed: bool,
    notes: str,
    language: str
) -> str:
    """
    🆕 ایجاد کامنت برچسب تاییدیه برای درج در فایل

    این کامنت در ابتدای فایل اضافه می‌شود و شامل:
    - نام مدل تایید کننده
    - تاریخ و ساعت تایید
    - نمره سلامت
    - وضعیت تایید
    - یادداشت‌های مهندسی
    """
    from datetime import datetime

    single_comment, multi_start, multi_end = _get_comment_syntax(language)
    timestamp = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')

    status_icon = "✅" if validation_passed else "⚠️"
    status_text = "تایید شده" if validation_passed else "نیاز به بررسی"

    # ساخت کامنت چندخطی
    if language in ['python', 'ruby', 'bash']:
        # زبان‌هایی که کامنت چندخطی با علامت متفاوت دارند
        stamp = f'''{multi_start}
🔬 ENGINEERING VALIDATION STAMP
{'=' * 50}
{status_icon} وضعیت: {status_text}
📊 نمره سلامت: {score}%
🤖 تایید کننده: {model_id}
📅 تاریخ: {timestamp}
📁 فایل: {file_path}
{'=' * 50}
📝 یادداشت: {notes[:200] if notes else 'بدون یادداشت'}
{'=' * 50}
⚠️ این کامنت توسط سیستم گزارش مهندسی تولید شده است
{multi_end}'''
    elif language in ['html']:
        stamp = f'''{multi_start}
🔬 ENGINEERING VALIDATION STAMP
{'=' * 50}
{status_icon} وضعیت: {status_text}
📊 نمره سلامت: {score}%
🤖 تایید کننده: {model_id}
📅 تاریخ: {timestamp}
📁 فایل: {file_path}
{'=' * 50}
📝 یادداشت: {notes[:200] if notes else 'بدون یادداشت'}
⚠️ این کامنت توسط سیستم گزارش مهندسی تولید شده است
{multi_end}'''
    else:
        # زبان‌های C-style (JavaScript, TypeScript, Java, etc.)
        stamp = f'''{multi_start}
 * 🔬 ENGINEERING VALIDATION STAMP
 * {'=' * 48}
 * {status_icon} وضعیت: {status_text}
 * 📊 نمره سلامت: {score}%
 * 🤖 تایید کننده: {model_id}
 * 📅 تاریخ: {timestamp}
 * 📁 فایل: {file_path}
 * {'=' * 48}
 * 📝 یادداشت: {notes[:200] if notes else 'بدون یادداشت'}
 * {'=' * 48}
 * ⚠️ این کامنت توسط سیستم گزارش مهندسی تولید شده است
 {multi_end}'''

    return stamp


def _add_issue_comments_to_content(content: str, issues: list, file_path: str) -> str:
    """
    افزودن کامنت‌های پیشنهادی AI به محتوای فایل

    - ایرادات با رنگ قرمز مشخص می‌شوند (به صورت کامنت)
    - پیشنهادات به صورت کامنت در کنار کد اضافه می‌شوند
    - کد اصلی دست نخورده می‌ماند
    """
    if not issues:
        return content

    language = _detect_language(file_path)
    single_comment, multi_start, multi_end = _get_comment_syntax(language)

    lines = content.split('\n')
    annotated_lines = []

    # گروه‌بندی ایرادات براساس شماره خط
    issues_by_line = {}
    for issue in issues:
        line_num = issue.get('line') or issue.get('start_line')
        if line_num:
            if line_num not in issues_by_line:
                issues_by_line[line_num] = []
            issues_by_line[line_num].append(issue)

    for i, line in enumerate(lines, 1):
        # اضافه کردن خط اصلی
        annotated_lines.append(line)

        # اگر این خط ایراد دارد، کامنت اضافه کن
        if i in issues_by_line:
            for issue in issues_by_line[i]:
                severity = issue.get('severity', 'medium')
                severity_icon = '🔴' if severity == 'critical' else '🟠' if severity == 'high' else '🟡' if severity == 'medium' else '🔵'

                # کامنت ایراد
                issue_comment = f"{single_comment} {severity_icon} [ایراد - {issue.get('type', 'general')}]: {issue.get('message', '')}"
                annotated_lines.append(issue_comment)

                # پیشنهاد اصلاح
                if issue.get('suggestion'):
                    suggestion_comment = f"{single_comment} 💡 [پیشنهاد]: {issue.get('suggestion')}"
                    annotated_lines.append(suggestion_comment)

                # کد پیشنهادی
                if issue.get('fix_code'):
                    annotated_lines.append(f"{single_comment} ✅ [کد پیشنهادی]:")
                    for fix_line in issue.get('fix_code', '').split('\n'):
                        annotated_lines.append(f"{single_comment}     {fix_line}")

    return '\n'.join(annotated_lines)


@router.post("/{project_id}/health/file/{file_path:path}/generate-suggestions")
async def generate_file_suggestions(
    project_id: str,
    file_path: str,
    model_id: str = "claude",
    db=Depends(get_db)
):
    """
    تولید پیشنهادات AI برای ایرادات فایل

    - بررسی هر ایراد توسط AI
    - تولید کد اصلاحی
    - افزودن به عنوان کامنت
    """
    from ...services.ai_manager import get_ai_manager
    from ...services.ai_base import Message

    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="پروژه یافت نشد")

    file_record = db.query(ProjectFile).filter(
        ProjectFile.project_id == project_id,
        ProjectFile.file_path == file_path
    ).first()

    if not file_record:
        raise HTTPException(status_code=404, detail="فایل یافت نشد")

    content = file_record.content or ""

    # دریافت ایرادات این فایل
    issues = []
    try:
        if project.issues_found:
            all_issues = json.loads(project.issues_found)
            issues = [i for i in all_issues if i.get("file") == file_path and not i.get("fix_code")]
    except:
        pass

    if not issues:
        return {"success": True, "message": "ایرادی برای بررسی وجود ندارد", "updated_issues": 0}

    ai_manager = get_ai_manager()
    language = _detect_language(file_path)
    updated_count = 0

    for issue in issues[:10]:  # حداکثر 10 ایراد در هر بار
        try:
            line_num = issue.get('line') or issue.get('start_line', 1)
            # استخراج چند خط اطراف ایراد
            lines = content.split('\n')
            start = max(0, line_num - 5)
            end = min(len(lines), line_num + 5)
            context_lines = lines[start:end]
            context = '\n'.join(f"{i+start+1}: {l}" for i, l in enumerate(context_lines))

            prompt = f"""
فایل: {file_path}
زبان: {language}
ایراد در خط {line_num}: {issue.get('message', '')}
نوع ایراد: {issue.get('type', 'general')}
شدت: {issue.get('severity', 'medium')}

کد اطراف ایراد:
```{language}
{context}
```

لطفاً:
1. توضیح بده چرا این یک ایراد است
2. پیشنهاد اصلاح بده
3. کد اصلاح شده را بنویس (فقط قسمت مربوطه)

پاسخ را به این فرمت JSON بده:
{{
    "explanation": "توضیح ایراد",
    "suggestion": "پیشنهاد اصلاح",
    "fix_code": "کد اصلاح شده"
}}
"""
            response = await ai_manager.generate_response(
                model_id=model_id,
                messages=[Message(role="user", content=prompt)],
                temperature=0.3
            )

            # پارس پاسخ
            try:
                import re
                json_match = re.search(r'\{[\s\S]*\}', response.content)
                if json_match:
                    fix_data = json.loads(json_match.group())
                    issue['suggestion'] = fix_data.get('suggestion', issue.get('suggestion'))
                    issue['fix_code'] = fix_data.get('fix_code')
                    issue['explanation'] = fix_data.get('explanation')
                    issue['ai_reviewed'] = True
                    issue['reviewed_by'] = model_id
                    updated_count += 1
            except:
                pass

        except Exception as e:
            logger.warning(f"Error generating suggestion for issue: {e}")

    # ذخیره ایرادات بروز شده
    try:
        all_issues = json.loads(project.issues_found) if project.issues_found else []
        # بروزرسانی ایرادات
        for updated_issue in issues:
            for i, stored_issue in enumerate(all_issues):
                if (stored_issue.get('file') == updated_issue.get('file') and
                    stored_issue.get('line') == updated_issue.get('line') and
                    stored_issue.get('message') == updated_issue.get('message')):
                    all_issues[i] = updated_issue
                    break

        project.issues_found = json.dumps(all_issues, ensure_ascii=False)
        db.commit()
    except Exception as e:
        logger.error(f"Error saving updated issues: {e}")

    return {
        "success": True,
        "updated_issues": updated_count,
        "total_issues": len(issues)
    }


# =====================================
# 🆕 دانلود فایل‌ها
# =====================================

class FileDownloadRequest(BaseModel):
    """درخواست دانلود فایل‌ها"""
    file_paths: List[str]
    include_suggestions: bool = True
    format: str = "zip"  # zip, tar


@router.get("/{project_id}/health/file/{file_path:path}/download")
async def download_single_file(
    project_id: str,
    file_path: str,
    include_suggestions: bool = True,
    db=Depends(get_db)
):
    """
    دانلود یک فایل با یا بدون کامنت‌های پیشنهادی
    """
    from fastapi.responses import Response

    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="پروژه یافت نشد")

    file_record = db.query(ProjectFile).filter(
        ProjectFile.project_id == project_id,
        ProjectFile.file_path == file_path
    ).first()

    if not file_record:
        raise HTTPException(status_code=404, detail="فایل یافت نشد")

    content = file_record.content or ""

    if include_suggestions:
        issues = []
        try:
            if project.issues_found:
                all_issues = json.loads(project.issues_found)
                issues = [i for i in all_issues if i.get("file") == file_path]
        except:
            pass

        if issues:
            content = _add_issue_comments_to_content(content, issues, file_path)

    filename = file_path.split('/')[-1]

    return Response(
        content=content,
        media_type="text/plain; charset=utf-8",
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{filename}"
        }
    )


@router.post("/{project_id}/health/files/download-batch")
async def download_batch_files(
    project_id: str,
    request: FileDownloadRequest,
    db=Depends(get_db)
):
    """
    دانلود چند فایل به صورت ZIP
    """
    import io
    import zipfile
    from fastapi.responses import StreamingResponse

    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="پروژه یافت نشد")

    # دریافت ایرادات
    all_issues = []
    try:
        if project.issues_found:
            all_issues = json.loads(project.issues_found)
    except:
        pass

    # ساخت ZIP
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for file_path in request.file_paths:
            file_record = db.query(ProjectFile).filter(
                ProjectFile.project_id == project_id,
                ProjectFile.file_path == file_path
            ).first()

            if file_record:
                content = file_record.content or ""

                if request.include_suggestions:
                    file_issues = [i for i in all_issues if i.get("file") == file_path]
                    if file_issues:
                        content = _add_issue_comments_to_content(content, file_issues, file_path)

                zip_file.writestr(file_path, content.encode('utf-8'))

    zip_buffer.seek(0)

    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={
            "Content-Disposition": f"attachment; filename={project.name}_health_files.zip"
        }
    )


@router.get("/{project_id}/health/files/download-all")
async def download_all_analyzed_files(
    project_id: str,
    include_suggestions: bool = True,
    only_with_issues: bool = False,
    db=Depends(get_db)
):
    """
    دانلود همه فایل‌های تحلیل شده
    """
    import io
    import zipfile
    from fastapi.responses import StreamingResponse

    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="پروژه یافت نشد")

    # دریافت ایرادات
    all_issues = []
    files_with_issues = set()
    try:
        if project.issues_found:
            all_issues = json.loads(project.issues_found)
            files_with_issues = set(i.get("file") for i in all_issues if i.get("file"))
    except:
        pass

    # دریافت همه فایل‌ها
    files = db.query(ProjectFile).filter(ProjectFile.project_id == project_id).all()

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for file_record in files:
            # اگر فقط فایل‌های دارای ایراد می‌خواهیم
            if only_with_issues and file_record.file_path not in files_with_issues:
                continue

            content = file_record.content or ""

            if include_suggestions:
                file_issues = [i for i in all_issues if i.get("file") == file_record.file_path]
                if file_issues:
                    content = _add_issue_comments_to_content(content, file_issues, file_record.file_path)

            zip_file.writestr(file_record.file_path, content.encode('utf-8'))

    zip_buffer.seek(0)

    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={
            "Content-Disposition": f"attachment; filename={project.name}_all_files.zip"
        }
    )


# =====================================
# 🆕 برچسب تاییدیه (Validation Stamp)
# =====================================

@router.post("/{project_id}/health/file/{file_path:path}/validate")
async def validate_file_issues(
    project_id: str,
    file_path: str,
    model_id: str = "claude",
    db=Depends(get_db)
):
    """
    اعتبارسنجی ایرادات یک فایل توسط گزارش مهندسی

    - بررسی صحت ایرادات
    - بررسی صحت پیشنهادات
    - افزودن برچسب تاییدیه
    """
    from ...services.ai_manager import get_ai_manager
    from ...services.ai_base import Message

    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="پروژه یافت نشد")

    file_record = db.query(ProjectFile).filter(
        ProjectFile.project_id == project_id,
        ProjectFile.file_path == file_path
    ).first()

    if not file_record:
        raise HTTPException(status_code=404, detail="فایل یافت نشد")

    content = file_record.content or ""

    # دریافت ایرادات این فایل
    all_issues = []
    file_issues = []
    try:
        if project.issues_found:
            all_issues = json.loads(project.issues_found)
            file_issues = [i for i in all_issues if i.get("file") == file_path]
    except:
        pass

    if not file_issues:
        return {"success": True, "message": "ایرادی برای اعتبارسنجی وجود ندارد"}

    ai_manager = get_ai_manager()
    language = _detect_language(file_path)

    # ساخت خلاصه ایرادات
    issues_summary = "\n".join([
        f"- خط {i.get('line', '?')}: [{i.get('severity', 'medium')}] {i.get('message', '')} | پیشنهاد: {i.get('suggestion', 'ندارد')}"
        for i in file_issues[:20]
    ])

    prompt = f"""
به عنوان مهندس ارشد نرم‌افزار، ایرادات شناسایی شده در فایل زیر را اعتبارسنجی کن.

فایل: {file_path}
زبان: {language}

محتوای فایل:
```{language}
{content[:5000]}
```

ایرادات شناسایی شده:
{issues_summary}

برای هر ایراد بررسی کن:
1. آیا ایراد واقعی و صحیح است؟
2. آیا پیشنهاد اصلاح درست است؟
3. آیا خط ایراد درست شناسایی شده؟

پاسخ را به این فرمت JSON بده:
{{
    "file_score": 85,
    "validation_passed": true,
    "issues_validated": [
        {{"line": 10, "is_valid": true, "notes": "ایراد صحیح است"}},
        {{"line": 25, "is_valid": false, "notes": "این ایراد نادرست است چون..."}}
    ],
    "overall_notes": "خلاصه نتیجه اعتبارسنجی",
    "stamp_text": "✅ تایید شده توسط {model_id} در {{date}}"
}}
"""

    try:
        response = await ai_manager.generate_response(
            model_id=model_id,
            messages=[Message(role="user", content=prompt)],
            temperature=0.2
        )

        import re
        json_match = re.search(r'\{[\s\S]*\}', response.content)
        if json_match:
            validation_result = json.loads(json_match.group())

            # بروزرسانی ایرادات با نتیجه اعتبارسنجی
            for validated in validation_result.get('issues_validated', []):
                for issue in file_issues:
                    if issue.get('line') == validated.get('line'):
                        issue['validated'] = validated.get('is_valid', True)
                        issue['validation_notes'] = validated.get('notes', '')
                        issue['validated_by'] = model_id
                        issue['validated_at'] = datetime.utcnow().isoformat()

            # بروزرسانی all_issues
            for updated_issue in file_issues:
                for i, stored_issue in enumerate(all_issues):
                    if (stored_issue.get('file') == updated_issue.get('file') and
                        stored_issue.get('line') == updated_issue.get('line')):
                        all_issues[i] = updated_issue
                        break

            project.issues_found = json.dumps(all_issues, ensure_ascii=False)

            # بروزرسانی نمره سلامت فایل با برچسب تایید
            validation_stamp_text = validation_result.get('stamp_text', '').replace('{date}', datetime.utcnow().strftime('%Y-%m-%d %H:%M'))
            if not validation_stamp_text:
                validation_stamp_text = f"✅ تایید شده توسط {model_id} در {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}"

            try:
                health_scores = json.loads(project.health_scores) if project.health_scores else {}
                if 'file_scores' not in health_scores:
                    health_scores['file_scores'] = {}

                health_scores['file_scores'][file_path] = {
                    'score': validation_result.get('file_score', 0),
                    'validated': True,
                    'validated_by': model_id,
                    'validated_at': datetime.utcnow().isoformat(),
                    'stamp': validation_stamp_text
                }
                project.health_scores = json.dumps(health_scores, ensure_ascii=False)
            except:
                pass

            # 🆕 افزودن کامنت تاییدیه داخل فایل
            # این کامنت در ابتدای فایل اضافه می‌شود بدون تغییر در کد اصلی
            comment_syntax = _get_comment_syntax(language)
            validation_comment = _create_validation_stamp_comment(
                file_path=file_path,
                model_id=model_id,
                score=validation_result.get('file_score', 0),
                validation_passed=validation_result.get('validation_passed', True),
                notes=validation_result.get('overall_notes', ''),
                language=language
            )

            # ذخیره محتوای به‌روز شده با کامنت تاییدیه
            # فقط اگر کامنت قبلاً اضافه نشده باشد
            if "🔬 ENGINEERING VALIDATION STAMP" not in content:
                validated_content = validation_comment + "\n\n" + content
            else:
                # به‌روزرسانی کامنت موجود
                import re
                stamp_pattern = r'(?s)(?:\/\*|#|//|<!--|--)\s*🔬 ENGINEERING VALIDATION STAMP.*?(?:\*\/|-->|\n\n|\n#|\n\/\/)'
                validated_content = re.sub(stamp_pattern, validation_comment + "\n", content)
                if validated_content == content:
                    validated_content = validation_comment + "\n\n" + content

            file_record.content = validated_content

            db.commit()

            return {
                "success": True,
                "file_path": file_path,
                "validation_result": validation_result,
                "issues_updated": len(file_issues),
                "stamp_added": True,
                "stamp_text": validation_stamp_text
            }

    except Exception as e:
        logger.error(f"Error validating file: {e}")
        raise HTTPException(status_code=500, detail=str(e))

    return {"success": False, "error": "اعتبارسنجی ناموفق"}


@router.post("/{project_id}/health/validate-all")
async def validate_all_files(
    project_id: str,
    model_id: str = "claude",
    db=Depends(get_db)
):
    """
    اعتبارسنجی همه فایل‌های دارای ایراد

    این endpoint به صورت streaming پیشرفت را گزارش می‌دهد
    """
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="پروژه یافت نشد")

    # دریافت فایل‌های دارای ایراد
    files_with_issues = set()
    try:
        if project.issues_found:
            all_issues = json.loads(project.issues_found)
            files_with_issues = set(i.get("file") for i in all_issues if i.get("file"))
    except:
        pass

    if not files_with_issues:
        return {"success": True, "message": "فایلی برای اعتبارسنجی وجود ندارد"}

    async def validation_generator():
        validated_count = 0
        total = len(files_with_issues)

        for file_path in files_with_issues:
            try:
                # اعتبارسنجی هر فایل
                result = await validate_file_issues(project_id, file_path, model_id, db)
                validated_count += 1

                yield f"data: {json.dumps({'file': file_path, 'progress': validated_count, 'total': total, 'status': 'validated'}, ensure_ascii=False)}\n\n"

            except Exception as e:
                yield f"data: {json.dumps({'file': file_path, 'progress': validated_count, 'total': total, 'status': 'error', 'error': str(e)}, ensure_ascii=False)}\n\n"

        yield f"data: {json.dumps({'status': 'completed', 'validated_count': validated_count, 'total': total}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        validation_generator(),
        media_type="text/event-stream"
    )


# =====================================
# Security Scan Endpoints
# =====================================

@router.get("/{project_id}/security/scan")
async def run_security_scan(
    project_id: str,
    db=Depends(get_db)
):
    """
    اجرای اسکن امنیتی کامل پروژه

    شامل:
    - تشخیص Secrets (API keys, passwords, tokens)
    - تشخیص لایسنس
    - بررسی فایل‌های حساس
    - بررسی آسیب‌پذیری وابستگی‌ها
    """
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="پروژه یافت نشد")

    # دریافت فایل‌های پروژه
    files = db.query(ProjectFile).filter(ProjectFile.project_id == project_id).all()

    # تبدیل به فرمت مورد نیاز اسکنر
    file_data = []
    for f in files:
        file_data.append({
            "path": f.file_path,
            "name": f.file_path.split("/")[-1] if "/" in f.file_path else f.file_path,
            "content": f.content or ""
        })

    # اجرای اسکن امنیتی
    scanner = get_security_scanner()
    scan_result = scanner.full_security_scan(file_data)

    # ذخیره نتایج در پروژه
    try:
        existing_metadata = json.loads(project.metadata or "{}")
    except:
        existing_metadata = {}

    existing_metadata["security_scan"] = {
        "last_scan": datetime.utcnow().isoformat(),
        "score": scan_result["security_score"],
        "summary": scan_result["summary"]
    }
    project.metadata = json.dumps(existing_metadata, ensure_ascii=False)

    # ذخیره نتایج کامل برای استفاده در انتقال به ایرادات
    project.security_scan_result = json.dumps(scan_result, ensure_ascii=False)

    db.commit()

    # ثبت در ژورنال
    total_findings = scan_result.get("summary", {}).get("total_issues", 0)
    await journal.log_scan(
        project_id=project_id,
        scan_type="security",
        findings_count=total_findings,
        details={
            "security_score": scan_result.get("security_score", 0),
            "files_scanned": len(file_data)
        },
        db=db
    )

    return {
        "success": True,
        "project_id": project_id,
        "scan_result": scan_result
    }


@router.get("/{project_id}/security/secrets")
async def scan_secrets_only(
    project_id: str,
    db=Depends(get_db)
):
    """
    اسکن فقط برای Secrets
    """
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="پروژه یافت نشد")

    files = db.query(ProjectFile).filter(ProjectFile.project_id == project_id).all()

    scanner = get_security_scanner()
    all_secrets = []

    for f in files:
        if f.content:
            secrets = scanner.scan_content_for_secrets(f.content, f.file_path)
            all_secrets.extend(secrets)

    return {
        "success": True,
        "project_id": project_id,
        "secrets_count": len(all_secrets),
        "findings": all_secrets
    }


@router.get("/{project_id}/security/license")
async def detect_project_license(
    project_id: str,
    db=Depends(get_db)
):
    """
    تشخیص لایسنس پروژه
    """
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="پروژه یافت نشد")

    files = db.query(ProjectFile).filter(ProjectFile.project_id == project_id).all()

    file_data = []
    for f in files:
        file_data.append({
            "path": f.file_path,
            "name": f.file_path.split("/")[-1] if "/" in f.file_path else f.file_path,
            "content": f.content or ""
        })

    scanner = get_security_scanner()
    license_info = scanner.detect_license(file_data)

    return {
        "success": True,
        "project_id": project_id,
        "license": license_info
    }


@router.get("/{project_id}/security/dependencies")
async def scan_dependencies(
    project_id: str,
    db=Depends(get_db)
):
    """
    بررسی آسیب‌پذیری وابستگی‌ها
    """
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="پروژه یافت نشد")

    files = db.query(ProjectFile).filter(ProjectFile.project_id == project_id).all()

    file_data = []
    for f in files:
        file_data.append({
            "path": f.file_path,
            "name": f.file_path.split("/")[-1] if "/" in f.file_path else f.file_path,
            "content": f.content or ""
        })

    scanner = get_security_scanner()
    dep_result = scanner.scan_dependencies(file_data)

    return {
        "success": True,
        "project_id": project_id,
        "dependencies": dep_result
    }


# =====================================
# Test Coverage Endpoints
# =====================================

@router.get("/{project_id}/test-coverage")
async def analyze_test_coverage(
    project_id: str,
    db=Depends(get_db)
):
    """
    تحلیل پوشش تست پروژه

    شامل:
    - شناسایی فایل‌های تست
    - تحلیل توابع و کلاس‌های تست شده
    - محاسبه درصد پوشش
    - توصیه‌ها برای بهبود
    """
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="پروژه یافت نشد")

    # دریافت فایل‌های پروژه
    files = db.query(ProjectFile).filter(ProjectFile.project_id == project_id).all()

    # تبدیل به فرمت مورد نیاز تحلیلگر
    file_data = []
    for f in files:
        file_data.append({
            "path": f.file_path,
            "name": f.file_path.split("/")[-1] if "/" in f.file_path else f.file_path,
            "content": f.content or ""
        })

    # اجرای تحلیل پوشش تست
    analyzer = get_test_coverage_analyzer()
    coverage_result = analyzer.analyze_project(file_data)

    # ذخیره نتایج در پروژه
    try:
        existing_metadata = json.loads(project.metadata or "{}")
    except:
        existing_metadata = {}

    existing_metadata["test_coverage"] = {
        "last_analysis": datetime.utcnow().isoformat(),
        "coverage_percent": coverage_result["summary"]["coverage_percent"],
        "health_score": coverage_result["health_score"],
        "total_tests": coverage_result["summary"]["total_tests"]
    }
    project.metadata = json.dumps(existing_metadata, ensure_ascii=False)

    # ذخیره نتایج کامل برای استفاده در انتقال به ایرادات
    project.test_coverage_result = json.dumps(coverage_result, ensure_ascii=False)

    db.commit()

    # ثبت در ژورنال
    untested_count = len(coverage_result.get("untested_files", []))
    await journal.log_scan(
        project_id=project_id,
        scan_type="coverage",
        findings_count=untested_count,
        details={
            "coverage_percent": coverage_result["summary"]["coverage_percent"],
            "total_tests": coverage_result["summary"]["total_tests"],
            "health_score": coverage_result["health_score"],
            "files_analyzed": len(file_data)
        },
        db=db
    )

    return {
        "success": True,
        "project_id": project_id,
        "coverage": coverage_result
    }


@router.get("/{project_id}/test-coverage/summary")
async def get_test_coverage_summary(
    project_id: str,
    db=Depends(get_db)
):
    """
    دریافت خلاصه پوشش تست (سریع‌تر)
    """
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="پروژه یافت نشد")

    # دریافت از metadata اگر موجود باشد
    try:
        metadata = json.loads(project.metadata or "{}")
        if "test_coverage" in metadata:
            return {
                "success": True,
                "project_id": project_id,
                "cached": True,
                "summary": metadata["test_coverage"]
            }
    except:
        pass

    # در غیر این صورت تحلیل جدید
    files = db.query(ProjectFile).filter(ProjectFile.project_id == project_id).all()

    analyzer = get_test_coverage_analyzer()
    file_data = [{"path": f.file_path, "content": f.content or ""} for f in files]
    coverage_result = analyzer.analyze_project(file_data)

    return {
        "success": True,
        "project_id": project_id,
        "cached": False,
        "summary": coverage_result["summary"]
    }


@router.get("/{project_id}/test-coverage/untested")
async def get_untested_files(
    project_id: str,
    db=Depends(get_db)
):
    """
    لیست فایل‌های بدون تست
    """
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="پروژه یافت نشد")

    files = db.query(ProjectFile).filter(ProjectFile.project_id == project_id).all()

    analyzer = get_test_coverage_analyzer()
    file_data = [{"path": f.file_path, "content": f.content or ""} for f in files]
    coverage_result = analyzer.analyze_project(file_data)

    return {
        "success": True,
        "project_id": project_id,
        "untested_files": coverage_result["untested_files"],
        "recommendations": coverage_result["recommendations"]
    }


# =====================================
# Download Endpoints (گزارشات قابل دانلود)
# =====================================

from fastapi.responses import Response
import csv
import io

@router.get("/{project_id}/security/download")
async def download_security_report(
    project_id: str,
    format: str = "json",
    db=Depends(get_db)
):
    """
    دانلود گزارش امنیتی پروژه

    فرمت‌ها: json, csv, txt
    """
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="پروژه یافت نشد")

    # دریافت فایل‌های پروژه
    files = db.query(ProjectFile).filter(ProjectFile.project_id == project_id).all()

    file_data = []
    for f in files:
        file_data.append({
            "path": f.file_path,
            "name": f.file_path.split("/")[-1] if "/" in f.file_path else f.file_path,
            "content": f.content or ""
        })

    # اجرای اسکن امنیتی
    scanner = get_security_scanner()
    scan_result = scanner.full_security_scan(file_data)

    # استخراج داده‌ها با ساختار صحیح
    secrets_data = scan_result.get("secrets", {})
    secrets_list = secrets_data.get("findings", []) if isinstance(secrets_data, dict) else []

    sensitive_data = scan_result.get("sensitive_files", {})
    sensitive_list = sensitive_data.get("findings", []) if isinstance(sensitive_data, dict) else []

    deps_data = scan_result.get("dependencies", {})
    vulns_list = deps_data.get("vulnerabilities", []) if isinstance(deps_data, dict) else []

    license_data = scan_result.get("license", {})

    # تولید گزارش بر اساس فرمت
    if format == "json":
        report = {
            "report_type": "security_scan",
            "project_name": project.name,
            "project_id": project_id,
            "generated_at": datetime.utcnow().isoformat(),
            "summary": scan_result.get("summary", {}),
            "security_score": scan_result.get("security_score", 0),
            "findings": {
                "secrets": secrets_list,
                "secrets_count": len(secrets_list),
                "vulnerabilities": vulns_list,
                "vulnerabilities_count": len(vulns_list),
                "sensitive_files": sensitive_list,
                "sensitive_files_count": len(sensitive_list),
                "license": license_data
            },
            "recommendations": [scan_result.get("summary", {}).get("recommendation", "")]
        }
        content = json.dumps(report, ensure_ascii=False, indent=2)
        media_type = "application/json"
        filename = f"security-report-{project.name}.json"

    elif format == "csv":
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["نوع", "شدت", "فایل", "خط", "توضیحات", "راه‌حل"])

        # Secrets
        for s in secrets_list:
            writer.writerow([
                "کلید محرمانه",
                s.get("severity", "بحرانی"),
                s.get("file", ""),
                s.get("line", ""),
                s.get("type", s.get("message", "")),
                "حذف از کد و استفاده از متغیرهای محیطی"
            ])

        # Vulnerabilities - کلیدهای صحیح: package, cve, current_version, vulnerable_versions, message, recommendation
        for v in vulns_list:
            writer.writerow([
                "آسیب‌پذیری",
                v.get("severity", "متوسط"),
                v.get("package", "نامشخص"),  # پکیج به جای فایل
                f"{v.get('current_version', '')} → {v.get('vulnerable_versions', '')}",  # نسخه‌ها
                f"{v.get('message', '')} (CVE: {v.get('cve', 'N/A')})",  # توضیحات با CVE
                v.get("recommendation", "به‌روزرسانی پکیج")
            ])

        # Sensitive files
        for sf in sensitive_list:
            writer.writerow([
                "فایل حساس",
                "بالا",
                sf.get("file", sf.get("path", "")),
                "",
                sf.get("reason", sf.get("type", "")),
                "اضافه به .gitignore"
            ])

        content = output.getvalue()
        media_type = "text/csv; charset=utf-8"
        filename = f"security-report-{project.name}.csv"

    else:  # txt
        lines = [
            "=" * 60,
            f"گزارش امنیتی پروژه: {project.name}",
            f"تاریخ: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}",
            f"نمره امنیتی: {scan_result.get('security_score', 0)}/100",
            "=" * 60,
            "",
            "📊 خلاصه:",
            f"  - کلیدهای محرمانه یافت شده: {len(secrets_list)}",
            f"  - آسیب‌پذیری‌ها: {len(vulns_list)}",
            f"  - فایل‌های حساس: {len(sensitive_list)}",
            "",
            "-" * 60,
            "🔐 کلیدهای محرمانه:",
            "-" * 60,
        ]

        for s in secrets_list:
            lines.append(f"  📍 فایل: {s.get('file', 'نامشخص')}")
            lines.append(f"     نوع: {s.get('type', s.get('message', 'نامشخص'))}")
            lines.append(f"     خط: {s.get('line', 'نامشخص')}")
            lines.append(f"     شدت: {s.get('severity', 'بحرانی')}")
            lines.append("")

        lines.extend([
            "-" * 60,
            "⚠️ آسیب‌پذیری‌ها:",
            "-" * 60,
        ])

        for v in vulns_list:
            # کلیدهای صحیح: package, cve, current_version, vulnerable_versions, message, recommendation
            lines.append(f"  📍 پکیج: {v.get('package', 'نامشخص')}")
            lines.append(f"     نسخه فعلی: {v.get('current_version', 'نامشخص')}")
            lines.append(f"     نسخه‌های آسیب‌پذیر: {v.get('vulnerable_versions', 'نامشخص')}")
            lines.append(f"     CVE: {v.get('cve', 'نامشخص')}")
            lines.append(f"     شدت: {v.get('severity', 'بالا')}")
            lines.append(f"     توضیح: {v.get('message', '')}")
            lines.append(f"     راه‌حل: {v.get('recommendation', '')}")
            lines.append("")

        lines.extend([
            "-" * 60,
            "📁 فایل‌های حساس:",
            "-" * 60,
        ])

        for sf in sensitive_list:
            lines.append(f"  📍 {sf.get('file', sf.get('path', 'نامشخص'))}")
            lines.append(f"     دلیل: {sf.get('reason', sf.get('type', ''))}")
            lines.append("")

        lines.extend([
            "-" * 60,
            "📄 وضعیت لایسنس:",
            "-" * 60,
        ])
        if license_data.get("has_license"):
            for lic in license_data.get("licenses", []):
                lines.append(f"  ✅ {lic.get('license', 'نامشخص')} - {lic.get('file', '')}")
        else:
            lines.append("  ❌ پروژه فاقد لایسنس است")

        lines.extend([
            "",
            "-" * 60,
            "💡 توصیه کلی:",
            "-" * 60,
        ])
        recommendation = scan_result.get("summary", {}).get("recommendation", "")
        if recommendation:
            lines.append(f"  {recommendation}")

        content = "\n".join(lines)
        media_type = "text/plain; charset=utf-8"
        filename = f"security-report-{project.name}.txt"

    return Response(
        content=content.encode("utf-8"),
        media_type=media_type,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        }
    )


@router.get("/{project_id}/test-coverage/download")
async def download_test_coverage_report(
    project_id: str,
    format: str = "json",
    db=Depends(get_db)
):
    """
    دانلود گزارش پوشش تست پروژه

    فرمت‌ها: json, csv, txt
    """
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="پروژه یافت نشد")

    # دریافت فایل‌های پروژه
    files = db.query(ProjectFile).filter(ProjectFile.project_id == project_id).all()

    file_data = []
    for f in files:
        file_data.append({
            "path": f.file_path,
            "name": f.file_path.split("/")[-1] if "/" in f.file_path else f.file_path,
            "content": f.content or ""
        })

    # اجرای تحلیل پوشش تست
    analyzer = get_test_coverage_analyzer()
    coverage_result = analyzer.analyze_project(file_data)

    # تولید گزارش بر اساس فرمت
    if format == "json":
        report = {
            "report_type": "test_coverage",
            "project_name": project.name,
            "project_id": project_id,
            "generated_at": datetime.utcnow().isoformat(),
            "summary": coverage_result.get("summary", {}),
            "health_score": coverage_result.get("health_score", 0),
            "coverage_percent": coverage_result.get("summary", {}).get("coverage_percent", 0),
            "test_files": coverage_result.get("test_files", []),
            "untested_files": coverage_result.get("untested_files", []),
            "untested_functions": coverage_result.get("untested_functions", []),
            "recommendations": coverage_result.get("recommendations", [])
        }
        content = json.dumps(report, ensure_ascii=False, indent=2)
        media_type = "application/json"
        filename = f"test-coverage-{project.name}.json"

    elif format == "csv":
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["نوع", "مسیر فایل", "تعداد موجودیت", "نمونه توابع", "وضعیت"])

        # فایل‌های تست
        for tf in coverage_result.get("test_files", []):
            tests = tf.get('tests', [])
            test_names = ', '.join(t.get('name', '') for t in tests[:3])
            writer.writerow([
                "فایل تست",
                tf.get("path", ""),
                tf.get("test_count", 0),
                test_names,
                "موجود"
            ])

        # فایل‌های بدون تست
        for uf in coverage_result.get("untested_files", []):
            entities = uf.get("entities", [])
            entity_names = ', '.join(entities[:3]) if entities else ""
            writer.writerow([
                "فایل بدون تست",
                uf.get("path", ""),
                uf.get("entity_count", 0),
                entity_names,
                "نیاز به تست"
            ])

        content = output.getvalue()
        media_type = "text/csv; charset=utf-8"
        filename = f"test-coverage-{project.name}.csv"

    else:  # txt
        summary = coverage_result.get("summary", {})
        lines = [
            "=" * 60,
            f"گزارش پوشش تست پروژه: {project.name}",
            f"تاریخ: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}",
            f"نمره سلامت: {coverage_result.get('health_score', 0)}/100",
            "=" * 60,
            "",
            "📊 خلاصه:",
            f"  - درصد پوشش تست: {summary.get('coverage_percent', 0)}%",
            f"  - تعداد فایل‌های تست: {summary.get('total_test_files', 0)}",
            f"  - تعداد تست‌ها: {summary.get('total_tests', 0)}",
            f"  - فایل‌های بدون تست: {summary.get('untested_file_count', 0)}",
            "",
            "-" * 60,
            "🧪 فایل‌های تست موجود:",
            "-" * 60,
        ]

        for tf in coverage_result.get("test_files", []):
            # کلید path است نه file
            lines.append(f"  ✅ {tf.get('path', 'نامشخص')}")
            lines.append(f"     تعداد تست: {tf.get('test_count', 0)}")
            # نمایش نام تست‌ها
            tests = tf.get('tests', [])
            if tests:
                for t in tests[:3]:  # فقط 3 تست اول
                    lines.append(f"       - {t.get('name', '')}")

        lines.extend([
            "",
            "-" * 60,
            "❌ فایل‌های بدون تست:",
            "-" * 60,
        ])

        for uf in coverage_result.get("untested_files", []):
            # کلید path است نه file
            lines.append(f"  📍 {uf.get('path', 'نامشخص')}")
            entity_count = uf.get("entity_count", 0)
            if entity_count:
                lines.append(f"     تعداد موجودیت: {entity_count}")
            entities = uf.get("entities", [])
            if entities:
                lines.append(f"     نمونه توابع: {', '.join(entities[:3])}")
            lines.append("")

        lines.extend([
            "-" * 60,
            "⚠️ توابع بدون تست:",
            "-" * 60,
        ])

        for func in coverage_result.get("untested_functions", []):
            lines.append(f"  📍 {func.get('file', '')}:{func.get('name', '')}")

        lines.extend([
            "",
            "-" * 60,
            "💡 توصیه‌ها:",
            "-" * 60,
        ])

        for i, rec in enumerate(coverage_result.get("recommendations", []), 1):
            if isinstance(rec, dict):
                # کلید message است نه title
                lines.append(f"  {i}. {rec.get('message', rec.get('title', ''))}")
                if rec.get("recommendation"):
                    lines.append(f"     توصیه: {rec.get('recommendation')}")
            else:
                lines.append(f"  {i}. {rec}")

        content = "\n".join(lines)
        media_type = "text/plain; charset=utf-8"
        filename = f"test-coverage-{project.name}.txt"

    return Response(
        content=content.encode("utf-8"),
        media_type=media_type,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        }
    )


# =====================================
# Transfer to Issues Endpoints (انتقال به ایرادات)
# =====================================

from ...services.health_to_issues_service import get_health_to_issues_service
from ...models.project import ProjectIssue

@router.post("/{project_id}/security/transfer-to-issues")
async def transfer_security_to_issues(
    project_id: str,
    db=Depends(get_db)
):
    """
    انتقال یافته‌های امنیتی به تب ایرادات

    - تحلیل و بسط توسط AI
    - ادغام با ایرادات مشابه
    - اولویت‌بندی خودکار
    """
    slog.api_request("POST", f"/projects/{project_id}/security/transfer-to-issues")

    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="پروژه یافت نشد")

    # ابتدا سعی می‌کنیم از نتایج ذخیره شده استفاده کنیم (همان چیزی که کاربر در UI می‌بیند)
    scan_result = None
    if project.security_scan_result:
        try:
            scan_result = json.loads(project.security_scan_result) if isinstance(project.security_scan_result, str) else project.security_scan_result
            slog.info(f"[DEBUG-TRANSFER] Using stored scan result from database")
        except:
            scan_result = None

    # اگر نتیجه ذخیره شده نبود، اسکن جدید اجرا می‌کنیم
    if not scan_result:
        slog.info(f"[DEBUG-TRANSFER] No stored result, running fresh scan")
        # دریافت فایل‌های پروژه
        files = db.query(ProjectFile).filter(ProjectFile.project_id == project_id).all()
        slog.info(f"[DEBUG-TRANSFER] Found {len(files)} files for project {project_id}")

        file_data = []
        files_with_content = 0
        for f in files:
            has_content = bool(f.content and len(f.content) > 0)
            if has_content:
                files_with_content += 1
            file_data.append({
                "path": f.file_path,
                "name": f.file_path.split("/")[-1] if "/" in f.file_path else f.file_path,
                "content": f.content or ""
            })

        slog.info(f"[DEBUG-TRANSFER] Files with content: {files_with_content}/{len(files)}")

        # اجرای اسکن امنیتی
        scanner = get_security_scanner()
        scan_result = scanner.full_security_scan(file_data)

    # Debug scan result
    slog.info(f"[DEBUG-TRANSFER] Scan result keys: {list(scan_result.keys()) if scan_result else 'None'}")
    secrets_count = len(scan_result.get('secrets', {}).get('findings', [])) if isinstance(scan_result.get('secrets'), dict) else 0
    vulns_count = len(scan_result.get('dependencies', {}).get('vulnerabilities', [])) if isinstance(scan_result.get('dependencies'), dict) else 0
    sensitive_count = len(scan_result.get('sensitive_files', {}).get('findings', [])) if isinstance(scan_result.get('sensitive_files'), dict) else 0
    slog.info(f"[DEBUG-TRANSFER] Scan findings: secrets={secrets_count}, vulns={vulns_count}, sensitive={sensitive_count}")

    # انتقال به ایرادات
    service = get_health_to_issues_service()
    result = await service.transfer_security_findings(
        project_id=project_id,
        scan_result=scan_result,
        db=db
    )

    return result


@router.post("/{project_id}/test-coverage/transfer-to-issues")
async def transfer_test_coverage_to_issues(
    project_id: str,
    db=Depends(get_db)
):
    """
    انتقال یافته‌های پوشش تست به تب ایرادات

    - تحلیل و بسط توسط AI
    - ادغام با ایرادات مشابه
    - اولویت‌بندی خودکار
    """
    slog.api_request("POST", f"/projects/{project_id}/test-coverage/transfer-to-issues")

    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="پروژه یافت نشد")

    # ابتدا سعی می‌کنیم از نتایج ذخیره شده استفاده کنیم (همان چیزی که کاربر در UI می‌بیند)
    coverage_result = None
    if project.test_coverage_result:
        try:
            coverage_result = json.loads(project.test_coverage_result) if isinstance(project.test_coverage_result, str) else project.test_coverage_result
            slog.info(f"[DEBUG-TRANSFER-COV] Using stored coverage result from database")
        except:
            coverage_result = None

    # اگر نتیجه ذخیره شده نبود، تحلیل جدید اجرا می‌کنیم
    if not coverage_result:
        slog.info(f"[DEBUG-TRANSFER-COV] No stored result, running fresh analysis")
        # دریافت فایل‌های پروژه
        files = db.query(ProjectFile).filter(ProjectFile.project_id == project_id).all()
        slog.info(f"[DEBUG-TRANSFER-COV] Found {len(files)} files for project {project_id}")

        file_data = []
        files_with_content = 0
        for f in files:
            has_content = bool(f.content and len(f.content) > 0)
            if has_content:
                files_with_content += 1
            file_data.append({
                "path": f.file_path,
                "name": f.file_path.split("/")[-1] if "/" in f.file_path else f.file_path,
                "content": f.content or ""
            })

        slog.info(f"[DEBUG-TRANSFER-COV] Files with content: {files_with_content}/{len(files)}")

        # اجرای تحلیل پوشش تست
        analyzer = get_test_coverage_analyzer()
        coverage_result = analyzer.analyze_project(file_data)

    # Debug coverage result
    slog.info(f"[DEBUG-TRANSFER-COV] Coverage result keys: {list(coverage_result.keys()) if coverage_result else 'None'}")
    untested_count = len(coverage_result.get('untested_files', []))
    recommendations_count = len(coverage_result.get('recommendations', []))
    coverage_percent = coverage_result.get('summary', {}).get('coverage_percent', 0)
    slog.info(f"[DEBUG-TRANSFER-COV] Coverage findings: untested={untested_count}, recommendations={recommendations_count}, coverage%={coverage_percent}")

    # انتقال به ایرادات
    service = get_health_to_issues_service()
    result = await service.transfer_test_coverage_findings(
        project_id=project_id,
        coverage_result=coverage_result,
        db=db
    )

    return result


# =====================================
# Issues Management Endpoints (مدیریت ایرادات)
# =====================================

@router.get("/{project_id}/issues")
async def get_project_issues(
    project_id: str,
    status: Optional[str] = None,
    source: Optional[str] = None,
    priority: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    db=Depends(get_db)
):
    """
    دریافت لیست ایرادات پروژه

    فیلترها:
    - status: open, in_progress, resolved, ignored
    - source: security_scan, test_coverage, render_logs, manual
    - priority: critical, high, medium, low
    """
    query = db.query(ProjectIssue).filter(ProjectIssue.project_id == project_id)

    if status:
        query = query.filter(ProjectIssue.status == status)
    if source:
        query = query.filter(ProjectIssue.source == source)
    if priority:
        priority_map = {"critical": 1, "high": 2, "medium": 3, "low": 4}
        if priority in priority_map:
            query = query.filter(ProjectIssue.priority == priority_map[priority])

    total = query.count()
    issues = query.order_by(ProjectIssue.priority, ProjectIssue.created_at.desc())\
        .offset(offset).limit(limit).all()

    return {
        "success": True,
        "project_id": project_id,
        "issues": [issue.to_dict() for issue in issues],
        "total": total,
        "has_more": offset + limit < total
    }


@router.get("/{project_id}/issues/summary")
async def get_issues_summary(
    project_id: str,
    db=Depends(get_db)
):
    """
    خلاصه ایرادات پروژه
    """
    from sqlalchemy import func

    # شمارش بر اساس وضعیت
    status_counts = db.query(
        ProjectIssue.status,
        func.count(ProjectIssue.id)
    ).filter(
        ProjectIssue.project_id == project_id
    ).group_by(ProjectIssue.status).all()

    # شمارش بر اساس منبع
    source_counts = db.query(
        ProjectIssue.source,
        func.count(ProjectIssue.id)
    ).filter(
        ProjectIssue.project_id == project_id
    ).group_by(ProjectIssue.source).all()

    # شمارش بر اساس اولویت
    priority_counts = db.query(
        ProjectIssue.priority,
        func.count(ProjectIssue.id)
    ).filter(
        ProjectIssue.project_id == project_id
    ).group_by(ProjectIssue.priority).all()

    priority_map = {1: "critical", 2: "high", 3: "medium", 4: "low"}

    return {
        "success": True,
        "project_id": project_id,
        "by_status": {status: count for status, count in status_counts},
        "by_source": {source: count for source, count in source_counts},
        "by_priority": {priority_map.get(p, "unknown"): count for p, count in priority_counts},
        "total": sum(count for _, count in status_counts)
    }


@router.patch("/{project_id}/issues/{issue_id}")
async def update_issue(
    project_id: str,
    issue_id: int,
    status: Optional[str] = None,
    priority: Optional[str] = None,
    db=Depends(get_db)
):
    """
    بروزرسانی وضعیت یا اولویت یک ایراد
    """
    issue = db.query(ProjectIssue).filter(
        ProjectIssue.id == issue_id,
        ProjectIssue.project_id == project_id
    ).first()

    if not issue:
        raise HTTPException(status_code=404, detail="ایراد یافت نشد")

    if status:
        issue.status = status
        if status == "resolved":
            issue.resolved_at = datetime.utcnow()

    if priority:
        priority_map = {"critical": 1, "high": 2, "medium": 3, "low": 4}
        if priority in priority_map:
            issue.priority = priority_map[priority]

    issue.updated_at = datetime.utcnow()
    db.commit()

    return {
        "success": True,
        "issue": issue.to_dict()
    }


@router.delete("/{project_id}/issues/{issue_id}")
async def delete_issue(
    project_id: str,
    issue_id: int,
    db=Depends(get_db)
):
    """
    حذف یک ایراد
    """
    issue = db.query(ProjectIssue).filter(
        ProjectIssue.id == issue_id,
        ProjectIssue.project_id == project_id
    ).first()

    if not issue:
        raise HTTPException(status_code=404, detail="ایراد یافت نشد")

    db.delete(issue)
    db.commit()

    return {
        "success": True,
        "message": "ایراد حذف شد"
    }
