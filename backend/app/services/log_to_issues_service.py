# -*- coding: utf-8 -*-
"""
🔄 سرویس انتقال خودکار خطاها از لاگ به ایرادات
Log to Issues Transfer Service

قابلیت‌ها:
1. شناسایی خودکار لاگ‌های خطا
2. تحلیل AI برای توضیح خطا
3. جستجوی ایرادات مشابه و ادغام
4. اضافه کردن به پروژه مناسب
5. فقط پروژه‌های ایمپورت شده
"""

import json
import re
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple

from sqlalchemy.orm import Session

from ..core.database import SessionLocal
from ..core.logging_utils import StructuredLogger
from ..models.project import Project
from ..models.render_log import RenderLog, RenderService
from .ai_manager import get_ai_manager
from .ai_base import Message

logger = logging.getLogger(__name__)
slog = StructuredLogger(__name__, "LOG2ISSUE")


class LogToIssuesService:
    """
    سرویس انتقال خودکار خطاها به تب ایرادات

    Flow:
    1. دریافت لاگ‌های خطا
    2. فیلتر بر اساس پروژه‌های ایمپورت شده
    3. تحلیل AI برای توضیح خطا
    4. جستجوی ایرادات مشابه
    5. ادغام یا ایجاد ردیف جدید
    """

    def __init__(self):
        self.ai_manager = None

    def initialize(self):
        """راه‌اندازی سرویس"""
        self.ai_manager = get_ai_manager()
        logger.info("LogToIssuesService initialized")

    async def transfer_error_logs(
        self,
        service_ids: List[str] = None,
        hours: int = 24,
        auto_mode: bool = False,
        db: Session = None
    ) -> Dict[str, Any]:
        """
        انتقال لاگ‌های خطا به تب ایرادات

        Args:
            service_ids: لیست سرویس‌های مورد نظر (None = همه)
            hours: بازه زمانی (ساعت)
            auto_mode: حالت خودکار (تریگر شده)
            db: نشست دیتابیس
        """
        if not self.ai_manager:
            self.initialize()

        should_close_db = False
        if db is None:
            db = SessionLocal()
            should_close_db = True

        try:
            result = {
                "success": True,
                "transferred": 0,
                "merged": 0,
                "skipped": 0,
                "errors": [],
                "details": []
            }

            # 1. دریافت لاگ‌های خطا
            error_logs = await self._get_error_logs(db, service_ids, hours)
            slog.info("Found error logs", count=len(error_logs))

            if not error_logs:
                result["message"] = "لاگ خطایی یافت نشد"
                return result

            # 2. دریافت پروژه‌های ایمپورت شده و نگاشت سرویس -> پروژه
            service_project_map = await self._build_service_project_map(db)
            slog.info("Service-Project mapping", map_count=len(service_project_map))

            # 3. پردازش هر لاگ خطا
            for log in error_logs:
                try:
                    transfer_result = await self._process_error_log(
                        log, service_project_map, db
                    )

                    if transfer_result["status"] == "transferred":
                        result["transferred"] += 1
                    elif transfer_result["status"] == "merged":
                        result["merged"] += 1
                    elif transfer_result["status"] == "skipped":
                        result["skipped"] += 1
                        result["errors"].append({
                            "log_id": log.id,
                            "reason": transfer_result.get("reason", "unknown")
                        })

                    result["details"].append(transfer_result)

                except Exception as e:
                    slog.error("Error processing log", log_id=log.id, exception=e)
                    result["errors"].append({
                        "log_id": log.id,
                        "error": str(e)
                    })

            db.commit()

            slog.success("Transfer completed",
                transferred=result["transferred"],
                merged=result["merged"],
                skipped=result["skipped"]
            )

            return result

        except Exception as e:
            slog.error("Transfer failed", exception=e)
            if should_close_db:
                db.rollback()
            return {
                "success": False,
                "error": str(e)
            }

        finally:
            if should_close_db:
                db.close()

    async def _get_error_logs(
        self,
        db: Session,
        service_ids: List[str],
        hours: int
    ) -> List[RenderLog]:
        """دریافت لاگ‌های خطا"""
        cutoff = datetime.utcnow() - timedelta(hours=hours)

        query = db.query(RenderLog).filter(
            RenderLog.timestamp >= cutoff,
            RenderLog.level.in_(["error", "fatal", "critical"])
        )

        if service_ids:
            query = query.filter(RenderLog.service_id.in_(service_ids))

        # فیلتر لاگ‌هایی که قبلاً منتقل نشده‌اند
        query = query.filter(RenderLog.transferred_to_issues == False)

        return query.order_by(RenderLog.timestamp.desc()).limit(100).all()

    async def _build_service_project_map(self, db: Session) -> Dict[str, Dict]:
        """
        ساخت نگاشت سرویس به پروژه

        بررسی می‌کند که آیا سرویس متعلق به پروژه‌ای ایمپورت شده است
        """
        service_project_map = {}

        # دریافت همه سرویس‌ها
        services = db.query(RenderService).all()

        for service in services:
            # جستجوی پروژه مرتبط
            # استراتژی ۱: نام سرویس در نام پروژه
            project = db.query(Project).filter(
                Project.name.ilike(f"%{service.name.split('-')[0]}%")
            ).first()

            if not project:
                # استراتژی ۲: جستجو در GitHub path
                project = db.query(Project).filter(
                    Project.github_path.ilike(f"%{service.name}%")
                ).first()

            if not project:
                # استراتژی ۳: جستجو در توضیحات
                project = db.query(Project).filter(
                    Project.description.ilike(f"%{service.name}%")
                ).first()

            if project:
                service_project_map[service.id] = {
                    "project_id": project.id,
                    "project_name": project.name,
                    "service_name": service.name
                }

        return service_project_map

    async def _process_error_log(
        self,
        log: RenderLog,
        service_project_map: Dict,
        db: Session
    ) -> Dict[str, Any]:
        """
        پردازش یک لاگ خطا

        1. بررسی پروژه مرتبط
        2. تحلیل AI
        3. جستجوی ایرادات مشابه
        4. ادغام یا ایجاد جدید
        """
        result = {
            "log_id": log.id,
            "status": "skipped",
            "reason": None,
            "project_id": None,
            "issue_index": None
        }

        # 1. بررسی اینکه سرویس پروژه‌ای دارد
        if log.service_id not in service_project_map:
            result["reason"] = "service_not_mapped"
            return result

        mapping = service_project_map[log.service_id]
        project_id = mapping["project_id"]
        result["project_id"] = project_id

        # دریافت پروژه
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            result["reason"] = "project_not_found"
            return result

        # 2. تحلیل AI برای توضیح خطا
        ai_analysis = await self._analyze_error_with_ai(log, project)

        # 3. دریافت ایرادات موجود
        issues = []
        try:
            if project.issues_found:
                issues = json.loads(project.issues_found)
        except:
            issues = []

        # 4. جستجوی ایراد مشابه
        similar_issue = self._find_similar_issue(
            log.message,
            ai_analysis.get("error_type", ""),
            issues
        )

        if similar_issue is not None:
            # ادغام با ایراد موجود
            merged_issue = self._merge_with_existing(
                issues[similar_issue],
                log,
                ai_analysis
            )
            issues[similar_issue] = merged_issue
            result["status"] = "merged"
            result["issue_index"] = similar_issue

        else:
            # ایجاد ایراد جدید
            new_issue = self._create_new_issue(log, ai_analysis, mapping)
            issues.append(new_issue)
            result["status"] = "transferred"
            result["issue_index"] = len(issues) - 1

        # 5. ذخیره ایرادات
        project.issues_found = json.dumps(issues, ensure_ascii=False)

        # علامت‌گذاری لاگ به عنوان منتقل شده
        log.transferred_to_issues = True
        log.transferred_at = datetime.utcnow()
        log.transferred_to_project = project_id

        result["ai_analysis"] = ai_analysis

        return result

    async def _analyze_error_with_ai(
        self,
        log: RenderLog,
        project: Project
    ) -> Dict[str, Any]:
        """تحلیل خطا با AI"""

        prompt = f"""تو یک متخصص دیباگ و تحلیل خطا هستی. این لاگ خطا را بررسی کن:

## لاگ خطا:
```
{log.message}
```

## اطلاعات:
- سرویس: {log.service_name}
- زمان: {log.timestamp}
- Deploy ID: {log.deploy_id or 'نامشخص'}
- پروژه: {project.name if project else 'نامشخص'}

## وظایف:
1. **نوع خطا**: چه نوع خطایی است (syntax, runtime, network, database, ...)
2. **علت احتمالی**: چرا این خطا رخ داده
3. **حالت‌های محتمل**: اگر علت مشخص نیست، چند احتمال بده
4. **اولویت**: بالا / متوسط / پایین
5. **پیشنهاد رفع**: چطور می‌توان رفع کرد

پاسخ JSON:
{{
    "error_type": "نوع خطا",
    "explanation": "توضیح کامل علت خطا (فارسی)",
    "possible_causes": ["علت ۱", "علت ۲"],
    "priority": "high|medium|low",
    "suggested_fix": "پیشنهاد رفع",
    "affected_components": ["کامپوننت ۱"],
    "search_keywords": ["کلمات کلیدی برای جستجو"]
}}"""

        try:
            # انتخاب مدل مناسب
            available = self.ai_manager.get_available_models(task_type="analysis")
            model_id = available[0].id if available else "claude"

            response = await self.ai_manager.generate(
                model_id=model_id,
                messages=[Message(role="user", content=prompt)],
                max_tokens=1000,
                temperature=0.3
            )

            # استخراج JSON
            return self._extract_json(response.content)

        except Exception as e:
            slog.error("AI analysis failed", exception=e)
            return {
                "error_type": "unknown",
                "explanation": f"تحلیل خودکار: {log.message[:200]}",
                "possible_causes": ["نیاز به بررسی دستی"],
                "priority": "medium",
                "suggested_fix": "بررسی لاگ کامل",
                "affected_components": [log.service_name or "unknown"],
                "search_keywords": []
            }

    def _find_similar_issue(
        self,
        error_message: str,
        error_type: str,
        existing_issues: List[Dict]
    ) -> Optional[int]:
        """
        جستجوی ایراد مشابه

        Returns:
            index ایراد مشابه یا None
        """
        for i, issue in enumerate(existing_issues):
            # بررسی نوع خطا
            if issue.get("error_type") == error_type and error_type:
                return i

            # بررسی تشابه پیام
            issue_message = issue.get("message", issue.get("description", ""))
            if self._messages_similar(error_message, issue_message):
                return i

            # بررسی کلمات کلیدی
            keywords = issue.get("search_keywords", [])
            for kw in keywords:
                if kw.lower() in error_message.lower():
                    return i

        return None

    def _messages_similar(self, msg1: str, msg2: str, threshold: float = 0.6) -> bool:
        """بررسی تشابه دو پیام"""
        if not msg1 or not msg2:
            return False

        # حذف اعداد و تاریخ‌ها
        clean1 = re.sub(r'\d+', 'N', msg1.lower())
        clean2 = re.sub(r'\d+', 'N', msg2.lower())

        # شکستن به کلمات
        words1 = set(clean1.split())
        words2 = set(clean2.split())

        if not words1 or not words2:
            return False

        # محاسبه Jaccard similarity
        intersection = len(words1 & words2)
        union = len(words1 | words2)

        similarity = intersection / union if union > 0 else 0

        return similarity >= threshold

    def _merge_with_existing(
        self,
        existing_issue: Dict,
        log: RenderLog,
        ai_analysis: Dict
    ) -> Dict:
        """ادغام با ایراد موجود"""

        # افزایش شمارنده تکرار
        existing_issue["occurrence_count"] = existing_issue.get("occurrence_count", 1) + 1

        # افزودن به تاریخچه
        if "occurrences" not in existing_issue:
            existing_issue["occurrences"] = []

        existing_issue["occurrences"].append({
            "log_id": log.id,
            "timestamp": log.timestamp.isoformat(),
            "service": log.service_name,
            "message_preview": log.message[:200]
        })

        # به‌روزرسانی آخرین وقوع
        existing_issue["last_occurrence"] = log.timestamp.isoformat()

        # به‌روزرسانی اولویت اگر تکرار زیاد شد
        if existing_issue["occurrence_count"] >= 5:
            existing_issue["priority"] = "high"
        elif existing_issue["occurrence_count"] >= 3:
            existing_issue["priority"] = "medium"

        return existing_issue

    def _create_new_issue(
        self,
        log: RenderLog,
        ai_analysis: Dict,
        mapping: Dict
    ) -> Dict:
        """ایجاد ایراد جدید"""
        return {
            "id": f"auto_{log.id}",
            "type": "auto_detected",
            "error_type": ai_analysis.get("error_type", "unknown"),
            "severity": ai_analysis.get("priority", "medium"),
            "priority": ai_analysis.get("priority", "medium"),
            "message": log.message,
            "description": ai_analysis.get("explanation", ""),
            "possible_causes": ai_analysis.get("possible_causes", []),
            "suggested_fix": ai_analysis.get("suggested_fix", ""),
            "affected_components": ai_analysis.get("affected_components", []),
            "search_keywords": ai_analysis.get("search_keywords", []),
            "source": "render_logs",
            "source_service": mapping.get("service_name", log.service_name),
            "source_log_id": log.id,
            "first_occurrence": log.timestamp.isoformat(),
            "last_occurrence": log.timestamp.isoformat(),
            "occurrence_count": 1,
            "occurrences": [{
                "log_id": log.id,
                "timestamp": log.timestamp.isoformat(),
                "service": log.service_name,
                "message_preview": log.message[:200]
            }],
            "status": "open",
            "created_at": datetime.utcnow().isoformat(),
            "auto_analyzed": True
        }

    def _extract_json(self, text: str) -> Dict:
        """استخراج JSON از متن"""
        try:
            return json.loads(text)
        except:
            pass

        # جستجوی JSON در متن
        json_match = re.search(r'\{[\s\S]*\}', text)
        if json_match:
            try:
                return json.loads(json_match.group())
            except:
                pass

        return {"error": "Could not parse JSON"}


# =====================================================
# Singleton Instance
# =====================================================

_log_to_issues_instance: Optional[LogToIssuesService] = None


def get_log_to_issues_service() -> LogToIssuesService:
    """دریافت نمونه LogToIssuesService"""
    global _log_to_issues_instance
    if _log_to_issues_instance is None:
        _log_to_issues_instance = LogToIssuesService()
    return _log_to_issues_instance
