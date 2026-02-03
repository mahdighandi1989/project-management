"""
API routes for Project Memory Management
مسیرهای API برای مدیریت حافظه و دستورات پروژه
"""

import json
import uuid
import time
import asyncio
import difflib
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from fastapi.responses import Response
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session

from ...core.database import get_db
from ...models.project import Project
# ActivityLog و log_detailed_operation داخل توابع import می‌شوند تا از circular import جلوگیری شود

router = APIRouter(prefix="/projects", tags=["Project Memory"])


# =====================================
# مدل‌های درخواست
# =====================================

class TriggerSettings(BaseModel):
    """تنظیمات تریگر برای اجرای خودکار"""
    enabled: bool = False
    interval_minutes: int = 60  # هر چند دقیقه اجرا شود
    interval_type: str = "minutes"  # minutes, hours, days
    last_run: Optional[str] = None  # آخرین زمان اجرا
    next_run: Optional[str] = None  # زمان اجرای بعدی


class MemoryInstructionsRequest(BaseModel):
    """درخواست بروزرسانی باکس حافظه"""
    content: str
    target_models: List[str] = ["all"]  # ["all"] یا ["openai", "claude", "gemini", ...]


class DynamicFieldRequest(BaseModel):
    """درخواست افزودن/ویرایش فیلد پویا"""
    name: str
    value: str
    target_models: List[str] = ["all"]
    trigger: Optional[TriggerSettings] = None
    # تنظیمات جدید برای اعمال روی GitHub
    action_type: str = "display"  # display, github_commit, github_multi_commit
    target_path: Optional[str] = None  # مسیر فایل در ریپو (مثلاً: backend/models/customer.py)
    archive_after_run: bool = True  # آیا بعد از اجرای موفق بایگانی شود؟ (پیش‌فرض: بله)
    deploy_after_commit: bool = False  # آیا بعد از commit در Render دیپلوی شود؟
    # 🆕 فیلدهای جدید
    field_type: str = "temporary"  # "permanent" (دائمی/تکرارشونده) یا "temporary" (موقت/یکبار مصرف)
    priority: int = 5  # اولویت از 1 (بالاترین) تا 10 (پایین‌ترین)
    attachments: Optional[List[str]] = None  # لیست فایل‌های پیوست (آدرس فایل یا base64)
    # 🆕 وابستگی فیلدها
    depends_on: Optional[List[str]] = None  # فیلدهایی که باید قبل از این اجرا شوند
    blocked_by: Optional[List[str]] = None  # فیلدهایی که اجرای این را بلوکه می‌کنند


class UpdateDynamicFieldRequest(BaseModel):
    """درخواست بروزرسانی فیلد پویا"""
    id: str
    name: Optional[str] = None
    value: Optional[str] = None
    target_models: Optional[List[str]] = None
    trigger: Optional[TriggerSettings] = None
    action_type: Optional[str] = None
    target_path: Optional[str] = None
    archive_after_run: Optional[bool] = None
    deploy_after_commit: Optional[bool] = None  # آیا بعد از commit در Render دیپلوی شود؟
    archived: Optional[bool] = None  # برای بایگانی/خروج از بایگانی
    # 🆕 فیلدهای جدید
    field_type: Optional[str] = None  # "permanent" یا "temporary"
    priority: Optional[int] = None  # اولویت از 1 تا 10
    attachments: Optional[List[str]] = None  # لیست پیوست‌ها
    # 🆕 وابستگی فیلدها
    depends_on: Optional[List[str]] = None  # فیلدهایی که باید قبل از این اجرا شوند
    blocked_by: Optional[List[str]] = None  # فیلدهایی که اجرای این را بلوکه می‌کنند


class BatchExecuteRequest(BaseModel):
    """درخواست اجرای گروهی فیلدها"""
    field_ids: List[str]  # لیست آی‌دی فیلدها یا "all" یا "permanent" یا "temporary"
    execute_type: str = "selected"  # "selected", "all", "permanent", "temporary"
    auto_prioritize: bool = True  # مرتب‌سازی خودکار براساس اولویت
    run_in_background: bool = False  # اجرا در پس‌زمینه
    force_archive: bool = True  # بایگانی اجباری همه فیلدهای اجراشده (پیش‌فرض: بله)


class BatchDeleteRequest(BaseModel):
    """درخواست حذف گروهی فیلدها"""
    field_ids: List[str]  # لیست آی‌دی فیلدها


class BatchControlRequest(BaseModel):
    """درخواست کنترل اجرای گروهی"""
    action: str  # "pause", "resume", "stop"


class FieldAttachmentRequest(BaseModel):
    """درخواست افزودن پیوست به فیلد"""
    field_id: str
    file_path: Optional[str] = None  # آدرس فایل در سرور
    file_content: Optional[str] = None  # محتوای فایل (base64)
    file_name: str  # نام فایل
    file_type: str  # نوع فایل (image, document, code)


# ثابت‌های نوع اکشن
ACTION_TYPES = [
    {"id": "display", "name": "فقط نمایش", "icon": "👁️", "description": "نتیجه فقط در ژورنال نمایش داده می‌شود"},
    {"id": "github_commit", "name": "Commit به GitHub", "icon": "📤", "description": "نتیجه به عنوان یک فایل در ریپو commit می‌شود"},
    {"id": "github_multi_commit", "name": "Multi Commit", "icon": "📦", "description": "چند فایل از پاسخ استخراج و commit می‌شوند"},
]

# 🆕 ثابت‌های نوع فیلد
FIELD_TYPES = [
    {"id": "permanent", "name": "دائمی/تکرارشونده", "icon": "🔄", "description": "فیلدهایی که باید همیشه فعال باشند و به صورت دوره‌ای اجرا شوند"},
    {"id": "temporary", "name": "موقت/یکبار مصرف", "icon": "⏱️", "description": "فیلدهایی که برای یک کار خاص ایجاد شده و بعد از اجرا بایگانی می‌شوند"},
]

# 🆕 سطوح اولویت
PRIORITY_LEVELS = [
    {"value": 1, "name": "بحرانی", "icon": "🔴", "description": "فوری - باید ابتدا اجرا شود"},
    {"value": 2, "name": "بسیار بالا", "icon": "🟠"},
    {"value": 3, "name": "بالا", "icon": "🟡"},
    {"value": 5, "name": "عادی", "icon": "🟢", "description": "پیش‌فرض"},
    {"value": 7, "name": "پایین", "icon": "🔵"},
    {"value": 10, "name": "خیلی پایین", "icon": "⚪", "description": "در صورت فرصت"},
]


# =====================================
# توابع کمکی برای وابستگی فیلدها
# =====================================

def check_field_dependencies(field: dict, all_fields: list) -> dict:
    """
    بررسی وابستگی‌های یک فیلد
    برمی‌گرداند: {"can_execute": bool, "blocking_fields": list, "pending_dependencies": list}
    """
    depends_on = field.get("depends_on", []) or []
    blocked_by = field.get("blocked_by", []) or []

    pending_dependencies = []
    blocking_fields = []

    # ساخت دیکشنری برای دسترسی سریع به فیلدها
    field_map = {f.get("id"): f for f in all_fields}

    # بررسی depends_on: فیلدهایی که باید اجرا شده باشند
    for dep_id in depends_on:
        dep_field = field_map.get(dep_id)
        if dep_field:
            # فیلد باید بایگانی شده باشد (یعنی اجرا شده)
            if not dep_field.get("archived"):
                pending_dependencies.append({
                    "id": dep_id,
                    "name": dep_field.get("name", "فیلد ناشناخته"),
                    "status": "pending"
                })

    # بررسی blocked_by: فیلدهایی که نباید فعال باشند
    for block_id in blocked_by:
        block_field = field_map.get(block_id)
        if block_field:
            # اگر فیلد بلوکه‌کننده هنوز فعال است (بایگانی نشده)
            if not block_field.get("archived"):
                blocking_fields.append({
                    "id": block_id,
                    "name": block_field.get("name", "فیلد ناشناخته"),
                    "status": "blocking"
                })

    can_execute = len(pending_dependencies) == 0 and len(blocking_fields) == 0

    return {
        "can_execute": can_execute,
        "pending_dependencies": pending_dependencies,
        "blocking_fields": blocking_fields,
        "message": None if can_execute else _get_dependency_message(pending_dependencies, blocking_fields)
    }


def _get_dependency_message(pending: list, blocking: list) -> str:
    """تولید پیام خطای وابستگی"""
    messages = []

    if pending:
        names = ", ".join([p["name"] for p in pending])
        messages.append(f"ابتدا این فیلدها باید اجرا شوند: {names}")

    if blocking:
        names = ", ".join([b["name"] for b in blocking])
        messages.append(f"این فیلدها مانع اجرا هستند: {names}")

    return " | ".join(messages)


def sort_fields_by_dependencies(fields: list) -> list:
    """
    مرتب‌سازی فیلدها براساس وابستگی‌ها (توپولوژیکی)
    فیلدهایی که وابستگی ندارند اول می‌آیند
    """
    sorted_fields = []
    remaining = fields.copy()
    executed_ids = set()

    # حداکثر تعداد تکرار برای جلوگیری از حلقه بی‌نهایت
    max_iterations = len(fields) * 2
    iteration = 0

    while remaining and iteration < max_iterations:
        iteration += 1
        made_progress = False

        for field in remaining[:]:
            depends_on = field.get("depends_on", []) or []
            blocked_by = field.get("blocked_by", []) or []

            # بررسی آیا همه وابستگی‌ها برآورده شده‌اند
            deps_satisfied = all(dep_id in executed_ids for dep_id in depends_on)
            not_blocked = all(block_id in executed_ids or block_id not in [f.get("id") for f in remaining] for block_id in blocked_by)

            if deps_satisfied and not_blocked:
                sorted_fields.append(field)
                executed_ids.add(field.get("id"))
                remaining.remove(field)
                made_progress = True

        # اگر پیشرفتی نداشتیم، ممکن است وابستگی دایره‌ای وجود داشته باشد
        if not made_progress:
            # باقی‌مانده‌ها را به انتها اضافه کن
            sorted_fields.extend(remaining)
            break

    return sorted_fields


# =====================================
# لیست مدل‌های موجود
# =====================================

AVAILABLE_MODELS = [
    {"id": "all", "name": "همه مدل‌ها", "icon": "🌐"},
    {"id": "openai", "name": "OpenAI (GPT)", "icon": "🟢"},
    {"id": "claude", "name": "Claude (Anthropic)", "icon": "🟣"},
    {"id": "gemini", "name": "Gemini (Google)", "icon": "🔵"},
    {"id": "deepseek", "name": "DeepSeek", "icon": "🔷"},
    {"id": "openrouter", "name": "OpenRouter", "icon": "🔶"},
    {"id": "groq", "name": "Groq", "icon": "⚡"},
    {"id": "perplexity", "name": "Perplexity AI", "icon": "🔍"},  # 🆕
]

# گزینه‌های بازه زمانی برای تریگرها
TRIGGER_INTERVALS = [
    {"value": 5, "type": "minutes", "label": "هر ۵ دقیقه"},
    {"value": 15, "type": "minutes", "label": "هر ۱۵ دقیقه"},
    {"value": 30, "type": "minutes", "label": "هر ۳۰ دقیقه"},
    {"value": 1, "type": "hours", "label": "هر ۱ ساعت"},
    {"value": 2, "type": "hours", "label": "هر ۲ ساعت"},
    {"value": 6, "type": "hours", "label": "هر ۶ ساعت"},
    {"value": 12, "type": "hours", "label": "هر ۱۲ ساعت"},
    {"value": 1, "type": "days", "label": "روزانه"},
    {"value": 7, "type": "days", "label": "هفتگی"},
]


# =====================================
# توابع کمکی GitHub
# =====================================

import re
import os
import base64
import aiohttp

async def extract_code_blocks(content: str) -> List[dict]:
    """
    استخراج بلوک‌های کد از پاسخ AI
    پشتیبانی از فرمت‌های:
    - ```python\n# path/to/file.py\n...```
    - ```python:path/to/file.py\n...```
    - # filename: path/to/file.py
    """
    blocks = []

    # الگوی اول: ```lang:path یا ```lang\n# path
    pattern = r'```(\w+)?(?::([^\n]+))?\n(.*?)```'
    matches = re.findall(pattern, content, re.DOTALL)

    for lang, path, code in matches:
        if not path:
            # بررسی خط اول برای مسیر
            lines = code.strip().split('\n')
            if lines and lines[0].startswith('#'):
                first_line = lines[0]
                # الگوهای مختلف برای مسیر فایل
                path_patterns = [
                    r'#\s*(?:path|file|filename):\s*(.+)',
                    r'#\s*([a-zA-Z0-9_/\\.-]+\.[a-zA-Z]+)',
                ]
                for pp in path_patterns:
                    match = re.match(pp, first_line, re.IGNORECASE)
                    if match:
                        path = match.group(1).strip()
                        code = '\n'.join(lines[1:])
                        break

        if path and code.strip():
            blocks.append({
                "path": path.strip(),
                "language": lang or "text",
                "content": code.strip()
            })

    return blocks


async def commit_to_github(
    owner: str,
    repo: str,
    token: str,
    file_path: str,
    content: str,
    message: str,
    branch: str = "main"
) -> dict:
    """
    Commit یک فایل به ریپو GitHub
    """
    api_url = f"https://api.github.com/repos/{owner}/{repo}/contents/{file_path}"

    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
        "X-GitHub-Api-Version": "2022-11-28"
    }

    # کدگذاری محتوا به base64
    content_bytes = content.encode('utf-8')
    content_b64 = base64.b64encode(content_bytes).decode('utf-8')

    async with aiohttp.ClientSession() as session:
        # بررسی وجود فایل برای گرفتن SHA
        existing_sha = None
        try:
            async with session.get(api_url, headers=headers) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    existing_sha = data.get("sha")
        except:
            pass

        # ساخت payload
        payload = {
            "message": message,
            "content": content_b64,
            "branch": branch
        }

        if existing_sha:
            payload["sha"] = existing_sha

        # ارسال درخواست
        async with session.put(api_url, headers=headers, json=payload) as resp:
            if resp.status in [200, 201]:
                data = await resp.json()
                return {
                    "success": True,
                    "path": file_path,
                    "sha": data.get("content", {}).get("sha"),
                    "url": data.get("content", {}).get("html_url"),
                    "action": "updated" if existing_sha else "created"
                }
            else:
                error = await resp.text()
                return {
                    "success": False,
                    "path": file_path,
                    "error": error
                }


async def trigger_render_deploy(
    render_service_id: str = None,
    project_id: str = None,
    db_session = None,
    project_name: str = None
) -> dict:
    """
    Trigger یک deploy جدید در Render
    سعی میکنه خودکار سرویس مناسب رو پیدا کنه بر اساس نام پروژه
    """
    import logging
    logger = logging.getLogger(__name__)

    from ...services.deploy_service import RenderDeployService
    from ...models.setting import Setting

    # ابتدا از environment بخون
    render_api_key = os.getenv("RENDER_API_KEY", "")

    # اگر نبود، از دیتابیس بخون
    if not render_api_key and db_session:
        try:
            render_api_key = Setting.get_value(db_session, "api_key_render") or ""
            if render_api_key:
                logger.info("[Render Deploy] API Key loaded from database")
                # همچنین در environment ذخیره کن برای دفعات بعد
                os.environ["RENDER_API_KEY"] = render_api_key
        except Exception as e:
            logger.warning(f"[Render Deploy] Could not load API key from database: {e}")

    logger.info(f"[Render Deploy] API Key exists: {bool(render_api_key)}")

    if not render_api_key:
        return {"success": False, "error": "Render API key not configured. Please set it in Settings."}

    render_service = RenderDeployService(api_key=render_api_key)

    service_id = render_service_id
    repo_name = None
    saved_service_ids = []

    # دریافت نام repo و سرویس‌های ذخیره شده از پروژه
    if project_id and db_session:
        try:
            project = db_session.query(Project).filter(Project.id == project_id).first()
            if project and project.extra_data:
                extra = json.loads(project.extra_data)
                # ابتدا چک کن آیا چند سرویس ذخیره شده
                saved_service_ids = extra.get("render_service_ids", [])
                if not service_id:
                    service_id = extra.get("render_service_id")
                repo_name = extra.get("repo")
                project_name = project_name or project.name
                logger.info(f"[Render Deploy] Project: {project_name}, saved_services: {len(saved_service_ids)}, service_id: {service_id}")
        except Exception as e:
            logger.warning(f"[Render Deploy] Error reading project extra_data: {e}")

    # اگر چند سرویس ذخیره شده، همه رو deploy کن
    if saved_service_ids and len(saved_service_ids) > 0:
        results = []
        for svc_id in saved_service_ids:
            try:
                result = await render_service.trigger_deploy(svc_id)
                results.append({
                    "service_id": svc_id,
                    "success": result.get("success"),
                    "deploy_id": result.get("deploy_id"),
                    "error": result.get("error"),
                })
            except Exception as e:
                results.append({
                    "service_id": svc_id,
                    "success": False,
                    "error": str(e),
                })

        await render_service.close()
        success_count = sum(1 for r in results if r.get("success"))

        return {
            "success": success_count > 0,
            "multiple_services": True,
            "services_deployed": results,
            "message": f"Deploy triggered for {success_count}/{len(results)} services",
        }

    # اگر service_id نداریم، سعی کن از روی نام پروژه پیدا کنی
    if not service_id:
        try:
            logger.info("[Render Deploy] Listing services to find matching ones...")
            services = await render_service.list_services()
            logger.info(f"[Render Deploy] Found {len(services) if services else 0} services")

            if services and len(services) > 0:
                matched_services = []
                search_name = (repo_name or project_name or "").lower().replace("_", "-").replace(" ", "-")

                for svc in services:
                    svc_data = svc.get("service", svc)
                    svc_id = svc_data.get("id")
                    svc_name = (svc_data.get("name") or "").lower()

                    # مطابقت بر اساس نام
                    if search_name and (search_name in svc_name or svc_name in search_name):
                        matched_services.append({
                            "id": svc_id,
                            "name": svc_data.get("name"),
                            "type": svc_data.get("type"),
                            "url": svc_data.get("serviceDetails", {}).get("url"),
                        })
                        logger.info(f"[Render Deploy] Matched service: {svc_data.get('name')} ({svc_id})")

                # اگر یک یا چند سرویس پیدا شد
                if len(matched_services) == 1:
                    service_id = matched_services[0]["id"]
                elif len(matched_services) > 1:
                    # چند سرویس پیدا شد (مثلاً frontend و backend) - همه رو deploy کن
                    results = []
                    for svc in matched_services:
                        try:
                            result = await render_service.trigger_deploy(svc["id"])
                            results.append({
                                "service_id": svc["id"],
                                "name": svc["name"],
                                "success": result.get("success"),
                                "deploy_id": result.get("deploy_id"),
                                "error": result.get("error"),
                            })
                        except Exception as e:
                            results.append({
                                "service_id": svc["id"],
                                "name": svc["name"],
                                "success": False,
                                "error": str(e),
                            })

                    await render_service.close()
                    success_count = sum(1 for r in results if r.get("success"))

                    return {
                        "success": success_count > 0,
                        "multiple_services": True,
                        "services_deployed": results,
                        "message": f"Deploy triggered for {success_count}/{len(results)} services",
                    }
                else:
                    # هیچ سرویس مطابقی پیدا نشد - لیست سرویس‌ها رو برگردون
                    await render_service.close()
                    all_services = []
                    for svc in services:
                        svc_data = svc.get("service", svc)
                        all_services.append({
                            "id": svc_data.get("id"),
                            "name": svc_data.get("name"),
                            "type": svc_data.get("type"),
                        })

                    return {
                        "success": False,
                        "error": f"سرویسی با نام '{search_name}' در Render پیدا نشد",
                        "available_services": all_services,
                        "hint": "لطفاً از لیست سرویس‌ها، service_id مناسب را در تنظیمات پروژه ذخیره کنید"
                    }

        except Exception as e:
            logger.error(f"[Render Deploy] Error listing services: {e}")
            await render_service.close()
            return {"success": False, "error": f"Error listing Render services: {str(e)}"}

    if not service_id:
        await render_service.close()
        return {"success": False, "error": "No Render service found. Please deploy your project to Render first."}

    # Trigger deploy
    try:
        logger.info(f"[Render Deploy] Triggering deploy for service: {service_id}")
        result = await render_service.trigger_deploy(service_id)
        await render_service.close()

        logger.info(f"[Render Deploy] Result: {result}")

        if result.get("success"):
            return {
                "success": True,
                "service_id": service_id,
                "deploy_id": result.get("deploy_id"),
                "status": result.get("status"),
                "message": "Deploy triggered successfully"
            }
        else:
            return {
                "success": False,
                "error": result.get("error", "Failed to trigger deploy")
            }
    except Exception as e:
        logger.error(f"[Render Deploy] Deploy error: {e}")
        await render_service.close()
        return {
            "success": False,
            "error": f"Deploy error: {str(e)}"
        }


# =====================================
# Endpoints
# =====================================

@router.get("/models/available")
async def get_available_models():
    """لیست مدل‌های AI موجود برای انتخاب"""
    return {
        "success": True,
        "models": AVAILABLE_MODELS
    }


@router.get("/{project_id}/memory")
async def get_project_memory(project_id: str, db: Session = Depends(get_db)):
    """
    دریافت اطلاعات حافظه پروژه
    شامل: باکس حافظه (دستورات ثابت) و فیلدهای پویا
    """
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="پروژه یافت نشد")

    # پارس JSON فیلدها
    memory_instructions = {"content": "", "target_models": ["all"]}
    dynamic_fields = []

    try:
        if project.memory_instructions:
            memory_instructions = json.loads(project.memory_instructions)
    except (json.JSONDecodeError, TypeError):
        pass

    try:
        if project.dynamic_fields:
            dynamic_fields = json.loads(project.dynamic_fields)
    except (json.JSONDecodeError, TypeError):
        pass

    return {
        "success": True,
        "project_id": project_id,
        "memory_instructions": memory_instructions,
        "dynamic_fields": dynamic_fields,
        "available_models": AVAILABLE_MODELS,
        "trigger_intervals": TRIGGER_INTERVALS
    }


@router.put("/{project_id}/memory/instructions")
async def update_memory_instructions(
    project_id: str,
    request: MemoryInstructionsRequest,
    db: Session = Depends(get_db)
):
    """
    بروزرسانی باکس حافظه (دستورات ثابت)
    این دستورات برای مدل‌های انتخاب شده در کارها اعمال می‌شوند

    🆕 با ردیابی تغییرات - هر تغییر در ژورنال ثبت می‌شود
    """
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="پروژه یافت نشد")

    # 🆕 ذخیره مقدار قبلی برای ردیابی
    previous_memory = {}
    try:
        if project.memory_instructions:
            previous_memory = json.loads(project.memory_instructions)
    except:
        pass

    previous_content = previous_memory.get("content", "")

    memory_data = {
        "content": request.content,
        "target_models": request.target_models
    }

    project.memory_instructions = json.dumps(memory_data, ensure_ascii=False)

    # 🆕 ثبت تغییرات در ژورنال با جزئیات کامل
    if previous_content != request.content:
        from .project_journal import ActivityLog, log_detailed_operation
        import uuid

        # ایجاد لاگ اصلی
        parent_log = ActivityLog(
            id=f"log_{uuid.uuid4().hex[:12]}",
            project_id=project_id,
            model_id="system",
            activity_type="memory_update",
            prompt=f"بروزرسانی باکس حافظه پروژه",
            response=f"تغییر از {len(previous_content)} کاراکتر به {len(request.content)} کاراکتر",
            tokens_used=0,
            latency_ms=0,
            success=True,
            field_name="memory_instructions",
            created_at=datetime.utcnow(),
            extra_data=json.dumps({
                "previous_length": len(previous_content),
                "new_length": len(request.content),
                "target_models": request.target_models
            }, ensure_ascii=False)
        )
        db.add(parent_log)
        db.flush()

        # 🆕 ثبت جزئیات تغییر با قابلیت کلیک
        log_detailed_operation(
            db=db,
            project_id=project_id,
            parent_log_id=parent_log.id,
            operation_type="memory_content_change",
            summary=f"تغییر محتوای باکس حافظه ({len(previous_content)} -> {len(request.content)} کاراکتر)",
            details={
                "change_type": "update",
                "previous_length": len(previous_content),
                "new_length": len(request.content),
                "target_models_changed": previous_memory.get("target_models") != request.target_models
            },
            before_value=previous_content,
            after_value=request.content,
            target_type="memory",
            target_id="memory_instructions",
            target_name="باکس حافظه"
        )

    db.commit()

    return {
        "success": True,
        "message": "باکس حافظه بروزرسانی شد",
        "memory_instructions": memory_data,
        "change_tracked": previous_content != request.content  # 🆕 آیا تغییر ردیابی شد
    }


