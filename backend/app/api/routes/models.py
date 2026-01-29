"""
API routes برای مدیریت مدل‌ها
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/models", tags=["Models"])


# ===========================================
# Response Models
# ===========================================

class ModelInfo(BaseModel):
    """اطلاعات یک مدل"""
    id: str
    provider: str
    name: str
    capabilities: List[str]
    max_tokens: int
    context_window: int
    strengths: List[str]
    weaknesses: List[str]
    cost_per_1k_tokens: float
    priority: int
    enabled: bool
    supports_images: bool
    supports_video: bool
    is_image_generator: bool
    is_available: bool = False


class ProviderStatus(BaseModel):
    """وضعیت یک provider"""
    provider: str
    available: bool
    model_count: int
    models: List[str]


class SmartSelectRequest(BaseModel):
    """درخواست انتخاب هوشمند"""
    prompt: str
    required_capabilities: Optional[List[str]] = None
    max_models: int = 3
    prefer_providers: Optional[List[str]] = None


# ===========================================
# Helper function to safely get provider value
# ===========================================
def get_provider_value(provider) -> str:
    """Safely get provider value as string"""
    if hasattr(provider, 'value'):
        return provider.value
    return str(provider)


def get_capability_value(cap) -> str:
    """Safely get capability value as string"""
    if hasattr(cap, 'value'):
        return cap.value
    return str(cap)


# ===========================================
# Endpoints
# ===========================================

@router.get("", response_model=List[ModelInfo])
@router.get("/", response_model=List[ModelInfo])
async def list_models(provider: Optional[str] = None, capability: Optional[str] = None):
    """لیست همه مدل‌ها"""
    try:
        from ...core.models_registry import MODEL_REGISTRY, ModelCapability
        from ...services.ai_manager import get_ai_manager

        # Get available providers
        available_providers = []
        try:
            ai_manager = get_ai_manager()
            available_providers = ai_manager.get_available_providers()
        except Exception as e:
            logger.warning(f"Could not get AI manager: {e}")

        models = []
        for model in MODEL_REGISTRY.values():
            try:
                model_provider = get_provider_value(model.provider)

                # فیلتر بر اساس provider
                if provider and model_provider != provider:
                    continue

                # فیلتر بر اساس capability
                if capability:
                    model_caps = [get_capability_value(c) for c in model.capabilities]
                    if capability not in model_caps:
                        continue

                is_available = model_provider in available_providers

                models.append(ModelInfo(
                    id=model.id,
                    provider=model_provider,
                    name=model.name,
                    capabilities=[get_capability_value(c) for c in model.capabilities],
                    max_tokens=model.max_tokens,
                    context_window=model.context_window,
                    strengths=model.strengths,
                    weaknesses=model.weaknesses,
                    cost_per_1k_tokens=model.cost_per_1k_tokens,
                    priority=model.priority,
                    enabled=model.enabled,
                    supports_images=model.supports_images,
                    supports_video=model.supports_video,
                    is_image_generator=model.is_image_generator,
                    is_available=is_available,
                ))
            except Exception as e:
                logger.error(f"Error processing model {model.id}: {e}")
                continue

        return models

    except Exception as e:
        logger.error(f"Error in list_models: {e}", exc_info=True)
        return []


@router.get("/providers", response_model=List[ProviderStatus])
async def list_providers():
    """لیست provider ها و وضعیتشان"""
    try:
        # Import inside function to avoid circular imports
        from ...core.models_registry import MODEL_REGISTRY
        from ...services.ai_manager import get_ai_manager

        # Get available providers
        available_providers = []
        try:
            ai_manager = get_ai_manager()
            available_providers = ai_manager.get_available_providers()
        except Exception as e:
            logger.warning(f"Could not get AI manager: {e}")

        # Build provider list
        providers = {}
        for model in MODEL_REGISTRY.values():
            try:
                provider = get_provider_value(model.provider)
                if provider not in providers:
                    providers[provider] = {
                        "provider": provider,
                        "available": provider in available_providers,
                        "models": []
                    }
                providers[provider]["models"].append(model.id)
            except Exception as e:
                logger.error(f"Error processing model: {e}")
                continue

        return [ProviderStatus(
            provider=p["provider"],
            available=p["available"],
            model_count=len(p["models"]),
            models=p["models"]
        ) for p in providers.values()]

    except Exception as e:
        logger.error(f"Error in list_providers: {e}", exc_info=True)
        # Return empty list instead of error
        return []


@router.get("/available", response_model=List[ModelInfo])
async def list_available_models():
    """لیست مدل‌های قابل استفاده (با API key)"""
    try:
        from ...services.ai_manager import get_ai_manager

        ai_manager = get_ai_manager()
        available = ai_manager.get_available_models()

        return [ModelInfo(
            id=m.id,
            provider=get_provider_value(m.provider),
            name=m.name,
            capabilities=[get_capability_value(c) for c in m.capabilities],
            max_tokens=m.max_tokens,
            context_window=m.context_window,
            strengths=m.strengths,
            weaknesses=m.weaknesses,
            cost_per_1k_tokens=m.cost_per_1k_tokens,
            priority=m.priority,
            enabled=m.enabled,
            supports_images=m.supports_images,
            supports_video=m.supports_video,
            is_image_generator=m.is_image_generator,
            is_available=True,
        ) for m in available]

    except Exception as e:
        logger.warning(f"Error in list_available_models: {e}")
        return []


@router.get("/capabilities")
async def get_capabilities():
    """لیست همه قابلیت‌ها"""
    try:
        from ...core.models_registry import ModelCapability
        return [{"id": c.value, "name": c.name} for c in ModelCapability]
    except Exception as e:
        logger.error(f"Error getting capabilities: {e}")
        return []


@router.get("/aliases")
async def get_aliases():
    """لیست alias های مدل‌ها"""
    try:
        from ...core.models_registry import MODEL_ALIASES
        return MODEL_ALIASES
    except Exception as e:
        logger.error(f"Error getting aliases: {e}")
        return {}


# ===========================================
# Model Profiles & Rankings Endpoints
# IMPORTANT: These MUST be before /{model_id} to avoid route conflicts!
# ===========================================

@router.get("/profiles")
async def get_model_profiles():
    """
    دریافت پروفایل همه مدل‌های AI
    نمرات تجمعی از تحلیل‌های قبلی
    """
    try:
        from ...services.model_profiler import get_model_profiler
        profiler = get_model_profiler()
        profiles = profiler.get_all_profiles()
        profiles_data = [p.model_dump() for p in profiles]
        # Return in expected frontend format
        return {
            "success": True,
            "profiles": profiles_data,
            "count": len(profiles_data),
            "is_fallback": len(profiles_data) == 0
        }
    except Exception as e:
        logger.error(f"Error getting profiles: {e}")
        return {"success": False, "profiles": [], "error": str(e)}


@router.get("/leaderboard")
async def get_model_leaderboard():
    """
    لیدربرد مدل‌ها - رتبه‌بندی بر اساس عملکرد
    """
    try:
        from ...services.model_profiler import get_model_profiler
        profiler = get_model_profiler()
        top_models = profiler.get_top_models(n=20)

        # Build leaderboard object in frontend expected format
        leaderboard = {}
        if top_models:
            # Best accuracy
            best_acc = max(top_models, key=lambda p: p.accuracy_score)
            leaderboard["best_accuracy"] = {
                "label": "بهترین دقت",
                "model_id": best_acc.model_id,
                "display_name": best_acc.model_id,
                "score": best_acc.accuracy_score,
                "tier": "S" if best_acc.accuracy_score >= 90 else "A" if best_acc.accuracy_score >= 80 else "B"
            }
            # Best speed (lowest response time)
            profiles_with_time = [p for p in top_models if p.avg_response_time > 0]
            if profiles_with_time:
                best_speed = min(profiles_with_time, key=lambda p: p.avg_response_time)
                leaderboard["best_speed"] = {
                    "label": "سریع‌ترین",
                    "model_id": best_speed.model_id,
                    "display_name": best_speed.model_id,
                    "score": 100 - min(best_speed.avg_response_time / 20, 100),
                    "tier": "S" if best_speed.avg_response_time < 1000 else "A"
                }
            # Best overall
            best_overall = max(top_models, key=lambda p: p.overall_score)
            leaderboard["best_overall"] = {
                "label": "بهترین کلی",
                "model_id": best_overall.model_id,
                "display_name": best_overall.model_id,
                "score": best_overall.overall_score,
                "tier": "S" if best_overall.overall_score >= 90 else "A" if best_overall.overall_score >= 80 else "B"
            }
            # Most active
            most_active = max(top_models, key=lambda p: p.total_analyses)
            leaderboard["most_active"] = {
                "label": "فعال‌ترین",
                "model_id": most_active.model_id,
                "display_name": most_active.model_id,
                "score": most_active.total_analyses,
                "tier": "A"
            }

        return {
            "success": True,
            "leaderboard": leaderboard
        }
    except Exception as e:
        logger.error(f"Error getting leaderboard: {e}")
        return {"success": False, "leaderboard": {}}


@router.get("/rankings")
async def get_model_rankings():
    """
    رتبه‌بندی مدل‌ها بر اساس نوع کار
    """
    try:
        from ...services.model_profiler import get_model_profiler
        from ...core.models_registry import MODEL_REGISTRY

        profiler = get_model_profiler()

        # Get profiles and sort by score
        profiles = profiler.get_all_profiles()
        profiles_dict = {p.model_id: p for p in profiles}

        rankings = {
            "by_score": [],
            "by_accuracy": [],
            "by_speed": [],
            "by_cost_efficiency": []
        }

        # Sort by overall score
        sorted_by_score = sorted(profiles, key=lambda p: p.overall_score, reverse=True)
        for i, p in enumerate(sorted_by_score[:10], 1):
            rankings["by_score"].append({
                "rank": i,
                "model_id": p.model_id,
                "score": p.overall_score
            })

        # Sort by accuracy
        sorted_by_accuracy = sorted(profiles, key=lambda p: p.accuracy_score, reverse=True)
        for i, p in enumerate(sorted_by_accuracy[:10], 1):
            rankings["by_accuracy"].append({
                "rank": i,
                "model_id": p.model_id,
                "accuracy": p.accuracy_score
            })

        # Sort by speed (lower is better)
        profiles_with_time = [p for p in profiles if p.avg_response_time > 0]
        sorted_by_speed = sorted(profiles_with_time, key=lambda p: p.avg_response_time)
        for i, p in enumerate(sorted_by_speed[:10], 1):
            rankings["by_speed"].append({
                "rank": i,
                "model_id": p.model_id,
                "avg_time": p.avg_response_time
            })

        # Add models from registry that don't have profiles yet
        for model_id in MODEL_REGISTRY:
            if model_id not in profiles_dict:
                rankings["by_score"].append({
                    "rank": len(rankings["by_score"]) + 1,
                    "model_id": model_id,
                    "score": 50.0  # Default
                })

        return {
            "success": True,
            "rankings": rankings
        }
    except Exception as e:
        logger.error(f"Error getting rankings: {e}")
        return {"success": False, "rankings": {"by_score": [], "by_accuracy": [], "by_speed": [], "by_cost_efficiency": []}}


# ===========================================
# Dynamic route - MUST be last!
# ===========================================
@router.get("/{model_id}", response_model=ModelInfo)
async def get_model_info(model_id: str):
    """دریافت اطلاعات یک مدل"""
    try:
        from ...core.models_registry import get_model
        from ...services.ai_manager import get_ai_manager

        model = get_model(model_id)
        if not model:
            raise HTTPException(status_code=404, detail="Model not found")

        # Check if available
        is_available = False
        try:
            ai_manager = get_ai_manager()
            is_available = get_provider_value(model.provider) in ai_manager.get_available_providers()
        except Exception:
            pass  # If AI manager not available, mark as unavailable

        return ModelInfo(
            id=model.id,
            provider=get_provider_value(model.provider),
            name=model.name,
            capabilities=[get_capability_value(c) for c in model.capabilities],
            max_tokens=model.max_tokens,
            context_window=model.context_window,
            strengths=model.strengths,
            weaknesses=model.weaknesses,
            cost_per_1k_tokens=model.cost_per_1k_tokens,
            priority=model.priority,
            enabled=model.enabled,
            supports_images=model.supports_images,
            supports_video=model.supports_video,
            is_image_generator=model.is_image_generator,
            is_available=is_available,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting model {model_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/smart-select", response_model=List[ModelInfo])
async def smart_select_models(request: SmartSelectRequest):
    """انتخاب هوشمند مدل‌ها"""
    try:
        from ...services.ai_manager import get_ai_manager
        from ...core.models_registry import ModelCapability, ModelProvider

        ai_manager = get_ai_manager()

        # تبدیل capabilities
        caps = None
        if request.required_capabilities:
            caps = []
            for c in request.required_capabilities:
                try:
                    caps.append(ModelCapability(c))
                except ValueError:
                    pass

        # تبدیل providers
        providers = None
        if request.prefer_providers:
            providers = []
            for p in request.prefer_providers:
                try:
                    providers.append(ModelProvider(p))
                except ValueError:
                    pass

        selected = ai_manager.smart_select_models(
            prompt=request.prompt,
            required_capabilities=caps,
            max_models=request.max_models,
            prefer_providers=providers,
        )

        return [ModelInfo(
            id=m.id,
            provider=get_provider_value(m.provider),
            name=m.name,
            capabilities=[get_capability_value(c) for c in m.capabilities],
            max_tokens=m.max_tokens,
            context_window=m.context_window,
            strengths=m.strengths,
            weaknesses=m.weaknesses,
            cost_per_1k_tokens=m.cost_per_1k_tokens,
            priority=m.priority,
            enabled=m.enabled,
            supports_images=m.supports_images,
            supports_video=m.supports_video,
            is_image_generator=m.is_image_generator,
            is_available=True,
        ) for m in selected]

    except Exception as e:
        logger.error(f"Error in smart_select: {e}")
        return []


# ===========================================
# Model Capability Testing Endpoints
# ===========================================

class CapabilityTestRequest(BaseModel):
    """درخواست تست توانایی"""
    model_id: str
    categories: Optional[List[str]] = None  # خالی = همه


@router.post("/capability-test")
async def test_model_capabilities(request: CapabilityTestRequest):
    """
    تست توانایی‌های یک مدل

    مدل با سوالات استاندارد تست می‌شود و badge می‌گیرد
    """
    try:
        from ...services.ai_manager import get_ai_manager
        from ...services.model_capability_tester import get_capability_tester

        ai_manager = get_ai_manager()
        tester = get_capability_tester(ai_manager)

        results = await tester.test_model(
            model_id=request.model_id,
            categories=request.categories
        )

        return {
            "success": True,
            "results": results
        }

    except Exception as e:
        logger.error(f"Error testing model capabilities: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e)
        }


@router.get("/capability-test/{model_id}")
async def get_model_capabilities(model_id: str):
    """
    دریافت نتایج تست توانایی یک مدل (از cache)
    """
    try:
        from ...services.model_capability_tester import get_capability_tester

        tester = get_capability_tester()
        results = tester.get_cached_results(model_id)

        if results:
            return {
                "success": True,
                "results": results
            }
        else:
            return {
                "success": False,
                "message": "نتایج تست برای این مدل موجود نیست. لطفاً ابتدا تست انجام دهید."
            }

    except Exception as e:
        logger.error(f"Error getting capabilities: {e}")
        return {"success": False, "error": str(e)}


@router.post("/capability-test-all")
async def test_all_models_capabilities():
    """
    تست توانایی همه مدل‌های موجود
    """
    try:
        from ...services.ai_manager import get_ai_manager
        from ...services.model_capability_tester import get_capability_tester

        ai_manager = get_ai_manager()
        tester = get_capability_tester(ai_manager)

        results = await tester.test_all_models()

        return {
            "success": True,
            "tested_models": len(results),
            "results": results
        }

    except Exception as e:
        logger.error(f"Error testing all models: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


@router.get("/badges")
async def get_all_badges():
    """
    دریافت همه badge های تعریف شده
    """
    try:
        from ...services.model_capability_tester import CAPABILITY_BADGES

        return {
            "success": True,
            "badges": [
                {
                    "id": badge_id,
                    "min_score": config["min_score"],
                    "color": config["color"],
                    "label": config["label"],
                    "icon": config["icon"]
                }
                for badge_id, config in CAPABILITY_BADGES.items()
            ]
        }

    except Exception as e:
        logger.error(f"Error getting badges: {e}")
        return {"success": False, "error": str(e)}


# ===========================================
# 🆕 مدیریت تنظیمات مدل‌ها
# ===========================================

from fastapi import Depends
from sqlalchemy.orm import Session
from ...core.database import get_db
from ...models.ai_profile import (
    ModelSettings,
    ModelSettingsSchema,
    ModelSettingsUpdateRequest,
    AVAILABLE_TASK_TYPES
)


@router.get("/settings")
async def get_all_model_settings(db: Session = Depends(get_db)):
    """
    دریافت تنظیمات همه مدل‌ها
    """
    try:
        from ...core.models_registry import MODEL_REGISTRY

        # دریافت تنظیمات از دیتابیس
        db_settings = db.query(ModelSettings).all()
        settings_map = {s.model_id: s for s in db_settings}

        result = []
        for model_id, model in MODEL_REGISTRY.items():
            if model_id in settings_map:
                setting = settings_map[model_id]
                result.append({
                    "model_id": model_id,
                    "model_name": model.name,
                    "provider": get_provider_value(model.provider),
                    "enabled": bool(setting.enabled),
                    "allowed_tasks": setting.allowed_tasks or ["all"],
                    "priority": setting.priority or model.priority,
                    "max_tokens_override": setting.max_tokens_override,
                    "max_daily_requests": setting.max_daily_requests,
                    "current_daily_requests": setting.current_daily_requests,
                    "preferred_for": setting.preferred_for or [],
                    "fallback_model_id": setting.fallback_model_id,
                    "max_daily_cost": setting.max_daily_cost,
                    "current_daily_cost": setting.current_daily_cost,
                    "notes": setting.notes,
                    "advanced_settings": setting.advanced_settings or {},
                    "has_custom_settings": True
                })
            else:
                # مدل بدون تنظیمات سفارشی - استفاده از پیش‌فرض‌ها
                result.append({
                    "model_id": model_id,
                    "model_name": model.name,
                    "provider": get_provider_value(model.provider),
                    "enabled": model.enabled,
                    "allowed_tasks": ["all"],
                    "priority": model.priority,
                    "max_tokens_override": None,
                    "max_daily_requests": 0,
                    "current_daily_requests": 0,
                    "preferred_for": [],
                    "fallback_model_id": None,
                    "max_daily_cost": 0,
                    "current_daily_cost": 0,
                    "notes": None,
                    "advanced_settings": {},
                    "has_custom_settings": False
                })

        return {
            "success": True,
            "settings": result,
            "total": len(result)
        }

    except Exception as e:
        logger.error(f"Error getting model settings: {e}")
        return {"success": False, "error": str(e)}


@router.get("/settings/{model_id}")
async def get_model_settings(model_id: str, db: Session = Depends(get_db)):
    """
    دریافت تنظیمات یک مدل خاص
    """
    try:
        from ...core.models_registry import MODEL_REGISTRY

        if model_id not in MODEL_REGISTRY:
            raise HTTPException(status_code=404, detail="مدل یافت نشد")

        model = MODEL_REGISTRY[model_id]
        setting = db.query(ModelSettings).filter(ModelSettings.model_id == model_id).first()

        if setting:
            return {
                "success": True,
                "model_id": model_id,
                "model_name": model.name,
                "provider": get_provider_value(model.provider),
                "enabled": bool(setting.enabled),
                "allowed_tasks": setting.allowed_tasks or ["all"],
                "priority": setting.priority or model.priority,
                "max_tokens_override": setting.max_tokens_override,
                "max_daily_requests": setting.max_daily_requests,
                "current_daily_requests": setting.current_daily_requests,
                "preferred_for": setting.preferred_for or [],
                "fallback_model_id": setting.fallback_model_id,
                "max_daily_cost": setting.max_daily_cost,
                "current_daily_cost": setting.current_daily_cost,
                "notes": setting.notes,
                "advanced_settings": setting.advanced_settings or {},
                "has_custom_settings": True
            }
        else:
            return {
                "success": True,
                "model_id": model_id,
                "model_name": model.name,
                "provider": get_provider_value(model.provider),
                "enabled": model.enabled,
                "allowed_tasks": ["all"],
                "priority": model.priority,
                "max_tokens_override": None,
                "max_daily_requests": 0,
                "current_daily_requests": 0,
                "preferred_for": [],
                "fallback_model_id": None,
                "max_daily_cost": 0,
                "current_daily_cost": 0,
                "notes": None,
                "advanced_settings": {},
                "has_custom_settings": False
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting model settings: {e}")
        return {"success": False, "error": str(e)}


@router.put("/settings/{model_id}")
async def update_model_settings(
    model_id: str,
    request: ModelSettingsUpdateRequest,
    db: Session = Depends(get_db)
):
    """
    بروزرسانی تنظیمات یک مدل
    """
    try:
        from ...core.models_registry import MODEL_REGISTRY

        if model_id not in MODEL_REGISTRY:
            raise HTTPException(status_code=404, detail="مدل یافت نشد")

        # دریافت یا ایجاد تنظیمات
        setting = db.query(ModelSettings).filter(ModelSettings.model_id == model_id).first()

        if not setting:
            setting = ModelSettings(model_id=model_id)
            db.add(setting)

        # بروزرسانی فیلدها
        if request.enabled is not None:
            setting.enabled = 1 if request.enabled else 0

        if request.allowed_tasks is not None:
            setting.allowed_tasks = request.allowed_tasks

        if request.priority is not None:
            setting.priority = request.priority

        if request.max_tokens_override is not None:
            setting.max_tokens_override = request.max_tokens_override

        if request.max_daily_requests is not None:
            setting.max_daily_requests = request.max_daily_requests

        if request.preferred_for is not None:
            setting.preferred_for = request.preferred_for

        if request.fallback_model_id is not None:
            setting.fallback_model_id = request.fallback_model_id

        if request.max_daily_cost is not None:
            setting.max_daily_cost = request.max_daily_cost

        if request.notes is not None:
            setting.notes = request.notes

        if request.advanced_settings is not None:
            setting.advanced_settings = request.advanced_settings

        db.commit()

        return {
            "success": True,
            "message": "تنظیمات ذخیره شد",
            "model_id": model_id
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating model settings: {e}")
        return {"success": False, "error": str(e)}


@router.post("/settings/{model_id}/toggle")
async def toggle_model_enabled(model_id: str, db: Session = Depends(get_db)):
    """
    تغییر وضعیت فعال/غیرفعال مدل
    """
    try:
        from ...core.models_registry import MODEL_REGISTRY

        if model_id not in MODEL_REGISTRY:
            raise HTTPException(status_code=404, detail="مدل یافت نشد")

        setting = db.query(ModelSettings).filter(ModelSettings.model_id == model_id).first()

        if not setting:
            # ایجاد تنظیمات جدید با وضعیت غیرفعال
            setting = ModelSettings(model_id=model_id, enabled=0)
            db.add(setting)
        else:
            setting.enabled = 0 if setting.enabled else 1

        db.commit()

        return {
            "success": True,
            "model_id": model_id,
            "enabled": bool(setting.enabled)
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error toggling model: {e}")
        return {"success": False, "error": str(e)}


@router.post("/settings/batch-update")
async def batch_update_model_settings(
    updates: List[Dict[str, Any]],
    db: Session = Depends(get_db)
):
    """
    بروزرسانی گروهی تنظیمات مدل‌ها
    مثال: [{"model_id": "gpt-4o", "enabled": true}, {"model_id": "claude-3", "enabled": false}]
    """
    try:
        from ...core.models_registry import MODEL_REGISTRY

        updated = []
        for update in updates:
            model_id = update.get("model_id")
            if not model_id or model_id not in MODEL_REGISTRY:
                continue

            setting = db.query(ModelSettings).filter(ModelSettings.model_id == model_id).first()
            if not setting:
                setting = ModelSettings(model_id=model_id)
                db.add(setting)

            if "enabled" in update:
                setting.enabled = 1 if update["enabled"] else 0
            if "allowed_tasks" in update:
                setting.allowed_tasks = update["allowed_tasks"]
            if "priority" in update:
                setting.priority = update["priority"]

            updated.append(model_id)

        db.commit()

        return {
            "success": True,
            "updated_count": len(updated),
            "updated_models": updated
        }

    except Exception as e:
        db.rollback()
        logger.error(f"Error batch updating models: {e}")
        return {"success": False, "error": str(e)}


@router.get("/task-types")
async def get_available_task_types():
    """
    دریافت لیست انواع کارهای قابل تخصیص به مدل‌ها
    """
    return {
        "success": True,
        "task_types": AVAILABLE_TASK_TYPES
    }


@router.get("/settings/by-task/{task_type}")
async def get_models_for_task(task_type: str, db: Session = Depends(get_db)):
    """
    دریافت مدل‌های مجاز برای یک نوع کار خاص
    """
    try:
        from ...core.models_registry import MODEL_REGISTRY
        from ...services.ai_manager import get_ai_manager

        ai_manager = get_ai_manager()
        available_providers = ai_manager.get_available_providers()

        db_settings = db.query(ModelSettings).all()
        settings_map = {s.model_id: s for s in db_settings}

        allowed_models = []
        for model_id, model in MODEL_REGISTRY.items():
            setting = settings_map.get(model_id)

            # بررسی فعال بودن
            if setting:
                if not setting.enabled:
                    continue
                allowed_tasks = setting.allowed_tasks or ["all"]
            else:
                if not model.enabled:
                    continue
                allowed_tasks = ["all"]

            # بررسی مجاز بودن برای این task
            if "all" in allowed_tasks or task_type in allowed_tasks:
                model_provider = get_provider_value(model.provider)
                is_available = model_provider in available_providers

                allowed_models.append({
                    "model_id": model_id,
                    "model_name": model.name,
                    "provider": model_provider,
                    "priority": setting.priority if setting else model.priority,
                    "is_available": is_available,
                    "is_preferred": task_type in (setting.preferred_for if setting else [])
                })

        # مرتب‌سازی بر اساس اولویت
        allowed_models.sort(key=lambda x: (not x["is_preferred"], x["priority"]))

        return {
            "success": True,
            "task_type": task_type,
            "models": allowed_models,
            "count": len(allowed_models)
        }

    except Exception as e:
        logger.error(f"Error getting models for task: {e}")
        return {"success": False, "error": str(e)}


@router.delete("/settings/{model_id}")
async def reset_model_settings(model_id: str, db: Session = Depends(get_db)):
    """
    بازگردانی تنظیمات مدل به حالت پیش‌فرض
    """
    try:
        setting = db.query(ModelSettings).filter(ModelSettings.model_id == model_id).first()

        if setting:
            db.delete(setting)
            db.commit()
            return {
                "success": True,
                "message": "تنظیمات به حالت پیش‌فرض بازگردانده شد",
                "model_id": model_id
            }
        else:
            return {
                "success": True,
                "message": "مدل تنظیمات سفارشی نداشت",
                "model_id": model_id
            }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"خطا در بازگردانی تنظیمات: {str(e)}")
