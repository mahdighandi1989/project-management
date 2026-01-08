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
    """آپدیت API keys (ذخیره در environment و فایل .env)"""
    try:
        updated = []
        env_updates = {}

        if request.openai:
            os.environ["OPENAI_API_KEY"] = request.openai
            env_updates["OPENAI_API_KEY"] = request.openai
            updated.append("openai")

        if request.claude:
            os.environ["CLAUDE_API_KEY"] = request.claude
            env_updates["CLAUDE_API_KEY"] = request.claude
            updated.append("claude")

        if request.gemini:
            os.environ["GEMINI_API_KEY"] = request.gemini
            env_updates["GEMINI_API_KEY"] = request.gemini
            updated.append("gemini")

        if request.deepseek:
            os.environ["DEEPSEEK_API_KEY"] = request.deepseek
            env_updates["DEEPSEEK_API_KEY"] = request.deepseek
            updated.append("deepseek")

        if request.openrouter:
            os.environ["OPENROUTER_API_KEY"] = request.openrouter
            env_updates["OPENROUTER_API_KEY"] = request.openrouter
            updated.append("openrouter")

        if request.groq:
            os.environ["GROQ_API_KEY"] = request.groq
            env_updates["GROQ_API_KEY"] = request.groq
            updated.append("groq")

        # ذخیره در فایل .env
        env_file = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), ".env")
        try:
            existing = {}
            if os.path.exists(env_file):
                with open(env_file, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if line and '=' in line and not line.startswith('#'):
                            key, value = line.split('=', 1)
                            existing[key] = value

            existing.update(env_updates)

            with open(env_file, 'w') as f:
                for key, value in existing.items():
                    f.write(f"{key}={value}\n")
        except Exception as e:
            print(f"Warning: Could not save to .env file: {e}")

        # Reload settings - no longer using cache
        # Settings are read fresh from environment on each instantiation

        # Reinitialize AI manager
        from ...services.ai_manager import reset_ai_manager
        try:
            new_manager = await reset_ai_manager()
            available = new_manager.get_available_providers()
        except Exception as e:
            available = []
            print(f"Warning: Could not reinitialize AI manager: {e}")

        return {
            "success": True,
            "updated": updated,
            "available_providers": available,
            "message": "API keys updated successfully!"
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


class UpdateDeployKeysRequest(BaseModel):
    """درخواست آپدیت کلیدهای Deploy"""
    render: Optional[str] = None
    github: Optional[str] = None


@router.put("/deploy-keys")
async def update_deploy_keys(request: UpdateDeployKeysRequest):
    """آپدیت کلیدهای Deploy (Render, GitHub)"""
    try:
        updated = []
        env_updates = {}

        if request.render:
            os.environ["RENDER_API_KEY"] = request.render
            env_updates["RENDER_API_KEY"] = request.render
            updated.append("render")

        if request.github:
            os.environ["GITHUB_TOKEN"] = request.github
            env_updates["GITHUB_TOKEN"] = request.github
            updated.append("github")

        # ذخیره در فایل .env
        env_file = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), ".env")
        try:
            existing = {}
            if os.path.exists(env_file):
                with open(env_file, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if line and '=' in line and not line.startswith('#'):
                            key, value = line.split('=', 1)
                            existing[key] = value

            existing.update(env_updates)

            with open(env_file, 'w') as f:
                for key, value in existing.items():
                    f.write(f"{key}={value}\n")
        except Exception as e:
            print(f"Warning: Could not save to .env file: {e}")

        return {
            "success": True,
            "updated": updated,
            "message": "Deploy keys updated successfully!"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/deploy-keys/status")
async def get_deploy_keys_status():
    """وضعیت کلیدهای Deploy"""
    return {
        "render": bool(os.environ.get("RENDER_API_KEY")),
        "github": bool(os.environ.get("GITHUB_TOKEN")),
    }