@router.post("/{project_id}/memory/fields")
async def add_dynamic_field(
    project_id: str,
    request: DynamicFieldRequest,
    db: Session = Depends(get_db)
):
    """
    افزودن فیلد پویای جدید
    این فیلدها برای دستورات متغیر و موقتی استفاده می‌شوند
    """
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="پروژه یافت نشد")

    # دریافت فیلدهای موجود
    dynamic_fields = []
    try:
        if project.dynamic_fields:
            dynamic_fields = json.loads(project.dynamic_fields)
    except (json.JSONDecodeError, TypeError):
        pass

    # تعیین خودکار field_type براساس archive_after_run
    field_type = request.field_type
    if field_type == "temporary" and request.archive_after_run:
        field_type = "temporary"
    elif not request.archive_after_run and request.trigger and request.trigger.enabled:
        field_type = "permanent"

    # افزودن فیلد جدید با تنظیمات کامل
    new_field = {
        "id": str(uuid.uuid4()),
        "name": request.name,
        "value": request.value,
        "target_models": request.target_models,
        "trigger": {
            "enabled": request.trigger.enabled if request.trigger else False,
            "interval_minutes": request.trigger.interval_minutes if request.trigger else 60,
            "interval_type": request.trigger.interval_type if request.trigger else "minutes",
            "last_run": None,
            "next_run": None
        },
        # فیلدهای GitHub
        "action_type": request.action_type,
        "target_path": request.target_path,
        "archive_after_run": request.archive_after_run,
        "deploy_after_commit": request.deploy_after_commit,
        # 🆕 فیلدهای جدید
        "field_type": field_type,
        "priority": request.priority if request.priority else 5,
        "attachments": request.attachments or [],
        # متادیتا
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "archived": False,
    }
    dynamic_fields.append(new_field)

    project.dynamic_fields = json.dumps(dynamic_fields, ensure_ascii=False)
    db.commit()

    return {
        "success": True,
        "message": "فیلد جدید اضافه شد",
        "field": new_field,
        "total_fields": len(dynamic_fields)
    }


@router.put("/{project_id}/memory/fields/{field_id}")
async def update_dynamic_field(
    project_id: str,
    field_id: str,
    request: UpdateDynamicFieldRequest,
    db: Session = Depends(get_db)
):
    """
    ویرایش فیلد پویا
    """
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="پروژه یافت نشد")

    # دریافت فیلدهای موجود
    dynamic_fields = []
    try:
        if project.dynamic_fields:
            dynamic_fields = json.loads(project.dynamic_fields)
    except (json.JSONDecodeError, TypeError):
        pass

    # پیدا کردن و ویرایش فیلد
    field_found = False
    updated_field = None
    for field in dynamic_fields:
        if field["id"] == field_id:
            if request.name is not None:
                field["name"] = request.name
            if request.value is not None:
                field["value"] = request.value
            if request.target_models is not None:
                field["target_models"] = request.target_models
            if request.trigger is not None:
                # اطمینان از وجود فیلد trigger
                if "trigger" not in field:
                    field["trigger"] = {}
                field["trigger"]["enabled"] = request.trigger.enabled
                field["trigger"]["interval_minutes"] = request.trigger.interval_minutes
                field["trigger"]["interval_type"] = request.trigger.interval_type
            # فیلدهای GitHub
            if request.action_type is not None:
                field["action_type"] = request.action_type
            if request.target_path is not None:
                field["target_path"] = request.target_path
            if request.archive_after_run is not None:
                field["archive_after_run"] = request.archive_after_run
            if request.deploy_after_commit is not None:
                field["deploy_after_commit"] = request.deploy_after_commit
            if request.archived is not None:
                field["archived"] = request.archived
                if request.archived:
                    field["archived_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ")
            # 🆕 فیلدهای جدید
            if request.field_type is not None:
                field["field_type"] = request.field_type
            if request.priority is not None:
                field["priority"] = request.priority
            if request.attachments is not None:
                field["attachments"] = request.attachments
            field["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ")
            field_found = True
            updated_field = field
            break

    if not field_found:
        raise HTTPException(status_code=404, detail="فیلد یافت نشد")

    project.dynamic_fields = json.dumps(dynamic_fields, ensure_ascii=False)
    db.commit()

    return {
        "success": True,
        "message": "فیلد بروزرسانی شد"
    }


@router.delete("/{project_id}/memory/fields/{field_id}")
async def delete_dynamic_field(
    project_id: str,
    field_id: str,
    db: Session = Depends(get_db)
):
    """
    حذف فیلد پویا
    """
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="پروژه یافت نشد")

    # دریافت فیلدهای موجود
    dynamic_fields = []
    try:
        if project.dynamic_fields:
            dynamic_fields = json.loads(project.dynamic_fields)
    except (json.JSONDecodeError, TypeError):
        pass

    # فیلتر کردن فیلد
    original_count = len(dynamic_fields)
    dynamic_fields = [f for f in dynamic_fields if f["id"] != field_id]

    if len(dynamic_fields) == original_count:
        raise HTTPException(status_code=404, detail="فیلد یافت نشد")

    project.dynamic_fields = json.dumps(dynamic_fields, ensure_ascii=False)
    db.commit()

    return {
        "success": True,
        "message": "فیلد حذف شد",
        "remaining_fields": len(dynamic_fields)
    }


@router.post("/{project_id}/memory/fields/upgrade-action-types")
async def upgrade_fields_action_types(
    project_id: str,
    db: Session = Depends(get_db)
):
    """
    🔴 ارتقای خودکار action_type فیلدهای موجود
    فیلدهایی که target_path دارند و نوع مشکل کدی هستند را به github_commit تغییر می‌دهد
    """
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="پروژه یافت نشد")

    dynamic_fields = []
    try:
        if project.dynamic_fields:
            dynamic_fields = json.loads(project.dynamic_fields)
    except (json.JSONDecodeError, TypeError):
        pass

    # انواع مشکلاتی که نیاز به تغییر کد دارند
    code_change_keywords = ["security", "bug", "quality", "performance", "error", "warning", "vulnerability", "fix", "اصلاح", "امنیت", "باگ"]

    upgraded_count = 0
    upgraded_fields = []

    for field in dynamic_fields:
        # فقط فیلدهایی که display هستند و target_path دارند
        if field.get("action_type") == "display" and field.get("target_path"):
            field_name = field.get("name", "").lower()
            field_value = field.get("value", "").lower()

            # بررسی آیا نوع مشکل کدی است
            needs_upgrade = any(kw in field_name or kw in field_value for kw in code_change_keywords)

            if needs_upgrade:
                field["action_type"] = "github_commit"
                field["deploy_after_commit"] = True
                field["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ")
                upgraded_count += 1
                upgraded_fields.append(field.get("name"))

    if upgraded_count > 0:
        project.dynamic_fields = json.dumps(dynamic_fields, ensure_ascii=False)
        db.commit()

    return {
        "success": True,
        "upgraded_count": upgraded_count,
        "upgraded_fields": upgraded_fields[:20],  # فقط 20 تای اول
        "message": f"{upgraded_count} فیلد به github_commit ارتقا یافت"
    }


@router.get("/{project_id}/memory/for-model/{model_id}")
async def get_memory_for_model(
    project_id: str,
    model_id: str,
    db: Session = Depends(get_db)
):
    """
    دریافت دستورات مرتبط با یک مدل خاص
    برای استفاده توسط سرویس‌های AI
    """
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="پروژه یافت نشد")

    # پارس JSON فیلدها
    memory_instructions = {"content": "", "target_models": ["all"]}
    dynamic_fields = []

    try:
        if project.memory_instructions:
            memory_instructions = json.loads(project.memory_instructions)
    except (json.JSONDecodeError, TypeError):
        pass

    try:
        if project.dynamic_fields:
            dynamic_fields = json.loads(project.dynamic_fields)
    except (json.JSONDecodeError, TypeError):
        pass

    # فیلتر کردن بر اساس مدل
    result_instructions = ""
    result_fields = []

    # بررسی باکس حافظه
    if "all" in memory_instructions.get("target_models", []) or model_id in memory_instructions.get("target_models", []):
        result_instructions = memory_instructions.get("content", "")

    # بررسی فیلدهای پویا
    for field in dynamic_fields:
        if "all" in field.get("target_models", []) or model_id in field.get("target_models", []):
            result_fields.append({
                "name": field.get("name"),
                "value": field.get("value")
            })

    # ساخت prompt ترکیبی
    combined_prompt = ""
    if result_instructions:
        combined_prompt += f"## دستورات ثابت پروژه:\n{result_instructions}\n\n"

    if result_fields:
        combined_prompt += "## دستورات اضافی:\n"
        for field in result_fields:
            combined_prompt += f"- {field['name']}: {field['value']}\n"

    return {
        "success": True,
        "project_id": project_id,
        "model_id": model_id,
        "memory_instructions": result_instructions,
        "dynamic_fields": result_fields,
        "combined_prompt": combined_prompt.strip() if combined_prompt else None
    }


# =====================================
# چت با AI در context پروژه
# =====================================

class ProjectChatRequest(BaseModel):
    """درخواست چت در context پروژه"""
    prompt: str
    model_id: str = "openai"  # مدل پیش‌فرض
    include_memory: bool = True  # شامل دستورات حافظه شود؟


class EnhancedProjectChatRequest(BaseModel):
    """درخواست چت پیشرفته با context کامل پروژه"""
    prompt: str
    model_ids: List[str] = ["openai"]  # امکان انتخاب چند مدل همزمان
    include_memory: bool = True  # شامل دستورات حافظه شود؟
    include_files: bool = True  # شامل محتوای فایل‌ها شود؟
    include_issues: bool = True  # شامل ایرادات شناسایی شده شود؟
    include_health: bool = True  # شامل وضعیت سلامت شود؟
    include_logs: bool = True  # شامل لاگ‌های سرویس شود؟
    log_hours: int = 24  # بازه زمانی لاگ‌ها (ساعت)
    log_levels: List[str] = ["error", "warn"]  # سطوح لاگ
    max_logs: int = 50  # حداکثر تعداد لاگ
    file_filter: Optional[List[str]] = None  # فیلتر فایل‌ها (فقط این فایل‌ها شامل شوند)
    max_file_content_length: int = 5000  # حداکثر طول محتوای هر فایل
    create_dynamic_fields: bool = False  # تبدیل پاسخ به فیلدهای پویا؟
    auto_detect_actions: bool = True  # تشخیص خودکار نوع اقدام از پاسخ؟


@router.post("/{project_id}/chat")
async def project_chat(
    project_id: str,
    request: ProjectChatRequest,
    db: Session = Depends(get_db)
):
    """
    چت با AI در context یک پروژه
    دستورات حافظه و فیلدهای پویا به صورت خودکار به prompt اضافه می‌شوند
    """
    from ...services.ai_manager import get_ai_manager
    from ...services.ai_base import Message

    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="پروژه یافت نشد")

    # ساخت system prompt با context پروژه
    system_parts = [f"تو یک دستیار هوشمند برای پروژه '{project.name}' هستی."]

    if project.description:
        system_parts.append(f"توضیحات پروژه: {project.description}")

    # اضافه کردن دستورات حافظه اگر فعال باشد
    if request.include_memory:
        # دریافت دستورات برای این مدل
        memory_instructions = {"content": "", "target_models": ["all"]}
        dynamic_fields = []

        try:
            if project.memory_instructions:
                memory_instructions = json.loads(project.memory_instructions)
        except (json.JSONDecodeError, TypeError):
            pass

        try:
            if project.dynamic_fields:
                dynamic_fields = json.loads(project.dynamic_fields)
        except (json.JSONDecodeError, TypeError):
            pass

        # فیلتر بر اساس مدل
        model_id = request.model_id.split("/")[0] if "/" in request.model_id else request.model_id

        if "all" in memory_instructions.get("target_models", []) or model_id in memory_instructions.get("target_models", []):
            if memory_instructions.get("content"):
                system_parts.append(f"\n## دستورات ثابت:\n{memory_instructions['content']}")

        relevant_fields = []
        for field in dynamic_fields:
            if "all" in field.get("target_models", []) or model_id in field.get("target_models", []):
                relevant_fields.append(field)

        if relevant_fields:
            system_parts.append("\n## دستورات اضافی:")
            for field in relevant_fields:
                system_parts.append(f"- {field.get('name')}: {field.get('value')}")

    system_prompt = "\n".join(system_parts)

    # ارسال به AI
    from datetime import datetime
    start_time = time.time()

    try:
        ai_manager = get_ai_manager()

        messages = [
            Message(role="system", content=system_prompt),
            Message(role="user", content=request.prompt),
        ]

        response = await ai_manager.generate(
            model_id=request.model_id,
            messages=messages,
            max_tokens=4096,
            temperature=0.7,
        )

        latency_ms = int((time.time() - start_time) * 1000)

        # ثبت در ژورنال - موفق
        log_entry = ActivityLog(
            id=f"log_{uuid.uuid4().hex[:12]}",
            project_id=project_id,
            model_id=response.model_id,
            model_provider=request.model_id.split("-")[0] if "-" in request.model_id else request.model_id,
            activity_type="chat",
            prompt=request.prompt[:2000],
            response=response.content[:5000] if response.content else None,
            tokens_used=response.tokens_used or 0,
            latency_ms=latency_ms,
            success=True,
            created_at=datetime.utcnow(),
        )
        db.add(log_entry)
        db.commit()

        return {
            "success": True,
            "model_id": response.model_id,
            "content": response.content,
            "tokens_used": response.tokens_used,
            "latency_ms": latency_ms,
        }

    except Exception as e:
        latency_ms = int((time.time() - start_time) * 1000)

        # ثبت در ژورنال - خطا
        log_entry = ActivityLog(
            id=f"log_{uuid.uuid4().hex[:12]}",
            project_id=project_id,
            model_id=request.model_id,
            activity_type="chat",
            prompt=request.prompt[:2000],
            tokens_used=0,
            latency_ms=latency_ms,
            success=False,
            error_message=str(e)[:500],
            created_at=datetime.utcnow(),
        )
        db.add(log_entry)
        db.commit()

        raise HTTPException(status_code=500, detail=f"خطا در ارتباط با AI: {str(e)}")


# =====================================
# چت پیشرفته با AI - با context کامل پروژه
# =====================================

