"""
API ساده برای مدیریت پروژه‌ها
بدون پیچیدگی - فقط کار میکنه!
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
import os
import json
import base64
import logging

from ...core.database import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/simple", tags=["Simple Projects"])


# ================================
# Request/Response Models
# ================================

class CreateProjectRequest(BaseModel):
    name: str
    description: str = ""  # legacy / fallback اگر structured_prompt نباشد
    project_type: str = "python"
    technologies: List[str] = []
    model_ids: List[str] = []  # 🆕 اجباری برای production flow (legacy خالی → 400)
    auto_detect_type: bool = False
    # 🆕 پرامپت ساختاریافته از idea-to-prompt — اولویت بر description
    structured_prompt: Optional[Dict[str, Any]] = None
    # 🆕 (Creator file upload) — اگر کاربر فایل آپلود کرده ولی idea-to-prompt
    # نزده، اینجا session_id ها پاس داده می‌شوند تا extraction در create
    # انجام شود. در flow عادی، idea-to-prompt قبلاً extraction را انجام داده
    # و structured_prompt پرشده — این فیلد در آن حالت اختیاری است.
    upload_session_ids: Optional[List[str]] = None
    # 🆕 (Reference Projects) — پروژه‌های مرجع برای پروژهٔ جدید. در meta
    # ذخیره می‌شوند تا کاربر بعداً ببیند از کجا الهام گرفته. هر آیتم:
    # {project_id, project_path, is_selected}
    selected_projects: Optional[List[Dict[str, Any]]] = None


class IdeaToPromptRequest(BaseModel):
    """🆕 ورودی preview prompt — idea → strong prompt بدون ساخت پروژه."""
    idea: str
    name: str
    project_type: str = "auto"
    technologies: Optional[List[str]] = None
    model_ids: List[str]  # اجباری
    # 🆕 (Creator file upload) — اگر کاربر فایل (صوت/PDF/تصویر/ویدئو) آپلود
    # کرده، session_id های آن‌ها اینجا پاس داده می‌شوند. backend از
    # _resolve_attachments_for_idea استفاده می‌کند تا extraction انجام شود
    # و متن استخراج‌شده با idea ادغام شود قبل از تولید پرامپت.
    upload_session_ids: Optional[List[str]] = None
    # 🆕 (Reference Projects) — پروژه‌های انتخاب‌شده به‌عنوان منبع الهام.
    selected_projects: Optional[List[Dict[str, Any]]] = None


class DetectTypeRequest(BaseModel):
    description: str
    name: Optional[str] = ""
    model_id: Optional[str] = None


class PushToGitHubRequest(BaseModel):
    repo_name: Optional[str] = None
    description: Optional[str] = ""
    # 🆕 force private — همیشه True (override در منطق هم enforce می‌شود)
    private: bool = True
    auto_init: bool = False
    commit_message: str = "Initial commit from AI Creator"


class ProjectResponse(BaseModel):
    id: str
    name: str
    description: str
    project_type: str
    status: str
    created_at: str
    files: List[dict] = []
    structure: dict = {}


# ================================
# AI Generate Function
# ================================

async def ai_generate(prompt: str, model_ids: Optional[List[str]] = None) -> str:
    """تولید متن با AI - با fallback chain روی model_ids."""
    from ...services.ai_manager import get_ai_manager
    from ...services.ai_base import Message

    ai_manager = get_ai_manager()
    available_models = ai_manager.get_available_models()
    if not available_models:
        raise HTTPException(status_code=400, detail="هیچ مدل AI فعالی نیست! اول از تنظیمات کلید وارد کنید.")

    available_by_id = {m.id: m for m in available_models}

    # ساخت ترتیب مدل‌ها برای امتحان
    target_ids: List[str] = []
    if model_ids:
        for mid in model_ids:
            if mid in available_by_id:
                target_ids.append(mid)
    if not target_ids:
        target_ids = [available_models[0].id]

    last_error: Optional[Exception] = None
    for mid in target_ids:
        try:
            response = await ai_manager.generate(
                model_id=mid,
                messages=[Message(role="user", content=prompt)],
                max_tokens=4000,
                temperature=0.7,
            )
            return response.content if hasattr(response, "content") else str(response)
        except Exception as e:
            last_error = e
            logger.warning(f"ai_generate: model {mid} failed: {e}; trying next")
            continue

    raise HTTPException(
        status_code=500,
        detail=f"همهٔ مدل‌های انتخابی شکست خوردند. آخرین خطا: {last_error}",
    )


def _extract_json(text: str) -> Optional[dict]:
    """استخراج اولین JSON معتبر از خروجی مدل."""
    if not text:
        return None
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[-1]
        if "```" in cleaned:
            cleaned = cleaned.rsplit("```", 1)[0]
    try:
        return json.loads(cleaned)
    except Exception:
        pass
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start != -1 and end > start:
        try:
            return json.loads(cleaned[start : end + 1])
        except Exception:
            return None
    return None


# ================================
# Endpoints
# ================================

@router.get("/projects")
async def list_projects():
    """لیست همه پروژه‌ها"""
    from ...services.simple_creator import get_simple_creator

    creator = get_simple_creator()
    projects = creator.list_projects()

    return {
        "success": True,
        "projects": [p.to_dict() for p in projects],
        "count": len(projects)
    }


# 🆕 endpoint جدید: idea → strong prompt (preview بدون ساخت پروژه)
@router.post("/projects/idea-to-prompt")
async def idea_to_prompt_preview(request: IdeaToPromptRequest):
    """مرحلهٔ ۱ از flow جدید: idea خام → strong prompt ساختاریافته.

    خروجی شامل full_prompt_text + همه فیلدها برای نمایش در preview UI.
    کاربر می‌تواند پرامپت را ویرایش کند و سپس به create_project بفرستد.
    """
    from ...services.creator_idea_to_prompt import idea_to_strong_prompt_for_creator

    if not request.idea.strip():
        raise HTTPException(status_code=400, detail="idea نمی‌تواند خالی باشد")
    if not request.name.strip():
        raise HTTPException(status_code=400, detail="name نمی‌تواند خالی باشد")
    if not request.model_ids:
        raise HTTPException(
            status_code=400,
            detail="حداقل یک مدل AI انتخاب کنید (model_ids الزامی است)",
        )

    async def _gen(prompt: str, model_ids: Optional[List[str]] = None) -> str:
        return await ai_generate(prompt, model_ids=model_ids)

    # 🆕 (Creator file upload) — اگر upload_session_ids آمد، extraction
    # انجام بده و idea را با محتوای فایل‌ها augment کن. استفاده مجدد از
    # همان منطق oversight (_resolve_attachments_for_idea).
    effective_idea = request.idea
    if request.upload_session_ids:
        try:
            from ...services.oversight_service import get_oversight_service
            ovs = get_oversight_service()
            effective_idea, _attachments_meta = await ovs._resolve_attachments_for_idea(
                request.idea, request.upload_session_ids,
            )
        except ValueError as ve:
            # blocked_no_vision_model یا all_extractions_failed — همان
            # ساختار oversight را با 409 برگردانیم تا UI toggle نشان دهد.
            blocked = getattr(ve, "blocked_payload", None)
            if blocked:
                raise HTTPException(
                    status_code=409,
                    detail=blocked,
                )
            raise HTTPException(status_code=400, detail=str(ve))
        except Exception as ae:
            logger.warning(f"creator idea-to-prompt extraction failed: {ae}")
            # graceful: ادامه با idea خام
            effective_idea = request.idea + f"\n\n[خطا در استخراج فایل‌ها: {str(ae)[:200]}]"

    # 🆕 (Reference Projects) — اگر کاربر پروژه‌های مرجع انتخاب کرده،
    # محتوای آن‌ها را scan/classify/fusion کن و قبل از فراخوانی AI به idea
    # تزریق کن. AI پرامپت تولیدی را با ساختار/الگوی مراجع هم‌خوان می‌سازد.
    # تمام failures silently ignore می‌شوند.
    if request.selected_projects:
        try:
            from ...services.reference_project_service import (
                get_reference_project_service,
            )
            from ...services.oversight_service import (
                get_oversight_service, get_github_token,
            )
            _ovs2 = get_oversight_service()
            valid_refs: List[Dict[str, Any]] = []
            for raw in request.selected_projects:
                if not isinstance(raw, dict) or not raw.get("is_selected", True):
                    continue
                pid = (raw.get("project_id") or "").strip()
                ppath = (raw.get("project_path") or "").strip()
                target = None
                if pid:
                    target = next((w for w in _ovs2.watched if w.id == pid), None)
                if target is None and ppath:
                    target = next(
                        (w for w in _ovs2.watched
                         if (w.repo_full_name or "").lower() == ppath.lower()),
                        None,
                    )
                if target:
                    valid_refs.append({
                        "project_id": target.id,
                        "project_path": target.repo_full_name,
                        "is_selected": True,
                    })
            if valid_refs:
                ref_ctx = await get_reference_project_service().build_reference_context(
                    selected_projects=valid_refs,
                    task_summary=effective_idea[:500],
                    token=get_github_token() or None,
                )
                if ref_ctx and ref_ctx.fusion_text:
                    effective_idea = (
                        f"{effective_idea}\n\n---\n"
                        f"## 📚 پروژه‌های مرجع (الهام از پیاده‌سازی‌های موجود)\n"
                        f"_ساختار/فایل‌های زیر را به‌عنوان الگو در نظر بگیر._\n\n"
                        f"{ref_ctx.fusion_text}\n---\n"
                    )
                    logger.info(
                        f"creator idea_to_prompt: injected reference context for "
                        f"{len(valid_refs)} project(s), {ref_ctx.total_chars} chars"
                    )
        except Exception as _ref_e:
            logger.warning(f"creator idea_to_prompt: ref scan failed: {_ref_e}")

    try:
        result = await idea_to_strong_prompt_for_creator(
            idea=effective_idea,
            name=request.name,
            project_type=request.project_type,
            technologies=list(request.technologies or []),
            ai_generate=_gen,
            model_ids=request.model_ids,
        )
        # 🆕 (Reference Projects) — نتیجه را با لیست مراجع که در پرامپت
        # استفاده شد augment کن تا UI نشان بدهد و در create persist شود.
        if request.selected_projects:
            result.setdefault("selected_projects", list(request.selected_projects))
        return {"success": True, **result}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(
            status_code=502,
            detail=f"خطا در AI generate: {str(e)[:300]}",
        )
    except Exception as e:
        logger.exception("idea_to_prompt_preview failed")
        raise HTTPException(
            status_code=500,
            detail=f"خطای داخلی: {str(e)[:300]}",
        )


@router.post("/projects/create")
async def create_project(request: CreateProjectRequest):
    """ساخت پروژه جدید با AI"""
    from ...services.simple_creator import get_simple_creator

    creator = get_simple_creator()

    # 🆕 enforce model_ids — حداقل یک مدل لازم است
    if not request.model_ids:
        raise HTTPException(
            status_code=400,
            detail="حداقل یک مدل AI انتخاب کنید (model_ids الزامی است)",
        )

    project_type = request.project_type
    technologies = list(request.technologies or [])

    # 🆕 اگر structured_prompt ارسال شد، اولویت دارد
    structured = request.structured_prompt
    description = request.description
    if structured and isinstance(structured, dict):
        # از structured_prompt استفاده کن
        if structured.get("full_prompt_text"):
            description = structured["full_prompt_text"]
        elif structured.get("structured_description"):
            description = structured["structured_description"]
        # technologies را از structured_prompt هم بگیر
        st_tech = structured.get("tech_stack") or []
        if isinstance(st_tech, list):
            for t in st_tech:
                if t and t not in technologies:
                    technologies.append(t)

    if not description.strip():
        raise HTTPException(status_code=400, detail="description یا structured_prompt لازم است")

    # تشخیص خودکار نوع پروژه (اگر کاربر خواسته باشد)
    if request.auto_detect_type or project_type == "auto":
        try:
            detection = await _detect_project_type(
                description=description,
                name=request.name,
                model_ids=request.model_ids,
            )
            if detection.get("primary_type"):
                project_type = detection["primary_type"]
            if detection.get("technologies"):
                for t in detection["technologies"]:
                    if t and t not in technologies:
                        technologies.append(t)
        except Exception as e:
            logger.warning(f"auto-detect failed (continuing with user choice): {e}")
            if project_type == "auto":
                project_type = "python"  # fallback

    # closure برای ai_generate که model_ids را capture می‌کند
    async def gen(prompt: str) -> str:
        return await ai_generate(prompt, model_ids=request.model_ids)

    # 🆕 (Reference Projects) — نرمال‌سازی selected_projects برای persist:
    # حذف self-references و آیتم‌های غیرمعتبر. (در این مرحله پروژهٔ جدید
    # هنوز watched نیست، پس خود-ارجاع منطقی نیست — صرفاً normalize کن.)
    normalized_selected: List[Dict[str, Any]] = []
    if request.selected_projects:
        try:
            from ...services.oversight_service import get_oversight_service
            _ovs3 = get_oversight_service()
            for raw in request.selected_projects:
                if not isinstance(raw, dict) or not raw.get("is_selected", True):
                    continue
                pid = (raw.get("project_id") or "").strip()
                ppath = (raw.get("project_path") or "").strip()
                target = None
                if pid:
                    target = next((w for w in _ovs3.watched if w.id == pid), None)
                if target is None and ppath:
                    target = next(
                        (w for w in _ovs3.watched
                         if (w.repo_full_name or "").lower() == ppath.lower()),
                        None,
                    )
                if target:
                    normalized_selected.append({
                        "project_id": target.id,
                        "project_path": target.repo_full_name,
                        "is_selected": True,
                    })
        except Exception as _e:
            logger.warning(f"create_project: selected_projects normalize failed: {_e}")

    try:
        project = await creator.create_project(
            name=request.name,
            description=description,
            project_type=project_type,
            technologies=technologies,
            ai_generate=gen,
            selected_projects=normalized_selected,
        )

        return {
            "success": True,
            "project": project.to_dict(),
            "detected_type": project_type if request.auto_detect_type else None,
            "detected_technologies": technologies if request.auto_detect_type else None,
            "model_ids_used": request.model_ids,
            "used_structured_prompt": bool(structured),
            "message": f"پروژه {project.name} با {len(project.files)} فایل ساخته شد!",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("create_project failed")
        # 🆕 error reporting پربار
        err_msg = str(e)[:500]
        err_category = "unknown"
        suggested: List[str] = []
        if "model" in err_msg.lower() and ("not found" in err_msg.lower() or "unavailable" in err_msg.lower()):
            err_category = "model_unavailable"
            suggested = [
                "بررسی کنید مدل انتخابی هنوز فعال است",
                "مدل دیگری انتخاب کنید",
                "توکن provider را بررسی کنید",
            ]
        elif "rate" in err_msg.lower() and "limit" in err_msg.lower():
            err_category = "rate_limit"
            suggested = ["چند دقیقه صبر کنید", "یک مدل از provider دیگر انتخاب کنید"]
        elif "auth" in err_msg.lower() or "401" in err_msg or "403" in err_msg:
            err_category = "auth_failed"
            suggested = ["توکن provider در /settings بررسی کنید"]
        else:
            suggested = [
                "بررسی logs برای جزئیات",
                "مدل دیگری امتحان کنید",
                "اگر مشکل ادامه دارد، error category را گزارش کنید",
            ]
        raise HTTPException(
            status_code=500,
            detail={
                "primary_error": err_msg[:200],
                "error_category": err_category,
                "detail": err_msg,
                "suggested_actions": suggested,
                "stage": "create_files",
            },
        )


# ================================
# تشخیص خودکار نوع پروژه
# ================================

async def _detect_project_type(
    description: str, name: str = "", model_ids: Optional[List[str]] = None
) -> dict:
    """با AI تشخیص می‌دهد کدام نوع پروژه برای این توضیح مناسب است."""
    if not description.strip():
        raise HTTPException(status_code=400, detail="توضیحات خالی است")

    prompt = f"""تو یک معمار نرم‌افزاری هستی. بر اساس توضیحات کاربر، بهترین نوع پروژه و تکنولوژی‌های مناسب را تشخیص بده.

