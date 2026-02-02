# -*- coding: utf-8 -*-
"""
📝 سرویس ژورنال - ثبت متمرکز فعالیت‌ها
Journal Service - Centralized Activity Logging

این سرویس امکان ثبت آسان فعالیت‌ها از هر جای برنامه را فراهم می‌کند
"""

import json
import uuid
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session

from ..core.database import SessionLocal

logger = logging.getLogger(__name__)


class JournalService:
    """
    سرویس متمرکز ثبت فعالیت‌ها

    استفاده:
    ```
    journal = get_journal_service()
    await journal.log_activity(
        project_id="...",
        activity_type="transfer",
        summary="انتقال 5 یافته امنیتی به ایرادات",
        details={"transferred": 5, "merged": 2}
    )
    ```
    """

    def __init__(self):
        self.enabled = True

    def _get_db(self) -> Session:
        """دریافت Session جدید"""
        return SessionLocal()

    def _get_activity_log_class(self):
        """دریافت کلاس ActivityLog به صورت lazy"""
        from ..api.routes.project_journal import ActivityLog
        return ActivityLog

    def _get_detailed_operation_class(self):
        """دریافت کلاس DetailedOperation به صورت lazy"""
        from ..api.routes.project_journal import DetailedOperation
        return DetailedOperation

    async def log_activity(
        self,
        project_id: str,
        activity_type: str,
        summary: str,
        details: Optional[Dict] = None,
        model_id: str = "system",
        model_provider: str = "system",
        tokens_used: int = 0,
        latency_ms: int = 0,
        success: bool = True,
        error_message: Optional[str] = None,
        field_id: Optional[str] = None,
        field_name: Optional[str] = None,
        db: Session = None
    ) -> str:
        """
        ثبت یک فعالیت در ژورنال

        Args:
            project_id: شناسه پروژه
            activity_type: نوع فعالیت (transfer, scan, analysis, import, etc.)
            summary: خلاصه فعالیت
            details: جزئیات به صورت dict
            model_id: شناسه مدل استفاده شده
            model_provider: ارائه‌دهنده مدل
            tokens_used: تعداد توکن‌های مصرفی
            latency_ms: تاخیر به میلی‌ثانیه
            success: آیا موفق بود؟
            error_message: پیام خطا در صورت وجود
            field_id: شناسه فیلد مرتبط
            field_name: نام فیلد مرتبط
            db: Session دیتابیس (اختیاری)

        Returns:
            شناسه لاگ ایجاد شده
        """
        if not self.enabled:
            return None

        should_close_db = False
        if db is None:
            db = self._get_db()
            should_close_db = True

        try:
            ActivityLog = self._get_activity_log_class()

            log_id = f"act_{uuid.uuid4().hex[:12]}"
            log = ActivityLog(
                id=log_id,
                project_id=project_id,
                model_id=model_id,
                model_provider=model_provider,
                activity_type=activity_type,
                prompt=summary,
                response=json.dumps(details, ensure_ascii=False) if details else None,
                tokens_used=tokens_used,
                latency_ms=latency_ms,
                success=success,
                error_message=error_message,
                field_id=field_id,
                field_name=field_name,
                created_at=datetime.utcnow(),
                extra_data=json.dumps({
                    "summary": summary,
                    "source": "journal_service"
                }, ensure_ascii=False)
            )

            db.add(log)
            db.commit()

            logger.info(f"📝 Journal: [{activity_type}] {summary} (project={project_id})")
            return log_id

        except Exception as e:
            logger.error(f"Error logging activity: {e}")
            if should_close_db:
                db.rollback()
            return None

        finally:
            if should_close_db:
                db.close()

    async def log_detailed_operation(
        self,
        project_id: str,
        parent_log_id: Optional[str],
        operation_type: str,
        summary: str,
        details: Optional[Dict] = None,
        before_value: Optional[Any] = None,
        after_value: Optional[Any] = None,
        target_type: Optional[str] = None,
        target_id: Optional[str] = None,
        target_name: Optional[str] = None,
        status: str = "completed",
        sequence_number: int = 0,
        db: Session = None
    ) -> str:
        """
        ثبت یک عملیات جزئی

        Args:
            project_id: شناسه پروژه
            parent_log_id: شناسه لاگ والد
            operation_type: نوع عملیات
            summary: خلاصه عملیات
            details: جزئیات
            before_value: مقدار قبلی
            after_value: مقدار جدید
            target_type: نوع هدف (field, file, issue, etc.)
            target_id: شناسه هدف
            target_name: نام هدف
            status: وضعیت (completed, pending, failed, skipped)
            sequence_number: شماره ترتیب
            db: Session دیتابیس (اختیاری)

        Returns:
            شناسه عملیات ایجاد شده
        """
        if not self.enabled:
            return None

        should_close_db = False
        if db is None:
            db = self._get_db()
            should_close_db = True

        try:
            DetailedOperation = self._get_detailed_operation_class()

            op_id = f"op_{uuid.uuid4().hex[:12]}"
            op = DetailedOperation(
                id=op_id,
                project_id=project_id,
                parent_log_id=parent_log_id,
                sequence_number=sequence_number,
                operation_type=operation_type,
                summary=summary,
                details=json.dumps(details, ensure_ascii=False) if details else None,
                before_value=json.dumps(before_value, ensure_ascii=False) if before_value else None,
                after_value=json.dumps(after_value, ensure_ascii=False) if after_value else None,
                target_type=target_type,
                target_id=target_id,
                target_name=target_name,
                status=status,
                created_at=datetime.utcnow()
            )

            db.add(op)
            db.commit()

            return op_id

        except Exception as e:
            logger.error(f"Error logging detailed operation: {e}")
            if should_close_db:
                db.rollback()
            return None

        finally:
            if should_close_db:
                db.close()

    async def log_transfer(
        self,
        project_id: str,
        source: str,
        transferred: int,
        merged: int,
        archived: int = 0,
        details: Optional[Dict] = None,
        db: Session = None
    ) -> str:
        """
        ثبت عملیات انتقال به ایرادات

        Args:
            project_id: شناسه پروژه
            source: منبع (security_scan, test_coverage, render_logs)
            transferred: تعداد منتقل شده
            merged: تعداد ادغام شده
            archived: تعداد بایگانی شده
            details: جزئیات اضافی
            db: Session
        """
        source_labels = {
            "security_scan": "اسکن امنیتی",
            "test_coverage": "پوشش تست",
            "render_logs": "لاگ‌های Render"
        }
        source_label = source_labels.get(source, source)

        summary = f"انتقال یافته‌های {source_label}: {transferred} جدید، {merged} ادغام"
        if archived > 0:
            summary += f"، {archived} بایگانی"

        return await self.log_activity(
            project_id=project_id,
            activity_type="transfer",
            summary=summary,
            details={
                "source": source,
                "transferred": transferred,
                "merged": merged,
                "archived": archived,
                **(details or {})
            },
            db=db
        )

    async def log_scan(
        self,
        project_id: str,
        scan_type: str,
        findings_count: int,
        details: Optional[Dict] = None,
        db: Session = None
    ) -> str:
        """
        ثبت عملیات اسکن

        Args:
            project_id: شناسه پروژه
            scan_type: نوع اسکن (security, coverage, health)
            findings_count: تعداد یافته‌ها
            details: جزئیات اضافی
            db: Session
        """
        scan_labels = {
            "security": "امنیتی",
            "coverage": "پوشش تست",
            "health": "سلامت"
        }
        scan_label = scan_labels.get(scan_type, scan_type)

        summary = f"اسکن {scan_label}: {findings_count} یافته"

        return await self.log_activity(
            project_id=project_id,
            activity_type="scan",
            summary=summary,
            details={
                "scan_type": scan_type,
                "findings_count": findings_count,
                **(details or {})
            },
            db=db
        )

    async def log_archive(
        self,
        project_id: str,
        archived_count: int,
        source: str,
        details: Optional[Dict] = None,
        db: Session = None
    ) -> str:
        """
        ثبت عملیات بایگانی

        Args:
            project_id: شناسه پروژه
            archived_count: تعداد بایگانی شده
            source: منبع داده‌ها
            details: جزئیات اضافی
            db: Session
        """
        summary = f"بایگانی {archived_count} مورد از {source}"

        return await self.log_activity(
            project_id=project_id,
            activity_type="archive",
            summary=summary,
            details={
                "archived_count": archived_count,
                "source": source,
                **(details or {})
            },
            db=db
        )

    async def log_import(
        self,
        project_id: str,
        source: str,
        items_count: int,
        details: Optional[Dict] = None,
        db: Session = None
    ) -> str:
        """
        ثبت عملیات import

        Args:
            project_id: شناسه پروژه
            source: منبع (github, local, etc.)
            items_count: تعداد آیتم‌ها
            details: جزئیات اضافی
            db: Session
        """
        summary = f"ایمپورت از {source}: {items_count} فایل"

        return await self.log_activity(
            project_id=project_id,
            activity_type="import",
            summary=summary,
            details={
                "source": source,
                "items_count": items_count,
                **(details or {})
            },
            db=db
        )

    async def log_health_analysis(
        self,
        project_id: str,
        models_used: List[str],
        files_analyzed: int,
        issues_found: int,
        details: Optional[Dict] = None,
        db: Session = None
    ) -> str:
        """
        ثبت تحلیل سلامت

        Args:
            project_id: شناسه پروژه
            models_used: مدل‌های استفاده شده
            files_analyzed: تعداد فایل‌های تحلیل شده
            issues_found: تعداد ایرادات یافت شده
            details: جزئیات اضافی
            db: Session
        """
        summary = f"تحلیل سلامت: {files_analyzed} فایل، {issues_found} ایراد با {len(models_used)} مدل"

        return await self.log_activity(
            project_id=project_id,
            activity_type="health_analysis",
            summary=summary,
            model_id=models_used[0] if models_used else "unknown",
            details={
                "models_used": models_used,
                "files_analyzed": files_analyzed,
                "issues_found": issues_found,
                **(details or {})
            },
            db=db
        )

    async def log_issue_update(
        self,
        project_id: str,
        action: str,
        issue_title: str,
        details: Optional[Dict] = None,
        db: Session = None
    ) -> str:
        """
        ثبت تغییر ایراد

        Args:
            project_id: شناسه پروژه
            action: عملیات (create, update, resolve, delete)
            issue_title: عنوان ایراد
            details: جزئیات اضافی
            db: Session
        """
        action_labels = {
            "create": "ایجاد",
            "update": "به‌روزرسانی",
            "resolve": "حل شده",
            "delete": "حذف",
            "ignore": "نادیده گرفتن"
        }
        action_label = action_labels.get(action, action)

        summary = f"{action_label} ایراد: {issue_title[:50]}"

        return await self.log_activity(
            project_id=project_id,
            activity_type="issue_update",
            summary=summary,
            details={
                "action": action,
                "issue_title": issue_title,
                **(details or {})
            },
            db=db
        )

    async def log_download(
        self,
        project_id: str,
        download_type: str,
        format: str,
        items_count: int,
        db: Session = None
    ) -> str:
        """
        ثبت دانلود گزارش

        Args:
            project_id: شناسه پروژه
            download_type: نوع دانلود (security, coverage, archive)
            format: فرمت (json, csv, txt)
            items_count: تعداد آیتم‌ها
            db: Session
        """
        summary = f"دانلود گزارش {download_type} ({format}): {items_count} آیتم"

        return await self.log_activity(
            project_id=project_id,
            activity_type="download",
            summary=summary,
            details={
                "download_type": download_type,
                "format": format,
                "items_count": items_count
            },
            db=db
        )


# =====================================================
# Singleton Instance
# =====================================================

_journal_service: Optional[JournalService] = None


def get_journal_service() -> JournalService:
    """دریافت نمونه JournalService"""
    global _journal_service
    if _journal_service is None:
        _journal_service = JournalService()
    return _journal_service
