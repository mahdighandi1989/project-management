"""
API routes for Project Memory Management
مسیرهای API برای مدیریت حافظه و دستورات پروژه
"""

import json
import uuid
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional
from sqlalchemy.orm import Session

from ...core.database import get_db
from ...models.project import Project

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


class UpdateDynamicFieldRequest(BaseModel):
    """درخواست بروزرسانی فیلد پویا"""
    id: str
    name: Optional[str] = None
    value: Optional[str] = None
    target_models: Optional[List[str]] = None
    trigger: Optional[TriggerSettings] = None


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

        return {
            "success": True,
            "model_id": response.model_id,
            "content": response.content,
            "tokens_used": response.tokens_used,
            "latency_ms": response.latency_ms,
        }

    except Exception as e:
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
        for field in dynamic_fields:
            if field.get("id") == field_id:
                target_field = field
                break

        if not target_field:
            raise HTTPException(status_code=404, detail="فیلد یافت نشد")

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

        user_prompt = f"دستور: {target_field.get('name', 'فیلد')}\n\n{target_field.get('value', '')}"

        # ارسال به مدل(های) هدف
        target_models = target_field.get("target_models", ["all"])
        if "all" in target_models or not target_models:
            target_models = ["claude"]  # پیش‌فرض claude بهتره برای کد

        results = []
        ai_manager = get_ai_manager()

        for model_id in target_models:
            if model_id == "all":
                continue
            try:
                messages = [
                    Message(role="system", content=system_prompt),
                    Message(role="user", content=user_prompt),
                ]

                # اجرا با timeout 60 ثانیه
                response = await asyncio.wait_for(
                    ai_manager.generate(
                        model_id=model_id,
                        messages=messages,
                        max_tokens=4096,
                        temperature=0.7,
                    ),
                    timeout=60.0
                )

                results.append({
                    "model_id": response.model_id,
                    "content": response.content,
                    "tokens_used": response.tokens_used,
                    "success": True
                })
            except asyncio.TimeoutError:
                results.append({
                    "model_id": model_id,
                    "error": "Timeout - پاسخ مدل بیش از 60 ثانیه طول کشید",
                    "success": False
                })
            except Exception as e:
                results.append({
                    "model_id": model_id,
                    "error": str(e),
                    "success": False
                })

        # بروزرسانی last_run
        for field in dynamic_fields:
            if field.get("id") == field_id:
                if "trigger" not in field:
                    field["trigger"] = {}
                field["trigger"]["last_run"] = datetime.utcnow().isoformat()
                break

        project.dynamic_fields = json.dumps(dynamic_fields, ensure_ascii=False)
        db.commit()

        return {
            "success": True,
            "field_id": field_id,
            "field_name": target_field.get("name"),
            "results": results,
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
