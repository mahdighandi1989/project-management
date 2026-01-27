# -*- coding: utf-8 -*-
"""
API برای ژورنال فعالیت‌ها و گزارشات پروژه
ثبت تمام فعالیت‌های مدل‌های AI در هر پروژه
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import Column, String, Text, DateTime, Integer, Boolean, desc, asc
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import json
import uuid

from ...core.database import get_db, Base, engine
from ...models.project import Project

router = APIRouter()


# ===================== مدل دیتابیس =====================

class ActivityLog(Base):
    """لاگ فعالیت‌های AI در پروژه"""
    __tablename__ = "activity_logs"

    id = Column(String(50), primary_key=True)
    project_id = Column(String(50), nullable=False, index=True)

    # اطلاعات مدل
    model_id = Column(String(100), nullable=False)
    model_provider = Column(String(50))

    # نوع فعالیت
    activity_type = Column(String(50), nullable=False)  # chat, trigger, analysis, generation

    # محتوا
    prompt = Column(Text)
    response = Column(Text)

    # متادیتا
    tokens_used = Column(Integer, default=0)
    latency_ms = Column(Integer, default=0)
    success = Column(Boolean, default=True)
    error_message = Column(Text)

    # فیلد مرتبط (برای trigger ها)
    field_id = Column(String(50))
    field_name = Column(String(200))

    # تاریخ
    created_at = Column(DateTime, default=datetime.utcnow)

    # اطلاعات اضافی (JSON)
    extra_data = Column(Text)


class Report(Base):
    """گزارشات تولید شده"""
    __tablename__ = "project_reports"

    id = Column(String(50), primary_key=True)
    project_id = Column(String(50), nullable=False, index=True)

    # نوع گزارش
    report_type = Column(String(50), default="daily")  # daily, weekly, custom

    # محتوا
    title = Column(String(500))
    content = Column(Text)
    summary = Column(Text)

    # آمار
    total_activities = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)
    models_used = Column(Text)  # JSON list

    # بازه زمانی
    period_start = Column(DateTime)
    period_end = Column(DateTime)

    # تاریخ
    created_at = Column(DateTime, default=datetime.utcnow)
    generated_by = Column(String(100))  # model that generated the report


class ReportTrigger(Base):
    """تنظیمات تریگر گزارش‌گیری"""
    __tablename__ = "report_triggers"

    id = Column(String(50), primary_key=True)
    project_id = Column(String(50), nullable=False, unique=True)

    enabled = Column(Boolean, default=False)
    interval_minutes = Column(Integer, default=1440)  # روزانه
    interval_type = Column(String(20), default="days")

    last_run = Column(DateTime)
    next_run = Column(DateTime)

    # مدل برای تولید گزارش
    report_model = Column(String(100), default="openai")


# ایجاد جداول
Base.metadata.create_all(bind=engine)


# ===================== مدل‌های Pydantic =====================

class ActivityLogCreate(BaseModel):
    """ایجاد لاگ فعالیت"""
    model_id: str
    model_provider: Optional[str] = None
    activity_type: str
    prompt: Optional[str] = None
    response: Optional[str] = None
    tokens_used: int = 0
    latency_ms: int = 0
    success: bool = True
    error_message: Optional[str] = None
    field_id: Optional[str] = None
    field_name: Optional[str] = None
    extra_data: Optional[Dict] = None


class ActivityLogResponse(BaseModel):
    """پاسخ لاگ فعالیت"""
    id: str
    project_id: str
    model_id: str
    model_provider: Optional[str]
    activity_type: str
    prompt: Optional[str]
    response: Optional[str]
    tokens_used: int
    latency_ms: int
    success: bool
    error_message: Optional[str]
    field_id: Optional[str]
    field_name: Optional[str]
    created_at: datetime
    extra_data: Optional[Dict]


class ReportTriggerSettings(BaseModel):
    """تنظیمات تریگر گزارش"""
    enabled: bool = False
    interval_minutes: int = 1440
    interval_type: str = "days"
    report_model: str = "openai"


# ===================== توابع کمکی =====================

def log_to_response(log: ActivityLog) -> Dict:
    """تبدیل لاگ به دیکشنری"""
    extra = {}
    try:
        if log.extra_data:
            extra = json.loads(log.extra_data)
    except:
        pass

    return {
        "id": log.id,
        "project_id": log.project_id,
        "model_id": log.model_id,
        "model_provider": log.model_provider,
        "activity_type": log.activity_type,
        "prompt": log.prompt[:200] + "..." if log.prompt and len(log.prompt) > 200 else log.prompt,
        "response": log.response[:300] + "..." if log.response and len(log.response) > 300 else log.response,
        "tokens_used": log.tokens_used,
        "latency_ms": log.latency_ms,
        "success": log.success,
        "error_message": log.error_message,
        "field_id": log.field_id,
        "field_name": log.field_name,
        "created_at": log.created_at.isoformat() if log.created_at else None,
        "extra_data": extra,
    }


def log_to_full_response(log: ActivityLog) -> Dict:
    """تبدیل لاگ به دیکشنری کامل (بدون truncate)"""
    extra = {}
    try:
        if log.extra_data:
            extra = json.loads(log.extra_data)
    except:
        pass

    return {
        "id": log.id,
        "project_id": log.project_id,
        "model_id": log.model_id,
        "model_provider": log.model_provider,
        "activity_type": log.activity_type,
        "prompt": log.prompt,
        "response": log.response,
        "tokens_used": log.tokens_used,
        "latency_ms": log.latency_ms,
        "success": log.success,
        "error_message": log.error_message,
        "field_id": log.field_id,
        "field_name": log.field_name,
        "created_at": log.created_at.isoformat() if log.created_at else None,
        "extra_data": extra,
    }


# ===================== Endpoints =====================

@router.post("/{project_id}/journal/log")
async def create_activity_log(
    project_id: str,
    log_data: ActivityLogCreate,
    db: Session = Depends(get_db)
):
    """ثبت یک فعالیت جدید در ژورنال"""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="پروژه یافت نشد")

    log = ActivityLog(
        id=f"log_{uuid.uuid4().hex[:12]}",
        project_id=project_id,
        model_id=log_data.model_id,
        model_provider=log_data.model_provider,
        activity_type=log_data.activity_type,
        prompt=log_data.prompt,
        response=log_data.response,
        tokens_used=log_data.tokens_used,
        latency_ms=log_data.latency_ms,
        success=log_data.success,
        error_message=log_data.error_message,
        field_id=log_data.field_id,
        field_name=log_data.field_name,
        extra_data=json.dumps(log_data.extra_data) if log_data.extra_data else None,
        created_at=datetime.utcnow(),
    )

    db.add(log)
    db.commit()

    return {
        "success": True,
        "log_id": log.id,
        "message": "فعالیت ثبت شد"
    }


@router.get("/{project_id}/journal")
async def get_activity_journal(
    project_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    activity_type: Optional[str] = None,
    model_id: Optional[str] = None,
    success: Optional[bool] = None,
    sort_by: str = Query("created_at", regex="^(created_at|tokens_used|latency_ms)$"),
    sort_order: str = Query("desc", regex="^(asc|desc)$"),
    db: Session = Depends(get_db)
):
    """دریافت ژورنال فعالیت‌های پروژه با فیلتر و صفحه‌بندی"""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="پروژه یافت نشد")

    query = db.query(ActivityLog).filter(ActivityLog.project_id == project_id)

    # فیلترها
    if activity_type:
        query = query.filter(ActivityLog.activity_type == activity_type)
    if model_id:
        query = query.filter(ActivityLog.model_id == model_id)
    if success is not None:
        query = query.filter(ActivityLog.success == success)

    # تعداد کل
    total = query.count()

    # مرتب‌سازی
    sort_column = getattr(ActivityLog, sort_by)
    if sort_order == "desc":
        query = query.order_by(desc(sort_column))
    else:
        query = query.order_by(asc(sort_column))

    # صفحه‌بندی
    offset = (page - 1) * page_size
    logs = query.offset(offset).limit(page_size).all()

    return {
        "success": True,
        "journal": [log_to_response(log) for log in logs],
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total": total,
            "total_pages": (total + page_size - 1) // page_size,
        }
    }


@router.get("/{project_id}/journal/stats")
async def get_journal_stats(
    project_id: str,
    days: int = Query(7, ge=1, le=365),
    db: Session = Depends(get_db)
):
    """آمار ژورنال پروژه"""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="پروژه یافت نشد")

    since = datetime.utcnow() - timedelta(days=days)

    logs = db.query(ActivityLog).filter(
        ActivityLog.project_id == project_id,
        ActivityLog.created_at >= since
    ).all()

    # آمار
    total_activities = len(logs)
    total_tokens = sum(log.tokens_used for log in logs)
    total_latency = sum(log.latency_ms for log in logs)
    success_count = sum(1 for log in logs if log.success)

    # گروه‌بندی بر اساس مدل
    by_model = {}
    for log in logs:
        if log.model_id not in by_model:
            by_model[log.model_id] = {"count": 0, "tokens": 0}
        by_model[log.model_id]["count"] += 1
        by_model[log.model_id]["tokens"] += log.tokens_used

    # گروه‌بندی بر اساس نوع فعالیت
    by_type = {}
    for log in logs:
        if log.activity_type not in by_type:
            by_type[log.activity_type] = 0
        by_type[log.activity_type] += 1

    return {
        "success": True,
        "stats": {
            "period_days": days,
            "total_activities": total_activities,
            "total_tokens": total_tokens,
            "avg_latency_ms": total_latency // total_activities if total_activities > 0 else 0,
            "success_rate": round(success_count / total_activities * 100, 1) if total_activities > 0 else 0,
            "by_model": by_model,
            "by_type": by_type,
        }
    }


@router.get("/{project_id}/journal/{log_id}")
async def get_activity_detail(
    project_id: str,
    log_id: str,
    db: Session = Depends(get_db)
):
    """دریافت جزئیات کامل یک فعالیت"""
    log = db.query(ActivityLog).filter(
        ActivityLog.id == log_id,
        ActivityLog.project_id == project_id
    ).first()

    if not log:
        raise HTTPException(status_code=404, detail="فعالیت یافت نشد")

    return {
        "success": True,
        "activity": log_to_full_response(log)
    }


# ===================== گزارشات =====================

@router.get("/{project_id}/reports")
async def get_project_reports(
    project_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db)
):
    """دریافت لیست گزارشات پروژه"""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="پروژه یافت نشد")

    query = db.query(Report).filter(Report.project_id == project_id).order_by(desc(Report.created_at))

    total = query.count()
    offset = (page - 1) * page_size
    reports = query.offset(offset).limit(page_size).all()

    return {
        "success": True,
        "reports": [{
            "id": r.id,
            "report_type": r.report_type,
            "title": r.title,
            "summary": r.summary[:200] + "..." if r.summary and len(r.summary) > 200 else r.summary,
            "total_activities": r.total_activities,
            "total_tokens": r.total_tokens,
            "period_start": r.period_start.isoformat() if r.period_start else None,
            "period_end": r.period_end.isoformat() if r.period_end else None,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        } for r in reports],
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total": total,
            "total_pages": (total + page_size - 1) // page_size,
        }
    }


@router.post("/{project_id}/reports/generate")
async def generate_report(
    project_id: str,
    days: int = Query(7, ge=1, le=30),
    model_id: str = Query("openai"),
    db: Session = Depends(get_db)
):
    """تولید گزارش ساده از فعالیت‌های اخیر"""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="پروژه یافت نشد")

    since = datetime.utcnow() - timedelta(days=days)

    logs = db.query(ActivityLog).filter(
        ActivityLog.project_id == project_id,
        ActivityLog.created_at >= since
    ).order_by(ActivityLog.created_at).all()

    if not logs:
        return {
            "success": False,
            "message": "فعالیتی در این بازه یافت نشد"
        }

    # آمار
    total_tokens = sum(log.tokens_used for log in logs)
    models_used = list(set(log.model_id for log in logs))

    # ساخت خلاصه فعالیت‌ها
    activities_summary = []
    for log in logs[:50]:  # حداکثر 50 فعالیت
        activities_summary.append({
            "type": log.activity_type,
            "model": log.model_id,
            "field": log.field_name,
            "prompt_preview": log.prompt[:100] if log.prompt else None,
            "success": log.success,
            "date": log.created_at.strftime("%Y-%m-%d %H:%M"),
        })

    # ایجاد گزارش
    report = Report(
        id=f"report_{uuid.uuid4().hex[:12]}",
        project_id=project_id,
        report_type="custom",
        title=f"گزارش {days} روز اخیر - {project.name}",
        content=json.dumps(activities_summary, ensure_ascii=False, indent=2),
        summary=f"تعداد {len(logs)} فعالیت با مصرف {total_tokens} توکن",
        total_activities=len(logs),
        total_tokens=total_tokens,
        models_used=json.dumps(models_used),
        period_start=since,
        period_end=datetime.utcnow(),
        created_at=datetime.utcnow(),
        generated_by=model_id,
    )

    db.add(report)
    db.commit()

    return {
        "success": True,
        "report_id": report.id,
        "message": f"گزارش با {len(logs)} فعالیت ایجاد شد"
    }


@router.post("/{project_id}/reports/generate-engineering")
async def generate_engineering_report(
    project_id: str,
    days: int = Query(7, ge=1, le=30),
    model_id: str = Query("claude"),
    auto_create_fields: bool = Query(True),
    db: Session = Depends(get_db)
):
    """
    تولید گزارش مهندسی جامع با:
    - تحلیل کامل ساختار پروژه
    - شناسایی باگ‌ها و مشکلات فنی
    - پیشنهادات بهبود
    - نقشه راه توسعه
    - تولید خودکار فیلدها بر اساس نقشه راه
    """
    from ...services.ai_manager import get_ai_manager
    from ...services.ai_base import Message
    from ...models.project import ProjectFile

    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="پروژه یافت نشد")

    # دریافت فعالیت‌های اخیر
    since = datetime.utcnow() - timedelta(days=days)
    logs = db.query(ActivityLog).filter(
        ActivityLog.project_id == project_id,
        ActivityLog.created_at >= since
    ).order_by(ActivityLog.created_at).all()

    # دریافت فایل‌های پروژه
    files = db.query(ProjectFile).filter(ProjectFile.project_id == project_id).all()
    files_summary = []
    code_samples = []
    total_code_chars = 0
    max_code_chars = 80000  # افزایش به 80K کاراکتر برای تحلیل بهتر

    # اولویت‌بندی فایل‌ها - فایل‌های مهم‌تر اول
    priority_files = ['auth', 'login', 'user', 'route', 'api', 'main', 'app', 'index', 'config', 'setting']
    code_extensions = ['py', 'ts', 'tsx', 'js', 'jsx', 'vue', 'svelte', 'java', 'go', 'rs', 'rb', 'php']

    # مرتب‌سازی فایل‌ها بر اساس اهمیت
    def file_priority(f):
        name = f.file_path.lower()
        score = 0
        for pf in priority_files:
            if pf in name:
                score += 10
        if f.file_type in code_extensions:
            score += 5
        return -score  # منفی برای مرتب‌سازی نزولی

    sorted_files = sorted(files, key=file_priority)

    for f in sorted_files[:100]:  # حداکثر 100 فایل
        files_summary.append({
            "path": f.file_path,
            "type": f.file_type,
            "size": len(f.content) if f.content else 0
        })
        # نمونه کد از فایل‌های کد - با محتوای بیشتر
        if f.content and f.file_type in code_extensions and total_code_chars < max_code_chars:
            content_limit = min(6000, max_code_chars - total_code_chars)  # حداکثر 6K per file
            code_samples.append({
                "path": f.file_path,
                "content": f.content[:content_limit]
            })
            total_code_chars += len(f.content[:content_limit])

    # دریافت فیلدهای فعلی
    existing_fields = []
    try:
        if project.dynamic_fields:
            existing_fields = json.loads(project.dynamic_fields)
    except:
        pass

    # خلاصه فعالیت‌ها
    activities_summary = []
    for log in logs[:30]:
        activities_summary.append({
            "type": log.activity_type,
            "model": log.model_id,
            "field": log.field_name,
            "success": log.success,
            "error": log.error_message if not log.success else None,
            "date": log.created_at.strftime("%Y-%m-%d %H:%M"),
        })

    # ساخت prompt برای AI
    system_prompt = """تو یک مهندس ارشد نرم‌افزار هستی که باید یک گزارش مهندسی جامع و حرفه‌ای تولید کنی.

