"""
سرویس پروفایل و اعتبارسنجی مدل‌های AI
Model Profiler Service

نمرات تجمعی و دائمی برای هر مدل AI
"""

from datetime import datetime
from typing import List, Dict, Any, Optional
import logging

from sqlalchemy.orm import Session

from ..core.database import SessionLocal
from ..models.ai_profile import (
    AIProfile, ModelValidationRecord,
    AIProfileSchema, ProfileUpdateRequest
)
from ..core.models_registry import MODEL_REGISTRY, get_model

logger = logging.getLogger(__name__)


class ModelProfiler:
    """
    مدیریت پروفایل و اعتبارسنجی مدل‌های AI

    ویژگی‌ها:
    - نمرات تجمعی (هیچوقت صفر نمی‌شوند)
    - تاریخچه کامل عملکرد
    - رتبه‌بندی مدل‌ها
    """

    def __init__(self):
        self.score_weights = {
            'accuracy': 0.25,
            'completeness': 0.25,
            'speed': 0.15,
            'reliability': 0.20,
            'code_quality': 0.10,
            'reasoning': 0.05
        }

    def get_or_create_profile(self, db: Session, model_id: str) -> AIProfile:
        """دریافت یا ایجاد پروفایل برای یک مدل"""
        profile = db.query(AIProfile).filter(AIProfile.model_id == model_id).first()

        if not profile:
            # ایجاد پروفایل جدید
            model_info = get_model(model_id)
            profile = AIProfile(
                model_id=model_id,
                provider=model_info.provider.value if model_info else "unknown",
                display_name=model_info.name if model_info else model_id,
                score_history=[],
                last_scores_by_task={}
            )
            db.add(profile)
            db.commit()
            db.refresh(profile)
            logger.info(f"Created new profile for model: {model_id}")

        return profile

    async def update_profile(
        self,
        model_id: str,
        task_type: str = "analysis",
        correct_findings: int = 0,
        total_expected: int = 0,
        false_positives: int = 0,
        response_time: float = 0.0,
        tokens_used: int = 0,
        cost: float = 0.0,
        analysis_report_id: str = None,
        details: Dict[str, Any] = None
    ) -> AIProfileSchema:
        """
        به‌روزرسانی پروفایل بر اساس نتایج جدید

        نمرات قبلی حفظ می‌شوند و میانگین متحرک محاسبه می‌شود
        """
        db = SessionLocal()
        try:
            profile = self.get_or_create_profile(db, model_id)

            # محاسبه Precision و Recall
            if total_expected > 0 or correct_findings > 0 or false_positives > 0:
                # Precision: درصد یافته‌های صحیح از کل یافته‌ها
                total_reported = correct_findings + false_positives
                if total_reported > 0:
                    precision = (correct_findings / total_reported) * 100
                else:
                    precision = 100.0

                # Recall: درصد مشکلات شناسایی‌شده از کل مشکلات واقعی
                if total_expected > 0:
                    recall = (correct_findings / total_expected) * 100
                else:
                    recall = 100.0

                # F1 Score
                if precision + recall > 0:
                    f1 = 2 * (precision * recall) / (precision + recall)
                else:
                    f1 = 0
            else:
                precision = recall = f1 = 100.0

            # ذخیره رکورد اعتبارسنجی
            validation = ModelValidationRecord(
                model_id=model_id,
                analysis_report_id=analysis_report_id,
                task_type=task_type,
                precision=precision,
                recall=recall,
                f1_score=f1,
                correct_findings=correct_findings,
                missed_issues=max(0, total_expected - correct_findings),
                false_positives=false_positives,
                response_time=response_time,
                tokens_used=tokens_used,
                cost=cost,
                details=details or {}
            )
            db.add(validation)

            # به‌روزرسانی آمار کلی
            profile.total_analyses += 1
            profile.total_tasks += 1
            profile.total_correct_findings += correct_findings
            profile.total_missed_issues += max(0, total_expected - correct_findings)
            profile.total_false_positives += false_positives
            profile.total_tokens_used += tokens_used
            profile.total_cost += cost

            # میانگین متحرک برای نمرات
            # فرمول: new_avg = old_avg * (n-1)/n + new_value * 1/n
            n = profile.total_analyses
            old_weight = (n - 1) / n if n > 1 else 0
            new_weight = 1 / n

            profile.accuracy_score = profile.accuracy_score * old_weight + precision * new_weight
            profile.completeness_score = profile.completeness_score * old_weight + recall * new_weight

            # نمره سرعت (بر اساس زمان پاسخ)
            # زیر 5 ثانیه = 100، بالای 30 ثانیه = 0
            if response_time > 0:
                speed_score = max(0, min(100, 100 - (response_time - 5) * (100 / 25)))
                profile.speed_score = profile.speed_score * old_weight + speed_score * new_weight

            # میانگین زمان پاسخ
            if response_time > 0:
                profile.avg_response_time = profile.avg_response_time * old_weight + response_time * new_weight

            # محاسبه نمره کلی
            profile.overall_score = (
                profile.accuracy_score * self.score_weights['accuracy'] +
                profile.completeness_score * self.score_weights['completeness'] +
                profile.speed_score * self.score_weights['speed'] +
                profile.reliability_score * self.score_weights['reliability'] +
                profile.code_quality_score * self.score_weights['code_quality'] +
                profile.reasoning_score * self.score_weights['reasoning']
            )

            # به‌روزرسانی tier
            profile.tier = self._calculate_tier(profile.overall_score)

            # ذخیره در تاریخچه
            history_entry = {
                'timestamp': datetime.utcnow().isoformat(),
                'task_type': task_type,
                'scores': {
                    'accuracy': precision,
                    'completeness': recall,
                    'f1': f1,
                    'overall': profile.overall_score
                },
                'details': {
                    'correct': correct_findings,
                    'missed': max(0, total_expected - correct_findings),
                    'false_positives': false_positives,
                    'response_time': response_time
                }
            }

            # اضافه کردن به تاریخچه (حداکثر 1000 ورودی)
            # 🔴 FIX: Ensure score_history is always a list
            history = profile.score_history
            if not isinstance(history, list):
                history = []
            history.append(history_entry)
            if len(history) > 1000:
                history = history[-1000:]
            profile.score_history = history

            # به‌روزرسانی آخرین نمرات هر نوع کار
            # 🔴 FIX: Ensure last_scores_by_task is always a dict
            last_scores = profile.last_scores_by_task
            if not isinstance(last_scores, dict):
                last_scores = {}
            last_scores[task_type] = history_entry['scores']
            profile.last_scores_by_task = last_scores

            profile.last_activity = datetime.utcnow()
            profile.updated_at = datetime.utcnow()

            db.commit()
            db.refresh(profile)

            logger.info(f"Updated profile for {model_id}: overall={profile.overall_score:.1f}, tier={profile.tier}")

            return AIProfileSchema.model_validate(profile)

        except Exception as e:
            db.rollback()
            logger.error(f"Error updating profile for {model_id}: {e}", exc_info=True)
            raise
        finally:
            db.close()

    def _calculate_tier(self, score: float) -> str:
        """محاسبه tier بر اساس نمره"""
        if score >= 95:
            return "S"
        elif score >= 85:
            return "A"
        elif score >= 70:
            return "B"
        elif score >= 55:
            return "C"
        elif score >= 40:
            return "D"
        else:
            return "F"

    def get_profile(self, model_id: str) -> Optional[AIProfileSchema]:
        """دریافت پروفایل یک مدل"""
        db = SessionLocal()
        try:
            profile = db.query(AIProfile).filter(AIProfile.model_id == model_id).first()
            if profile:
                return AIProfileSchema.model_validate(profile)
            return None
        finally:
            db.close()

    def get_all_profiles(self) -> List[AIProfileSchema]:
        """دریافت همه پروفایل‌ها"""
        db = SessionLocal()
        try:
            profiles = db.query(AIProfile).order_by(AIProfile.overall_score.desc()).all()
            return [AIProfileSchema.model_validate(p) for p in profiles]
        finally:
            db.close()

    def get_top_models(self, n: int = 5, task_type: str = None) -> List[AIProfileSchema]:
        """دریافت n مدل برتر"""
        db = SessionLocal()
        try:
            query = db.query(AIProfile)

            if task_type:
                # فیلتر بر اساس نوع کار
                query = query.filter(
                    AIProfile.last_scores_by_task.contains({task_type: {}})
                )

            profiles = query.order_by(AIProfile.overall_score.desc()).limit(n).all()
            return [AIProfileSchema.model_validate(p) for p in profiles]
        finally:
            db.close()

    def update_rankings(self):
        """به‌روزرسانی رتبه‌بندی همه مدل‌ها"""
        db = SessionLocal()
        try:
            profiles = db.query(AIProfile).order_by(AIProfile.overall_score.desc()).all()

            for rank, profile in enumerate(profiles, start=1):
                profile.rank = rank

            db.commit()
            logger.info(f"Updated rankings for {len(profiles)} models")
        finally:
            db.close()

    def get_score_history(
        self,
        model_id: str,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """دریافت تاریخچه نمرات یک مدل"""
        db = SessionLocal()
        try:
            profile = db.query(AIProfile).filter(AIProfile.model_id == model_id).first()
            if profile and profile.score_history:
                return profile.score_history[-limit:]
            return []
        finally:
            db.close()

    def compare_models(
        self,
        model_ids: List[str]
    ) -> Dict[str, Any]:
        """مقایسه چند مدل با هم"""
        db = SessionLocal()
        try:
            profiles = db.query(AIProfile).filter(AIProfile.model_id.in_(model_ids)).all()

            comparison = {
                'models': [],
                'metrics': ['accuracy', 'completeness', 'speed', 'reliability', 'overall'],
                'data': {}
            }

            for profile in profiles:
                comparison['models'].append(profile.model_id)
                comparison['data'][profile.model_id] = {
                    'accuracy': profile.accuracy_score,
                    'completeness': profile.completeness_score,
                    'speed': profile.speed_score,
                    'reliability': profile.reliability_score,
                    'overall': profile.overall_score,
                    'tier': profile.tier,
                    'total_analyses': profile.total_analyses
                }

            return comparison
        finally:
            db.close()

    def initialize_profiles_for_known_models(self):
        """ایجاد پروفایل اولیه برای مدل‌های شناخته‌شده"""
        db = SessionLocal()
        try:
            for model_id, model in MODEL_REGISTRY.items():
                existing = db.query(AIProfile).filter(AIProfile.model_id == model_id).first()
                if not existing:
                    profile = AIProfile(
                        model_id=model_id,
                        provider=model.provider.value,
                        display_name=model.name,
                        score_history=[],
                        last_scores_by_task={},
                        # نمرات اولیه 100
                        accuracy_score=100.0,
                        completeness_score=100.0,
                        speed_score=100.0,
                        reliability_score=100.0,
                        code_quality_score=100.0,
                        reasoning_score=100.0,
                        overall_score=100.0,
                        tier="unranked"
                    )
                    db.add(profile)
                    logger.info(f"Created initial profile for: {model_id}")

            db.commit()
        finally:
            db.close()


# Singleton instance
_profiler_instance: Optional[ModelProfiler] = None


def get_model_profiler() -> ModelProfiler:
    """دریافت نمونه ModelProfiler"""
    global _profiler_instance
    if _profiler_instance is None:
        _profiler_instance = ModelProfiler()
    return _profiler_instance
