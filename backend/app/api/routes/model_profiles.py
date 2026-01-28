# -*- coding: utf-8 -*-
"""
API Routes برای پروفایل مدل‌های AI
Model Profiles API

شامل:
1. لیست پروفایل مدل‌ها با نمرات تجمعی
2. جزئیات پروفایل هر مدل
3. تاریخچه عملکرد
4. رتبه‌بندی مدل‌ها
"""

import json
import logging
from datetime import datetime, timedelta
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel

logger = logging.getLogger(__name__)

# Defensive imports
try:
    from ...core.database import get_db
    DB_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Could not import database: {e}")
    DB_AVAILABLE = False
    def get_db():
        return None

try:
    from ...models.ai_profile import AIProfile, ModelValidationRecord
    MODELS_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Could not import ai_profile models: {e}")
    MODELS_AVAILABLE = False
    AIProfile = None
    ModelValidationRecord = None

try:
    from ...services.model_profiler import get_model_profiler
    PROFILER_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Could not import model_profiler: {e}")
    PROFILER_AVAILABLE = False
    def get_model_profiler():
        return None

router = APIRouter(prefix="/api/models", tags=["model-profiles"])


# =====================================
# Pydantic Models
# =====================================

class ProfileSummary(BaseModel):
    """خلاصه پروفایل مدل"""
    model_id: str
    provider: str
    display_name: Optional[str] = None
    overall_score: float
    tier: str
    rank: int
    total_analyses: int
    total_tasks: int


class ProfileDetail(BaseModel):
    """جزئیات کامل پروفایل"""
    model_id: str
    provider: str
    display_name: Optional[str] = None

    # نمرات
    accuracy_score: float
    completeness_score: float
    speed_score: float
    reliability_score: float
    code_quality_score: float
    reasoning_score: float
    overall_score: float

    # آمار
    total_analyses: int
    total_tasks: int
    total_debates: int
    total_correct_findings: int
    total_missed_issues: int
    total_false_positives: int

    # رتبه
    rank: int
    tier: str

    # عملکرد
    avg_response_time: float
    total_tokens_used: int
    total_cost: float

    # قابلیت‌ها
    proven_strengths: List[str]
    proven_weaknesses: List[str]

    # زمان
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    last_activity: Optional[datetime] = None


class ValidationHistory(BaseModel):
    """تاریخچه اعتبارسنجی"""
    id: int
    model_id: str
    task_type: str
    precision: float
    recall: float
    f1_score: float
    correct_findings: int
    missed_issues: int
    false_positives: int
    response_time: float
    created_at: datetime


# =====================================
# API Endpoints
# =====================================

@router.get("/health")
async def health_check():
    """Health check endpoint برای تست اینکه router درست لود شده"""
    return {
        "success": True,
        "status": "ok",
        "db_available": DB_AVAILABLE,
        "models_available": MODELS_AVAILABLE,
        "profiler_available": PROFILER_AVAILABLE
    }


@router.get("/profiles")
async def get_all_profiles(
    sort_by: str = Query("overall_score", description="فیلد مرتب‌سازی"),
    order: str = Query("desc", description="ترتیب: asc یا desc"),
    limit: int = Query(50, description="تعداد نتایج"),
    db=Depends(get_db)
):
    """
    دریافت لیست پروفایل همه مدل‌ها

    مرتب‌شده بر اساس نمره کلی (پیش‌فرض)
    شامل رتبه‌بندی و Tier هر مدل
    """
    # اگر دیتابیس در دسترس نیست، داده‌های پیش‌فرض برگردان
    if not DB_AVAILABLE or not MODELS_AVAILABLE or db is None:
        return {
            "success": True,
            "profiles": _get_default_profile_list(),
            "total": 0,
            "note": "Using default profiles - database not available"
        }

    try:
        # دریافت پروفایل‌ها از دیتابیس
        query = db.query(AIProfile)

        # مرتب‌سازی
        sort_field = getattr(AIProfile, sort_by, AIProfile.overall_score)
        if order == "desc":
            query = query.order_by(sort_field.desc())
        else:
            query = query.order_by(sort_field.asc())

        profiles = query.limit(limit).all()

        # اگر پروفایلی نیست، پروفایل‌های پیش‌فرض بساز
        if not profiles:
            profiles = await _create_default_profiles(db)

        # تبدیل به فرمت خروجی
        result = []
        for i, profile in enumerate(profiles, 1):
            result.append({
                "model_id": profile.model_id,
                "provider": profile.provider,
                "display_name": profile.display_name or profile.model_id,
                "overall_score": round(profile.overall_score, 1),
                "accuracy_score": round(profile.accuracy_score, 1),
                "completeness_score": round(profile.completeness_score, 1),
                "speed_score": round(profile.speed_score, 1),
                "reliability_score": round(profile.reliability_score, 1),
                "tier": profile.tier,
                "rank": i,
                "total_analyses": profile.total_analyses,
                "total_tasks": profile.total_tasks,
                "avg_response_time": round(profile.avg_response_time, 2),
                "last_activity": profile.last_activity.isoformat() if profile.last_activity else None
            })

        return {
            "success": True,
            "profiles": result,
            "total": len(result)
        }
    except Exception as e:
        logger.error(f"Error getting profiles: {e}")
        return {
            "success": True,
            "profiles": _get_default_profile_list(),
            "total": 0,
            "note": f"Error: {str(e)}"
        }


