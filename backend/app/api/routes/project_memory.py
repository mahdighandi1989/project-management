"""
API routes for Project Memory Management
مسیرهای API برای مدیریت حافظه و دستورات پروژه
"""

import json
import uuid
import time
import asyncio
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session

from ...core.database import get_db
from ...models.project import Project
from .project_journal import ActivityLog

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
    """
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="پروژه یافت نشد")

    memory_data = {
        "content": request.content,
        "target_models": request.target_models
    }

    project.memory_instructions = json.dumps(memory_data, ensure_ascii=False)
    db.commit()

    return {
        "success": True,
        "message": "باکس حافظه بروزرسانی شد",
        "memory_instructions": memory_data
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
                context_parts.append(f"\n## ایرادات شناسایی شده ({len(issues_found)} مورد):")
                for i, issue in enumerate(issues_found[:20], 1):  # حداکثر 20 ایراد
                    issue_text = f"{i}. "
                    if isinstance(issue, dict):
                        issue_text += f"[{issue.get('severity', 'نامشخص')}] {issue.get('title', issue.get('description', str(issue)))}"
                        if issue.get('file'):
                            issue_text += f" (فایل: {issue.get('file')})"
                    else:
                        issue_text += str(issue)
                    context_parts.append(issue_text)
                if len(issues_found) > 20:
                    context_parts.append(f"... و {len(issues_found) - 20} ایراد دیگر")
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

    full_context = "\n".join(context_parts)

    # 7. ساخت system prompt
    system_prompt = f"""تو یک دستیار هوشمند برای تحلیل و بررسی دقیق پروژه هستی.

وظیفه تو:
1. بررسی دقیق و جزء به جزء محتوای پروژه
2. یافتن مشکلات واقعی با ارجاع به فایل و خط کد مربوطه
3. ارائه راه‌حل‌های مشخص و عملی
4. پاسخ‌های قاطع (نه با شاید و احتمالا) بر اساس آنچه در کد می‌بینی

هنگام پاسخ‌گویی:
- اگر مشکلی وجود دارد، دقیقاً بگو کجا و چرا
- اگر باید اقدامی انجام شود، مشخص کن: فایل، خط، و تغییر لازم
- اولویت مشکلات را مشخص کن (بحرانی، بالا، متوسط، پایین)

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

            # ثبت در ژورنال
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

            # ثبت خطا در ژورنال
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
                created_at=datetime.utcnow(),
            )
            db.add(log_entry)

    db.commit()

    # 9. تبدیل به فیلدهای پویا اگر درخواست شده
    # 🔴 بهبود: بررسی تکراری و ادغام فیلدهای مشابه قبل از افزودن
    created_fields = []
    merged_fields = []
    skipped_fields = []

    if request.create_dynamic_fields:
        for resp in responses:
            if resp.get("success") and resp.get("content"):
                fields = await parse_response_to_dynamic_fields(
                    resp["content"],
                    resp["model_id"],
                    request.auto_detect_actions
                )

                # ذخیره فیلدها در پروژه با بررسی تکراری
                if fields:
                    existing_fields = []
                    try:
                        existing_fields = json.loads(project.dynamic_fields) if project.dynamic_fields else []
                    except:
                        pass

                    for field in fields:
                        field["id"] = f"field_{uuid.uuid4().hex[:8]}"
                        field["created_at"] = datetime.utcnow().isoformat()
                        field["source_model"] = resp["model_id"]
                        field["source"] = "ai_query"  # 🔴 منبع فیلد

                        # 🔴 بررسی تکراری بودن و امکان ادغام
                        similar_field = None
                        for ef in existing_fields:
                            if ef.get("archived"):
                                continue

                            # بررسی شباهت نام یا محتوا
                            name_similarity = _calculate_similarity(field.get("name", ""), ef.get("name", ""))
                            value_similarity = _calculate_similarity(field.get("value", "")[:200], ef.get("value", "")[:200])

                            # اگر نام یا محتوا خیلی شبیه بود
                            if name_similarity > 0.7 or value_similarity > 0.6:
                                similar_field = ef
                                break

                        if similar_field:
                            # 🔴 بررسی کدام بهتر است
                            new_priority = field.get("priority", 5)
                            existing_priority = similar_field.get("priority", 5)

                            if new_priority < existing_priority:
                                # فیلد جدید بهتر است - ادغام
                                similar_field["value"] = f"{similar_field.get('value', '')}\n\n--- ادغام شده از پرسش AI ---\n{field.get('value', '')}"
                                similar_field["priority"] = new_priority
                                similar_field["updated_at"] = datetime.utcnow().isoformat()
                                similar_field["merged_with"] = field.get("name")
                                merged_fields.append({"original": similar_field.get("name"), "merged": field.get("name")})
                            else:
                                # فیلد موجود بهتر است - رد شود
                                skipped_fields.append({
                                    "name": field.get("name"),
                                    "reason": f"فیلد مشابه با اولویت بهتر وجود دارد: {similar_field.get('name')}"
                                })
                        else:
                            # فیلد جدید - اضافه شود
                            # 🔴 فیلدهای از پرسش AI نیاز به تاییدیه دارند (validation_marker=pending)
                            field["validation_marker"] = "pending"
                            field["needs_approval"] = True
                            existing_fields.append(field)
                            created_fields.append(field)

                    project.dynamic_fields = json.dumps(existing_fields, ensure_ascii=False)

        db.commit()

        # 🔴 ثبت در ژورنال
        if created_fields or merged_fields:
            ai_query_log = ActivityLog(
                id=f"log_{uuid.uuid4().hex[:12]}",
                project_id=project_id,
                model_id="system",
                activity_type="ai_query_fields",
                prompt=f"تولید فیلد از پرسش AI: {request.prompt[:200]}",
                response=f"ایجاد {len(created_fields)} فیلد، ادغام {len(merged_fields)} فیلد، رد {len(skipped_fields)} فیلد",
                tokens_used=0,
                latency_ms=0,
                success=True,
                created_at=datetime.utcnow(),
            )
            db.add(ai_query_log)
            db.commit()