# نام پروژه
{name or '(بدون نام)'}

# توضیحات
{description.strip()}

# انواع موجود
- python      (اسکریپت یا CLI)
- fastapi     (API سرور Python)
- flask       (وب‌اپ ساده Python)
- nextjs      (وب‌اپ React/TypeScript)
- react       (فقط فرانت‌اند SPA)
- node        (بک‌اند JavaScript / Express)

# وظیفه
بهترین نوع را به‌عنوان primary_type انتخاب کن. اگر پروژه ترکیبی است (مثل full-stack)، یکی را primary بگذار و سایر را در alternative_types بگذار.
تکنولوژی‌های ضروری (دیتابیس، احراز هویت، redis، …) را در technologies لیست کن.

# خروجی فقط JSON
{{
  "primary_type": "fastapi",
  "alternative_types": ["nextjs"],
  "technologies": ["PostgreSQL", "JWT"],
  "reasoning": "یک پاراگراف کوتاه چرا این انتخاب بهترینه"
}}"""

    response = await ai_generate(prompt, model_ids=model_ids)
    parsed = _extract_json(response)
    if not parsed or "primary_type" not in parsed:
        raise HTTPException(status_code=500, detail="پاسخ AI قابل تجزیه نبود")

    valid_types = {"python", "fastapi", "flask", "nextjs", "react", "node"}
    if parsed["primary_type"] not in valid_types:
        parsed["primary_type"] = "python"

    return {
        "primary_type": parsed.get("primary_type", "python"),
        "alternative_types": [
            t for t in parsed.get("alternative_types", []) if t in valid_types
        ],
        "technologies": parsed.get("technologies", []) or [],
        "reasoning": parsed.get("reasoning", ""),
        "raw_response": response[:2000],
    }


@router.post("/detect-type")
async def detect_project_type(request: DetectTypeRequest):
    """تشخیص خودکار نوع پروژه از توضیحات."""
    return await _detect_project_type(
        description=request.description,
        name=request.name or "",
        model_ids=[request.model_id] if request.model_id else None,
    )


@router.get("/projects/{project_id}")
async def get_project(project_id: str):
    """دریافت یک پروژه"""
    from ...services.simple_creator import get_simple_creator

    creator = get_simple_creator()
    project = creator.get_project(project_id)

    if not project:
        raise HTTPException(status_code=404, detail="پروژه پیدا نشد")

    # بارگذاری فایل‌ها از دیسک
    files = await creator.get_project_files(project_id)

    data = project.to_dict()
    data["disk_files"] = files

    return {
        "success": True,
        "project": data
    }


@router.get("/projects/{project_id}/files")
async def list_project_files(project_id: str):
    """لیست فایل‌های پروژه"""
    from ...services.simple_creator import get_simple_creator

    creator = get_simple_creator()
    files = await creator.get_project_files(project_id)

    return {
        "success": True,
        "files": files,
        "count": len(files)
    }


@router.get("/projects/{project_id}/files/{file_path:path}")
async def get_file_content(project_id: str, file_path: str):
    """خواندن محتوای فایل"""
    from ...services.simple_creator import get_simple_creator

    creator = get_simple_creator()
    content = await creator.get_file_content(project_id, file_path)

    if content is None:
        raise HTTPException(status_code=404, detail="فایل پیدا نشد")

    return {
        "success": True,
        "path": file_path,
        "content": content
    }


@router.delete("/projects/{project_id}")
async def delete_project(project_id: str, db: Session = Depends(get_db)):
    """حذف پروژه"""
    from ...services.simple_creator import get_simple_creator
    from ...models.project import Project, ProjectFile

    creator = get_simple_creator()

    # حذف از memory و فایل‌سیستم
    memory_deleted = creator.delete_project(project_id)

    # حذف از دیتابیس هم
    try:
        # حذف داده‌های مرتبط با ژورنال
        try:
            from .project_journal import ActivityLog, Report, ReportTrigger
            db.query(ActivityLog).filter(ActivityLog.project_id == project_id).delete()
            db.query(Report).filter(Report.project_id == project_id).delete()
            db.query(ReportTrigger).filter(ReportTrigger.project_id == project_id).delete()
        except Exception:
            pass

        # حذف فایل‌ها و پروژه از دیتابیس
        db.query(ProjectFile).filter(ProjectFile.project_id == project_id).delete()
        project = db.query(Project).filter(Project.id == project_id).first()
        if project:
            db.delete(project)
            db.commit()
    except Exception as e:
        db.rollback()
        # ادامه بده حتی اگه از دیتابیس نتونست حذف کنه

    if not memory_deleted and not project:
        raise HTTPException(status_code=404, detail="پروژه پیدا نشد")

    return {
        "success": True,
        "message": "پروژه حذف شد"
    }


class GenerateMoreRequest(BaseModel):
    """درخواست تولید فایل‌های بیشتر"""
    file_paths: List[str] = []
    descriptions: dict = {}  # path -> description


@router.post("/projects/{project_id}/generate-more")
async def generate_more_files(project_id: str, request: GenerateMoreRequest = None):
    """تولید فایل‌های بیشتر برای پروژه"""
    from ...services.simple_creator import get_simple_creator
    import aiofiles
    from pathlib import Path

    creator = get_simple_creator()
    project = creator.get_project(project_id)

    if not project:
        raise HTTPException(status_code=404, detail="پروژه پیدا نشد")

    file_paths = request.file_paths if request else []
    descriptions = request.descriptions if request else {}

    if not file_paths:
        raise HTTPException(status_code=400, detail="لیست فایل‌ها خالی است")

    generated_files = []
    errors = []
    project_path = creator.workspace / project_id

    for file_path in file_paths:
        try:
            # توضیح فایل
            file_desc = descriptions.get(file_path, f"فایل {file_path} برای پروژه")

            # تولید محتوای فایل با AI
            content = await creator._generate_file(
                project_name=project.name,
                project_desc=project.description,
                project_type=project.project_type,
                file_path=file_path,
                file_desc=file_desc,
                ai_generate=ai_generate
            )

            # ذخیره فایل در دیسک
            full_path = project_path / file_path
            full_path.parent.mkdir(parents=True, exist_ok=True)

            async with aiofiles.open(full_path, 'w') as f:
                await f.write(content)

            # اضافه کردن به لیست فایل‌های پروژه
            from ...services.simple_creator import ProjectFile
            new_file = ProjectFile(
                path=file_path,
                content=content,
                language=creator._detect_language(file_path)
            )
            project.files.append(new_file)

            generated_files.append({
                "path": file_path,
                "size": len(content),
                "language": new_file.language
            })

        except HTTPException:
            raise
        except Exception as e:
            errors.append({"path": file_path, "error": str(e)})

    # ذخیره metadata پروژه
    await creator._save_project_meta(project)

    return {
        "success": len(errors) == 0,
        "project_id": project_id,
        "generated": generated_files,
        "errors": errors,
        "message": f"{len(generated_files)} فایل تولید شد" + (f" ({len(errors)} خطا)" if errors else "")
    }


class DeployRequest(BaseModel):
    """درخواست Deploy"""
    github_repo_url: Optional[str] = None
    github_branch: str = "main"
    env_vars: dict = {}


@router.post("/projects/{project_id}/deploy")
async def deploy_project(project_id: str, request: DeployRequest = None):
    """Deploy پروژه به Render"""
    from ...services.simple_creator import get_simple_creator
    from ...services.deploy_service import get_deploy_manager
    from ...services.github_storage import get_github_storage
    import os

    creator = get_simple_creator()
    project = creator.get_project(project_id)

    if not project:
        raise HTTPException(status_code=404, detail="پروژه پیدا نشد")

    render_key = os.environ.get("RENDER_API_KEY")
    if not render_key:
        raise HTTPException(status_code=400, detail="کلید Render تنظیم نشده. از صفحه تنظیمات کلید رو وارد کن.")

    # دریافت deploy manager
    deploy_manager = get_deploy_manager()
    deploy_manager.configure_render(render_key)

    # بررسی GitHub repo
    github_repo_url = None
    if request and request.github_repo_url:
        github_repo_url = request.github_repo_url
    else:
        # سعی کن از GitHub storage اطلاعات رو بگیر
        github_storage = get_github_storage()
        if github_storage.token and github_storage.owner and github_storage.repo:
            github_repo_url = f"https://github.com/{github_storage.owner}/{github_storage.repo}"

    if not github_repo_url:
        # اگر GitHub repo نداریم، راهنمای دستی بده
        return {
            "success": True,
            "deployed": False,
            "message": "برای Deploy خودکار، اول پروژه رو به GitHub push کن.",
            "project_id": project_id,
            "instructions": [
                "۱. فایل‌های پروژه رو دانلود کن",
                "۲. یه repo جدید در GitHub بساز",
                "۳. فایل‌ها رو push کن",
                "۴. برگرد و دوباره Deploy رو بزن با آدرس repo"
            ]
        }

    try:
        # Deploy به Render
        deployment = await deploy_manager.quick_deploy(
            project_id=project_id,
            project_name=project.name,
            project_type=project.project_type,
            github_repo_url=github_repo_url,
            github_branch=request.github_branch if request else "main",
            root_dir=f"ai-workspace/projects/{project_id}/generated",
            env_vars=request.env_vars if request else {}
        )

        if deployment.error:
            return {
                "success": False,
                "error": deployment.error,
                "project_id": project_id
            }

        return {
            "success": True,
            "deployed": True,
            "message": f"پروژه در حال Deploy شدن به Render است!",
            "project_id": project_id,
            "deployment_id": deployment.id,
            "service_id": deployment.service_id,
            "status": deployment.status.value,
            "url": deployment.url,
            "dashboard_url": f"https://dashboard.render.com/web/{deployment.service_id}" if deployment.service_id else None
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"خطا در Deploy: {str(e)}")


@router.get("/status")
async def get_status():
    """وضعیت سیستم"""
    from ...services.ai_manager import get_ai_manager
    from ...services.simple_creator import get_simple_creator

    ai_manager = get_ai_manager()
    creator = get_simple_creator()

    available_models = ai_manager.get_available_models()

    # وضعیت GitHub token
    github_token = os.environ.get("GITHUB_TOKEN", "").strip()
    if not github_token:
        try:
            from ...models.setting import Setting
            from ...core.database import SessionLocal
            db = SessionLocal()
            try:
                for k in ("api_key_github", "github_token", "GITHUB_TOKEN"):
                    v = Setting.get_value(db, k)
                    if v:
                        github_token = v
                        break
            finally:
                db.close()
        except Exception:
            pass

    return {
        "success": True,
        "ai_ready": len(available_models) > 0,
        "models_count": len(available_models),
        "models": [{"id": m.id, "name": m.name, "provider": m.provider.value} for m in available_models],
        "projects_count": len(creator.projects),
        "github_ready": bool(github_token),
    }


# ================================
# GitHub Push (پروژه → repo جدید)
# ================================

def _get_github_token_value() -> str:
    """دریافت توکن GitHub از env یا دیتابیس."""
    token = os.environ.get("GITHUB_TOKEN", "").strip()
    if token:
        return token
    try:
        from ...models.setting import Setting
        from ...core.database import SessionLocal
        db = SessionLocal()
        try:
            for k in ("api_key_github", "github_token", "GITHUB_TOKEN"):
                v = Setting.get_value(db, k)
                if v:
                    os.environ["GITHUB_TOKEN"] = v
                    return v
        finally:
            db.close()
    except Exception:
        pass
    return ""


def _normalize_repo_name(name: str) -> str:
    """نرمال‌سازی نام برای GitHub repo."""
    import re
    s = re.sub(r"[^a-zA-Z0-9._-]+", "-", name.strip())
    s = re.sub(r"-+", "-", s).strip("-_.")
    return s[:80] or "ai-creator-project"


@router.post("/projects/{project_id}/push-to-github")
async def push_to_github(project_id: str, request: Optional[PushToGitHubRequest] = None):
    """ساخت یک repo جدید روی GitHub و push کردن همه فایل‌های پروژه به آن."""
    from ...services.simple_creator import get_simple_creator
    import aiohttp

    creator = get_simple_creator()
    project = creator.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="پروژه یافت نشد")

    token = _get_github_token_value()
    if not token:
        raise HTTPException(
            status_code=400,
            detail="توکن GitHub تنظیم نشده. به /settings بروید و وارد کنید.",
        )

    payload = request or PushToGitHubRequest()
    desired_repo = payload.repo_name or _normalize_repo_name(project.name)
    desired_repo = _normalize_repo_name(desired_repo)
    # 🐛 (creator push-to-github fix) — GitHub API description نباید
    # control characters (\n, \r, \t, ...) داشته باشد، در غیر این صورت
    # خطای "description control characters are not allowed" برمی‌گرداند.
    # توضیحات پروژه معمولاً چندخطی است (از پرامپت تولیدی)، باید single-line
    # شود + sanitize. cap به ۳۰۰ کاراکتر طبق محدودیت GitHub.
    raw_desc = payload.description or (project.description or "")
    # حذف control chars (0x00-0x1F + 0x7F)، حفظ newline/tab به‌عنوان space
    import re as _re_desc
    sanitized_desc = _re_desc.sub(r"[\x00-\x1F\x7F]+", " ", raw_desc)
    # collapse spaces
    sanitized_desc = _re_desc.sub(r"\s+", " ", sanitized_desc).strip()
    repo_description = sanitized_desc[:300]

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "ai-creator-pusher/1.0",
    }

    async with aiohttp.ClientSession() as session:
        # 1) شناسایی owner (کاربر فعلی)
        async with session.get("https://api.github.com/user", headers=headers) as r:
            if r.status != 200:
                text = await r.text()
                raise HTTPException(
                    status_code=r.status, detail=f"احراز هویت GitHub ناموفق: {text[:200]}"
                )
            user_data = await r.json()
            owner = user_data.get("login")

        if not owner:
            raise HTTPException(status_code=500, detail="نام کاربری GitHub یافت نشد")

        # 2) بررسی وجود repo و در صورت نبود ساخت آن
        repo_url_api = f"https://api.github.com/repos/{owner}/{desired_repo}"
        async with session.get(repo_url_api, headers=headers) as r:
            repo_exists = r.status == 200
            if r.status not in (200, 404):
                text = await r.text()
                raise HTTPException(
                    status_code=r.status, detail=f"خطای GitHub: {text[:200]}"
                )

        if not repo_exists:
            # 🆕 force private — هیچ‌گاه public نسازیم
            create_payload = {
                "name": desired_repo,
                "description": repo_description,
                "private": True,  # FORCED
                "auto_init": payload.auto_init,
            }
            async with session.post(
                "https://api.github.com/user/repos", headers=headers, json=create_payload
            ) as r:
                if r.status not in (200, 201):
                    text = await r.text()
                    raise HTTPException(
                        status_code=r.status, detail=f"ساخت repo ناموفق: {text[:200]}"
                    )
                repo_info = await r.json()
        else:
            async with session.get(repo_url_api, headers=headers) as r:
                repo_info = await r.json()

        default_branch = repo_info.get("default_branch") or "main"
        repo_html_url = repo_info.get("html_url")

        # 3) خواندن فایل‌های پروژه از دیسک
        try:
            files = await creator.get_project_files(project_id)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"خواندن فایل‌ها ناموفق: {e}")

        if not files:
            return {
                "success": True,
                "repo_url": repo_html_url,
                "owner": owner,
                "repo": desired_repo,
                "uploaded": 0,
                "skipped": 0,
                "message": "Repo ساخته شد ولی فایلی برای آپلود وجود نداشت",
            }

        # 4) آپلود فایل‌ها (هر کدام جدا از طریق contents API)
        uploaded: List[str] = []
        failed: List[dict] = []

        def _classify_error(status: int, text: str) -> tuple:
            """طبقه‌بندی خطا → (category, suggested_fix)"""
            tl = (text or "").lower()
            if status in (401, 403) or "bad credentials" in tl or "authentication" in tl:
                return ("auth_failed", "توکن GitHub را در /settings بررسی کنید — احتمالاً منقضی یا scope ناکافی")
            if status == 429 or "rate limit" in tl or "abuse" in tl:
                return ("rate_limit", "GitHub API rate limit زده — چند دقیقه صبر کنید")
            if status == 422 and ("too large" in tl or "size" in tl):
                return ("file_too_large", "فایل >1MB — GitHub API محدودیت اندازه دارد (از LFS استفاده کنید)")
            if "encoding" in tl or "base64" in tl:
                return ("encoding_error", "محتوای فایل با UTF-8 سازگار نیست")
            if status == 409 or "conflict" in tl:
                return ("branch_conflict", "فایل با sha متفاوت موجود است — pull کنید سپس push")
            if status == 404:
                return ("not_found", "repo یا branch وجود ندارد")
            if status >= 500:
                return ("github_server_error", "GitHub API دچار مشکل سرور — بعداً تلاش کنید")
            return ("unknown", "logs را بررسی کنید")

        async def _put_file(path: str, content: str, sha: Optional[str] = None):
            url = f"https://api.github.com/repos/{owner}/{desired_repo}/contents/{path}"
            content_b64 = base64.b64encode(content.encode("utf-8", errors="ignore")).decode("ascii")
            body = {
                "message": payload.commit_message,
                "content": content_b64,
                "branch": default_branch,
            }
            if sha:
                body["sha"] = sha
            async with session.put(url, headers=headers, json=body) as r:
                if r.status in (200, 201):
                    return True, None, None, None
                text = await r.text()
                category, suggested = _classify_error(r.status, text)
                return False, f"{r.status}: {text[:200]}", category, suggested

        for f in files:
            file_path = f.get("path") or ""
            if not file_path:
                continue
            content = f.get("content", "")
            if not isinstance(content, str):
                content = str(content)

            # برای repoهای موجود، sha فعلی را بگیر
            sha = None
            if repo_exists:
                async with session.get(
                    f"https://api.github.com/repos/{owner}/{desired_repo}/contents/{file_path}?ref={default_branch}",
                    headers=headers,
                ) as r:
                    if r.status == 200:
                        meta = await r.json()
                        if isinstance(meta, dict):
                            sha = meta.get("sha")

            ok, err, err_category, suggested = await _put_file(file_path, content, sha)
            if ok:
                uploaded.append(file_path)
            else:
                # 🆕 schema جدید با error_category و suggested_fix
                failed.append({
                    "path": file_path,
                    "error": err or "unknown",
                    "error_category": err_category or "unknown",
                    "suggested_fix": suggested or "logs را بررسی کنید",
                })

    full_name = f"{owner}/{desired_repo}"

    # 🆕 (Creator) auto-register به watched + notification
    auto_watched_info: Optional[Dict[str, Any]] = None
    if len(failed) == 0:
        try:
            from ...services.oversight_service import get_oversight_service
            from ...services.notification_service import notification_service
            oversight = get_oversight_service()
            auto_watched_info = await oversight.auto_register_watched(
                full_name,
                source="creator_via_web",
                repo_url=repo_html_url,
                default_branch=default_branch,
                language=(project.project_type or ""),
                private=True,  # 🆕 forced — همه repo ها private
                user_notes=(project.description or "")[:300],
            )
            # event project_created (موفقیت)
            await notification_service.notify_event(
                "project_created",
                f"🚀 *پروژه با موفقیت ساخته شد*\n"
                f"📦 نام: `{full_name}`\n"
                f"🔗 GitHub: {repo_html_url}\n"
                f"📁 نوع: `{project.project_type or '—'}`\n"
                f"📄 فایل‌های push شده: *{len(uploaded)}*\n\n"
                f"💡 *کارکرد:*\n{(project.description or '')[:400]}\n\n"
                f"👁 خودکار به مرکز نظارت اضافه شد",
                subject="Project created",
                priority="medium",
                project_name=full_name,
                watched_id=(auto_watched_info or {}).get("id"),
                extra_buttons=[{"text": "🔗 GitHub repo", "url": repo_html_url}],
            )
        except Exception as _e:
            logger.warning(f"auto_register_watched/notification failed: {_e}")
    # 🆕 محاسبهٔ خلاصهٔ پربار خطا
    primary_error = ""
    error_category = "none"
    suggested_actions: List[str] = []
    detail = ""
    if failed:
        first = failed[0] or {}
        primary_error = first.get("error", "unknown")[:150]
        error_category = first.get("error_category", "unknown")
        suggested_actions = [first.get("suggested_fix", "logs را بررسی کنید")]
        if len(failed) > 1:
            suggested_actions.append(
                f"در total {len(failed)} فایل fail شد — بقیه را پس از حل علت اصلی push کنید"
            )
        suggested_actions.append("از /settings توکن GitHub را بازبینی کنید")
        detail = "\n".join(
            f"• {f.get('path')}: {f.get('error', '')[:100]} ({f.get('error_category', '?')})"
            for f in failed[:5]
        )
        if len(failed) > 5:
            detail += f"\n… و {len(failed) - 5} فایل دیگر"

    if failed:
        # event creator_failed (شکست در push) — پربار
        try:
            from ...services.notification_service import notification_service
            err_msg = (
                f"💥 *خطا در push پروژه به GitHub*\n\n"
                f"📦 پروژه: `{project.name}`\n"
                f"🔍 مرحلهٔ شکست: *push_to_github*\n\n"
                f"❌ *علت اصلی:*\n{primary_error}\n\n"
                f"📋 *جزئیات فنی:*\n```\n{detail[:500]}\n```\n"
                f"🛠 *اقدامات پیشنهادی:*\n"
                + "\n".join(f"• {a}" for a in suggested_actions[:3])
                + f"\n\n📊 *آنچه انجام شد:*\n"
                f"✓ create_files: موفق ({len(uploaded) + len(failed)} فایل local)\n"
                f"✗ push_to_github: شکست ({len(uploaded)}/{len(uploaded) + len(failed)} فایل push شد)"
            )
            await notification_service.notify_event(
                "creator_failed",
                err_msg,
                subject="Creator push failed",
                priority="high",
                project_name=project.name,
                extra_hashtags=[error_category],
            )
        except Exception as _e:
            logger.debug(f"creator_failed notification skipped: {_e}")

    return {
        "success": len(failed) == 0,
        "repo_url": repo_html_url,
        "owner": owner,
        "repo": desired_repo,
        "full_name": full_name,
        "default_branch": default_branch,
        "uploaded": len(uploaded),
        "failed": failed,
        "private": True,  # 🆕 always private
        "auto_watched": auto_watched_info,
        # 🆕 پربار خطا برای UI/notification
        "primary_error": primary_error,
        "error_category": error_category,
        "suggested_actions": suggested_actions,
        "error_detail": detail,
        "message": (
            f"{len(uploaded)} فایل push شد"
            + (f" — {len(failed)} خطا" if failed else "")
        ),
    }