@router.get("/profiles/{model_id}")
async def get_profile_detail(model_id: str, db=Depends(get_db)):
    """
    دریافت جزئیات کامل پروفایل یک مدل

    شامل:
    - همه نمرات
    - آمار عملکرد
    - نقاط قوت و ضعف
    - تاریخچه فعالیت
    """
    profile = db.query(AIProfile).filter(AIProfile.model_id == model_id).first()

    if not profile:
        # ایجاد پروفایل جدید
        profile = await _create_profile_for_model(model_id, db)
        if not profile:
            raise HTTPException(status_code=404, detail="مدل یافت نشد")

    # دریافت تاریخچه نمرات
    score_history = []
    try:
        if profile.score_history:
            score_history = json.loads(profile.score_history) if isinstance(profile.score_history, str) else profile.score_history
    except:
        pass

    # دریافت آخرین اعتبارسنجی‌ها
    recent_validations = db.query(ModelValidationRecord).filter(
        ModelValidationRecord.model_id == model_id
    ).order_by(ModelValidationRecord.created_at.desc()).limit(20).all()

    validation_history = [{
        "id": v.id,
        "task_type": v.task_type,
        "precision": round(v.precision, 1),
        "recall": round(v.recall, 1),
        "f1_score": round(v.f1_score, 1),
        "correct_findings": v.correct_findings,
        "missed_issues": v.missed_issues,
        "false_positives": v.false_positives,
        "response_time": round(v.response_time, 2),
        "created_at": v.created_at.isoformat() if v.created_at else None
    } for v in recent_validations]

    # محاسبه رتبه
    rank = db.query(AIProfile).filter(
        AIProfile.overall_score > profile.overall_score
    ).count() + 1

    return {
        "success": True,
        "profile": {
            "model_id": profile.model_id,
            "provider": profile.provider,
            "display_name": profile.display_name or profile.model_id,

            "scores": {
                "overall": round(profile.overall_score, 1),
                "accuracy": round(profile.accuracy_score, 1),
                "completeness": round(profile.completeness_score, 1),
                "speed": round(profile.speed_score, 1),
                "reliability": round(profile.reliability_score, 1),
                "code_quality": round(profile.code_quality_score, 1),
                "reasoning": round(profile.reasoning_score, 1),
            },

            "stats": {
                "total_analyses": profile.total_analyses,
                "total_tasks": profile.total_tasks,
                "total_debates": profile.total_debates,
                "correct_findings": profile.total_correct_findings,
                "missed_issues": profile.total_missed_issues,
                "false_positives": profile.total_false_positives,
            },

            "performance": {
                "avg_response_time": round(profile.avg_response_time, 2),
                "total_tokens_used": profile.total_tokens_used,
                "total_cost": round(profile.total_cost, 4),
            },

            "ranking": {
                "rank": rank,
                "tier": profile.tier,
            },

            "capabilities": {
                "strengths": profile.proven_strengths or [],
                "weaknesses": profile.proven_weaknesses or [],
            },

            "timestamps": {
                "created_at": profile.created_at.isoformat() if profile.created_at else None,
                "updated_at": profile.updated_at.isoformat() if profile.updated_at else None,
                "last_activity": profile.last_activity.isoformat() if profile.last_activity else None,
            },

            "score_history": score_history[-30:],  # آخرین 30 تا
            "validation_history": validation_history,
            "notes": profile.notes
        }
    }