گزارش باید شامل بخش‌های زیر باشد (حتماً از این ساختار JSON استفاده کن):

```json
{
    "executive_summary": "خلاصه مدیریتی 2-3 پاراگراف از وضعیت پروژه",

    "project_health": {
        "score": 75,
        "status": "متوسط/خوب/عالی/نیاز به توجه",
        "key_metrics": {
            "code_quality": 70,
            "documentation": 50,
            "test_coverage": 30,
            "architecture": 80
        }
    },

    "technical_analysis": {
        "strengths": ["نقطه قوت 1", "نقطه قوت 2"],
        "weaknesses": ["نقطه ضعف 1", "نقطه ضعف 2"],
        "architecture_review": "تحلیل معماری",
        "code_quality_issues": [
            {"file": "path/to/file", "issue": "توضیح مشکل", "severity": "high/medium/low"}
        ]
    },

    "bugs_and_issues": [
        {"title": "عنوان باگ", "description": "توضیحات", "severity": "critical/high/medium/low", "file": "path/to/file", "suggested_fix": "راه حل پیشنهادی"}
    ],

    "security_review": {
        "vulnerabilities": [{"type": "نوع آسیب‌پذیری", "location": "محل", "risk": "high/medium/low"}],
        "recommendations": ["پیشنهاد امنیتی 1", "پیشنهاد امنیتی 2"]
    },

    "performance_analysis": {
        "bottlenecks": ["گلوگاه 1", "گلوگاه 2"],
        "optimization_suggestions": ["پیشنهاد بهینه‌سازی 1"]
    },

    "recommendations": [
        {"priority": "high/medium/low", "title": "عنوان", "description": "توضیحات", "effort": "کم/متوسط/زیاد"}
    ],

    "field_management": {
        "fields_to_archive": ["id_فیلدهایی که انجام شده یا دیگر نیاز نیست"],
        "fields_to_merge": [
            {"source_ids": ["id1", "id2"], "merged_name": "نام جدید", "merged_value": "دستور ادغام‌شده"}
        ],
        "fields_to_update": [
            {"id": "id_فیلد", "new_value": "دستور جدید", "new_priority": 3}
        ]
    },

    "roadmap": {
        "immediate": [
            {"task": "کار فوری 1", "description": "توضیحات کامل برای تولید کد", "action_type": "github_commit", "target_path": "path/to/file.py", "priority": 1, "field_type": "temporary"}
        ],
        "short_term": [
            {"task": "کار کوتاه‌مدت 1", "description": "توضیحات", "action_type": "github_commit", "target_path": "path/to/file.py", "priority": 3, "field_type": "temporary"}
        ],
        "long_term": [
            {"task": "کار بلندمدت 1", "description": "توضیحات", "action_type": "display", "priority": 7, "field_type": "permanent"}
        ]
    },

    "activity_analysis": {
        "success_rate": 75,
        "failed_tasks_analysis": "تحلیل تسک‌های ناموفق",
        "model_performance": {"claude": "خوب", "openai": "متوسط"}
    }
}
```

