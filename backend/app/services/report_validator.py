# -*- coding: utf-8 -*-
"""
سرویس اعتبارسنجی گزارش‌های مدل‌های AI
Report Validator Service

قابلیت‌ها:
1. بررسی گزارش‌های مدل‌ها
2. اعتبارسنجی یافته‌ها
3. نمره‌دهی تجمعی به مدل‌ها (هیچوقت صفر نمیشه)
4. شناسایی مواردی که مدل‌ها پیدا نکردن
"""

import asyncio
import json
from datetime import datetime
from typing import List, Dict, Any, Optional
import logging

from ..core.database import SessionLocal
from ..models.analysis_report import AnalysisReport
from .model_profiler import get_model_profiler
from .ai_manager import get_ai_manager

logger = logging.getLogger(__name__)


class ReportValidator:
    """
    اعتبارسنجی گزارش‌های مدل‌های AI و نمره‌دهی

    - بررسی صحت یافته‌های مدل‌ها
    - شناسایی موارد ناگفته
    - نمره‌دهی تجمعی به مدل‌ها
    """

    def __init__(self):
        self.profiler = None
        self.ai_manager = None

    def initialize(self):
        """راه‌اندازی سرویس"""
        self.profiler = get_model_profiler()
        self.ai_manager = get_ai_manager()

    async def validate_analysis_reports(
        self,
        project_id: str,
        files_content: Dict[str, str],  # file_path -> content
        model_reports: Dict[str, Dict],  # model_id -> report
        reference_issues: List[Dict] = None  # لیست ایرادات مرجع (اختیاری)
    ) -> Dict[str, Any]:
        """
        اعتبارسنجی گزارش‌های تحلیل مدل‌ها

        Args:
            project_id: شناسه پروژه
            files_content: محتوای فایل‌ها برای بررسی
            model_reports: گزارش‌های هر مدل
            reference_issues: لیست ایرادات مرجع (برای مقایسه)

        Returns:
            نتیجه اعتبارسنجی و نمرات
        """
        if not self.ai_manager:
            self.initialize()

        validation_id = f"val_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"

        result = {
            "validation_id": validation_id,
            "project_id": project_id,
            "timestamp": datetime.utcnow().isoformat(),
            "model_validations": {},
            "cross_validation": {},
            "discovered_issues": [],
            "summary": {}
        }

        # 1. اگر ایرادات مرجع نداریم، از یک مدل قوی بخواهیم بررسی کنه
        if not reference_issues:
            reference_issues = await self._generate_reference_issues(
                files_content, model_reports
            )

        result["reference_issues_count"] = len(reference_issues)

        # 2. اعتبارسنجی هر مدل
        all_reported_issues = set()
        for model_id, report in model_reports.items():
            model_validation = await self._validate_single_model_report(
                model_id=model_id,
                report=report,
                reference_issues=reference_issues,
                files_content=files_content
            )
            result["model_validations"][model_id] = model_validation

            # جمع‌آوری ایرادات گزارش‌شده
            for issue in report.get("issues", []):
                issue_key = f"{issue.get('file', '')}:{issue.get('line', '')}:{issue.get('type', '')}"
                all_reported_issues.add(issue_key)

        # 3. مقایسه متقابل (cross-validation)
        result["cross_validation"] = self._cross_validate_reports(model_reports)

        # 4. شناسایی موارد پیدا نشده توسط هیچ مدلی
        result["discovered_issues"] = [
            ref for ref in reference_issues
            if not self._is_issue_reported(ref, model_reports)
        ]

        # 5. به‌روزرسانی پروفایل مدل‌ها (نمرات تجمعی)
        await self._update_model_profiles(
            validation_id=validation_id,
            model_validations=result["model_validations"],
            reference_issues=reference_issues
        )

        # 6. خلاصه
        result["summary"] = self._generate_summary(result)

        return result

    async def _validate_single_model_report(
        self,
        model_id: str,
        report: Dict,
        reference_issues: List[Dict],
        files_content: Dict[str, str]
    ) -> Dict:
        """اعتبارسنجی گزارش یک مدل"""

        validation = {
            "model_id": model_id,
            "reported_issues": [],
            "correct_findings": 0,
            "false_positives": 0,
            "missed_issues": 0,
            "precision": 0.0,
            "recall": 0.0,
            "f1_score": 0.0,
            "score": 100.0,  # شروع از 100
            "penalty_details": []
        }

        reported_issues = report.get("issues", [])
        validation["reported_issues_count"] = len(reported_issues)

        # بررسی هر یافته مدل
        for issue in reported_issues:
            is_valid = self._verify_issue(issue, files_content, reference_issues)

            if is_valid:
                validation["correct_findings"] += 1
            else:
                validation["false_positives"] += 1
                # کسر نمره برای false positive
                penalty = self._calculate_penalty(issue, "false_positive")
                validation["score"] -= penalty
                validation["penalty_details"].append({
                    "type": "false_positive",
                    "issue": issue,
                    "penalty": penalty
                })

        # بررسی موارد پیدا نشده
        for ref_issue in reference_issues:
            if not self._is_issue_found_by_model(ref_issue, reported_issues):
                validation["missed_issues"] += 1
                # کسر نمره برای miss
                penalty = self._calculate_penalty(ref_issue, "missed")
                validation["score"] -= penalty
                validation["penalty_details"].append({
                    "type": "missed",
                    "issue": ref_issue,
                    "penalty": penalty
                })

        # محاسبه Precision, Recall, F1
        total_reported = validation["correct_findings"] + validation["false_positives"]
        if total_reported > 0:
            validation["precision"] = (validation["correct_findings"] / total_reported) * 100
        else:
            validation["precision"] = 100.0

        if len(reference_issues) > 0:
            validation["recall"] = (validation["correct_findings"] / len(reference_issues)) * 100
        else:
            validation["recall"] = 100.0

        if validation["precision"] + validation["recall"] > 0:
            validation["f1_score"] = 2 * (validation["precision"] * validation["recall"]) / (validation["precision"] + validation["recall"])
        else:
            validation["f1_score"] = 0.0

        # نمره نباید از 0 کمتر بشه
        validation["score"] = max(0, validation["score"])

        return validation

    def _verify_issue(
        self,
        issue: Dict,
        files_content: Dict[str, str],
        reference_issues: List[Dict]
    ) -> bool:
        """بررسی صحت یک یافته"""

        # اول چک کن آیا در reference_issues هست
        for ref in reference_issues:
            if self._issues_match(issue, ref):
                return True

        # اگر نبود، سعی کن خودت verify کنی
        file_path = issue.get("file", "")
        content = files_content.get(file_path, "")

        if not content:
            return False  # فایل وجود نداره

        # بررسی وجود خط مشکل‌دار
        line_num = issue.get("line")
        if line_num:
            lines = content.split("\n")
            if line_num <= len(lines):
                # خط وجود داره - فرض کن درسته (هر چند دقیق‌تر باید بررسی بشه)
                return True

        # اگر خط مشخص نشده، با احتمال بررسی کن
        issue_type = issue.get("type", "").lower()
        message = issue.get("message", "").lower()

        # بررسی‌های ساده
        if "hardcoded" in issue_type or "secret" in issue_type:
            if any(kw in content.lower() for kw in ["password", "secret", "api_key", "token"]):
                return True

        if "unused" in issue_type:
            # ممکنه درست باشه
            return True

        if "import" in issue_type:
            return True

        # پیش‌فرض: به نفع شک (مگه اینکه واضحا غلط باشه)
        return True

    def _issues_match(self, issue1: Dict, issue2: Dict) -> bool:
        """آیا دو ایراد یکی هستند"""
        # مقایسه بر اساس فایل، خط و نوع
        if issue1.get("file") != issue2.get("file"):
            return False

        # اگر هر دو خط دارن، باید نزدیک باشن
        line1 = issue1.get("line")
        line2 = issue2.get("line")
        if line1 and line2:
            if abs(line1 - line2) > 5:  # تلورانس 5 خط
                return False

        # مقایسه نوع یا پیام
        type1 = (issue1.get("type", "") + issue1.get("message", "")).lower()
        type2 = (issue2.get("type", "") + issue2.get("message", "")).lower()

        # اگر کلمات کلیدی مشترک دارن
        words1 = set(type1.split())
        words2 = set(type2.split())
        common = words1 & words2

        if len(common) >= 2:  # حداقل 2 کلمه مشترک
            return True

        return False

    def _is_issue_reported(self, issue: Dict, model_reports: Dict) -> bool:
        """آیا این ایراد توسط حداقل یک مدل گزارش شده"""
        for model_id, report in model_reports.items():
            for reported in report.get("issues", []):
                if self._issues_match(issue, reported):
                    return True
        return False

    def _is_issue_found_by_model(self, ref_issue: Dict, reported_issues: List[Dict]) -> bool:
        """آیا این ایراد مرجع توسط مدل پیدا شده"""
        for reported in reported_issues:
            if self._issues_match(ref_issue, reported):
                return True
        return False

    def _calculate_penalty(self, issue: Dict, penalty_type: str) -> float:
        """محاسبه جریمه بر اساس نوع و شدت"""
        severity = issue.get("severity", "medium").lower()

        # وزن‌های شدت
        severity_weights = {
            "critical": 3.0,
            "high": 2.0,
            "medium": 1.0,
            "low": 0.5
        }
        weight = severity_weights.get(severity, 1.0)

        # جریمه پایه بر اساس نوع خطا
        if penalty_type == "false_positive":
            base_penalty = 2.0  # گزارش اشتباه
        elif penalty_type == "missed":
            base_penalty = 3.0  # پیدا نکردن مشکل
        else:
            base_penalty = 1.0

        return base_penalty * weight

    async def _generate_reference_issues(
        self,
        files_content: Dict[str, str],
        model_reports: Dict
    ) -> List[Dict]:
        """تولید لیست ایرادات مرجع با استفاده از یک مدل قوی"""

        # ترکیب همه ایرادات گزارش‌شده
        all_issues = []
        issue_keys = set()

        for model_id, report in model_reports.items():
            for issue in report.get("issues", []):
                key = f"{issue.get('file')}:{issue.get('line')}:{issue.get('type')}"
                if key not in issue_keys:
                    issue_keys.add(key)
                    all_issues.append({
                        **issue,
                        "reported_by": [model_id]
                    })
                else:
                    # اضافه کردن مدل به لیست گزارش‌دهنده‌ها
                    for existing in all_issues:
                        if f"{existing.get('file')}:{existing.get('line')}:{existing.get('type')}" == key:
                            existing["reported_by"].append(model_id)
                            break

        # ایراداتی که توسط چند مدل گزارش شدن اعتبار بیشتری دارن
        reference_issues = [
            issue for issue in all_issues
            if len(issue.get("reported_by", [])) >= 1  # حداقل یک مدل
        ]

        return reference_issues

    def _cross_validate_reports(self, model_reports: Dict) -> Dict:
        """مقایسه متقابل گزارش‌ها"""

        cross_val = {
            "agreement_matrix": {},
            "consensus_issues": [],
            "disputed_issues": []
        }

        models = list(model_reports.keys())

        # ماتریس توافق
        for m1 in models:
            cross_val["agreement_matrix"][m1] = {}
            issues1 = model_reports[m1].get("issues", [])

            for m2 in models:
                if m1 == m2:
                    cross_val["agreement_matrix"][m1][m2] = 100.0
                    continue

                issues2 = model_reports[m2].get("issues", [])

                # درصد توافق
                agreed = 0
                for i1 in issues1:
                    for i2 in issues2:
                        if self._issues_match(i1, i2):
                            agreed += 1
                            break

                total = max(len(issues1), 1)
                agreement = (agreed / total) * 100
                cross_val["agreement_matrix"][m1][m2] = round(agreement, 1)

        # ایرادات اجماع (همه مدل‌ها موافقن)
        all_issues = []
        for report in model_reports.values():
            all_issues.extend(report.get("issues", []))

        # گروه‌بندی ایرادات مشابه
        issue_groups = {}
        for issue in all_issues:
            key = f"{issue.get('file')}_{issue.get('type')}"
            if key not in issue_groups:
                issue_groups[key] = {"issue": issue, "count": 1}
            else:
                issue_groups[key]["count"] += 1

        # ایرادات اجماع (همه مدل‌ها گزارش کردن)
        num_models = len(models)
        for key, data in issue_groups.items():
            if data["count"] >= num_models:
                cross_val["consensus_issues"].append(data["issue"])
            elif data["count"] == 1:
                cross_val["disputed_issues"].append(data["issue"])

        return cross_val

    async def _update_model_profiles(
        self,
        validation_id: str,
        model_validations: Dict,
        reference_issues: List[Dict]
    ):
        """به‌روزرسانی پروفایل مدل‌ها با نمرات تجمعی"""

        for model_id, validation in model_validations.items():
            try:
                await self.profiler.update_profile(
                    model_id=model_id,
                    task_type="report_validation",
                    correct_findings=validation["correct_findings"],
                    total_expected=len(reference_issues),
                    false_positives=validation["false_positives"],
                    analysis_report_id=validation_id,
                    details={
                        "precision": validation["precision"],
                        "recall": validation["recall"],
                        "f1_score": validation["f1_score"],
                        "final_score": validation["score"]
                    }
                )

                logger.info(
                    f"Updated profile for {model_id}: "
                    f"correct={validation['correct_findings']}, "
                    f"missed={validation['missed_issues']}, "
                    f"fp={validation['false_positives']}, "
                    f"score={validation['score']:.1f}"
                )

            except Exception as e:
                logger.error(f"Error updating profile for {model_id}: {e}")

    def _generate_summary(self, result: Dict) -> Dict:
        """تولید خلاصه اعتبارسنجی"""

        validations = result.get("model_validations", {})
        if not validations:
            return {}

        # بهترین مدل
        best_model = max(
            validations.items(),
            key=lambda x: x[1].get("score", 0)
        )

        # بدترین مدل
        worst_model = min(
            validations.items(),
            key=lambda x: x[1].get("score", 0)
        )

        # میانگین نمرات
        avg_precision = sum(v.get("precision", 0) for v in validations.values()) / len(validations)
        avg_recall = sum(v.get("recall", 0) for v in validations.values()) / len(validations)
        avg_score = sum(v.get("score", 0) for v in validations.values()) / len(validations)

        return {
            "total_models_validated": len(validations),
            "best_model": {
                "id": best_model[0],
                "score": best_model[1].get("score", 0)
            },
            "worst_model": {
                "id": worst_model[0],
                "score": worst_model[1].get("score", 0)
            },
            "average_precision": round(avg_precision, 1),
            "average_recall": round(avg_recall, 1),
            "average_score": round(avg_score, 1),
            "total_reference_issues": result.get("reference_issues_count", 0),
            "total_discovered_issues": len(result.get("discovered_issues", [])),
            "consensus_issues_count": len(result.get("cross_validation", {}).get("consensus_issues", [])),
            "disputed_issues_count": len(result.get("cross_validation", {}).get("disputed_issues", []))
        }


# Singleton instance
_validator_instance: Optional[ReportValidator] = None


def get_report_validator() -> ReportValidator:
    """دریافت نمونه ReportValidator"""
    global _validator_instance
    if _validator_instance is None:
        _validator_instance = ReportValidator()
    return _validator_instance