@router.get("/profiles/{model_id}/history")
async def get_profile_history(
    model_id: str,
    days: int = Query(30, description="تعداد روز"),
    db=Depends(get_db)
):
    """
    دریافت تاریخچه عملکرد یک مدل

    برای نمودار روند نمرات
    """
    since = datetime.utcnow() - timedelta(days=days)

    validations = db.query(ModelValidationRecord).filter(
        ModelValidationRecord.model_id == model_id,
        ModelValidationRecord.created_at >= since
    ).order_by(ModelValidationRecord.created_at.asc()).all()

    history = [{
        "date": v.created_at.isoformat() if v.created_at else None,
        "task_type": v.task_type,
        "precision": round(v.precision, 1),
        "recall": round(v.recall, 1),
        "f1_score": round(v.f1_score, 1),
        "response_time": round(v.response_time, 2)
    } for v in validations]

    return {
        "success": True,
        "model_id": model_id,
        "period_days": days,
        "history": history,
        "total_records": len(history)
    }


@router.get("/rankings")
async def get_model_rankings(
    task_type: str = Query(None, description="فیلتر بر اساس نوع کار"),
    db=Depends(get_db)
):
    """
    رتبه‌بندی مدل‌ها

    بر اساس نمره کلی یا نوع کار خاص
    """
    # اگر دیتابیس در دسترس نیست
    if not DB_AVAILABLE or not MODELS_AVAILABLE or db is None:
        default_profiles = _get_default_profile_list()
        rankings = [{
            "rank": p["rank"],
            "model_id": p["model_id"],
            "provider": p["provider"],
            "display_name": p["display_name"],
            "overall_score": p["overall_score"],
            "tier": p["tier"],
            "total_tasks": p["total_tasks"],
            "accuracy": p["accuracy_score"],
            "speed": p["speed_score"],
        } for p in default_profiles]
        return {"success": True, "rankings": rankings, "total": len(rankings), "task_type_filter": task_type}

    try:
        query = db.query(AIProfile).filter(AIProfile.total_tasks > 0)

        # مرتب‌سازی بر اساس نمره
        profiles = query.order_by(AIProfile.overall_score.desc()).all()

        rankings = []
        for i, profile in enumerate(profiles, 1):
            tier = _calculate_tier(profile.overall_score)

            rankings.append({
                "rank": i,
                "model_id": profile.model_id,
                "provider": profile.provider,
                "display_name": profile.display_name or profile.model_id,
                "overall_score": round(profile.overall_score, 1),
                "tier": tier,
                "total_tasks": profile.total_tasks,
                "accuracy": round(profile.accuracy_score, 1),
                "speed": round(profile.speed_score, 1),
            })

        # اگر خالی است، پیش‌فرض برگردان
        if not rankings:
            default_profiles = _get_default_profile_list()
            rankings = [{
                "rank": p["rank"],
                "model_id": p["model_id"],
                "provider": p["provider"],
                "display_name": p["display_name"],
                "overall_score": p["overall_score"],
                "tier": p["tier"],
                "total_tasks": p["total_tasks"],
                "accuracy": p["accuracy_score"],
                "speed": p["speed_score"],
            } for p in default_profiles]

        return {
            "success": True,
            "rankings": rankings,
            "total": len(rankings),
            "task_type_filter": task_type
        }
    except Exception as e:
        logger.error(f"Error getting rankings: {e}")
        default_profiles = _get_default_profile_list()
        rankings = [{
            "rank": p["rank"],
            "model_id": p["model_id"],
            "provider": p["provider"],
            "display_name": p["display_name"],
            "overall_score": p["overall_score"],
            "tier": p["tier"],
            "total_tasks": p["total_tasks"],
            "accuracy": p["accuracy_score"],
            "speed": p["speed_score"],
        } for p in default_profiles]
        return {"success": True, "rankings": rankings, "total": len(rankings), "task_type_filter": task_type}