@router.post("/{project_id}/enhanced-chat")
async def enhanced_project_chat(
    project_id: str,
    request: EnhancedProjectChatRequest,
    db: Session = Depends(get_db)
):
    """
    چت پیشرفته با AI در context کامل پروژه

    ویژگی‌ها:
    - دسترسی کامل به محتوای تمام فایل‌ها
    - مشاهده ایرادات شناسایی شده و وضعیت سلامت
    - امکان انتخاب چندین مدل همزمان
    - تبدیل خودکار پاسخ به فیلدهای پویا
    """
    from ...services.ai_manager import get_ai_manager
    from ...services.ai_base import Message
    from ...models.project import ProjectFile
    from datetime import datetime

    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="پروژه یافت نشد")

    # 1. ساخت context کامل پروژه
    context_parts = [
        f"# پروژه: {project.name}",
        f"نوع: {project.project_type}",
    ]

    if project.description:
        context_parts.append(f"توضیحات: {project.description}")

    # 2. اضافه کردن تکنولوژی‌ها و ویژگی‌ها
    try:
        technologies = json.loads(project.technologies) if project.technologies else []
        if technologies:
            context_parts.append(f"تکنولوژی‌ها: {', '.join(technologies)}")
    except:
        pass

    try:
        features = json.loads(project.features) if project.features else []
        if features:
            context_parts.append(f"ویژگی‌ها: {', '.join(features)}")
    except:
        pass

    # 3. اضافه کردن وضعیت سلامت
    if request.include_health:
        try:
            health_scores = json.loads(project.health_scores) if project.health_scores else {}
            if health_scores:
                context_parts.append("\n## وضعیت سلامت پروژه:")
                for key, value in health_scores.items():
                    context_parts.append(f"- {key}: {value}")
        except:
            pass

        if project.ideal_state:
            context_parts.append(f"\n## حالت ایده‌آل پروژه:\n{project.ideal_state}")

    # 4. اضافه کردن ایرادات شناسایی شده
    if request.include_issues:
        try:
            issues_found = json.loads(project.issues_found) if project.issues_found else []
            if issues_found:
                # 🔴 رفع محدودیت - تمام ایرادات نمایش داده می‌شوند
                context_parts.append(f"\n## ایرادات شناسایی شده ({len(issues_found)} مورد):")
                for i, issue in enumerate(issues_found, 1):
                    issue_text = f"{i}. "
                    if isinstance(issue, dict):
                        issue_text += f"[{issue.get('severity', 'نامشخص')}] {issue.get('title', issue.get('description', str(issue)))}"
                        if issue.get('file'):
                            issue_text += f" (فایل: {issue.get('file')})"
                    else:
                        issue_text += str(issue)
                    context_parts.append(issue_text)
        except:
            pass

    # 5. اضافه کردن محتوای فایل‌ها
    if request.include_files:
        files = db.query(ProjectFile).filter(ProjectFile.project_id == project_id).all()

        # فیلتر فایل‌ها
        if request.file_filter:
            files = [f for f in files if any(
                pattern in f.file_path or f.file_path.endswith(pattern.lstrip('*'))
                for pattern in request.file_filter
            )]

        if files:
            context_parts.append(f"\n## محتوای فایل‌های پروژه ({len(files)} فایل):")
            for file in files:
                content = file.content or ""
                if len(content) > request.max_file_content_length:
                    content = content[:request.max_file_content_length] + "\n... (ادامه truncated شد)"

                context_parts.append(f"\n### فایل: {file.file_path}")
                context_parts.append(f"```{file.file_type or ''}\n{content}\n```")

    # 6. اضافه کردن دستورات حافظه
    if request.include_memory:
        try:
            memory_instructions = json.loads(project.memory_instructions) if project.memory_instructions else {}
            if memory_instructions.get("content"):
                context_parts.append(f"\n## دستورات ثابت:\n{memory_instructions['content']}")
        except:
            pass

        try:
            dynamic_fields = json.loads(project.dynamic_fields) if project.dynamic_fields else []
            if dynamic_fields:
                relevant_fields = [f for f in dynamic_fields if not f.get("archived")]
                if relevant_fields:
                    context_parts.append("\n## دستورات پویا:")
                    for field in relevant_fields:
                        context_parts.append(f"- {field.get('name')}: {field.get('value')}")
        except:
            pass

    # 7. 🆕 اضافه کردن نتایج اسکن امنیتی
    try:
        if project.security_scan_result:
            scan_data = json.loads(project.security_scan_result) if isinstance(project.security_scan_result, str) else project.security_scan_result
            context_parts.append("\n## نتایج اسکن امنیتی:")
            context_parts.append(f"- امتیاز امنیتی: {scan_data.get('security_score', 0)}/100")
            summary = scan_data.get("summary", {})
            if summary:
                context_parts.append(f"- کل مشکلات: {summary.get('total_issues', 0)}")
                context_parts.append(f"- بحرانی: {summary.get('critical', 0)}, بالا: {summary.get('high', 0)}, متوسط: {summary.get('medium', 0)}")
            secrets = scan_data.get("secrets", {}).get("findings", [])
            if secrets:
                context_parts.append(f"- کلیدهای محرمانه: {len(secrets)} مورد یافت شد")
            vulns = scan_data.get("dependencies", {}).get("vulnerabilities", [])
            if vulns:
                context_parts.append(f"- آسیب‌پذیری وابستگی‌ها: {len(vulns)} مورد")
    except:
        pass

    # 8. 🆕 اضافه کردن نتایج پوشش تست
    try:
        if project.test_coverage_result:
            coverage_data = json.loads(project.test_coverage_result) if isinstance(project.test_coverage_result, str) else project.test_coverage_result
            context_parts.append("\n## نتایج پوشش تست:")
            summary = coverage_data.get("summary", {})
            context_parts.append(f"- درصد پوشش: {summary.get('coverage_percent', 0)}%")
            context_parts.append(f"- تعداد تست‌ها: {summary.get('total_tests', 0)}")
            context_parts.append(f"- امتیاز سلامت تست: {coverage_data.get('health_score', 0)}/100")
            untested = coverage_data.get("untested_files", [])
            if untested:
                context_parts.append(f"- فایل‌های بدون تست: {len(untested)} فایل")
                for uf in untested[:5]:
                    context_parts.append(f"  - {uf.get('path', uf)}")
            recs = coverage_data.get("recommendations", [])
            if recs:
                context_parts.append(f"- توصیه‌ها: {len(recs)} مورد")
    except:
        pass

    # 9. 🆕 اضافه کردن ایرادات پروژه (از مدل ProjectIssue)
    try:
        from ...models.project import ProjectIssue
        issues = db.query(ProjectIssue).filter(
            ProjectIssue.project_id == project_id,
            ProjectIssue.status.in_(["open", "in_progress"])
        ).order_by(ProjectIssue.priority).limit(20).all()
        if issues:
            context_parts.append(f"\n## ایرادات ثبت شده ({len(issues)} مورد):")
            for issue in issues:
                priority_map = {1: "بحرانی", 2: "بالا", 3: "متوسط", 4: "پایین"}
                priority_label = priority_map.get(issue.priority, "نامشخص")
                context_parts.append(f"- [{priority_label}] {issue.title} (منبع: {issue.source})")
                if issue.description:
                    context_parts.append(f"  توضیح: {issue.description[:200]}")
    except:
        pass

    # 10. 🆕 اضافه کردن خلاصه بایگانی
    try:
        if project.general_archive:
            archive_data = json.loads(project.general_archive) if isinstance(project.general_archive, str) else project.general_archive
            if archive_data:
                context_parts.append(f"\n## خلاصه بایگانی ({len(archive_data)} مورد):")
                by_type = {}
                for item in archive_data:
                    item_type = item.get("type", "other")
                    by_type[item_type] = by_type.get(item_type, 0) + 1
                for t, c in by_type.items():
                    context_parts.append(f"- {t}: {c} مورد")
    except:
        pass

    # 11. 🆕 اضافه کردن اطلاعات GitHub
    try:
        if project.extra_data:
            extra = json.loads(project.extra_data) if isinstance(project.extra_data, str) else project.extra_data
            if extra.get("source") == "github":
                context_parts.append("\n## اطلاعات GitHub:")
                context_parts.append(f"- مخزن: {extra.get('owner')}/{extra.get('repo')}")
                context_parts.append(f"- شاخه: {extra.get('branch', 'main')}")
    except:
        pass

    # 12. 🆕 اضافه کردن لاگ‌های سرویس Render
    if request.include_logs:
        try:
            from datetime import timedelta
            from ...models.render_log import RenderLog, RenderService

            # پیدا کردن سرویس‌های مرتبط با پروژه
            services = db.query(RenderService).all()
            service_ids = []

            # تلاش برای match کردن سرویس با پروژه
            project_name_lower = project.name.lower() if project.name else ""
            github_path = project.github_path.lower() if project.github_path else ""

            for service in services:
                service_name_lower = service.name.lower() if service.name else ""
                if (project_name_lower and project_name_lower in service_name_lower) or \
                   (service_name_lower and service_name_lower in project_name_lower) or \
                   (github_path and service_name_lower in github_path):
                    service_ids.append(service.id)

            if service_ids:
                # دریافت لاگ‌ها
                cutoff = datetime.utcnow() - timedelta(hours=request.log_hours)
                logs_query = db.query(RenderLog).filter(
                    RenderLog.service_id.in_(service_ids),
                    RenderLog.timestamp >= cutoff,
                    RenderLog.level.in_(request.log_levels)
                ).order_by(RenderLog.timestamp.desc()).limit(request.max_logs)

                logs = logs_query.all()

                if logs:
                    context_parts.append(f"\n## لاگ‌های سرویس ({len(logs)} مورد از {request.log_hours} ساعت اخیر):")
                    for log in logs:
                        ts = log.timestamp.strftime("%Y-%m-%d %H:%M") if log.timestamp else "?"
                        level = (log.level or "?").upper()
                        service = log.service_name or log.service_id or "?"
                        msg = (log.message or "")[:300]  # محدود کردن طول پیام
                        context_parts.append(f"[{ts}] [{level}] [{service}] {msg}")

                    # اضافه کردن آمار خطاها
                    error_count = sum(1 for l in logs if l.level in ["error", "fatal", "critical"])
                    warn_count = sum(1 for l in logs if l.level == "warn")
                    context_parts.append(f"\n📊 آمار: {error_count} خطا، {warn_count} هشدار در {request.log_hours} ساعت اخیر")
        except Exception as e:
            context_parts.append(f"\n⚠️ خطا در دریافت لاگ‌ها: {str(e)}")

    full_context = "\n".join(context_parts)

    # 13. ساخت system prompt
    system_prompt = f"""تو یک دستیار هوشمند برای تحلیل و بررسی دقیق پروژه هستی.

وظیفه تو:
1. بررسی دقیق و جزء به جزء محتوای پروژه
2. یافتن مشکلات واقعی با ارجاع به فایل و خط کد مربوطه
3. ارائه راه‌حل‌های مشخص و عملی
4. پاسخ‌های قاطع (نه با شاید و احتمالا) بر اساس آنچه در کد می‌بینی
5. تحلیل لاگ‌های سرویس و شناسایی الگوهای خطا

هنگام پاسخ‌گویی:
- اگر مشکلی وجود دارد، دقیقاً بگو کجا و چرا
- اگر باید اقدامی انجام شود، مشخص کن: فایل، خط، و تغییر لازم
- اولویت مشکلات را مشخص کن (بحرانی، بالا، متوسط، پایین)
- در صورت وجود لاگ خطا، علت احتمالی و راه‌حل را ارائه بده
- الگوهای تکراری در لاگ‌ها را شناسایی کن

{full_context}"""

    # 8. ارسال به مدل‌های انتخاب شده
    ai_manager = get_ai_manager()
    responses = []
    total_tokens = 0

    for model_id in request.model_ids:
        start_time = time.time()
        try:
            messages = [
                Message(role="system", content=system_prompt),
                Message(role="user", content=request.prompt),
            ]

            response = await ai_manager.generate(
                model_id=model_id,
                messages=messages,
                max_tokens=4096,
                temperature=0.3,  # دقت بالاتر
            )

            latency_ms = int((time.time() - start_time) * 1000)
            tokens_used = response.tokens_used or 0
            total_tokens += tokens_used

            model_response = {
                "model_id": model_id,
                "actual_model": response.model_id,
                "content": response.content,
                "tokens_used": tokens_used,
                "latency_ms": latency_ms,
                "success": True,
            }
            responses.append(model_response)

            # 🔴 ثبت کامل جزئیات در ژورنال (بهبود یافته)
            log_entry = ActivityLog(
                id=f"log_{uuid.uuid4().hex[:12]}",
                project_id=project_id,
                model_id=response.model_id,
                model_provider=model_id.split("-")[0] if "-" in model_id else model_id,
                activity_type="enhanced_chat",
                prompt=request.prompt[:2000],
                response=response.content[:5000] if response.content else None,
                tokens_used=tokens_used,
                latency_ms=latency_ms,
                success=True,
                field_name=f"AI Query: {request.prompt[:50]}...",  # 🔴 نام قابل شناسایی
                extra_data=json.dumps({
                    "full_prompt": request.prompt,
                    "model_requested": model_id,
                    "model_used": response.model_id,
                    "create_dynamic_fields": request.create_dynamic_fields,
                    "auto_detect_actions": request.auto_detect_actions,
                    "files_included_count": len(files) if request.include_files else 0,
                    "context_length": len(full_context),
                    "response_length": len(response.content) if response.content else 0,
                    "clickable": True,  # 🔴 قابل کلیک در UI
                }, ensure_ascii=False),
                created_at=datetime.utcnow(),
            )
            db.add(log_entry)

        except Exception as e:
            latency_ms = int((time.time() - start_time) * 1000)
            model_response = {
                "model_id": model_id,
                "content": None,
                "error": str(e),
                "latency_ms": latency_ms,
                "success": False,
            }
            responses.append(model_response)

            # 🔴 ثبت کامل جزئیات خطا در ژورنال (بهبود یافته)
            log_entry = ActivityLog(
                id=f"log_{uuid.uuid4().hex[:12]}",
                project_id=project_id,
                model_id=model_id,
                activity_type="enhanced_chat",
                prompt=request.prompt[:2000],
                tokens_used=0,
                latency_ms=latency_ms,
                success=False,
                error_message=str(e)[:500],
                field_name=f"AI Query Error: {request.prompt[:40]}...",  # 🔴 نام قابل شناسایی
                extra_data=json.dumps({
                    "full_prompt": request.prompt,
                    "model_requested": model_id,
                    "error_details": str(e),
                    "create_dynamic_fields": request.create_dynamic_fields,
                    "files_included_count": len(files) if request.include_files else 0,
                    "clickable": True,  # 🔴 قابل کلیک در UI
                }, ensure_ascii=False),
                created_at=datetime.utcnow(),
            )
            db.add(log_entry)

    db.commit()

    # 9. تبدیل به فیلدهای پویا با سرویس هوشمند
    # 🆕 استفاده از IntelligentFieldCreator برای:
    # - بررسی قابلیت‌های موجود (فیلد + نقشه راه)
    # - تعیین وابستگی و اولویت هوشمند
    # - اضافه کردن خودکار به نقشه راه
    created_fields = []
    merged_fields = []
    skipped_fields = []
    roadmap_items_added = []
    existing_capabilities = []

    if request.create_dynamic_fields:
        from ...services.intelligent_field_creator import get_intelligent_field_creator

        field_creator = get_intelligent_field_creator(project_id, db)

        for resp in responses:
            if resp.get("success") and resp.get("content"):
                # پارس پاسخ AI به بخش‌های قابل تبدیل به فیلد
                fields = await parse_response_to_dynamic_fields(
                    resp["content"],
                    resp["model_id"],
                    request.auto_detect_actions
                )

                for field in fields:
                    # 🆕 ایجاد هوشمند فیلد با بررسی کامل
                    result = await field_creator.create_intelligent_field(
                        name=field.get("name", "فیلد جدید"),
                        value=field.get("value", ""),
                        source_prompt=request.prompt,
                        ai_response_context=resp["content"][:500],
                        force_create=False
                    )

                    if result["success"]:
                        if result["action"] == "created":
                            result["field"]["source_model"] = resp["model_id"]
                            result["field"]["validation_marker"] = "pending"
                            result["field"]["needs_approval"] = True
                            created_fields.append(result["field"])

                            if result.get("roadmap_item_added"):
                                roadmap_items_added.append(field.get("name"))

                        elif result["action"] == "merged":
                            merged_fields.append({
                                "name": field.get("name"),
                                "merged_with": result.get("existing_match", {}).get("match", {}).get("name"),
                                "message": result.get("message")
                            })
                    else:
                        # فیلد رد شد - قابلیت مشابه وجود دارد
                        if result.get("existing_match"):
                            existing_capabilities.append({
                                "requested": field.get("name"),
                                "existing_type": result["existing_match"].get("type"),
                                "existing_name": result["existing_match"].get("match", {}).get("name") or result["existing_match"].get("match", {}).get("text"),
                                "similarity": result["existing_match"].get("similarity"),
                                "suggestion": result["existing_match"].get("suggestion")
                            })
                        skipped_fields.append({
                            "name": field.get("name"),
                            "reason": result.get("message", "قابلیت مشابه وجود دارد")
                        })

        # 🔴 ثبت در ژورنال
        if created_fields or merged_fields or existing_capabilities:
            summary_parts = []
            if created_fields:
                summary_parts.append(f"ایجاد {len(created_fields)} فیلد")
            if merged_fields:
                summary_parts.append(f"ادغام {len(merged_fields)} فیلد")
            if skipped_fields:
                summary_parts.append(f"رد {len(skipped_fields)} فیلد")
            if roadmap_items_added:
                summary_parts.append(f"اضافه به نقشه راه: {len(roadmap_items_added)} آیتم")

            ai_query_log = ActivityLog(
                id=f"log_{uuid.uuid4().hex[:12]}",
                project_id=project_id,
                model_id="system",
                activity_type="ai_query_fields_intelligent",
                prompt=f"تولید هوشمند فیلد از پرسش AI: {request.prompt[:200]}",
                response=", ".join(summary_parts) if summary_parts else "بدون تغییر",
                tokens_used=0,
                latency_ms=0,
                success=True,
                extra_data=json.dumps({
                    "created_count": len(created_fields),
                    "merged_count": len(merged_fields),
                    "skipped_count": len(skipped_fields),
                    "roadmap_added": roadmap_items_added,
                    "existing_capabilities": existing_capabilities[:5]  # فقط 5 تا اول
                }, ensure_ascii=False),
                created_at=datetime.utcnow(),
            )
            db.add(ai_query_log)
            db.commit()

    # 🆕 برگرداندن نتیجه با اطلاعات کامل
    return {
        "success": True,
        "project_id": project_id,
        "responses": responses,
        "total_tokens": total_tokens,
        "models_used": len(request.model_ids),
        "context_summary": {
            "files_included": len(files) if request.include_files else 0,
            "health_included": request.include_health,
            "memory_included": request.include_memory,
        },
        # 🔴 اطلاعات کامل فیلدها
        "created_fields": created_fields if request.create_dynamic_fields else None,
        "merged_fields": merged_fields if request.create_dynamic_fields else None,
        "skipped_fields": skipped_fields if request.create_dynamic_fields else None,
        # 🆕 اطلاعات جدید از سرویس هوشمند
        "existing_capabilities": existing_capabilities if request.create_dynamic_fields else None,
        "roadmap_items_added": roadmap_items_added if request.create_dynamic_fields else None,
        "fields_summary": {
            "created": len(created_fields),
            "merged": len(merged_fields),
            "skipped": len(skipped_fields),
            "roadmap_added": len(roadmap_items_added),
            "existing_found": len(existing_capabilities)
        } if request.create_dynamic_fields else None,
    }


def _calculate_similarity(str1: str, str2: str) -> float:
    """
    🆕 محاسبه شباهت دو رشته - نسخه بهبود یافته

    الگوریتم ترکیبی:
    1. شباهت Jaccard (کلمات مشترک)
    2. شباهت توالی (n-gram)
    3. شباهت معنایی (کلمات کلیدی)
    """
    if not str1 or not str2:
        return 0.0

    str1 = str1.lower().strip()
    str2 = str2.lower().strip()

    if str1 == str2:
        return 1.0

    # 1. شباهت Jaccard (کلمات مشترک)
    words1 = set(str1.split())
    words2 = set(str2.split())
    if words1 and words2:
        jaccard = len(words1 & words2) / len(words1 | words2)
    else:
        jaccard = 0.0

    # 2. شباهت n-gram (3-gram)
    def get_ngrams(s, n=3):
        return set(s[i:i+n] for i in range(max(0, len(s)-n+1)))

    ngrams1 = get_ngrams(str1.replace(' ', ''))
    ngrams2 = get_ngrams(str2.replace(' ', ''))
    if ngrams1 and ngrams2:
        ngram_sim = len(ngrams1 & ngrams2) / len(ngrams1 | ngrams2)
    else:
        ngram_sim = 0.0

    # 3. شباهت معنایی (کلمات کلیدی مشترک)
    key_terms = {
        'action': ['اصلاح', 'تغییر', 'حذف', 'اضافه', 'بهبود', 'fix', 'change', 'remove', 'add', 'improve'],
        'file': ['فایل', 'کلاس', 'تابع', 'متد', 'file', 'class', 'function', 'method'],
        'severity': ['مهم', 'بحرانی', 'فوری', 'جزئی', 'critical', 'important', 'urgent', 'minor'],
    }

    semantic_score = 0.0
    for category, terms in key_terms.items():
        has1 = any(term in str1 for term in terms)
        has2 = any(term in str2 for term in terms)
        if has1 and has2:
            semantic_score += 0.15

    # ترکیب نمرات با وزن
    final_score = (jaccard * 0.5) + (ngram_sim * 0.3) + min(semantic_score, 0.3)

    return min(final_score, 1.0)


def _smart_merge_fields(existing_field: dict, new_field: dict) -> dict:
    """
    🆕 ادغام هوشمند دو فیلد مشابه

    - ترکیب محتوا با جداکننده مناسب
    - حفظ اولویت بالاتر
    - ترکیب مسیرهای هدف
    - تاریخچه ادغام
    """
    merged = existing_field.copy()

    # ترکیب محتوا
    existing_value = existing_field.get('value', '')
    new_value = new_field.get('value', '')

    # جلوگیری از تکرار محتوا
    if new_value and new_value not in existing_value:
        separator = "\n\n" + "─" * 40 + "\n"
        merged['value'] = f"{existing_value}{separator}🔄 ادغام شده از: {new_field.get('name', 'فیلد جدید')}\n{new_value}"

    # حفظ اولویت بالاتر (عدد کمتر = اولویت بالاتر)
    merged['priority'] = min(
        existing_field.get('priority', 5),
        new_field.get('priority', 5)
    )

    # ترکیب مسیرهای هدف
    existing_path = existing_field.get('target_path', '')
    new_path = new_field.get('target_path', '')
    if new_path and new_path != existing_path:
        if existing_path:
            # اگر هر دو مسیر دارند، به multi_commit تبدیل کن
            merged['action_type'] = 'github_multi_commit'
            paths = merged.get('target_paths', [existing_path])
            if new_path not in paths:
                paths.append(new_path)
            merged['target_paths'] = paths
        else:
            merged['target_path'] = new_path

    # ارتقا action_type اگر لازم است
    action_priority = {'github_multi_commit': 1, 'github_commit': 2, 'file_edit': 3, 'display': 4}
    existing_action = existing_field.get('action_type', 'display')
    new_action = new_field.get('action_type', 'display')
    if action_priority.get(new_action, 4) < action_priority.get(existing_action, 4):
        merged['action_type'] = new_action

    # بروزرسانی متادیتا
    merged['updated_at'] = datetime.utcnow().isoformat()
    merge_history = merged.get('merge_history', [])
    merge_history.append({
        'merged_field': new_field.get('name'),
        'merged_at': datetime.utcnow().isoformat(),
        'source': new_field.get('source', 'unknown')
    })
    merged['merge_history'] = merge_history
    merged['merge_count'] = len(merge_history)

    return merged


def _should_merge_fields(field1: dict, field2: dict) -> tuple:
    """
    🆕 تشخیص اینکه آیا دو فیلد باید ادغام شوند

    Returns:
        tuple: (should_merge: bool, confidence: float, reason: str)
    """
    # بررسی مسیر یکسان
    path1 = field1.get('target_path', '')
    path2 = field2.get('target_path', '')
    if path1 and path2 and path1 == path2:
        return (True, 1.0, "مسیر هدف یکسان")

    # بررسی نام
    name_sim = _calculate_similarity(field1.get('name', ''), field2.get('name', ''))
    if name_sim > 0.8:
        return (True, name_sim, "نام بسیار مشابه")

    # بررسی محتوا
    value_sim = _calculate_similarity(
        field1.get('value', '')[:300],
        field2.get('value', '')[:300]
    )
    if value_sim > 0.7:
        return (True, value_sim, "محتوای مشابه")

    # بررسی action_type + path similarity
    same_action = field1.get('action_type') == field2.get('action_type')
    if path1 and path2:
        path_sim = _calculate_similarity(path1, path2)
        if same_action and path_sim > 0.6:
            return (True, path_sim, "اکشن یکسان با مسیر مشابه")

    # بررسی ترکیبی
    combined_score = (name_sim * 0.4) + (value_sim * 0.4) + (0.2 if same_action else 0)
    if combined_score > 0.6:
        return (True, combined_score, "شباهت ترکیبی بالا")

    return (False, combined_score, None)


async def parse_response_to_dynamic_fields(content: str, model_id: str, auto_detect: bool = True) -> List[dict]:
    """
    تبدیل پاسخ AI به فیلدهای پویا

    تشخیص خودکار:
    - اقدامات لازم (action items)
    - باگ‌ها و مشکلات
    - پیشنهادات بهبود
    """
    fields = []

    # الگوهای تشخیص
    patterns = {
        "bug_fix": {
            "keywords": ["باگ", "خطا", "ایراد", "مشکل", "bug", "error", "fix"],
            "action_type": "github_commit",
            "priority": 2,
            "field_type": "temporary",
        },
        "improvement": {
            "keywords": ["بهبود", "پیشنهاد", "بهتر", "improve", "suggest", "enhance"],
            "action_type": "display",
            "priority": 5,
            "field_type": "temporary",
        },
        "critical": {
            "keywords": ["بحرانی", "فوری", "امنیتی", "critical", "urgent", "security"],
            "action_type": "github_commit",
            "priority": 1,
            "field_type": "temporary",
        },
        "refactor": {
            "keywords": ["ریفکتور", "بازنویسی", "refactor", "rewrite", "restructure"],
            "action_type": "github_multi_commit",
            "priority": 4,
            "field_type": "temporary",
        },
    }

    # تقسیم محتوا به بخش‌ها
    lines = content.split('\n')
    current_section = None
    current_content = []

    for line in lines:
        # تشخیص سرتیتر
        if line.strip().startswith('#') or line.strip().startswith('**'):
            if current_section and current_content:
                # ذخیره بخش قبلی
                field = create_field_from_section(current_section, '\n'.join(current_content), patterns, auto_detect)
                if field:
                    fields.append(field)
            current_section = line.strip().replace('#', '').replace('**', '').strip()
            current_content = []
        elif line.strip().startswith(('-', '*', '•')) or (line.strip() and line.strip()[0].isdigit()):
            # آیتم‌های لیست
            current_content.append(line.strip())
        elif line.strip():
            current_content.append(line.strip())

    # آخرین بخش
    if current_section and current_content:
        field = create_field_from_section(current_section, '\n'.join(current_content), patterns, auto_detect)
        if field:
            fields.append(field)

    # اگر هیچ بخشی نبود، کل پاسخ را به یک فیلد تبدیل کن
    if not fields and content.strip():
        fields.append({
            "name": f"پاسخ {model_id}",
            "value": content[:2000],
            "target_models": ["all"],
            "action_type": "display",
            "priority": 5,
            "field_type": "temporary",
            "archived": False,
        })

    return fields


def create_field_from_section(title: str, content: str, patterns: dict, auto_detect: bool) -> Optional[dict]:
    """ساخت فیلد از یک بخش"""
    import logging
    logger = logging.getLogger(__name__)

    if not title or not content.strip():
        return None

    # تنظیمات پیش‌فرض
    action_type = "display"
    priority = 5
    field_type = "temporary"
    target_path = None

    if auto_detect:
        # تشخیص نوع از محتوا
        combined_text = (title + " " + content).lower()

        for pattern_name, pattern_config in patterns.items():
            if any(kw in combined_text for kw in pattern_config["keywords"]):
                action_type = pattern_config["action_type"]
                priority = min(priority, pattern_config["priority"])
                field_type = pattern_config["field_type"]
                logger.info(f"[create_field] Detected pattern '{pattern_name}' -> action_type={action_type}")
                break

        # استخراج مسیر فایل - الگوهای بیشتر
        import re
        file_patterns = [
            r'(?:فایل|file|path|مسیر)[:\s]+[`"]?([^\s\n`"]+\.\w+)[`"]?',
            r'`([a-zA-Z0-9_/\\.-]+\.\w{2,4})`',
            r'(?:در|in|to)\s+[`"]?([a-zA-Z0-9_/\\.-]+\.(?:py|js|ts|tsx|jsx|json|yaml|yml|md|html|css|vue|svelte))[`"]?',
            r'([a-zA-Z0-9_/\\-]+/[a-zA-Z0-9_/\\-]+\.(?:py|js|ts|tsx|jsx|json|yaml|yml|md))',
        ]
        for pattern in file_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                target_path = match.group(1)
                logger.info(f"[create_field] Found target_path: {target_path}")
                break

        # اگر action_type کامیت هست ولی target_path نداریم، به display تغییر بده
        if action_type in ["github_commit", "file_edit"] and not target_path:
            logger.warning(f"[create_field] No target_path found for {action_type}, changing to display")
            action_type = "display"

    return {
        "name": title[:100],
        "value": content[:2000],
        "target_models": ["all"],
        "action_type": action_type,
        "target_path": target_path,
        "priority": priority,
        "field_type": field_type,
        "archived": False,
        "archive_after_run": True,  # 🔴 همیشه بایگانی بشه بعد از اجرا
        "trigger": {
            "enabled": False,
            "interval_minutes": 60,
            "interval_type": "minutes",
        },
    }


# =====================================
# مدیریت تریگرها
# =====================================

@router.post("/{project_id}/memory/fields/{field_id}/trigger/toggle")
async def toggle_field_trigger(
    project_id: str,
    field_id: str,
    enabled: bool,
    db: Session = Depends(get_db)
):
    """
    روشن/خاموش کردن تریگر یک فیلد
    """
    from datetime import datetime, timedelta

    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="پروژه یافت نشد")

    dynamic_fields = []
    try:
        if project.dynamic_fields:
            dynamic_fields = json.loads(project.dynamic_fields)
    except (json.JSONDecodeError, TypeError):
        pass

    field_found = False
    for field in dynamic_fields:
        if field["id"] == field_id:
            if "trigger" not in field:
                field["trigger"] = {"enabled": False, "interval_minutes": 60, "interval_type": "minutes"}

            field["trigger"]["enabled"] = enabled

            # اگر فعال شد، زمان اجرای بعدی را محاسبه کن
            if enabled:
                interval = field["trigger"].get("interval_minutes", 60)
                interval_type = field["trigger"].get("interval_type", "minutes")

                if interval_type == "hours":
                    next_run = datetime.utcnow() + timedelta(hours=interval)
                elif interval_type == "days":
                    next_run = datetime.utcnow() + timedelta(days=interval)
                else:
                    next_run = datetime.utcnow() + timedelta(minutes=interval)

                field["trigger"]["next_run"] = next_run.isoformat()
            else:
                field["trigger"]["next_run"] = None

            field_found = True
            break

    if not field_found:
        raise HTTPException(status_code=404, detail="فیلد یافت نشد")

    project.dynamic_fields = json.dumps(dynamic_fields, ensure_ascii=False)
    db.commit()

    return {
        "success": True,
        "enabled": enabled,
        "message": "تریگر فعال شد" if enabled else "تریگر غیرفعال شد"
    }


@router.get("/{project_id}/memory/fields/{field_id}/dependencies")
async def get_field_dependencies(
    project_id: str,
    field_id: str,
    db: Session = Depends(get_db)
):
    """
    بررسی وضعیت وابستگی‌های یک فیلد
    """
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="پروژه یافت نشد")

    dynamic_fields = []
    try:
        if project.dynamic_fields:
            dynamic_fields = json.loads(project.dynamic_fields)
    except:
        pass

    target_field = None
    for field in dynamic_fields:
        if field.get("id") == field_id:
            target_field = field
            break

    if not target_field:
        raise HTTPException(status_code=404, detail="فیلد یافت نشد")

    dep_check = check_field_dependencies(target_field, dynamic_fields)

    # اطلاعات کامل وابستگی‌ها
    depends_on_details = []
    blocked_by_details = []
    field_map = {f.get("id"): f for f in dynamic_fields}

    for dep_id in (target_field.get("depends_on") or []):
        dep_field = field_map.get(dep_id)
        if dep_field:
            depends_on_details.append({
                "id": dep_id,
                "name": dep_field.get("name"),
                "archived": dep_field.get("archived", False),
                "status": "completed" if dep_field.get("archived") else "pending"
            })

    for block_id in (target_field.get("blocked_by") or []):
        block_field = field_map.get(block_id)
        if block_field:
            blocked_by_details.append({
                "id": block_id,
                "name": block_field.get("name"),
                "archived": block_field.get("archived", False),
                "status": "cleared" if block_field.get("archived") else "blocking"
            })

    return {
        "success": True,
        "field_id": field_id,
        "field_name": target_field.get("name"),
        "can_execute": dep_check["can_execute"],
        "depends_on": depends_on_details,
        "blocked_by": blocked_by_details,
        "pending_dependencies": dep_check["pending_dependencies"],
        "blocking_fields": dep_check["blocking_fields"],
        "message": dep_check.get("message")
    }


