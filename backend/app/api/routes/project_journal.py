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


@router.post("/{project_id}/reports/generate")
async def generate_report(
    project_id: str,
    days: int = Query(7, ge=1, le=30),
    model_id: str = Query("openai"),
    db: Session = Depends(get_db)
):
    """تولید گزارش از فعالیت‌های اخیر"""
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