@router.get("/leaderboard")
async def get_leaderboard(db=Depends(get_db)):
    """
    لیدربورد مدل‌ها

    نمایش بهترین مدل‌ها در هر دسته
    """
    # اگر دیتابیس در دسترس نیست
    if not DB_AVAILABLE or not MODELS_AVAILABLE or db is None:
        return {"success": True, "leaderboard": _get_default_leaderboard()}

    try:
        # بهترین در هر فاکتور
        categories = {
            "best_accuracy": {"field": "accuracy_score", "label": "دقیق‌ترین"},
            "best_speed": {"field": "speed_score", "label": "سریع‌ترین"},
            "best_reliability": {"field": "reliability_score", "label": "قابل‌اعتمادترین"},
            "best_code_quality": {"field": "code_quality_score", "label": "بهترین کیفیت کد"},
            "most_active": {"field": "total_tasks", "label": "فعال‌ترین"},
        }

        leaderboard = {}

        for cat_id, cat_info in categories.items():
            field = getattr(AIProfile, cat_info["field"])
            top = db.query(AIProfile).filter(
                AIProfile.total_tasks > 0
            ).order_by(field.desc()).first()

            if top:
                leaderboard[cat_id] = {
                    "label": cat_info["label"],
                    "model_id": top.model_id,
                    "display_name": top.display_name or top.model_id,
                    "score": round(getattr(top, cat_info["field"]), 1),
                    "tier": top.tier
                }

        # اگر خالی است، پیش‌فرض برگردان
        if not leaderboard:
            leaderboard = _get_default_leaderboard()

        return {
            "success": True,
            "leaderboard": leaderboard
        }
    except Exception as e:
        logger.error(f"Error getting leaderboard: {e}")
        return {"success": True, "leaderboard": _get_default_leaderboard()}


@router.post("/profiles/{model_id}/update-score")
async def manual_update_score(
    model_id: str,
    task_type: str = "manual",
    correct_findings: int = 0,
    missed_issues: int = 0,
    false_positives: int = 0,
    response_time: float = 0,
    db=Depends(get_db)
):
    """
    به‌روزرسانی دستی نمره یک مدل

    برای ثبت نتایج اعتبارسنجی
    """
    profiler = get_model_profiler()

    result = await profiler.update_profile(
        model_id=model_id,
        task_type=task_type,
        correct_findings=correct_findings,
        total_expected=correct_findings + missed_issues,
        false_positives=false_positives,
        response_time=response_time,
        db_session=db
    )

    return {
        "success": True,
        "model_id": model_id,
        "new_scores": result
    }


# =====================================
# Helper Functions
# =====================================

def _calculate_tier(score: float) -> str:
    """محاسبه Tier بر اساس نمره"""
    if score >= 95:
        return "S"
    elif score >= 85:
        return "A"
    elif score >= 75:
        return "B"
    elif score >= 65:
        return "C"
    elif score >= 50:
        return "D"
    else:
        return "F"


def _get_default_profile_list() -> List[dict]:
    """لیست پروفایل‌های پیش‌فرض برای زمانی که دیتابیس در دسترس نیست"""
    default_profiles = [
        {"model_id": "gpt-4", "provider": "openai", "display_name": "GPT-4", "tier": "S", "overall_score": 92.5, "accuracy_score": 95, "completeness_score": 90, "speed_score": 88, "reliability_score": 94, "total_analyses": 0, "total_tasks": 0, "avg_response_time": 1200, "last_activity": None, "rank": 1},
        {"model_id": "gpt-4o", "provider": "openai", "display_name": "GPT-4o", "tier": "S", "overall_score": 91.0, "accuracy_score": 93, "completeness_score": 89, "speed_score": 95, "reliability_score": 92, "total_analyses": 0, "total_tasks": 0, "avg_response_time": 800, "last_activity": None, "rank": 2},
        {"model_id": "claude-3-opus", "provider": "anthropic", "display_name": "Claude 3 Opus", "tier": "S", "overall_score": 90.5, "accuracy_score": 94, "completeness_score": 92, "speed_score": 82, "reliability_score": 93, "total_analyses": 0, "total_tasks": 0, "avg_response_time": 1500, "last_activity": None, "rank": 3},
        {"model_id": "gpt-4o-mini", "provider": "openai", "display_name": "GPT-4o Mini", "tier": "A", "overall_score": 85.0, "accuracy_score": 86, "completeness_score": 83, "speed_score": 92, "reliability_score": 88, "total_analyses": 0, "total_tasks": 0, "avg_response_time": 500, "last_activity": None, "rank": 4},
        {"model_id": "claude-3-sonnet", "provider": "anthropic", "display_name": "Claude 3 Sonnet", "tier": "A", "overall_score": 84.0, "accuracy_score": 88, "completeness_score": 85, "speed_score": 80, "reliability_score": 86, "total_analyses": 0, "total_tasks": 0, "avg_response_time": 1000, "last_activity": None, "rank": 5},
        {"model_id": "gpt-4-turbo", "provider": "openai", "display_name": "GPT-4 Turbo", "tier": "A", "overall_score": 83.0, "accuracy_score": 87, "completeness_score": 82, "speed_score": 85, "reliability_score": 84, "total_analyses": 0, "total_tasks": 0, "avg_response_time": 900, "last_activity": None, "rank": 6},
        {"model_id": "deepseek-chat", "provider": "deepseek", "display_name": "DeepSeek Chat", "tier": "B", "overall_score": 78.0, "accuracy_score": 80, "completeness_score": 76, "speed_score": 82, "reliability_score": 78, "total_analyses": 0, "total_tasks": 0, "avg_response_time": 700, "last_activity": None, "rank": 7},
        {"model_id": "gemini-pro", "provider": "google", "display_name": "Gemini Pro", "tier": "B", "overall_score": 76.0, "accuracy_score": 78, "completeness_score": 74, "speed_score": 80, "reliability_score": 76, "total_analyses": 0, "total_tasks": 0, "avg_response_time": 600, "last_activity": None, "rank": 8},
    ]
    return default_profiles


