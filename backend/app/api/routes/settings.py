"""
API routes برای تنظیمات سیستم
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Optional, Any
import os

from ...core.config import settings
from ...core.roles import WORK_MODES, ROLES_REGISTRY, WorkMode, RoleType

router = APIRouter(prefix="/settings", tags=["Settings"])


# ===========================================
# Response Models
# ===========================================

class SystemStatus(BaseModel):
    """وضعیت سیستم"""
    app_name: str
    version: str
    environment: str
    debug: bool
    available_providers: Dict[str, bool]


class ApiKeyStatus(BaseModel):
    """وضعیت API keys"""
    openai: bool
    claude: bool
    gemini: bool
    deepseek: bool
    openrouter: bool
    groq: bool


class WorkModeInfo(BaseModel):
    """اطلاعات یک حالت کاری"""
    id: str
    name: str
    name_fa: str
    icon: str
    rounds: int
    scoring: bool
    judge: bool
    summary: bool
    default_roles: list


class RoleInfo(BaseModel):
    """اطلاعات یک نقش"""
    id: str
    name: str
    name_fa: str
    icon: str
    description: str


class UpdateApiKeysRequest(BaseModel):
    """درخواست آپدیت API keys"""
    openai: Optional[str] = None
    claude: Optional[str] = None
    gemini: Optional[str] = None
    deepseek: Optional[str] = None
    openrouter: Optional[str] = None
    groq: Optional[str] = None


# ===========================================
# Endpoints
# ===========================================

@router.get("/status", response_model=SystemStatus)
async def get_system_status():
    """دریافت وضعیت سیستم"""
    return SystemStatus(
        app_name=settings.APP_NAME,
        version=settings.APP_VERSION,
        environment=settings.ENVIRONMENT,
        debug=settings.DEBUG,
        available_providers=settings.get_available_providers(),
    )


@router.get("/api-keys/status", response_model=ApiKeyStatus)
async def get_api_keys_status():
    """وضعیت API keys (فقط بررسی وجود)"""
    providers = settings.get_available_providers()
    return ApiKeyStatus(
        openai=providers.get("openai", False),
        claude=providers.get("claude", False),
        gemini=providers.get("gemini", False),
        deepseek=providers.get("deepseek", False),
        openrouter=providers.get("openrouter", False),
        groq=providers.get("groq", False),
    )


@router.put("/api-keys")
async def update_api_keys(request: UpdateApiKeysRequest):
    """آپدیت API keys (ذخیره در environment)"""
    try:
        updated = []

        if request.openai:
            os.environ["OPENAI_API_KEY"] = request.openai
            updated.append("openai")

        if request.claude:
            os.environ["CLAUDE_API_KEY"] = request.claude
            updated.append("claude")

        if request.gemini:
            os.environ["GEMINI_API_KEY"] = request.gemini
            updated.append("gemini")

        if request.deepseek:
            os.environ["DEEPSEEK_API_KEY"] = request.deepseek
            updated.append("deepseek")

        if request.openrouter:
            os.environ["OPENROUTER_API_KEY"] = request.openrouter
            updated.append("openrouter")

        if request.groq:
            os.environ["GROQ_API_KEY"] = request.groq
            updated.append("groq")

        # Reinitialize AI manager
        from ...services.ai_manager import get_ai_manager, _ai_manager
        global _ai_manager
        if _ai_manager:
            await _ai_manager.close()
        _ai_manager = None

        return {
            "success": True,
            "updated": updated,
            "message": "API keys updated. Please restart for full effect."
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/work-modes", response_model=list[WorkModeInfo])
async def get_work_modes():
    """لیست حالت‌های کاری"""
    return [WorkModeInfo(
        id=mode.id.value,
        name=mode.name,
        name_fa=mode.name_fa,
        icon=mode.icon,
        rounds=mode.rounds,
        scoring=mode.scoring,
        judge=mode.judge,
        summary=mode.summary,
        default_roles=[r.value for r in mode.default_roles],
    ) for mode in WORK_MODES.values()]


@router.get("/roles", response_model=list[RoleInfo])
async def get_roles():
    """لیست نقش‌ها"""
    return [RoleInfo(
        id=role.id.value,
        name=role.name,
        name_fa=role.name_fa,
        icon=role.icon,
        description=role.description,
    ) for role in ROLES_REGISTRY.values()]


@router.get("/config")
async def get_config():
    """تنظیمات فعلی (بدون secrets)"""
    return {
        "max_tokens_per_model": settings.MAX_TOKENS_PER_MODEL,
        "max_tokens_for_scoring": settings.MAX_TOKENS_FOR_SCORING,
        "max_tokens_for_judge": settings.MAX_TOKENS_FOR_JUDGE,
        "max_tokens_for_summary": settings.MAX_TOKENS_FOR_SUMMARY,
        "max_prompt_length": settings.MAX_PROMPT_LENGTH,
        "request_timeout": settings.REQUEST_TIMEOUT,
        "max_model_time": settings.MAX_MODEL_TIME,
        "cors_origins": settings.CORS_ORIGINS,
    }
