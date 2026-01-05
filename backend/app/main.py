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
from .api.routes import debate, models, chat, settings as settings_routes
from .api.routes import projects, diagrams, creator, upload, orchestrator
from .api.routes import config, external

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

    # بررسی API keys
    providers = settings.get_available_providers()
    available = [k for k, v in providers.items() if v]
    logger.info(f"✅ Available providers: {', '.join(available) or 'None'}")

    # بارگذاری داده‌ها از GitHub (مهم برای persistence)
    await initialize_persistent_data()

    yield

    # Shutdown
    logger.info("👋 Shutting down...")
    from .services.ai_manager import get_ai_manager
    ai_manager = get_ai_manager()
    await ai_manager.close()


async def initialize_persistent_data():
    """بارگذاری داده‌های ذخیره شده از GitHub در startup"""
    try:
        from .services.github_storage import get_github_storage
        from .services.project_service import get_project_service
        from .services.smart_orchestrator import get_smart_orchestrator
        from .services.ai_manager import get_ai_manager
        from .services.creator_engine import get_creator_engine

        # اول GitHub storage را بررسی کن
        github_storage = get_github_storage()
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
            ai_manager = get_ai_manager()
            creator_engine = get_creator_engine()
            creator_engine.initialize(ai_manager)
            orchestrator.initialize(ai_manager, project_service, creator_engine)
            orchestrator.integrator.set_github_storage(github_storage)

        # بارگذاری workflow های ذخیره شده
        await load_workflows_from_github(github_storage, orchestrator)

        logger.info("✅ Persistent data loaded successfully")

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

    response = await call_next(request)

    process_time = time.time() - start_time
    logger.info(
        f"{request.method} {request.url.path} - {response.status_code} - {process_time:.3f}s"
    )

    response.headers["X-Process-Time"] = str(process_time)
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

    return {
        "status": "healthy",
        "version": settings.APP_VERSION,
        "providers": ai_manager.get_available_providers(),
        "models_count": len(ai_manager.get_available_models()),
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
