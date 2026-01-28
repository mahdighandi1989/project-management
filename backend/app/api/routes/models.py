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
            best_acc = max(top_models, key=lambda p: p.accuracy_rate)
            leaderboard["best_accuracy"] = {
                "label": "بهترین دقت",
                "model_id": best_acc.model_id,
                "display_name": best_acc.model_id,
                "score": best_acc.accuracy_rate,
                "tier": "S" if best_acc.accuracy_rate >= 90 else "A" if best_acc.accuracy_rate >= 80 else "B"
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
            best_overall = max(top_models, key=lambda p: p.cumulative_score)
            leaderboard["best_overall"] = {
                "label": "بهترین کلی",
                "model_id": best_overall.model_id,
                "display_name": best_overall.model_id,
                "score": best_overall.cumulative_score,
                "tier": "S" if best_overall.cumulative_score >= 90 else "A" if best_overall.cumulative_score >= 80 else "B"
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

        # Sort by cumulative score
        sorted_by_score = sorted(profiles, key=lambda p: p.cumulative_score, reverse=True)
        for i, p in enumerate(sorted_by_score[:10], 1):
            rankings["by_score"].append({
                "rank": i,
                "model_id": p.model_id,
                "score": p.cumulative_score
            })

        # Sort by accuracy
        sorted_by_accuracy = sorted(profiles, key=lambda p: p.accuracy_rate, reverse=True)
        for i, p in enumerate(sorted_by_accuracy[:10], 1):
            rankings["by_accuracy"].append({
                "rank": i,
                "model_id": p.model_id,
                "accuracy": p.accuracy_rate
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


