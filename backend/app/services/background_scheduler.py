# -*- coding: utf-8 -*-
"""
🕐 Background Scheduler Service
سرویس زمان‌بندی کارهای پس‌زمینه

قابلیت‌ها:
1. انتقال خودکار خطاها به ایرادات
2. قابل گسترش برای کارهای دیگر
"""

import logging
import asyncio
from datetime import datetime
from typing import Optional, Dict, Any

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from ..core.database import SessionLocal
from ..core.logging_utils import StructuredLogger
from ..models.render_log import RenderLogSettings

logger = logging.getLogger(__name__)
slog = StructuredLogger(__name__, "SCHEDULER")


class BackgroundScheduler:
    """
    مدیریت کارهای پس‌زمینه

    Features:
    - Auto-transfer errors to issues (configurable interval)
    - Dynamic job management (add/remove/update)
    - Graceful shutdown
    """

    def __init__(self):
        self.scheduler: Optional[AsyncIOScheduler] = None
        self.is_running = False
        self._auto_transfer_job_id = "auto_transfer_errors"

    def start(self):
        """شروع scheduler"""
        if self.is_running:
            slog.warning("Scheduler already running")
            return

        self.scheduler = AsyncIOScheduler(timezone="UTC")
        self.scheduler.start()
        self.is_running = True

        slog.success("Background scheduler started")

        # بارگذاری تنظیمات و شروع job های فعال
        asyncio.create_task(self._initialize_jobs())

    async def _initialize_jobs(self):
        """بارگذاری و راه‌اندازی job های فعال"""
        try:
            await self._sync_auto_transfer_settings()
        except Exception as e:
            slog.error("Failed to initialize jobs", exception=e)

    def stop(self):
        """توقف scheduler"""
        if self.scheduler and self.is_running:
            self.scheduler.shutdown(wait=False)
            self.is_running = False
            slog.info("Background scheduler stopped")

    async def _sync_auto_transfer_settings(self):
        """
        همگام‌سازی تنظیمات auto-transfer از دیتابیس
        این متد هر بار که تنظیمات تغییر می‌کند فراخوانی می‌شود
        """
        db = SessionLocal()
        try:
            settings = db.query(RenderLogSettings).first()

            if not settings:
                slog.info("No render log settings found, creating default")
                settings = RenderLogSettings()
                db.add(settings)
                db.commit()
                db.refresh(settings)

            if settings.auto_transfer_enabled:
                await self._enable_auto_transfer(
                    interval_minutes=settings.auto_transfer_interval_minutes or 30,
                    hours_back=settings.auto_transfer_hours_back or 24
                )
            else:
                await self._disable_auto_transfer()

        except Exception as e:
            slog.error("Failed to sync auto-transfer settings", exception=e)
        finally:
            db.close()

    async def _enable_auto_transfer(self, interval_minutes: int, hours_back: int):
        """فعال‌سازی job انتقال خودکار"""
        if not self.scheduler:
            slog.error("Scheduler not started")
            return

        # حذف job قبلی اگر وجود دارد
        existing = self.scheduler.get_job(self._auto_transfer_job_id)
        if existing:
            self.scheduler.remove_job(self._auto_transfer_job_id)
            slog.info("Removed existing auto-transfer job")

        # اضافه کردن job جدید
        self.scheduler.add_job(
            self._run_auto_transfer,
            trigger=IntervalTrigger(minutes=interval_minutes),
            id=self._auto_transfer_job_id,
            name="Auto Transfer Errors to Issues",
            kwargs={"hours_back": hours_back},
            replace_existing=True,
            max_instances=1  # فقط یک instance همزمان
        )

        slog.success("Auto-transfer job enabled",
            interval_minutes=interval_minutes,
            hours_back=hours_back
        )

    async def _disable_auto_transfer(self):
        """غیرفعال‌سازی job انتقال خودکار"""
        if not self.scheduler:
            return

        existing = self.scheduler.get_job(self._auto_transfer_job_id)
        if existing:
            self.scheduler.remove_job(self._auto_transfer_job_id)
            slog.info("Auto-transfer job disabled")

    async def _run_auto_transfer(self, hours_back: int = 24):
        """
        اجرای انتقال خودکار
        این متد توسط scheduler فراخوانی می‌شود
        """
        slog.info("Running auto-transfer job", hours_back=hours_back)

        db = SessionLocal()
        try:
            # Import here to avoid circular imports
            from .log_to_issues_service import get_log_to_issues_service

            service = get_log_to_issues_service()
            result = await service.transfer_error_logs(
                service_ids=None,  # همه سرویس‌ها
                hours=hours_back,
                auto_mode=True,
                db=db
            )

            # به‌روزرسانی last_auto_transfer
            settings = db.query(RenderLogSettings).first()
            if settings:
                settings.last_auto_transfer = datetime.utcnow()
                db.commit()

            slog.success("Auto-transfer completed",
                transferred=result.get("transferred", 0),
                merged=result.get("merged", 0),
                skipped=result.get("skipped", 0)
            )

            return result

        except Exception as e:
            slog.error("Auto-transfer failed", exception=e)
            db.rollback()
            return {"success": False, "error": str(e)}

        finally:
            db.close()

    async def update_auto_transfer_settings(
        self,
        enabled: bool,
        interval_minutes: int = 30,
        hours_back: int = 24
    ):
        """
        به‌روزرسانی تنظیمات auto-transfer
        این متد از API فراخوانی می‌شود
        """
        if enabled:
            await self._enable_auto_transfer(interval_minutes, hours_back)
        else:
            await self._disable_auto_transfer()

    def get_jobs_info(self) -> Dict[str, Any]:
        """دریافت اطلاعات job های فعال"""
        if not self.scheduler:
            return {"running": False, "jobs": []}

        jobs = []
        for job in self.scheduler.get_jobs():
            next_run = job.next_run_time
            jobs.append({
                "id": job.id,
                "name": job.name,
                "next_run": next_run.isoformat() if next_run else None,
                "trigger": str(job.trigger)
            })

        return {
            "running": self.is_running,
            "jobs": jobs
        }

    def trigger_job_now(self, job_id: str) -> bool:
        """اجرای فوری یک job"""
        if not self.scheduler:
            return False

        job = self.scheduler.get_job(job_id)
        if job:
            # Run immediately
            self.scheduler.modify_job(job_id, next_run_time=datetime.utcnow())
            slog.info("Job triggered manually", job_id=job_id)
            return True
        return False


# =====================================================
# Singleton Instance
# =====================================================

_scheduler_instance: Optional[BackgroundScheduler] = None


def get_background_scheduler() -> BackgroundScheduler:
    """دریافت نمونه BackgroundScheduler"""
    global _scheduler_instance
    if _scheduler_instance is None:
        _scheduler_instance = BackgroundScheduler()
    return _scheduler_instance
