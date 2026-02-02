"""
System Prompts API - مدیریت پرامپت‌های سیستم
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
import json
import uuid
import logging

from ...core.database import get_db
from ...models.system_prompt import SystemPrompt, PromptExecution

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/prompts", tags=["System Prompts"])


# =====================================================
# Pydantic Models
# =====================================================

class PromptCreateRequest(BaseModel):
    """درخواست ایجاد پرامپت جدید"""
    name: str = Field(..., min_length=2, max_length=200)
    description: Optional[str] = None
    category: str = Field(..., pattern="^(health_analysis|engineering_report|auto_setup|deep_analysis|custom)$")
    prompt_type: str = Field(default="instruction", pattern="^(system|user|context|instruction)$")
    content: str = Field(..., min_length=10)
    variables: Optional[Dict[str, str]] = None
    execution_order: int = Field(default=10, ge=1, le=100)
    is_required: bool = False
    depends_on: Optional[List[str]] = None
    parent_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class PromptUpdateRequest(BaseModel):
    """درخواست به‌روزرسانی پرامپت"""
    name: Optional[str] = Field(None, min_length=2, max_length=200)
    description: Optional[str] = None
    content: Optional[str] = Field(None, min_length=10)
    variables: Optional[Dict[str, str]] = None
    execution_order: Optional[int] = Field(None, ge=1, le=100)
    is_required: Optional[bool] = None
    is_active: Optional[bool] = None
    depends_on: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None


class PromptResponse(BaseModel):
    """پاسخ پرامپت"""
    id: str
    name: str
    description: Optional[str]
    category: str
    prompt_type: str
    content: str
    variables: Dict[str, str]
    execution_order: int
    is_required: bool
    is_active: bool
    is_default: bool
    is_locked: bool
    depends_on: List[str]
    parent_id: Optional[str]
    metadata: Dict[str, Any]
    usage_count: int
    success_count: int
    last_used_at: Optional[str]
    last_error: Optional[str]
    created_at: Optional[str]
    updated_at: Optional[str]


class ExecutionStatusResponse(BaseModel):
    """پاسخ وضعیت اجرا"""
    id: str
    prompt_id: str
    prompt_name: str
    project_id: Optional[str]
    status: str
    started_at: Optional[str]
    completed_at: Optional[str]
    duration_seconds: Optional[int]
    result_summary: Optional[str]
    error_message: Optional[str]
    model_used: Optional[str]


# =====================================================
# API Endpoints - CRUD Operations
# =====================================================

@router.get("/categories")
async def get_categories():
    """دریافت لیست دسته‌بندی‌های پرامپت"""
    return {
        "success": True,
        "categories": [
            {
                "id": "health_analysis",
                "name": "تحلیل سلامت",
                "description": "پرامپت‌های مربوط به تحلیل سلامت فایل‌ها و پروژه",
                "icon": "🩺"
            },
            {
                "id": "engineering_report",
                "name": "گزارش مهندسی",
                "description": "پرامپت‌های مربوط به تولید گزارش مهندسی",
                "icon": "📊"
            },
            {
                "id": "auto_setup",
                "name": "راه‌اندازی خودکار",
                "description": "پرامپت‌های مربوط به راه‌اندازی و تنظیم خودکار پروژه",
                "icon": "🚀"
            },
            {
                "id": "deep_analysis",
                "name": "تحلیل عمیق",
                "description": "پرامپت‌های مربوط به تحلیل عمیق و جزئی",
                "icon": "🔬"
            },
            {
                "id": "custom",
                "name": "سفارشی",
                "description": "پرامپت‌های سفارشی کاربر",
                "icon": "⚙️"
            }
        ]
    }


@router.get("")
async def list_prompts(
    category: Optional[str] = Query(None, description="فیلتر بر اساس دسته‌بندی"),
    active_only: bool = Query(True, description="فقط پرامپت‌های فعال"),
    include_defaults: bool = Query(True, description="شامل پرامپت‌های پیش‌فرض"),
    db: Session = Depends(get_db)
):
    """دریافت لیست پرامپت‌ها"""
    try:
        query = db.query(SystemPrompt)

        if category:
            query = query.filter(SystemPrompt.category == category)

        if active_only:
            query = query.filter(SystemPrompt.is_active == True)

        if not include_defaults:
            query = query.filter(SystemPrompt.is_default == False)

        prompts = query.order_by(
            SystemPrompt.category,
            SystemPrompt.execution_order
        ).all()

        # گروه‌بندی بر اساس دسته‌بندی
        grouped = {}
        for prompt in prompts:
            cat = prompt.category
            if cat not in grouped:
                grouped[cat] = []
            grouped[cat].append(prompt.to_dict())

        return {
            "success": True,
            "prompts": [p.to_dict() for p in prompts],
            "grouped": grouped,
            "total": len(prompts)
        }

    except Exception as e:
        logger.error(f"Error listing prompts: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{prompt_id}")
async def get_prompt(
    prompt_id: str,
    db: Session = Depends(get_db)
):
    """دریافت جزئیات یک پرامپت"""
    prompt = db.query(SystemPrompt).filter(SystemPrompt.id == prompt_id).first()

    if not prompt:
        raise HTTPException(status_code=404, detail="پرامپت پیدا نشد")

    return {
        "success": True,
        "prompt": prompt.to_dict()
    }


@router.post("")
async def create_prompt(
    request: PromptCreateRequest,
    db: Session = Depends(get_db)
):
    """ایجاد پرامپت جدید"""
    try:
        # چک تکراری نبودن نام در همان دسته
        existing = db.query(SystemPrompt).filter(
            SystemPrompt.category == request.category,
            SystemPrompt.name == request.name
        ).first()

        if existing:
            raise HTTPException(
                status_code=400,
                detail=f"پرامپتی با نام '{request.name}' در دسته '{request.category}' وجود دارد"
            )

        prompt = SystemPrompt(
            id=str(uuid.uuid4()),
            name=request.name,
            description=request.description,
            category=request.category,
            prompt_type=request.prompt_type,
            content=request.content,
            variables=json.dumps(request.variables or {}, ensure_ascii=False),
            execution_order=request.execution_order,
            is_required=request.is_required,
            depends_on=json.dumps(request.depends_on or [], ensure_ascii=False),
            parent_id=request.parent_id,
            metadata_json=json.dumps(request.metadata or {}, ensure_ascii=False),
            is_active=True,
            is_default=False,
            is_locked=False
        )

        db.add(prompt)
        db.commit()

        logger.info(f"✅ Created new prompt: {prompt.name} ({prompt.category})")

        return {
            "success": True,
            "message": "پرامپت با موفقیت ایجاد شد",
            "prompt": prompt.to_dict()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating prompt: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{prompt_id}")
async def update_prompt(
    prompt_id: str,
    request: PromptUpdateRequest,
    db: Session = Depends(get_db)
):
    """به‌روزرسانی پرامپت"""
    try:
        prompt = db.query(SystemPrompt).filter(SystemPrompt.id == prompt_id).first()

        if not prompt:
            raise HTTPException(status_code=404, detail="پرامپت پیدا نشد")

        # چک قفل بودن - فقط محتوا قابل ویرایش است
        if prompt.is_locked:
            # فقط محتوا و متغیرها قابل ویرایش
            if request.name is not None or request.execution_order is not None:
                raise HTTPException(
                    status_code=403,
                    detail="این پرامپت قفل شده و فقط محتوای آن قابل ویرایش است"
                )

        # به‌روزرسانی فیلدها
        if request.name is not None:
            prompt.name = request.name
        if request.description is not None:
            prompt.description = request.description
        if request.content is not None:
            prompt.content = request.content
        if request.variables is not None:
            prompt.variables = json.dumps(request.variables, ensure_ascii=False)
        if request.execution_order is not None:
            prompt.execution_order = request.execution_order
        if request.is_required is not None:
            prompt.is_required = request.is_required
        if request.is_active is not None:
            prompt.is_active = request.is_active
        if request.depends_on is not None:
            prompt.depends_on = json.dumps(request.depends_on, ensure_ascii=False)
        if request.metadata is not None:
            prompt.metadata_json = json.dumps(request.metadata, ensure_ascii=False)

        db.commit()

        logger.info(f"✅ Updated prompt: {prompt.name}")

        return {
            "success": True,
            "message": "پرامپت با موفقیت به‌روزرسانی شد",
            "prompt": prompt.to_dict()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating prompt: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{prompt_id}")
async def delete_prompt(
    prompt_id: str,
    db: Session = Depends(get_db)
):
    """حذف پرامپت"""
    try:
        prompt = db.query(SystemPrompt).filter(SystemPrompt.id == prompt_id).first()

        if not prompt:
            raise HTTPException(status_code=404, detail="پرامپت پیدا نشد")

        if prompt.is_locked:
            raise HTTPException(
                status_code=403,
                detail="این پرامپت قفل شده و قابل حذف نیست"
            )

        if prompt.is_default:
            raise HTTPException(
                status_code=403,
                detail="پرامپت‌های پیش‌فرض سیستم قابل حذف نیستند"
            )

        prompt_name = prompt.name
        db.delete(prompt)
        db.commit()

        logger.info(f"🗑️ Deleted prompt: {prompt_name}")

        return {
            "success": True,
            "message": f"پرامپت '{prompt_name}' با موفقیت حذف شد"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting prompt: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{prompt_id}/toggle")
async def toggle_prompt(
    prompt_id: str,
    db: Session = Depends(get_db)
):
    """فعال/غیرفعال کردن پرامپت"""
    try:
        prompt = db.query(SystemPrompt).filter(SystemPrompt.id == prompt_id).first()

        if not prompt:
            raise HTTPException(status_code=404, detail="پرامپت پیدا نشد")

        prompt.is_active = not prompt.is_active
        db.commit()

        status = "فعال" if prompt.is_active else "غیرفعال"
        logger.info(f"🔄 Toggled prompt {prompt.name}: {status}")

        return {
            "success": True,
            "message": f"پرامپت '{prompt.name}' {status} شد",
            "is_active": prompt.is_active
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error toggling prompt: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{prompt_id}/duplicate")
async def duplicate_prompt(
    prompt_id: str,
    new_name: str = Query(..., min_length=2),
    db: Session = Depends(get_db)
):
    """کپی کردن پرامپت"""
    try:
        original = db.query(SystemPrompt).filter(SystemPrompt.id == prompt_id).first()

        if not original:
            raise HTTPException(status_code=404, detail="پرامپت پیدا نشد")

        # چک تکراری نبودن نام
        existing = db.query(SystemPrompt).filter(
            SystemPrompt.category == original.category,
            SystemPrompt.name == new_name
        ).first()

        if existing:
            raise HTTPException(
                status_code=400,
                detail=f"پرامپتی با نام '{new_name}' در این دسته وجود دارد"
            )

        new_prompt = SystemPrompt(
            id=str(uuid.uuid4()),
            name=new_name,
            description=f"کپی از {original.name}",
            category=original.category,
            prompt_type=original.prompt_type,
            content=original.content,
            variables=original.variables,
            execution_order=original.execution_order + 1,
            is_required=False,
            depends_on=original.depends_on,
            parent_id=original.parent_id,
            metadata_json=original.metadata_json,
            is_active=True,
            is_default=False,
            is_locked=False
        )

        db.add(new_prompt)
        db.commit()

        logger.info(f"📋 Duplicated prompt {original.name} -> {new_name}")

        return {
            "success": True,
            "message": f"پرامپت کپی شد: {new_name}",
            "prompt": new_prompt.to_dict()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error duplicating prompt: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{prompt_id}/reset")
async def reset_prompt_to_default(
    prompt_id: str,
    db: Session = Depends(get_db)
):
    """بازگردانی پرامپت پیش‌فرض به حالت اولیه"""
    from ...core.database import _seed_default_prompts

    try:
        prompt = db.query(SystemPrompt).filter(SystemPrompt.id == prompt_id).first()

        if not prompt:
            raise HTTPException(status_code=404, detail="پرامپت پیدا نشد")

        if not prompt.is_default:
            raise HTTPException(
                status_code=400,
                detail="فقط پرامپت‌های پیش‌فرض قابل بازگردانی هستند"
            )

        # حذف و ایجاد مجدد پرامپت‌های پیش‌فرض
        # برای سادگی، فقط پیام می‌دهیم
        return {
            "success": False,
            "message": "برای بازگردانی به حالت اولیه، پرامپت را از دیتابیس حذف کنید و سرور را ریستارت کنید"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error resetting prompt: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =====================================================
# Execution Status API
# =====================================================

@router.get("/executions/active")
async def get_active_executions(
    project_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """دریافت اجراهای در حال انجام"""
    try:
        query = db.query(PromptExecution).filter(
            PromptExecution.status.in_(["pending", "running"])
        )

        if project_id:
            query = query.filter(PromptExecution.project_id == project_id)

        executions = query.order_by(PromptExecution.created_at.desc()).all()

        results = []
        for exec in executions:
            prompt = db.query(SystemPrompt).filter(
                SystemPrompt.id == exec.prompt_id
            ).first()

            results.append({
                **exec.to_dict(),
                "prompt_name": prompt.name if prompt else "نامشخص",
                "prompt_category": prompt.category if prompt else "نامشخص"
            })

        return {
            "success": True,
            "executions": results,
            "count": len(results)
        }

    except Exception as e:
        logger.error(f"Error getting active executions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/executions/history")
async def get_execution_history(
    project_id: Optional[str] = None,
    category: Optional[str] = None,
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """دریافت تاریخچه اجراها"""
    try:
        query = db.query(PromptExecution)

        if project_id:
            query = query.filter(PromptExecution.project_id == project_id)

        executions = query.order_by(
            PromptExecution.created_at.desc()
        ).limit(limit).all()

        results = []
        for exec in executions:
            prompt = db.query(SystemPrompt).filter(
                SystemPrompt.id == exec.prompt_id
            ).first()

            if category and prompt and prompt.category != category:
                continue

            results.append({
                **exec.to_dict(),
                "prompt_name": prompt.name if prompt else "نامشخص",
                "prompt_category": prompt.category if prompt else "نامشخص"
            })

        return {
            "success": True,
            "executions": results[:limit],
            "count": len(results)
        }

    except Exception as e:
        logger.error(f"Error getting execution history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/executions/start")
async def start_execution(
    prompt_id: str,
    project_id: Optional[str] = None,
    model_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """شروع اجرای پرامپت (برای ثبت وضعیت real-time)"""
    try:
        prompt = db.query(SystemPrompt).filter(SystemPrompt.id == prompt_id).first()

        if not prompt:
            raise HTTPException(status_code=404, detail="پرامپت پیدا نشد")

        if not prompt.is_active:
            raise HTTPException(
                status_code=400,
                detail="این پرامپت غیرفعال است"
            )

        execution = PromptExecution(
            id=str(uuid.uuid4()),
            prompt_id=prompt_id,
            project_id=project_id,
            status="running",
            started_at=datetime.utcnow(),
            model_used=model_id
        )

        db.add(execution)

        # به‌روزرسانی آمار پرامپت
        prompt.usage_count = (prompt.usage_count or 0) + 1
        prompt.last_used_at = datetime.utcnow()

        db.commit()

        logger.info(f"▶️ Started execution of prompt: {prompt.name}")

        return {
            "success": True,
            "execution_id": execution.id,
            "message": f"اجرای پرامپت '{prompt.name}' شروع شد"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting execution: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/executions/{execution_id}/complete")
async def complete_execution(
    execution_id: str,
    success: bool = True,
    result_summary: Optional[str] = None,
    error_message: Optional[str] = None,
    tokens_used: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """تکمیل اجرای پرامپت"""
    try:
        execution = db.query(PromptExecution).filter(
            PromptExecution.id == execution_id
        ).first()

        if not execution:
            raise HTTPException(status_code=404, detail="اجرا پیدا نشد")

        execution.status = "completed" if success else "failed"
        execution.completed_at = datetime.utcnow()
        execution.result_summary = result_summary
        execution.error_message = error_message
        execution.tokens_used = tokens_used

        if execution.started_at:
            duration = (execution.completed_at - execution.started_at).total_seconds()
            execution.duration_seconds = int(duration)

        # به‌روزرسانی آمار پرامپت
        prompt = db.query(SystemPrompt).filter(
            SystemPrompt.id == execution.prompt_id
        ).first()

        if prompt:
            if success:
                prompt.success_count = (prompt.success_count or 0) + 1
            if error_message:
                prompt.last_error = error_message

        db.commit()

        status = "completed" if success else "failed"
        logger.info(f"⏹️ Execution {status}: {execution_id}")

        return {
            "success": True,
            "message": f"اجرا با وضعیت '{status}' تکمیل شد",
            "execution": execution.to_dict()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error completing execution: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


# =====================================================
# Helper Functions for Services
# =====================================================

def get_active_prompts_for_category(db: Session, category: str) -> List[SystemPrompt]:
    """دریافت پرامپت‌های فعال یک دسته (برای استفاده در سرویس‌ها)"""
    return db.query(SystemPrompt).filter(
        SystemPrompt.category == category,
        SystemPrompt.is_active == True
    ).order_by(SystemPrompt.execution_order).all()


def build_combined_prompt(db: Session, category: str, context: Dict[str, Any] = None) -> str:
    """ساخت پرامپت ترکیبی از تمام پرامپت‌های فعال (برای استفاده در سرویس‌ها)"""
    prompts = get_active_prompts_for_category(db, category)
    if not prompts:
        return ""

    combined = []
    for prompt in prompts:
        content = prompt.content

        # جایگزینی متغیرها
        if context:
            for key, value in context.items():
                placeholder = f"{{{key}}}"
                if placeholder in content:
                    content = content.replace(placeholder, str(value) if value else "")

        combined.append(f"## {prompt.name}\n{content}")

    return "\n\n".join(combined)


# =====================================================
# Validation & Error Handling
# =====================================================

@router.post("/{prompt_id}/validate")
async def validate_prompt(
    prompt_id: str,
    context: Optional[Dict[str, Any]] = None,
    db: Session = Depends(get_db)
):
    """
    اعتبارسنجی پرامپت قبل از اجرا

    بررسی می‌کند:
    - آیا پرامپت فعال است
    - آیا متغیرهای اجباری موجودند
    - آیا پرامپت‌های وابسته فعال هستند
    - آیا محتوای پرامپت معتبر است
    """
    try:
        prompt = db.query(SystemPrompt).filter(SystemPrompt.id == prompt_id).first()

        if not prompt:
            return {
                "valid": False,
                "can_execute": False,
                "error": "پرامپت یافت نشد",
                "error_type": "not_found",
                "fix_instruction": "پرامپت با این شناسه در سیستم وجود ندارد"
            }

        errors = []
        warnings = []

        # بررسی فعال بودن
        if not prompt.is_active:
            errors.append({
                "type": "inactive",
                "message": "پرامپت غیرفعال است",
                "fix": "پرامپت را از طریق تب پرامپت‌ها فعال کنید"
            })

        # بررسی متغیرهای اجباری
        if prompt.variables:
            try:
                variables = json.loads(prompt.variables) if isinstance(prompt.variables, str) else prompt.variables
                missing_vars = []

                for var_name, var_desc in variables.items():
                    placeholder = f"{{{var_name}}}"
                    if placeholder in prompt.content:
                        # چک کن آیا در context هست
                        if context and var_name not in context:
                            missing_vars.append({
                                "name": var_name,
                                "description": var_desc
                            })

                if missing_vars:
                    warnings.append({
                        "type": "missing_variables",
                        "message": f"{len(missing_vars)} متغیر در زمان اجرا باید مقداردهی شوند",
                        "details": missing_vars,
                        "fix": "این متغیرها در زمان اجرا توسط سیستم مقداردهی می‌شوند"
                    })
            except (json.JSONDecodeError, TypeError):
                pass

        # بررسی پرامپت‌های وابسته
        if prompt.depends_on:
            try:
                depends_on = json.loads(prompt.depends_on) if isinstance(prompt.depends_on, str) else prompt.depends_on
                if depends_on:
                    for dep_id in depends_on:
                        dep_prompt = db.query(SystemPrompt).filter(SystemPrompt.id == dep_id).first()
                        if not dep_prompt:
                            errors.append({
                                "type": "missing_dependency",
                                "message": f"پرامپت وابسته {dep_id} یافت نشد",
                                "fix": "پرامپت وابسته را اضافه کنید یا وابستگی را حذف کنید"
                            })
                        elif not dep_prompt.is_active:
                            errors.append({
                                "type": "inactive_dependency",
                                "message": f"پرامپت وابسته '{dep_prompt.name}' غیرفعال است",
                                "fix": f"پرامپت '{dep_prompt.name}' را فعال کنید"
                            })
            except (json.JSONDecodeError, TypeError):
                pass

        # بررسی طول محتوا
        if len(prompt.content) < 10:
            errors.append({
                "type": "content_too_short",
                "message": "محتوای پرامپت بسیار کوتاه است",
                "fix": "محتوای پرامپت باید حداقل 10 کاراکتر باشد"
            })

        if len(prompt.content) > 50000:
            warnings.append({
                "type": "content_too_long",
                "message": "محتوای پرامپت بسیار طولانی است و ممکن است باعث خطای token شود",
                "fix": "پرامپت را به چند بخش کوچکتر تقسیم کنید"
            })

        # بررسی فرمت خروجی
        metadata = {}
        if prompt.metadata_json:
            try:
                metadata = json.loads(prompt.metadata_json) if isinstance(prompt.metadata_json, str) else prompt.metadata_json
            except (json.JSONDecodeError, TypeError):
                pass

        output_format = metadata.get("output_format", "text")
        if output_format == "json" and "```json" not in prompt.content and '{"' not in prompt.content:
            warnings.append({
                "type": "json_format_hint",
                "message": "پرامپت فرمت JSON دارد اما نمونه JSON در متن نیست",
                "fix": "برای نتیجه بهتر، یک نمونه JSON در پرامپت قرار دهید"
            })

        # نتیجه نهایی
        can_execute = len(errors) == 0
        is_valid = can_execute and len(warnings) == 0

        return {
            "valid": is_valid,
            "can_execute": can_execute,
            "prompt_id": prompt_id,
            "prompt_name": prompt.name,
            "errors": errors,
            "warnings": warnings,
            "error_count": len(errors),
            "warning_count": len(warnings),
            "fix_instructions": [e["fix"] for e in errors] if errors else None,
            "summary": "آماده اجرا" if can_execute else f"{len(errors)} خطا وجود دارد"
        }

    except Exception as e:
        logger.error(f"Error validating prompt: {e}")
        return {
            "valid": False,
            "can_execute": False,
            "error": str(e),
            "error_type": "internal_error",
            "fix_instruction": "خطای داخلی رخ داد. لطفاً دوباره تلاش کنید"
        }


@router.get("/category/{category}/validate-all")
async def validate_category_prompts(
    category: str,
    db: Session = Depends(get_db)
):
    """
    اعتبارسنجی تمام پرامپت‌های یک دسته
    """
    try:
        prompts = db.query(SystemPrompt).filter(
            SystemPrompt.category == category
        ).all()

        results = []
        total_errors = 0
        total_warnings = 0
        can_execute_count = 0

        for prompt in prompts:
            validation_result = {
                "valid": True,
                "can_execute": True,
                "error_count": 0,
                "warning_count": 0,
                "errors": [],
                "warnings": []
            }

            # بررسی فعال بودن
            if not prompt.is_active:
                validation_result["can_execute"] = False
                validation_result["errors"].append({
                    "type": "inactive",
                    "message": "پرامپت غیرفعال است"
                })
                validation_result["error_count"] += 1

            # بررسی طول محتوا
            if len(prompt.content) < 10:
                validation_result["can_execute"] = False
                validation_result["errors"].append({
                    "type": "content_too_short",
                    "message": "محتوا کوتاه است"
                })
                validation_result["error_count"] += 1

            results.append({
                "prompt_id": prompt.id,
                "prompt_name": prompt.name,
                "is_active": prompt.is_active,
                "valid": validation_result["error_count"] == 0,
                "can_execute": validation_result["can_execute"],
                "error_count": validation_result["error_count"],
                "warning_count": validation_result["warning_count"],
                "errors": validation_result["errors"],
                "warnings": validation_result["warnings"]
            })

            total_errors += validation_result["error_count"]
            total_warnings += validation_result["warning_count"]
            if validation_result["can_execute"]:
                can_execute_count += 1

        return {
            "success": True,
            "category": category,
            "total_prompts": len(prompts),
            "active_prompts": sum(1 for p in prompts if p.is_active),
            "can_execute_count": can_execute_count,
            "total_errors": total_errors,
            "total_warnings": total_warnings,
            "ready_to_run": total_errors == 0,
            "prompts": results,
            "summary": f"{can_execute_count}/{len(prompts)} پرامپت آماده اجرا"
        }

    except Exception as e:
        logger.error(f"Error validating category prompts: {e}")
        raise HTTPException(status_code=500, detail=str(e))
