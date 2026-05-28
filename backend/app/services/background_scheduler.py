# -*- coding: utf-8 -*-
"""
🕐 Background Scheduler Service
سرویس زمان‌بندی کارهای پس‌زمینه

قابلیت‌ها:
1. انتقال خودکار خطاها به ایرادات (Render Logs)
2. تحلیل سلامت خودکار (Health Analysis)
3. اجرای خودکار فیلدهای پویا با تریگر (Dynamic Fields)
4. انتقال خودکار یافته‌های امنیتی (Security Findings)
5. انتقال خودکار پوشش تست (Test Coverage)
6. گزارش مهندسی خودکار (Engineering Report)
"""

import logging
import asyncio
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger

from ..core.database import SessionLocal
from ..core.logging_utils import StructuredLogger
from ..models.render_log import RenderLogSettings
from ..models.project import Project

logger = logging.getLogger(__name__)
slog = StructuredLogger(__name__, "SCHEDULER")


class BackgroundScheduler:
    """
    مدیریت کارهای پس‌زمینه

    Features:
    - Auto-transfer errors to issues (configurable interval)
    - Auto health analysis for projects
    - Auto execute triggered dynamic fields
    - Auto transfer security/test findings
    - Auto engineering reports
    - Dynamic job management (add/remove/update)
    - Graceful shutdown
    """

    # Job IDs
    JOB_AUTO_TRANSFER = "auto_transfer_errors"
    JOB_HEALTH_ANALYSIS = "auto_health_analysis"
    JOB_DYNAMIC_FIELDS = "auto_dynamic_fields"
    JOB_SECURITY_TRANSFER = "auto_security_transfer"
    JOB_TEST_COVERAGE_TRANSFER = "auto_test_coverage_transfer"
    JOB_ENGINEERING_REPORT = "auto_engineering_report"
    # 🆕 (Auto Discover) — کشف خودکار repo های جدید GitHub
    # و اضافه‌کردن به watched list. به‌صورت پیش‌فرض هر ۶۰ دقیقه.
    # کنترل: env var REPO_AUTO_DISCOVER_ENABLED (default: 1)
    # کنترل بازه: env var REPO_AUTO_DISCOVER_INTERVAL_MINUTES (default: 60)
    JOB_REPO_AUTO_DISCOVER = "auto_repo_discover"

    def __init__(self):
        self.scheduler: Optional[AsyncIOScheduler] = None
        self.is_running = False

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
            # 1. Auto-transfer Render logs
            await self._sync_auto_transfer_settings()

            # 2. Health Analysis trigger
            await self._sync_health_analysis_settings()

            # 3. Dynamic Fields trigger
            await self._sync_dynamic_fields_trigger()

            # 4. Security findings transfer
            await self._sync_security_transfer_settings()

            # 5. Test coverage transfer
            await self._sync_test_coverage_transfer_settings()

            # 6. Engineering report
            await self._sync_engineering_report_settings()

            # 7. 🆕 (Auto Discover) — کشف repo های جدید GitHub
            await self._sync_repo_auto_discover_settings()

            slog.success("All scheduler jobs initialized")

        except Exception as e:
            slog.error("Failed to initialize jobs", exception=e)

    def stop(self):
        """توقف scheduler"""
        if self.scheduler and self.is_running:
            self.scheduler.shutdown(wait=False)
            self.is_running = False
            slog.info("Background scheduler stopped")

    # =====================================================
    # 1. Auto-Transfer Render Logs
    # =====================================================

    async def _sync_auto_transfer_settings(self):
        """همگام‌سازی تنظیمات auto-transfer از دیتابیس"""
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
                    hours_back=settings.auto_transfer_hours_back or 24,
                    mode=getattr(settings, 'auto_transfer_mode', 'since_deploy') or 'since_deploy'
                )
            else:
                await self._disable_job(self.JOB_AUTO_TRANSFER)

        except Exception as e:
            slog.error("Failed to sync auto-transfer settings", exception=e)
        finally:
            db.close()

    async def _enable_auto_transfer(
        self,
        interval_minutes: int,
        hours_back: int,
        mode: str = "since_deploy"
    ):
        """فعال‌سازی job انتقال خودکار"""
        if not self.scheduler:
            return

        self._remove_job_if_exists(self.JOB_AUTO_TRANSFER)

        self.scheduler.add_job(
            self._run_auto_transfer,
            trigger=IntervalTrigger(minutes=interval_minutes),
            id=self.JOB_AUTO_TRANSFER,
            name="Auto Transfer Errors to Issues",
            kwargs={"hours_back": hours_back, "mode": mode},
            replace_existing=True,
            max_instances=1
        )

        slog.success("Auto-transfer job enabled",
            interval_minutes=interval_minutes,
            hours_back=hours_back,
            mode=mode
        )

    async def _run_auto_transfer(self, hours_back: int = 24, mode: str = "since_deploy"):
        """اجرای انتقال خودکار"""
        slog.info("Running auto-transfer job", hours_back=hours_back, mode=mode)

        db = SessionLocal()
        try:
            from .log_to_issues_service import get_log_to_issues_service

            service = get_log_to_issues_service()
            result = await service.transfer_error_logs(
                service_ids=None,
                hours=hours_back,
                auto_mode=True,
                mode=mode,
                db=db
            )

            settings = db.query(RenderLogSettings).first()
            if settings:
                settings.last_auto_transfer = datetime.utcnow()
                db.commit()

            slog.success("Auto-transfer completed",
                transferred=result.get("transferred", 0),
                merged=result.get("merged", 0)
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
        hours_back: int = 24,
        mode: str = "since_deploy"
    ):
        """به‌روزرسانی تنظیمات auto-transfer"""
        if enabled:
            await self._enable_auto_transfer(interval_minutes, hours_back, mode)
        else:
            await self._disable_job(self.JOB_AUTO_TRANSFER)

    # =====================================================
    # 2. Auto Health Analysis
    # =====================================================

    async def _sync_health_analysis_settings(self):
        """همگام‌سازی تنظیمات تحلیل سلامت خودکار"""
        db = SessionLocal()
        try:
            # بررسی پروژه‌هایی که trigger فعال دارند
            projects = db.query(Project).filter(Project.analysis_settings.isnot(None)).all()

            projects_with_trigger = []
            min_interval = 60  # حداقل interval

            for project in projects:
                try:
                    settings = json.loads(project.analysis_settings) if project.analysis_settings else {}
                    if settings.get("trigger_enabled", False):
                        interval = settings.get("trigger_interval_minutes", 60)
                        projects_with_trigger.append({
                            "id": project.id,
                            "interval": interval
                        })
                        if interval < min_interval:
                            min_interval = interval
                except:
                    continue

            if projects_with_trigger:
                # یک job برای بررسی همه پروژه‌ها
                await self._enable_health_analysis(min_interval)
                slog.info(f"Health analysis enabled for {len(projects_with_trigger)} projects")
            else:
                await self._disable_job(self.JOB_HEALTH_ANALYSIS)

        except Exception as e:
            slog.error("Failed to sync health analysis settings", exception=e)
        finally:
            db.close()

    async def _enable_health_analysis(self, interval_minutes: int = 60):
        """فعال‌سازی job تحلیل سلامت"""
        if not self.scheduler:
            return

        self._remove_job_if_exists(self.JOB_HEALTH_ANALYSIS)

        self.scheduler.add_job(
            self._run_health_analysis,
            trigger=IntervalTrigger(minutes=interval_minutes),
            id=self.JOB_HEALTH_ANALYSIS,
            name="Auto Health Analysis",
            replace_existing=True,
            max_instances=1
        )

        slog.success("Health analysis job enabled", interval_minutes=interval_minutes)

    async def _run_health_analysis(self):
        """اجرای تحلیل سلامت برای پروژه‌های با trigger فعال"""
        slog.info("Running auto health analysis")

        db = SessionLocal()
        try:
            projects = db.query(Project).filter(Project.analysis_settings.isnot(None)).all()

            analyzed = 0
            for project in projects:
                try:
                    settings = json.loads(project.analysis_settings) if project.analysis_settings else {}
                    if not settings.get("trigger_enabled", False):
                        continue

                    interval = settings.get("trigger_interval_minutes", 60)
                    last_analysis = project.last_analysis_at

                    # بررسی آیا زمان تحلیل رسیده
                    if last_analysis:
                        next_run = last_analysis + timedelta(minutes=interval)
                        if datetime.utcnow() < next_run:
                            continue

                    # اجرای تحلیل از طریق API endpoint
                    from ..api.routes.project_health import run_health_analysis, RunAnalysisRequest
                    from starlette.background import BackgroundTasks

                    slog.info(f"Running health analysis for project: {project.id}")

                    # ساخت درخواست تحلیل
                    request = RunAnalysisRequest(
                        model_ids=None,  # همه مدل‌های فعال
                        full_analysis=True,
                        update_roadmap=True,
                        update_readme=True,
                        depth="standard"
                    )

                    # BackgroundTasks خالی (چون خودمون در background هستیم)
                    background_tasks = BackgroundTasks()

                    result = await run_health_analysis(
                        project_id=project.id,
                        request=request,
                        background_tasks=background_tasks,
                        db=db
                    )

                    if result.get("success") or result.get("analysis_id"):
                        analyzed += 1
                        slog.info(f"Health analysis started for {project.id}: {result.get('analysis_id')}")

                except Exception as e:
                    slog.error(f"Health analysis failed for {project.id}", exception=e)
                    continue

            slog.success("Auto health analysis completed", analyzed=analyzed)
            return {"analyzed": analyzed}

        except Exception as e:
            slog.error("Auto health analysis failed", exception=e)
            return {"success": False, "error": str(e)}
        finally:
            db.close()

    async def update_health_analysis_settings(self, project_id: str, enabled: bool, interval_minutes: int = 60):
        """به‌روزرسانی تنظیمات تحلیل سلامت برای یک پروژه"""
        db = SessionLocal()
        try:
            project = db.query(Project).filter(Project.id == project_id).first()
            if project:
                settings = json.loads(project.analysis_settings) if project.analysis_settings else {}
                settings["trigger_enabled"] = enabled
                settings["trigger_interval_minutes"] = interval_minutes
                project.analysis_settings = json.dumps(settings)
                db.commit()

            # بررسی مجدد همه پروژه‌ها
            await self._sync_health_analysis_settings()

        finally:
            db.close()

    # =====================================================
    # 3. Auto Dynamic Fields Trigger
    # =====================================================

    async def _sync_dynamic_fields_trigger(self):
        """همگام‌سازی تریگر فیلدهای پویا"""
        db = SessionLocal()
        try:
            projects = db.query(Project).filter(Project.dynamic_fields.isnot(None)).all()

            has_triggered_fields = False
            min_interval = 60

            for project in projects:
                try:
                    fields = json.loads(project.dynamic_fields) if project.dynamic_fields else []
                    for field in fields:
                        trigger = field.get("trigger", {})
                        if trigger.get("enabled", False) and not field.get("archived"):
                            has_triggered_fields = True
                            interval = trigger.get("interval_minutes", 60)
                            if interval < min_interval:
                                min_interval = interval
                except:
                    continue

            if has_triggered_fields:
                await self._enable_dynamic_fields_trigger(min_interval)
            else:
                await self._disable_job(self.JOB_DYNAMIC_FIELDS)

        except Exception as e:
            slog.error("Failed to sync dynamic fields trigger", exception=e)
        finally:
            db.close()

    async def _enable_dynamic_fields_trigger(self, interval_minutes: int = 30):
        """فعال‌سازی job فیلدهای پویا"""
        if not self.scheduler:
            return

        self._remove_job_if_exists(self.JOB_DYNAMIC_FIELDS)

        self.scheduler.add_job(
            self._run_dynamic_fields_trigger,
            trigger=IntervalTrigger(minutes=interval_minutes),
            id=self.JOB_DYNAMIC_FIELDS,
            name="Auto Execute Dynamic Fields",
            replace_existing=True,
            max_instances=1
        )

        slog.success("Dynamic fields trigger enabled", interval_minutes=interval_minutes)

    async def _run_dynamic_fields_trigger(self):
        """اجرای فیلدهای پویا با trigger فعال"""
        slog.info("Running dynamic fields trigger check")

        db = SessionLocal()
        executed = 0
        try:
            projects = db.query(Project).filter(Project.dynamic_fields.isnot(None)).all()

            for project in projects:
                try:
                    fields = json.loads(project.dynamic_fields) if project.dynamic_fields else []
                    updated = False

                    for field in fields:
                        if field.get("archived"):
                            continue

                        trigger = field.get("trigger", {})
                        if not trigger.get("enabled", False):
                            continue

                        interval = trigger.get("interval_minutes", 60)
                        last_run_str = trigger.get("last_run")

                        # بررسی آیا زمان اجرا رسیده
                        should_run = True
                        if last_run_str:
                            try:
                                last_run = datetime.fromisoformat(last_run_str.replace("Z", "+00:00"))
                                next_run = last_run + timedelta(minutes=interval)
                                if datetime.utcnow() < next_run.replace(tzinfo=None):
                                    should_run = False
                            except:
                                pass

                        if should_run:
                            # اجرای فیلد
                            slog.info(f"Executing triggered field: {field.get('name')} in project {project.id}")

                            try:
                                from .smart_orchestrator import get_smart_orchestrator
                                orchestrator = get_smart_orchestrator()
                                await orchestrator.execute_field(project.id, field.get("id"), db)

                                # به‌روزرسانی last_run و next_run
                                now = datetime.utcnow()
                                trigger["last_run"] = now.isoformat() + "Z"
                                trigger["next_run"] = (now + timedelta(minutes=interval)).isoformat() + "Z"
                                field["trigger"] = trigger
                                updated = True
                                executed += 1

                            except Exception as e:
                                slog.error(f"Failed to execute field {field.get('id')}", exception=e)

                    if updated:
                        project.dynamic_fields = json.dumps(fields)
                        db.commit()

                except Exception as e:
                    slog.error(f"Error processing project {project.id}", exception=e)
                    continue

            slog.success("Dynamic fields trigger completed", executed=executed)
            return {"executed": executed}

        except Exception as e:
            slog.error("Dynamic fields trigger failed", exception=e)
            db.rollback()
            return {"success": False, "error": str(e)}
        finally:
            db.close()

    # =====================================================
    # 4. Auto Security Findings Transfer
    # =====================================================

    async def _sync_security_transfer_settings(self):
        """همگام‌سازی تنظیمات انتقال یافته‌های امنیتی"""
        db = SessionLocal()
        try:
            settings = db.query(RenderLogSettings).first()
            if settings and getattr(settings, 'auto_security_transfer_enabled', False):
                interval = getattr(settings, 'auto_security_transfer_interval_minutes', 60) or 60
                await self._enable_security_transfer(interval)
            else:
                await self._disable_job(self.JOB_SECURITY_TRANSFER)
        except Exception as e:
            slog.error("Failed to sync security transfer settings", exception=e)
        finally:
            db.close()

    async def _enable_security_transfer(self, interval_minutes: int = 120):
        """فعال‌سازی job انتقال یافته‌های امنیتی"""
        if not self.scheduler:
            return

        self._remove_job_if_exists(self.JOB_SECURITY_TRANSFER)

        self.scheduler.add_job(
            self._run_security_transfer,
            trigger=IntervalTrigger(minutes=interval_minutes),
            id=self.JOB_SECURITY_TRANSFER,
            name="Auto Transfer Security Findings",
            replace_existing=True,
            max_instances=1
        )

        slog.success("Security transfer job enabled", interval_minutes=interval_minutes)

    async def _run_security_transfer(self):
        """اجرای انتقال یافته‌های امنیتی"""
        slog.info("Running auto security transfer")

        db = SessionLocal()
        try:
            from .health_to_issues_service import get_health_to_issues_service

            projects = db.query(Project).filter(Project.security_scan_result.isnot(None)).all()
            transferred = 0

            for project in projects:
                try:
                    service = get_health_to_issues_service()
                    result = await service.transfer_security_findings(project.id, db)
                    transferred += result.get("transferred", 0)
                except Exception as e:
                    slog.error(f"Security transfer failed for {project.id}", exception=e)

            slog.success("Auto security transfer completed", transferred=transferred)
            return {"transferred": transferred}

        except Exception as e:
            slog.error("Auto security transfer failed", exception=e)
            return {"success": False, "error": str(e)}
        finally:
            db.close()

    # =====================================================
    # 5. Auto Test Coverage Transfer
    # =====================================================

    async def _sync_test_coverage_transfer_settings(self):
        """همگام‌سازی تنظیمات انتقال پوشش تست"""
        db = SessionLocal()
        try:
            settings = db.query(RenderLogSettings).first()
            if settings and getattr(settings, 'auto_test_coverage_transfer_enabled', False):
                interval = getattr(settings, 'auto_test_coverage_transfer_interval_minutes', 60) or 60
                await self._enable_test_coverage_transfer(interval)
            else:
                await self._disable_job(self.JOB_TEST_COVERAGE_TRANSFER)
        except Exception as e:
            slog.error("Failed to sync test coverage transfer settings", exception=e)
        finally:
            db.close()

    async def _enable_test_coverage_transfer(self, interval_minutes: int = 120):
        """فعال‌سازی job انتقال پوشش تست"""
        if not self.scheduler:
            return

        self._remove_job_if_exists(self.JOB_TEST_COVERAGE_TRANSFER)

        self.scheduler.add_job(
            self._run_test_coverage_transfer,
            trigger=IntervalTrigger(minutes=interval_minutes),
            id=self.JOB_TEST_COVERAGE_TRANSFER,
            name="Auto Transfer Test Coverage Findings",
            replace_existing=True,
            max_instances=1
        )

        slog.success("Test coverage transfer job enabled", interval_minutes=interval_minutes)

    async def _run_test_coverage_transfer(self):
        """اجرای انتقال پوشش تست"""
        slog.info("Running auto test coverage transfer")

        db = SessionLocal()
        try:
            from .health_to_issues_service import get_health_to_issues_service

            projects = db.query(Project).filter(Project.test_coverage_result.isnot(None)).all()
            transferred = 0

            for project in projects:
                try:
                    service = get_health_to_issues_service()
                    result = await service.transfer_test_coverage_findings(project.id, db)
                    transferred += result.get("transferred", 0)
                except Exception as e:
                    slog.error(f"Test coverage transfer failed for {project.id}", exception=e)

            slog.success("Auto test coverage transfer completed", transferred=transferred)
            return {"transferred": transferred}

        except Exception as e:
            slog.error("Auto test coverage transfer failed", exception=e)
            return {"success": False, "error": str(e)}
        finally:
            db.close()

    # =====================================================
    # 6. Auto Engineering Report
    # =====================================================

    async def _sync_engineering_report_settings(self):
        """همگام‌سازی تنظیمات گزارش مهندسی خودکار"""
        db = SessionLocal()
        try:
            settings = db.query(RenderLogSettings).first()
            if settings and getattr(settings, 'auto_engineering_report_enabled', False):
                interval = getattr(settings, 'auto_engineering_report_interval_minutes', 180) or 180  # هر 3 ساعت
                await self._enable_engineering_report(interval)
            else:
                await self._disable_job(self.JOB_ENGINEERING_REPORT)
        except Exception as e:
            slog.error("Failed to sync engineering report settings", exception=e)
        finally:
            db.close()

    async def _enable_engineering_report(self, interval_minutes: int = 1440):
        """فعال‌سازی job گزارش مهندسی"""
        if not self.scheduler:
            return

        self._remove_job_if_exists(self.JOB_ENGINEERING_REPORT)

        self.scheduler.add_job(
            self._run_engineering_report,
            trigger=IntervalTrigger(minutes=interval_minutes),
            id=self.JOB_ENGINEERING_REPORT,
            name="Auto Engineering Report",
            replace_existing=True,
            max_instances=1
        )

        slog.success("Engineering report job enabled", interval_minutes=interval_minutes)

    async def _run_engineering_report(self):
        """اجرای گزارش مهندسی خودکار"""
        slog.info("Running auto engineering report")

        db = SessionLocal()
        try:
            # پروژه‌هایی که تحلیل سلامت دارند و تریگر گزارش مهندسی فعال است
            projects = db.query(Project).filter(
                Project.analysis_settings.isnot(None)
            ).all()

            generated = 0
            for project in projects:
                try:
                    settings = json.loads(project.analysis_settings) if project.analysis_settings else {}
                    if not settings.get("auto_engineering_report", False):
                        continue

                    # بررسی آیا تحلیل سلامت جدید انجام شده
                    if project.last_analysis_at:
                        # فقط اگر در 24 ساعت گذشته تحلیل شده باشد
                        if datetime.utcnow() - project.last_analysis_at > timedelta(hours=24):
                            continue

                    slog.info(f"Generating engineering report for project: {project.id}")

                    # استفاده از تابع اصلی generate_engineering_report
                    from ..api.routes.project_journal import generate_engineering_report

                    # فراخوانی مستقیم با پارامترهای پیش‌فرض
                    result = await generate_engineering_report(
                        project_id=project.id,
                        days=7,  # 7 روز گذشته
                        model_id="claude",  # مدل پیش‌فرض
                        auto_create_fields=True,
                        validate_health_issues=True,
                        db=db
                    )

                    if result.get("success"):
                        generated += 1
                        slog.info(f"Engineering report generated for {project.id}: {result.get('report_id')}")
                    else:
                        slog.warning(f"Engineering report failed for {project.id}: {result.get('error')}")

                except Exception as e:
                    slog.error(f"Engineering report failed for {project.id}", exception=e)

            slog.success("Auto engineering report completed", generated=generated)
            return {"generated": generated}

        except Exception as e:
            slog.error("Auto engineering report failed", exception=e)
            return {"success": False, "error": str(e)}
        finally:
            db.close()

    # =====================================================
    # 7. Auto Repo Discover (🆕 — GitHub → watched خودکار)
    # =====================================================
    #
    # هدف: هر N دقیقه repos کاربر را از GitHub بخواند، با لیست watched
    # موجود مقایسه کند، و repo های جدید را به‌صورت خودکار با
    # `auto_register_watched` ثبت کند.
    #
    # **محافظت در برابر خراب‌شدن**:
    # - off-by-default روی env var `REPO_AUTO_DISCOVER_ENABLED` (default: "1" = on)
    # - max_instances=1 (همزمانی نداریم)
    # - try/except سراسری — هرگز scheduler را crash نمی‌کند
    # - rate-limit aware: از cache 6 ساعته‌ی list_user_repos استفاده می‌کند
    # - **dedup در sublevel** — auto_register_watched خودش duplicate-check دارد
    # - **respects ignored repos** — اگر کاربر repo را از watched حذف کرده،
    #   در audit trail user_notes دیده می‌شود. در نسخه‌ی فعلی دوباره ثبت
    #   می‌شود (می‌توان در آینده با blocklist بهبود داد).

    async def _sync_repo_auto_discover_settings(self):
        """راه‌اندازی job کشف خودکار repo بر اساس env vars."""
        try:
            import os as _os
            enabled = _os.environ.get(
                "REPO_AUTO_DISCOVER_ENABLED", "1"
            ).strip().lower() in ("1", "true", "yes", "on")
            interval_minutes = int(
                _os.environ.get("REPO_AUTO_DISCOVER_INTERVAL_MINUTES", "60") or 60
            )
            if interval_minutes < 5:
                # حفاظت: حداقل 5 دقیقه interval تا rate-limit نخوریم
                interval_minutes = 5

            if enabled:
                await self._enable_repo_auto_discover(interval_minutes)
            else:
                await self._disable_job(self.JOB_REPO_AUTO_DISCOVER)
        except Exception as e:
            slog.error("Failed to sync repo auto-discover settings", exception=e)

    async def _enable_repo_auto_discover(self, interval_minutes: int = 60):
        """فعال‌سازی job کشف خودکار repo.

        اولین اجرا 30 ثانیه پس از startup — تا کاربر سریعاً ببیند کار می‌کند.
        سپس هر `interval_minutes` دقیقه تکرار.
        """
        if not self.scheduler:
            return
        self._remove_job_if_exists(self.JOB_REPO_AUTO_DISCOVER)
        from datetime import datetime as _dt, timedelta as _td
        first_run = _dt.now() + _td(seconds=30)
        self.scheduler.add_job(
            self._run_repo_auto_discover,
            trigger=IntervalTrigger(
                minutes=interval_minutes, start_date=first_run,
            ),
            id=self.JOB_REPO_AUTO_DISCOVER,
            name="Auto Discover New GitHub Repos",
            replace_existing=True,
            max_instances=1,
            next_run_time=first_run,
        )
        slog.success(
            "Repo auto-discover enabled",
            interval_minutes=interval_minutes,
            first_run_in_seconds=30,
        )

    async def _run_repo_auto_discover(self) -> Dict[str, Any]:
        """اجرای یک round کشف repo. ایمن در برابر هر خطایی."""
        slog.info("repo-auto-discover: round started")
        try:
            from .oversight_service import get_oversight_service
            service = get_oversight_service()

            # ۱) repos فعلی کاربر را از GitHub بگیر (force_refresh=True تا
            # یک snapshot تازه داشته باشیم — cache 6 ساعته در غیر این حالت
            # تشخیص repo جدید را به تأخیر می‌اندازد)
            repos_result = await service.list_user_repos(
                max_pages=5, force_refresh=True
            )
            if not repos_result.get("success"):
                slog.warning(
                    "repo-auto-discover: list_user_repos failed",
                    error=repos_result.get("error", "?"),
                )
                return {"success": False, "error": repos_result.get("error")}

            github_repos = repos_result.get("repos", []) or []
            total_github = len(github_repos)
            total_watched_before = len(service.watched)
            if not github_repos:
                slog.info(
                    "repo-auto-discover: no repos returned from GitHub "
                    "(token may be missing or repo list empty)"
                )
                return {"success": True, "discovered": 0, "skipped_existing": 0}

            # ۲) مجموعه‌ی repos موجود در watched (case-insensitive)
            existing_watched = {
                (w.repo_full_name or "").strip().lower()
                for w in service.watched
            }

            # ۳) برای هر repo جدید، auto_register_watched را صدا بزن
            discovered: List[Dict[str, Any]] = []
            skipped = 0
            failed: List[Dict[str, str]] = []
            for r in github_repos:
                full_name = (r.get("full_name") or "").strip()
                if not full_name or "/" not in full_name:
                    continue
                if full_name.lower() in existing_watched:
                    skipped += 1
                    continue
                # repo جدید پیدا شد
                try:
                    res = await service.auto_register_watched(
                        repo_full_name=full_name,
                        source="auto_discover_scheduler",
                        repo_url=r.get("html_url") or r.get("clone_url") or "",
                        default_branch=r.get("default_branch") or "main",
                        language=r.get("language") or "",
                        private=bool(r.get("private", False)),
                    )
                    if res.get("_was_duplicate"):
                        skipped += 1
                    else:
                        discovered.append({
                            "repo": full_name,
                            "watched_id": res.get("id"),
                        })
                except Exception as inner_e:
                    failed.append({"repo": full_name, "error": str(inner_e)})
                    slog.warning(
                        "repo-auto-discover: register failed",
                        repo=full_name,
                        error=str(inner_e),
                    )

            # خلاصه‌ی نهایی همیشه log می‌شود (حتی اگر discovered=0)
            slog.info(
                "repo-auto-discover: round done",
                total_github_repos=total_github,
                watched_before=total_watched_before,
                discovered=len(discovered),
                skipped_existing=skipped,
                failed=len(failed),
            )
            if discovered:
                slog.success(
                    "repo-auto-discover: NEW REPOS AUTO-WATCHED",
                    count=len(discovered),
                    repos=[d["repo"] for d in discovered][:10],
                )
            if failed:
                slog.warning(
                    "repo-auto-discover: some registrations failed",
                    count=len(failed),
                    samples=[f["repo"] for f in failed][:5],
                )
            return {
                "success": True,
                "discovered": len(discovered),
                "skipped_existing": skipped,
                "failed": len(failed),
                "details": discovered,
            }
        except Exception as e:
            # هرگز scheduler را crash نکن
            slog.error("repo-auto-discover: unexpected error", exception=e)
            return {"success": False, "error": str(e)}

    # =====================================================
    # Helper Methods
    # =====================================================

    def _remove_job_if_exists(self, job_id: str):
        """حذف job اگر وجود دارد"""
        if self.scheduler:
            existing = self.scheduler.get_job(job_id)
            if existing:
                self.scheduler.remove_job(job_id)

    async def _disable_job(self, job_id: str):
        """غیرفعال‌سازی یک job"""
        self._remove_job_if_exists(job_id)
        slog.info(f"Job disabled: {job_id}")

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
            self.scheduler.modify_job(job_id, next_run_time=datetime.utcnow())
            slog.info("Job triggered manually", job_id=job_id)
            return True
        return False

    async def refresh_all_jobs(self):
        """بارگذاری مجدد تنظیمات همه job ها"""
        await self._initialize_jobs()


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


async def start_background_scheduler():
    """شروع scheduler - برای فراخوانی در startup"""
    scheduler = get_background_scheduler()
    scheduler.start()


async def stop_background_scheduler():
    """توقف scheduler - برای فراخوانی در shutdown"""
    scheduler = get_background_scheduler()
    scheduler.stop()
