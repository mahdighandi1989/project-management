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
    # 🆕 متدهای جدید برای لاگ کردن فعالیت‌های جزئی
    # =====================================================

    async def log_field_change(
        self,
        project_id: str,
        field_name: str,
        action: str,
        old_value: Optional[Any] = None,
        new_value: Optional[Any] = None,
        details: Optional[Dict] = None,
        db: Session = None
    ) -> str:
        """
        ثبت تغییر فیلد پویا

        Args:
            project_id: شناسه پروژه
            field_name: نام فیلد
            action: عملیات (create, update, execute, archive, restore)
            old_value: مقدار قبلی
            new_value: مقدار جدید
            details: جزئیات اضافی
            db: Session
        """
        action_labels = {
            "create": "ایجاد",
            "update": "به‌روزرسانی",
            "execute": "اجرا",
            "archive": "بایگانی",
            "restore": "بازیابی",
            "delete": "حذف"
        }
        action_label = action_labels.get(action, action)

        summary = f"{action_label} فیلد: {field_name}"

        return await self.log_activity(
            project_id=project_id,
            activity_type="field_change",
            summary=summary,
            field_name=field_name,
            details={
                "action": action,
                "field_name": field_name,
                "old_value": str(old_value)[:200] if old_value else None,
                "new_value": str(new_value)[:200] if new_value else None,
                **(details or {})
            },
            db=db
        )

    async def log_settings_change(
        self,
        project_id: str,
        settings_type: str,
        changes: Dict[str, Any],
        db: Session = None
    ) -> str:
        """
        ثبت تغییر تنظیمات

        Args:
            project_id: شناسه پروژه (یا 'global')
            settings_type: نوع تنظیمات (render_logs, ai_limits, sync, etc.)
            changes: تغییرات انجام شده
            db: Session
        """
        settings_labels = {
            "render_logs": "لاگ Render",
            "ai_limits": "محدودیت‌های AI",
            "sync": "همگام‌سازی",
            "auto_transfer": "انتقال خودکار",
            "trigger": "تریگر گزارش"
        }
        settings_label = settings_labels.get(settings_type, settings_type)

        # خلاصه تغییرات
        change_summary = ", ".join([f"{k}: {v}" for k, v in list(changes.items())[:3]])
        if len(changes) > 3:
            change_summary += f" و {len(changes) - 3} مورد دیگر"

        summary = f"تغییر تنظیمات {settings_label}: {change_summary}"

        return await self.log_activity(
            project_id=project_id,
            activity_type="settings_change",
            summary=summary,
            details={
                "settings_type": settings_type,
                "changes": changes
            },
            db=db
        )

    async def log_user_action(
        self,
        project_id: str,
        action: str,
        target: str,
        details: Optional[Dict] = None,
        db: Session = None
    ) -> str:
        """
        ثبت اقدام کاربر

        Args:
            project_id: شناسه پروژه
            action: نوع اقدام (view, click, navigate, search, filter)
            target: هدف اقدام (page, component, item)
            details: جزئیات اضافی
            db: Session
        """
        action_labels = {
            "view": "مشاهده",
            "click": "کلیک",
            "navigate": "پیمایش",
            "search": "جستجو",
            "filter": "فیلتر"
        }
        action_label = action_labels.get(action, action)

        summary = f"{action_label}: {target}"

        return await self.log_activity(
            project_id=project_id,
            activity_type="user_action",
            summary=summary,
            details={
                "action": action,
                "target": target,
                **(details or {})
            },
            db=db
        )

    async def log_file_operation(
        self,
        project_id: str,
        operation: str,
        file_path: str,
        details: Optional[Dict] = None,
        db: Session = None
    ) -> str:
        """
        ثبت عملیات فایل

        Args:
            project_id: شناسه پروژه
            operation: نوع عملیات (add, update, delete, analyze)
            file_path: مسیر فایل
            details: جزئیات اضافی
            db: Session
        """
        operation_labels = {
            "add": "افزودن",
            "update": "به‌روزرسانی",
            "delete": "حذف",
            "analyze": "تحلیل"
        }
        operation_label = operation_labels.get(operation, operation)

        summary = f"{operation_label} فایل: {file_path}"

        return await self.log_activity(
            project_id=project_id,
            activity_type="file_operation",
            summary=summary,
            details={
                "operation": operation,
                "file_path": file_path,
                **(details or {})
            },
            db=db
        )

    async def log_api_call(
        self,
        project_id: str,
        endpoint: str,
        method: str,
        status: str,
        latency_ms: int = 0,
        details: Optional[Dict] = None,
        db: Session = None
    ) -> str:
        """
        ثبت فراخوانی API

        Args:
            project_id: شناسه پروژه
            endpoint: آدرس endpoint
            method: متد HTTP (GET, POST, PUT, DELETE)
            status: وضعیت (success, error)
            latency_ms: زمان پاسخگویی
            details: جزئیات اضافی
            db: Session
        """
        status_icon = "✅" if status == "success" else "❌"
        summary = f"{status_icon} {method} {endpoint} ({latency_ms}ms)"

        return await self.log_activity(
            project_id=project_id,
            activity_type="api_call",
            summary=summary,
            latency_ms=latency_ms,
            success=status == "success",
            details={
                "endpoint": endpoint,
                "method": method,
                "status": status,
                **(details or {})
            },
            db=db
        )

    async def log_quick(
        self,
        project_id: str,
        activity_type: str,
        message: str,
        db: Session = None
    ) -> str:
        """
        لاگ سریع برای فعالیت‌های کوچک

        Args:
            project_id: شناسه پروژه
            activity_type: نوع فعالیت
            message: پیام کوتاه
            db: Session
        """
        return await self.log_activity(
            project_id=project_id,
            activity_type=activity_type,
            summary=message,
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
