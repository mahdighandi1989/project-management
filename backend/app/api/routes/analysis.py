"""
API Routes for Project Analysis
مسیرهای API برای تحلیل پروژه و پروفایل مدل‌ها
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from typing import List, Optional
from pydantic import BaseModel
import logging
import json
import asyncio

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


@router.post("/run-stream")
async def run_analysis_stream(request: AnalysisRequest):
    """
    اجرای تحلیل با استریم پیشرفت (Server-Sent Events)

    این endpoint پیشرفت تحلیل را به صورت Real-time ارسال می‌کند:
    - کدام مدل در حال کار است
    - کدام فایل در حال تحلیل است
    - درصد پیشرفت
    - زمان سپری شده
    """
    import os
    from ...services.ai_manager import get_ai_manager
    from ...services.deep_analysis_service import DeepAnalysisService

    # صف برای ارسال رویدادها
    progress_queue: asyncio.Queue = asyncio.Queue()

    async def progress_callback(progress_data: dict):
        """callback برای دریافت رویدادهای پیشرفت"""
        await progress_queue.put(progress_data)

    async def generate_events():
        """ژنراتور رویدادهای SSE"""
        final_result = None

        async def run_analysis_task():
            nonlocal final_result
            try:
                # دریافت AI Manager
                ai_manager = get_ai_manager()

                # ساخت DeepAnalysisService با progress callback
                deep_analyzer = DeepAnalysisService(
                    ai_manager=ai_manager,
                    progress_callback=progress_callback
                )

                # جمع‌آوری فایل‌های پروژه
                project_path = request.project_path
                files = []

                # خواندن README اگر موجود باشد
                readme_content = ""
                readme_paths = ["README.md", "readme.md", "README.txt"]
                for readme_name in readme_paths:
                    readme_path = os.path.join(project_path, readme_name)
                    if os.path.exists(readme_path):
                        try:
                            with open(readme_path, 'r', encoding='utf-8') as f:
                                readme_content = f.read()
                            break
                        except:
                            pass

                # خواندن Roadmap اگر موجود باشد
                roadmap_content = ""
                if request.roadmap_path and os.path.exists(request.roadmap_path):
                    try:
                        with open(request.roadmap_path, 'r', encoding='utf-8') as f:
                            roadmap_content = f.read()
                    except:
                        pass

                # جمع‌آوری فایل‌ها
                supported_extensions = {
                    '.py', '.js', '.ts', '.tsx', '.jsx', '.java',
                    '.go', '.rs', '.cpp', '.c', '.h', '.hpp',
                    '.rb', '.php', '.swift', '.kt', '.scala',
                    '.vue', '.svelte', '.html', '.css', '.scss'
                }

                for root, dirs, filenames in os.walk(project_path):
                    # فیلتر دایرکتوری‌های غیرضروری
                    dirs[:] = [d for d in dirs if d not in {
                        'node_modules', '.git', '__pycache__', 'venv',
                        '.venv', 'env', 'dist', 'build', '.next'
                    }]

                    for filename in filenames:
                        ext = os.path.splitext(filename)[1].lower()
                        if ext in supported_extensions:
                            full_path = os.path.join(root, filename)
                            rel_path = os.path.relpath(full_path, project_path)
                            try:
                                with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                                    content = f.read()
                                files.append({
                                    "path": rel_path,
                                    "content": content
                                })
                            except:
                                pass

                logger.info(f"Collected {len(files)} files for analysis")

                # انتخاب مدل‌ها
                model_ids = request.models if request.models else None
                if not model_ids:
                    available = ai_manager.get_available_models()
                    model_ids = [m.id for m in available]

                # اجرای تحلیل
                final_result = await deep_analyzer.run_full_analysis(
                    project_id=request.project_id,
                    files=files,
                    roadmap_content=roadmap_content,
                    readme_content=readme_content,
                    model_ids=model_ids,
                    instruction=""
                )

            except Exception as e:
                logger.error(f"Streaming analysis failed: {e}", exc_info=True)
                await progress_queue.put({
                    "event": "error",
                    "message": str(e),
                    "error": True
                })
            finally:
                # سیگنال اتمام
                await progress_queue.put({
                    "event": "done",
                    "result": final_result if final_result else None
                })

        # شروع تحلیل
        analysis_task = asyncio.create_task(run_analysis_task())

        try:
            while True:
                try:
                    # دریافت رویداد با timeout
                    progress_data = await asyncio.wait_for(
                        progress_queue.get(),
                        timeout=2.0
                    )

                    # ارسال رویداد SSE
                    event_type = progress_data.get("event", "progress")

                    # محدود کردن داده‌ها برای ارسال
                    safe_data = {k: v for k, v in progress_data.items()
                                 if k not in ['result'] or v is None}
                    if 'result' in progress_data and progress_data['result']:
                        safe_data['has_result'] = True
                        safe_data['overall_score'] = progress_data['result'].get('overall_scores', {}).get('total', 0)

                    data = json.dumps(safe_data, ensure_ascii=False, default=str)
                    yield f"event: {event_type}\ndata: {data}\n\n"

                    # اگر تحلیل تمام شد
                    if event_type == "done" or event_type == "analysis_completed":
                        break

                except asyncio.TimeoutError:
                    # ارسال heartbeat
                    yield f"event: heartbeat\ndata: {{}}\n\n"

                    # بررسی وضعیت task
                    if analysis_task.done():
                        break

        except Exception as e:
            logger.error(f"Error in SSE stream: {e}")
            yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"

        finally:
            if not analysis_task.done():
                analysis_task.cancel()

    return StreamingResponse(
        generate_events(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # برای nginx
            "Access-Control-Allow-Origin": "*"
        }
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
