"""
API Routes for Project Analysis
مسیرهای API برای تحلیل پروژه و پروفایل مدل‌ها
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import List, Optional
from pydantic import BaseModel
import logging

from ...services.project_analyzer import get_project_analyzer
from ...services.model_profiler import get_model_profiler
from ...models.analysis_report import (
    AnalysisReportSchema, AnalysisRequestSchema, AnalysisScheduleSchema
)
from ...models.ai_profile import AIProfileSchema, AIProfileSummarySchema

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/analysis", tags=["Analysis"])


# =====================
# Analysis Endpoints
# =====================

class AnalysisRequest(BaseModel):
    """درخواست تحلیل"""
    project_id: str
    project_path: str
    models: List[str] = []  # خالی = همه مدل‌های فعال
    roadmap_path: Optional[str] = None


class AnalysisResponse(BaseModel):
    """پاسخ تحلیل"""
    success: bool
    report_id: Optional[str] = None
    message: str
    report: Optional[AnalysisReportSchema] = None


@router.post("/run", response_model=AnalysisResponse)
async def run_analysis(
    request: AnalysisRequest,
    background_tasks: BackgroundTasks
):
    """
    اجرای تحلیل جدید

    تحلیل کامل پروژه توسط مدل‌های انتخابی
    """
    try:
        analyzer = get_project_analyzer()
        analyzer.initialize()

        # اجرای تحلیل
        report = await analyzer.analyze_project(
            project_id=request.project_id,
            project_path=request.project_path,
            models=request.models if request.models else None,
            roadmap_path=request.roadmap_path
        )

        return AnalysisResponse(
            success=True,
            report_id=report.id,
            message="تحلیل با موفقیت انجام شد",
            report=report
        )

    except Exception as e:
        logger.error(f"Analysis failed: {e}", exc_info=True)
        return AnalysisResponse(
            success=False,
            message=f"خطا در تحلیل: {str(e)}"
        )


@router.get("/reports", response_model=List[AnalysisReportSchema])
async def get_analysis_reports(
    project_id: Optional[str] = None,
    limit: int = 20
):
    """دریافت لیست گزارش‌های تحلیل"""
    from ...core.database import SessionLocal
    from ...models.analysis_report import AnalysisReport

    db = SessionLocal()
    try:
        query = db.query(AnalysisReport)

        if project_id:
            query = query.filter(AnalysisReport.project_id == project_id)

        reports = query.order_by(AnalysisReport.created_at.desc()).limit(limit).all()
        return [AnalysisReportSchema.model_validate(r) for r in reports]
    finally:
        db.close()


@router.get("/reports/{report_id}", response_model=AnalysisReportSchema)
async def get_analysis_report(report_id: str):
    """دریافت جزئیات یک گزارش"""
    from ...core.database import SessionLocal
    from ...models.analysis_report import AnalysisReport

    db = SessionLocal()
    try:
        report = db.query(AnalysisReport).filter(AnalysisReport.id == report_id).first()
        if not report:
            raise HTTPException(status_code=404, detail="گزارش یافت نشد")
        return AnalysisReportSchema.model_validate(report)
    finally:
        db.close()


@router.delete("/reports/{report_id}")
async def delete_analysis_report(report_id: str):
    """حذف یک گزارش"""
    from ...core.database import SessionLocal
    from ...models.analysis_report import AnalysisReport

    db = SessionLocal()
    try:
        report = db.query(AnalysisReport).filter(AnalysisReport.id == report_id).first()
        if not report:
            raise HTTPException(status_code=404, detail="گزارش یافت نشد")

        db.delete(report)
        db.commit()
        return {"success": True, "message": "گزارش حذف شد"}
    finally:
        db.close()


# =====================
# AI Profile Endpoints
# =====================

@router.get("/profiles", response_model=List[AIProfileSchema])
async def get_all_profiles():
    """دریافت همه پروفایل‌های AI"""
    profiler = get_model_profiler()
    return profiler.get_all_profiles()


@router.get("/profiles/top", response_model=List[AIProfileSchema])
async def get_top_models(n: int = 5, task_type: Optional[str] = None):
    """دریافت مدل‌های برتر"""
    profiler = get_model_profiler()
    return profiler.get_top_models(n=n, task_type=task_type)


@router.get("/profiles/{model_id}", response_model=AIProfileSchema)
async def get_model_profile(model_id: str):
    """دریافت پروفایل یک مدل"""
    profiler = get_model_profiler()
    profile = profiler.get_profile(model_id)

    if not profile:
        raise HTTPException(status_code=404, detail="پروفایل یافت نشد")

    return profile


@router.get("/profiles/{model_id}/history")
async def get_model_history(model_id: str, limit: int = 100):
    """دریافت تاریخچه نمرات یک مدل"""
    profiler = get_model_profiler()
    history = profiler.get_score_history(model_id, limit=limit)
    return {"model_id": model_id, "history": history}


class CompareModelsRequest(BaseModel):
    """درخواست مقایسه مدل‌ها"""
    model_ids: List[str]


@router.post("/profiles/compare")
async def compare_models(request: CompareModelsRequest):
    """مقایسه چند مدل با هم"""
    profiler = get_model_profiler()
    comparison = profiler.compare_models(request.model_ids)
    return comparison


@router.post("/profiles/refresh-rankings")
async def refresh_rankings():
    """به‌روزرسانی رتبه‌بندی همه مدل‌ها"""
    profiler = get_model_profiler()
    profiler.update_rankings()
    return {"success": True, "message": "رتبه‌بندی به‌روز شد"}


@router.post("/profiles/initialize")
async def initialize_profiles():
    """ایجاد پروفایل اولیه برای همه مدل‌های شناخته‌شده"""
    profiler = get_model_profiler()
    profiler.initialize_profiles_for_known_models()
    return {"success": True, "message": "پروفایل‌ها ایجاد شدند"}


# =====================
# Schedule Endpoints
# =====================

@router.get("/schedule/{project_id}", response_model=AnalysisScheduleSchema)
async def get_schedule(project_id: str):
    """دریافت زمان‌بندی تحلیل یک پروژه"""
    from ...core.database import SessionLocal
    from ...models.analysis_report import AnalysisSchedule

    db = SessionLocal()
    try:
        schedule = db.query(AnalysisSchedule).filter(
            AnalysisSchedule.project_id == project_id
        ).first()

        if not schedule:
            raise HTTPException(status_code=404, detail="زمان‌بندی یافت نشد")

        return AnalysisScheduleSchema.model_validate(schedule)
    finally:
        db.close()


class ScheduleRequest(BaseModel):
    """درخواست تنظیم زمان‌بندی"""
    project_id: str
    enabled: bool = True
    interval: str = "daily"  # hourly, daily, weekly, manual
    time: str = "02:00"
    day_of_week: int = 0
    models: List[str] = []


@router.put("/schedule", response_model=AnalysisScheduleSchema)
async def update_schedule(request: ScheduleRequest):
    """تنظیم یا به‌روزرسانی زمان‌بندی"""
    from ...core.database import SessionLocal
    from ...models.analysis_report import AnalysisSchedule

    db = SessionLocal()
    try:
        schedule = db.query(AnalysisSchedule).filter(
            AnalysisSchedule.project_id == request.project_id
        ).first()

        if not schedule:
            schedule = AnalysisSchedule(project_id=request.project_id)
            db.add(schedule)

        schedule.enabled = 1 if request.enabled else 0
        schedule.interval = request.interval
        schedule.time = request.time
        schedule.day_of_week = request.day_of_week
        schedule.models = request.models

        db.commit()
        db.refresh(schedule)

        return AnalysisScheduleSchema.model_validate(schedule)
    finally:
        db.close()


@router.delete("/schedule/{project_id}")
async def delete_schedule(project_id: str):
    """حذف زمان‌بندی"""
    from ...core.database import SessionLocal
    from ...models.analysis_report import AnalysisSchedule

    db = SessionLocal()
    try:
        schedule = db.query(AnalysisSchedule).filter(
            AnalysisSchedule.project_id == project_id
        ).first()

        if schedule:
            db.delete(schedule)
            db.commit()

        return {"success": True, "message": "زمان‌بندی حذف شد"}
    finally:
        db.close()


# =====================
# Health & Stats
# =====================

@router.get("/stats")
async def get_analysis_stats():
    """آمار کلی تحلیل‌ها"""
    from ...core.database import SessionLocal
    from ...models.analysis_report import AnalysisReport
    from ...models.ai_profile import AIProfile

    db = SessionLocal()
    try:
        total_reports = db.query(AnalysisReport).count()
        completed_reports = db.query(AnalysisReport).filter(
            AnalysisReport.status == "completed"
        ).count()
        total_profiles = db.query(AIProfile).count()

        # میانگین نمره کلی
        from sqlalchemy import func
        avg_score = db.query(func.avg(AnalysisReport.overall_score)).filter(
            AnalysisReport.status == "completed"
        ).scalar() or 0

        return {
            "total_reports": total_reports,
            "completed_reports": completed_reports,
            "total_profiles": total_profiles,
            "average_score": round(avg_score, 1)
        }
    finally:
        db.close()