def _get_default_leaderboard() -> dict:
    """لیدربورد پیش‌فرض"""
    return {
        "best_accuracy": {"label": "بهترین دقت", "model_id": "gpt-4", "display_name": "GPT-4", "score": 95, "tier": "S"},
        "best_speed": {"label": "سریع‌ترین", "model_id": "gpt-4o", "display_name": "GPT-4o", "score": 95, "tier": "S"},
        "best_reliability": {"label": "قابل‌اطمینان‌ترین", "model_id": "gpt-4", "display_name": "GPT-4", "score": 94, "tier": "S"},
        "best_code_quality": {"label": "بهترین کیفیت کد", "model_id": "claude-3-opus", "display_name": "Claude 3 Opus", "score": 92, "tier": "S"},
        "most_active": {"label": "فعال‌ترین", "model_id": "gpt-4o-mini", "display_name": "GPT-4o Mini", "score": 0, "tier": "A"},
    }


async def _create_default_profiles(db) -> List[AIProfile]:
    """ایجاد پروفایل‌های پیش‌فرض برای مدل‌های معروف"""
    default_models = [
        {"id": "gpt-4", "provider": "openai", "name": "GPT-4"},
        {"id": "gpt-4-turbo", "provider": "openai", "name": "GPT-4 Turbo"},
        {"id": "gpt-3.5-turbo", "provider": "openai", "name": "GPT-3.5 Turbo"},
        {"id": "claude-3-opus", "provider": "anthropic", "name": "Claude 3 Opus"},
        {"id": "claude-3-sonnet", "provider": "anthropic", "name": "Claude 3 Sonnet"},
        {"id": "gemini-pro", "provider": "google", "name": "Gemini Pro"},
        {"id": "deepseek-chat", "provider": "deepseek", "name": "DeepSeek Chat"},
    ]

    profiles = []
    for model in default_models:
        existing = db.query(AIProfile).filter(AIProfile.model_id == model["id"]).first()
        if not existing:
            profile = AIProfile(
                model_id=model["id"],
                provider=model["provider"],
                display_name=model["name"],
                overall_score=100.0,
                accuracy_score=100.0,
                completeness_score=100.0,
                speed_score=100.0,
                reliability_score=100.0,
                code_quality_score=100.0,
                reasoning_score=100.0,
                tier="unranked",
                rank=0
            )
            db.add(profile)
            profiles.append(profile)

    if profiles:
        db.commit()

    return db.query(AIProfile).order_by(AIProfile.overall_score.desc()).all()


async def _create_profile_for_model(model_id: str, db) -> Optional[AIProfile]:
    """ایجاد پروفایل برای یک مدل جدید"""
    # تشخیص provider از نام مدل
    provider = "unknown"
    if "gpt" in model_id.lower() or "openai" in model_id.lower():
        provider = "openai"
    elif "claude" in model_id.lower():
        provider = "anthropic"
    elif "gemini" in model_id.lower():
        provider = "google"
    elif "deepseek" in model_id.lower():
        provider = "deepseek"

    profile = AIProfile(
        model_id=model_id,
        provider=provider,
        display_name=model_id,
        overall_score=100.0,
        accuracy_score=100.0,
        completeness_score=100.0,
        speed_score=100.0,
        reliability_score=100.0,
        code_quality_score=100.0,
        reasoning_score=100.0,
        tier="unranked",
        rank=0
    )
    db.add(profile)
    db.commit()
    db.refresh(profile)

    return profile
