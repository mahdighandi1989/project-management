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
    validate_health_issues: bool = Query(True),  # 🆕 اعتبارسنجی نتایج health analysis
    db: Session = Depends(get_db)
):
    """
    تولید گزارش مهندسی جامع با:
    - تحلیل کامل ساختار پروژه
    - 🆕 اعتبارسنجی نتایج آخرین health analysis توسط مدل‌های منتخب
    - شناسایی باگ‌ها و مشکلات فنی
    - پیشنهادات بهبود
    - نقشه راه توسعه
    - تولید خودکار فیلدها با مارکر اعتبارسنجی
    - 🆕 آرشیو مسائل رد شده برای مشاهده
    """
    from ...services.ai_manager import get_ai_manager
    from ...services.ai_base import Message
    from ...models.project import ProjectFile
    import logging
    logger = logging.getLogger(__name__)

    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="پروژه یافت نشد")

    # دریافت فعالیت‌های اخیر
    since = datetime.utcnow() - timedelta(days=days)
    logs = db.query(ActivityLog).filter(
        ActivityLog.project_id == project_id,
        ActivityLog.created_at >= since
    ).order_by(ActivityLog.created_at).all()

    # دریافت تنظیمات محدودیت‌ها
    from .settings import get_ai_limits_sync
    ai_limits = get_ai_limits_sync(db)
    limits_enabled = ai_limits.get("limits_enabled", False)

    # مقادیر محدودیت (0 = نامحدود)
    max_files = ai_limits.get("max_files_for_report", 0) if limits_enabled else 0
    max_code_samples = ai_limits.get("max_code_samples_for_report", 0) if limits_enabled else 0
    max_chars_per_sample = ai_limits.get("max_chars_per_code_sample", 0) if limits_enabled else 0

    # دریافت فایل‌های پروژه
    files = db.query(ProjectFile).filter(ProjectFile.project_id == project_id).all()
    files_summary = []
    code_samples = []
    total_code_chars = 0

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

    files_added = 0
    for f in sorted_files:
        # چک محدودیت تعداد فایل (0 = نامحدود)
        if max_files > 0 and files_added >= max_files:
            break

        files_summary.append({
            "path": f.file_path,
            "type": f.file_type,
            "size": len(f.content) if f.content else 0
        })
        files_added += 1

        # نمونه کد از فایل‌های کد
        if f.content and f.file_type in code_extensions:
            # چک محدودیت تعداد نمونه کد (0 = نامحدود)
            if max_code_samples > 0 and len(code_samples) >= max_code_samples:
                continue

            # محتوای فایل (0 = بدون محدودیت)
            content = f.content if max_chars_per_sample == 0 else f.content[:max_chars_per_sample]
            code_samples.append({
                "path": f.file_path,
                "content": content
            })
            total_code_chars += len(content)

    # دریافت فیلدهای فعلی
    existing_fields = []
    try:
        if project.dynamic_fields:
            existing_fields = json.loads(project.dynamic_fields)
    except:
        pass

    # ====================================
    # 🆕 دریافت و آماده‌سازی نتایج health analysis برای اعتبارسنجی
    # ====================================
    health_analysis_issues = []
    health_analysis_summary = ""
    partial_results = {}

    # 🔴 DEBUG: Log raw data before extraction
    logger.info(f"=" * 60)
    logger.info(f"🔴 DEBUG: Starting health issues extraction for project {project_id}")
    logger.info(f"🔴 DEBUG: validate_health_issues = {validate_health_issues}")
    logger.info(f"🔴 DEBUG: project.issues_found type: {type(project.issues_found)}")
    logger.info(f"🔴 DEBUG: project.issues_found length: {len(project.issues_found or '')}")
    if project.issues_found:
        logger.info(f"🔴 DEBUG: project.issues_found preview: {project.issues_found[:500]}...")
    else:
        # 🔴 CRITICAL: Try to refresh from database!
        logger.error(f"🔴🔴🔴 CRITICAL: project.issues_found is None/empty! Trying to refresh from DB...")
        db.refresh(project)
        logger.info(f"🔴 DEBUG: After refresh: project.issues_found length: {len(project.issues_found or '')}")
        if project.issues_found:
            logger.info(f"🔴 DEBUG: After refresh preview: {project.issues_found[:500]}...")
    logger.info(f"=" * 60)

    def normalize_issue(issue, file_path=None, source_models=None):
        """نرمال‌سازی فرمت ایراد از منابع مختلف"""
        return {
            "file": issue.get("file") or file_path or "unknown",
            "type": issue.get("type") or issue.get("category") or "code_quality",
            "severity": issue.get("severity") or "medium",
            "message": issue.get("message") or issue.get("description") or issue.get("problem") or str(issue),
            "line": issue.get("line"),
            "source_models": source_models or issue.get("source_models") or ["unknown"],
        }

    # 1. دریافت از file_health_map (نتایج تحلیل هر فایل)
    if project.file_health_map:
        try:
            file_map = json.loads(project.file_health_map)
            for file_path, file_data in file_map.items():
                if isinstance(file_data, dict):
                    # استخراج issues از داخل file_data
                    file_issues = file_data.get("issues", [])
                    if isinstance(file_issues, list):
                        for issue in file_issues:
                            if isinstance(issue, dict):
                                health_analysis_issues.append(normalize_issue(
                                    issue,
                                    file_path=file_path,
                                    source_models=file_data.get("analyzed_by", ["file_analysis"])
                                ))
        except Exception as e:
            logger.warning(f"Error parsing file_health_map: {e}")

    logger.info(f"🔴 DEBUG: After file_health_map extraction: {len(health_analysis_issues)} issues")

    # 2. دریافت نتایج از analysis_progress (partial_results)
    if project.analysis_progress:
        try:
            progress_data = json.loads(project.analysis_progress)
            partial_results = progress_data.get("partial_results", {})

            # استخراج issues از micro analysis
            if "micro" in partial_results:
                micro_results = partial_results["micro"]
                if isinstance(micro_results, dict):
                    for file_path, file_data in micro_results.items():
                        if isinstance(file_data, dict):
                            issues = file_data.get("issues", [])
                            if isinstance(issues, list):
                                for issue in issues:
                                    if isinstance(issue, dict):
                                        health_analysis_issues.append(normalize_issue(
                                            issue,
                                            file_path=file_path,
                                            source_models=file_data.get("analyzed_by", [])
                                        ))

            # استخراج issues از structural analysis
            if "structural" in partial_results:
                structural = partial_results["structural"]
                if isinstance(structural, dict):
                    for issue in structural.get("issues", []):
                        if isinstance(issue, dict):
                            health_analysis_issues.append(normalize_issue(
                                issue,
                                file_path=issue.get("file", "structural"),
                                source_models=["structural_analysis"]
                            ))
        except Exception as e:
            logger.warning(f"Error parsing analysis_progress: {e}")

    logger.info(f"🔴 DEBUG: After analysis_progress extraction: {len(health_analysis_issues)} issues")

    # 3. دریافت از issues_found (ذخیره شده از قبل) - این منبع اصلی است!
    logger.info(f"🔴 DEBUG: Checking project.issues_found...")
    if project.issues_found:
        try:
            stored_issues = json.loads(project.issues_found)
            logger.info(f"🔴 DEBUG: Parsed issues_found: type={type(stored_issues)}, count={len(stored_issues) if isinstance(stored_issues, list) else 'N/A'}")
            if isinstance(stored_issues, list):
                # ادغام با issues موجود (بدون تکرار)
                existing_keys = {f"{i.get('file', '')}:{i.get('line', '')}:{i.get('message', '')[:50]}" for i in health_analysis_issues}
                added_count = 0
                for issue in stored_issues:
                    if isinstance(issue, dict):
                        normalized = normalize_issue(issue)
                        key = f"{normalized['file']}:{normalized.get('line', '')}:{normalized['message'][:50]}"
                        if key not in existing_keys:
                            health_analysis_issues.append(normalized)
                            existing_keys.add(key)
                            added_count += 1
                logger.info(f"🔴 DEBUG: Added {added_count} issues from issues_found (after dedup)")
            else:
                logger.warning(f"🔴 DEBUG: issues_found is not a list! Content: {str(stored_issues)[:200]}")
        except Exception as e:
            logger.warning(f"Error parsing issues_found: {e}")
    else:
        logger.warning(f"🔴 DEBUG: project.issues_found is EMPTY!")

    logger.info(f"🔴 DEBUG: After issues_found extraction: {len(health_analysis_issues)} issues")

    # 4. دریافت از health_scores (ممکن است issues داخلش باشد)
    if project.health_scores:
        try:
            scores = json.loads(project.health_scores)
            if isinstance(scores, dict) and "issues" in scores:
                for issue in scores.get("issues", []):
                    if isinstance(issue, dict):
                        health_analysis_issues.append(normalize_issue(issue))
        except:
            pass

    # Log detailed extraction stats
    logger.info(f"🔍 Health issues extraction from project {project_id}:")
    logger.info(f"   - project.file_health_map: {len(project.file_health_map or '')} chars")
    logger.info(f"   - project.analysis_progress: {len(project.analysis_progress or '')} chars")
    logger.info(f"   - project.issues_found: {len(project.issues_found or '')} chars")
    logger.info(f"   - project.health_scores: {len(project.health_scores or '')} chars")
    logger.info(f"📊 Total health issues found for validation: {len(health_analysis_issues)}")

    # Group issues by severity for logging
    if health_analysis_issues:
        severity_counts = {}
        for issue in health_analysis_issues:
            sev = issue.get("severity", "unknown")
            severity_counts[sev] = severity_counts.get(sev, 0) + 1
        logger.info(f"📊 Issues by severity: {severity_counts}")
    else:
        logger.warning(f"⚠️ No health issues found from any source. Attempting recovery...")
        # 🔴 FAILSAFE: Try to force-load issues from issues_found
        if project.issues_found:
            try:
                stored = json.loads(project.issues_found)
                if isinstance(stored, list) and len(stored) > 0:
                    logger.info(f"🔴 FAILSAFE: Found {len(stored)} issues in issues_found, force-loading...")
                    for issue in stored:
                        if isinstance(issue, dict):
                            health_analysis_issues.append(normalize_issue(issue))
                    logger.info(f"🔴 FAILSAFE: Loaded {len(health_analysis_issues)} issues from issues_found")
            except Exception as e:
                logger.error(f"🔴 FAILSAFE failed: {e}")

        # Additional debug for empty issues
        if not health_analysis_issues:
            logger.error(f"🔴🔴🔴 CRITICAL: Still no issues after failsafe!")
            if project.file_health_map:
                try:
                    fhm = json.loads(project.file_health_map)
                    total_issues_in_map = sum(len(fd.get("issues", [])) for fd in fhm.values() if isinstance(fd, dict))
                    total_issues_count = sum(fd.get("issues_count", 0) for fd in fhm.values() if isinstance(fd, dict))
                    logger.info(f"   - file_health_map has {len(fhm)} files, {total_issues_in_map} issues embedded, {total_issues_count} issues_count")
                except:
                    pass

    # ساخت خلاصه health analysis برای prompt
    if health_analysis_issues:
        health_analysis_summary = f"""

=== 🔍 نتایج آخرین health analysis ({len(health_analysis_issues)} ایراد شناسایی شده) ===

⚠️ بسیار مهم: این ایرادات توسط تحلیل سلامت شناسایی شده‌اند و باید توسط شما اعتبارسنجی شوند!
- هر ایراد را با کد واقعی مقایسه کن
- اگر ایراد واقعاً وجود دارد، در validated_issues قرار بده (با create_field=true)
- اگر ایراد اشتباه است، در rejected_issues با دلیل رد شدن قرار بده

لیست ایرادات برای بررسی:
{json.dumps(health_analysis_issues[:30], ensure_ascii=False, indent=2)}
"""
    else:
        health_analysis_summary = """

=== 🔍 نتایج تحلیل سلامت ===
هیچ ایرادی از تحلیل سلامت قبلی یافت نشد.
در صورتی که مشکلاتی در کد مشاهده می‌کنید، آنها را در بخش bugs_and_issues گزارش کنید.
"""

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

