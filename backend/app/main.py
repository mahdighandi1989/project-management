"""
نقطه ورود اصلی برنامه
FastAPI Application
"""

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging
import time
from contextlib import asynccontextmanager

from .core.config import settings
from .core.database import init_db, get_db_info
from .api.routes import debate, models, chat, settings as settings_routes
from .api.routes import projects, diagrams, creator, upload, orchestrator
from .api.routes import config, external, runtime, external_projects, unified_api
from .api.routes import simple_projects  # 🆕 API ساده
from .api.routes import github_import  # 🆕 GitHub Import
from .api.routes import project_memory  # 🆕 Project Memory (باکس حافظه)
from .api.routes import project_structure  # 🆕 Project Structure Diagram
from .api.routes import project_journal  # 🆕 Project Journal & Reports
from .api.routes import analysis  # 🆕 Project Analysis & AI Profiles
from .api.routes import project_health  # 🆕 Project Health Analysis (تحلیل سلامت پروژه)
from .api.routes import render_logs  # 🆕 Render Logs (لاگ‌های رندر)
from .api.routes import security_analysis  # 🆕 Security Analysis (تحلیل امنیتی)
from .api.routes import system_prompts  # 🆕 System Prompts (مدیریت پرامپت‌ها)
from .api.routes import notifications  # 🆕 Notifications (Telegram/Email)
from .api.routes import ai_usage  # 🆕 AI Usage tracking (token consumption + leak detection)

# Defensive import for oversight (mustn't block app boot if storage/AI deps misbehave)
try:
    from .api.routes import oversight  # 🆕 Oversight (مرکز نظارت پروژه‌های GitHub)
    OVERSIGHT_AVAILABLE = True
except Exception as _e:
    import logging as _logging
    _logging.error(f"Could not import oversight (skipping): {_e}", exc_info=True)
    OVERSIGHT_AVAILABLE = False
    oversight = None

# Defensive import for model_profiles
try:
    from .api.routes import model_profiles  # 🆕 Model Profiles API (پروفایل مدل‌ها)
    MODEL_PROFILES_AVAILABLE = True
except ImportError as e:
    import logging as _logging
    _logging.warning(f"Could not import model_profiles: {e}")
    MODEL_PROFILES_AVAILABLE = False
    model_profiles = None

