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

class MemoryInstructionsRequest(BaseModel):
    """درخواست بروزرسانی باکس حافظه"""
    content: str
    target_models: List[str] = ["all"]  # ["all"] یا ["openai", "claude", "gemini", ...]


class DynamicFieldRequest(BaseModel):
    """درخواست افزودن/ویرایش فیلد پویا"""
    name: str
    value: str
    target_models: List[str] = ["all"]


class UpdateDynamicFieldRequest(BaseModel):
    """درخواست بروزرسانی فیلد پویا"""
    id: str
    name: Optional[str] = None
    value: Optional[str] = None
    target_models: Optional[List[str]] = None


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
        "available_models": AVAILABLE_MODELS
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

    # افزودن فیلد جدید
    new_field = {
        "id": str(uuid.uuid4()),
        "name": request.name,
        "value": request.value,
        "target_models": request.target_models
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
