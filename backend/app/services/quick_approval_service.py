# -*- coding: utf-8 -*-
"""
⚡ سرویس تایید سریع فیلدها و تبدیل خودکار ایرادات بحرانی
Quick Approval Service

قابلیت‌ها:
1. تبدیل خودکار ایرادات بحرانی به فیلد (با validation_marker="auto_pending")
2. مکانیزم تایید سریع (بدون نیاز به گزارش مهندسی کامل)
3. بررسی تکراری بودن هنگام تبدیل ایراد به فیلد
4. اعتبارسنجی قبل از اجرا - بررسی حل شدن ایراد قبل از اجرای فیلد
"""

import json
import uuid
import re
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from sqlalchemy.orm import Session

from ..core.database import SessionLocal
from ..core.logging_utils import StructuredLogger
from ..models.project import Project, ProjectIssue
from .intelligent_field_creator import IntelligentFieldCreator, get_intelligent_field_creator
from .journal_service import get_journal_service

logger = logging.getLogger(__name__)
slog = StructuredLogger(__name__, "QUICK-APPROVAL")
journal = get_journal_service()


class QuickApprovalService:
    """
    سرویس تایید سریع و تبدیل خودکار ایرادات

    این سرویس مکمل Engineering Report است:
    - Engineering Report: بررسی کامل با AI، تایید قوی
    - Quick Approval: تایید سریع با یک کلیک، برای موارد واضح

    Validation Markers:
    - "pending": نیاز به Engineering Report
    - "auto_pending": تبدیل خودکار، نیاز به Quick Approval یا Engineering Report
    - "quick_approved": تایید سریع شده، آماده اجرا
    - "engineering_approved": تایید شده توسط Engineering Report
    """

    # آستانه اولویت برای تبدیل خودکار به فیلد
    CRITICAL_PRIORITY_THRESHOLD = 2  # 1=critical, 2=high

    # حداکثر تعداد فیلدهای auto_pending در هر پروژه
    MAX_AUTO_PENDING_FIELDS = 10

    def __init__(self):
        self.ai_manager = None

    def _get_ai_manager(self):
        """دریافت AI manager به صورت lazy"""
        if not self.ai_manager:
            from .ai_manager import get_ai_manager
            self.ai_manager = get_ai_manager()
        return self.ai_manager

    # =====================================================
    # 1. تبدیل خودکار ایرادات بحرانی به فیلد
    # =====================================================

    async def auto_convert_critical_issues(
        self,
        project_id: str,
        db: Session
    ) -> Dict[str, Any]:
        """
        تبدیل خودکار ایرادات بحرانی به فیلد

        معیارها:
        - priority <= 2 (critical یا high)
        - status == "open"
        - تکراری نباشد (با IntelligentFieldCreator بررسی می‌شود)

        Returns:
            {
                "success": bool,
                "converted": int,
                "skipped_duplicate": int,
                "skipped_limit": int,
                "fields_created": [...]
            }
        """
        slog.start("Auto-converting critical issues", project_id=project_id)

        result = {
            "success": True,
            "converted": 0,
            "skipped_duplicate": 0,
            "skipped_limit": 0,
            "fields_created": [],
            "errors": []
        }

        try:
            project = db.query(Project).filter(Project.id == project_id).first()
            if not project:
                result["success"] = False
                result["errors"].append("پروژه یافت نشد")
                return result

            # بارگذاری فیلدهای موجود
            existing_fields = []
            try:
                existing_fields = json.loads(project.dynamic_fields) if project.dynamic_fields else []
            except:
                existing_fields = []

            # شمارش فیلدهای auto_pending موجود
            auto_pending_count = sum(
                1 for f in existing_fields
                if f.get("validation_marker") == "auto_pending" and not f.get("archived")
            )

            if auto_pending_count >= self.MAX_AUTO_PENDING_FIELDS:
                slog.warning("Max auto_pending fields reached",
                    count=auto_pending_count, max=self.MAX_AUTO_PENDING_FIELDS)
                result["skipped_limit"] = "MAX_REACHED"
                return result

            # دریافت ایرادات بحرانی از جدول ProjectIssue
            critical_issues = db.query(ProjectIssue).filter(
                ProjectIssue.project_id == project_id,
                ProjectIssue.priority <= self.CRITICAL_PRIORITY_THRESHOLD,
                ProjectIssue.status == "open"
            ).order_by(ProjectIssue.priority.asc()).limit(
                self.MAX_AUTO_PENDING_FIELDS - auto_pending_count
            ).all()

            slog.info(f"Found {len(critical_issues)} critical issues to convert")

            # ایجاد IntelligentFieldCreator برای بررسی تکراری
            field_creator = get_intelligent_field_creator(project_id, db)

            for issue in critical_issues:
                try:
                    # بررسی تکراری بودن
                    duplicate_check = self._check_issue_duplicate_in_fields(
                        issue, existing_fields, field_creator
                    )

                    if duplicate_check["is_duplicate"]:
                        slog.info(f"Skipping duplicate issue: {issue.title[:50]}",
                            similarity=duplicate_check["similarity"])
                        result["skipped_duplicate"] += 1
                        continue

                    # تبدیل به فیلد
                    new_field = self._convert_issue_to_field(issue, project)

                    existing_fields.append(new_field)
                    result["converted"] += 1
                    result["fields_created"].append({
                        "field_id": new_field["id"],
                        "issue_id": issue.id,
                        "title": new_field["name"]
                    })

                    # علامت‌گذاری ایراد
                    issue.status = "converted_to_field"
                    issue.converted_field_id = new_field["id"]

                    slog.info(f"Converted issue to field: {issue.title[:50]}")

                except Exception as e:
                    slog.error(f"Error converting issue {issue.id}", exception=e)
                    result["errors"].append(str(e))

            # ذخیره فیلدها
            if result["converted"] > 0:
                project.dynamic_fields = json.dumps(existing_fields, ensure_ascii=False)
                db.commit()

                # ثبت در ژورنال
                await journal.log_activity(
                    project_id=project_id,
                    activity_type="auto_convert_issues",
                    details={
                        "converted": result["converted"],
                        "skipped_duplicate": result["skipped_duplicate"],
                        "fields": result["fields_created"]
                    },
                    db=db
                )

            slog.end("Auto-convert completed",
                converted=result["converted"],
                skipped=result["skipped_duplicate"]
            )

            return result

        except Exception as e:
            slog.error("Auto-convert failed", exception=e)
            result["success"] = False
            result["errors"].append(str(e))
            return result

    def _check_issue_duplicate_in_fields(
        self,
        issue: ProjectIssue,
        existing_fields: List[Dict],
        field_creator: IntelligentFieldCreator
    ) -> Dict[str, Any]:
        """
        بررسی تکراری بودن ایراد در فیلدهای موجود

        Returns:
            {
                "is_duplicate": bool,
                "similarity": float,
                "matching_field": dict or None
            }
        """
        issue_text = f"{issue.title} {issue.description or ''}"

        # استفاده از IntelligentFieldCreator برای بررسی شباهت
        existing_check = field_creator.check_existing_capability(issue_text)

        if existing_check["exists"] and existing_check["similarity"] > 0.7:
            return {
                "is_duplicate": True,
                "similarity": existing_check["similarity"],
                "matching_field": existing_check["match"]
            }

        # بررسی مستقیم در فیلدهای موجود
        for field in existing_fields:
            if field.get("archived"):
                continue

            field_text = f"{field.get('name', '')} {field.get('value', '')}"
            similarity = self._calculate_text_similarity(issue_text, field_text)

            if similarity > 0.7:
                return {
                    "is_duplicate": True,
                    "similarity": similarity,
                    "matching_field": field
                }

        return {
            "is_duplicate": False,
            "similarity": 0.0,
            "matching_field": None
        }

    def _convert_issue_to_field(self, issue: ProjectIssue, project: Project) -> Dict:
        """
        تبدیل یک ایراد به فیلد

        Returns:
            فیلد جدید با validation_marker="auto_pending"
        """
        # تعیین action_type بر اساس نوع ایراد
        action_type = "display"
        target_path = None

        issue_text = f"{issue.title} {issue.description or ''}".lower()

        # اگر مربوط به فایل خاصی باشد
        if issue.source_data:
            try:
                source_data = json.loads(issue.source_data)
                target_path = source_data.get("file") or source_data.get("file_path")
            except:
                pass

        # تشخیص نوع اکشن
        if any(kw in issue_text for kw in ["باگ", "bug", "خطا", "error", "fix", "اصلاح"]):
            action_type = "github_commit"
        elif any(kw in issue_text for kw in ["چند فایل", "multi", "refactor"]):
            action_type = "github_multi_commit"

        # اگر کامیت ولی فایل نداریم
        if action_type in ["github_commit"] and not target_path:
            action_type = "display"

        # محاسبه priority (1-10)
        priority_map = {1: 1, 2: 2, 3: 4, 4: 6}
        field_priority = priority_map.get(issue.priority, 5)

        field = {
            "id": f"auto_{uuid.uuid4().hex[:8]}",
            "name": issue.title[:100],
            "value": issue.solution or issue.description or "نیاز به بررسی",
            "target_models": ["all"],
            "action_type": action_type,
            "trigger": {"enabled": False, "interval_minutes": 60, "interval_type": "minutes"},
            "field_type": "temporary",
            "archived": False,
            "archive_after_run": True,
            "created_at": datetime.utcnow().isoformat(),
            "source": "auto_converted_issue",
            "source_issue_id": issue.id,
            "priority": field_priority,

            # ✅ نشانگرهای تایید
            "needs_approval": True,
            "validation_marker": "auto_pending",  # نیاز به تایید سریع یا Engineering Report
            "auto_converted_at": datetime.utcnow().isoformat(),

            # اطلاعات اصلی ایراد
            "original_issue": {
                "title": issue.title,
                "description": issue.description,
                "solution": issue.solution,
                "priority": issue.priority,
                "source": issue.source
            }
        }

        if target_path:
            field["target_path"] = target_path

        return field

    # =====================================================
    # 2. تایید سریع فیلدها
    # =====================================================

    async def quick_approve_field(
        self,
        project_id: str,
        field_id: str,
        approver_note: str = None,
        db: Session = None
    ) -> Dict[str, Any]:
        """
        تایید سریع یک فیلد

        این روش برای موارد واضح است که نیازی به Engineering Report کامل ندارند.

        Args:
            project_id: شناسه پروژه
            field_id: شناسه فیلد
            approver_note: یادداشت تایید کننده (اختیاری)
            db: session دیتابیس

        Returns:
            {
                "success": bool,
                "field": dict,
                "message": str
            }
        """
        slog.start("Quick approving field", project_id=project_id, field_id=field_id)

        should_close_db = False
        if db is None:
            db = SessionLocal()
            should_close_db = True

        try:
            project = db.query(Project).filter(Project.id == project_id).first()
            if not project:
                return {"success": False, "error": "پروژه یافت نشد"}

            # بارگذاری فیلدها
            fields = []
            try:
                fields = json.loads(project.dynamic_fields) if project.dynamic_fields else []
            except:
                fields = []

            # پیدا کردن فیلد
            field_found = None
            field_index = -1
            for i, f in enumerate(fields):
                if f.get("id") == field_id:
                    field_found = f
                    field_index = i
                    break

            if not field_found:
                return {"success": False, "error": "فیلد یافت نشد"}

            # بررسی اینکه آیا نیاز به تایید دارد
            if not field_found.get("needs_approval"):
                return {"success": False, "error": "این فیلد نیازی به تایید ندارد"}

            current_marker = field_found.get("validation_marker", "pending")
            if current_marker in ["quick_approved", "engineering_approved"]:
                return {"success": False, "error": "این فیلد قبلاً تایید شده است"}

            # تایید سریع
            field_found["validation_marker"] = "quick_approved"
            field_found["needs_approval"] = False
            field_found["quick_approved_at"] = datetime.utcnow().isoformat()
            if approver_note:
                field_found["approver_note"] = approver_note

            # ذخیره
            fields[field_index] = field_found
            project.dynamic_fields = json.dumps(fields, ensure_ascii=False)
            db.commit()

            # ثبت در ژورنال
            await journal.log_activity(
                project_id=project_id,
                activity_type="quick_approve_field",
                details={
                    "field_id": field_id,
                    "field_name": field_found.get("name"),
                    "previous_marker": current_marker,
                    "approver_note": approver_note
                },
                db=db
            )

            slog.success("Field quick approved", field_id=field_id)

            return {
                "success": True,
                "field": field_found,
                "message": f"فیلد '{field_found.get('name')}' با موفقیت تایید سریع شد"
            }

        except Exception as e:
            slog.error("Quick approve failed", exception=e)
            if should_close_db:
                db.rollback()
            return {"success": False, "error": str(e)}

        finally:
            if should_close_db:
                db.close()

    async def reject_field(
        self,
        project_id: str,
        field_id: str,
        rejection_reason: str,
        db: Session = None
    ) -> Dict[str, Any]:
        """
        رد کردن یک فیلد auto_pending

        Args:
            project_id: شناسه پروژه
            field_id: شناسه فیلد
            rejection_reason: دلیل رد
            db: session دیتابیس

        Returns:
            {
                "success": bool,
                "message": str
            }
        """
        slog.start("Rejecting field", project_id=project_id, field_id=field_id)

        should_close_db = False
        if db is None:
            db = SessionLocal()
            should_close_db = True

        try:
            project = db.query(Project).filter(Project.id == project_id).first()
            if not project:
                return {"success": False, "error": "پروژه یافت نشد"}

            # بارگذاری فیلدها
            fields = []
            try:
                fields = json.loads(project.dynamic_fields) if project.dynamic_fields else []
            except:
                fields = []

            # پیدا کردن فیلد
            field_found = None
            field_index = -1
            for i, f in enumerate(fields):
                if f.get("id") == field_id:
                    field_found = f
                    field_index = i
                    break

            if not field_found:
                return {"success": False, "error": "فیلد یافت نشد"}

            # آرشیو کردن فیلد
            field_found["archived"] = True
            field_found["rejection_reason"] = rejection_reason
            field_found["rejected_at"] = datetime.utcnow().isoformat()

            fields[field_index] = field_found
            project.dynamic_fields = json.dumps(fields, ensure_ascii=False)
            db.commit()

            # ثبت در ژورنال
            await journal.log_activity(
                project_id=project_id,
                activity_type="reject_auto_field",
                details={
                    "field_id": field_id,
                    "field_name": field_found.get("name"),
                    "rejection_reason": rejection_reason
                },
                db=db
            )

            slog.success("Field rejected", field_id=field_id)

            return {
                "success": True,
                "message": f"فیلد '{field_found.get('name')}' رد و آرشیو شد"
            }

        except Exception as e:
            slog.error("Reject field failed", exception=e)
            if should_close_db:
                db.rollback()
            return {"success": False, "error": str(e)}

        finally:
            if should_close_db:
                db.close()

    # =====================================================
    # 3. اعتبارسنجی قبل از اجرا (Pre-Execution Validation)
    # =====================================================

    async def pre_execution_validation(
        self,
        project_id: str,
        field_id: str,
        db: Session
    ) -> Dict[str, Any]:
        """
        🔍 اعتبارسنجی قبل از اجرای فیلد

        بررسی می‌کند:
        1. آیا ایراد اصلی هنوز وجود دارد؟
        2. آیا به صورت دستی یا روش دیگری حل شده؟
        3. آیا فایل هدف تغییر کرده؟

        Returns:
            {
                "can_execute": bool,
                "reason": str,
                "checks": {
                    "issue_still_exists": bool,
                    "file_modified": bool,
                    "similar_fix_applied": bool
                },
                "recommendation": str
            }
        """
        slog.start("Pre-execution validation", project_id=project_id, field_id=field_id)

        result = {
            "can_execute": True,
            "reason": None,
            "checks": {
                "issue_still_exists": True,
                "file_modified": False,
                "similar_fix_applied": False
            },
            "recommendation": "آماده اجرا"
        }

        try:
            project = db.query(Project).filter(Project.id == project_id).first()
            if not project:
                result["can_execute"] = False
                result["reason"] = "پروژه یافت نشد"
                return result

            # بارگذاری فیلدها
            fields = []
            try:
                fields = json.loads(project.dynamic_fields) if project.dynamic_fields else []
            except:
                fields = []

            # پیدا کردن فیلد
            field_found = None
            for f in fields:
                if f.get("id") == field_id:
                    field_found = f
                    break

            if not field_found:
                result["can_execute"] = False
                result["reason"] = "فیلد یافت نشد"
                return result

            # بررسی 1: آیا ایراد اصلی هنوز open است؟
            source_issue_id = field_found.get("source_issue_id")
            if source_issue_id:
                original_issue = db.query(ProjectIssue).filter(
                    ProjectIssue.id == source_issue_id
                ).first()

                if original_issue:
                    if original_issue.status in ["resolved", "closed", "fixed"]:
                        result["can_execute"] = False
                        result["checks"]["issue_still_exists"] = False
                        result["reason"] = "ایراد اصلی قبلاً حل شده است"
                        result["recommendation"] = "این فیلد را آرشیو کنید"
                        return result

            # بررسی 2: آیا فیلد مشابهی اخیراً اجرا شده؟
            for f in fields:
                if f.get("id") == field_id:
                    continue
                if f.get("archived") and f.get("executed_at"):
                    # بررسی شباهت
                    similarity = self._calculate_text_similarity(
                        f"{field_found.get('name', '')} {field_found.get('value', '')}",
                        f"{f.get('name', '')} {f.get('value', '')}"
                    )
                    if similarity > 0.7:
                        result["can_execute"] = False
                        result["checks"]["similar_fix_applied"] = True
                        result["reason"] = f"فیلد مشابه '{f.get('name')}' قبلاً اجرا شده"
                        result["recommendation"] = "این فیلد احتمالاً تکراری است"
                        return result

            # بررسی 3: اگر AI در دسترس است، بررسی هوشمند
            ai_validation = await self._ai_pre_validation(field_found, project)
            if ai_validation:
                if not ai_validation.get("should_execute", True):
                    result["can_execute"] = False
                    result["reason"] = ai_validation.get("reason", "AI توصیه به اجرا نمی‌کند")
                    result["recommendation"] = ai_validation.get("recommendation", "بررسی دستی")
                    return result

            slog.success("Pre-validation passed", field_id=field_id)
            return result

        except Exception as e:
            slog.error("Pre-validation failed", exception=e)
            # در صورت خطا، اجازه اجرا بده ولی هشدار بده
            result["can_execute"] = True
            result["reason"] = f"خطا در اعتبارسنجی: {str(e)}"
            result["recommendation"] = "با احتیاط اجرا کنید"
            return result

    async def _ai_pre_validation(
        self,
        field: Dict,
        project: Project
    ) -> Optional[Dict]:
        """
        اعتبارسنجی هوشمند با AI

        بررسی می‌کند آیا این فیلد هنوز معتبر و مورد نیاز است
        """
        try:
            ai_manager = self._get_ai_manager()
            if not ai_manager:
                return None

            # انتخاب مدل سریع
            available = ai_manager.get_available_models(task_type="validation")
            if not available:
                return None

            model_id = available[0].id if hasattr(available[0], 'id') else "claude"

            prompt = f"""به عنوان یک مهندس نرم‌افزار، بررسی کن آیا این فیلد/تسک هنوز نیاز به اجرا دارد:

## فیلد:
- نام: {field.get('name')}
- مقدار: {field.get('value', '')[:500]}
- نوع اکشن: {field.get('action_type')}
- ایجاد شده در: {field.get('created_at')}

## پروژه: {project.name}

## بررسی کن:
1. آیا این تسک منطقی است؟
2. آیا ممکن است قبلاً به روش دیگری حل شده باشد؟
3. آیا توصیه به اجرا می‌کنی؟

پاسخ JSON:
{{
    "should_execute": true/false,
    "confidence": 0.0-1.0,
    "reason": "دلیل کوتاه",
    "recommendation": "توصیه"
}}"""

            from .ai_base import Message
            response = await ai_manager.generate(
                model_id=model_id,
                messages=[Message(role="user", content=prompt)],
                max_tokens=500,
                temperature=0.2
            )

            # استخراج JSON
            result_text = response.content
            json_match = re.search(r'\{[\s\S]*\}', result_text)
            if json_match:
                return json.loads(json_match.group())

            return None

        except Exception as e:
            slog.warning("AI pre-validation failed", exception=e)
            return None

    # =====================================================
    # 4. لیست فیلدهای در انتظار تایید
    # =====================================================

    async def get_pending_approvals(
        self,
        project_id: str,
        db: Session
    ) -> Dict[str, Any]:
        """
        دریافت لیست فیلدهای در انتظار تایید

        Returns:
            {
                "auto_pending": [...],  # تبدیل خودکار، نیاز به تایید
                "pending": [...],  # از AI Q&A، نیاز به Engineering Report
                "total": int
            }
        """
        try:
            project = db.query(Project).filter(Project.id == project_id).first()
            if not project:
                return {"error": "پروژه یافت نشد"}

            fields = []
            try:
                fields = json.loads(project.dynamic_fields) if project.dynamic_fields else []
            except:
                fields = []

            auto_pending = []
            pending = []

            for f in fields:
                if f.get("archived"):
                    continue

                marker = f.get("validation_marker", "")
                needs_approval = f.get("needs_approval", False)

                if marker == "auto_pending":
                    auto_pending.append({
                        "id": f.get("id"),
                        "name": f.get("name"),
                        "value": f.get("value", "")[:200],
                        "priority": f.get("priority", 5),
                        "created_at": f.get("created_at"),
                        "source": f.get("source"),
                        "can_quick_approve": True
                    })
                elif marker == "pending" or needs_approval:
                    pending.append({
                        "id": f.get("id"),
                        "name": f.get("name"),
                        "value": f.get("value", "")[:200],
                        "priority": f.get("priority", 5),
                        "created_at": f.get("created_at"),
                        "source": f.get("source"),
                        "can_quick_approve": False,
                        "needs_engineering_report": True
                    })

            # مرتب‌سازی بر اساس اولویت
            auto_pending.sort(key=lambda x: x.get("priority", 5))
            pending.sort(key=lambda x: x.get("priority", 5))

            return {
                "auto_pending": auto_pending,
                "pending": pending,
                "total": len(auto_pending) + len(pending)
            }

        except Exception as e:
            slog.error("Get pending approvals failed", exception=e)
            return {"error": str(e)}

    # =====================================================
    # Helper Methods
    # =====================================================

    def _calculate_text_similarity(self, text1: str, text2: str) -> float:
        """محاسبه شباهت دو متن"""
        if not text1 or not text2:
            return 0.0

        text1 = text1.lower().strip()
        text2 = text2.lower().strip()

        if text1 == text2:
            return 1.0

        # شباهت کلمات (Jaccard)
        words1 = set(re.findall(r'\w+', text1))
        words2 = set(re.findall(r'\w+', text2))

        if not words1 or not words2:
            return 0.0

        intersection = words1 & words2
        union = words1 | words2

        return len(intersection) / len(union) if union else 0.0


# =====================================================
# Singleton Instance
# =====================================================

_quick_approval_instance: Optional[QuickApprovalService] = None


def get_quick_approval_service() -> QuickApprovalService:
    """دریافت نمونه QuickApprovalService"""
    global _quick_approval_instance
    if _quick_approval_instance is None:
        _quick_approval_instance = QuickApprovalService()
    return _quick_approval_instance