⚠️ مهم:
- فقط JSON خروجی بده، بدون هیچ توضیح اضافی
- در roadmap، برای هر تسک که نیاز به تولید کد دارد، action_type را "github_commit" و target_path را مسیر فایل هدف قرار بده
- توضیحات هر تسک باید به قدری کامل باشد که AI بتواند مستقیماً کد تولید کند
- در field_management، فیلدهای موجود را بررسی کن و تصمیم بگیر کدام‌ها بایگانی، ادغام یا به‌روزرسانی شوند
- priority از 1 (بالاترین) تا 10 (پایین‌ترین): 1-2=فوری، 3-4=بالا، 5=عادی، 6-7=پایین، 8-10=خیلی پایین
- field_type: "permanent" برای دائمی/تکرارشونده، "temporary" برای یکبار مصرف"""

    user_prompt = f"""پروژه: {project.name}
توضیحات: {project.description or 'ندارد'}
نوع پروژه: {project.project_type or 'نامشخص'}

=== ساختار فایل‌ها ===
{json.dumps(files_summary, ensure_ascii=False, indent=2)}

=== کدهای پروژه ({len(code_samples)} فایل) ===
{json.dumps(code_samples[:30], ensure_ascii=False, indent=2)}

=== فعالیت‌های اخیر ({days} روز) ===
{json.dumps(activities_summary, ensure_ascii=False, indent=2)}

