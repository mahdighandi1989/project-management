"""
API routes برای مدیریت مدل‌ها
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any

from ...services.ai_manager import get_ai_manager
from ...core.models_registry import (
    MODEL_REGISTRY, MODEL_ALIASES,
    get_model, get_enabled_models,
    get_models_by_capability, get_image_generator_models,
    get_vision_models,
    ModelCapability
)
from ...core.config import settings

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
# Endpoints
# ===========================================

@router.get("/", response_model=List[ModelInfo])
async def list_models(provider: Optional[str] = None, capability: Optional[str] = None):
    """لیست همه مدل‌ها"""
    try:
        ai_manager = get_ai_manager()
        available_providers = ai_manager.get_available_providers()
    except Exception:
        available_providers = []

    models = []
    for model in MODEL_REGISTRY.values():
        # فیلتر بر اساس provider
        if provider and model.provider.value != provider:
            continue

        # فیلتر بر اساس capability
        if capability:
            try:
                cap = ModelCapability(capability)
                if cap not in model.capabilities:
                    continue
            except ValueError:
                pass

        is_available = model.provider.value in available_providers

        models.append(ModelInfo(
            id=model.id,
            provider=model.provider.value,
            name=model.name,
            capabilities=[c.value for c in model.capabilities],
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

    return models


@router.get("/available", response_model=List[ModelInfo])
async def list_available_models():
    """لیست مدل‌های قابل استفاده (با API key)"""
    try:
        ai_manager = get_ai_manager()
        available = ai_manager.get_available_models()
    except Exception:
        # اگر هیچ API key ست نشده، لیست خالی برگردان
        return []

    return [ModelInfo(
        id=m.id,
        provider=m.provider.value,
        name=m.name,
        capabilities=[c.value for c in m.capabilities],
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


@router.get("/providers", response_model=List[ProviderStatus])
async def list_providers():
    """لیست provider ها و وضعیتشان"""
    try:
        ai_manager = get_ai_manager()
        available_providers = ai_manager.get_available_providers()
    except Exception:
        # اگر AI manager مشکل داشت، لیست خالی برگردان
        available_providers = []

    providers = {}
    for model in MODEL_REGISTRY.values():
        provider = model.provider.value
        if provider not in providers:
            providers[provider] = {
                "provider": provider,
                "available": provider in available_providers,
                "models": []
            }
        providers[provider]["models"].append(model.id)

    return [ProviderStatus(
        provider=p["provider"],
        available=p["available"],
        model_count=len(p["models"]),
        models=p["models"]
    ) for p in providers.values()]


@router.get("/{model_id}", response_model=ModelInfo)
async def get_model_info(model_id: str):
    """دریافت اطلاعات یک مدل"""
    try:
        model = get_model(model_id)
        if not model:
            raise HTTPException(status_code=404, detail="Model not found")

        ai_manager = get_ai_manager()
        is_available = model.provider.value in ai_manager.get_available_providers()

        return ModelInfo(
            id=model.id,
            provider=model.provider.value,
            name=model.name,
            capabilities=[c.value for c in model.capabilities],
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
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/smart-select", response_model=List[ModelInfo])
async def smart_select_models(request: SmartSelectRequest):
    """انتخاب هوشمند مدل‌ها"""
    try:
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
        from ...core.models_registry import ModelProvider
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
            provider=m.provider.value,
            name=m.name,
            capabilities=[c.value for c in m.capabilities],
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
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/aliases", response_model=Dict[str, str])
async def get_aliases():
    """لیست alias های مدل‌ها"""
    return MODEL_ALIASES


@router.get("/capabilities")
async def get_capabilities():
    """لیست همه قابلیت‌ها"""
    return [{"id": c.value, "name": c.name} for c in ModelCapability]