@router.post("/{project_id}/memory/fields/{field_id}/preview")
async def preview_field_changes(
    project_id: str,
    field_id: str,
    db: Session = Depends(get_db)
):
    """
    پیش‌نمایش تغییراتی که فیلد ایجاد می‌کند (Diff View)
    بدون اجرای واقعی یا commit
    """
    import re
    from ...services.ai_manager import get_ai_manager
    from ...services.ai_base import Message
    from ...models.project import ProjectFile

    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="پروژه یافت نشد")

    dynamic_fields = []
    try:
        if project.dynamic_fields:
            dynamic_fields = json.loads(project.dynamic_fields)
    except:
        pass

    target_field = None
    for field in dynamic_fields:
        if field.get("id") == field_id:
            target_field = field
            break

    if not target_field:
        raise HTTPException(status_code=404, detail="فیلد یافت نشد")

    action_type = target_field.get("action_type", "display")
    target_path = target_field.get("target_path")

    # دریافت محتوای فعلی فایل هدف
    original_content = ""
    if target_path:
        file = db.query(ProjectFile).filter(
            ProjectFile.project_id == project_id,
            ProjectFile.path == target_path
        ).first()
        if file:
            original_content = file.content or ""

    # ساخت prompt برای AI
    system_prompt = f"تو یک دستیار هوشمند برای پروژه '{project.name}' هستی."
    if project.description:
        system_prompt += f"\nتوضیحات پروژه: {project.description}"

    if original_content:
        system_prompt += f"\n\n=== محتوای فعلی فایل {target_path} ===\n```\n{original_content}\n```"

    if action_type in ["github_commit", "github_multi_commit"]:
        system_prompt += "\n\n⚠️ کد کامل فایل را تولید کن (نه فقط تغییرات)."
        if action_type == "github_commit" and target_path:
            system_prompt += f"\nفایل هدف: {target_path}"
            system_prompt += "\nفقط محتوای کد را بدون توضیحات اضافی تولید کن."
        else:
            system_prompt += "\nبرای هر فایل از این فرمت استفاده کن:"
            system_prompt += "\n```language:path/to/file.ext\nکد\n```"

    user_prompt = f"دستور: {target_field.get('name', 'فیلد')}\n\n{target_field.get('value', '')}"

    # ارسال به AI
    ai_manager = get_ai_manager()
    target_models = target_field.get("target_models", ["claude"])
    if "all" in target_models:
        target_models = ["claude"]

    try:
        messages = [
            Message(role="system", content=system_prompt),
            Message(role="user", content=user_prompt),
        ]

        response = await asyncio.wait_for(
            ai_manager.generate(
                model_id=target_models[0],
                messages=messages,
                max_tokens=8192,
                temperature=0.7,
            ),
            timeout=120.0
        )

        new_content = response.content

        # استخراج کد از پاسخ
        if action_type == "github_commit":
            code_match = re.search(r'```\w*\n?(.*?)```', new_content, re.DOTALL)
            if code_match:
                new_content = code_match.group(1).strip()

        # تولید diff
        original_lines = original_content.splitlines(keepends=True) if original_content else []
        new_lines = new_content.splitlines(keepends=True) if new_content else []

        diff_generator = difflib.unified_diff(
            original_lines,
            new_lines,
            fromfile=f"a/{target_path or 'original'}",
            tofile=f"b/{target_path or 'modified'}",
            lineterm=""
        )
        diff_text = "".join(diff_generator)

        # تولید HTML diff برای نمایش رنگی
        html_diff = difflib.HtmlDiff()
        html_table = html_diff.make_table(
            original_lines,
            new_lines,
            fromdesc="قبل",
            todesc="بعد",
            context=True,
            numlines=3
        )

        # استخراج فایل‌های چندگانه برای multi_commit
        file_changes = []
        if action_type == "github_multi_commit":
            blocks = re.findall(r'```(\w+)?:([^\n]+)\n(.*?)```', response.content, re.DOTALL)
            for lang, path, code in blocks:
                # دریافت محتوای فعلی این فایل
                file = db.query(ProjectFile).filter(
                    ProjectFile.project_id == project_id,
                    ProjectFile.path == path.strip()
                ).first()
                orig = file.content if file else ""

                orig_lines = orig.splitlines(keepends=True) if orig else []
                code_lines = code.strip().splitlines(keepends=True) if code else []

                file_diff = "".join(difflib.unified_diff(
                    orig_lines,
                    code_lines,
                    fromfile=f"a/{path.strip()}",
                    tofile=f"b/{path.strip()}",
                    lineterm=""
                ))

                file_changes.append({
                    "path": path.strip(),
                    "language": lang or "text",
                    "original_content": orig[:1000] + "..." if len(orig) > 1000 else orig,
                    "new_content": code.strip()[:1000] + "..." if len(code.strip()) > 1000 else code.strip(),
                    "diff": file_diff,
                    "lines_added": sum(1 for l in file_diff.splitlines() if l.startswith("+")),
                    "lines_removed": sum(1 for l in file_diff.splitlines() if l.startswith("-")),
                })
        else:
            file_changes.append({
                "path": target_path or "unknown",
                "original_content": original_content[:1000] + "..." if len(original_content) > 1000 else original_content,
                "new_content": new_content[:1000] + "..." if len(new_content) > 1000 else new_content,
                "diff": diff_text,
                "lines_added": sum(1 for l in diff_text.splitlines() if l.startswith("+")),
                "lines_removed": sum(1 for l in diff_text.splitlines() if l.startswith("-")),
            })

        return {
            "success": True,
            "preview_mode": True,
            "field_id": field_id,
            "field_name": target_field.get("name"),
            "action_type": action_type,
            "file_changes": file_changes,
            "unified_diff": diff_text,
            "html_diff": html_table,
            "tokens_used": response.tokens_used,
            "warning": "این پیش‌نمایش است و هیچ تغییری اعمال نشده است. برای اعمال تغییرات از دکمه اجرا استفاده کنید."
        }

    except asyncio.TimeoutError:
        raise HTTPException(status_code=504, detail="زمان پاسخگویی مدل بیش از حد طول کشید")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"خطا در تولید پیش‌نمایش: {str(e)}")


@router.post("/{project_id}/memory/fields/{field_id}/trigger/execute")
async def execute_field_trigger(
    project_id: str,
    field_id: str,
    db: Session = Depends(get_db)
):
    """
    اجرای دستی یک تریگر (بدون انتظار برای زمان‌بندی)
    با قابلیت commit به GitHub و بایگانی خودکار
    """
    from datetime import datetime
    from ...services.ai_manager import get_ai_manager
    from ...services.ai_base import Message
    import asyncio

    try:
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            raise HTTPException(status_code=404, detail="پروژه یافت نشد")

        dynamic_fields = []
        try:
            if project.dynamic_fields:
                dynamic_fields = json.loads(project.dynamic_fields)
        except (json.JSONDecodeError, TypeError):
            pass

        target_field = None
        target_field_index = None
        for idx, field in enumerate(dynamic_fields):
            if field.get("id") == field_id:
                target_field = field
                target_field_index = idx
                break

        if not target_field:
            raise HTTPException(status_code=404, detail="فیلد یافت نشد")

        # بررسی بایگانی بودن
        if target_field.get("archived"):
            raise HTTPException(status_code=400, detail="این فیلد بایگانی شده و قابل اجرا نیست")

        # 🆕 بررسی وابستگی‌های فیلد
        dep_check = check_field_dependencies(target_field, dynamic_fields)
        if not dep_check["can_execute"]:
            raise HTTPException(
                status_code=409,
                detail=dep_check["message"],
                headers={"X-Dependency-Error": "true"}
            )

        # 🔴 جلوگیری از دور باطل - بررسی اجرای تکراری
        try:
            from .project_journal import check_cycle_prevention
            if not check_cycle_prevention(
                db=db,
                project_id=project_id,
                activity_type="field_execution",
                field_id=field_id,
                minutes_threshold=3  # حداقل 3 دقیقه بین اجراها
            ):
                raise HTTPException(
                    status_code=429,
                    detail="این فیلد اخیراً اجرا شده است. لطفاً چند دقیقه صبر کنید."
                )
        except ImportError:
            pass  # اگر ایمپورت ناموفق بود، ادامه بده

        # 🔴 بررسی تاییدیه گزارش مهندسی - فقط فیلدهای تایید شده قابل اجرا هستند
        action_type = target_field.get("action_type", "display")
        if action_type in ["github_commit", "github_multi_commit", "file_edit"]:
            engineering_approval = target_field.get("engineering_approval", {})
            validation_marker = target_field.get("validation_marker")

            # فیلدهای اقدام‌محور باید تاییدیه داشته باشند
            if not engineering_approval.get("approved") and validation_marker not in ["validated", "approved"]:
                # بررسی آیا فیلد از گزارش مهندسی آمده (این‌ها به طور پیش‌فرض تایید شده‌اند)
                if not target_field.get("created_from_report"):
                    raise HTTPException(
                        status_code=403,
                        detail="این فیلد تاییدیه گزارش مهندسی ندارد. ابتدا گزارش مهندسی را اجرا کنید تا فیلدها تایید شوند."
                    )

        # دریافت تنظیمات GitHub از پروژه
        github_info = {}
        try:
            if project.extra_data:
                github_info = json.loads(project.extra_data)
        except:
            pass

        action_type = target_field.get("action_type", "display")
        target_path = target_field.get("target_path")
        archive_after_run = target_field.get("archive_after_run", False)

        # ============ دریافت فایل‌های پروژه برای context ============
        from ...models.project import ProjectFile
        from .settings import get_ai_limits_sync

        project_files_context = ""
        try:
            # دریافت تنظیمات محدودیت‌ها
            ai_limits = get_ai_limits_sync(db)
            limits_enabled = ai_limits.get("limits_enabled", False)

            # مقادیر محدودیت (0 = نامحدود)
            max_files = ai_limits.get("max_files_for_context", 0) if limits_enabled else 0
            max_chars_per_file = ai_limits.get("max_chars_per_file", 0) if limits_enabled else 0
            max_total_chars = ai_limits.get("max_total_context_chars", 0) if limits_enabled else 0

            # دریافت فایل‌های پروژه
            files = db.query(ProjectFile).filter(ProjectFile.project_id == project_id).all()

            if files:
                # اگر target_path مشخص شده، اول اون فایل رو بخون
                target_file_content = None
                if target_path:
                    for f in files:
                        if f.file_path == target_path or f.file_path.endswith(target_path):
                            target_file_content = f.content
                            break

                # ساخت context از فایل‌های مرتبط
                relevant_files = []
                total_chars = 0

                # اولویت: فایل هدف (بدون محدودیت)
                if target_file_content and target_path:
                    content = target_file_content if max_chars_per_file == 0 else target_file_content[:max_chars_per_file]
                    relevant_files.append({
                        "path": target_path,
                        "content": content
                    })
                    total_chars += len(content)

                # بقیه فایل‌های کد
                code_extensions = ['py', 'ts', 'tsx', 'js', 'jsx', 'java', 'go', 'rs', 'rb', 'php', 'vue', 'svelte']

                # اولویت‌بندی فایل‌ها بر اساس اهمیت
                priority_keywords = ['auth', 'login', 'user', 'route', 'api', 'main', 'app', 'index', 'config', 'model', 'service']

                def file_score(f):
                    score = 0
                    name = f.file_path.lower()
                    for kw in priority_keywords:
                        if kw in name:
                            score += 10
                    return score

                sorted_files = sorted(files, key=file_score, reverse=True)

                files_added = 1 if target_file_content else 0
                for f in sorted_files:
                    # چک محدودیت تعداد فایل (0 = نامحدود)
                    if max_files > 0 and files_added >= max_files:
                        break
                    # چک محدودیت کل کاراکترها (0 = نامحدود)
                    if max_total_chars > 0 and total_chars >= max_total_chars:
                        break
                    if f.file_path == target_path:  # قبلاً اضافه شده
                        continue
                    if f.content and f.file_type in code_extensions:
                        # اگر محدودیت فعال نیست، همه محتوا رو بگیر
                        content = f.content if max_chars_per_file == 0 else f.content[:max_chars_per_file]
                        relevant_files.append({
                            "path": f.file_path,
                            "content": content
                        })
                        total_chars += len(content)
                        files_added += 1

                # ساخت متن context (بدون محدودیت تعداد در خروجی)
                if relevant_files:
                    project_files_context = f"\n\n=== فایل‌های پروژه ({len(relevant_files)} فایل، {total_chars:,} کاراکتر) ===\n"
                    for rf in relevant_files:
                        project_files_context += f"\n--- {rf['path']} ---\n```\n{rf['content']}\n```\n"
        except Exception as e:
            project_files_context = f"\n\n[خطا در خواندن فایل‌های پروژه: {str(e)}]"

        # ساخت prompt از دستور فیلد
        system_prompt = f"تو یک دستیار هوشمند برای پروژه '{project.name}' هستی."
        if project.description:
            system_prompt += f"\nتوضیحات پروژه: {project.description}"

        # اضافه کردن فایل‌های پروژه به context
        if project_files_context:
            system_prompt += project_files_context

        # اضافه کردن دستورات حافظه به system prompt
        try:
            if project.memory_instructions:
                memory = json.loads(project.memory_instructions)
                if memory.get("content"):
                    system_prompt += f"\n\nدستورات کلی:\n{memory['content']}"
        except:
            pass

        # برای commit به GitHub، دستورات اضافی
        if action_type in ["github_commit", "github_multi_commit"]:
            system_prompt += "\n\n⚠️ مهم: کد تولید شده مستقیماً در ریپو commit می‌شود."
            if action_type == "github_commit" and target_path:
                system_prompt += f"\nفایل هدف: {target_path}"
                system_prompt += "\nفقط محتوای کد را بدون توضیحات اضافی تولید کن."
            else:
                system_prompt += "\nبرای هر فایل از این فرمت استفاده کن:"
                system_prompt += "\n```language:path/to/file.ext\nکد\n```"

        user_prompt = f"دستور: {target_field.get('name', 'فیلد')}\n\n{target_field.get('value', '')}"

        # ارسال به مدل(های) هدف
        target_models = target_field.get("target_models", ["all"])
        if "all" in target_models or not target_models:
            target_models = ["claude"]  # پیش‌فرض claude بهتره برای کد

        results = []
        github_commits = []
        ai_manager = get_ai_manager()

        for model_id in target_models:
            if model_id == "all":
                continue

            start_time = time.time()
            try:
                messages = [
                    Message(role="system", content=system_prompt),
                    Message(role="user", content=user_prompt),
                ]

                # اجرا با timeout 120 ثانیه برای تولید کد بیشتر
                response = await asyncio.wait_for(
                    ai_manager.generate(
                        model_id=model_id,
                        messages=messages,
                        max_tokens=8192,  # افزایش برای کد بیشتر
                        temperature=0.7,
                    ),
                    timeout=120.0
                )

                latency_ms = int((time.time() - start_time) * 1000)

                result = {
                    "model_id": response.model_id,
                    "content": response.content,
                    "tokens_used": response.tokens_used,
                    "success": True
                }

                # اگر action_type برای GitHub است، commit کن
                if action_type in ["github_commit", "github_multi_commit"] and response.content:
                    if github_info.get("source") == "github":
                        owner = github_info.get("owner")
                        repo = github_info.get("repo")
                        # 🔴 بارگذاری توکن از environment یا database
                        token = os.getenv("GITHUB_TOKEN", "")
                        if not token:
                            from ...models.setting import Setting
                            try:
                                token = Setting.get_value(db, "api_key_github") or ""
                                if token:
                                    os.environ["GITHUB_TOKEN"] = token
                            except:
                                pass

                        if owner and repo and token:
                            if action_type == "github_commit" and target_path:
                                # یک فایل مشخص
                                # استخراج محتوای کد از پاسخ (حذف markdown)
                                code_content = response.content
                                # حذف بلوک‌های markdown
                                code_match = re.search(r'```\w*\n?(.*?)```', code_content, re.DOTALL)
                                if code_match:
                                    code_content = code_match.group(1)

                                commit_result = await commit_to_github(
                                    owner=owner,
                                    repo=repo,
                                    token=token,
                                    file_path=target_path,
                                    content=code_content.strip(),
                                    message=f"AI Generated: {target_field.get('name', 'Update')}",
                                    branch=github_info.get("branch", "main")
                                )
                                github_commits.append(commit_result)

                            elif action_type == "github_multi_commit":
                                # چند فایل از پاسخ
                                code_blocks = await extract_code_blocks(response.content)
                                for block in code_blocks:
                                    commit_result = await commit_to_github(
                                        owner=owner,
                                        repo=repo,
                                        token=token,
                                        file_path=block["path"],
                                        content=block["content"],
                                        message=f"AI Generated: {block['path']}",
                                        branch=github_info.get("branch", "main")
                                    )
                                    github_commits.append(commit_result)

                            result["github_commits"] = github_commits
                        else:
                            result["github_error"] = "اطلاعات GitHub ناقص است"
                    else:
                        result["github_error"] = "این پروژه از GitHub ایمپورت نشده"

                results.append(result)

                # ثبت در ژورنال - موفق
                extra_data = None
                if github_commits:
                    extra_data = json.dumps({"github_commits": github_commits}, ensure_ascii=False)

                log_entry = ActivityLog(
                    id=f"log_{uuid.uuid4().hex[:12]}",
                    project_id=project_id,
                    model_id=response.model_id,
                    model_provider=model_id.split("-")[0] if "-" in model_id else model_id,
                    activity_type="trigger",
                    prompt=user_prompt[:10000],  # افزایش محدودیت برای گزارش کامل‌تر
                    response=response.content,  # بدون محدودیت - گزارش کامل ذخیره شود
                    tokens_used=response.tokens_used or 0,
                    latency_ms=latency_ms,
                    success=True,
                    field_id=field_id,
                    field_name=target_field.get("name"),
                    extra_data=extra_data,
                    created_at=datetime.utcnow(),
                )
                db.add(log_entry)

            except asyncio.TimeoutError:
                latency_ms = int((time.time() - start_time) * 1000)
                results.append({
                    "model_id": model_id,
                    "error": "Timeout - پاسخ مدل بیش از 120 ثانیه طول کشید",
                    "success": False
                })

                log_entry = ActivityLog(
                    id=f"log_{uuid.uuid4().hex[:12]}",
                    project_id=project_id,
                    model_id=model_id,
                    activity_type="trigger",
                    prompt=user_prompt[:10000],
                    tokens_used=0,
                    latency_ms=latency_ms,
                    success=False,
                    error_message="Timeout - پاسخ مدل بیش از 120 ثانیه طول کشید",
                    field_id=field_id,
                    field_name=target_field.get("name"),
                    created_at=datetime.utcnow(),
                )
                db.add(log_entry)

            except Exception as e:
                latency_ms = int((time.time() - start_time) * 1000)
                results.append({
                    "model_id": model_id,
                    "error": str(e),
                    "success": False
                })

                log_entry = ActivityLog(
                    id=f"log_{uuid.uuid4().hex[:12]}",
                    project_id=project_id,
                    model_id=model_id,
                    activity_type="trigger",
                    prompt=user_prompt[:10000],
                    tokens_used=0,
                    latency_ms=latency_ms,
                    success=False,
                    error_message=str(e)[:500],
                    field_id=field_id,
                    field_name=target_field.get("name"),
                    created_at=datetime.utcnow(),
                )
                db.add(log_entry)

        # بروزرسانی فیلد
        any_success = any(r.get("success") for r in results)
        any_github_success = any(c.get("success") for c in github_commits) if github_commits else False

        # Trigger Render deploy اگر فعال باشد و commit موفق بوده
        deploy_result = None
        deploy_after_commit = target_field.get("deploy_after_commit", False)

        if deploy_after_commit and any_github_success:
            try:
                render_service_id = github_info.get("render_service_id")
                deploy_result = await trigger_render_deploy(
                    render_service_id=render_service_id,
                    project_id=project_id,
                    db_session=db
                )
            except Exception as e:
                deploy_result = {"success": False, "error": str(e)}

        for field in dynamic_fields:
            if field.get("id") == field_id:
                if "trigger" not in field:
                    field["trigger"] = {}
                field["trigger"]["last_run"] = datetime.utcnow().isoformat()
                field["executed"] = True  # 🔴 علامت اجرا شده

                # بایگانی خودکار اگر موفق و تنظیم شده
                if archive_after_run and any_success:
                    if action_type == "display" or any_github_success:
                        field["archived"] = True
                        field["archived_at"] = datetime.utcnow().isoformat()
                        field["archived_reason"] = "auto_archive_after_execution"

                        # 🔴 ثبت بایگانی در ژورنال
                        from .project_journal import ActivityLog
                        archive_log = ActivityLog(
                            id=f"log_{uuid.uuid4().hex[:12]}",
                            project_id=project_id,
                            model_id="system",
                            model_provider="auto-archive",
                            activity_type="field_archived",
                            prompt=f"بایگانی خودکار فیلد: {target_field.get('name')}",
                            response=f"فیلد '{target_field.get('name')}' پس از اجرای موفق بایگانی شد.",
                            tokens_used=0,
                            latency_ms=0,
                            success=True,
                            field_id=field_id,
                            field_name=target_field.get("name"),
                            extra_data=json.dumps({
                                "action_type": action_type,
                                "github_success": any_github_success,
                                "archived_at": field["archived_at"],
                                "clickable": True
                            }, ensure_ascii=False),
                            created_at=datetime.utcnow(),
                        )
                        db.add(archive_log)
                break

        project.dynamic_fields = json.dumps(dynamic_fields, ensure_ascii=False)
        db.commit()

        return {
            "success": True,
            "field_id": field_id,
            "field_name": target_field.get("name"),
            "action_type": action_type,
            "results": results,
            "github_commits": github_commits if github_commits else None,
            "deploy_result": deploy_result,
            "archived": target_field.get("archived", False),
            "executed_at": datetime.utcnow().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "field_id": field_id
        }


# =====================================
# بایگانی فیلدها
# =====================================

@router.post("/{project_id}/memory/fields/{field_id}/archive")
async def archive_field(
    project_id: str,
    field_id: str,
    db: Session = Depends(get_db)
):
    """بایگانی یک فیلد"""
    from datetime import datetime

    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="پروژه یافت نشد")

    dynamic_fields = []
    try:
        if project.dynamic_fields:
            dynamic_fields = json.loads(project.dynamic_fields)
    except:
        pass

    field_found = False
    for field in dynamic_fields:
        if field.get("id") == field_id:
            field["archived"] = True
            field["archived_at"] = datetime.utcnow().isoformat()
            field_found = True
            break

    if not field_found:
        raise HTTPException(status_code=404, detail="فیلد یافت نشد")

    project.dynamic_fields = json.dumps(dynamic_fields, ensure_ascii=False)
    db.commit()

    return {"success": True, "message": "فیلد بایگانی شد"}


@router.post("/{project_id}/memory/fields/{field_id}/unarchive")
async def unarchive_field(
    project_id: str,
    field_id: str,
    db: Session = Depends(get_db)
):
    """خروج از بایگانی"""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="پروژه یافت نشد")

    dynamic_fields = []
    try:
        if project.dynamic_fields:
            dynamic_fields = json.loads(project.dynamic_fields)
    except:
        pass

    field_found = False
    for field in dynamic_fields:
        if field.get("id") == field_id:
            field["archived"] = False
            field.pop("archived_at", None)
            field_found = True
            break

    if not field_found:
        raise HTTPException(status_code=404, detail="فیلد یافت نشد")

    project.dynamic_fields = json.dumps(dynamic_fields, ensure_ascii=False)
    db.commit()

    return {"success": True, "message": "فیلد از بایگانی خارج شد"}


@router.get("/{project_id}/memory/fields/archived")
async def get_archived_fields(
    project_id: str,
    db: Session = Depends(get_db)
):
    """دریافت فیلدهای بایگانی شده"""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="پروژه یافت نشد")

    dynamic_fields = []
    try:
        if project.dynamic_fields:
            dynamic_fields = json.loads(project.dynamic_fields)
    except:
        pass

    archived = [f for f in dynamic_fields if f.get("archived")]

    return {
        "success": True,
        "archived_fields": archived,
        "count": len(archived)
    }


@router.get("/{project_id}/memory/action-types")
async def get_action_types():
    """دریافت لیست انواع اکشن برای فیلدها"""
    return {
        "success": True,
        "action_types": ACTION_TYPES
    }


