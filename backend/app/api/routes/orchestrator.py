"""
🎯 Smart Orchestrator API Routes
مسیرهای API برای هماهنگ‌کننده هوشمند
"""

from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Query, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import io
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/orchestrator", tags=["Smart Orchestrator"])


# =====================================
# Auto-Detection Helper Functions
# =====================================

def get_optimal_settings_for_file(filename: str, file_size: int) -> Dict[str, Any]:
    """
    تشخیص خودکار تنظیمات بهینه بر اساس نوع فایل و اندازه
    """
    extension = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
    size_mb = file_size / (1024 * 1024)

    # تنظیمات پیش‌فرض
    settings = {
        "max_tokens": 4000,
        "temperature": 0.7,
        "timeout": 120,
        "chunk_size": 50000,  # 50KB per chunk
        "recommended_model": "gpt-4o-mini",
        "analysis_type": "general",
        "file_category": "other"
    }

    # کد و برنامه‌نویسی
    code_extensions = {
        'py', 'js', 'ts', 'jsx', 'tsx', 'java', 'cpp', 'c', 'h', 'go', 'rs',
        'php', 'rb', 'swift', 'kt', 'mq4', 'mq5', 'mqh', 'sql', 'sh', 'bat',
        'vue', 'svelte', 'astro', 'graphql', 'proto'
    }
    if extension in code_extensions:
        settings.update({
            "max_tokens": 8000,
            "temperature": 0.2,  # کمتر برای کد
            "timeout": 180,
            "chunk_size": 100000,  # 100KB
            "recommended_model": "claude-3-5-sonnet-20241022" if size_mb > 1 else "gpt-4o",
            "analysis_type": "code_review",
            "file_category": "code"
        })

    # Trading/MetaTrader
    elif extension in {'mq4', 'mq5', 'mqh', 'ex4', 'ex5'}:
        settings.update({
            "max_tokens": 16000,  # بیشتر برای Expert Advisor ها
            "temperature": 0.1,
            "timeout": 300,
            "chunk_size": 150000,
            "recommended_model": "claude-3-5-sonnet-20241022",
            "analysis_type": "trading_code_analysis",
            "file_category": "trading"
        })

    # اسناد متنی
    elif extension in {'txt', 'md', 'rtf', 'tex'}:
        settings.update({
            "max_tokens": 4000,
            "temperature": 0.5,
            "timeout": 120,
            "recommended_model": "gpt-4o-mini",
            "analysis_type": "text_analysis",
            "file_category": "document"
        })

    # PDF و اسناد پیچیده
    elif extension in {'pdf', 'doc', 'docx', 'ppt', 'pptx'}:
        settings.update({
            "max_tokens": 8000,
            "temperature": 0.3,
            "timeout": 240,
            "recommended_model": "gpt-4o",  # برای اسناد پیچیده
            "analysis_type": "document_analysis",
            "file_category": "document"
        })

    # داده و JSON/YAML
    elif extension in {'json', 'yaml', 'yml', 'xml', 'csv'}:
        settings.update({
            "max_tokens": 8000,
            "temperature": 0.2,
            "timeout": 180,
            "recommended_model": "gpt-4o-mini",
            "analysis_type": "data_analysis",
            "file_category": "data"
        })

    # Excel
    elif extension in {'xlsx', 'xls'}:
        settings.update({
            "max_tokens": 16000,
            "temperature": 0.3,
            "timeout": 300,
            "recommended_model": "gpt-4o",
            "analysis_type": "spreadsheet_analysis",
            "file_category": "data"
        })

    # تصویر
    elif extension in {'jpg', 'jpeg', 'png', 'gif', 'webp', 'bmp', 'svg'}:
        settings.update({
            "max_tokens": 4000,
            "temperature": 0.5,
            "timeout": 120,
            "recommended_model": "gpt-4o",  # مدل با قابلیت vision
            "analysis_type": "image_analysis",
            "file_category": "image"
        })

    # صوت و ویدیو
    elif extension in {'mp3', 'wav', 'mp4', 'webm', 'avi', 'mov', 'mkv'}:
        settings.update({
            "max_tokens": 4000,
            "temperature": 0.5,
            "timeout": 300,
            "recommended_model": "whisper-1",  # برای صوت
            "analysis_type": "media_transcription",
            "file_category": "media"
        })

    # آرشیو
    elif extension in {'zip', 'tar', 'gz', 'rar', '7z'}:
        settings.update({
            "max_tokens": 2000,
            "temperature": 0.5,
            "timeout": 60,
            "recommended_model": "gpt-4o-mini",
            "analysis_type": "archive_listing",
            "file_category": "archive"
        })

    # تنظیم بر اساس حجم فایل
    if size_mb > 10:
        settings["timeout"] = max(settings["timeout"], 300)
        settings["max_tokens"] = max(settings["max_tokens"], 8000)
    if size_mb > 50:
        settings["timeout"] = 600
        settings["max_tokens"] = 16000
    if size_mb > 100:
        settings["max_tokens"] = 32000
        settings["recommended_model"] = "claude-3-5-sonnet-20241022"

    return settings


# =====================================
# Request/Response Models
# =====================================

class SmartSetupRequest(BaseModel):
    """درخواست راه‌اندازی هوشمند"""
    request: str  # درخواست کاربر به زبان ساده


class TaskExecuteRequest(BaseModel):
    """درخواست اجرای وظیفه"""
    project_id: str
    task: str
    category: str = "code_generation"  # TaskCategory


class EvaluateRequest(BaseModel):
    """درخواست ارزیابی"""
    task: str
    model_id: str
    output: str


class CompareModelsRequest(BaseModel):
    """درخواست مقایسه مدل‌ها"""
    task: str
    outputs: Dict[str, str]  # model_id -> output


class ModelSelectRequest(BaseModel):
    """درخواست انتخاب مدل"""
    category: str
    exclude: List[str] = []


class FileAnalysisRequest(BaseModel):
    """درخواست تحلیل فایل"""
    project_id: Optional[str] = None
    debate_id: Optional[str] = None
    analysis_type: str = "full"  # full, summary, code_review


# =====================================
# Helper Functions
# =====================================

def get_orchestrator():
    """دریافت instance هماهنگ‌کننده"""
    from ...services.smart_orchestrator import get_smart_orchestrator
    orchestrator = get_smart_orchestrator()

    if not orchestrator.is_initialized():
        # مقداردهی اولیه
        try:
            from ...services.ai_manager import get_ai_manager
            from ...services.project_service import get_project_service
            from ...services.creator_engine import get_creator_engine
            from ...services.github_storage import get_github_storage as _get_github

            ai_manager = get_ai_manager()
            project_service = get_project_service()
            creator_engine = get_creator_engine()
            creator_engine.initialize(ai_manager)

            # Initialize GitHub storage for project persistence
            github_storage = None
            try:
                github_storage = _get_github()
                project_service.initialize_github(github_storage)
                logger.info("GitHub storage initialized for project persistence")
            except Exception as gh_error:
                logger.warning(f"Could not initialize GitHub storage: {gh_error}")

            orchestrator.initialize(ai_manager, project_service, creator_engine)

            # Pass GitHub storage to integrator for saving generated files
            if github_storage and orchestrator.integrator:
                orchestrator.integrator.set_github_storage(github_storage)
                logger.info("GitHub storage set for integrator")
        except Exception as e:
            logger.error(f"Failed to initialize orchestrator: {e}")
            raise HTTPException(status_code=500, detail=f"خطا در مقداردهی سیستم: {str(e)}")

    return orchestrator


def get_github_storage():
    """دریافت سرویس GitHub"""
    from ...services.github_storage import get_github_storage as _get_github
    return _get_github()


# =====================================
# Smart Setup Endpoints
# =====================================