def _calculate_similarity(str1: str, str2: str) -> float:
    """محاسبه شباهت دو رشته (0-1)"""
    if not str1 or not str2:
        return 0.0
    str1 = str1.lower().strip()
    str2 = str2.lower().strip()
    if str1 == str2:
        return 1.0
    # محاسبه ساده با کلمات مشترک
    words1 = set(str1.split())
    words2 = set(str2.split())
    if not words1 or not words2:
        return 0.0
    intersection = len(words1 & words2)
    union = len(words1 | words2)
    return intersection / union if union > 0 else 0.0

    return {
        "success": True,
        "project_id": project_id,
        "responses": responses,
        "total_tokens": total_tokens,
        "models_used": len(request.model_ids),
        "context_summary": {
            "files_included": len(files) if request.include_files else 0,
            "issues_included": len(issues_found) if request.include_issues and 'issues_found' in locals() else 0,
            "health_included": request.include_health,
            "memory_included": request.include_memory,
        },
        # 🔴 اطلاعات کامل فیلدها
        "created_fields": created_fields if request.create_dynamic_fields else None,
        "merged_fields": merged_fields if request.create_dynamic_fields else None,
        "skipped_fields": skipped_fields if request.create_dynamic_fields else None,
        "fields_summary": {
            "created": len(created_fields),
            "merged": len(merged_fields),
            "skipped": len(skipped_fields)
        } if request.create_dynamic_fields else None,
    }


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

                # بایگانی خودکار اگر موفق و تنظیم شده
                if archive_after_run and any_success:
                    if action_type == "display" or any_github_success:
                        field["archived"] = True
                        field["archived_at"] = datetime.utcnow().isoformat()
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
        dynamic_fields.sort(key=lambda x: x.get("priority", 5))

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
        fields_to_execute.sort(key=lambda x: x.get("priority", 5))

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

        # 🔴 بایگانی خودکار - اگر اجرا موفق بود و archive_after_run فعاله، بایگانی میشه
        should_archive = False
        if archive_after_run and any_success:
            # همیشه بایگانی کن اگر اجرای AI موفق بود - مهم نیست GitHub چی شد
            should_archive = True
            logger.info(f"[execute_field_internal] Will archive: archive_after_run={archive_after_run}, any_success={any_success}")

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
# راه‌اندازی خودکار پروژه
# =====================================

@router.post("/{project_id}/memory/auto-setup")
async def auto_setup_project(
    project_id: str,
    use_ai: bool = True,
    db: Session = Depends(get_db)
):
    """
    راه‌اندازی خودکار هوشمند حافظه و فیلدهای پویا برای پروژه
    🔴 نسخه بهبودیافته: در نظر گرفتن تمام context موجود
    """
    from ...services.project_auto_setup import auto_setup_project_memory
    from ...models.project import ProjectFile
    import logging
    logger = logging.getLogger(__name__)

    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="پروژه یافت نشد")

    # دریافت فایل‌ها
    files = db.query(ProjectFile).filter(ProjectFile.project_id == project_id).all()
    files_data = [
        {"path": f.file_path, "content": f.content[:2000] if f.content else "", "file_type": f.file_type}
        for f in files
    ]

    # 🔴 جمع‌آوری context کامل از پروژه
    full_context = await gather_project_context(project_id, project, db)
    logger.info(f"[Auto-Setup] Gathered context: {len(full_context.get('health_issues', []))} health issues, "
                f"{len(full_context.get('unexecuted_fields', []))} unexecuted fields, "
                f"run_count={full_context.get('auto_setup_run_count', 0)}")

    # اجرای auto-setup با context کامل
    try:
        result = await auto_setup_project_memory(
            project_id=project_id,
            project_name=project.name,
            project_description=project.description or "",
            project_type=project.project_type or "",
            files=files_data,
            use_ai=use_ai,
            db_session=db,
            full_context=full_context  # 🔴 ارسال context کامل
        )
    except Exception as e:
        logger.error(f"[Auto-Setup] Error: {e}")
        raise HTTPException(status_code=500, detail=f"خطا در راه‌اندازی: {str(e)}")

    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error", "خطا در راه‌اندازی"))

    # تبدیل به JSON-serializable
    return {
        "success": True,
        "project_id": result.get("project_id"),
        "detected_type": result.get("detected_type"),
        "language": result.get("language"),
        "architecture": result.get("architecture"),
        "frameworks": result.get("frameworks", []),
        "ai_insights": result.get("ai_insights"),
        "recommendations": result.get("recommendations", []),
        "tokens_used": result.get("tokens_used", 0),
        "model_used": result.get("model_used"),
        "fields_created": len(result.get("dynamic_fields", [])),
        "context_used": {  # 🔴 اطلاع‌رسانی از context استفاده شده
            "health_issues_count": len(full_context.get("health_issues", [])),
            "unexecuted_fields_count": len(full_context.get("unexecuted_fields", [])),
            "has_roadmap": bool(full_context.get("roadmap_content")),
            "run_count": full_context.get("auto_setup_run_count", 0)
        }
    }


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
        context["health_issues"] = health_issues[:20]  # حداکثر 20 تا

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
            from ...models.activity import ActivityLog
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
                        if isinstance(score_data, dict) and score_data.get("score", 100) < 70:
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