# =====================================
# 🆕 انواع فیلد و اولویت‌ها
# =====================================

@router.get("/{project_id}/memory/field-types")
async def get_field_types():
    """دریافت لیست انواع فیلد (دائمی/موقت)"""
    return {
        "success": True,
        "field_types": FIELD_TYPES,
        "priority_levels": PRIORITY_LEVELS
    }


@router.get("/{project_id}/memory/fields/by-type")
async def get_fields_by_type(
    project_id: str,
    field_type: Optional[str] = None,  # permanent, temporary, all
    include_archived: bool = False,
    sort_by_priority: bool = True,
    db: Session = Depends(get_db)
):
    """
    دریافت فیلدها براساس نوع با امکان فیلتر و مرتب‌سازی
    """
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="پروژه یافت نشد")

    dynamic_fields = []
    try:
        if project.dynamic_fields:
            dynamic_fields = json.loads(project.dynamic_fields)
    except:
        pass

    # فیلتر بر اساس نوع
    if field_type and field_type != "all":
        dynamic_fields = [f for f in dynamic_fields if f.get("field_type") == field_type]

    # فیلتر بایگانی
    if not include_archived:
        dynamic_fields = [f for f in dynamic_fields if not f.get("archived")]

    # مرتب‌سازی بر اساس اولویت
    if sort_by_priority:
        dynamic_fields.sort(key=lambda x: int(x.get("priority", 5)) if str(x.get("priority", 5)).isdigit() else 5)

    # گروه‌بندی
    permanent_fields = [f for f in dynamic_fields if f.get("field_type") == "permanent"]
    temporary_fields = [f for f in dynamic_fields if f.get("field_type") == "temporary"]
    other_fields = [f for f in dynamic_fields if f.get("field_type") not in ["permanent", "temporary"]]

    return {
        "success": True,
        "all_fields": dynamic_fields,
        "permanent_fields": permanent_fields,
        "temporary_fields": temporary_fields,
        "other_fields": other_fields,
        "counts": {
            "total": len(dynamic_fields),
            "permanent": len(permanent_fields),
            "temporary": len(temporary_fields),
            "other": len(other_fields)
        }
    }


# =====================================
# 🆕 اجرای گروهی فیلدها با اولویت‌بندی
# =====================================

@router.post("/{project_id}/memory/fields/batch-execute")
async def batch_execute_fields(
    project_id: str,
    request: BatchExecuteRequest,
    db: Session = Depends(get_db)
):
    """
    اجرای گروهی فیلدها با اولویت‌بندی هوشمند
    - execute_type: "selected" (فیلدهای انتخاب شده), "all", "permanent", "temporary"
    - auto_prioritize: مرتب‌سازی خودکار براساس اولویت
    """
    from datetime import datetime
    from ...services.ai_manager import get_ai_manager
    from ...services.ai_base import Message
    import asyncio

    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="پروژه یافت نشد")

    dynamic_fields = []
    try:
        if project.dynamic_fields:
            dynamic_fields = json.loads(project.dynamic_fields)
    except:
        pass

    # فیلتر فیلدهای غیربایگانی
    active_fields = [f for f in dynamic_fields if not f.get("archived")]

    # 🔴 لاگ برای دیباگ
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"[Batch Execute] Project: {project_id}")
    logger.info(f"[Batch Execute] Total fields: {len(dynamic_fields)}, Active: {len(active_fields)}")
    logger.info(f"[Batch Execute] Request: execute_type={request.execute_type}, field_ids={request.field_ids[:5] if request.field_ids else []}")
    available_ids = [f.get("id") for f in active_fields]
    logger.info(f"[Batch Execute] Available field IDs: {available_ids[:5]}")

    # انتخاب فیلدها برای اجرا
    fields_to_execute = []

    if request.execute_type == "all":
        fields_to_execute = active_fields
    elif request.execute_type == "permanent":
        fields_to_execute = [f for f in active_fields if f.get("field_type") == "permanent"]
    elif request.execute_type == "temporary":
        fields_to_execute = [f for f in active_fields if f.get("field_type") == "temporary"]
    elif request.execute_type == "selected":
        fields_to_execute = [f for f in active_fields if f.get("id") in request.field_ids]
        logger.info(f"[Batch Execute] Selected mode - matched {len(fields_to_execute)} fields")

    if not fields_to_execute:
        logger.warning(f"[Batch Execute] No fields to execute! active={len(active_fields)}, requested_ids={request.field_ids}")
        return {
            "success": False,
            "error": "هیچ فیلدی برای اجرا انتخاب نشده",
            "executed_count": 0,
            "debug": {
                "total_fields": len(dynamic_fields),
                "active_fields": len(active_fields),
                "requested_ids": request.field_ids[:5] if request.field_ids else [],
                "available_ids": available_ids[:10]
            }
        }

    # مرتب‌سازی براساس اولویت (1 = بالاترین اولویت)
    if request.auto_prioritize:
        fields_to_execute.sort(key=lambda x: int(x.get("priority", 5)) if str(x.get("priority", 5)).isdigit() else 5)

    logger.info(f"[Batch Execute] About to start loop with {len(fields_to_execute)} fields")

    # 🔴 مدیریت وضعیت اجرا
    state = get_execution_state(project_id)
    state["status"] = "running"
    state["total_fields"] = len(fields_to_execute)
    state["started_at"] = datetime.utcnow().isoformat()
    state["results"] = []

    # بررسی آیا باید از جای قبلی ادامه دهیم
    start_index = 0
    if request.execute_type == "resume" and state.get("current_index", 0) > 0:
        start_index = state["current_index"]
        logger.info(f"[Batch Execute] Resuming from index {start_index}")

    # اجرای ترتیبی فیلدها
    execution_results = []
    success_count = 0
    failed_count = 0
    github_success_count = 0
    archived_count = 0
    fields_to_archive = []  # لیست ID فیلدهایی که باید بایگانی شوند

    for idx, field in enumerate(fields_to_execute):
        # 🔴 بررسی وضعیت کنترل (pause/stop)
        current_state = get_execution_state(project_id)
        if current_state["status"] == "stopped":
            logger.info(f"[Batch Execute] Execution stopped by user at index {idx}")
            break
        while current_state["status"] == "paused":
            await asyncio.sleep(1)  # صبر کن تا resume شود
            current_state = get_execution_state(project_id)
            if current_state["status"] == "stopped":
                break

        if current_state["status"] == "stopped":
            break

        # 🔴 رد کردن فیلدهای قبلی در حالت resume
        if idx < start_index:
            continue

        state["current_index"] = idx
        state["last_field_id"] = field.get("id")

        logger.info(f"[Batch Execute] Loop iteration {idx+1}/{len(fields_to_execute)}: field={field.get('name')}, id={field.get('id')}")

        # 🔴 جلوگیری از دور باطل - بررسی اجرای تکراری برای هر فیلد
        try:
            from .project_journal import check_cycle_prevention
            if not check_cycle_prevention(
                db=db,
                project_id=project_id,
                activity_type="field_execution",
                field_id=field.get("id"),
                minutes_threshold=3
            ):
                logger.info(f"[Batch Execute] Skipping field {field.get('name')} - cycle prevention (recently executed)")
                results.append({
                    "field_id": field.get("id"),
                    "field_name": field.get("name"),
                    "success": False,
                    "error": "اخیراً اجرا شده - رد شد برای جلوگیری از تکرار",
                    "skipped_cycle": True
                })
                continue
        except ImportError:
            pass

        try:
            logger.info(f"[Batch Execute] Calling execute_field_internal for field: {field.get('name')}")
            # اجرای فیلد با قابلیت کامل (commit + deploy + archive)
            result = await execute_field_internal(
                project_id=project_id,
                field_id=field.get("id"),
                db=db,
                field_data=field,
                project=project
            )
            logger.info(f"[Batch Execute] execute_field_internal returned for {field.get('name')}: success={result.get('success')}")

            # 🔴 استخراج خطای GitHub از نتایج
            github_error = None
            if result.get("results"):
                for r in result.get("results", []):
                    if r.get("github_error"):
                        github_error = r.get("github_error")
                        break

            exec_result = {
                "field_id": field.get("id"),
                "field_name": field.get("name"),
                "priority": field.get("priority", 5),
                "field_type": field.get("field_type"),
                "action_type": field.get("action_type", "display"),
                "target_path": field.get("target_path"),  # 🔴 اضافه شد
                "success": result.get("success", False),
                "error": result.get("error"),
                "github_commits": result.get("github_commits"),
                "github_error": github_error,  # 🔴 خطای GitHub
                "deploy_result": result.get("deploy_result"),
            }

            if result.get("success"):
                success_count += 1
                # 🔴 بایگانی فوری بعد از هر فیلد موفق
                # اگر force_archive فعاله (پیش‌فرض) یا فیلد خودش should_archive داره
                should_archive_now = request.force_archive or result.get("should_archive")
                logger.info(f"[Batch Execute] Archive decision for {field.get('name')}: force_archive={request.force_archive}, should_archive={result.get('should_archive')}, final={should_archive_now}")

                if should_archive_now:
                    try:
                        # بروزرسانی فوری در دیتابیس
                        current_fields = json.loads(project.dynamic_fields) if project.dynamic_fields else []
                        for f in current_fields:
                            if f.get("id") == field.get("id"):
                                f["archived"] = True
                                f["archived_at"] = datetime.utcnow().isoformat()
                                f["executed"] = True
                                f["last_executed"] = datetime.utcnow().isoformat()
                                break
                        project.dynamic_fields = json.dumps(current_fields, ensure_ascii=False)
                        db.commit()
                        db.refresh(project)  # refresh برای گرفتن آخرین داده
                        exec_result["archived"] = True
                        archived_count += 1
                        logger.info(f"[Batch Execute] Field {field.get('name')} archived immediately ✅")
                    except Exception as archive_err:
                        logger.error(f"[Batch Execute] Failed to archive field {field.get('id')}: {archive_err}")
                        db.rollback()
                else:
                    # بروزرسانی زمان اجرا حتی اگر بایگانی نشد
                    try:
                        current_fields = json.loads(project.dynamic_fields) if project.dynamic_fields else []
                        for f in current_fields:
                            if f.get("id") == field.get("id"):
                                f["executed"] = True
                                f["last_executed"] = datetime.utcnow().isoformat()
                                if "trigger" not in f:
                                    f["trigger"] = {}
                                f["trigger"]["last_run"] = datetime.utcnow().isoformat()
                                break
                        project.dynamic_fields = json.dumps(current_fields, ensure_ascii=False)
                        db.commit()
                        db.refresh(project)
                    except:
                        db.rollback()

                # شمارش کامیت‌های موفق
                if result.get("any_github_success"):
                    github_success_count += 1
            else:
                failed_count += 1

            execution_results.append(exec_result)

            # 🔴 بروزرسانی state برای frontend (progress bar)
            state["completed_count"] = success_count
            state["failed_count"] = failed_count
            state["archived_count"] = archived_count
            state["current_field_name"] = field.get("name")
            state["last_update"] = datetime.utcnow().isoformat()

        except Exception as e:
            logger.error(f"[Batch Execute] Exception in field {field.get('name')}: {type(e).__name__}: {str(e)}")
            import traceback
            logger.error(f"[Batch Execute] Traceback: {traceback.format_exc()}")
            execution_results.append({
                "field_id": field.get("id"),
                "field_name": field.get("name"),
                "success": False,
                "error": str(e)
            })
            failed_count += 1

    logger.info(f"[Batch Execute] Loop completed: success={success_count}, failed={failed_count}, results={len(execution_results)}")

    # 🔴 بروزرسانی وضعیت نهایی
    state["status"] = "completed"
    state["results"] = execution_results
    state["completed_fields"] = [r["field_id"] for r in execution_results if r.get("success")]
    state["failed_fields"] = [r["field_id"] for r in execution_results if not r.get("success")]
    state["completed_at"] = datetime.utcnow().isoformat()

    # 🔴 بایگانی دیگر در اینجا انجام نمیشه - هر فیلد بلافاصله بایگانی شده

    return {
        "success": success_count > 0,
        "executed_count": len(fields_to_execute),
        "success_count": success_count,
        "failed_count": failed_count,
        "github_commits_count": github_success_count,
        "archived_count": archived_count,
        "results": execution_results,
        "execution_order": [f.get("name") for f in fields_to_execute],
        "executed_at": datetime.utcnow().isoformat()
    }


# =====================================
# 🆕 مدیریت اجرای پس‌زمینه
# =====================================

# وضعیت اجرای هر پروژه
_batch_execution_state = {}

def get_execution_state(project_id: str):
    """دریافت وضعیت اجرای پروژه"""
    if project_id not in _batch_execution_state:
        _batch_execution_state[project_id] = {
            "status": "idle",  # idle, running, paused, stopped
            "current_index": 0,
            "total_fields": 0,
            "completed_fields": [],
            "failed_fields": [],
            "results": [],
            "started_at": None,
            "last_field_id": None,
        }
    return _batch_execution_state[project_id]


@router.get("/{project_id}/memory/fields/batch-status")
async def get_batch_execution_status(project_id: str):
    """دریافت وضعیت اجرای گروهی - برای polling از frontend"""
    state = get_execution_state(project_id)

    # محاسبه progress با اطلاعات جدید
    completed = state.get("completed_count", len(state.get("completed_fields", [])))
    failed = state.get("failed_count", len(state.get("failed_fields", [])))
    total = state.get("total_fields", 0)
    current_idx = state.get("current_index", 0)

    progress = 0
    if total > 0:
        progress = round(((completed + failed) / total) * 100, 1)

    return {
        "success": True,
        "status": state.get("status", "idle"),
        "current_index": current_idx,
        "total_fields": total,
        "completed_count": completed,
        "failed_count": failed,
        "archived_count": state.get("archived_count", 0),
        "progress_percent": progress,
        "started_at": state.get("started_at"),
        "completed_at": state.get("completed_at"),
        "last_field_id": state.get("last_field_id"),
        "current_field_name": state.get("current_field_name"),
        "last_update": state.get("last_update"),
        "is_running": state.get("status") in ["running", "paused"],
    }


@router.post("/{project_id}/memory/fields/batch-control")
async def control_batch_execution(
    project_id: str,
    request: BatchControlRequest
):
    """کنترل اجرای گروهی (توقف موقت، از سرگیری، توقف کامل)"""
    state = get_execution_state(project_id)

    if request.action == "pause":
        if state["status"] == "running":
            state["status"] = "paused"
            return {"success": True, "message": "اجرا متوقف شد", "status": "paused"}
        return {"success": False, "message": "اجرایی در حال انجام نیست"}

    elif request.action == "resume":
        if state["status"] == "paused":
            state["status"] = "running"
            return {"success": True, "message": "اجرا از سر گرفته شد", "status": "running", "resume_from": state["current_index"]}
        return {"success": False, "message": "اجرا در حالت توقف نیست"}

    elif request.action == "stop":
        state["status"] = "stopped"
        return {"success": True, "message": "اجرا کاملاً متوقف شد", "status": "stopped"}

    return {"success": False, "message": "اقدام نامعتبر"}


@router.post("/{project_id}/memory/fields/batch-delete")
async def batch_delete_fields(
    project_id: str,
    request: BatchDeleteRequest,
    db: Session = Depends(get_db)
):
    """حذف گروهی فیلدها"""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="پروژه یافت نشد")

    dynamic_fields = []
    try:
        if project.dynamic_fields:
            dynamic_fields = json.loads(project.dynamic_fields)
    except:
        pass

    original_count = len(dynamic_fields)
    field_ids_to_delete = set(request.field_ids)

    # فیلتر کردن فیلدها (حذف فیلدهای انتخاب شده)
    remaining_fields = [f for f in dynamic_fields if f.get("id") not in field_ids_to_delete]
    deleted_count = original_count - len(remaining_fields)

    if deleted_count > 0:
        project.dynamic_fields = json.dumps(remaining_fields, ensure_ascii=False)
        db.commit()

    return {
        "success": True,
        "deleted_count": deleted_count,
        "remaining_count": len(remaining_fields),
        "message": f"{deleted_count} فیلد حذف شد"
    }


async def execute_field_internal(project_id: str, field_id: str, db: Session, field_data: dict, project: Project):
    """
    اجرای داخلی فیلد برای batch execution
    شامل تمام قابلیت‌های execute_field_trigger: کامیت GitHub، بایگانی، دیپلوی
    """
    from datetime import datetime
    from ...services.ai_manager import get_ai_manager
    from ...services.ai_base import Message
    from ...models.project import ProjectFile
    # ActivityLog is already imported at the top from project_journal
    import asyncio
    import re
    import logging
    logger = logging.getLogger(__name__)

    logger.info(f"[execute_field_internal] STARTED - field_id={field_id}, field_name={field_data.get('name')}")

    try:
        target_field = field_data

        # 🔴 بررسی تاییدیه گزارش مهندسی
        action_type = target_field.get("action_type", "display")
        if action_type in ["github_commit", "github_multi_commit", "file_edit"]:
            engineering_approval = target_field.get("engineering_approval", {})
            validation_marker = target_field.get("validation_marker")

            if not engineering_approval.get("approved") and validation_marker not in ["validated", "approved"]:
                if not target_field.get("created_from_report"):
                    logger.warning(f"[execute_field_internal] Field {field_id} lacks engineering approval, skipping")
                    return {
                        "success": False,
                        "field_id": field_id,
                        "error": "فیلد تاییدیه گزارش مهندسی ندارد",
                        "requires_approval": True
                    }

        # دریافت تنظیمات GitHub از پروژه
        github_info = {}
        try:
            if project.extra_data:
                github_info = json.loads(project.extra_data)
        except:
            pass

        action_type = target_field.get("action_type", "display")
        target_path = target_field.get("target_path")
        # 🔴 پیش‌فرض: فیلدهای temporary بعد از اجرای موفق بایگانی شوند
        field_type = target_field.get("field_type", "temporary")
        archive_after_run = target_field.get("archive_after_run", field_type == "temporary")
        deploy_after_commit = target_field.get("deploy_after_commit", False)

        # 🔴 لاگ برای دیباگ GitHub commit
        logger.info(f"[execute_field_internal] action_type={action_type}, target_path={target_path}")
        logger.info(f"[execute_field_internal] github_info: source={github_info.get('source')}, owner={github_info.get('owner')}, repo={github_info.get('repo')}")

        # دریافت فایل‌های پروژه برای context
        from .settings import get_ai_limits_sync
        project_files_context = ""
        target_file_content = None
        try:
            ai_limits = get_ai_limits_sync(db)
            limits_enabled = ai_limits.get("limits_enabled", False)

            max_files = ai_limits.get("max_files_for_context", 0) if limits_enabled else 0
            max_chars_per_file = ai_limits.get("max_chars_per_file", 0) if limits_enabled else 0
            max_total_chars = ai_limits.get("max_total_context_chars", 0) if limits_enabled else 0

            files = db.query(ProjectFile).filter(ProjectFile.project_id == project_id).all()
            if files:
                # خواندن فایل هدف اگر موجود باشد
                if target_path:
                    for f in files:
                        if f.file_path == target_path or f.file_path.endswith(target_path):
                            target_file_content = f.content
                            break

                relevant_files = []
                total_chars = 0

                # اضافه کردن فایل هدف
                if target_file_content and target_path:
                    content = target_file_content if max_chars_per_file == 0 else target_file_content[:max_chars_per_file]
                    relevant_files.append({"path": target_path, "content": content})
                    total_chars += len(content)

                priority_keywords = ['auth', 'login', 'user', 'route', 'api', 'main', 'app', 'index', 'config']
                code_extensions = ['py', 'ts', 'tsx', 'js', 'jsx', 'vue', 'svelte', 'java', 'go', 'rs', 'rb', 'php']

                def file_score(f):
                    score = 0
                    name = f.file_path.lower()
                    for kw in priority_keywords:
                        if kw in name:
                            score += 10
                    return score

                sorted_files = sorted(files, key=file_score, reverse=True)

                files_added = 1 if target_file_content else 0
                for f in sorted_files:
                    if max_files > 0 and files_added >= max_files:
                        break
                    if max_total_chars > 0 and total_chars >= max_total_chars:
                        break
                    if f.file_path == target_path:
                        continue
                    if f.content and f.file_type in code_extensions:
                        content = f.content if max_chars_per_file == 0 else f.content[:max_chars_per_file]
                        relevant_files.append({"path": f.file_path, "content": content})
                        total_chars += len(content)
                        files_added += 1

                if relevant_files:
                    project_files_context = f"\n\n=== فایل‌های پروژه ({len(relevant_files)} فایل) ===\n"
                    for rf in relevant_files:
                        project_files_context += f"\n--- {rf['path']} ---\n```\n{rf['content']}\n```\n"
        except:
            pass

        # ساخت prompt
        system_prompt = f"تو یک دستیار هوشمند برای پروژه '{project.name}' هستی."
        if project.description:
            system_prompt += f"\nتوضیحات پروژه: {project.description}"
        if project_files_context:
            system_prompt += project_files_context

        # دستورات حافظه
        try:
            if project.memory_instructions:
                memory = json.loads(project.memory_instructions)
                if memory.get("content"):
                    system_prompt += f"\n\nدستورات کلی:\n{memory['content']}"
        except:
            pass

        # دستورات خاص برای GitHub commit
        if action_type in ["github_commit", "github_multi_commit"]:
            system_prompt += "\n\n⚠️ مهم: کد تولید شده مستقیماً در ریپو commit می‌شود."
            if action_type == "github_commit" and target_path:
                system_prompt += f"\nفایل هدف: {target_path}"
                system_prompt += "\nفقط محتوای کد را بدون توضیحات اضافی تولید کن."
            else:
                system_prompt += "\nبرای هر فایل از این فرمت استفاده کن:"
                system_prompt += "\n```language:path/to/file.ext\nکد\n```"

        # اضافه کردن پیوست‌ها
        attachments = target_field.get("attachments", [])
        if attachments:
            system_prompt += "\n\n=== پیوست‌ها ===\n"
            for att in attachments:
                if isinstance(att, dict):
                    system_prompt += f"- {att.get('name', 'پیوست')}: {att.get('content', '')[:2000]}\n"
                else:
                    system_prompt += f"- {att[:500]}\n"

        user_prompt = f"دستور: {target_field.get('name', 'فیلد')}\n\n{target_field.get('value', '')}"

        # ارسال به مدل
        target_models = target_field.get("target_models", ["claude"])
        if "all" in target_models:
            target_models = ["claude"]

        ai_manager = get_ai_manager()
        results = []
        github_commits = []

        for model_id in target_models[:1]:
            start_time = time.time()
            try:
                messages = [
                    Message(role="system", content=system_prompt),
                    Message(role="user", content=user_prompt),
                ]

                response = await asyncio.wait_for(
                    ai_manager.generate(
                        model_id=model_id,
                        messages=messages,
                        max_tokens=8192,
                        temperature=0.7,
                    ),
                    timeout=120.0
                )

                latency_ms = int((time.time() - start_time) * 1000)

                result = {
                    "model_id": model_id,
                    "content": response.content,
                    "tokens_used": response.tokens_used,
                    "success": True
                }

                # 🔴 GitHub Commit Logic - مهم!
                logger.info(f"[execute_field_internal] Checking GitHub commit: action_type={action_type}, has_content={bool(response.content)}")
                if action_type in ["github_commit", "github_multi_commit"] and response.content:
                    if github_info.get("source") == "github":
                        owner = github_info.get("owner")
                        repo = github_info.get("repo")
                        # 🔴 بارگذاری توکن از environment یا database
                        token = os.getenv("GITHUB_TOKEN", "")
                        if not token:
                            from ...models.setting import Setting
                            try:
                                token = Setting.get_value(db, "api_key_github") or ""
                                if token:
                                    os.environ["GITHUB_TOKEN"] = token
                                    logger.info("[Batch Execute] GitHub token loaded from database")
                            except Exception as te:
                                logger.warning(f"[Batch Execute] Could not load GitHub token: {te}")

                        if owner and repo and token:
                            if action_type == "github_commit" and target_path:
                                # استخراج کد از پاسخ
                                code_content = response.content
                                code_match = re.search(r'```\w*\n?(.*?)```', code_content, re.DOTALL)
                                if code_match:
                                    code_content = code_match.group(1)

                                logger.info(f"[Batch Execute] Committing to GitHub: {target_path}")
                                commit_result = await commit_to_github(
                                    owner=owner,
                                    repo=repo,
                                    token=token,
                                    file_path=target_path,
                                    content=code_content.strip(),
                                    message=f"AI Generated: {target_field.get('name', 'Update')}",
                                    branch=github_info.get("branch", "main")
                                )
                                github_commits.append(commit_result)
                                logger.info(f"[Batch Execute] Commit result: {commit_result.get('success')}")

                            elif action_type == "github_multi_commit":
                                code_blocks = await extract_code_blocks(response.content)
                                for block in code_blocks:
                                    logger.info(f"[Batch Execute] Multi-committing: {block['path']}")
                                    commit_result = await commit_to_github(
                                        owner=owner,
                                        repo=repo,
                                        token=token,
                                        file_path=block["path"],
                                        content=block["content"],
                                        message=f"AI Generated: {block['path']}",
                                        branch=github_info.get("branch", "main")
                                    )
                                    github_commits.append(commit_result)

                            result["github_commits"] = github_commits
                        else:
                            result["github_error"] = "اطلاعات GitHub ناقص است"
                            logger.warning(f"[Batch Execute] Missing GitHub info: owner={bool(owner)}, repo={bool(repo)}, token={bool(token)}")
                    else:
                        result["github_error"] = "این پروژه از GitHub ایمپورت نشده"
                        logger.warning(f"[execute_field_internal] GitHub skipped: source={github_info.get('source')} (not 'github')")
                else:
                    # action_type is not github_commit or github_multi_commit
                    logger.info(f"[execute_field_internal] GitHub commit skipped: action_type={action_type} (need 'github_commit' or 'github_multi_commit')")

                results.append(result)

                # ثبت در لاگ فعالیت
                try:
                    extra_data = None
                    if github_commits:
                        extra_data = json.dumps({"github_commits": github_commits}, ensure_ascii=False)

                    log_entry = ActivityLog(
                        id=f"log_{uuid.uuid4().hex[:12]}",
                        project_id=project_id,
                        model_id=model_id,
                        model_provider=model_id.split("-")[0] if "-" in model_id else model_id,
                        activity_type="batch_trigger",
                        prompt=user_prompt[:10000],
                        response=response.content,
                        tokens_used=response.tokens_used or 0,
                        latency_ms=latency_ms,
                        success=True,
                        field_id=field_id,
                        field_name=target_field.get("name"),
                        extra_data=extra_data,
                        created_at=datetime.utcnow(),
                    )
                    db.add(log_entry)
                except Exception as log_err:
                    logger.error(f"[Batch Execute] Error logging: {log_err}")

            except asyncio.TimeoutError:
                results.append({
                    "model_id": model_id,
                    "error": "Timeout - پاسخ مدل بیش از 120 ثانیه طول کشید",
                    "success": False
                })
            except Exception as e:
                results.append({
                    "model_id": model_id,
                    "error": str(e),
                    "success": False
                })

        any_success = any(r.get("success") for r in results)
        any_github_success = any(c.get("success") for c in github_commits) if github_commits else False

        # 🔴 Trigger Deploy بعد از commit موفق
        deploy_result = None
        if deploy_after_commit and any_github_success:
            try:
                render_service_id = github_info.get("render_service_id")
                deploy_result = await trigger_render_deploy(
                    render_service_id=render_service_id,
                    project_id=project_id,
                    db_session=db
                )
                logger.info(f"[Batch Execute] Deploy triggered: {deploy_result}")
            except Exception as e:
                deploy_result = {"success": False, "error": str(e)}

        # 🔴 بایگانی خودکار - منطق اصلاح شده
        # برای فیلدهای GitHub: فقط اگر commit واقعاً موفق باشد بایگانی کن
        # برای فیلدهای display: اگر AI موفق بود بایگانی کن
        should_archive = False
        if archive_after_run and any_success:
            if action_type in ["github_commit", "github_multi_commit"]:
                # 🆕 برای اکشن‌های GitHub، فقط اگر commit واقعی موفق بود بایگانی کن
                if any_github_success:
                    should_archive = True
                    logger.info(f"[execute_field_internal] Will archive (GitHub success): action_type={action_type}, github_success={any_github_success}")
                else:
                    # اگر commit نشد، بایگانی نکن - این خیلی مهمه!
                    should_archive = False
                    logger.warning(f"[execute_field_internal] NOT archiving (GitHub failed): action_type={action_type}, github_success={any_github_success}")
            else:
                # برای display یا سایر action_type ها، اگر AI موفق بود کافیه
                should_archive = True
                logger.info(f"[execute_field_internal] Will archive (AI success): action_type={action_type}, any_success={any_success}")

        logger.info(f"[execute_field_internal] COMPLETED - field_id={field_id}, success={any_success}, github_success={any_github_success}")
        return {
            "success": any_success,
            "results": results,
            "github_commits": github_commits if github_commits else None,
            "deploy_result": deploy_result,
            "should_archive": should_archive,
            "any_github_success": any_github_success
        }

    except Exception as e:
        import traceback
        logger.error(f"[execute_field_internal] EXCEPTION in field_id={field_id}: {type(e).__name__}: {e}")
        logger.error(f"[execute_field_internal] Traceback: {traceback.format_exc()}")
        return {"success": False, "error": str(e)}