🔴🔴🔴 بسیار مهم - اعتبارسنجی health analysis 🔴🔴🔴
اگر در بخش ورودی "نتایج آخرین health analysis" وجود دارد، باید:
1. هر ایراد را یک به یک بررسی کنی
2. ایرادات تایید شده را در validated_issues قرار بدی
3. ایرادات رد شده را در rejected_issues قرار بدی
4. بخش health_analysis_validation را حتماً در JSON خروجی قرار بدی

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
    },

    "health_analysis_validation": {
        "total_reviewed": 15,
        "validated_issues": [
            {
                "original_issue": {"file": "path/file.py", "type": "security", "message": "..."},
                "validation_score": 95,
                "validation_note": "این ایراد تایید می‌شود چون...",
                "priority": "high",
                "create_field": true
            }
        ],
        "rejected_issues": [
            {
                "original_issue": {"file": "path/file.py", "type": "unused", "message": "..."},
                "rejection_reason": "این متغیر در خط 45 استفاده شده است",
                "validation_score": 20,
                "source_model_error": "مدل X اشتباهاً این را ایراد تشخیص داده"
            }
        ],
        "validation_summary": "خلاصه اعتبارسنجی: از 15 ایراد، 10 تایید و 5 رد شد"
    },

    "comprehensive_ideal_state": {
        "description": "توضیح کامل حالت ایده‌آل پروژه (3-5 پاراگراف)",
        "current_deficiencies": ["کمبود 1", "کمبود 2"],
        "unexecuted_tasks": ["تسک اجرا نشده 1", "تسک اجرا نشده 2"],
        "system_structure": {
            "overview": "ساختار کلی سیستم",
            "components": ["کامپوننت 1", "کامپوننت 2"],
            "wiring": "نحوه اتصال و سیم‌کشی بین بخش‌ها"
        },
        "roadmap_integration": "نحوه رسیدن از وضعیت فعلی به حالت ایده‌آل"
    }
}
```

⚠️ مهم:
- فقط JSON خروجی بده، بدون هیچ توضیح اضافی
- در roadmap، برای هر تسک که نیاز به تولید کد دارد، action_type را "github_commit" و target_path را مسیر فایل هدف قرار بده
- توضیحات هر تسک باید به قدری کامل باشد که AI بتواند مستقیماً کد تولید کند
- در field_management، فیلدهای موجود را بررسی کن و تصمیم بگیر کدام‌ها بایگانی، ادغام یا به‌روزرسانی شوند
- priority از 1 (بالاترین) تا 10 (پایین‌ترین): 1-2=فوری، 3-4=بالا، 5=عادی، 6-7=پایین، 8-10=خیلی پایین
- field_type: "permanent" برای دائمی/تکرارشونده، "temporary" برای یکبار مصرف

🔴 اعتبارسنجی health analysis (بسیار مهم):
- تمام ایرادات ارسال شده از health analysis را یک به یک بررسی کن
- با نگاه به کد واقعی، مشخص کن آیا هر ایراد معتبر است یا نه
- ایرادات معتبر را در validated_issues با create_field=true قرار بده (فیلد ساخته می‌شود)
- ایرادات نامعتبر را در rejected_issues با دلیل دقیق رد شدن قرار بده
- validation_score از 0-100: بالای 70 = معتبر، زیر 30 = رد شده

🟢 حالت ایده‌آل جامع (comprehensive_ideal_state):
- وضعیت ایده‌آل باید شامل: کمبودها، تسک‌های اجرا نشده، ساختار سیستم، سیم‌کشی و نقشه راه باشد
- این بخش برای راهنمایی توسعه‌دهنده بسیار مهم است"""

    # ساخت خلاصه فیلدهای اجرا نشده برای ideal state
    unexecuted_fields = [
        {"name": f.get("name"), "value": f.get("value", "")[:200], "priority": f.get("priority", 5)}
        for f in existing_fields
        if not f.get("archived") and f.get("field_type") == "temporary" and not f.get("executed")
    ]

    user_prompt = f"""پروژه: {project.name}
توضیحات: {project.description or 'ندارد'}
نوع پروژه: {project.project_type or 'نامشخص'}

=== ساختار فایل‌ها ===
{json.dumps(files_summary, ensure_ascii=False, indent=2)}

=== کدهای پروژه ({len(code_samples)} فایل، {total_code_chars:,} کاراکتر) ===
{json.dumps(code_samples, ensure_ascii=False, indent=2)}
{health_analysis_summary if validate_health_issues else ''}
=== فعالیت‌های اخیر ({days} روز) ===
{json.dumps(activities_summary, ensure_ascii=False, indent=2)}

=== فیلدهای فعلی (غیربایگانی) ===
{json.dumps([{"id": f.get("id"), "name": f.get("name"), "action_type": f.get("action_type"), "field_type": f.get("field_type"), "executed": f.get("executed", False)} for f in existing_fields if not f.get("archived")], ensure_ascii=False, indent=2)}

=== فیلدهای اجرا نشده (برای ideal state) ===
{json.dumps(unexecuted_fields, ensure_ascii=False, indent=2)}

=== حالت ایده‌آل فعلی ===
{project.ideal_state or 'تعریف نشده'}

=== نقشه راه فعلی ===
{(project.roadmap_content or '')[:2000] if project.roadmap_content else 'تعریف نشده'}

لطفاً گزارش مهندسی جامع تولید کن.

⚠️ بسیار مهم:
1. اگر بخش "نتایج آخرین health analysis" بالا وجود دارد، حتماً تمام ایرادات را یک به یک بررسی و اعتبارسنجی کن
2. بخش health_analysis_validation را حتماً در خروجی JSON قرار بده
3. برای هر ایراد تایید شده، یک فیلد پویا ایجاد می‌شود تا توسعه‌دهنده آن را رفع کند"""

    # فراخوانی AI
    ai_manager = get_ai_manager()
    messages = [
        Message(role="system", content=system_prompt),
        Message(role="user", content=user_prompt),
    ]

    # 🔴 DEBUG: Final summary before AI call
    logger.info(f"=" * 60)
    logger.info(f"🔴 DEBUG: FINAL SUMMARY before AI call:")
    logger.info(f"   - validate_health_issues: {validate_health_issues}")
    logger.info(f"   - health_analysis_issues count: {len(health_analysis_issues)}")
    logger.info(f"   - health_analysis_summary length: {len(health_analysis_summary)}")
    logger.info(f"   - health_analysis_summary included in prompt: {'yes' if (validate_health_issues and len(health_analysis_issues) > 0) else 'NO!'}")
    logger.info(f"   - user_prompt length: {len(user_prompt)}")
    logger.info(f"   - system_prompt length: {len(system_prompt)}")
    if len(health_analysis_issues) == 0:
        logger.error(f"🔴🔴🔴 CRITICAL: No health issues to validate! Check extraction logic above.")
    logger.info(f"=" * 60)

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

        # استخراج JSON از پاسخ - بهبود یافته برای مدیریت markdown code blocks
        import re

        def try_fix_json(json_str):
            """تلاش برای تصحیح خطاهای رایج JSON"""
            fixes = [
                # حذف trailing commas قبل از } یا ]
                (r',(\s*[}\]])', r'\1'),
                # حذف trailing comma در آخر
                (r',\s*$', ''),
                # تصحیح newlines در strings
                (r'(?<!\\)\n(?=[^"]*"[^"]*$)', r'\\n'),
            ]

            fixed = json_str
            for pattern, replacement in fixes:
                fixed = re.sub(pattern, replacement, fixed)
            return fixed

        def attempt_json_parse(json_str, source_name):
            """تلاش برای پارس JSON با تصحیح خودکار"""
            # تلاش اول - مستقیم
            try:
                return json.loads(json_str), None
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse JSON from {source_name}: {e}")

                # تلاش دوم - با تصحیح
                try:
                    fixed = try_fix_json(json_str)
                    result = json.loads(fixed)
                    logger.info(f"Successfully parsed JSON from {source_name} after auto-fix")
                    return result, None
                except json.JSONDecodeError as e2:
                    return None, str(e2)

        # 1. ابتدا تلاش برای استخراج از داخل ```json ... ``` یا ``` ... ```
        code_block_match = re.search(r'```(?:json)?\s*([\s\S]*?)```', report_content)
        if code_block_match:
            json_str = code_block_match.group(1).strip()
            report_data, error = attempt_json_parse(json_str, "code block")
            if report_data:
                logger.info(f"Successfully parsed JSON from code block ({len(json_str)} chars)")

        # 2. اگر از code block استخراج نشد، تلاش برای پیدا کردن مستقیم JSON
        if not report_data:
            # پیدا کردن اولین { و آخرین }
            first_brace = report_content.find('{')
            last_brace = report_content.rfind('}')
            if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
                json_str = report_content[first_brace:last_brace+1]
                report_data, error = attempt_json_parse(json_str, "direct extraction")
                if report_data:
                    logger.info(f"Successfully parsed JSON directly ({len(json_str)} chars)")

        # 3. اگر هنوز پارس نشده، محتوای خام را ذخیره کن
        if not report_data:
            logger.error(f"Could not parse JSON from AI response after all attempts. Content preview: {report_content[:500]}")
            report_data = {"raw_content": report_content, "parse_error": True}
        else:
            logger.info(f"Report data parsed successfully. Keys: {list(report_data.keys())}")

        # ====================================
        # 🆕 پردازش نتایج اعتبارسنجی health analysis
        # ====================================
        validated_issues_count = 0
        rejected_issues_count = 0
        new_rejected_archive = []

        # لاگ برای debug
        logger.info(f"🔍 Checking for health_analysis_validation in report_data...")
        logger.info(f"   - validate_health_issues param: {validate_health_issues}")
        logger.info(f"   - 'health_analysis_validation' in report_data: {'health_analysis_validation' in report_data}")
        logger.info(f"   - Health issues sent to AI: {len(health_analysis_issues)}")
        if report_data and not report_data.get("raw_content"):
            logger.info(f"   - Report data keys: {list(report_data.keys())}")

        if validate_health_issues and "health_analysis_validation" in report_data:
            validation_data = report_data["health_analysis_validation"]

            # ذخیره نتایج اعتبارسنجی
            validation_results = {
                "validated_at": datetime.utcnow().isoformat(),
                "validator_model": model_id,
                "total_issues_reviewed": validation_data.get("total_reviewed", 0),
                "validated_count": len(validation_data.get("validated_issues", [])),
                "rejected_count": len(validation_data.get("rejected_issues", [])),
                "validation_summary": validation_data.get("validation_summary", ""),
                "validated_issues": validation_data.get("validated_issues", []),
            }
            project.last_validation_results = json.dumps(validation_results, ensure_ascii=False)
            validated_issues_count = validation_results["validated_count"]
            rejected_issues_count = validation_results["rejected_count"]

            # پردازش ایرادات رد شده و اضافه به آرشیو
            existing_archive = []
            if project.rejected_issues_archive:
                try:
                    existing_archive = json.loads(project.rejected_issues_archive)
                except:
                    pass

            for rejected in validation_data.get("rejected_issues", []):
                archive_entry = {
                    "id": f"rej_{uuid.uuid4().hex[:8]}",
                    "original_issue": rejected.get("original_issue", {}),
                    "source_model": rejected.get("original_issue", {}).get("source_models", ["unknown"])[0] if isinstance(rejected.get("original_issue", {}).get("source_models"), list) else "unknown",
                    "validator_model": model_id,
                    "rejection_reason": rejected.get("rejection_reason", ""),
                    "rejected_at": datetime.utcnow().isoformat(),
                    "validation_score": rejected.get("validation_score", 0),
                }
                new_rejected_archive.append(archive_entry)

            # ادغام با آرشیو موجود (حداکثر 100 آیتم)
            combined_archive = new_rejected_archive + existing_archive
            project.rejected_issues_archive = json.dumps(combined_archive[:100], ensure_ascii=False)

            # 🔴 CRITICAL: Commit validation results immediately
            db.commit()
            logger.info(f"✅ Health validation: {validated_issues_count} validated, {rejected_issues_count} rejected - COMMITTED to DB")

        # 🆕 Fallback: اگر AI بخش health_analysis_validation را برنگرداند (یا JSON پارس نشد)، فیلدها را مستقیماً از health issues بساز
        elif validate_health_issues and health_analysis_issues and (report_data.get("parse_error") or "health_analysis_validation" not in report_data):
            parse_error = report_data.get("parse_error", False)
            has_validation = "health_analysis_validation" in report_data
            logger.warning(f"⚠️ FALLBACK TRIGGERED: parse_error={parse_error}, has_validation={has_validation}")
            logger.warning(f"⚠️ Processing ALL {len(health_analysis_issues)} health issues directly.")

            # 🆕 گروه‌بندی ایرادات براساس severity
            critical_issues = [i for i in health_analysis_issues if i.get("severity") == "critical"]
            high_issues = [i for i in health_analysis_issues if i.get("severity") == "high"]
            medium_issues = [i for i in health_analysis_issues if i.get("severity") == "medium"]
            low_issues = [i for i in health_analysis_issues if i.get("severity") == "low"]

            logger.info(f"📊 Issues breakdown: critical={len(critical_issues)}, high={len(high_issues)}, medium={len(medium_issues)}, low={len(low_issues)}")

            # ذخیره این به عنوان validation results
            validation_results = {
                "validated_at": datetime.utcnow().isoformat(),
                "validator_model": model_id,
                "total_issues_reviewed": len(health_analysis_issues),
                "validated_count": 0,
                "rejected_count": 0,
                "pending_count": 0,  # 🆕 ایرادات در انتظار بررسی
                "validation_summary": "",
                "validated_issues": [],
                "pending_issues": [],  # 🆕 ایرادات medium/low که فیلد ایجاد نشد
                "fallback_mode": True,
            }

            # 🆕 ایجاد فیلد برای تمام critical و high issues (بدون محدودیت 10)
            issues_for_fields = critical_issues + high_issues
            logger.info(f"📝 Creating fields for ALL {len(issues_for_fields)} critical+high issues")

            # اگر critical/high نبود، medium با اولویت بالا رو هم اضافه کن (حداکثر 15)
            if len(issues_for_fields) < 5 and medium_issues:
                additional_medium = medium_issues[:15 - len(issues_for_fields)]
                issues_for_fields.extend(additional_medium)
                logger.info(f"📝 Added {len(additional_medium)} medium issues (total: {len(issues_for_fields)})")

            # ایجاد validated_issues برای فیلدسازی
            for issue in issues_for_fields:
                validation_results["validated_issues"].append({
                    "original_issue": issue,
                    "validation_score": 80 if issue.get("severity") in ["critical", "high"] else 70,
                    "validation_note": "تایید خودکار (Fallback mode) - اولویت بالا",
                    "priority": issue.get("severity"),
                    "create_field": True
                })
                validated_issues_count += 1

            # 🆕 بقیه issues رو به عنوان pending ثبت کن (medium/low که فیلد ایجاد نشد)
            remaining_issues = [i for i in health_analysis_issues if i not in issues_for_fields]
            for issue in remaining_issues:
                validation_results["pending_issues"].append({
                    "original_issue": issue,
                    "validation_score": 50,
                    "validation_note": "در انتظار بررسی - فیلد ایجاد نشد (severity پایین)",
                    "priority": issue.get("severity"),
                    "create_field": False
                })

            validation_results["validated_count"] = validated_issues_count
            validation_results["pending_count"] = len(remaining_issues)
            validation_results["validation_summary"] = f"AI بخش اعتبارسنجی را برنگرداند. از {len(health_analysis_issues)} ایراد: {validated_issues_count} تایید شد (فیلد ایجاد شد)، {len(remaining_issues)} در انتظار بررسی (severity پایین)"
            project.last_validation_results = json.dumps(validation_results, ensure_ascii=False)

            # اضافه کردن به report_data برای پردازش بعدی
            report_data["health_analysis_validation"] = validation_results

            # 🔴 CRITICAL: Commit validation results immediately
            db.commit()
            logger.info(f"✅ Fallback: {validated_issues_count} validated (fields), {len(remaining_issues)} pending - COMMITTED to DB")

        # ====================================
        # 🆕 به‌روزرسانی حالت ایده‌آل جامع
        # ====================================
        if "comprehensive_ideal_state" in report_data:
            ideal_state_data = report_data["comprehensive_ideal_state"]
            comprehensive_ideal = f"""## حالت ایده‌آل پروژه

{ideal_state_data.get('description', '')}

### کمبودهای فعلی:
{chr(10).join(['- ' + d for d in ideal_state_data.get('current_deficiencies', [])])}

### تسک‌های اجرا نشده:
{chr(10).join(['- ' + t for t in ideal_state_data.get('unexecuted_tasks', [])])}

### ساختار سیستم:
{ideal_state_data.get('system_structure', {}).get('overview', '')}

**کامپوننت‌ها:** {', '.join(ideal_state_data.get('system_structure', {}).get('components', []))}

**سیم‌کشی:** {ideal_state_data.get('system_structure', {}).get('wiring', '')}

### نقشه راه یکپارچه:
{ideal_state_data.get('roadmap_integration', '')}
"""
            project.ideal_state = comprehensive_ideal
            logger.info(f"Updated comprehensive ideal state for project {project_id}")

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

            # 2. 🆕 تولید فیلدهای جدید از validated issues (با مارکر اعتبارسنجی)
            if validate_health_issues and "health_analysis_validation" in report_data:
                validated_issues = report_data["health_analysis_validation"].get("validated_issues", [])
                logger.info(f"Creating fields from {len(validated_issues)} validated health issues")
                for issue in validated_issues:
                    if not issue.get("create_field", True):
                        continue

                    original = issue.get("original_issue", {})
                    field_name = f"✅ [تایید شده] {original.get('type', 'issue')}: {original.get('file', 'unknown')}"

                    # بررسی وجود فیلد مشابه
                    existing = any(
                        f.get("name", "").lower() == field_name.lower()
                        for f in existing_fields if not f.get("archived")
                    )

                    if not existing:
                        priority_map = {"critical": 1, "high": 2, "medium": 5, "low": 7}
                        priority = priority_map.get(issue.get("priority", original.get("severity", "medium")), 5)

                        new_field = {
                            "id": str(uuid.uuid4()),
                            "name": field_name,
                            "value": f"""## ایراد تایید شده توسط {model_id}

**فایل:** {original.get('file', 'نامشخص')}
**نوع:** {original.get('type', 'نامشخص')}
**شدت:** {original.get('severity', 'نامشخص')}
**خط:** {original.get('line', 'نامشخص')}

### پیام:
{original.get('message', '')}

### یادداشت اعتبارسنجی:
{issue.get('validation_note', '')}

### امتیاز اعتبارسنجی: {issue.get('validation_score', 0)}/100

---
لطفاً این مشکل را بررسی و رفع کنید.
""",
                            "target_models": ["claude"],
                            "action_type": "display",
                            "target_path": original.get("file"),
                            "archive_after_run": True,
                            "field_type": "temporary",
                            "priority": priority,
                            "attachments": [],
                            "trigger": {"enabled": False, "interval_minutes": 60, "interval_type": "minutes"},
                            "created_from_report": True,
                            "validation_marker": "validated",
                            "validation_score": issue.get("validation_score", 0),
                            "validator_model": model_id,
                            "original_issue": original,
                        }
                        existing_fields.append(new_field)
                        created_fields.append(new_field["name"])

            # 3. تولید فیلدهای جدید از roadmap
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
                logger.info(f"Field management: created={len(created_fields)}, archived={archived_count}, merged={merged_count}, updated={updated_count}")

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

        # 🆕 ثبت فعالیت در ژورنال
        activity_log = ActivityLog(
            id=f"log_{uuid.uuid4().hex[:12]}",
            project_id=project_id,
            model_id=model_id,
            model_provider="anthropic" if "claude" in model_id.lower() else "openai",
            activity_type="engineering_report",
            prompt=f"تولید گزارش مهندسی برای {days} روز اخیر",
            response=report_data.get("executive_summary", "")[:500] if isinstance(report_data, dict) else None,
            tokens_used=response.tokens_used or 0,
            latency_ms=int((datetime.utcnow() - since).total_seconds() * 1000) if since else 0,
            success=True,
            field_id=None,
            field_name=f"گزارش مهندسی - {report.id}",
            extra_data=json.dumps({
                "report_id": report.id,
                "files_analyzed": len(files),
                "health_issues_reviewed": len(health_analysis_issues),
                "validated_count": validated_issues_count,
                "rejected_count": rejected_issues_count,
                "fields_created": len(created_fields),
                "project_health_score": report_data.get("project_health", {}).get("score") if isinstance(report_data, dict) else None,
            }, ensure_ascii=False),
            created_at=datetime.utcnow(),
        )
        db.add(activity_log)
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
            "recommendations_count": len(report_data.get("recommendations", [])),
            # 🆕 نتایج اعتبارسنجی
            "validation_results": {
                "issues_reviewed": validated_issues_count + rejected_issues_count,
                "validated_count": validated_issues_count,
                "rejected_count": rejected_issues_count,
                "fields_created_from_validation": len([f for f in created_fields if "✅" in f]),
            } if validate_health_issues else None,
            "ideal_state_updated": "comprehensive_ideal_state" in report_data,
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
