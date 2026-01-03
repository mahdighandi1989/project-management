"""
نقطه ورود اصلی برنامه
FastAPI Application
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
import logging
import time
from contextlib import asynccontextmanager

from .core.config import settings
from .api.routes import debate, models, chat, settings as settings_routes
from .api.routes import projects, diagrams

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

    yield

    # Shutdown
    logger.info("👋 Shutting down...")
    from .services.ai_manager import get_ai_manager
    ai_manager = get_ai_manager()
    await ai_manager.close()


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

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Middleware برای logging
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
        content={"detail": "Internal server error", "error": str(exc) if settings.DEBUG else None}
    )


# ثبت routes
app.include_router(debate.router, prefix="/api")
app.include_router(models.router, prefix="/api")
app.include_router(chat.router, prefix="/api")
app.include_router(settings_routes.router, prefix="/api")
app.include_router(projects.router, prefix="/api")
app.include_router(diagrams.router, prefix="/api")


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
        },
        "docs": "/docs",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        workers=1 if settings.DEBUG else settings.WORKERS,
    )