# =====================================
# 🆕 مدیریت پیوست‌های فیلد
# =====================================

@router.post("/{project_id}/memory/fields/{field_id}/attachments")
async def add_field_attachment(
    project_id: str,
    field_id: str,
    request: FieldAttachmentRequest,
    db: Session = Depends(get_db)
):
    """افزودن پیوست به فیلد"""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="پروژه یافت نشد")

    dynamic_fields = []
    try:
        if project.dynamic_fields:
            dynamic_fields = json.loads(project.dynamic_fields)
    except:
        pass

    field_found = False
    for field in dynamic_fields:
        if field.get("id") == field_id:
            if "attachments" not in field:
                field["attachments"] = []

            attachment = {
                "id": str(uuid.uuid4())[:8],
                "name": request.file_name,
                "type": request.file_type,
                "path": request.file_path,
                "content": request.file_content[:10000] if request.file_content else None,  # حداکثر 10K
                "added_at": time.strftime("%Y-%m-%dT%H:%M:%SZ")
            }
            field["attachments"].append(attachment)
            field_found = True
            break

    if not field_found:
        raise HTTPException(status_code=404, detail="فیلد یافت نشد")

    project.dynamic_fields = json.dumps(dynamic_fields, ensure_ascii=False)
    db.commit()

    return {
        "success": True,
        "message": "پیوست اضافه شد",
        "attachment_id": attachment["id"]
    }


@router.delete("/{project_id}/memory/fields/{field_id}/attachments/{attachment_id}")
async def remove_field_attachment(
    project_id: str,
    field_id: str,
    attachment_id: str,
    db: Session = Depends(get_db)
):
    """حذف پیوست از فیلد"""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="پروژه یافت نشد")

    dynamic_fields = []
    try:
        if project.dynamic_fields:
            dynamic_fields = json.loads(project.dynamic_fields)
    except:
        pass

    field_found = False
    for field in dynamic_fields:
        if field.get("id") == field_id:
            attachments = field.get("attachments", [])
            field["attachments"] = [a for a in attachments if a.get("id") != attachment_id]
            field_found = True
            break

    if not field_found:
        raise HTTPException(status_code=404, detail="فیلد یافت نشد")

    project.dynamic_fields = json.dumps(dynamic_fields, ensure_ascii=False)
    db.commit()

    return {"success": True, "message": "پیوست حذف شد"}


# =====================================
# تست و Debug دیپلوی
# =====================================

@router.post("/{project_id}/deploy/test")
async def test_render_deploy(
    project_id: str,
    db: Session = Depends(get_db)
):
    """
    تست دیپلوی به Render - برای دیباگ
    این endpoint مستقیماً Render deploy رو تست میکنه
    """
    import logging
    logger = logging.getLogger(__name__)
    from ...models.setting import Setting

    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="پروژه یافت نشد")

    # بررسی API Key - ابتدا environment بعد دیتابیس
    render_api_key = os.getenv("RENDER_API_KEY", "")
    github_token = os.getenv("GITHUB_TOKEN", "")

    # اگر در environment نبود، از دیتابیس بخون
    if not render_api_key:
        try:
            render_api_key = Setting.get_value(db, "api_key_render") or ""
            if render_api_key:
                os.environ["RENDER_API_KEY"] = render_api_key
                logger.info("[Deploy Test] Render API key loaded from database")
        except Exception as e:
            logger.warning(f"Could not load Render API key from DB: {e}")

    if not github_token:
        try:
            github_token = Setting.get_value(db, "api_key_github") or ""
            if github_token:
                os.environ["GITHUB_TOKEN"] = github_token
        except:
            pass

    debug_info = {
        "render_api_key_exists": bool(render_api_key),
        "render_api_key_length": len(render_api_key) if render_api_key else 0,
        "github_token_exists": bool(github_token),
    }

    # دریافت اطلاعات پروژه
    github_info = {}
    try:
        if project.extra_data:
            github_info = json.loads(project.extra_data)
    except:
        pass

    debug_info["github_info"] = {
        "source": github_info.get("source"),
        "owner": github_info.get("owner"),
        "repo": github_info.get("repo"),
        "render_service_id": github_info.get("render_service_id"),
    }

    if not render_api_key:
        return {
            "success": False,
            "error": "RENDER_API_KEY is not set. Please set it in Settings → Deploy Keys",
            "debug_info": debug_info,
            "solution": "در صفحه Settings → Deploy Keys کلید API رندر را تنظیم کنید"
        }

    # تست اتصال به Render
    try:
        result = await trigger_render_deploy(
            render_service_id=github_info.get("render_service_id"),
            project_id=project_id,
            db_session=db
        )

        return {
            "success": result.get("success", False),
            "deploy_result": result,
            "debug_info": debug_info,
        }

    except Exception as e:
        logger.error(f"[Render Deploy Test] Error: {e}")
        return {
            "success": False,
            "error": str(e),
            "debug_info": debug_info,
        }


@router.get("/{project_id}/deploy/status")
async def get_deploy_status(
    project_id: str,
    db: Session = Depends(get_db)
):
    """بررسی وضعیت Deploy keys و تنظیمات"""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="پروژه یافت نشد")

    render_api_key = os.getenv("RENDER_API_KEY", "")
    github_token = os.getenv("GITHUB_TOKEN", "")

    # دریافت اطلاعات پروژه
    github_info = {}
    try:
        if project.extra_data:
            github_info = json.loads(project.extra_data)
    except:
        pass

    # بررسی فیلدهایی که deploy_after_commit دارند
    fields_with_deploy = []
    try:
        if project.dynamic_fields:
            fields = json.loads(project.dynamic_fields)
            for f in fields:
                if f.get("deploy_after_commit") and not f.get("archived"):
                    fields_with_deploy.append({
                        "name": f.get("name"),
                        "action_type": f.get("action_type"),
                    })
    except:
        pass

    return {
        "success": True,
        "status": {
            "render_api_key_configured": bool(render_api_key),
            "github_token_configured": bool(github_token),
            "project_from_github": github_info.get("source") == "github",
            "github_owner": github_info.get("owner"),
            "github_repo": github_info.get("repo"),
            "render_service_id": github_info.get("render_service_id"),
            "fields_with_deploy_enabled": fields_with_deploy,
        },
        "ready_for_deploy": bool(render_api_key) and github_info.get("source") == "github",
    }


@router.post("/{project_id}/deploy/set-service-id")
async def set_render_service_id(
    project_id: str,
    service_id: str,
    db: Session = Depends(get_db)
):
    """
    ذخیره Render service_id برای پروژه
    این service_id از Render Dashboard دریافت میشه (مثلاً srv-xxxxx)
    """
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="پروژه یافت نشد")

    # دریافت و بروزرسانی extra_data
    try:
        extra_data = json.loads(project.extra_data) if project.extra_data else {}
    except:
        extra_data = {}

    extra_data["render_service_id"] = service_id
    project.extra_data = json.dumps(extra_data, ensure_ascii=False)
    db.commit()

    return {
        "success": True,
        "message": f"Render service ID ذخیره شد: {service_id}",
        "service_id": service_id
    }


class SetServicesRequest(BaseModel):
    """درخواست ذخیره چند سرویس Render"""
    service_ids: List[str]
    services: List[dict] = []


@router.post("/{project_id}/deploy/set-services")
async def set_render_services(
    project_id: str,
    request: SetServicesRequest,
    db: Session = Depends(get_db)
):
    """
    ذخیره چند سرویس Render برای پروژه
    برای پروژه‌هایی که هم frontend و هم backend دارند
    """
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="پروژه یافت نشد")

    # دریافت و بروزرسانی extra_data
    try:
        extra_data = json.loads(project.extra_data) if project.extra_data else {}
    except:
        extra_data = {}

    # ذخیره لیست سرویس‌ها
    extra_data["render_services"] = request.services
    extra_data["render_service_ids"] = request.service_ids
    # برای سازگاری با کد قبلی، اولین سرویس رو هم ذخیره کن
    if request.service_ids:
        extra_data["render_service_id"] = request.service_ids[0]

    project.extra_data = json.dumps(extra_data, ensure_ascii=False)
    db.commit()

    return {
        "success": True,
        "message": f"{len(request.service_ids)} سرویس Render ذخیره شد",
        "services": request.services,
        "service_ids": request.service_ids
    }


@router.get("/{project_id}/deploy/saved-services")
async def get_saved_render_services(
    project_id: str,
    db: Session = Depends(get_db)
):
    """دریافت سرویس‌های Render ذخیره شده برای پروژه"""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="پروژه یافت نشد")

    try:
        extra_data = json.loads(project.extra_data) if project.extra_data else {}
    except:
        extra_data = {}

    return {
        "success": True,
        "services": extra_data.get("render_services", []),
        "service_ids": extra_data.get("render_service_ids", []),
    }


