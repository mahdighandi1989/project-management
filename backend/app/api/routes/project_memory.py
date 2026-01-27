"""
API routes for Project Memory Management
مسیرهای API برای مدیریت حافظه و دستورات پروژه
"""

import json
import uuid
import time
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional
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
    archive_after_run: bool = False  # آیا بعد از اجرای موفق بایگانی شود؟
    deploy_after_commit: bool = False  # آیا بعد از commit در Render دیپلوی شود؟


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


# ثابت‌های نوع اکشن
ACTION_TYPES = [
    {"id": "display", "name": "فقط نمایش", "icon": "👁️", "description": "نتیجه فقط در ژورنال نمایش داده می‌شود"},
    {"id": "github_commit", "name": "Commit به GitHub", "icon": "📤", "description": "نتیجه به عنوان یک فایل در ریپو commit می‌شود"},
    {"id": "github_multi_commit", "name": "Multi Commit", "icon": "📦", "description": "چند فایل از پاسخ استخراج و commit می‌شوند"},
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
    db_session = None
) -> dict:
    """
    Trigger یک deploy جدید در Render
    ابتدا سعی می‌کند از render_service_id استفاده کند
    اگر نبود، از تنظیمات پروژه می‌خواند
    """
    import logging
    logger = logging.getLogger(__name__)

    from ...services.deploy_service import RenderDeployService

    # دریافت کلید از environment (ممکن است بعد از شروع برنامه تنظیم شده باشد)
    render_api_key = os.getenv("RENDER_API_KEY", "")

    logger.info(f"[Render Deploy] API Key exists: {bool(render_api_key)}")

    if not render_api_key:
        return {"success": False, "error": "Render API key not configured. Please set it in Settings."}

    # ساخت مستقیم سرویس Render با کلید جدید (جلوگیری از cache شدن session قدیمی)
    render_service = RenderDeployService(api_key=render_api_key)

    # پیدا کردن service_id
    service_id = render_service_id

    # اگر service_id نداریم، از پروژه بخوان
    if not service_id and project_id and db_session:
        try:
            project = db_session.query(Project).filter(Project.id == project_id).first()
            if project and project.extra_data:
                extra = json.loads(project.extra_data)
                service_id = extra.get("render_service_id")
                logger.info(f"[Render Deploy] Found service_id from project: {service_id}")
        except Exception as e:
            logger.warning(f"[Render Deploy] Error reading project extra_data: {e}")

    if not service_id:
        # سعی کن از سرویس‌های موجود پیدا کنی
        try:
            logger.info("[Render Deploy] Listing services to find service_id...")
            services = await render_service.list_services()
            logger.info(f"[Render Deploy] Found {len(services) if services else 0} services")

            if services and len(services) > 0:
                # اولین سرویس را استفاده کن (یا می‌تونی بر اساس نام پروژه فیلتر کنی)
                for svc in services:
                    svc_data = svc.get("service", svc)
                    service_id = svc_data.get("id")
                    svc_name = svc_data.get("name", "unknown")
                    if service_id:
                        logger.info(f"[Render Deploy] Using service: {svc_name} ({service_id})")
                        break
        except Exception as e:
            logger.error(f"[Render Deploy] Error listing services: {e}")
            await render_service.close()
            return {"success": False, "error": f"Error listing Render services: {str(e)}"}

    if not service_id:
        await render_service.close()
        return {"success": False, "error": "No Render service found. Please deploy your project to Render first or set render_service_id in project settings."}

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

    # افزودن فیلد جدید با تنظیمات تریگر
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
        }
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
            field_found = True
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

        # ساخت prompt از دستور فیلد
        system_prompt = f"تو یک دستیار هوشمند برای پروژه '{project.name}' هستی."
        if project.description:
            system_prompt += f"\nتوضیحات پروژه: {project.description}"

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
                        token = os.getenv("GITHUB_TOKEN", "")

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
                    prompt=user_prompt[:2000],
                    response=response.content[:5000] if response.content else None,
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
                    prompt=user_prompt[:2000],
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
                    prompt=user_prompt[:2000],
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
# راه‌اندازی خودکار پروژه
# =====================================

@router.post("/{project_id}/memory/auto-setup")
async def auto_setup_project(
    project_id: str,
    use_ai: bool = True,
    db: Session = Depends(get_db)
):
    """
    راه‌اندازی خودکار حافظه و فیلدهای پویا برای پروژه
    بر اساس تحلیل فایل‌ها و نوع پروژه
    """
    from ...services.project_auto_setup import auto_setup_project_memory
    from ...models.project import ProjectFile

    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="پروژه یافت نشد")

    # دریافت فایل‌ها
    files = db.query(ProjectFile).filter(ProjectFile.project_id == project_id).all()
    files_data = [
        {"path": f.file_path, "content": f.content[:2000] if f.content else "", "file_type": f.file_type}
        for f in files
    ]

    # اجرای auto-setup
    try:
        result = await auto_setup_project_memory(
            project_id=project_id,
            project_name=project.name,
            project_description=project.description or "",
            project_type=project.project_type or "",
            files=files_data,
            use_ai=use_ai,
            db_session=db
        )
    except Exception as e:
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
        "fields_created": len(result.get("dynamic_fields", []))
    }


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
