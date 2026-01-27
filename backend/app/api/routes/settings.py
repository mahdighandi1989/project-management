"""
API routes برای تنظیمات سیستم
با پشتیبانی SQLite
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Dict, Optional, Any, List
from sqlalchemy.orm import Session
import os

from ...core.config import settings
from ...core.roles import WORK_MODES, ROLES_REGISTRY, WorkMode, RoleType
from ...core.database import get_db
from ...models.setting import Setting

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
    perplexity: bool  # 🆕


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
    perplexity: Optional[str] = None  # 🆕


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
        perplexity=providers.get("perplexity", False),  # 🆕
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

        if request.perplexity:  # 🆕
            os.environ["PERPLEXITY_API_KEY"] = request.perplexity
            env_updates["PERPLEXITY_API_KEY"] = request.perplexity
            updated.append("perplexity")

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
async def update_deploy_keys(request: UpdateDeployKeysRequest, db: Session = Depends(get_db)):
    """آپدیت کلیدهای Deploy (Render, GitHub) - ذخیره در دیتابیس و environment"""
    try:
        updated = []
        env_updates = {}

        if request.render:
            os.environ["RENDER_API_KEY"] = request.render
            env_updates["RENDER_API_KEY"] = request.render
            # ذخیره در دیتابیس
            Setting.set_value(
                db=db,
                key="api_key_render",
                value=request.render,
                value_type="encrypted",
                category="api_keys",
                description="Render API Key",
                is_secret=True
            )
            updated.append("render")

        if request.github:
            os.environ["GITHUB_TOKEN"] = request.github
            env_updates["GITHUB_TOKEN"] = request.github
            # ذخیره در دیتابیس
            Setting.set_value(
                db=db,
                key="api_key_github",
                value=request.github,
                value_type="encrypted",
                category="api_keys",
                description="GitHub Token",
                is_secret=True
            )
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
async def get_deploy_keys_status(db: Session = Depends(get_db)):
    """وضعیت کلیدهای Deploy - چک environment و دیتابیس"""
    render_key = os.environ.get("RENDER_API_KEY")
    github_key = os.environ.get("GITHUB_TOKEN")

    # اگر در environment نبود، از دیتابیس بخون
    if not render_key:
        try:
            render_key = Setting.get_value(db, "api_key_render")
            if render_key:
                os.environ["RENDER_API_KEY"] = render_key
        except:
            pass

    if not github_key:
        try:
            github_key = Setting.get_value(db, "api_key_github")
            if github_key:
                os.environ["GITHUB_TOKEN"] = github_key
        except:
            pass

    return {
        "render": bool(render_key),
        "github": bool(github_key),
    }


# ===========================================
# 🆕 Database-backed Settings (SQLite)
# ===========================================

class SettingValue(BaseModel):
    """یک تنظیم"""
    key: str
    value: Any
    value_type: str = "string"
    category: str = "general"
    description: Optional[str] = None
    is_secret: bool = False


class SettingsUpdateRequest(BaseModel):
    """درخواست بروزرسانی چند تنظیم"""
    settings: List[SettingValue]


@router.get("/db/all")
async def get_all_db_settings(db: Session = Depends(get_db)):
    """
    دریافت همه تنظیمات از دیتابیس
    تنظیمات حساس فقط چند کاراکتر آخر نشون داده میشن
    """
    try:
        all_settings = db.query(Setting).all()
        return {
            "success": True,
            "settings": [s.to_dict(hide_secrets=True) for s in all_settings],
            "count": len(all_settings)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/db/category/{category}")
async def get_settings_by_category(category: str, db: Session = Depends(get_db)):
    """دریافت تنظیمات یک دسته"""
    try:
        category_settings = db.query(Setting).filter(Setting.category == category).all()
        return {
            "success": True,
            "category": category,
            "settings": [s.to_dict(hide_secrets=True) for s in category_settings],
            "count": len(category_settings)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/db/{key}")
async def get_db_setting(key: str, db: Session = Depends(get_db)):
    """دریافت یک تنظیم خاص"""
    try:
        value = Setting.get_value(db, key)
        setting = db.query(Setting).filter(Setting.key == key).first()

        if setting is None:
            return {"success": False, "error": "تنظیم یافت نشد"}

        return {
            "success": True,
            "key": key,
            "value": value if not setting.is_secret else "***hidden***",
            "value_type": setting.value_type,
            "category": setting.category,
            "is_secret": setting.is_secret
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/db/{key}")
async def set_db_setting(key: str, data: SettingValue, db: Session = Depends(get_db)):
    """تنظیم یا بروزرسانی یک مقدار"""
    try:
        setting = Setting.set_value(
            db=db,
            key=key,
            value=data.value,
            value_type=data.value_type,
            category=data.category,
            description=data.description,
            is_secret=data.is_secret
        )
        return {
            "success": True,
            "message": f"تنظیم '{key}' ذخیره شد",
            "setting": setting.to_dict(hide_secrets=True)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/db/bulk")
async def set_bulk_settings(request: SettingsUpdateRequest, db: Session = Depends(get_db)):
    """بروزرسانی چندین تنظیم همزمان"""
    try:
        updated = []
        for setting_data in request.settings:
            Setting.set_value(
                db=db,
                key=setting_data.key,
                value=setting_data.value,
                value_type=setting_data.value_type,
                category=setting_data.category,
                description=setting_data.description,
                is_secret=setting_data.is_secret
            )
            updated.append(setting_data.key)

        return {
            "success": True,
            "updated": updated,
            "count": len(updated)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/db/{key}")
async def delete_db_setting(key: str, db: Session = Depends(get_db)):
    """حذف یک تنظیم"""
    try:
        setting = db.query(Setting).filter(Setting.key == key).first()
        if not setting:
            return {"success": False, "error": "تنظیم یافت نشد"}

        db.delete(setting)
        db.commit()

        return {"success": True, "message": f"تنظیم '{key}' حذف شد"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/db/sync-env")
async def sync_env_to_db(db: Session = Depends(get_db)):
    """
    سینک متغیرهای محیطی به دیتابیس
    API keyها رو به صورت is_secret=True ذخیره می‌کنه
    """
    try:
        synced = []

        # API Keys
        api_keys = {
            "OPENAI_API_KEY": "openai",
            "CLAUDE_API_KEY": "claude",
            "GEMINI_API_KEY": "gemini",
            "DEEPSEEK_API_KEY": "deepseek",
            "OPENROUTER_API_KEY": "openrouter",
            "GROQ_API_KEY": "groq",
            "PERPLEXITY_API_KEY": "perplexity",  # 🆕
            "RENDER_API_KEY": "render",
            "GITHUB_TOKEN": "github",
        }

        for env_key, name in api_keys.items():
            value = os.environ.get(env_key)
            if value:
                Setting.set_value(
                    db=db,
                    key=f"api_key_{name}",
                    value=value,
                    value_type="encrypted",
                    category="api_keys",
                    description=f"API Key for {name}",
                    is_secret=True
                )
                synced.append(f"api_key_{name}")

        # GitHub settings
        github_settings = {
            "GITHUB_OWNER": "github_owner",
            "GITHUB_REPO": "github_repo",
        }

        for env_key, db_key in github_settings.items():
            value = os.environ.get(env_key)
            if value:
                Setting.set_value(
                    db=db,
                    key=db_key,
                    value=value,
                    value_type="string",
                    category="storage",
                    description=f"GitHub {db_key.replace('github_', '')}"
                )
                synced.append(db_key)

        return {
            "success": True,
            "synced": synced,
            "count": len(synced),
            "message": "تنظیمات محیطی به دیتابیس سینک شدند"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