@router.get("/{project_id}/deploy/list-services")
async def list_render_services(
    project_id: str,
    db: Session = Depends(get_db)
):
    """
    لیست سرویس‌های موجود در Render
    برای انتخاب service_id مناسب
    """
    from ...services.deploy_service import RenderDeployService

    render_api_key = os.getenv("RENDER_API_KEY", "")

    if not render_api_key:
        return {
            "success": False,
            "error": "Render API key not configured"
        }

    render_service = RenderDeployService(api_key=render_api_key)

    try:
        services = await render_service.list_services()
        await render_service.close()

        # استخراج اطلاعات مفید
        service_list = []
        for svc in services:
            svc_data = svc.get("service", svc)
            service_list.append({
                "id": svc_data.get("id"),
                "name": svc_data.get("name"),
                "type": svc_data.get("type"),
                "suspended": svc_data.get("suspended"),
                "url": svc_data.get("serviceDetails", {}).get("url"),
            })

        return {
            "success": True,
            "services": service_list,
            "count": len(service_list)
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


# =====================================
# راه‌اندازی خودکار پروژه - نسخه جامع
# =====================================

async def _log_to_journal(
    db: Session,
    project_id: str,
    action_type: str,
    title: str,
    description: str,
    details: Dict[str, Any] = None,
    success: bool = True
) -> str:
    """
    ثبت یک فعالیت در ژورنال پروژه
    """
    from datetime import datetime
    from .project_journal import ActivityLog
    log_id = f"log_{uuid.uuid4().hex[:12]}"

    log = ActivityLog(
        id=log_id,
        project_id=project_id,
        model_id="system",
        model_provider="auto-setup",
        activity_type=action_type,
        prompt=title,
        response=description,
        tokens_used=0,
        latency_ms=0,
        success=success,
        field_name=title,
        extra_data=json.dumps({
            "details": details or {},
            "timestamp": datetime.utcnow().isoformat(),
            "clickable": True,  # قابل کلیک در UI
            "full_description": description
        }, ensure_ascii=False),
        created_at=datetime.utcnow(),
    )

    db.add(log)
    return log_id


@router.post("/{project_id}/memory/auto-setup")
async def auto_setup_project(
    project_id: str,
    use_ai: bool = True,
    sync_github: bool = True,  # سینک با GitHub قبل از شروع
    clean_invalid: bool = True,  # حذف محتوای نامعتبر
    db: Session = Depends(get_db)
):
    """
    🚀 راه‌اندازی خودکار جامع پروژه

    قابلیت‌ها:
    1. بررسی کامل پوشه اصلی پروژه در گیت‌هاب (sync_github=True)
    2. به‌روزرسانی و سینک داده‌های تب‌های مختلف با محتوای فعلی
    3. حذف محتوای نامعتبر از تب‌ها (clean_invalid=True)
    4. ایجاد/به‌روزرسانی فیلدهای پویا با اولویت‌بندی
    5. بررسی فیلدها: نگه‌داری، بایگانی، ادغام
    6. ثبت تمام عملیات در ژورنال (سطر به سطر، قابل کلیک)
    7. به‌روزرسانی دقیق باکس حافظه
    """
    from ...services.project_auto_setup import auto_setup_project_memory
    from ...models.project import ProjectFile
    from ...services.ai_manager import load_api_keys_and_reset
    from datetime import datetime
    import logging
    import httpx

    logger = logging.getLogger(__name__)

    # مقادیر پیش‌فرض
    keys_loaded = []
    available_providers = []

    # ========================================
    # 🔴 مرحله 0: بارگذاری API keys و ریست AI manager (تابع متمرکز)
    # ========================================
    if use_ai:
        logger.info("🔑 Loading API keys using centralized function...")
        ai_manager, keys_loaded, available_providers = await load_api_keys_and_reset()

        if not available_providers:
            logger.warning("⚠️ No AI providers available! Auto-setup will use fallback mode.")
            logger.warning("   💡 Please add API keys in Settings page")
        else:
            logger.info(f"✅ Available AI providers: {available_providers}")

    # نتیجه نهایی با جزئیات کامل
    result = {
        "success": False,
        "project_id": project_id,
        "journal_entries": [],  # لیست تمام ثبت‌های ژورنال
        "operations": {
            "github_sync": {"done": False, "details": {}},
            "invalid_cleanup": {"done": False, "removed": []},
            "fields_analysis": {"done": False, "archived": [], "merged": [], "created": [], "updated": [], "preserved": []},
            "memory_update": {"done": False, "previous": "", "new": ""},
            "tabs_update": {"done": False, "tabs": []},
            "ai_status": {"keys_loaded": keys_loaded if use_ai else [], "providers_available": available_providers if use_ai else []}
        },
        "summary": ""
    }

    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="پروژه یافت نشد")

    # ========================================
    # مرحله 1: سینک با GitHub (اگر فعال باشد)
    # ========================================
    if sync_github and project.project_type == "github_import":
        try:
            log_id = await _log_to_journal(
                db, project_id, "auto_setup_step",
                "🔄 شروع سینک با GitHub",
                "در حال بازیابی آخرین تغییرات از ریپازیتوری GitHub...",
                {"step": 1, "action": "github_sync_start"}
            )
            result["journal_entries"].append(log_id)

            # دریافت اطلاعات GitHub از extra_data
            extra_data = {}
            try:
                if project.extra_data:
                    extra_data = json.loads(project.extra_data)
            except:
                pass

            owner = extra_data.get("owner")
            repo = extra_data.get("repo")
            branch = extra_data.get("branch", "main")

            if owner and repo:
                # فراخوانی API سینک داخلی
                try:
                    async with httpx.AsyncClient() as client:
                        sync_response = await client.post(
                            f"http://localhost:8000/api/github/imported/{project_id}/refresh",
                            timeout=60.0
                        )
                        sync_data = sync_response.json()

                        if sync_data.get("success"):
                            files_added = sync_data.get("files_added", 0)
                            files_updated = sync_data.get("files_updated", 0)
                            files_removed = sync_data.get("files_removed", 0)

                            result["operations"]["github_sync"] = {
                                "done": True,
                                "details": {
                                    "files_added": files_added,
                                    "files_updated": files_updated,
                                    "files_removed": files_removed,
                                    "owner": owner,
                                    "repo": repo,
                                    "branch": branch
                                }
                            }

                            log_id = await _log_to_journal(
                                db, project_id, "auto_setup_step",
                                "✅ سینک GitHub کامل شد",
                                f"فایل‌های اضافه شده: {files_added} | به‌روز شده: {files_updated} | حذف شده: {files_removed}",
                                {"step": 1, "action": "github_sync_complete", "files_added": files_added, "files_updated": files_updated, "files_removed": files_removed}
                            )
                            result["journal_entries"].append(log_id)
                        else:
                            logger.warning(f"GitHub sync returned error: {sync_data}")
                except Exception as e:
                    logger.error(f"GitHub sync error: {e}")
                    log_id = await _log_to_journal(
                        db, project_id, "auto_setup_step",
                        "⚠️ خطا در سینک GitHub",
                        f"سینک با GitHub انجام نشد: {str(e)}",
                        {"step": 1, "action": "github_sync_error", "error": str(e)},
                        success=False
                    )
                    result["journal_entries"].append(log_id)
        except Exception as e:
            logger.error(f"GitHub sync phase error: {e}")

    # ========================================
    # مرحله 2: دریافت فایل‌های به‌روز شده
    # ========================================
    files = db.query(ProjectFile).filter(ProjectFile.project_id == project_id).all()
    current_file_paths = set(f.file_path for f in files)
    files_data = [
        {"path": f.file_path, "content": f.content[:2000] if f.content else "", "file_type": f.file_type}
        for f in files
    ]

    log_id = await _log_to_journal(
        db, project_id, "auto_setup_step",
        "📁 بررسی فایل‌های پروژه",
        f"تعداد کل فایل‌ها: {len(files)}",
        {"step": 2, "action": "files_loaded", "total_files": len(files)}
    )
    result["journal_entries"].append(log_id)

    # ========================================
    # مرحله 3: حذف محتوای نامعتبر
    # ========================================
    if clean_invalid:
        removed_items = []

        # بررسی فیلدهای موجود برای target_path نامعتبر
        existing_fields = []
        try:
            if project.dynamic_fields:
                existing_fields = json.loads(project.dynamic_fields)
        except:
            pass

        for field in existing_fields:
            if field.get("archived"):
                continue
            target_path = field.get("target_path")
            if target_path and target_path not in current_file_paths:
                # فایل هدف حذف شده - فیلد را بایگانی کن
                field["archived"] = True
                field["archived_at"] = datetime.utcnow().isoformat()
                field["archived_reason"] = "target_file_removed_auto_setup"
                removed_items.append({
                    "type": "field",
                    "name": field.get("name"),
                    "reason": f"فایل هدف حذف شده: {target_path}"
                })

                log_id = await _log_to_journal(
                    db, project_id, "auto_setup_cleanup",
                    f"🗑️ بایگانی فیلد: {field.get('name')}",
                    f"فایل هدف ({target_path}) دیگر در پروژه وجود ندارد",
                    {"field_id": field.get("id"), "field_name": field.get("name"), "target_path": target_path}
                )
                result["journal_entries"].append(log_id)

        # ذخیره فیلدهای به‌روز شده
        if removed_items:
            project.dynamic_fields = json.dumps(existing_fields, ensure_ascii=False)

        # 🔴 سینک تب‌ها: پاکسازی health issues که به فایل‌های حذف شده اشاره می‌کنند
        health_issues_cleaned = []
        try:
            if project.issues_found:
                issues = json.loads(project.issues_found)
                valid_issues = []
                for issue in issues:
                    issue_file = issue.get("file", "")
                    # اگر فایل هنوز وجود دارد یا issue مربوط به کل پروژه است
                    if not issue_file or issue_file in current_file_paths or issue_file.startswith("/"):
                        valid_issues.append(issue)
                    else:
                        health_issues_cleaned.append({
                            "file": issue_file,
                            "type": issue.get("type"),
                            "message": issue.get("message", "")[:100]
                        })
                        removed_items.append({
                            "type": "health_issue",
                            "name": f"Issue in {issue_file}",
                            "reason": f"فایل مرتبط حذف شده: {issue_file}"
                        })

                if health_issues_cleaned:
                    project.issues_found = json.dumps(valid_issues, ensure_ascii=False)
                    log_id = await _log_to_journal(
                        db, project_id, "auto_setup_cleanup",
                        f"🧹 پاکسازی {len(health_issues_cleaned)} ایراد نامعتبر",
                        f"ایرادات مربوط به فایل‌های حذف شده از لیست برداشته شدند",
                        {"cleaned_issues": health_issues_cleaned[:10], "total_cleaned": len(health_issues_cleaned)}
                    )
                    result["journal_entries"].append(log_id)
        except Exception as e:
            logger.warning(f"Error cleaning health issues: {e}")

        result["operations"]["invalid_cleanup"] = {
            "done": True,
            "removed": removed_items,
            "health_issues_cleaned": len(health_issues_cleaned)
        }

        if removed_items:
            log_id = await _log_to_journal(
                db, project_id, "auto_setup_step",
                "🧹 پاکسازی محتوای نامعتبر",
                f"تعداد موارد حذف/بایگانی شده: {len(removed_items)} (فیلدها + ایرادات سلامت)",
                {"step": 3, "action": "cleanup_complete", "removed_count": len(removed_items), "items": removed_items}
            )
            result["journal_entries"].append(log_id)

    # ========================================
    # مرحله 4: جمع‌آوری context کامل
    # ========================================
    full_context = await gather_project_context(project_id, project, db)

    log_id = await _log_to_journal(
        db, project_id, "auto_setup_step",
        "📊 جمع‌آوری اطلاعات پروژه",
        f"ایرادات سلامت: {len(full_context.get('health_issues', []))} | فیلدهای اجرا نشده: {len(full_context.get('unexecuted_fields', []))}",
        {"step": 4, "action": "context_gathered",
         "health_issues": len(full_context.get('health_issues', [])),
         "unexecuted_fields": len(full_context.get('unexecuted_fields', [])),
         "has_roadmap": bool(full_context.get('roadmap_content')),
         "run_count": full_context.get('auto_setup_run_count', 0)}
    )
    result["journal_entries"].append(log_id)

    # ========================================
    # مرحله 5: اجرای auto-setup با AI
    # ========================================
    log_id = await _log_to_journal(
        db, project_id, "auto_setup_step",
        "🤖 شروع تحلیل هوشمند AI",
        "در حال تحلیل ساختار پروژه و تولید فیلدهای پویا...",
        {"step": 5, "action": "ai_analysis_start", "use_ai": use_ai}
    )
    result["journal_entries"].append(log_id)

    # ذخیره حافظه قبلی
    previous_memory = ""
    try:
        if project.memory_instructions:
            mem_data = json.loads(project.memory_instructions)
            previous_memory = mem_data.get("content", "")
    except:
        previous_memory = project.memory_instructions or ""

    try:
        setup_result = await auto_setup_project_memory(
            project_id=project_id,
            project_name=project.name,
            project_description=project.description or "",
            project_type=project.project_type or "",
            files=files_data,
            use_ai=use_ai,
            db_session=db,
            full_context=full_context
        )
    except Exception as e:
        logger.error(f"[Auto-Setup] AI Error: {e}")
        log_id = await _log_to_journal(
            db, project_id, "auto_setup_error",
            "❌ خطا در تحلیل AI",
            str(e),
            {"step": 5, "action": "ai_error", "error": str(e)},
            success=False
        )
        result["journal_entries"].append(log_id)
        db.commit()
        raise HTTPException(status_code=500, detail=f"خطا در راه‌اندازی: {str(e)}")

    if not setup_result.get("success"):
        error_msg = setup_result.get("error", "خطای ناشناخته")
        log_id = await _log_to_journal(
            db, project_id, "auto_setup_error",
            "❌ راه‌اندازی خودکار ناموفق",
            error_msg,
            {"step": 5, "action": "setup_failed", "error": error_msg},
            success=False
        )
        result["journal_entries"].append(log_id)
        db.commit()
        raise HTTPException(status_code=500, detail=error_msg)

    # ========================================
    # مرحله 6: ثبت جزئیات عملیات فیلدها
    # ========================================

    # فیلدهای بایگانی شده
    archived_count = setup_result.get("fields_archived", 0)
    if archived_count > 0:
        log_id = await _log_to_journal(
            db, project_id, "auto_setup_field_op",
            f"📦 بایگانی {archived_count} فیلد",
            "فیلدهای انجام شده یا منسوخ بایگانی شدند",
            {"action": "fields_archived", "count": archived_count}
        )
        result["journal_entries"].append(log_id)

    # فیلدهای ادغام شده
    merged_count = setup_result.get("fields_merged", 0)
    if merged_count > 0:
        log_id = await _log_to_journal(
            db, project_id, "auto_setup_field_op",
            f"🔗 ادغام {merged_count} فیلد",
            "فیلدهای مشابه برای عملکرد بهتر ادغام شدند",
            {"action": "fields_merged", "count": merged_count}
        )
        result["journal_entries"].append(log_id)

    # فیلدهای به‌روز شده
    updated_count = setup_result.get("fields_updated", 0)
    if updated_count > 0:
        log_id = await _log_to_journal(
            db, project_id, "auto_setup_field_op",
            f"✏️ به‌روزرسانی {updated_count} فیلد",
            "محتوا و تنظیمات فیلدها به‌روز شد",
            {"action": "fields_updated", "count": updated_count}
        )
        result["journal_entries"].append(log_id)

    # فیلدهای جدید
    new_count = setup_result.get("new_fields_count", 0)
    if new_count > 0:
        log_id = await _log_to_journal(
            db, project_id, "auto_setup_field_op",
            f"➕ ایجاد {new_count} فیلد جدید",
            "فیلدهای جدید بر اساس نیازهای شناسایی شده ایجاد شدند",
            {"action": "fields_created", "count": new_count}
        )
        result["journal_entries"].append(log_id)

    # فیلدهای محافظت شده
    protected_count = setup_result.get("fields_protected", 0)
    if protected_count > 0:
        log_id = await _log_to_journal(
            db, project_id, "auto_setup_field_op",
            f"🛡️ محافظت از {protected_count} فیلد",
            "فیلدهای ایجاد شده توسط گزارش مهندسی محافظت شدند",
            {"action": "fields_protected", "count": protected_count}
        )
        result["journal_entries"].append(log_id)

    result["operations"]["fields_analysis"] = {
        "done": True,
        "archived": archived_count,
        "merged": merged_count,
        "updated": updated_count,
        "created": new_count,
        "protected": protected_count
    }

    # ========================================
    # مرحله 7: ثبت به‌روزرسانی حافظه
    # ========================================
    new_memory = ""
    try:
        mem_data = setup_result.get("memory_instructions", {})
        if isinstance(mem_data, dict):
            new_memory = mem_data.get("content", "")
        else:
            new_memory = str(mem_data)
    except:
        pass

    if new_memory and new_memory != previous_memory:
        log_id = await _log_to_journal(
            db, project_id, "auto_setup_memory",
            "💾 به‌روزرسانی باکس حافظه",
            f"حافظه پروژه با اطلاعات جدید به‌روز شد (طول: {len(new_memory)} کاراکتر)",
            {"action": "memory_updated", "previous_length": len(previous_memory), "new_length": len(new_memory)}
        )
        result["journal_entries"].append(log_id)

    result["operations"]["memory_update"] = {
        "done": True,
        "previous_length": len(previous_memory),
        "new_length": len(new_memory),
        "changed": new_memory != previous_memory
    }

    # ========================================
    # مرحله 8: به‌روزرسانی سایر تب‌ها
    # ========================================
    tabs_updated = []

    # به‌روزرسانی اطلاعات تشخیص داده شده در پروژه
    try:
        extra_data = json.loads(project.extra_data) if project.extra_data else {}
    except:
        extra_data = {}

    extra_data["auto_setup_result"] = {
        "detected_type": setup_result.get("detected_type"),
        "language": setup_result.get("language"),
        "architecture": setup_result.get("architecture"),
        "frameworks": setup_result.get("frameworks", []),
        "last_run": datetime.utcnow().isoformat(),
        "run_count": full_context.get("auto_setup_run_count", 1)
    }

    # ذخیره توصیه‌ها در extra_data برای تب سلامت
    if setup_result.get("recommendations"):
        extra_data["ai_recommendations"] = setup_result.get("recommendations")
        tabs_updated.append("health")

    # ذخیره missing_files برای تب ساختار
    if setup_result.get("missing_files"):
        extra_data["missing_files"] = setup_result.get("missing_files")
        tabs_updated.append("structure")

    project.extra_data = json.dumps(extra_data, ensure_ascii=False)

    # به‌روزرسانی توضیحات پروژه اگر خالی است
    if not project.description and setup_result.get("ai_insights"):
        project.description = setup_result.get("ai_insights")[:500]
        tabs_updated.append("info")

    result["operations"]["tabs_update"] = {
        "done": True,
        "tabs": tabs_updated
    }

    if tabs_updated:
        log_id = await _log_to_journal(
            db, project_id, "auto_setup_tabs",
            f"📑 به‌روزرسانی تب‌ها: {', '.join(tabs_updated)}",
            "اطلاعات تب‌های مختلف با داده‌های جدید به‌روز شد",
            {"action": "tabs_updated", "tabs": tabs_updated}
        )
        result["journal_entries"].append(log_id)

    # ========================================
    # مرحله 9: ثبت خلاصه نهایی
    # ========================================
    summary = f"""راه‌اندازی خودکار با موفقیت انجام شد!
• نوع پروژه: {setup_result.get('detected_type', 'نامشخص')}
• زبان: {setup_result.get('language', 'نامشخص')}
• فیلدهای جدید: {new_count}
• فیلدهای بایگانی شده: {archived_count}
• فیلدهای به‌روز شده: {updated_count}
• مدل AI: {setup_result.get('model_used', 'نامشخص')}"""

    log_id = await _log_to_journal(
        db, project_id, "auto_setup_complete",
        "✅ راه‌اندازی خودکار کامل شد",
        summary,
        {
            "action": "setup_complete",
            "detected_type": setup_result.get("detected_type"),
            "language": setup_result.get("language"),
            "architecture": setup_result.get("architecture"),
            "frameworks": setup_result.get("frameworks", []),
            "total_journal_entries": len(result["journal_entries"]) + 1
        }
    )
    result["journal_entries"].append(log_id)

    # کامیت نهایی
    db.commit()

    result["success"] = True
    result["summary"] = summary
    result["detected_type"] = setup_result.get("detected_type")
    result["language"] = setup_result.get("language")
    result["architecture"] = setup_result.get("architecture")
    result["frameworks"] = setup_result.get("frameworks", [])
    result["ai_insights"] = setup_result.get("ai_insights")
    result["recommendations"] = setup_result.get("recommendations", [])
    result["tokens_used"] = setup_result.get("tokens_used", 0)
    result["model_used"] = setup_result.get("model_used")
    result["fields_count"] = len(setup_result.get("dynamic_fields", []))
    result["context_used"] = {
        "health_issues_count": len(full_context.get("health_issues", [])),
        "unexecuted_fields_count": len(full_context.get("unexecuted_fields", [])),
        "has_roadmap": bool(full_context.get("roadmap_content")),
        "run_count": full_context.get("auto_setup_run_count", 0)
    }

    return result


async def gather_project_context(project_id: str, project, db: Session) -> Dict[str, Any]:
    """
    جمع‌آوری تمام context موجود از پروژه برای auto-setup هوشمند
    """
    import logging
    logger = logging.getLogger(__name__)
    context = {}

    try:
        # 1. فیلدهای موجود (اجرا شده و نشده)
        existing_fields = []
        unexecuted_fields = []
        executed_fields = []
        if project.dynamic_fields:
            try:
                all_fields = json.loads(project.dynamic_fields)
                for f in all_fields:
                    if not f.get("archived"):
                        existing_fields.append(f)
                        if f.get("executed"):
                            executed_fields.append(f)
                        else:
                            unexecuted_fields.append(f)
            except:
                pass
        context["existing_fields"] = existing_fields
        context["unexecuted_fields"] = unexecuted_fields
        context["executed_fields"] = executed_fields

        # 2. حافظه فعلی
        memory_data = {}
        if project.memory_instructions:
            try:
                memory_data = json.loads(project.memory_instructions)
            except:
                memory_data = {"content": project.memory_instructions}
        context["current_memory"] = memory_data.get("content", "")

        # 3. تعداد دفعات اجرای auto-setup
        run_count = memory_data.get("auto_setup_run_count", 0) + 1
        context["auto_setup_run_count"] = run_count

        # 4. ایرادات تب سلامت (از extra_data یا health_analysis)
        health_issues = []
        try:
            if project.extra_data:
                extra = json.loads(project.extra_data)
                # از آخرین تحلیل سلامت
                if extra.get("health_analysis"):
                    health = extra["health_analysis"]
                    health_issues = health.get("issues", [])
                # یا از issues ذخیره شده
                if extra.get("tracked_issues"):
                    for issue in extra["tracked_issues"]:
                        if not issue.get("resolved") and not issue.get("converted_to_field"):
                            health_issues.append(issue)
        except:
            pass
        # 🔴 رفع محدودیت - تمام health_issues بدون محدودیت
        context["health_issues"] = health_issues

        # 5. نقشه راه
        roadmap_content = ""
        try:
            from ...models.project import ProjectFile
            roadmap_file = db.query(ProjectFile).filter(
                ProjectFile.project_id == project_id,
                ProjectFile.file_path.ilike("%roadmap%")
            ).first()
            if roadmap_file and roadmap_file.content:
                roadmap_content = roadmap_file.content[:2000]
        except:
            pass
        context["roadmap_content"] = roadmap_content

        # 6. گزارشات مهندسی (از journal)
        reports_summary = []
        try:
            from .project_journal import ActivityLog
            reports = db.query(ActivityLog).filter(
                ActivityLog.project_id == project_id,
                ActivityLog.activity_type.in_(["engineering_report", "ai_analysis", "deep_analysis"])
            ).order_by(ActivityLog.created_at.desc()).limit(5).all()

            for r in reports:
                try:
                    data = json.loads(r.activity_data) if r.activity_data else {}
                    reports_summary.append({
                        "type": r.activity_type,
                        "date": r.created_at.isoformat() if r.created_at else "",
                        "summary": data.get("summary", data.get("title", ""))[:200],
                        "issues_found": data.get("issues_count", len(data.get("issues", [])))
                    })
                except:
                    pass
        except Exception as e:
            logger.debug(f"Could not load reports: {e}")
        context["recent_reports"] = reports_summary

        # 7. امتیاز فایل‌ها (اگر موجود باشه)
        file_scores = []
        try:
            if project.extra_data:
                extra = json.loads(project.extra_data)
                if extra.get("file_scores"):
                    # فقط فایل‌های با مشکل
                    for path, score_data in extra["file_scores"].items():
                        score_val = score_data.get("score", 100) if isinstance(score_data, dict) else 100
                        try:
                            score_val = float(score_val) if score_val else 100
                        except (ValueError, TypeError):
                            score_val = 100
                        if isinstance(score_data, dict) and score_val < 70:
                            file_scores.append({
                                "path": path,
                                "score": score_data.get("score"),
                                "issues": score_data.get("issues", [])[:3]
                            })
        except:
            pass
        context["problematic_files"] = file_scores[:10]

        # 8. اطلاعات GitHub (برای تولید فیلدهای commit)
        github_info = {}
        try:
            if project.extra_data:
                extra = json.loads(project.extra_data)
                if extra.get("source") == "github":
                    github_info = {
                        "source": "github",
                        "owner": extra.get("owner"),
                        "repo": extra.get("repo"),
                        "branch": extra.get("branch", "main")
                    }
        except:
            pass
        context["github_info"] = github_info

        # 9. 🆕 نتایج اسکن امنیتی
        security_scan = {}
        try:
            if project.security_scan_result:
                scan_data = json.loads(project.security_scan_result) if isinstance(project.security_scan_result, str) else project.security_scan_result
                security_scan = {
                    "last_scan": project.security_scan_at.isoformat() if project.security_scan_at else None,
                    "security_score": scan_data.get("security_score", 0),
                    "summary": scan_data.get("summary", {}),
                    "secrets_count": len(scan_data.get("secrets", {}).get("findings", [])),
                    "vulnerabilities_count": len(scan_data.get("dependencies", {}).get("vulnerabilities", [])),
                    "sensitive_files_count": len(scan_data.get("sensitive_files", {}).get("findings", []))
                }
        except Exception as e:
            logger.debug(f"Could not load security scan: {e}")
        context["security_scan"] = security_scan

        # 10. 🆕 نتایج پوشش تست
        test_coverage = {}
        try:
            if project.test_coverage_result:
                coverage_data = json.loads(project.test_coverage_result) if isinstance(project.test_coverage_result, str) else project.test_coverage_result
                test_coverage = {
                    "coverage_percent": coverage_data.get("summary", {}).get("coverage_percent", 0),
                    "health_score": coverage_data.get("health_score", 0),
                    "total_tests": coverage_data.get("summary", {}).get("total_tests", 0),
                    "untested_files_count": len(coverage_data.get("untested_files", [])),
                    "recommendations_count": len(coverage_data.get("recommendations", []))
                }
        except Exception as e:
            logger.debug(f"Could not load test coverage: {e}")
        context["test_coverage"] = test_coverage

        # 11. 🆕 ایرادات پروژه (از مدل ProjectIssue)
        project_issues = []
        try:
            from ...models.project import ProjectIssue
            issues = db.query(ProjectIssue).filter(
                ProjectIssue.project_id == project_id,
                ProjectIssue.status.in_(["open", "in_progress"])
            ).order_by(ProjectIssue.priority).limit(20).all()
            for issue in issues:
                project_issues.append({
                    "id": issue.id,
                    "title": issue.title,
                    "priority": issue.priority,
                    "status": issue.status,
                    "source": issue.source,
                    "occurrences": issue.occurrences
                })
        except Exception as e:
            logger.debug(f"Could not load project issues: {e}")
        context["project_issues"] = project_issues

        # 12. 🆕 بایگانی عمومی (خلاصه)
        archive_summary = {"total": 0, "by_type": {}}
        try:
            if project.general_archive:
                archive_data = json.loads(project.general_archive) if isinstance(project.general_archive, str) else project.general_archive
                archive_summary["total"] = len(archive_data)
                for item in archive_data:
                    item_type = item.get("type", "other")
                    archive_summary["by_type"][item_type] = archive_summary["by_type"].get(item_type, 0) + 1
        except Exception as e:
            logger.debug(f"Could not load archive: {e}")
        context["archive_summary"] = archive_summary

        # 13. 🆕 خلاصه فایل‌های پروژه
        files_summary = {"total": 0, "by_type": {}, "sample_paths": []}
        try:
            from ...models.project import ProjectFile
            files = db.query(ProjectFile).filter(ProjectFile.project_id == project_id).all()
            files_summary["total"] = len(files)
            for f in files[:50]:  # فقط 50 فایل اول
                ext = f.file_path.split(".")[-1] if "." in f.file_path else "no_ext"
                files_summary["by_type"][ext] = files_summary["by_type"].get(ext, 0) + 1
                if len(files_summary["sample_paths"]) < 20:
                    files_summary["sample_paths"].append(f.file_path)
        except Exception as e:
            logger.debug(f"Could not load files summary: {e}")
        context["files_summary"] = files_summary

        # 14. 🆕 اطلاعات پایه پروژه
        project_info = {
            "id": project.id,
            "name": project.name,
            "description": project.description,
            "project_type": project.project_type,
            "status": project.status,
            "technologies": [],
            "features": [],
            "deploy_url": project.deploy_url,
            "github_path": project.github_path,
            "file_count": project.file_count,
            "total_size": project.total_size,
            "created_at": project.created_at.isoformat() if project.created_at else None
        }
        try:
            if project.technologies:
                project_info["technologies"] = json.loads(project.technologies) if isinstance(project.technologies, str) else project.technologies
            if project.features:
                project_info["features"] = json.loads(project.features) if isinstance(project.features, str) else project.features
        except:
            pass
        context["project_info"] = project_info

        # 15. 🆕 نتایج آخرین اعتبارسنجی
        validation_results = {}
        try:
            if project.last_validation_results:
                validation_results = json.loads(project.last_validation_results) if isinstance(project.last_validation_results, str) else project.last_validation_results
        except Exception as e:
            logger.debug(f"Could not load validation results: {e}")
        context["validation_results"] = validation_results

        # 16. 🆕 امتیازات سلامت
        health_scores = {}
        try:
            if project.health_scores:
                health_scores = json.loads(project.health_scores) if isinstance(project.health_scores, str) else project.health_scores
        except Exception as e:
            logger.debug(f"Could not load health scores: {e}")
        context["health_scores"] = health_scores

    except Exception as e:
        logger.error(f"Error gathering context: {e}")

    return context


@router.post("/memory/auto-setup-all")
async def auto_setup_all_projects(
    use_ai: bool = True,
    force: bool = False,
    db: Session = Depends(get_db)
):
    """
    راه‌اندازی خودکار همه پروژه‌ها
    force=True: حتی پروژه‌هایی که قبلاً تنظیم شده‌اند
    """
    from ...services.project_auto_setup import apply_auto_setup_to_existing_project

    projects = db.query(Project).all()
    results = {
        "total": len(projects),
        "success": 0,
        "skipped": 0,
        "failed": 0,
        "details": []
    }

    for project in projects:
        try:
            # بررسی اگه قبلا تنظیم شده
            if not force:
                existing_memory = {}
                try:
                    if project.memory_instructions:
                        existing_memory = json.loads(project.memory_instructions)
                except:
                    pass

                if existing_memory.get("content") and not existing_memory.get("auto_generated"):
                    results["skipped"] += 1
                    results["details"].append({
                        "project_id": project.id,
                        "name": project.name,
                        "status": "skipped",
                        "reason": "قبلاً تنظیم شده"
                    })
                    continue

            result = await apply_auto_setup_to_existing_project(project.id, db)

            if result.get("success"):
                if result.get("skipped"):
                    results["skipped"] += 1
                else:
                    results["success"] += 1
            else:
                results["failed"] += 1

            results["details"].append({
                "project_id": project.id,
                "name": project.name,
                "status": "success" if result.get("success") else "failed",
                "detected_type": result.get("detected_type"),
                "ai_insights": result.get("ai_insights")
            })

        except Exception as e:
            results["failed"] += 1
            results["details"].append({
                "project_id": project.id,
                "name": project.name,
                "status": "error",
                "error": str(e)
            })

    return {
        "success": True,
        "results": results
    }


@router.get("/{project_id}/memory/auto-setup/preview")
async def preview_auto_setup(
    project_id: str,
    db: Session = Depends(get_db)
):
    """
    پیش‌نمایش راه‌اندازی خودکار بدون اعمال تغییرات
    """
    from ...services.project_auto_setup import auto_setup_project_memory
    from ...models.project import ProjectFile

    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="پروژه یافت نشد")

    # دریافت فایل‌ها
    files = db.query(ProjectFile).filter(ProjectFile.project_id == project_id).all()
    files_data = [
        {"path": f.file_path, "content": f.content[:1000] if f.content else "", "file_type": f.file_type}
        for f in files
    ]

    # اجرای auto-setup بدون ذخیره (db_session=None)
    result = await auto_setup_project_memory(
        project_id=project_id,
        project_name=project.name,
        project_description=project.description or "",
        project_type=project.project_type or "",
        files=files_data,
        use_ai=False,  # برای preview فقط قالب
        db_session=None  # ذخیره نکن
    )

    result["is_preview"] = True
    return result


# =====================================
# تنظیمات سینک GitHub
# =====================================

class SyncSettingsRequest(BaseModel):
    """تنظیمات سینک GitHub"""
    auto_sync_enabled: bool = False  # سینک خودکار با تایمر
    sync_interval_minutes: int = 15  # هر چند دقیقه
    sync_after_field_execution: bool = True  # سینک بعد از اجرای فیلد (پیش‌فرض فعال)
    sync_after_commit: bool = True  # سینک بعد از commit به GitHub
    update_diagram_after_sync: bool = True  # بروزرسانی دیاگرام بعد از سینک
    update_structure_after_sync: bool = True  # بروزرسانی ساختار بعد از سینک


@router.get("/{project_id}/sync-settings")
async def get_sync_settings(
    project_id: str,
    db: Session = Depends(get_db)
):
    """دریافت تنظیمات سینک پروژه"""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="پروژه یافت نشد")

    # دریافت تنظیمات از extra_data
    sync_settings = {
        "auto_sync_enabled": False,
        "sync_interval_minutes": 15,
        "sync_after_field_execution": True,  # پیش‌فرض فعال
        "sync_after_commit": True,
        "update_diagram_after_sync": True,
        "update_structure_after_sync": True,
    }

    try:
        if project.extra_data:
            extra = json.loads(project.extra_data)
            if "sync_settings" in extra:
                sync_settings.update(extra["sync_settings"])
    except:
        pass

    return {
        "success": True,
        "project_id": project_id,
        "sync_settings": sync_settings,
        "is_github_project": project.project_type == "github_import"
    }