@router.post("/smart-setup")
async def smart_project_setup(request: SmartSetupRequest):
    """
    راه‌اندازی هوشمند پروژه از یک درخواست ساده

    از یک توضیح ساده، پروژه را با فازها، تکنولوژی‌ها و ساختار کامل ایجاد می‌کند.
    """
    try:
        orchestrator = get_orchestrator()
        result = await orchestrator.smart_setup(request.request)
        return result
    except Exception as e:
        logger.error(f"Error in smart setup: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class AutoBuildRequest(BaseModel):
    """درخواست ساخت خودکار"""
    project_id: str
    github_repo: Optional[str] = None
    check_runtime: bool = True  # بررسی قابلیت اجرا


@router.post("/auto-build")
async def auto_build_project(request: AutoBuildRequest):
    """
    ساخت خودکار پروژه با نظارت مستمر

    - اجرای تمام فازها به صورت خودکار
    - تولید کد و فایل‌ها
    - ذخیره در Creator Engine
    - نظارت و ارزیابی مستمر
    - 🆕 بررسی قابلیت اجرا و ایجاد نیازمندی‌ها
    """
    try:
        orchestrator = get_orchestrator()
        result = await orchestrator.auto_build(request.project_id, request.github_repo)

        # 🆕 بررسی قابلیت اجرا برای پروژه‌های تکمیل شده
        if request.check_runtime and result.get("success"):
            runtime_check = await check_and_prepare_runtime(request.project_id)
            result["runtime"] = runtime_check

        return result
    except Exception as e:
        logger.error(f"Error in auto build: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def check_and_prepare_runtime(project_id: str) -> Dict[str, Any]:
    """بررسی و آماده‌سازی محیط اجرا برای پروژه"""
    try:
        from ...services.capability_detector import get_capability_detector
        from ...services.runtime_executor import get_runtime_executor
        from ...services.project_service import get_project_service

        # دریافت اطلاعات پروژه
        project_service = get_project_service()
        project_data = project_service.get_project(project_id)

        if not project_data.get("success"):
            return {"checked": False, "error": "پروژه یافت نشد"}

        project = project_data["project"]
        project_type = project.get("type", "custom")

        # دریافت فایل‌های پروژه
        github_storage = get_github_storage()
        files = []

        if github_storage and github_storage.token:
            try:
                import base64
                project_files = await github_storage.get_project_files(project_id)
                for folder_type, folder_files in project_files.get("files", {}).items():
                    for f in folder_files:
                        if f.get("name") and f["name"] != ".gitkeep":
                            # خواندن محتوا
                            file_path = f"projects/{project_id}/{folder_type}/{f['name']}"
                            result = await github_storage.get_file(file_path)
                            content = ""
                            if result.get("success") and result.get("content"):
                                content = base64.b64decode(result["content"]).decode('utf-8', errors='replace')
                            files.append({
                                "name": f["name"],
                                "folder": folder_type,
                                "content": content
                            })
            except Exception as e:
                logger.warning(f"Could not load files for runtime check: {e}")

        if not files:
            return {"checked": False, "error": "فایلی برای بررسی وجود ندارد"}

        # تحلیل نیازمندی‌ها
        detector = get_capability_detector()
        if not detector._initialized:
            detector.initialize(github_storage)

        requirements = await detector.analyze_project_requirements(
            project_id, project_type, files
        )

        # بررسی در دسترس بودن Docker
        executor = get_runtime_executor()
        if not executor._initialized:
            executor.initialize(github_storage)

        docker_available = executor.is_docker_available()

        # نتیجه بررسی
        result = {
            "checked": True,
            "can_run": requirements.can_run,
            "can_run_with_docker": requirements.can_run_with_docker,
            "docker_available": docker_available,
            "missing_capabilities": [
                {"name": cap.name, "type": cap.type.value, "docker_image": cap.docker_image}
                for cap in requirements.missing_capabilities
            ],
            "notes": requirements.notes,
            "message": None
        }

        if not docker_available:
            result["message"] = "⚠️ Docker در این سرور در دسترس نیست. پروژه‌ها فقط در محیط محلی با Docker قابل اجرا هستند."

        # اگر نیاز به ارتقا داره و Docker موجوده، image ها رو pull کن

        if requirements.missing_capabilities and executor.is_docker_available():
            pulled_images = []
            for cap in requirements.missing_capabilities:
                if cap.docker_image:
                    try:
                        import asyncio
                        process = await asyncio.create_subprocess_exec(
                            "docker", "pull", cap.docker_image,
                            stdout=asyncio.subprocess.PIPE,
                            stderr=asyncio.subprocess.PIPE
                        )
                        await asyncio.wait_for(process.communicate(), timeout=300)
                        if process.returncode == 0:
                            pulled_images.append(cap.docker_image)
                            logger.info(f"Pulled Docker image: {cap.docker_image}")
                    except Exception as e:
                        logger.warning(f"Could not pull {cap.docker_image}: {e}")

            result["pulled_images"] = pulled_images
            result["can_run_with_docker"] = len(pulled_images) == len(requirements.missing_capabilities)

        # ذخیره نیازمندی‌ها برای ارتقای بعدی
        if requirements.missing_capabilities and not result.get("can_run_with_docker"):
            await detector.save_upgrade_requirements(project_id, requirements)
            result["upgrade_requested"] = True

        return result

    except Exception as e:
        logger.error(f"Error checking runtime: {e}")
        return {"checked": False, "error": str(e)}


class StartWorkflowRequest(BaseModel):
    """درخواست شروع workflow"""
    project_id: str
    auto_execute: bool = True  # اجرای خودکار فازها
    use_competition: bool = True  # حالت رقابتی چند مدل
    num_models: int = 3  # تعداد مدل‌ها در رقابت


@router.post("/start-workflow")
async def start_project_workflow(request: StartWorkflowRequest):
    """
    شروع workflow پروژه با رقابت چند مدل

    - انتخاب بهترین مدل‌ها
    - اجرای موازی و رقابت
    - انتخاب بهترین خروجی
    - گزارش پیشرفت و نتایج رقابت
    """
    try:
        orchestrator = get_orchestrator()

        # بررسی وجود پروژه
        project_data = orchestrator.integrator.project_service.get_project(request.project_id)
        if not project_data.get("success"):
            raise HTTPException(status_code=404, detail="پروژه یافت نشد")

        project = project_data["project"]
        phases = project.get("phases", [])

        if not phases:
            raise HTTPException(status_code=400, detail="پروژه فازی ندارد")

        # تولید estimated_files از فازها
        estimated_files = []
        for phase in phases:
            if isinstance(phase, dict):
                for step in phase.get("steps", []):
                    # اگر step شامل نام فایل باشه
                    if any(ext in step.lower() for ext in ['.py', '.js', '.ts', '.tsx', '.json', '.md', '.html', '.css']):
                        estimated_files.append(step)

        # اگر فایلی پیدا نشد، فایل‌های پیش‌فرض بر اساس نوع پروژه
        if not estimated_files:
            project_type = project.get("project_type", "custom")
            if project_type == "web_app":
                estimated_files = ["README.md", "main.py", "requirements.txt", "app.py"]
            elif project_type == "api_service":
                estimated_files = ["README.md", "main.py", "requirements.txt", "routes.py"]
            else:
                estimated_files = ["README.md", "main.py", "requirements.txt"]

        # اگر workflow فعال نیست، ایجاد کن
        if request.project_id not in orchestrator.integrator.active_workflows:
            orchestrator.integrator.active_workflows[request.project_id] = {
                "analysis": {
                    "project_name": project.get("name"),
                    "description": project.get("description", ""),
                    "project_type": project.get("project_type", "custom"),
                    "goal": project.get("goal", ""),
                    "phases": phases,
                    "technologies": [],  # TODO: extract from project
                    "features": [],
                    "estimated_files": estimated_files
                },
                "status": "initialized",
                "current_phase": 0,
                "started_at": None
            }

        # اگر auto_execute فعال است، شروع ساخت خودکار با رقابت
        if request.auto_execute:
            result = await orchestrator.integrator.auto_build_project(
                request.project_id,
                use_competition=request.use_competition,
                num_models=request.num_models
            )
            return result

        return {
            "success": True,
            "project_id": request.project_id,
            "phases_count": len(phases),
            "current_phase": 0,
            "message": "Workflow آماده اجرا است"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting workflow: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/workflow-status/{project_id}")
async def get_workflow_status(project_id: str):
    """
    وضعیت workflow پروژه با جزئیات پیشرفت
    """
    try:
        orchestrator = get_orchestrator()

        # اول از memory چک کن، اگه نبود از GitHub بارگذاری کن
        workflow = await orchestrator.integrator.get_workflow_with_fallback(project_id)
        if not workflow:
            return {
                "success": True,
                "project_id": project_id,
                "status": "not_started",
                "message": "Workflow هنوز شروع نشده"
            }

        return {
            "success": True,
            "project_id": project_id,
            "status": workflow.get("status"),
            "current_phase": workflow.get("current_phase", 0),
            "started_at": workflow.get("started_at"),
            "completed_at": workflow.get("completed_at"),
            "progress": workflow.get("progress", 0),
            "current_step": workflow.get("current_step", ""),
            "current_file": workflow.get("current_file", ""),
            "current_file_index": workflow.get("current_file_index", 0),
            "total_files": workflow.get("total_files", 0),
            "results": workflow.get("results", []),
            "analysis": workflow.get("analysis", {})
        }

    except Exception as e:
        logger.error(f"Error getting workflow status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/generated-files/{project_id}")
async def get_generated_files(project_id: str):
    """
    دریافت لیست فایل‌های تولید شده پروژه - مستقیم از GitHub
    """
    try:
        github_storage = get_github_storage()
        files = []

        # 🆕 مستقیم از GitHub بخون
        if github_storage and github_storage.token:
            try:
                project_files = await github_storage.get_project_files(project_id)
                for folder_type, folder_files in project_files.get("files", {}).items():
                    for f in folder_files:
                        if f.get("name") and f["name"] != ".gitkeep":
                            files.append({
                                "file": f["name"],
                                "folder": folder_type,
                                "path": f"{folder_type}/{f['name']}",
                                "size": f.get("size", 0),
                                "url": f.get("url", ""),
                                "download_url": f.get("download_url", ""),
                                "github_saved": True,
                                "has_content": True
                            })
            except Exception as e:
                logger.warning(f"Could not load files from GitHub: {e}")

        # اگر از GitHub خالی بود، از workflow بخون
        if not files:
            orchestrator = get_orchestrator()
            workflow = await orchestrator.integrator.get_workflow_with_fallback(project_id)
            if workflow:
                results = workflow.get("results", [])
                for r in results:
                    if r.get("status") == "created":
                        files.append({
                            "file": r.get("file"),
                            "score": r.get("score", 0),
                            "github_saved": r.get("github_saved", False),
                            "has_content": bool(r.get("content")),
                            "content_preview": r.get("content_preview", "")
                        })

        return {
            "success": True,
            "project_id": project_id,
            "files_count": len(files),
            "files": files,
            "source": "github" if files and files[0].get("download_url") else "workflow"
        }

    except Exception as e:
        logger.error(f"Error getting generated files: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/project-files/{project_id}")
async def get_project_files_for_export(project_id: str, recursive: bool = False):
    """
    دریافت ساختار فایل‌های پروژه برای export به StackBlitz/Replit/Colab
    Returns files grouped by folder with metadata
    recursive=True برای دریافت همه فایل‌ها شامل زیرپوشه‌ها
    """
    try:
        github_storage = get_github_storage()
        files_by_folder: Dict[str, List] = {}

        if github_storage and github_storage.token:
            try:
                if recursive:
                    project_files = await github_storage.get_project_files_recursive(project_id)
                else:
                    project_files = await github_storage.get_project_files(project_id)
                for folder_type, folder_files in project_files.get("files", {}).items():
                    files_by_folder[folder_type] = []
                    for f in folder_files:
                        if f.get("name") and f["name"] != ".gitkeep":
                            files_by_folder[folder_type].append({
                                "name": f["name"],
                                "size": f.get("size", 0),
                                "path": f"{folder_type}/{f['name']}"
                            })
            except Exception as e:
                logger.warning(f"Could not load project files from GitHub: {e}")

        return {
            "success": True,
            "project_id": project_id,
            "files": files_by_folder
        }

    except Exception as e:
        logger.error(f"Error getting project files: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/file-content/{project_id}/{file_path:path}")
async def get_file_content(project_id: str, file_path: str):
    """
    دریافت محتوای یک فایل تولید شده
    """
    try:
        orchestrator = get_orchestrator()

        # اول از memory چک کن
        workflow = orchestrator.integrator.active_workflows.get(project_id)
        if workflow:
            results = workflow.get("results", [])
            for r in results:
                if r.get("file") == file_path and r.get("status") == "created":
                    content = r.get("content")
                    if content:
                        return {
                            "success": True,
                            "file": file_path,
                            "content": content,
                            "score": r.get("score", 0),
                            "github_saved": r.get("github_saved", False),
                            "winner_model": r.get("winner_model"),
                            "source": "memory"
                        }

        # اگه در memory نبود یا محتوا نداشت، از GitHub بخون
        github_storage = get_github_storage()
        if github_storage:
            try:
                import base64
                # Try different paths - first the direct path, then generated folder
                paths_to_try = [
                    f"projects/{project_id}/{file_path}",  # Direct: projects/proj_xxx/src/file.py
                    f"projects/{project_id}/generated/{file_path}",  # Legacy: projects/proj_xxx/generated/file.py
                ]

                for github_path in paths_to_try:
                    result = await github_storage.get_file(github_path)
                    if result.get("success") and result.get("content"):
                        content = base64.b64decode(result["content"]).decode('utf-8', errors='replace')
                        return {
                            "success": True,
                            "file": file_path,
                            "content": content,
                            "score": 0,
                            "github_saved": True,
                            "source": "github"
                        }
            except Exception as e:
                logger.warning(f"Could not load file from GitHub: {e}")

        return {
            "success": False,
            "error": "فایل یافت نشد"
        }

    except Exception as e:
        logger.error(f"Error getting file content: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class SaveFileRequest(BaseModel):
    """درخواست ذخیره فایل"""
    project_id: str
    file_name: str
    content: str
    folder: str = "generated"


@router.post("/save-file")
async def save_generated_file(request: SaveFileRequest):
    """
    ذخیره یک فایل در پروژه (برای Colab notebook و غیره)

    Returns:
        - success: آیا ذخیره شد
        - github_url: آدرس فایل در GitHub
        - github_path: مسیر فایل
        - owner: صاحب repo
        - repo: نام repo
    """
    try:
        github_storage = get_github_storage()
        if not github_storage or not github_storage.token:
            raise HTTPException(status_code=400, detail="GitHub storage not configured")

        # ذخیره فایل
        file_path = f"projects/{request.project_id}/{request.folder}/{request.file_name}"
        result = await github_storage.save_project_file(
            request.project_id,
            request.content.encode('utf-8'),
            request.file_name,
            request.folder
        )

        if result.get("success"):
            # استخراج اطلاعات repo - مستقیم از github_storage
            owner = github_storage.owner
            repo = github_storage.repo

            return {
                "success": True,
                "github_url": result.get("url"),
                "github_path": file_path,
                "owner": owner,
                "repo": repo,
                "file_name": request.file_name
            }
        else:
            return {"success": False, "error": result.get("error", "Unknown error")}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error saving file: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/download-project/{project_id}")
async def download_project(project_id: str):
    """
    دانلود کل پروژه به صورت ZIP

    Returns:
        - Zip file containing all generated files
        - OR a JSON with download links to GitHub
    """
    import zipfile
    import base64
    import re
    from urllib.parse import quote

    try:
        github_storage = get_github_storage()

        if not github_storage or not github_storage.token:
            raise HTTPException(status_code=400, detail="GitHub storage not configured")

        # دریافت اطلاعات پروژه
        from ...services.project_service import get_project_service
        project_service = get_project_service()
        project_data = project_service.get_project(project_id)

        if not project_data.get("success"):
            raise HTTPException(status_code=404, detail="Project not found")

        project = project_data["project"]
        # استفاده از project_id برای نام فایل (بدون کاراکترهای فارسی)
        safe_name = re.sub(r'[^\w\-_]', '_', project_id)

        # دریافت فایل‌ها از GitHub
        project_files = await github_storage.get_project_files(project_id)
        all_files = []

        for folder_type, folder_files in project_files.get("files", {}).items():
            for f in folder_files:
                if f.get("name") and f["name"] != ".gitkeep":
                    all_files.append({
                        "folder": folder_type,
                        "name": f["name"],
                        "download_url": f.get("download_url", "")
                    })

        if not all_files:
            return {
                "success": False,
                "error": "No files to download"
            }

        # ایجاد ZIP در حافظه
        zip_buffer = io.BytesIO()

        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            # اضافه کردن README (به انگلیسی برای سازگاری)
            project_type = project.get('type', 'custom')
            readme_content = f"""# {project.get('name', 'Project')}

{project.get('description', '')}

## Project Type
{project_type}

## How to Run

### Prerequisites
- Node.js 18+ (for web projects)
- Python 3.9+ (for API projects)
- Git

### Steps
1. Extract the ZIP file
2. Open terminal in the project folder
3. Install dependencies:

For Node.js:
```bash
npm install
npm run dev
```

For Python:
```bash
pip install -r requirements.txt
python main.py
```

4. Open browser: http://localhost:3000 or http://localhost:8000

## Generated by
AI Creator Engine
"""
            zip_file.writestr("README.md", readme_content.encode('utf-8'))

            # دانلود و اضافه کردن هر فایل
            for file_info in all_files:
                try:
                    # خواندن محتوای فایل از GitHub
                    file_path = f"projects/{project_id}/{file_info['folder']}/{file_info['name']}"
                    result = await github_storage.get_file(file_path)

                    if result.get("success") and result.get("content"):
                        content = base64.b64decode(result["content"])
                        # ذخیره در پوشه مناسب
                        zip_path = f"{file_info['folder']}/{file_info['name']}"
                        zip_file.writestr(zip_path, content)
                except Exception as e:
                    logger.warning(f"Could not add file {file_info['name']}: {e}")

        zip_buffer.seek(0)

        # برگرداندن ZIP با نام ASCII-safe
        filename = f"{safe_name}.zip"
        return StreamingResponse(
            zip_buffer,
            media_type="application/zip",
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading project: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/project-summary/{project_id}")
async def get_project_summary(project_id: str):
    """
    خلاصه کامل پروژه - وضعیت، فایل‌ها، و راهنمای اجرا
    """
    try:
        from ...services.project_service import get_project_service
        project_service = get_project_service()
        github_storage = get_github_storage()

        project_data = project_service.get_project(project_id)
        if not project_data.get("success"):
            raise HTTPException(status_code=404, detail="پروژه یافت نشد")

        project = project_data["project"]
        phases = project.get("phases", [])

        # شمارش فازها
        completed_phases = sum(1 for p in phases if p.get("status") == "completed")
        total_phases = len(phases)

        # دریافت فایل‌ها
        files = []
        github_repo_url = None

        if github_storage and github_storage.token:
            try:
                project_files = await github_storage.get_project_files(project_id)
                for folder_type, folder_files in project_files.get("files", {}).items():
                    for f in folder_files:
                        if f.get("name") and f["name"] != ".gitkeep":
                            files.append({
                                "name": f["name"],
                                "folder": folder_type,
                                "size": f.get("size", 0)
                            })

                # لینک به GitHub repo
                github_repo_url = f"https://github.com/{github_storage.owner}/{github_storage.repo}/tree/{github_storage.branch}/{github_storage.base_path}/projects/{project_id}"
            except Exception as e:
                logger.warning(f"Could not load files: {e}")

        # تشخیص وضعیت پروژه
        if completed_phases == 0:
            status = "not_started"
            status_text = "هنوز شروع نشده"
            next_action = "ابتدا روی 'ساخت خودکار' کلیک کنید"
        elif completed_phases < total_phases:
            status = "in_progress"
            status_text = f"در حال پیشرفت ({completed_phases}/{total_phases} فاز)"
            next_action = "روی 'ساخت خودکار' کلیک کنید تا فایل‌های فاز بعدی ساخته شود"
        else:
            status = "completed"
            status_text = "تکمیل شده - آماده دانلود و اجرا"
            next_action = "پروژه را دانلود کرده و در محیط توسعه اجرا کنید"

        return {
            "success": True,
            "project": {
                "id": project_id,
                "name": project.get("name"),
                "description": project.get("description"),
                "type": project.get("type"),
                "status": status,
                "status_text": status_text,
                "progress": int((completed_phases / total_phases) * 100) if total_phases > 0 else 0
            },
            "phases": {
                "total": total_phases,
                "completed": completed_phases,
                "current": phases[completed_phases] if completed_phases < total_phases else None
            },
            "files": {
                "count": len(files),
                "list": files
            },
            "github": {
                "url": github_repo_url,
                "connected": bool(github_storage and github_storage.token)
            },
            "next_action": next_action,
            "can_download": len(files) > 0,
            "download_url": f"/api/orchestrator/download-project/{project_id}" if files else None,

            # راهنمای اجرا
            "run_instructions": {
                "title": "چطور پروژه رو اجرا کنم؟",
                "steps": [
                    "۱. پروژه را دانلود کنید (دکمه دانلود)",
                    "۲. فایل ZIP را extract کنید",
                    "۳. ترمینال باز کنید و به پوشه پروژه بروید",
                    "۴. وابستگی‌ها را نصب کنید (npm install یا pip install)",
                    "۵. پروژه را اجرا کنید (npm run dev یا python main.py)",
                    "۶. در مرورگر localhost:3000 یا localhost:8000 را باز کنید"
                ],
                "note": "این پروژه فقط کدهای تولید شده است. برای اجرا باید روی کامپیوتر خودتان یا یک سرور نصب شود."
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting project summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/execute-task")
async def execute_monitored_task(request: TaskExecuteRequest):
    """
    اجرای وظیفه با نظارت و بازخورد

    - انتخاب هوشمند مدل
    - اجرای وظیفه
    - ارزیابی توسط مدل ناظر
    - بررسی انحراف از هدف
    - تلاش مجدد در صورت نیاز
    """
    try:
        from ...services.smart_orchestrator import TaskCategory

        orchestrator = get_orchestrator()
        category = TaskCategory(request.category)

        result = await orchestrator.execute_task(
            request.project_id,
            request.task,
            category
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"دسته نامعتبر: {request.category}")
    except Exception as e:
        logger.error(f"Error executing task: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =====================================
# Evaluation Endpoints
# =====================================

@router.post("/evaluate")
async def evaluate_output(request: EvaluateRequest):
    """
    ارزیابی خروجی یک مدل

    معیارها:
    - صحت (accuracy)
    - کامل بودن (completeness)
    - مرتبط بودن (relevance)
    - وضوح (clarity)
    - عملی بودن (feasibility)
    """
    try:
        orchestrator = get_orchestrator()
        evaluation = await orchestrator.evaluate(
            request.task,
            request.model_id,
            request.output
        )

        return {
            "success": True,
            "evaluation": {
                "task_id": evaluation.task_id,
                "model_id": evaluation.model_id,
                "evaluator": evaluation.evaluator_model_id,
                "scores": evaluation.scores,
                "overall_score": evaluation.overall_score,
                "feedback": evaluation.feedback,
                "suggestions": evaluation.suggestions,
                "is_acceptable": evaluation.is_acceptable
            }
        }
    except Exception as e:
        logger.error(f"Error evaluating: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/compare-models")
async def compare_model_outputs(request: CompareModelsRequest):
    """
    مقایسه خروجی چند مدل و رتبه‌بندی

    - ارزیابی هر خروجی
    - رتبه‌بندی مدل‌ها
    - انتخاب بهترین
    """
    try:
        orchestrator = get_orchestrator()
        result = await orchestrator.compare_models(request.task, request.outputs)
        return result
    except Exception as e:
        logger.error(f"Error comparing: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =====================================
# Model Selection Endpoints
# =====================================

@router.post("/select-model")
async def select_best_model(request: ModelSelectRequest):
    """
    انتخاب بهترین مدل برای یک وظیفه

    بر اساس:
    - نوع وظیفه
    - تاریخچه عملکرد
    - در دسترس بودن
    """
    try:
        from ...services.smart_orchestrator import TaskCategory

        orchestrator = get_orchestrator()
        category = TaskCategory(request.category)

        model_id, confidence = orchestrator.select_model(category, request.exclude)

        return {
            "success": True,
            "model_id": model_id,
            "confidence": confidence,
            "category": request.category
        }
    except ValueError:
        raise HTTPException(status_code=400, detail=f"دسته نامعتبر: {request.category}")
    except Exception as e:
        logger.error(f"Error selecting model: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/model-categories")
async def get_task_categories():
    """لیست دسته‌بندی‌های وظایف"""
    from ...services.smart_orchestrator import TaskCategory

    return {
        "categories": [
            {"id": cat.value, "name": cat.name}
            for cat in TaskCategory
        ]
    }


# =====================================
# File Upload & Analysis
# =====================================

@router.post("/upload-for-analysis")
async def upload_file_for_analysis(
    file: UploadFile = File(...),
    project_id: Optional[str] = Form(default=None),
    debate_id: Optional[str] = Form(default=None),
    analysis_type: str = Form(default="full"),
    store_in_github: bool = Form(default=True)
):
    """
    آپلود فایل برای تحلیل با AI

    - ذخیره در storage محلی یا GitHub
    - تقسیم فایل‌های بزرگ
    - تحلیل محتوا با مدل مناسب
    """
    try:
        from ...services.storage_service import get_storage_service
        from ...services.smart_orchestrator import FileChunker, TaskCategory

        content = await file.read()
        filename = file.filename
        extension = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''

        # بررسی نیاز به تقسیم
        needs_chunking = FileChunker.should_chunk(len(content), f".{extension}")

        # ذخیره محلی
        storage = get_storage_service()
        category = "debates" if debate_id else "projects" if project_id else "attachments"
        subcategory = debate_id or project_id

        local_meta = await storage.save_file(
            content=content,
            original_name=filename,
            category=category,
            subcategory=subcategory,
            tags=["uploaded", "for_analysis"]
        )

        # تشخیص خودکار تنظیمات بهینه
        optimal_settings = get_optimal_settings_for_file(filename, len(content))

        result = {
            "success": True,
            "file_id": local_meta.id,
            "filename": filename,
            "size": len(content),
            "size_mb": round(len(content) / (1024 * 1024), 2),
            "needs_chunking": needs_chunking,
            "local_path": local_meta.relative_path,
            "optimal_settings": optimal_settings
        }

        # ذخیره در GitHub
        if store_in_github:
            github = get_github_storage()
            connection = await github.check_connection()

            if connection.get("success"):
                if needs_chunking:
                    gh_result = await github.upload_large_file(
                        content,
                        f"{category}/{subcategory}/uploaded/{filename}"
                    )
                else:
                    if debate_id:
                        gh_result = await github.save_debate_file(
                            debate_id, content, filename, "uploaded"
                        )
                    elif project_id:
                        gh_result = await github.save_project_file(
                            project_id, content, filename, "source"
                        )
                    else:
                        gh_result = await github.upload_file(
                            content, f"uploads/{filename}"
                        )

                result["github"] = gh_result

        # تحلیل اولیه
        if analysis_type != "none":
            orchestrator = get_orchestrator()

            # انتخاب دسته مناسب
            if extension in ['py', 'js', 'ts', 'java', 'cpp', 'go']:
                task_category = TaskCategory.CODE_REVIEW
            elif extension in ['jpg', 'png', 'gif', 'webp']:
                task_category = TaskCategory.IMAGE_ANALYSIS
            else:
                task_category = TaskCategory.FILE_ANALYSIS

            model_id, _ = orchestrator.select_model(task_category)
            result["suggested_model"] = model_id
            result["analysis_category"] = task_category.value

        return result

    except Exception as e:
        logger.error(f"Error uploading file: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/analyze-file/{file_id}")
async def analyze_uploaded_file(
    file_id: str,
    analysis_prompt: str = Form(default="این فایل را کامل تحلیل کن"),
    project_id: Optional[str] = Form(default=None)
):
    """تحلیل فایل آپلود شده"""
    try:
        from ...services.storage_service import get_storage_service
        from ...services.smart_orchestrator import TaskCategory

        storage = get_storage_service()
        file_data = await storage.get_file(file_id)

        if not file_data:
            raise HTTPException(status_code=404, detail="فایل یافت نشد")

        content, meta = file_data
        orchestrator = get_orchestrator()

        # تعیین نوع تحلیل
        extension = meta.original_name.rsplit('.', 1)[-1].lower() if '.' in meta.original_name else ''

        if extension in ['py', 'js', 'ts', 'java']:
            category = TaskCategory.CODE_REVIEW
            prompt = f"""کد زیر را کامل بررسی کن:

نام فایل: {meta.original_name}

```
{content.decode('utf-8', errors='replace')[:8000]}
```

{analysis_prompt}

موارد زیر را بررسی کن:
1. کیفیت کد
2. باگ‌های احتمالی
3. پیشنهادات بهبود
4. امنیت
5. کارایی"""
        else:
            category = TaskCategory.FILE_ANALYSIS
            prompt = f"""فایل زیر را تحلیل کن:

نام: {meta.original_name}
نوع: {meta.mime_type}
سایز: {meta.size} bytes

محتوا:
{content.decode('utf-8', errors='replace')[:8000]}

{analysis_prompt}"""

        if project_id:
            result = await orchestrator.execute_task(project_id, prompt, category)
        else:
            model_id, _ = orchestrator.select_model(category)

            from ...services.ai_manager import get_ai_manager
            from ...services.ai_base import Message
            ai_manager = get_ai_manager()

            response = await ai_manager.generate(
                model_id=model_id,
                messages=[Message(role="user", content=prompt)],
                max_tokens=4000
            )

            if response.content and not response.error:
                result = {
                    "success": True,
                    "analysis": response.content,
                    "model_used": model_id
                }
            else:
                result = {"success": False, "error": response.error or "خطا در تحلیل"}

        return {
            "success": True,
            "file_id": file_id,
            "filename": meta.original_name,
            "analysis_result": result
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error analyzing file: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =====================================
# GitHub Integration
# =====================================

@router.get("/github/status")
async def github_connection_status():
    """وضعیت اتصال به GitHub"""
    try:
        github = get_github_storage()
        return await github.check_connection()
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.post("/github/setup-folders")
async def setup_github_folders(
    entity_type: str = Form(...),  # debates, projects
    entity_id: str = Form(...)
):
    """ایجاد ساختار پوشه در GitHub"""
    try:
        github = get_github_storage()
        connection = await github.check_connection()

        if not connection.get("success"):
            raise HTTPException(status_code=400, detail="اتصال به GitHub برقرار نیست")

        result = await github.create_folder_structure(entity_type, entity_id)
        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error setting up folders: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/github/files/{entity_type}/{entity_id}")
async def get_github_files(entity_type: str, entity_id: str):
    """لیست فایل‌های یک موجودیت در GitHub"""
    try:
        github = get_github_storage()

        if entity_type == "debates":
            return await github.get_debate_files(entity_id)
        elif entity_type == "projects":
            return await github.get_project_files(entity_id)
        else:
            raise HTTPException(status_code=400, detail="نوع نامعتبر")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting files: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/github/save-output")
async def save_output_to_github(
    entity_type: str = Form(...),
    entity_id: str = Form(...),
    filename: str = Form(...),
    content: str = Form(...),
    file_type: str = Form(default="generated")
):
    """ذخیره خروجی در GitHub"""
    try:
        github = get_github_storage()
        connection = await github.check_connection()

        if not connection.get("success"):
            raise HTTPException(status_code=400, detail="اتصال به GitHub برقرار نیست")

        content_bytes = content.encode('utf-8')

        if entity_type == "debates":
            result = await github.save_debate_file(
                entity_id, content_bytes, filename, file_type
            )
        elif entity_type == "projects":
            result = await github.save_project_file(
                entity_id, content_bytes, filename, file_type
            )
        else:
            raise HTTPException(status_code=400, detail="نوع نامعتبر")

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error saving output: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =====================================
# Performance & Stats
# =====================================

@router.get("/performance/models")
async def get_model_performance():
    """عملکرد مدل‌ها"""
    try:
        orchestrator = get_orchestrator()

        if not orchestrator.model_selector:
            return {"success": False, "error": "سیستم مقداردهی نشده"}

        performance = {}
        for model_id, perf in orchestrator.model_selector.performance_history.items():
            performance[model_id] = {
                "total_tasks": perf.total_tasks,
                "successful_tasks": perf.successful_tasks,
                "success_rate": round(perf.successful_tasks / perf.total_tasks * 100, 1) if perf.total_tasks > 0 else 0,
                "average_score": round(perf.average_score, 1),
                "scores_by_category": perf.scores_by_category,
                "last_used": perf.last_used
            }

        return {
            "success": True,
            "models": performance
        }

    except Exception as e:
        logger.error(f"Error getting performance: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_orchestrator_stats():
    """آمار کلی سیستم"""
    try:
        orchestrator = get_orchestrator()

        stats = {
            "initialized": orchestrator.is_initialized(),
            "model_count": len(orchestrator.model_selector.MODEL_SPECIALTIES) if orchestrator.model_selector else 0,
            "evaluations_count": len(orchestrator.supervisor.evaluation_history) if orchestrator.supervisor else 0,
            "active_workflows": len(orchestrator.integrator.active_workflows) if orchestrator.integrator else 0
        }

        return {"success": True, "stats": stats}

    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        return {"success": False, "error": str(e)}


# =====================================
# Smart Import Endpoints
# =====================================

def get_smart_import():
    """دریافت سرویس Smart Import"""
    from ...services.smart_import import get_smart_import_service
    service = get_smart_import_service()

    if not service.is_initialized():
        from ...services.ai_manager import get_ai_manager
        from ...services.project_service import get_project_service

        ai_manager = get_ai_manager()
        project_service = get_project_service()
        github_storage = get_github_storage()

        orchestrator = get_orchestrator()

        service.initialize(
            ai_manager=ai_manager,
            project_service=project_service,
            github_storage=github_storage,
            orchestrator=orchestrator
        )

    return service


@router.post("/smart-import/{project_id}")
async def smart_import_file(
    project_id: str,
    file: UploadFile = File(...),
    user_prompt: Optional[str] = Form(default=None),
    auto_apply: bool = Form(default=True)
):
    """
    وارد کردن هوشمند فایل به پروژه

    - تحلیل توسط چند مدل نخبه
    - تشخیص ارتباط با فازها
    - اعتبارسنجی و اصلاح خودکار
    - انتقال به پوشه مناسب
    """
    try:
        service = get_smart_import()

        content = await file.read()

        result = await service.analyze_and_import_file(
            project_id=project_id,
            file_content=content,
            file_name=file.filename,
            user_prompt=user_prompt,
            auto_apply=auto_apply
        )

        return result

    except Exception as e:
        logger.error(f"Error in smart import: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/smart-import-text/{project_id}")
async def smart_import_text(
    project_id: str,
    content: str = Form(...),
    file_name: str = Form(...),
    user_prompt: Optional[str] = Form(default=None),
    auto_apply: bool = Form(default=True)
):
    """
    وارد کردن هوشمند کد/متن به پروژه
    (برای paste کردن کد بدون آپلود فایل)
    """
    try:
        service = get_smart_import()

        result = await service.analyze_and_import_file(
            project_id=project_id,
            file_content=content.encode('utf-8'),
            file_name=file_name,
            user_prompt=user_prompt,
            auto_apply=auto_apply
        )

        return result

    except Exception as e:
        logger.error(f"Error in smart import text: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sync-project/{project_id}")
async def sync_project_files(project_id: str):
    """
    سینک کردن پروژه با GitHub
    بررسی فایل‌های جدید و پردازش خودکار
    """
    try:
        service = get_smart_import()
        result = await service.sync_project(project_id)
        return {"success": True, "project_id": project_id, **result}

    except Exception as e:
        logger.error(f"Error syncing project: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/process-github-file/{project_id}")
async def process_github_file(
    project_id: str,
    file_path: str = Form(...),
    user_prompt: Optional[str] = Form(default=None)
):
    """
    پردازش یک فایل مشخص از GitHub
    """
    try:
        service = get_smart_import()

        result = await service.process_file_from_github(
            project_id=project_id,
            file_path=file_path,
            user_prompt=user_prompt
        )

        return result

    except Exception as e:
        logger.error(f"Error processing GitHub file: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/start-auto-sync")
async def start_auto_sync(interval: int = Query(default=300, ge=60, le=3600)):
    """
    شروع sync خودکار با GitHub
    (هر X ثانیه بررسی فایل‌های جدید)
    """
    try:
        service = get_smart_import()
        await service.start_github_sync(interval)
        return {
            "success": True,
            "message": f"Auto sync started with interval {interval}s"
        }

    except Exception as e:
        logger.error(f"Error starting auto sync: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stop-auto-sync")
async def stop_auto_sync():
    """توقف sync خودکار"""
    try:
        service = get_smart_import()
        await service.stop_github_sync()
        return {"success": True, "message": "Auto sync stopped"}

    except Exception as e:
        logger.error(f"Error stopping auto sync: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =====================================
# Project State & Self-Awareness
# =====================================

@router.get("/project-state/{project_id}")
async def get_project_state(project_id: str):
    """
    تحلیل وضعیت پروژه - خودآگاهی کامل

    Returns:
        - existing_files: فایل‌های موجود
        - missing_files: فایل‌هایی که هنوز ساخته نشده‌اند
        - current_phase: فاز فعلی
        - overall_progress: درصد پیشرفت
        - recommendations: پیشنهادات
        - ready_for_next_phase: آیا آماده فاز بعدی است
    """
    try:
        orchestrator = get_orchestrator()
        state = await orchestrator.integrator.analyze_project_state(project_id)
        return state

    except Exception as e:
        logger.error(f"Error getting project state: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/smart-build/{project_id}")
async def smart_build_project(
    project_id: str,
    force_rebuild: bool = Query(default=False, description="بازسازی اجباری همه فایل‌ها")
):
    """
    ساخت هوشمند پروژه

    - فقط فایل‌های ناقص یا missing را می‌سازد
    - فایل‌های موجود را skip می‌کند
    - پیشرفت را به صورت خودکار بروزرسانی می‌کند
    """
    try:
        orchestrator = get_orchestrator()

        # اول وضعیت را بررسی کن
        state = await orchestrator.integrator.analyze_project_state(project_id)

        if not state.get("success", True):
            return state

        # اگر نیازی به ساخت نیست
        if not state.get("needs_building") and not force_rebuild:
            return {
                "success": True,
                "message": "همه فایل‌ها قبلاً ساخته شده‌اند!",
                "state": state
            }

        # شروع ساخت
        result = await orchestrator.integrator.auto_build_project(
            project_id,
            use_competition=True,
            num_models=3,
            force_rebuild=force_rebuild
        )

        return result

    except Exception as e:
        logger.error(f"Error in smart build: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/github-status")
async def get_github_status():
    """بررسی وضعیت اتصال به GitHub"""
    try:
        github_storage = get_github_storage()

        status = {
            "token_set": bool(github_storage.token),
            "owner": github_storage.owner or "NOT SET",
            "repo": github_storage.repo or "NOT SET",
            "branch": github_storage.branch,
            "base_path": github_storage.base_path
        }

        if github_storage.token and github_storage.owner and github_storage.repo:
            connection = await github_storage.check_connection()
            status["connected"] = connection.get("success", False)
            status["connection_error"] = connection.get("error")
            status["repo_info"] = connection.get("repo")

            # بررسی فایل‌های موجود
            try:
                folders = await github_storage.list_folder("projects")
                status["project_folders"] = [f.name for f in folders if f.type == "dir"]
            except Exception as e:
                status["list_error"] = str(e)
        else:
            status["connected"] = False
            status["connection_error"] = "GitHub credentials not configured"

        return status

    except Exception as e:
        logger.error(f"Error checking GitHub status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/deployment-guide/{project_id}")
async def get_deployment_guide(project_id: str):
    """
    راهنمای استقرار و اجرای پروژه

    Returns:
        - project_type: نوع پروژه
        - steps: مراحل اجرا
        - commands: دستورات مورد نیاز
        - requirements: پیش‌نیازها
    """
    try:
        from ...services.project_service import get_project_service
        project_service = get_project_service()
        project_data = project_service.get_project(project_id)

        if not project_data.get("success"):
            raise HTTPException(status_code=404, detail="پروژه یافت نشد")

        project = project_data["project"]
        project_type = project.get("type", "custom")

        # راهنمای بر اساس نوع پروژه
        guides = {
            "web_app": {
                "title": "راهنمای اجرای اپلیکیشن وب",
                "requirements": [
                    "Node.js نسخه 18 یا بالاتر",
                    "npm یا yarn",
                    "Git"
                ],
                "steps": [
                    {
                        "step": 1,
                        "title": "کلون کردن از GitHub",
                        "command": f"git clone https://github.com/YOUR_USERNAME/YOUR_REPO.git",
                        "description": "فایل‌های پروژه را از GitHub دانلود کنید"
                    },
                    {
                        "step": 2,
                        "title": "نصب وابستگی‌ها",
                        "command": "npm install",
                        "description": "وابستگی‌های پروژه را نصب کنید"
                    },
                    {
                        "step": 3,
                        "title": "اجرای محلی",
                        "command": "npm run dev",
                        "description": "پروژه را در محیط توسعه اجرا کنید"
                    },
                    {
                        "step": 4,
                        "title": "ساخت نسخه Production",
                        "command": "npm run build",
                        "description": "نسخه نهایی را بسازید"
                    }
                ],
                "deployment_options": [
                    {"name": "Vercel", "url": "https://vercel.com", "description": "استقرار رایگان و سریع"},
                    {"name": "Netlify", "url": "https://netlify.com", "description": "CI/CD خودکار"},
                    {"name": "Railway", "url": "https://railway.app", "description": "استقرار ساده"}
                ]
            },
            "api_service": {
                "title": "راهنمای اجرای سرویس API",
                "requirements": [
                    "Python 3.9 یا بالاتر",
                    "pip یا Poetry",
                    "Git"
                ],
                "steps": [
                    {
                        "step": 1,
                        "title": "کلون کردن از GitHub",
                        "command": f"git clone https://github.com/YOUR_USERNAME/YOUR_REPO.git",
                        "description": "فایل‌های پروژه را از GitHub دانلود کنید"
                    },
                    {
                        "step": 2,
                        "title": "ایجاد محیط مجازی",
                        "command": "python -m venv venv && source venv/bin/activate",
                        "description": "محیط مجازی پایتون بسازید"
                    },
                    {
                        "step": 3,
                        "title": "نصب وابستگی‌ها",
                        "command": "pip install -r requirements.txt",
                        "description": "وابستگی‌های پروژه را نصب کنید"
                    },
                    {
                        "step": 4,
                        "title": "اجرای سرور",
                        "command": "uvicorn main:app --reload",
                        "description": "سرور API را اجرا کنید"
                    }
                ],
                "deployment_options": [
                    {"name": "Render", "url": "https://render.com", "description": "استقرار رایگان"},
                    {"name": "Railway", "url": "https://railway.app", "description": "استقرار ساده"},
                    {"name": "Fly.io", "url": "https://fly.io", "description": "استقرار سریع"}
                ]
            },
            "mobile_app": {
                "title": "راهنمای اجرای اپلیکیشن موبایل",
                "requirements": [
                    "Node.js نسخه 18 یا بالاتر",
                    "React Native CLI یا Expo",
                    "Android Studio یا Xcode"
                ],
                "steps": [
                    {
                        "step": 1,
                        "title": "کلون و نصب",
                        "command": "git clone ... && cd project && npm install",
                        "description": "فایل‌ها را دانلود و وابستگی‌ها را نصب کنید"
                    },
                    {
                        "step": 2,
                        "title": "اجرا روی اندروید",
                        "command": "npx react-native run-android",
                        "description": "اپ را روی شبیه‌ساز اندروید اجرا کنید"
                    },
                    {
                        "step": 3,
                        "title": "اجرا روی iOS",
                        "command": "npx react-native run-ios",
                        "description": "اپ را روی شبیه‌ساز iOS اجرا کنید"
                    }
                ],
                "deployment_options": [
                    {"name": "Expo", "url": "https://expo.dev", "description": "استقرار سریع"},
                    {"name": "App Store", "url": "https://developer.apple.com", "description": "انتشار در اپ استور"},
                    {"name": "Google Play", "url": "https://play.google.com/console", "description": "انتشار در گوگل پلی"}
                ]
            }
        }

        # راهنمای پیش‌فرض
        default_guide = {
            "title": "راهنمای اجرای پروژه",
            "requirements": ["بررسی فایل README.md پروژه"],
            "steps": [
                {
                    "step": 1,
                    "title": "دانلود فایل‌ها",
                    "command": "git clone ...",
                    "description": "فایل‌ها را از GitHub دانلود کنید"
                },
                {
                    "step": 2,
                    "title": "بررسی README",
                    "command": "cat README.md",
                    "description": "راهنمای پروژه را بخوانید"
                }
            ],
            "deployment_options": []
        }

        guide = guides.get(project_type, default_guide)
        guide["project_id"] = project_id
        guide["project_name"] = project.get("name", "")
        guide["project_type"] = project_type

        return {"success": True, "guide": guide}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting deployment guide: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/reload-from-github")
async def reload_from_github():
    """بارگذاری مجدد داده‌ها از GitHub"""
    try:
        from ...main import load_projects_from_github, load_workflows_from_github
        from ...services.project_service import get_project_service

        github_storage = get_github_storage()
        project_service = get_project_service()
        project_service.github_storage = github_storage

        # بارگذاری پروژه‌ها
        await load_projects_from_github(github_storage, project_service)

        # بارگذاری workflows
        orchestrator = get_orchestrator()
        await load_workflows_from_github(github_storage, orchestrator)

        return {
            "success": True,
            "projects_loaded": len(project_service.projects),
            "workflows_loaded": len(orchestrator.integrator.active_workflows)
        }

    except Exception as e:
        logger.error(f"Error reloading from GitHub: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/check-runtime/{project_id}")
async def check_project_runtime(project_id: str):
    """
    بررسی قابلیت اجرای یک پروژه و آماده‌سازی محیط

    - بررسی نیازمندی‌ها
    - Pull کردن Docker images مورد نیاز
    - ذخیره درخواست ارتقا در صورت نیاز
    """
    try:
        result = await check_and_prepare_runtime(project_id)
        return {"success": True, **result}
    except Exception as e:
        logger.error(f"Error checking runtime: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/update-all-projects")
async def update_all_projects_runtime():
    """
    بررسی و به‌روزرسانی همه پروژه‌های موجود

    برای هر پروژه:
    - بررسی قابلیت اجرا
    - Pull کردن Docker images
    - آماده‌سازی محیط
    """
    try:
        from ...services.project_service import get_project_service

        project_service = get_project_service()
        results = {
            "total": 0,
            "updated": 0,
            "can_run": 0,
            "need_upgrade": 0,
            "projects": []
        }

        for project_id, project in project_service.projects.items():
            results["total"] += 1

            # بررسی قابلیت اجرا
            runtime_result = await check_and_prepare_runtime(project_id)

            project_result = {
                "project_id": project_id,
                "name": project.name if hasattr(project, 'name') else project.get('name', ''),
                "runtime": runtime_result
            }

            if runtime_result.get("checked"):
                results["updated"] += 1
                if runtime_result.get("can_run") or runtime_result.get("can_run_with_docker"):
                    results["can_run"] += 1
                else:
                    results["need_upgrade"] += 1

            results["projects"].append(project_result)

        return {
            "success": True,
            **results,
            "message": f"بررسی {results['total']} پروژه انجام شد. {results['can_run']} پروژه آماده اجرا."
        }

    except Exception as e:
        logger.error(f"Error updating all projects: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/prepare-runtime/{project_id}")
async def prepare_project_for_runtime(project_id: str, force_pull: bool = False):
    """
    آماده‌سازی کامل یک پروژه برای اجرا

    - Pull کردن همه Docker images
    - ایجاد Dockerfile اگر وجود ندارد
    - بررسی و رفع مشکلات
    """
    try:
        from ...services.runtime_executor import get_runtime_executor, RUNTIME_CONFIGS, RuntimeType
        from ...services.capability_detector import get_capability_detector
        from ...services.project_service import get_project_service
        import base64

        github_storage = get_github_storage()
        project_service = get_project_service()
        executor = get_runtime_executor()
        detector = get_capability_detector()

        if not executor._initialized:
            executor.initialize(github_storage)
        if not detector._initialized:
            detector.initialize(github_storage)

        # دریافت پروژه
        project_data = project_service.get_project(project_id)
        if not project_data.get("success"):
            raise HTTPException(status_code=404, detail="پروژه یافت نشد")

        project = project_data["project"]
        project_type = project.get("type", "custom")

        # دریافت فایل‌ها
        files = []
        if github_storage and github_storage.token:
            project_files = await github_storage.get_project_files(project_id)
            for folder_type, folder_files in project_files.get("files", {}).items():
                for f in folder_files:
                    if f.get("name") and f["name"] != ".gitkeep":
                        file_path = f"projects/{project_id}/{folder_type}/{f['name']}"
                        result = await github_storage.get_file(file_path)
                        content = ""
                        if result.get("success") and result.get("content"):
                            content = base64.b64decode(result["content"]).decode('utf-8', errors='replace')
                        files.append({
                            "name": f["name"],
                            "folder": folder_type,
                            "content": content
                        })

        if not files:
            raise HTTPException(status_code=400, detail="فایلی برای آماده‌سازی وجود ندارد")

        # تشخیص نوع runtime
        runtime_type = await executor.detect_runtime_type(project_id, files)

        # Pull کردن image اصلی
        config = RUNTIME_CONFIGS.get(runtime_type, RUNTIME_CONFIGS.get(RuntimeType.STATIC))
        pulled_images = []

        if config.get("image") and executor.is_docker_available():
            import asyncio
            try:
                process = await asyncio.create_subprocess_exec(
                    "docker", "pull", config["image"],
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                await asyncio.wait_for(process.communicate(), timeout=300)
                if process.returncode == 0:
                    pulled_images.append(config["image"])
            except Exception as e:
                logger.warning(f"Could not pull {config['image']}: {e}")

        # بررسی Dockerfile
        has_dockerfile = any(f["name"].lower() == "dockerfile" for f in files)

        # اگر Dockerfile نداره، یکی بساز و ذخیره کن
        dockerfile_created = False
        if not has_dockerfile and github_storage:
            dockerfile_content = await generate_dockerfile_content(runtime_type, config)
            if dockerfile_content:
                try:
                    await github_storage.save_project_file(
                        project_id,
                        dockerfile_content.encode('utf-8'),
                        "Dockerfile",
                        "generated"
                    )
                    dockerfile_created = True
                    logger.info(f"Created Dockerfile for {project_id}")
                except Exception as e:
                    logger.warning(f"Could not save Dockerfile: {e}")

        docker_available = executor.is_docker_available()

        return {
            "success": True,
            "project_id": project_id,
            "runtime_type": runtime_type.value,
            "pulled_images": pulled_images,
            "dockerfile_existed": has_dockerfile,
            "dockerfile_created": dockerfile_created,
            "ready_to_run": len(pulled_images) > 0 or has_dockerfile,
            "docker_available": docker_available,
            "message": "آماده برای اجرا" if docker_available else "⚠️ Docker در این سرور در دسترس نیست. پروژه‌ها فقط در محیط محلی با Docker قابل اجرا هستند.",
            "config": {
                "port": config.get("port"),
                "memory": config.get("memory"),
                "build_cmd": config.get("build_cmd"),
                "start_cmd": config.get("start_cmd")
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error preparing runtime: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def generate_dockerfile_content(runtime_type, config: Dict) -> Optional[str]:
    """تولید محتوای Dockerfile بر اساس نوع runtime"""
    from ...services.runtime_executor import RuntimeType
    import json

    if runtime_type in [RuntimeType.NODEJS, RuntimeType.REACT, RuntimeType.VUE]:
        return f"""FROM {config['image']}
WORKDIR /app
COPY package*.json ./
RUN {config['build_cmd']}
COPY . .
EXPOSE {config['port']}
CMD {json.dumps(config['start_cmd'].split())}
"""
    elif runtime_type == RuntimeType.NEXTJS:
        return f"""FROM {config['image']}
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
RUN npm run build
EXPOSE {config['port']}
CMD ["npm", "run", "start"]
"""
    elif runtime_type in [RuntimeType.PYTHON, RuntimeType.FASTAPI]:
        start_cmd_parts = config['start_cmd'].split()
        return f"""FROM {config['image']}
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE {config['port']}
CMD {json.dumps(start_cmd_parts)}
"""
    elif runtime_type == RuntimeType.STATIC:
        return """FROM nginx:alpine
COPY . /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
"""
    return None