=== فیلدهای فعلی ===
{json.dumps([{"name": f.get("name"), "action_type": f.get("action_type")} for f in existing_fields if not f.get("archived")], ensure_ascii=False, indent=2)}

لطفاً گزارش مهندسی جامع تولید کن."""

    # فراخوانی AI
    ai_manager = get_ai_manager()
    messages = [
        Message(role="system", content=system_prompt),
        Message(role="user", content=user_prompt),
    ]

    try:
        response = await ai_manager.generate(
            model_id=model_id,
            messages=messages,
            max_tokens=8192,
            temperature=0.3,
        )

        # پارس JSON از پاسخ
        report_content = response.content
        report_data = None

        # استخراج JSON از پاسخ
        import re
        json_match = re.search(r'\{[\s\S]*\}', report_content)
        if json_match:
            try:
                report_data = json.loads(json_match.group())
            except json.JSONDecodeError:
                pass

        if not report_data:
            report_data = {"raw_content": report_content}

        # مدیریت هوشمند فیلدها
        created_fields = []
        archived_count = 0
        merged_count = 0
        updated_count = 0

        if auto_create_fields:
            # 1. پردازش field_management - بایگانی، ادغام، به‌روزرسانی
            field_mgmt = report_data.get("field_management", {})

            # بایگانی فیلدها
            for field_id in field_mgmt.get("fields_to_archive", []):
                for field in existing_fields:
                    if field.get("id") == field_id and not field.get("archived"):
                        field["archived"] = True
                        field["archived_at"] = datetime.utcnow().isoformat()
                        field["archived_reason"] = "report review"
                        archived_count += 1

            # ادغام فیلدها
            for merge_info in field_mgmt.get("fields_to_merge", []):
                source_ids = merge_info.get("source_ids", [])
                if len(source_ids) >= 2:
                    merged_attachments = []
                    for sid in source_ids:
                        for field in existing_fields:
                            if field.get("id") == sid:
                                merged_attachments.extend(field.get("attachments", []))
                                field["archived"] = True
                                field["archived_at"] = datetime.utcnow().isoformat()
                                field["archived_reason"] = "merged"

                    merged_field = {
                        "id": str(uuid.uuid4()),
                        "name": merge_info.get("merged_name", "فیلد ادغام‌شده"),
                        "value": merge_info.get("merged_value", ""),
                        "target_models": ["claude"],
                        "action_type": "display",
                        "field_type": "permanent",
                        "priority": 5,
                        "attachments": merged_attachments,
                        "trigger": {"enabled": False, "interval_minutes": 60, "interval_type": "minutes"},
                        "created_from_report": True,
                        "merged_from": source_ids,
                    }
                    existing_fields.append(merged_field)
                    merged_count += 1

            # به‌روزرسانی فیلدها
            for update_info in field_mgmt.get("fields_to_update", []):
                field_id = update_info.get("id")
                for field in existing_fields:
                    if field.get("id") == field_id and not field.get("archived"):
                        if update_info.get("new_value"):
                            field["value"] = update_info["new_value"]
                        if update_info.get("new_priority"):
                            field["priority"] = update_info["new_priority"]
                        field["updated_at"] = datetime.utcnow().isoformat()
                        updated_count += 1

            # 2. تولید فیلدهای جدید از roadmap
            roadmap = report_data.get("roadmap", {})

            for phase_name, phase_tasks in [("immediate", roadmap.get("immediate", [])), ("short_term", roadmap.get("short_term", []))]:
                for task in phase_tasks[:5]:
                    field_name = task.get("task", "تسک جدید")
                    field_value = task.get("description", "")
                    action_type = task.get("action_type", "display")
                    target_path = task.get("target_path")
                    field_type = task.get("field_type", "temporary")
                    priority = task.get("priority", 5)

                    # بررسی وجود فیلد مشابه
                    existing = any(
                        f.get("name", "").lower() == field_name.lower()
                        for f in existing_fields if not f.get("archived")
                    )

                    if not existing and field_value:
                        new_field = {
                            "id": str(uuid.uuid4()),
                            "name": f"[{phase_name}] {field_name}",
                            "value": field_value,
                            "target_models": ["claude"],
                            "action_type": action_type,
                            "target_path": target_path,
                            "archive_after_run": field_type == "temporary",
                            "deploy_after_commit": action_type == "github_commit",
                            "field_type": field_type,
                            "priority": priority,
                            "attachments": [],
                            "trigger": {"enabled": False, "interval_minutes": 60, "interval_type": "minutes"},
                            "created_from_report": True,
                        }
                        existing_fields.append(new_field)
                        created_fields.append(new_field["name"])

            # 3. مرتب‌سازی براساس اولویت و ذخیره
            active = [f for f in existing_fields if not f.get("archived")]
            archived = [f for f in existing_fields if f.get("archived")]
            active.sort(key=lambda x: x.get("priority", 5))
            existing_fields = active + archived

            if created_fields or archived_count or merged_count or updated_count:
                project.dynamic_fields = json.dumps(existing_fields, ensure_ascii=False)
                db.commit()

        # ایجاد گزارش
        total_tokens = sum(log.tokens_used for log in logs) + (response.tokens_used or 0)
        models_used = list(set(log.model_id for log in logs))
        models_used.append(model_id)

        report = Report(
            id=f"eng_report_{uuid.uuid4().hex[:12]}",
            project_id=project_id,
            report_type="engineering",
            title=f"گزارش مهندسی - {project.name}",
            content=json.dumps(report_data, ensure_ascii=False, indent=2),
            summary=report_data.get("executive_summary", f"گزارش مهندسی با تحلیل {len(files)} فایل"),
            total_activities=len(logs),
            total_tokens=total_tokens,
            models_used=json.dumps(list(set(models_used))),
            period_start=since,
            period_end=datetime.utcnow(),
            created_at=datetime.utcnow(),
            generated_by=model_id,
        )

        db.add(report)
        db.commit()

        return {
            "success": True,
            "report_id": report.id,
            "report_type": "engineering",
            "message": f"گزارش مهندسی جامع تولید شد",
            "fields_created": created_fields,
            "fields_count": len(created_fields),
            "fields_archived": archived_count,
            "fields_merged": merged_count,
            "fields_updated": updated_count,
            "project_health_score": report_data.get("project_health", {}).get("score"),
            "bugs_found": len(report_data.get("bugs_and_issues", [])),
            "recommendations_count": len(report_data.get("recommendations", []))
        }

    except Exception as e:
        return {
            "success": False,
            "error": f"خطا در تولید گزارش: {str(e)}"
        }


# ===================== تریگر گزارش =====================

@router.get("/{project_id}/reports/trigger")
async def get_report_trigger(
    project_id: str,
    db: Session = Depends(get_db)
):
    """دریافت تنظیمات تریگر گزارش"""
    trigger = db.query(ReportTrigger).filter(ReportTrigger.project_id == project_id).first()

    if not trigger:
        return {
            "success": True,
            "trigger": {
                "enabled": False,
                "interval_minutes": 1440,
                "interval_type": "days",
                "report_model": "openai",
                "last_run": None,
                "next_run": None,
            }
        }

    return {
        "success": True,
        "trigger": {
            "enabled": trigger.enabled,
            "interval_minutes": trigger.interval_minutes,
            "interval_type": trigger.interval_type,
            "report_model": trigger.report_model,
            "last_run": trigger.last_run.isoformat() if trigger.last_run else None,
            "next_run": trigger.next_run.isoformat() if trigger.next_run else None,
        }
    }


@router.put("/{project_id}/reports/trigger")
async def update_report_trigger(
    project_id: str,
    settings: ReportTriggerSettings,
    db: Session = Depends(get_db)
):
    """بروزرسانی تنظیمات تریگر گزارش"""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="پروژه یافت نشد")

    trigger = db.query(ReportTrigger).filter(ReportTrigger.project_id == project_id).first()

    if not trigger:
        trigger = ReportTrigger(
            id=f"trigger_{uuid.uuid4().hex[:12]}",
            project_id=project_id,
        )
        db.add(trigger)

    trigger.enabled = settings.enabled
    trigger.interval_minutes = settings.interval_minutes
    trigger.interval_type = settings.interval_type
    trigger.report_model = settings.report_model

    # محاسبه زمان بعدی
    if settings.enabled:
        if settings.interval_type == "minutes":
            trigger.next_run = datetime.utcnow() + timedelta(minutes=settings.interval_minutes)
        elif settings.interval_type == "hours":
            trigger.next_run = datetime.utcnow() + timedelta(hours=settings.interval_minutes)
        else:
            trigger.next_run = datetime.utcnow() + timedelta(days=settings.interval_minutes)

    db.commit()

    return {
        "success": True,
        "message": "تنظیمات تریگر ذخیره شد",
        "trigger": {
            "enabled": trigger.enabled,
            "interval_minutes": trigger.interval_minutes,
            "interval_type": trigger.interval_type,
            "report_model": trigger.report_model,
            "next_run": trigger.next_run.isoformat() if trigger.next_run else None,
        }
    }


# ===================== جزئیات گزارش (باید آخر باشد) =====================

@router.get("/{project_id}/reports/{report_id}")
async def get_report_detail(
    project_id: str,
    report_id: str,
    db: Session = Depends(get_db)
):
    """دریافت جزئیات کامل یک گزارش"""
    report = db.query(Report).filter(
        Report.id == report_id,
        Report.project_id == project_id
    ).first()

    if not report:
        raise HTTPException(status_code=404, detail="گزارش یافت نشد")

    models_used = []
    try:
        if report.models_used:
            models_used = json.loads(report.models_used)
    except:
        pass

    return {
        "success": True,
        "report": {
            "id": report.id,
            "report_type": report.report_type,
            "title": report.title,
            "content": report.content,
            "summary": report.summary,
            "total_activities": report.total_activities,
            "total_tokens": report.total_tokens,
            "models_used": models_used,
            "period_start": report.period_start.isoformat() if report.period_start else None,
            "period_end": report.period_end.isoformat() if report.period_end else None,
            "created_at": report.created_at.isoformat() if report.created_at else None,
            "generated_by": report.generated_by,
        }
    }