@router.put("/{project_id}/sync-settings")
async def update_sync_settings(
    project_id: str,
    request: SyncSettingsRequest,
    db: Session = Depends(get_db)
):
    """بروزرسانی تنظیمات سینک پروژه"""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="پروژه یافت نشد")

    # دریافت extra_data موجود
    try:
        extra_data = json.loads(project.extra_data) if project.extra_data else {}
    except:
        extra_data = {}

    # بروزرسانی تنظیمات سینک
    extra_data["sync_settings"] = {
        "auto_sync_enabled": request.auto_sync_enabled,
        "sync_interval_minutes": request.sync_interval_minutes,
        "sync_after_field_execution": request.sync_after_field_execution,
        "sync_after_commit": request.sync_after_commit,
        "update_diagram_after_sync": request.update_diagram_after_sync,
        "update_structure_after_sync": request.update_structure_after_sync,
    }

    project.extra_data = json.dumps(extra_data, ensure_ascii=False)
    db.commit()

    return {
        "success": True,
        "message": "تنظیمات سینک بروزرسانی شد",
        "sync_settings": extra_data["sync_settings"]
    }


@router.post("/{project_id}/sync-now")
async def trigger_sync_now(
    project_id: str,
    db: Session = Depends(get_db)
):
    """
    اجرای سینک فوری
    فایل‌ها را از GitHub سینک کرده و بر اساس تنظیمات دیاگرام/ساختار را بروزرسانی می‌کند
    """
    from datetime import datetime

    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="پروژه یافت نشد")

    if project.project_type != "github_import":
        return {
            "success": False,
            "error": "این پروژه از GitHub نیست"
        }

    # دریافت تنظیمات
    sync_settings = {
        "update_diagram_after_sync": True,
        "update_structure_after_sync": True,
    }
    try:
        if project.extra_data:
            extra = json.loads(project.extra_data)
            if "sync_settings" in extra:
                sync_settings.update(extra["sync_settings"])
    except:
        pass

    # اجرای سینک
    result = {
        "success": True,
        "synced_at": datetime.utcnow().isoformat(),
        "actions": []
    }

    # سینک فایل‌ها
    try:
        github_token = os.getenv("GITHUB_TOKEN", "")
        if github_token:
            result["actions"].append("files_sync_requested")
            result["github_sync"] = True
        else:
            result["github_sync"] = False
            result["actions"].append("github_token_missing")
    except Exception as e:
        result["github_sync_error"] = str(e)

    # ثبت آخرین زمان سینک
    try:
        extra_data = json.loads(project.extra_data) if project.extra_data else {}
        extra_data["last_sync_at"] = datetime.utcnow().isoformat()
        project.extra_data = json.dumps(extra_data, ensure_ascii=False)
        db.commit()
    except:
        pass

    result["update_diagram"] = sync_settings.get("update_diagram_after_sync", True)
    result["update_structure"] = sync_settings.get("update_structure_after_sync", True)

    return result


# Intervals برای UI
SYNC_INTERVALS = [
    {"value": 5, "label": "هر ۵ دقیقه"},
    {"value": 10, "label": "هر ۱۰ دقیقه"},
    {"value": 15, "label": "هر ۱۵ دقیقه"},
    {"value": 30, "label": "هر ۳۰ دقیقه"},
    {"value": 60, "label": "هر ۱ ساعت"},
    {"value": 120, "label": "هر ۲ ساعت"},
    {"value": 360, "label": "هر ۶ ساعت"},
    {"value": 720, "label": "هر ۱۲ ساعت"},
    {"value": 1440, "label": "روزانه"},
]


@router.get("/sync-intervals")
async def get_sync_intervals():
    """لیست بازه‌های زمانی موجود برای سینک"""
    return {
        "success": True,
        "intervals": SYNC_INTERVALS
    }


# =====================================
# 🆕 دانلود مارک‌داون
# =====================================

from fastapi.responses import Response

def _format_field_to_markdown(field: dict, include_details: bool = True) -> str:
    """تبدیل یک فیلد به فرمت مارک‌داون"""
    md = []

    # عنوان
    status_icon = "✅" if field.get("executed") else ("📦" if field.get("archived") else "📋")
    engineering_badge = " 🔬" if field.get("engineering_approval") else ""
    md.append(f"## {status_icon} {field.get('name', 'بدون نام')}{engineering_badge}")
    md.append("")

    if include_details:
        # متادیتا
        md.append("### مشخصات")
        md.append(f"- **شناسه:** `{field.get('id', '-')}`")
        md.append(f"- **نوع فیلد:** {field.get('field_type', 'temporary')}")
        md.append(f"- **نوع اقدام:** {field.get('action_type', 'display')}")
        md.append(f"- **اولویت:** {field.get('priority', 5)}")
        if field.get('target_path'):
            md.append(f"- **مسیر هدف:** `{field.get('target_path')}`")
        if field.get('target_models'):
            models = ', '.join(field.get('target_models', []))
            md.append(f"- **مدل‌ها:** {models}")
        md.append("")

    # محتوا/دستور
    md.append("### دستور")
    md.append("```")
    md.append(field.get("value", ""))
    md.append("```")
    md.append("")

    # وضعیت
    if field.get("executed"):
        md.append(f"✅ **اجرا شده:** {field.get('executed_at', '-')}")
    if field.get("archived"):
        md.append(f"📦 **بایگانی شده:** {field.get('archived_at', '-')}")

    md.append("")
    md.append("---")
    md.append("")

    return "\n".join(md)


def _format_issue_to_markdown(issue: dict, include_details: bool = True) -> str:
    """تبدیل یک ایراد به فرمت مارک‌داون"""
    md = []

    # آیکون severity
    severity_icons = {
        "critical": "🔴",
        "high": "🟠",
        "medium": "🟡",
        "low": "🟢",
        "info": "ℹ️"
    }
    severity = issue.get("severity", "medium")
    icon = severity_icons.get(severity, "⚪")

    md.append(f"## {icon} {issue.get('type', 'ایراد')} ({severity})")
    md.append("")

    if include_details:
        if issue.get("file"):
            md.append(f"**فایل:** `{issue.get('file')}`")
        if issue.get("line"):
            md.append(f"**خط:** {issue.get('line')}")
        md.append("")

    # پیام/توضیحات
    md.append("### توضیحات")
    md.append(issue.get("message", issue.get("description", "-")))
    md.append("")

    # راه حل پیشنهادی
    if issue.get("suggested_fix") or issue.get("recommendation"):
        md.append("### راه حل پیشنهادی")
        md.append(issue.get("suggested_fix") or issue.get("recommendation"))
        md.append("")

    # منبع شناسایی
    if issue.get("source_models"):
        models = ', '.join(issue.get("source_models", []))
        md.append(f"*شناسایی شده توسط: {models}*")
        md.append("")

    md.append("---")
    md.append("")

    return "\n".join(md)


@router.get("/{project_id}/export/fields/markdown")
async def export_fields_to_markdown(
    project_id: str,
    field_ids: str = None,  # کاما جدا شده، یا "all", "active", "archived"
    include_details: bool = True,
    db: Session = Depends(get_db)
):
    """
    دانلود فیلدهای پویا به فرمت مارک‌داون

    پارامترها:
    - field_ids: لیست شناسه‌ها با کاما جدا شده، یا "all", "active", "archived"
    - include_details: شامل جزئیات کامل باشد؟
    """
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="پروژه یافت نشد")

    dynamic_fields = []
    try:
        if project.dynamic_fields:
            dynamic_fields = json.loads(project.dynamic_fields)
    except:
        pass

    # فیلتر فیلدها
    if field_ids:
        if field_ids == "all":
            selected_fields = dynamic_fields
        elif field_ids == "active":
            selected_fields = [f for f in dynamic_fields if not f.get("archived")]
        elif field_ids == "archived":
            selected_fields = [f for f in dynamic_fields if f.get("archived")]
        else:
            ids = [id.strip() for id in field_ids.split(",")]
            selected_fields = [f for f in dynamic_fields if f.get("id") in ids]
    else:
        selected_fields = [f for f in dynamic_fields if not f.get("archived")]

    # ساخت مارک‌داون
    md_content = []
    md_content.append(f"# 📋 فیلدهای پویا - {project.name}")
    md_content.append("")
    md_content.append(f"*تاریخ استخراج: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC*")
    md_content.append("")
    md_content.append(f"**تعداد فیلدها:** {len(selected_fields)}")
    md_content.append("")
    md_content.append("---")
    md_content.append("")

    # گروه‌بندی بر اساس اولویت
    selected_fields.sort(key=lambda x: int(x.get("priority", 5)) if str(x.get("priority", 5)).isdigit() else 5)

    for field in selected_fields:
        md_content.append(_format_field_to_markdown(field, include_details))

    content = "\n".join(md_content)

    # ارسال به عنوان فایل دانلودی
    filename = f"{project.name}_fields_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.md"

    return Response(
        content=content,
        media_type="text/markdown; charset=utf-8",
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{filename}"
        }
    )


@router.get("/{project_id}/export/issues/markdown")
async def export_issues_to_markdown(
    project_id: str,
    issue_ids: str = None,  # کاما جدا شده، یا "all", "validated", "rejected"
    include_details: bool = True,
    db: Session = Depends(get_db)
):
    """
    دانلود ایرادات شناسایی شده به فرمت مارک‌داون

    پارامترها:
    - issue_ids: لیست شناسه‌ها، یا "all", "validated", "rejected"
    - include_details: شامل جزئیات کامل باشد؟
    """
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="پروژه یافت نشد")

    all_issues = []
    rejected_issues = []

    # ایرادات شناسایی شده
    try:
        if project.issues_found:
            all_issues = json.loads(project.issues_found)
    except:
        pass

    # ایرادات رد شده
    try:
        if project.rejected_issues_archive:
            rejected_issues = json.loads(project.rejected_issues_archive)
    except:
        pass

    # فیلتر
    if issue_ids:
        if issue_ids == "all":
            selected_issues = all_issues + rejected_issues
        elif issue_ids == "validated":
            selected_issues = all_issues
        elif issue_ids == "rejected":
            selected_issues = rejected_issues
        else:
            # فیلتر بر اساس شناسه یا ایندکس
            ids = [id.strip() for id in issue_ids.split(",")]
            selected_issues = []
            for idx, issue in enumerate(all_issues):
                if str(idx) in ids or issue.get("id") in ids:
                    selected_issues.append(issue)
    else:
        selected_issues = all_issues

    # ساخت مارک‌داون
    md_content = []
    md_content.append(f"# 🔍 ایرادات شناسایی شده - {project.name}")
    md_content.append("")
    md_content.append(f"*تاریخ استخراج: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC*")
    md_content.append("")

    # آمار
    severity_counts = {}
    for issue in selected_issues:
        sev = issue.get("severity", "medium")
        severity_counts[sev] = severity_counts.get(sev, 0) + 1

    md_content.append("## آمار")
    md_content.append(f"- **تعداد کل:** {len(selected_issues)}")
    for sev, count in sorted(severity_counts.items()):
        md_content.append(f"- **{sev}:** {count}")
    md_content.append("")
    md_content.append("---")
    md_content.append("")

    # مرتب‌سازی بر اساس severity
    severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
    # 🔴 تبدیل امن برای جلوگیری از خطای NoneType comparison
    selected_issues.sort(key=lambda x: severity_order.get(x.get("severity") if x.get("severity") else "medium", 2))

    for issue in selected_issues:
        md_content.append(_format_issue_to_markdown(issue, include_details))

    content = "\n".join(md_content)

    filename = f"{project.name}_issues_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.md"

    return Response(
        content=content,
        media_type="text/markdown; charset=utf-8",
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{filename}"
        }
    )


@router.get("/{project_id}/export/report/{report_id}/markdown")
async def export_report_to_markdown(
    project_id: str,
    report_id: str,
    db: Session = Depends(get_db)
):
    """
    دانلود گزارش مهندسی به فرمت مارک‌داون
    """
    from .project_journal import Report

    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="پروژه یافت نشد")

    report = db.query(Report).filter(
        Report.id == report_id,
        Report.project_id == project_id
    ).first()

    if not report:
        raise HTTPException(status_code=404, detail="گزارش یافت نشد")

    # ساخت مارک‌داون
    md_content = []
    md_content.append(f"# 📊 {report.title}")
    md_content.append("")
    md_content.append(f"**پروژه:** {project.name}")
    md_content.append(f"**تاریخ تولید:** {report.created_at.strftime('%Y-%m-%d %H:%M:%S') if report.created_at else '-'}")
    md_content.append(f"**مدل:** {report.generated_by or '-'}")
    md_content.append("")
    md_content.append("---")
    md_content.append("")

    # خلاصه
    if report.summary:
        md_content.append("## خلاصه اجرایی")
        md_content.append(report.summary)
        md_content.append("")

    # محتوای کامل
    if report.content:
        try:
            content_data = json.loads(report.content)

            # سلامت پروژه
            if "project_health" in content_data:
                health = content_data["project_health"]
                md_content.append("## 🏥 سلامت پروژه")
                md_content.append(f"- **امتیاز کلی:** {health.get('score', '-')}%")
                md_content.append(f"- **وضعیت:** {health.get('status', '-')}")
                if "key_metrics" in health:
                    md_content.append("### معیارها")
                    for key, val in health["key_metrics"].items():
                        md_content.append(f"- **{key}:** {val}")
                md_content.append("")

            # تحلیل فنی
            if "technical_analysis" in content_data:
                tech = content_data["technical_analysis"]
                md_content.append("## 🔧 تحلیل فنی")
                if tech.get("strengths"):
                    md_content.append("### نقاط قوت")
                    for s in tech["strengths"]:
                        md_content.append(f"- ✅ {s}")
                if tech.get("weaknesses"):
                    md_content.append("### نقاط ضعف")
                    for w in tech["weaknesses"]:
                        md_content.append(f"- ⚠️ {w}")
                md_content.append("")

            # باگ‌ها
            if "bugs_and_issues" in content_data:
                bugs = content_data["bugs_and_issues"]
                md_content.append(f"## 🐛 باگ‌ها و ایرادات ({len(bugs)} مورد)")
                for bug in bugs:
                    md_content.append(f"### {bug.get('title', 'ایراد')}")
                    md_content.append(f"- **شدت:** {bug.get('severity', '-')}")
                    if bug.get("file"):
                        md_content.append(f"- **فایل:** `{bug.get('file')}`")
                    md_content.append(f"- **توضیحات:** {bug.get('description', '-')}")
                    if bug.get("suggested_fix"):
                        md_content.append(f"- **راه حل:** {bug.get('suggested_fix')}")
                    md_content.append("")

            # امنیت
            if "security_review" in content_data:
                sec = content_data["security_review"]
                md_content.append("## 🔒 بررسی امنیتی")
                if sec.get("vulnerabilities"):
                    for vuln in sec["vulnerabilities"]:
                        md_content.append(f"- **{vuln.get('type', 'آسیب‌پذیری')}:** {vuln.get('location', '-')} (ریسک: {vuln.get('risk', '-')})")
                if sec.get("recommendations"):
                    md_content.append("### توصیه‌های امنیتی")
                    for rec in sec["recommendations"]:
                        md_content.append(f"- {rec}")
                md_content.append("")

            # پیشنهادات
            if "recommendations" in content_data:
                recs = content_data["recommendations"]
                md_content.append(f"## 💡 پیشنهادات ({len(recs)} مورد)")
                for rec in recs:
                    md_content.append(f"### [{rec.get('priority', '-')}] {rec.get('title', 'پیشنهاد')}")
                    md_content.append(f"{rec.get('description', '-')}")
                    md_content.append(f"*تلاش مورد نیاز: {rec.get('effort', '-')}*")
                    md_content.append("")

            # نقشه راه
            if "roadmap" in content_data:
                roadmap = content_data["roadmap"]
                md_content.append("## 🗺️ نقشه راه")
                if roadmap.get("immediate"):
                    md_content.append("### فوری")
                    for item in roadmap["immediate"]:
                        md_content.append(f"- [ ] {item.get('task', '-')}: {item.get('description', '')}")
                if roadmap.get("short_term"):
                    md_content.append("### کوتاه‌مدت")
                    for item in roadmap["short_term"]:
                        md_content.append(f"- [ ] {item.get('task', '-')}: {item.get('description', '')}")
                if roadmap.get("long_term"):
                    md_content.append("### بلندمدت")
                    for item in roadmap["long_term"]:
                        md_content.append(f"- [ ] {item.get('task', '-')}: {item.get('description', '')}")
                md_content.append("")

            # حالت ایده‌آل
            if "comprehensive_ideal_state" in content_data:
                ideal = content_data["comprehensive_ideal_state"]
                md_content.append("## ⭐ حالت ایده‌آل")
                md_content.append(ideal.get("description", "-"))
                md_content.append("")

        except json.JSONDecodeError:
            # اگر JSON نبود، محتوا را مستقیم اضافه کن
            md_content.append("## محتوای گزارش")
            md_content.append(report.content)

    md_content.append("")
    md_content.append("---")
    md_content.append(f"*تولید شده توسط سیستم گزارش مهندسی*")

    content = "\n".join(md_content)

    filename = f"{project.name}_report_{report_id}_{datetime.utcnow().strftime('%Y%m%d')}.md"

    return Response(
        content=content,
        media_type="text/markdown; charset=utf-8",
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{filename}"
        }
    )


# ==============================================
# 🆕 دانلود تکی فیلد و ایراد به مارک‌داون
# ==============================================

@router.get("/{project_id}/export/field/{field_id}/markdown")
async def export_single_field_to_markdown(
    project_id: str,
    field_id: str,
    db: Session = Depends(get_db)
):
    """
    دانلود یک فیلد پویا به فرمت مارک‌داون

    پارامترها:
    - field_id: شناسه فیلد یا ایندکس آن
    """
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="پروژه یافت نشد")

    dynamic_fields = []
    try:
        if project.dynamic_fields:
            dynamic_fields = json.loads(project.dynamic_fields)
    except:
        pass

    # یافتن فیلد
    target_field = None
    for idx, field in enumerate(dynamic_fields):
        if field.get("id") == field_id or str(idx) == field_id:
            target_field = field
            break

    if not target_field:
        raise HTTPException(status_code=404, detail="فیلد یافت نشد")

    # ساخت مارک‌داون
    md_content = []
    md_content.append(f"# 📝 فیلد پویا: {target_field.get('name', 'بدون نام')}")
    md_content.append("")
    md_content.append(f"**پروژه:** {project.name}")
    md_content.append(f"**شناسه:** `{target_field.get('id', '-')}`")
    md_content.append(f"**تاریخ ایجاد:** {target_field.get('created_at', '-')}")
    md_content.append("")
    md_content.append("---")
    md_content.append("")

    # اطلاعات اصلی
    md_content.append("## مشخصات فیلد")
    md_content.append("")
    md_content.append(f"| ویژگی | مقدار |")
    md_content.append(f"|--------|-------|")
    md_content.append(f"| نوع | {target_field.get('type', 'text')} |")
    md_content.append(f"| اولویت | {target_field.get('priority', '-')} |")
    md_content.append(f"| مدل‌های هدف | {', '.join(target_field.get('target_models', ['all']))} |")
    md_content.append(f"| تریگر | {target_field.get('trigger', 'manual')} |")
    md_content.append(f"| وضعیت | {'✅ فعال' if not target_field.get('archived') else '📦 بایگانی'} |")

    # تاییدیه مهندسی
    approval = target_field.get('engineering_approval', {})
    if approval:
        md_content.append(f"| تایید مهندسی | {'✅' if approval.get('approved') else '❌'} |")
        md_content.append(f"| تایید کننده | {approval.get('approved_by', '-')} |")

    md_content.append("")

    # محتوای فیلد
    md_content.append("## محتوا")
    md_content.append("")
    value = target_field.get('value', '')
    if isinstance(value, dict):
        md_content.append("```json")
        md_content.append(json.dumps(value, ensure_ascii=False, indent=2))
        md_content.append("```")
    else:
        md_content.append(str(value))
    md_content.append("")

    # توضیحات
    if target_field.get('description'):
        md_content.append("## توضیحات")
        md_content.append("")
        md_content.append(target_field.get('description'))
        md_content.append("")

    # تاریخچه اجرا
    if target_field.get('execution_history'):
        md_content.append("## تاریخچه اجرا")
        md_content.append("")
        for exec_record in target_field.get('execution_history', [])[-5:]:
            md_content.append(f"- **{exec_record.get('executed_at', '-')}**: {exec_record.get('result', '-')}")
        md_content.append("")

    content = '\n'.join(md_content)
    filename = f"field_{target_field.get('id', 'unknown')}_{datetime.utcnow().strftime('%Y%m%d')}.md"

    return Response(
        content=content,
        media_type="text/markdown; charset=utf-8",
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{filename}"
        }
    )


@router.get("/{project_id}/export/issue/{issue_index}/markdown")
async def export_single_issue_to_markdown(
    project_id: str,
    issue_index: str,  # می‌تواند شناسه یا ایندکس باشد
    db: Session = Depends(get_db)
):
    """
    دانلود یک ایراد به فرمت مارک‌داون

    پارامترها:
    - issue_index: ایندکس ایراد (0-based) یا شناسه آن
    """
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="پروژه یافت نشد")

    all_issues = []
    try:
        if project.issues_found:
            all_issues = json.loads(project.issues_found)
    except:
        pass

    # یافتن ایراد
    target_issue = None
    try:
        idx = int(issue_index)
        if 0 <= idx < len(all_issues):
            target_issue = all_issues[idx]
    except ValueError:
        # شناسه
        for issue in all_issues:
            if issue.get("id") == issue_index:
                target_issue = issue
                break

    if not target_issue:
        raise HTTPException(status_code=404, detail="ایراد یافت نشد")

    # نگاشت شدت
    severity_map = {
        "critical": "🔴 بحرانی",
        "high": "🟠 بالا",
        "medium": "🟡 متوسط",
        "low": "🟢 پایین",
        "info": "ℹ️ اطلاعاتی"
    }

    severity = target_issue.get("severity", "medium")
    severity_text = severity_map.get(severity, severity)

    # ساخت مارک‌داون
    md_content = []
    md_content.append(f"# 🐛 ایراد: {target_issue.get('message', target_issue.get('description', 'بدون توضیح'))[:80]}")
    md_content.append("")
    md_content.append(f"**پروژه:** {project.name}")
    md_content.append(f"**شدت:** {severity_text}")
    md_content.append("")
    md_content.append("---")
    md_content.append("")

    # اطلاعات فایل
    md_content.append("## موقعیت")
    md_content.append("")
    file_path = target_issue.get("file_path", target_issue.get("file", "-"))
    line = target_issue.get("line", target_issue.get("line_number", "-"))
    md_content.append(f"- **فایل:** `{file_path}`")
    md_content.append(f"- **خط:** {line}")
    md_content.append("")

    # توضیحات ایراد
    md_content.append("## توضیحات")
    md_content.append("")
    md_content.append(target_issue.get("description", target_issue.get("message", "توضیحی ثبت نشده")))
    md_content.append("")

    # پیشنهاد رفع
    if target_issue.get("suggestion") or target_issue.get("fix"):
        md_content.append("## پیشنهاد رفع")
        md_content.append("")
        suggestion = target_issue.get("suggestion") or target_issue.get("fix", "")
        if suggestion:
            md_content.append("```")
            md_content.append(suggestion)
            md_content.append("```")
        md_content.append("")

    # مدل شناسایی‌کننده
    if target_issue.get("detected_by") or target_issue.get("model_id"):
        md_content.append("## اطلاعات تکمیلی")
        md_content.append("")
        md_content.append(f"- **شناسایی توسط:** {target_issue.get('detected_by', target_issue.get('model_id', '-'))}")
        md_content.append(f"- **تاریخ شناسایی:** {target_issue.get('detected_at', '-')}")
        md_content.append("")

    content = '\n'.join(md_content)
    filename = f"issue_{issue_index}_{datetime.utcnow().strftime('%Y%m%d')}.md"

    return Response(
        content=content,
        media_type="text/markdown; charset=utf-8",
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{filename}"
        }
    )