# تنظیم logging
logging.basicConfig(
    level=logging.INFO if not settings.DEBUG else logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """مدیریت lifecycle برنامه"""
    # Startup
    logger.info(f"🚀 Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    logger.info(f"📍 Environment: {settings.ENVIRONMENT}")

    # 🆕 Initialize SQLite Database
    logger.info("🗄️ Initializing SQLite database...")
    init_db()
    db_info = get_db_info()
    logger.info(f"📊 Database: {db_info.get('path')} ({db_info.get('size_mb', 0)} MB)")
    if db_info.get('record_counts'):
        for table, count in db_info['record_counts'].items():
            logger.info(f"  📋 {table}: {count} records")

    # بارگذاری API keys از دیتابیس
    await load_api_keys_from_database()

    # بررسی API keys
    providers = settings.get_available_providers()
    available = [k for k, v in providers.items() if v]
    logger.info(f"✅ Available providers: {', '.join(available) or 'None'}")

    # بارگذاری داده‌ها از GitHub (مهم برای persistence)
    await initialize_persistent_data()

    # 🆕 Start Background Scheduler
    await start_background_scheduler()

    # 🆕 Start Oversight scheduler loop (defensively — never block app startup)
    try:
        import asyncio
        from .services.oversight_service import oversight_scheduler_loop
        app.state.oversight_stop_event = asyncio.Event()
        app.state.oversight_task = asyncio.create_task(
            oversight_scheduler_loop(app.state.oversight_stop_event, interval_seconds=60)
        )
        logger.info("🛰️ Oversight scheduler started")
    except Exception as e:
        logger.error(f"Oversight scheduler failed to start (app continues): {e}", exc_info=True)
        app.state.oversight_stop_event = None
        app.state.oversight_task = None

    # 🆕 (Stage 2 — File Attachment) — orphan upload cleanup on boot
    try:
        from .services.oversight_upload_session import get_upload_session_service
        removed = await get_upload_session_service().cleanup_orphans()
        if removed:
            logger.info(f"📎 cleaned up {removed} orphan upload temp files on boot")
    except Exception as e:
        logger.warning(f"upload orphan cleanup failed (non-fatal): {e}")

    # 🆕 (Stage 6 — temp model activation) — revert stale temp_enabled flags
    try:
        from .services.oversight_model_temp_activate import cleanup_stale_temp_activations_on_boot
        n = await cleanup_stale_temp_activations_on_boot()
        if n:
            logger.info(f"🔒 reset temporary_enabled flag for {n} models on boot")
    except Exception as e:
        logger.warning(f"temp-activate boot cleanup failed (non-fatal): {e}")

    # 🆕 (Stage 9 — extraction recovery) — extractionهای stale را mark failed کن
    try:
        from .services.oversight_extraction import boot_recover_stale_extractions
        rec = await boot_recover_stale_extractions()
        if rec.get("cleared_stale_extractions"):
            logger.info(
                f"📎 cleared {rec['cleared_stale_extractions']} stale extraction(s) on boot"
            )
    except Exception as e:
        logger.warning(f"extraction boot recovery failed (non-fatal): {e}")

    # 🆕 (Telegram Compose Stage 1) — bufferهای expired را حذف کن
    try:
        from .services.oversight_telegram_compose import get_compose_service
        n = await get_compose_service().cleanup_expired()
        if n:
            logger.info(f"📦 cleaned up {n} expired compose buffer(s) on boot")
    except Exception as e:
        logger.warning(f"compose boot cleanup failed (non-fatal): {e}")

    yield

    # Shutdown
    logger.info("👋 Shutting down...")

    # 🆕 Stop Background Scheduler
    stop_background_scheduler()

    # Stop oversight loop
    try:
        stop_evt = getattr(app.state, "oversight_stop_event", None)
        task = getattr(app.state, "oversight_task", None)
        if stop_evt:
            stop_evt.set()
        if task:
            await asyncio.wait_for(task, timeout=5)
    except Exception as e:
        logger.warning(f"Oversight stop error: {e}")

    # close oversight session
    try:
        from .services.oversight_service import get_oversight_service
        await get_oversight_service().close()
    except Exception:
        pass

    # Stop all running project containers
    try:
        from .services.runtime_executor import get_runtime_executor
        executor = get_runtime_executor()
        await executor.cleanup_all()
        logger.info("🐳 Stopped all running project containers")
    except Exception as e:
        logger.error(f"Error stopping containers: {e}")

    from .services.ai_manager import get_ai_manager
    ai_manager = get_ai_manager()
    await ai_manager.close()


async def load_api_keys_from_database():
    """بارگذاری API keys از دیتابیس به environment در startup"""
    import os
    try:
        from sqlalchemy.orm import Session
        from .core.database import SessionLocal
        from .models.setting import Setting

        db = SessionLocal()

        # مپ کلیدها: (db_key, env_key)
        key_mapping = [
            ("api_key_openai", "OPENAI_API_KEY"),
            ("api_key_claude", "CLAUDE_API_KEY"),
            ("api_key_gemini", "GEMINI_API_KEY"),
            ("api_key_deepseek", "DEEPSEEK_API_KEY"),
            ("api_key_openrouter", "OPENROUTER_API_KEY"),
            ("api_key_groq", "GROQ_API_KEY"),
            ("api_key_perplexity", "PERPLEXITY_API_KEY"),
            ("api_key_render", "RENDER_API_KEY"),
            ("api_key_github", "GITHUB_TOKEN"),
        ]

        loaded_count = 0
        for db_key, env_key in key_mapping:
            # فقط اگر در environment نیست، از دیتابیس بخون
            if not os.environ.get(env_key):
                try:
                    value = Setting.get_value(db, db_key)
                    if value:
                        os.environ[env_key] = value
                        loaded_count += 1
                        logger.info(f"  🔑 Loaded {env_key} from database")
                except Exception:
                    pass

        db.close()

        if loaded_count > 0:
            logger.info(f"🔐 Loaded {loaded_count} API keys from database")
        else:
            logger.info("🔐 No API keys found in database (or all already in environment)")

    except Exception as e:
        logger.warning(f"⚠️ Could not load API keys from database: {e}")


async def initialize_persistent_data():
    """بارگذاری داده‌های ذخیره شده از GitHub در startup"""
    try:
        from .services.github_storage import get_github_storage
        from .services.project_service import get_project_service
        from .services.smart_orchestrator import get_smart_orchestrator
        from .services.ai_manager import get_ai_manager
        from .services.creator_engine import get_creator_engine

        logger.info("🔄 Initializing services...")

        # ✅ ALWAYS initialize AI manager and creator engine first
        ai_manager = get_ai_manager()
        creator_engine = get_creator_engine()

        # Initialize creator engine (required for project creation!)
        if not creator_engine.ai_orchestrator:
            creator_engine.initialize(ai_manager)
            logger.info("✅ Creator Engine initialized")

        # بعد GitHub storage رو بررسی کن (optional)
        github_storage = get_github_storage()

        # بررسی تنظیمات GitHub
        if not github_storage.token:
            logger.warning("⚠️ GITHUB_TOKEN not set - persistence disabled")
            return
        if not github_storage.owner:
            logger.warning("⚠️ GITHUB_OWNER not set - persistence disabled")
            return
        if not github_storage.repo:
            logger.warning("⚠️ GITHUB_REPO not set - persistence disabled")
            return

        logger.info(f"🔗 GitHub config: {github_storage.owner}/{github_storage.repo}")

        connection = await github_storage.check_connection()

        if not connection.get("success"):
            logger.warning(f"⚠️ GitHub not connected: {connection.get('error')}")
            return

        logger.info("📂 GitHub connected, loading persisted data...")

        # بارگذاری پروژه‌ها از GitHub
        project_service = get_project_service()
        project_service.github_storage = github_storage
        await load_projects_from_github(github_storage, project_service)

        # Initialize orchestrator و بارگذاری workflow ها
        orchestrator = get_smart_orchestrator()
        if not orchestrator.is_initialized():
            orchestrator.initialize(ai_manager, project_service, creator_engine)
            orchestrator.integrator.set_github_storage(github_storage)

        # بارگذاری workflow های ذخیره شده
        await load_workflows_from_github(github_storage, orchestrator)

        logger.info("✅ Persistent data loaded successfully")

        # Initialize runtime executor and check for pending upgrades
        await initialize_runtime_services(github_storage)

    except Exception as e:
        logger.error(f"❌ Error loading persistent data: {e}", exc_info=True)


async def load_projects_from_github(github_storage, project_service):
    """بارگذاری همه پروژه‌ها از GitHub"""
    try:
        import base64
        import json
        from .services.project_service import ProjectContext

        # لیست پوشه projects
        folders = await github_storage.list_folder("projects")
        loaded_count = 0

        for folder in folders:
            if folder.type == "dir" and folder.name.startswith("proj_"):
                project_id = folder.name

                # اگه قبلا لود نشده
                if project_id not in project_service.projects:
                    # اول source/metadata.json رو چک کن
                    result = await github_storage.get_file(f"projects/{project_id}/source/metadata.json")
                    if not result.get("success"):
                        # اگه نبود، metadata.json رو چک کن
                        result = await github_storage.get_file(f"projects/{project_id}/metadata.json")

                    if result.get("success") and result.get("content"):
                        try:
                            content = base64.b64decode(result["content"]).decode('utf-8')
                            data = json.loads(content)
                            project = ProjectContext(**data)
                            project_service.projects[project_id] = project
                            loaded_count += 1
                            logger.info(f"  📁 Loaded project: {project.name}")
                        except Exception as e:
                            logger.warning(f"  ⚠️ Could not load project {project_id}: {e}")

        logger.info(f"📊 Loaded {loaded_count} projects from GitHub")

    except Exception as e:
        logger.error(f"Error loading projects from GitHub: {e}")


async def load_workflows_from_github(github_storage, orchestrator):
    """بارگذاری workflow results از GitHub"""
    try:
        import base64
        import json

        # لیست پوشه projects
        folders = await github_storage.list_folder("projects")
        loaded_count = 0

        for folder in folders:
            if folder.type == "dir" and folder.name.startswith("proj_"):
                project_id = folder.name

                # اگه workflow قبلا در memory نیست
                if project_id not in orchestrator.integrator.active_workflows:
                    # workflow_results.json رو بخون
                    result = await github_storage.get_file(f"projects/{project_id}/generated/workflow_results.json")
                    if result.get("success") and result.get("content"):
                        try:
                            content = base64.b64decode(result["content"]).decode('utf-8')
                            workflow_data = json.loads(content)
                            orchestrator.integrator.active_workflows[project_id] = workflow_data
                            loaded_count += 1
                            logger.info(f"  🔄 Loaded workflow for: {project_id}")
                        except Exception as e:
                            logger.warning(f"  ⚠️ Could not load workflow {project_id}: {e}")

        logger.info(f"🔄 Loaded {loaded_count} workflows from GitHub")

    except Exception as e:
        logger.error(f"Error loading workflows from GitHub: {e}")


async def start_background_scheduler():
    """شروع scheduler برای کارهای پس‌زمینه"""
    try:
        from .services.background_scheduler import get_background_scheduler
        scheduler = get_background_scheduler()
        scheduler.start()
        logger.info("🕐 Background scheduler started")
    except Exception as e:
        logger.error(f"❌ Failed to start background scheduler: {e}")


def stop_background_scheduler():
    """توقف scheduler"""
    try:
        from .services.background_scheduler import get_background_scheduler
        scheduler = get_background_scheduler()
        scheduler.stop()
        logger.info("🕐 Background scheduler stopped")
    except Exception as e:
        logger.error(f"❌ Error stopping background scheduler: {e}")


async def initialize_runtime_services(github_storage):
    """Initialize runtime executor and apply pending upgrades"""
    try:
        from .services.runtime_executor import get_runtime_executor
        from .services.capability_detector import get_capability_detector

        logger.info("🐳 Initializing runtime services...")

        # Initialize runtime executor
        executor = get_runtime_executor()
        executor.initialize(github_storage)

        if executor.is_docker_available():
            logger.info("✅ Docker is available for project execution")
        else:
            logger.warning("⚠️ Docker not available - project execution disabled")

        # Initialize capability detector
        detector = get_capability_detector()
        detector.initialize(github_storage)

        # Log system capabilities
        caps = detector.get_capability_summary()
        logger.info(f"📊 System: {caps.get('system', {}).get('os', 'Unknown')}")
        logger.info(f"🔧 Runtimes: {list(caps.get('runtimes', {}).keys())}")
        logger.info(f"🗄️ Databases: {list(caps.get('databases', {}).keys())}")

        # Apply pending upgrades (pull Docker images)
        if github_storage and executor.is_docker_available():
            logger.info("🔄 Checking for pending upgrades...")
            results = await detector.check_and_apply_upgrades()
            if results.get("applied", 0) > 0:
                logger.info(f"✅ Applied {results['applied']} upgrades")
            if results.get("failed", 0) > 0:
                logger.warning(f"⚠️ Failed {results['failed']} upgrades")

        logger.info("✅ Runtime services initialized")

    except Exception as e:
        logger.error(f"❌ Error initializing runtime services: {e}", exc_info=True)


# ایجاد FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="""
سیستم مناظره و همکاری هوش مصنوعی + مدیریت پروژه

## قابلیت‌ها
- 🤖 مناظره بین AI ها با نقش‌های مختلف
- 🎯 حالت‌های کاری متنوع (مناظره، همکاری، تحقیق، ...)
- ⚖️ امتیازدهی و داوری خودکار
- 📝 خلاصه‌نویسی هوشمند
- 🔄 پشتیبانی از چند provider (OpenAI, Claude, Gemini, DeepSeek)
    """,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# ======================================
# CORS Configuration - MUST BE FIRST!
# ======================================
logger.info(f"🔧 Setting up CORS with origins: {settings.cors_origins_list}")

# Use wildcard for simplicity - more permissive but works
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins
    allow_credentials=False,  # Must be False when using "*"
    allow_methods=["*"],  # Allow all methods
    allow_headers=["*"],  # Allow all headers
    expose_headers=["*"],
)


# Middleware برای logging (after CORS)
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()

    try:
        response = await call_next(request)
    except Exception as e:
        # خطا رخ داده - برگرداندن پاسخ با header های CORS
        logger.error(f"Middleware error: {e}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error", "error": str(e)},
            headers={
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "*",
                "Access-Control-Allow-Headers": "*",
            }
        )

    process_time = time.time() - start_time
    logger.info(
        f"{request.method} {request.url.path} - {response.status_code} - {process_time:.3f}s"
    )

    # اضافه کردن header های CORS به همه پاسخ‌ها (اطمینان از وجود)
    response.headers["X-Process-Time"] = str(process_time)
    response.headers["Access-Control-Allow-Origin"] = "*"

    # 🆕 (commit 3.2) Deprecation headers برای endpoint های Health analysis
    # که در حال migration به Oversight هستند. /health/export استثناست
    # (خودش راهکار migration است).
    try:
        path = request.url.path or ""
        is_deprecated = (
            ("/health/" in path and "/health/export" not in path)
            or "/security/scan" in path or "/security/secrets" in path
            or "/security/license" in path or "/security/dependencies" in path
            or "/test-coverage" in path
            or path.endswith("/roadmap") or "/roadmap/items/" in path
            or path.endswith("/readme")
            or path.endswith("/ideal-state")
        )
        if is_deprecated:
            response.headers["Deprecation"] = "true"
            response.headers["Sunset"] = "Wed, 31 Dec 2026 23:59:59 GMT"
            response.headers["Link"] = (
                '</api/oversight/scan>; rel="successor-version", '
                '</api/oversight/codex>; rel="successor-version"'
            )
            response.headers["X-Migration-Note"] = (
                "Deprecated: Health analysis is migrating to /oversight (Deep Scan + Codex). "
                "See /api/projects/{id}/health/export for data backup."
            )
    except Exception:
        pass  # هرگز نباید response را بشکند

    return response


# Exception handler سراسری
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled error: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "error": str(exc) if settings.DEBUG else None},
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "*",
            "Access-Control-Allow-Headers": "*",
        }
    )


# ثبت routes
app.include_router(debate.router, prefix="/api")
app.include_router(models.router, prefix="/api")
app.include_router(chat.router, prefix="/api")
app.include_router(settings_routes.router, prefix="/api")
app.include_router(projects.router, prefix="/api")
app.include_router(diagrams.router, prefix="/api")
app.include_router(creator.router, prefix="/api")
app.include_router(upload.router, prefix="/api")
app.include_router(orchestrator.router, prefix="/api")
app.include_router(config.router, prefix="/api")
app.include_router(external.router, prefix="/api")
app.include_router(runtime.router, prefix="/api")
app.include_router(external_projects.router)
app.include_router(unified_api.router)  # 🆕 Unified API
app.include_router(simple_projects.router)  # 🆕 API ساده و کارآمد
app.include_router(github_import.router, prefix="/api")  # 🆕 GitHub Import
app.include_router(project_memory.router, prefix="/api")  # 🆕 Project Memory (باکس حافظه)
app.include_router(project_structure.router, prefix="/api/projects")  # 🆕 Project Structure Diagram
app.include_router(project_journal.router, prefix="/api/projects")  # 🆕 Project Journal & Reports
app.include_router(analysis.router, prefix="/api")  # 🆕 Project Analysis & AI Profiles
app.include_router(project_health.router)  # 🆕 Project Health Analysis (تحلیل سلامت پروژه)
app.include_router(render_logs.router)  # 🆕 Render Logs (لاگ‌های رندر)
app.include_router(security_analysis.router)  # 🆕 Security Analysis (تحلیل امنیتی)
app.include_router(system_prompts.router)  # 🆕 System Prompts (مدیریت پرامپت‌ها)
app.include_router(notifications.router, prefix="/api")  # 🆕 Notifications (Telegram/Email)
app.include_router(ai_usage.router, prefix="/api")  # 🆕 AI Usage tracking
if OVERSIGHT_AVAILABLE and oversight is not None:
    app.include_router(oversight.router, prefix="/api")  # 🆕 Oversight (مرکز نظارت GitHub)
    # bridge endpoints under /api/projects/{project_id}/{apply-oversight-task,verify-task,oversight-summary}
    try:
        app.include_router(oversight.projects_bridge_router, prefix="/api")
    except AttributeError:
        # backwards-compatible: older oversight module without bridge router
        pass

# Conditionally include model_profiles router
if MODEL_PROFILES_AVAILABLE and model_profiles:
    app.include_router(model_profiles.router)  # 🆕 Model Profiles API (پروفایل مدل‌ها)
    logger.info("✅ Model Profiles API loaded")
else:
    logger.warning("⚠️ Model Profiles API not available")


# Root endpoint
@app.get("/")
async def root():
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running",
        "docs": "/docs",
    }


# Health check
@app.get("/health")
async def health_check():
    from .services.ai_manager import get_ai_manager
    ai_manager = get_ai_manager()

    # Get database info
    db_info = get_db_info()

    return {
        "status": "healthy",
        "version": settings.APP_VERSION,
        "providers": ai_manager.get_available_providers(),
        "models_count": len(ai_manager.get_available_models()),
        "database": {
            "exists": db_info.get("exists", False),
            "size_mb": db_info.get("size_mb", 0),
            "tables": db_info.get("tables", []),
            "record_counts": db_info.get("record_counts", {}),
        }
    }


# API info
@app.get("/api")
async def api_info():
    return {
        "version": "2.0.0",
        "endpoints": {
            "debate": "/api/debate",
            "models": "/api/models",
            "chat": "/api/chat",
            "settings": "/api/settings",
            "projects": "/api/projects",
            "diagrams": "/api/diagrams",
            "creator": "/api/creator",
            "upload": "/api/upload",
            "orchestrator": "/api/orchestrator",
            "config": "/api/config",
            "external": "/api/external",
            "runtime": "/api/runtime",
        },
        "docs": "/docs",
    }


# OPTIONS handler for all routes (CORS preflight)
@app.options("/{full_path:path}")
async def options_handler(full_path: str):
    return Response(
        content="",
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS, PATCH",
            "Access-Control-Allow-Headers": "*",
            "Access-Control-Max-Age": "86400",
        }
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        workers=1 if settings.DEBUG else settings.WORKERS,
    )
