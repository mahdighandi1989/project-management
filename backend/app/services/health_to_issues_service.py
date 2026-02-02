# -*- coding: utf-8 -*-
"""
🔄 سرویس انتقال گزارشات سلامت به تب ایرادات
Health Reports to Issues Transfer Service

امکانات:
- انتقال یافته‌های امنیتی به ایرادات
- انتقال نقص‌های پوشش تست به ایرادات
- بسط و شرح توسط AI
- ادغام با ایرادات مشابه
- اولویت‌بندی خودکار
"""

import json
import logging
from datetime import datetime
from typing import List, Dict, Optional, Any
from sqlalchemy.orm import Session

from ..core.database import SessionLocal
from ..core.logging_utils import StructuredLogger
from ..models.project import Project, ProjectIssue
from .journal_service import get_journal_service

slog = StructuredLogger(__name__, "HEALTH-TRANSFER")
logger = logging.getLogger(__name__)
journal = get_journal_service()


class HealthToIssuesService:
    """سرویس انتقال گزارشات سلامت به ایرادات"""

    def __init__(self):
        self.ai_manager = None

    def _get_ai_manager(self):
        """دریافت AI manager به صورت lazy"""
        if not self.ai_manager:
            from .ai_manager import get_ai_manager
            self.ai_manager = get_ai_manager()
        return self.ai_manager

    async def _get_best_model(self) -> str:
        """انتخاب بهترین مدل AI موجود"""
        ai_manager = self._get_ai_manager()
        available = ai_manager.get_available_models()

        # اولویت مدل‌ها
        preferred_models = [
            "claude-3-5-sonnet",
            "claude-3-opus",
            "gpt-4-turbo",
            "gpt-4",
            "gemini-1.5-pro",
            "deepseek-chat",
            "gpt-3.5-turbo"
        ]

        for model in preferred_models:
            for avail in available:
                if model in avail.get("id", ""):
                    return avail["id"]

        # اگر هیچکدام نبود، اولین مدل موجود
        if available:
            return available[0]["id"]

        return None

    async def _enhance_with_ai(
        self,
        issue_type: str,
        raw_content: Dict,
        project_name: str
    ) -> Dict[str, str]:
        """
        بسط و شرح یافته توسط AI

        Returns:
            {
                "title": "عنوان بهبودیافته",
                "description": "توضیحات کامل",
                "solution": "راه‌حل پیشنهادی",
                "priority": "high/medium/low"
            }
        """
        model_id = await self._get_best_model()
        if not model_id:
            # اگر مدلی نبود، خروجی ساده
            return {
                "title": raw_content.get("title", "یافته جدید"),
                "description": json.dumps(raw_content, ensure_ascii=False, indent=2),
                "solution": "نیاز به بررسی دستی",
                "priority": "medium"
            }

        ai_manager = self._get_ai_manager()

        # ساخت prompt بر اساس نوع
        if issue_type == "security":
            prompt = f"""
به عنوان یک متخصص امنیت نرم‌افزار، یافته امنیتی زیر را تحلیل کن و به فارسی توضیح بده.

پروژه: {project_name}
یافته امنیتی:
{json.dumps(raw_content, ensure_ascii=False, indent=2)}

لطفاً خروجی را دقیقاً در فرمت JSON زیر بده:
{{
    "title": "عنوان کوتاه و گویا (حداکثر 100 کاراکتر)",
    "description": "توضیح کامل مشکل امنیتی، علت آن، و تأثیرات احتمالی",
    "solution": "راه‌حل پیشنهادی برای رفع این مشکل امنیتی با مثال کد در صورت نیاز",
    "priority": "یکی از: critical, high, medium, low"
}}

فقط JSON خالص برگردان، بدون توضیحات اضافی.
"""
        elif issue_type == "test_coverage":
            prompt = f"""
به عنوان یک متخصص تست نرم‌افزار، نقص پوشش تست زیر را تحلیل کن و به فارسی توضیح بده.

پروژه: {project_name}
یافته:
{json.dumps(raw_content, ensure_ascii=False, indent=2)}

لطفاً خروجی را دقیقاً در فرمت JSON زیر بده:
{{
    "title": "عنوان کوتاه و گویا (حداکثر 100 کاراکتر)",
    "description": "توضیح کامل نقص تست، اهمیت پوشش تست برای این بخش، و ریسک‌های عدم تست",
    "solution": "راه‌حل پیشنهادی شامل نوع تست‌هایی که باید نوشته شود",
    "priority": "یکی از: critical, high, medium, low"
}}

فقط JSON خالص برگردان، بدون توضیحات اضافی.
"""
        else:
            prompt = f"""
یافته زیر را تحلیل کن و به فارسی توضیح بده:

پروژه: {project_name}
یافته:
{json.dumps(raw_content, ensure_ascii=False, indent=2)}

لطفاً خروجی را دقیقاً در فرمت JSON زیر بده:
{{
    "title": "عنوان کوتاه",
    "description": "توضیح کامل",
    "solution": "راه‌حل پیشنهادی",
    "priority": "یکی از: critical, high, medium, low"
}}

فقط JSON خالص برگردان.
"""

        try:
            response = await ai_manager.generate(
                prompt=prompt,
                model_id=model_id,
                max_tokens=1500,
                temperature=0.3
            )

            result_text = response.get("content", "")

            # استخراج JSON از پاسخ
            import re
            json_match = re.search(r'\{[\s\S]*\}', result_text)
            if json_match:
                enhanced = json.loads(json_match.group())
                return {
                    "title": enhanced.get("title", raw_content.get("title", "یافته")),
                    "description": enhanced.get("description", ""),
                    "solution": enhanced.get("solution", ""),
                    "priority": enhanced.get("priority", "medium")
                }
        except Exception as e:
            slog.error("AI enhancement failed", exception=e)

        # Fallback
        return {
            "title": raw_content.get("title", raw_content.get("type", "یافته")),
            "description": json.dumps(raw_content, ensure_ascii=False, indent=2),
            "solution": "نیاز به بررسی دستی",
            "priority": "medium"
        }

    def _find_similar_issue(
        self,
        db: Session,
        project_id: str,
        title: str,
        issue_type: str
    ) -> Optional[ProjectIssue]:
        """
        جستجوی ایراد مشابه
        بر اساس عنوان و نوع
        """
        # جستجوی دقیق
        existing = db.query(ProjectIssue).filter(
            ProjectIssue.project_id == project_id,
            ProjectIssue.title == title,
            ProjectIssue.source == issue_type
        ).first()

        if existing:
            return existing

        # جستجوی fuzzy - اگر عنوان شبیه باشد
        all_issues = db.query(ProjectIssue).filter(
            ProjectIssue.project_id == project_id,
            ProjectIssue.source == issue_type
        ).all()

        for issue in all_issues:
            # اگر بیش از 70% شباهت داشت
            if self._similarity(issue.title, title) > 0.7:
                return issue

        return None

    def _similarity(self, s1: str, s2: str) -> float:
        """محاسبه شباهت دو رشته"""
        if not s1 or not s2:
            return 0.0

        s1_words = set(s1.lower().split())
        s2_words = set(s2.lower().split())

        if not s1_words or not s2_words:
            return 0.0

        intersection = len(s1_words & s2_words)
        union = len(s1_words | s2_words)

        return intersection / union if union > 0 else 0.0

    def _priority_to_order(self, priority: str) -> int:
        """تبدیل اولویت به عدد برای مرتب‌سازی"""
        mapping = {
            "critical": 1,
            "high": 2,
            "medium": 3,
            "low": 4
        }
        return mapping.get(priority.lower(), 3)

    async def transfer_security_findings(
        self,
        project_id: str,
        scan_result: Dict,
        db: Session
    ) -> Dict:
        """
        انتقال یافته‌های امنیتی به تب ایرادات
        """
        slog.info("Transferring security findings", project_id=project_id)

        # Debug: نمایش ساختار scan_result
        slog.info(f"[DEBUG] scan_result keys: {list(scan_result.keys()) if scan_result else 'None'}")
        slog.info(f"[DEBUG] secrets: {scan_result.get('secrets', {})}")
        slog.info(f"[DEBUG] sensitive_files: {scan_result.get('sensitive_files', {})}")
        slog.info(f"[DEBUG] dependencies: {scan_result.get('dependencies', {})}")

        # دریافت پروژه
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            return {"success": False, "error": "پروژه یافت نشد"}

        transferred = 0
        merged = 0
        errors = []

        # پردازش یافته‌های مختلف
        findings_to_process = []

        # Secrets - ساختار: secrets.findings[]
        secrets_data = scan_result.get("secrets", {})
        secrets_list = secrets_data.get("findings", []) if isinstance(secrets_data, dict) else secrets_data
        slog.info(f"[DEBUG] secrets_list count: {len(secrets_list)}")
        for secret in secrets_list:
            findings_to_process.append({
                "type": "secret",
                "title": f"کلید محرمانه در {secret.get('file', 'unknown')}",
                "data": secret
            })

        # Vulnerabilities - ساختار: dependencies.vulnerabilities[]
        deps_data = scan_result.get("dependencies", {})
        vulns_list = deps_data.get("vulnerabilities", []) if isinstance(deps_data, dict) else []
        slog.info(f"[DEBUG] vulns_list count: {len(vulns_list)}")
        for vuln in vulns_list:
            findings_to_process.append({
                "type": "vulnerability",
                "title": f"آسیب‌پذیری: {vuln.get('type', 'unknown')}",
                "data": vuln
            })

        # Sensitive files - ساختار: sensitive_files.findings[]
        sensitive_data = scan_result.get("sensitive_files", {})
        sensitive_list = sensitive_data.get("findings", []) if isinstance(sensitive_data, dict) else sensitive_data
        slog.info(f"[DEBUG] sensitive_list count: {len(sensitive_list)}")
        for sensitive in sensitive_list:
            findings_to_process.append({
                "type": "sensitive_file",
                "title": f"فایل حساس: {sensitive.get('file', 'unknown')}",
                "data": sensitive
            })

        # License issues - ساختار: license.has_license
        license_data = scan_result.get("license", {})
        if isinstance(license_data, dict) and not license_data.get("has_license", True):
            findings_to_process.append({
                "type": "license",
                "title": "پروژه فاقد لایسنس است",
                "data": license_data
            })

        # Summary issues
        summary = scan_result.get("summary", {})
        if summary.get("total_issues", 0) > 0:
            findings_to_process.append({
                "type": "security_summary",
                "title": f"خلاصه امنیتی: {summary.get('total_issues', 0)} مشکل",
                "data": summary
            })

        slog.info(f"[DEBUG] Total findings_to_process: {len(findings_to_process)}")
        slog.info(f"[DEBUG] findings_to_process types: {[f['type'] for f in findings_to_process]}")

        # پردازش هر یافته
        for i, finding in enumerate(findings_to_process):
            slog.info(f"[DEBUG] Processing finding {i+1}/{len(findings_to_process)}: {finding.get('type')}")
            try:
                # بسط توسط AI
                enhanced = await self._enhance_with_ai(
                    "security",
                    finding,
                    project.name
                )
                slog.info(f"[DEBUG] Enhanced result: title={enhanced.get('title', 'NO_TITLE')[:50]}")

                # جستجوی ایراد مشابه
                existing = self._find_similar_issue(
                    db,
                    project_id,
                    enhanced["title"],
                    "security_scan"
                )

                if existing:
                    # ادغام با موجود
                    existing.description = enhanced["description"]
                    existing.solution = enhanced.get("solution", "")
                    existing.priority = self._priority_to_order(enhanced["priority"])
                    existing.updated_at = datetime.utcnow()
                    existing.occurrences = (existing.occurrences or 0) + 1
                    merged += 1
                else:
                    # ایجاد جدید
                    new_issue = ProjectIssue(
                        project_id=project_id,
                        title=enhanced["title"],
                        description=enhanced["description"],
                        solution=enhanced.get("solution", ""),
                        priority=self._priority_to_order(enhanced["priority"]),
                        status="open",
                        source="security_scan",
                        source_data=json.dumps(finding, ensure_ascii=False),
                        occurrences=1,
                        created_at=datetime.utcnow()
                    )
                    db.add(new_issue)
                    transferred += 1

            except Exception as e:
                slog.error(f"[DEBUG] Error processing security finding: {str(e)}", exception=e)
                errors.append(str(e))

        db.commit()

        # آرشیو کردن یافته‌ها و پاک کردن نتایج اصلی
        archive_result = self._archive_and_clear(
            db=db,
            project=project,
            findings=findings_to_process,
            source_type="security_scan",
            scan_result=scan_result
        )

        slog.success("Security findings transferred",
            project_id=project_id,
            transferred=transferred,
            merged=merged,
            archived=archive_result.get("archived_count", 0)
        )

        # ثبت در ژورنال
        await journal.log_transfer(
            project_id=project_id,
            source="security_scan",
            transferred=transferred,
            merged=merged,
            archived=archive_result.get("archived_count", 0),
            details={
                "total_findings": len(findings_to_process),
                "errors_count": len(errors)
            },
            db=db
        )

        return {
            "success": True,
            "transferred": transferred,
            "merged": merged,
            "total_findings": len(findings_to_process),
            "archived": archive_result.get("archived_count", 0),
            "errors": errors if errors else None
        }

    async def transfer_test_coverage_findings(
        self,
        project_id: str,
        coverage_result: Dict,
        db: Session
    ) -> Dict:
        """
        انتقال یافته‌های پوشش تست به تب ایرادات
        """
        slog.info("Transferring test coverage findings", project_id=project_id)

        # Debug: نمایش ساختار coverage_result
        slog.info(f"[DEBUG] coverage_result keys: {list(coverage_result.keys()) if coverage_result else 'None'}")
        slog.info(f"[DEBUG] untested_files count: {len(coverage_result.get('untested_files', []))}")
        slog.info(f"[DEBUG] recommendations count: {len(coverage_result.get('recommendations', []))}")

        # دریافت پروژه
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            return {"success": False, "error": "پروژه یافت نشد"}

        transferred = 0
        merged = 0
        errors = []

        findings_to_process = []

        # فایل‌های بدون تست - ساختار: untested_files[].path
        for untested in coverage_result.get("untested_files", []):
            file_path = untested.get("path", untested.get("file", "unknown"))
            findings_to_process.append({
                "type": "untested_file",
                "title": f"فایل بدون تست: {file_path}",
                "data": untested
            })

        # توصیه‌ها - ساختار: recommendations[].message
        for rec in coverage_result.get("recommendations", []):
            msg = rec.get("message", rec.get("title", "توصیه تست"))
            findings_to_process.append({
                "type": "test_recommendation",
                "title": msg,
                "data": rec
            })

        # نمره پایین پوشش
        summary = coverage_result.get("summary", {})
        if summary.get("coverage_percent", 100) < 50:
            findings_to_process.append({
                "type": "low_coverage",
                "title": f"پوشش تست پایین: {summary.get('coverage_percent', 0)}%",
                "data": summary
            })

        slog.info(f"[DEBUG] Total findings_to_process: {len(findings_to_process)}")
        slog.info(f"[DEBUG] findings_to_process types: {[f['type'] for f in findings_to_process]}")

        # پردازش هر یافته
        for i, finding in enumerate(findings_to_process):
            slog.info(f"[DEBUG] Processing finding {i+1}/{len(findings_to_process)}: {finding.get('type')}")
            try:
                # بسط توسط AI
                enhanced = await self._enhance_with_ai(
                    "test_coverage",
                    finding,
                    project.name
                )
                slog.info(f"[DEBUG] Enhanced result: title={enhanced.get('title', 'NO_TITLE')[:50]}")

                # جستجوی ایراد مشابه
                existing = self._find_similar_issue(
                    db,
                    project_id,
                    enhanced["title"],
                    "test_coverage"
                )

                if existing:
                    # ادغام با موجود
                    existing.description = enhanced["description"]
                    existing.solution = enhanced.get("solution", "")
                    existing.priority = self._priority_to_order(enhanced["priority"])
                    existing.updated_at = datetime.utcnow()
                    existing.occurrences = (existing.occurrences or 0) + 1
                    merged += 1
                else:
                    # ایجاد جدید
                    new_issue = ProjectIssue(
                        project_id=project_id,
                        title=enhanced["title"],
                        description=enhanced["description"],
                        solution=enhanced.get("solution", ""),
                        priority=self._priority_to_order(enhanced["priority"]),
                        status="open",
                        source="test_coverage",
                        source_data=json.dumps(finding, ensure_ascii=False),
                        occurrences=1,
                        created_at=datetime.utcnow()
                    )
                    db.add(new_issue)
                    transferred += 1

            except Exception as e:
                slog.error(f"[DEBUG] Error processing test coverage finding: {str(e)}", exception=e)
                errors.append(str(e))

        db.commit()

        # آرشیو کردن یافته‌ها و پاک کردن نتایج اصلی
        archive_result = self._archive_and_clear(
            db=db,
            project=project,
            findings=findings_to_process,
            source_type="test_coverage",
            scan_result=coverage_result
        )

        slog.success("Test coverage findings transferred",
            project_id=project_id,
            transferred=transferred,
            merged=merged,
            archived=archive_result.get("archived_count", 0)
        )

        # ثبت در ژورنال
        await journal.log_transfer(
            project_id=project_id,
            source="test_coverage",
            transferred=transferred,
            merged=merged,
            archived=archive_result.get("archived_count", 0),
            details={
                "total_findings": len(findings_to_process),
                "errors_count": len(errors)
            },
            db=db
        )

        return {
            "success": True,
            "transferred": transferred,
            "merged": merged,
            "total_findings": len(findings_to_process),
            "archived": archive_result.get("archived_count", 0),
            "errors": errors if errors else None
        }

    def _archive_and_clear(
        self,
        db: Session,
        project: Project,
        findings: List[Dict],
        source_type: str,
        scan_result: Dict
    ) -> Dict:
        """
        آرشیو کردن یافته‌ها بعد از انتقال و پاک کردن نتایج اصلی

        Args:
            db: Session دیتابیس
            project: پروژه
            findings: لیست یافته‌ها
            source_type: نوع منبع (security_scan, test_coverage)
            scan_result: نتایج اسکن اصلی

        Returns:
            {"archived_count": int, "cleared": bool}
        """
        import uuid

        try:
            # دریافت آرشیو موجود
            general_archive = []
            if project.general_archive:
                try:
                    general_archive = json.loads(project.general_archive) if isinstance(project.general_archive, str) else project.general_archive
                except:
                    general_archive = []

            archive_timestamp = datetime.utcnow().isoformat()
            archived_count = 0

            # آرشیو کردن هر یافته
            for finding in findings:
                archive_item = {
                    "id": str(uuid.uuid4()),
                    "type": source_type,
                    "category": finding.get("type", "unknown"),
                    "title": finding.get("title", "یافته"),
                    "content": finding.get("data", {}),
                    "summary": finding.get("title", ""),
                    "archived_at": archive_timestamp,
                    "archived_reason": "transferred_to_issues",
                    "archived_by": "system",
                    "metadata": {
                        "original_created_at": archive_timestamp,
                        "source": source_type,
                        "transfer_status": "completed"
                    }
                }
                general_archive.append(archive_item)
                archived_count += 1

            # آرشیو کردن نتیجه کلی اسکن
            summary_archive = {
                "id": str(uuid.uuid4()),
                "type": f"{source_type}_full_report",
                "category": "full_report",
                "title": f"گزارش کامل {source_type}",
                "content": scan_result,
                "summary": f"گزارش کامل منتقل شده در {archive_timestamp}",
                "archived_at": archive_timestamp,
                "archived_reason": "transferred_to_issues",
                "archived_by": "system",
                "metadata": {
                    "original_created_at": archive_timestamp,
                    "source": source_type,
                    "findings_count": len(findings)
                }
            }
            general_archive.append(summary_archive)

            # ذخیره آرشیو
            project.general_archive = json.dumps(general_archive, ensure_ascii=False)

            # نتایج را پاک نمی‌کنیم - فقط علامت‌گذاری می‌کنیم که انتقال شده
            # این به کاربر اجازه می‌دهد بدون اسکن مجدد، دوباره انتقال کند
            # if source_type == "security_scan":
            #     project.security_scan_result = None
            # elif source_type == "test_coverage":
            #     project.test_coverage_result = None

            db.commit()

            slog.info(f"Archived {archived_count} findings and cleared original results",
                project_id=project.id,
                source_type=source_type
            )

            return {
                "archived_count": archived_count + 1,  # +1 برای گزارش کامل
                "cleared": True
            }

        except Exception as e:
            slog.error("Error archiving findings", exception=e)
            return {
                "archived_count": 0,
                "cleared": False,
                "error": str(e)
            }


# Singleton instance
_health_to_issues_service = None

def get_health_to_issues_service() -> HealthToIssuesService:
    """دریافت instance سرویس"""
    global _health_to_issues_service
    if _health_to_issues_service is None:
        _health_to_issues_service = HealthToIssuesService()
    return _health_to_issues_service
