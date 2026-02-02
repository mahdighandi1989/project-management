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
from .journal_service import get_journal_service

logger = logging.getLogger(__name__)
slog = StructuredLogger(__name__, "LOG2ISSUE")
journal = get_journal_service()


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
        mode: str = "since_deploy",  # since_deploy یا time_based
        db: Session = None
    ) -> Dict[str, Any]:
        """
        انتقال لاگ‌های خطا به تب ایرادات

        Args:
            service_ids: لیست سرویس‌های مورد نظر (None = همه)
            hours: بازه زمانی (ساعت) - فقط در حالت time_based
            auto_mode: حالت خودکار (تریگر شده)
            mode: حالت فیلتر - since_deploy (از آخرین دیپلوی) یا time_based (بازه زمانی)
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
            error_logs = await self._get_error_logs(db, service_ids, hours, mode)
            slog.info("Found error logs", count=len(error_logs), mode=mode)

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

            # به‌روزرسانی last_transferred_deploy_id برای هر سرویس
            if mode == "since_deploy" and (result["transferred"] > 0 or result["merged"] > 0):
                await self._update_last_transferred_deploy(db, error_logs)

            # آرشیو کردن لاگ‌های منتقل شده
            if result["transferred"] > 0 or result["merged"] > 0:
                archive_result = await self._archive_transferred_logs(
                    db=db,
                    transferred_logs=error_logs,
                    service_project_map=service_project_map
                )
                result["archived"] = archive_result.get("archived_count", 0)

            db.commit()

            slog.success("Transfer completed",
                transferred=result["transferred"],
                merged=result["merged"],
                skipped=result["skipped"],
                archived=result.get("archived", 0),
                mode=mode
            )

            # ثبت در ژورنال برای هر پروژه
            for project_id in set(d.get("project_id") for d in result["details"] if d.get("project_id")):
                project_transferred = sum(1 for d in result["details"] if d.get("project_id") == project_id and d.get("status") == "transferred")
                project_merged = sum(1 for d in result["details"] if d.get("project_id") == project_id and d.get("status") == "merged")
                await journal.log_transfer(
                    project_id=project_id,
                    source="render_logs",
                    transferred=project_transferred,
                    merged=project_merged,
                    archived=result.get("archived", 0),
                    details={
                        "mode": mode,
                        "service_count": len(service_ids) if service_ids else "all"
                    },
                    db=db
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
        hours: int,
        mode: str = "since_deploy",
        force: bool = False
    ) -> List[RenderLog]:
        """
        دریافت لاگ‌های خطا

        Args:
            mode:
                - since_deploy: فقط خطاهای بعد از آخرین دیپلوی هر سرویس
                - time_based: خطاهای X ساعت اخیر
            force: اگر True باشد، لاگ‌های قبلاً منتقل شده هم برگردانده می‌شوند
        """
        error_logs = []

        # DEBUG: ابتدا تعداد کل لاگ‌های خطا را بررسی کن (بدون فیلتر transferred)
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        try:
            total_error_logs = db.query(RenderLog).filter(
                RenderLog.timestamp >= cutoff,
                RenderLog.level.in_(["error", "fatal", "critical"])
            ).count()
            slog.info(f"[DEBUG-TRANSFER] Total error logs in last {hours} hours: {total_error_logs}")

            # بررسی تعداد لاگ‌های منتقل شده
            try:
                transferred_count = db.query(RenderLog).filter(
                    RenderLog.timestamp >= cutoff,
                    RenderLog.level.in_(["error", "fatal", "critical"]),
                    RenderLog.transferred_to_issues == True
                ).count()
                slog.info(f"[DEBUG-TRANSFER] Already transferred: {transferred_count}")
            except Exception as e:
                slog.warning(f"[DEBUG-TRANSFER] Could not count transferred logs: {e}")
                transferred_count = 0

            # اگر force=True است، لاگ‌ها را ریست کن برای re-transfer
            if force and transferred_count > 0:
                slog.info(f"[DEBUG-TRANSFER] Force mode: resetting {transferred_count} transferred logs")

        except Exception as e:
            slog.warning(f"[DEBUG-TRANSFER] Could not get total count: {e}")
            total_error_logs = 0

        try:
            if mode == "since_deploy":
                # حالت جدید: فیلتر بر اساس آخرین دیپلوی
                try:
                    services_query = db.query(RenderService)
                    if service_ids:
                        services_query = services_query.filter(RenderService.id.in_(service_ids))
                    services = services_query.all()
                    slog.info(f"[DEBUG-TRANSFER] Found {len(services)} services")
                except Exception as e:
                    slog.warning("Error querying services, using fallback", exception=e)
                    services = []

                for service in services:
                    try:
                        # برای هر سرویس، لاگ‌های خطایی که منتقل نشده را بگیر
                        service_query = db.query(RenderLog).filter(
                            RenderLog.service_id == service.id,
                            RenderLog.level.in_(["error", "fatal", "critical"])
                        )

                        # DEBUG: تعداد خطاها قبل از فیلتر transferred
                        service_error_count = service_query.count()
                        slog.info(f"[DEBUG-TRANSFER] Service {service.name}: {service_error_count} error logs total")

                        # فیلتر لاگ‌های منتقل نشده - مگر اینکه force=True باشد
                        if not force:
                            try:
                                service_query = service_query.filter(
                                    RenderLog.transferred_to_issues == False
                                )
                            except Exception:
                                pass  # ستون وجود ندارد

                        # اگر آخرین دیپلوی منتقل شده مشخص باشه
                        last_transferred = getattr(service, 'last_transferred_deploy_id', None)
                        if last_transferred:
                            slog.info(f"[DEBUG-TRANSFER] Service {service.name}: filtering out deploy_id={last_transferred}")
                            service_query = service_query.filter(
                                RenderLog.deploy_id != last_transferred
                            )

                        logs = service_query.order_by(RenderLog.timestamp.desc()).limit(50).all()
                        error_logs.extend(logs)
                        slog.info(f"[DEBUG-TRANSFER] Service {service.name}: found {len(logs)} untransferred error logs")

                    except Exception as e:
                        slog.warning(f"Error querying logs for service {service.id}", exception=e)

                # اگر هیچ لاگی پیدا نشد، fallback به حالت time_based
                if not error_logs:
                    slog.info("[DEBUG-TRANSFER] No logs found in since_deploy mode, falling back to time_based")
                    mode = "time_based"

            if mode == "time_based" or not error_logs:
                # حالت قدیمی: فیلتر بر اساس زمان
                cutoff = datetime.utcnow() - timedelta(hours=hours)

                query = db.query(RenderLog).filter(
                    RenderLog.timestamp >= cutoff,
                    RenderLog.level.in_(["error", "fatal", "critical"])
                )

                if service_ids:
                    query = query.filter(RenderLog.service_id.in_(service_ids))

                # فیلتر لاگ‌های منتقل نشده - مگر اینکه force=True باشد
                if not force:
                    try:
                        query = query.filter(RenderLog.transferred_to_issues == False)
                    except Exception:
                        pass  # ستون وجود ندارد

                error_logs = query.order_by(RenderLog.timestamp.desc()).limit(100).all()
                slog.info(f"[DEBUG-TRANSFER] Time-based mode: found {len(error_logs)} error logs (force={force})")

        except Exception as e:
            slog.error("Error in _get_error_logs", exception=e)
            # Fallback: گرفتن همه لاگ‌های خطا بدون فیلتر پیچیده
            try:
                cutoff = datetime.utcnow() - timedelta(hours=hours)
                error_logs = db.query(RenderLog).filter(
                    RenderLog.timestamp >= cutoff,
                    RenderLog.level.in_(["error", "fatal", "critical"])
                ).order_by(RenderLog.timestamp.desc()).limit(100).all()
                slog.info(f"[DEBUG-TRANSFER] Fallback: found {len(error_logs)} error logs")
            except Exception as e2:
                slog.error("Fallback also failed", exception=e2)
                error_logs = []

        slog.info(f"[DEBUG-TRANSFER] Total error logs returned: {len(error_logs)}")
        return error_logs

    async def _update_last_transferred_deploy(
        self,
        db: Session,
        transferred_logs: List[RenderLog]
    ):
        """به‌روزرسانی آخرین دیپلوی منتقل شده برای هر سرویس"""
        # گروه‌بندی بر اساس سرویس
        service_deploys = {}
        for log in transferred_logs:
            if log.deploy_id and log.service_id:
                if log.service_id not in service_deploys:
                    service_deploys[log.service_id] = log.deploy_id
                # نگه داشتن جدیدترین deploy_id
                # (چون لاگ‌ها به ترتیب timestamp desc هستند، اولی جدیدترین است)

        # به‌روزرسانی سرویس‌ها
        for service_id, deploy_id in service_deploys.items():
            service = db.query(RenderService).filter(
                RenderService.id == service_id
            ).first()
            if service:
                service.last_transferred_deploy_id = deploy_id
                slog.info("Updated last_transferred_deploy",
                    service_id=service_id, deploy_id=deploy_id)

    async def _build_service_project_map(self, db: Session) -> Dict[str, Dict]:
        """
        ساخت نگاشت سرویس به پروژه

        بررسی می‌کند که آیا سرویس متعلق به پروژه‌ای ایمپورت شده است
        """
        service_project_map = {}

        # دریافت همه سرویس‌ها
        services = db.query(RenderService).all()
        slog.info(f"[DEBUG-LOG-TRANSFER] Found {len(services)} render services")

        # دریافت همه پروژه‌ها برای debug
        all_projects = db.query(Project).all()
        slog.info(f"[DEBUG-LOG-TRANSFER] Found {len(all_projects)} projects")
        for p in all_projects[:5]:  # نمایش 5 پروژه اول برای debug
            slog.info(f"[DEBUG-LOG-TRANSFER] Project: name={p.name}, github_path={p.github_path}")

        for service in services:
            slog.info(f"[DEBUG-LOG-TRANSFER] Processing service: {service.name} (id={service.id})")

            # جستجوی پروژه مرتبط
            # استراتژی ۱: نام سرویس در نام پروژه
            search_term = service.name.split('-')[0]
            slog.info(f"[DEBUG-LOG-TRANSFER] Strategy 1: searching for '{search_term}' in project names")
            project = db.query(Project).filter(
                Project.name.ilike(f"%{search_term}%")
            ).first()

            if not project:
                # استراتژی ۲: جستجو در GitHub path
                slog.info(f"[DEBUG-LOG-TRANSFER] Strategy 2: searching for '{service.name}' in github_path")
                project = db.query(Project).filter(
                    Project.github_path.ilike(f"%{service.name}%")
                ).first()

            if not project:
                # استراتژی ۳: جستجو در توضیحات
                slog.info(f"[DEBUG-LOG-TRANSFER] Strategy 3: searching in description")
                project = db.query(Project).filter(
                    Project.description.ilike(f"%{service.name}%")
                ).first()

            if not project:
                # استراتژی ۴: اولین پروژه (Fallback برای تست)
                slog.info(f"[DEBUG-LOG-TRANSFER] Strategy 4: fallback to first project")
                project = db.query(Project).first()

            if project:
                service_project_map[service.id] = {
                    "project_id": project.id,
                    "project_name": project.name,
                    "service_name": service.name
                }
                slog.info(f"[DEBUG-LOG-TRANSFER] Mapped service '{service.name}' to project '{project.name}'")
            else:
                slog.warning(f"[DEBUG-LOG-TRANSFER] No project found for service '{service.name}'")

        slog.info(f"[DEBUG-LOG-TRANSFER] Final service_project_map: {len(service_project_map)} mappings")
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
            "source_service_id": log.service_id,  # برای بررسی دیپلوی جدید
            "source_log_id": log.id,
            "source_deploy_id": log.deploy_id,  # دیپلوی زمان ایجاد ایراد
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

    async def _archive_transferred_logs(
        self,
        db: Session,
        transferred_logs: List[RenderLog],
        service_project_map: Dict
    ) -> Dict:
        """
        آرشیو کردن لاگ‌های منتقل شده به general_archive پروژه

        Args:
            db: Session دیتابیس
            transferred_logs: لاگ‌های منتقل شده
            service_project_map: نگاشت سرویس به پروژه

        Returns:
            {"archived_count": int}
        """
        import uuid

        archived_count = 0
        archive_timestamp = datetime.utcnow().isoformat()

        # گروه‌بندی لاگ‌ها بر اساس پروژه
        project_logs: Dict[str, List] = {}
        for log in transferred_logs:
            if log.service_id in service_project_map:
                project_id = service_project_map[log.service_id]["project_id"]
                if project_id not in project_logs:
                    project_logs[project_id] = []
                project_logs[project_id].append(log)

        # آرشیو کردن برای هر پروژه
        for project_id, logs in project_logs.items():
            try:
                project = db.query(Project).filter(Project.id == project_id).first()
                if not project:
                    continue

                # دریافت آرشیو موجود
                general_archive = []
                if project.general_archive:
                    try:
                        general_archive = json.loads(project.general_archive) if isinstance(project.general_archive, str) else project.general_archive
                    except:
                        general_archive = []

                # آرشیو کردن هر لاگ
                for log in logs:
                    archive_item = {
                        "id": str(uuid.uuid4()),
                        "type": "render_logs",
                        "category": log.level or "error",
                        "title": f"خطای Render: {log.service_name or 'unknown'}",
                        "content": {
                            "log_id": log.id,
                            "service_name": log.service_name,
                            "service_id": log.service_id,
                            "level": log.level,
                            "message": log.message,
                            "timestamp": log.timestamp.isoformat() if log.timestamp else None,
                            "deploy_id": log.deploy_id
                        },
                        "summary": log.message[:200] if log.message else "",
                        "archived_at": archive_timestamp,
                        "archived_reason": "transferred_to_issues",
                        "archived_by": "system",
                        "metadata": {
                            "original_created_at": log.timestamp.isoformat() if log.timestamp else archive_timestamp,
                            "source": "render_logs",
                            "transfer_status": "completed"
                        }
                    }
                    general_archive.append(archive_item)
                    archived_count += 1

                # ذخیره آرشیو
                project.general_archive = json.dumps(general_archive, ensure_ascii=False)

            except Exception as e:
                slog.error(f"Error archiving logs for project {project_id}", exception=e)

        slog.info(f"Archived {archived_count} logs to general archive")
        return {"archived_count": archived_count}

    async def archive_stale_issues_after_deploy(
        self,
        service_id: str,
        new_deploy_id: str,
        db: Session
    ) -> Dict:
        """
        بایگانی خودکار ایرادات قدیمی بعد از دیپلوی جدید

        وقتی یک دیپلوی جدید صورت می‌گیرد:
        1. ایرادات مربوط به دیپلوی‌های قبلی را پیدا کن
        2. این ایرادات را به آرشیو منتقل کن
        3. از لیست issues_found حذف کن

        این کار به این دلیل انجام می‌شود که:
        - خطاهای دیپلوی قبلی ممکن است در دیپلوی جدید رفع شده باشند
        - نگه داشتن آن‌ها باعث شلوغی می‌شود
        """
        try:
            from ..models.project import Project
            import uuid

            archived_count = 0
            archive_timestamp = datetime.utcnow().isoformat()

            # پیدا کردن پروژه‌های مرتبط با این سرویس
            service_project_map = await self._build_service_project_map(db)

            if service_id not in service_project_map:
                slog.info(f"No project mapping for service {service_id}")
                return {"archived_count": 0}

            project_id = service_project_map[service_id]["project_id"]
            project = db.query(Project).filter(Project.id == project_id).first()

            if not project:
                return {"archived_count": 0}

            # دریافت ایرادات موجود
            issues = []
            try:
                if project.issues_found:
                    issues = json.loads(project.issues_found)
            except:
                issues = []

            if not issues:
                return {"archived_count": 0}

            # دریافت آرشیو موجود
            general_archive = []
            if project.general_archive:
                try:
                    general_archive = json.loads(project.general_archive) if isinstance(project.general_archive, str) else project.general_archive
                except:
                    general_archive = []

            # فیلتر ایرادات قدیمی مربوط به این سرویس
            issues_to_keep = []
            issues_to_archive = []

            for issue in issues:
                # بررسی اینکه آیا ایراد مربوط به این سرویس و دیپلوی قدیمی است
                issue_service_id = issue.get("source_service_id")
                issue_deploy_id = issue.get("source_deploy_id")

                # اگر ایراد مربوط به این سرویس است و دیپلوی آن با دیپلوی جدید فرق دارد
                if (issue_service_id == service_id and
                    issue_deploy_id and
                    issue_deploy_id != new_deploy_id):
                    issues_to_archive.append(issue)
                else:
                    issues_to_keep.append(issue)

            if not issues_to_archive:
                slog.info(f"No stale issues to archive for service {service_id}")
                return {"archived_count": 0}

            # آرشیو کردن ایرادات قدیمی
            for issue in issues_to_archive:
                archive_item = {
                    "id": str(uuid.uuid4()),
                    "type": "stale_issue",
                    "category": "auto_archived_after_deploy",
                    "title": issue.get("message", "")[:100] if issue.get("message") else issue.get("error_type", "unknown"),
                    "content": issue,
                    "summary": f"ایراد بایگانی شده بعد از دیپلوی جدید {new_deploy_id}",
                    "archived_at": archive_timestamp,
                    "archived_reason": "new_deploy_superseded",
                    "archived_by": "system",
                    "metadata": {
                        "original_deploy_id": issue.get("source_deploy_id"),
                        "new_deploy_id": new_deploy_id,
                        "service_id": service_id,
                        "original_created_at": issue.get("first_occurrence", archive_timestamp)
                    }
                }
                general_archive.append(archive_item)
                archived_count += 1

            # ذخیره تغییرات
            project.issues_found = json.dumps(issues_to_keep, ensure_ascii=False)
            project.general_archive = json.dumps(general_archive, ensure_ascii=False)
            db.commit()

            slog.success(f"Auto-archived {archived_count} stale issues after deploy",
                service_id=service_id,
                new_deploy_id=new_deploy_id,
                project_id=project_id
            )

            return {
                "archived_count": archived_count,
                "remaining_issues": len(issues_to_keep)
            }

        except Exception as e:
            slog.error("Error archiving stale issues", exception=e)
            return {
                "archived_count": 0,
                "error": str(e)
            }


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
