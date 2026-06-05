"""
API ساده برای مدیریت پروژه‌ها
بدون پیچیدگی - فقط کار میکنه!
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
import asyncio
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

async def ai_generate_with_meta(
    prompt: str, model_ids: Optional[List[str]] = None,
) -> tuple:
    """🆕 (model attribution) — same as ai_generate but returns a
    (content, used_model_id) tuple so callers can record which model
    actually answered. The fallback chain semantics are unchanged: try
    each model_id in order, return on first success.

    The simple_creator's _tracked_ai_generate unpacks this tuple to
    populate ProjectFile.generated_by, which the UI then displays per
    file. Without this attribution the user couldn't tell which of
    their selected models produced which file."""
    from ...services.ai_manager import get_ai_manager
    from ...services.ai_base import Message

    ai_manager = get_ai_manager()
    available_models = ai_manager.get_available_models()
    if not available_models:
        raise HTTPException(
            status_code=400,
            detail="هیچ مدل AI فعالی نیست! اول از تنظیمات کلید وارد کنید.",
        )

    available_by_id = {m.id: m for m in available_models}

    # Build the order to try. The user's selected list wins (honoring
    # their choice on the Creator page); if empty/all-invalid, fall
    # back to the first available so the call doesn't fail outright.
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
            content = response.content if hasattr(response, "content") else str(response)
            # If ai_manager substituted a fallback model under the hood
            # (model_id disabled, etc.), prefer the EFFECTIVE model id
            # so the user sees what actually generated the content.
            effective_id = getattr(response, "model_id", None) or mid
            return content, effective_id
        except Exception as e:
            last_error = e
            logger.warning(f"ai_generate: model {mid} failed: {e}; trying next")
            continue

    raise HTTPException(
        status_code=500,
        detail=f"همهٔ مدل‌های انتخابی شکست خوردند. آخرین خطا: {last_error}",
    )


async def ai_generate(prompt: str, model_ids: Optional[List[str]] = None) -> str:
    """Back-compat shim — returns just the content string.

    Existing callers (audit prompt generation, _detect_project_type,
    idea_to_prompt) don't care which model answered; they only need
    the text. For attribution-aware callers use ai_generate_with_meta.
    """
    content, _model = await ai_generate_with_meta(prompt, model_ids)
    return content


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
                        # 🆕 (focus_notes) — نقطهٔ تمرکز این مرجع
                        "focus_notes": str(raw.get("focus_notes") or "").strip()[:500],
                    })
            if valid_refs:
                # 🆕 (current_project_profile) — برای creator، پروژهٔ «فعلی» در
                # واقع پروژه‌ای است که الان ساخته می‌شود (پس watched نیست).
                # خلاصه‌ای از خواسته‌های کاربر برای پروژهٔ جدید را به‌جای
                # profile پروژهٔ موجود می‌سازیم.
                _new_proj_profile_lines: List[str] = []
                _new_proj_profile_lines.append(
                    f"- **نام پروژهٔ جدید**: `{request.name}`"
                )
                _new_proj_profile_lines.append(
                    f"- **نوع**: {request.project_type}"
                )
                if request.technologies:
                    _new_proj_profile_lines.append(
                        f"- **تکنولوژی‌های انتخابی کاربر**: "
                        f"{', '.join(request.technologies[:10])}"
                    )
                _new_proj_profile_lines.append(
                    "- **توجه**: این یک پروژهٔ جدید است (هنوز کد ندارد). "
                    "از پروژه‌های مرجع فقط **الگو** را برداشت کن و با stack/"
                    "نام‌گذاری انتخابی کاربر در بالا پیاده‌سازی کن."
                )
                _cur_profile = "\n".join(_new_proj_profile_lines)
                ref_ctx = await get_reference_project_service().build_reference_context(
                    selected_projects=valid_refs,
                    task_summary=effective_idea[:500],
                    token=get_github_token() or None,
                    current_project_profile=_cur_profile,
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
                # 🐛 (auto-detect fallback fix) — previously this fell to
                # "python" which was wrong for the most common case (user
                # wants a web app). When auto-detect fails, lean to
                # fullstack so we generate both halves — much easier for
                # the user to delete unused files than to have to add
                # missing frontend manually.
                project_type = "fullstack"

    # 🆕 Normalize the hyphen alias REGARDLESS of how project_type got set:
    # AI detect might emit "full-stack", user form might post "full-stack",
    # or some legacy code path. Single canonical form: "fullstack".
    # (Was previously inside the auto-detect branch — missed the case
    # where the user supplies the hyphen form explicitly.)
    if project_type == "full-stack":
        project_type = "fullstack"

    # closure برای ai_generate که model_ids را capture می‌کند.
    # 🆕 (model attribution) — returns (content, model_id) tuple so
    # simple_creator can record per-file which model wrote it.
    async def gen(prompt: str):
        return await ai_generate_with_meta(prompt, model_ids=request.model_ids)

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
                        "focus_notes": str(raw.get("focus_notes") or "").strip()[:500],
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
- fastapi     (API سرور Python — فقط backend)
- flask       (وب‌اپ ساده Python)
- nextjs      (وب‌اپ React/TypeScript — فقط frontend)
- react       (فقط فرانت‌اند SPA)
- node        (بک‌اند JavaScript / Express)
- fullstack   (هم backend (FastAPI) هم frontend (Next.js) — برای dashboard‌ها،
                CRM، OSINT analysis، پلتفرم‌هایی که UI + API می‌خواهند)

# وظیفه
بهترین نوع را به‌عنوان primary_type انتخاب کن.

📌 **مهم — اگر پروژه هم UI و هم API می‌خواهد**:
  - "fullstack" را انتخاب کن (نه "fastapi" به‌تنهایی)
  - علائم نیاز به fullstack: کلمات «داشبورد»، «پنل کاربری»، «dashboard»،
    «تحلیل بصری»، «نمودار»، «گزارش‌گیری تعاملی»، «OSINT»، «CRM»،
    «admin panel»، «UI for ...»، «وب‌اپ»، یا توضیح هر چیزی که از کاربر
    تعامل گرافیکی می‌خواهد + داده‌ای روی backend ذخیره می‌کند.
  - حتی اگر کاربر صریحاً نگفته "frontend"، اگر منطق پروژه برای کاربر
    نهایی UI لازم دارد، fullstack بزن.

تکنولوژی‌های ضروری (دیتابیس، احراز هویت، redis، …) را در technologies لیست کن.

# خروجی فقط JSON
{{
  "primary_type": "fullstack",
  "alternative_types": [],
  "technologies": ["PostgreSQL", "JWT", "Tailwind"],
  "reasoning": "یک پاراگراف کوتاه چرا این انتخاب بهترینه — خصوصاً اگر fullstack انتخاب کردی، چرا نه فقط fastapi"
}}"""

    response = await ai_generate(prompt, model_ids=model_ids)
    parsed = _extract_json(response)
    if not parsed or "primary_type" not in parsed:
        raise HTTPException(status_code=500, detail="پاسخ AI قابل تجزیه نبود")

    valid_types = {
        "python", "fastapi", "flask", "nextjs", "react", "node", "fullstack",
    }
    # Normalize hyphen variants
    if parsed["primary_type"] == "full-stack":
        parsed["primary_type"] = "fullstack"
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


# ─────────────────────────────────────────────────────────────────────────────
# 🆕 Pre-push audit — re-check generated files against the original goal
# ─────────────────────────────────────────────────────────────────────────────
# User explicitly asked for this: "وقتی پروژه ساخته میشه بتونم توسط مدل های
# فعال حاضر دوباره بررسی بشن فایل ها و همه چیز و ساختار همه چیزش با هدف
# ساخت تطبیق داده بشه و کلا یه بررسی مجدد اساسی انجام بشه ... قبل از اینکه
# بفرستمش تو گیت هاب".
# Each selected model independently audits the project. Findings are
# aggregated so the user can see consensus issues vs single-model nitpicks.
# ─────────────────────────────────────────────────────────────────────────────

class AuditProjectRequest(BaseModel):
    """Optional override: which models perform the audit. If empty, uses
    all currently active models (parity with the create flow)."""
    model_ids: List[str] = []


@router.post("/projects/{project_id}/audit")
async def audit_project(
    project_id: str, request: Optional[AuditProjectRequest] = None,
):
    """بررسی مجدد پروژهٔ ساخته‌شده توسط همهٔ مدل‌های فعال قبل از push به GitHub.

    هر مدل به‌صورت مستقل پروژه را در برابر هدف اولیه audit می‌کند و
    findings ها aggregate می‌شوند تا کاربر هم نظر هر مدل و هم اجماع را
    ببیند.
    """
    # 🐛 (audit-pass fix) — get_simple_creator wasn't imported at module
    # level; every other route does the same lazy import. Without this,
    # the audit endpoint crashed with NameError on first call.
    from ...services.simple_creator import get_simple_creator
    creator = get_simple_creator()
    project = creator.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="پروژه یافت نشد")

    # Pick the audit models. If caller didn't specify, use all available.
    from ...services.ai_manager import get_ai_manager
    ai_manager = get_ai_manager()
    available = ai_manager.get_available_models()
    available_by_id = {m.id: m for m in available}
    if request and request.model_ids:
        audit_ids = [m for m in request.model_ids if m in available_by_id]
        if not audit_ids:
            raise HTTPException(
                status_code=400,
                detail="هیچ‌کدام از model_ids درخواست‌شده فعال نیستند.",
            )
    else:
        # Use all available models so user gets multi-perspective audit
        audit_ids = [m.id for m in available]
    if not audit_ids:
        raise HTTPException(
            status_code=400,
            detail="هیچ مدل AI فعالی برای audit نیست.",
        )

    # Build the audit prompt — original goal + generated structure.
    # Cap each file body to keep prompt size sane (the audit doesn't need
    # to re-read every line — just structure + key signals).
    file_summaries: List[str] = []
    for f in project.files[:80]:  # ceiling so 200-file projects don't blow up
        body = (f.content or "")[:800]
        file_summaries.append(
            f"### `{f.path}` ({f.language or '?'})\n```\n{body}\n```"
        )
    file_text = "\n\n".join(file_summaries)

    audit_prompt = f"""تو یک معمار نرم‌افزاری ارشد هستی. این پروژه به‌تازگی توسط AI ساخته شده. وظیفهٔ تو یک **audit مستقل** قبل از push به GitHub است.

# هدف اولیهٔ کاربر
نام پروژه: {project.name}
نوع: {project.project_type}
تکنولوژی‌ها: {', '.join(project.technologies or []) or '—'}

توضیحات کاربر (هدف اصلی):
{project.description}

# ساختار خروجی AI
دایرکتوری‌ها: {', '.join(project.structure.get('directories', []) or [])}
نقطهٔ ورود: {project.structure.get('entry_point', '—')}
دستور اجرا: {project.structure.get('run_command', '—')}

# فایل‌های تولیدشده ({len(project.files)} فایل)
{file_text}

# وظیفهٔ تو
1. بررسی کن آیا فایل‌ها و ساختار با **هدف اولیه** تطبیق دارد یا نه
2. فایل‌های **مفقود حیاتی** را شناسایی کن (مثلاً اگر OSINT platform است ولی frontend ندارد، این bug است)
3. فایل‌های **اشتباه/زائد** را شناسایی کن (فایل‌هایی که وجود دارند ولی نباید باشند — مثلاً اگر پروژه CLI است ولی فایل web view ساخته شده، یا duplicate)
4. فایل‌های موجود را که **محتوای نادرست** دارند شناسایی کن (مثلاً main.py فقط `pass` دارد، یا route ای که توضیحات می‌گفت لازم است ولی schema غلط دارد، یا dependency ای که در requirements.txt مفقود است)
5. مشکلات **ساختاری** را پیدا کن (مثلاً Dockerfile entry-point اشتباه، dependency گم‌شده)
6. کیفیت کد را ارزیابی کن (production-ready vs scaffolding)
7. اگر همه چیز خوب است صریحاً بگو

📌 برای هر فایلی که محتوایش نیاز به اصلاح دارد، در `files_to_modify` با path دقیق + توضیح *آنچه که اشتباه است* + پیشنهاد *چه باید بشود* مشخص کن. کاربر می‌تواند per-file انتخاب کند کدام را regenerate کنیم.

📌 برای فایلی که نباید باشد، در `files_to_delete` با path دقیق + دلیل ذکر کن. حذف فقط با تأیید صریح کاربر انجام می‌شود.

خروجی فقط JSON با این فرمت:
{{
  "overall_score": 0-100,
  "ready_to_push": true/false,
  "missing_critical_files": ["frontend/src/app/page.tsx چون پروژه نیاز به UI دارد", ...],
  "files_to_modify": [
    {{"path": "backend/app/main.py", "issue": "فقط FastAPI() instance دارد، route ها register نشده", "suggestion": "router های auth, users, items را include کن"}},
    ...
  ],
  "files_to_delete": [
    {{"path": "backend/app/legacy.py", "reason": "بقایای template، در توضیحات خواسته نشده"}},
    ...
  ],
  "structural_issues": ["Dockerfile entry-point اشتباه است", ...],
  "quality_concerns": ["فایل foo.py فقط placeholder است، منطق واقعی ندارد", ...],
  "matches_goal": true/false,
  "goal_mismatch_reasons": ["..."],
  "suggestions_before_push": ["..."],
  "summary": "یک پاراگراف نظر کلی"
}}"""

    # Helper: coerce whatever the AI gave us into a usable dict.
    # _extract_json can return None or a non-dict (if AI emitted an array
    # at the top level). Defensive coercion so the aggregation step
    # below doesn't crash on `.get()` against a list.
    def _to_report_dict(raw) -> Dict[str, Any]:
        parsed = _extract_json(raw) if raw else None
        return parsed if isinstance(parsed, dict) else {}

    # Helper: parse a score that might be "85", "85/100", "85.5", or "high"
    # into 0-100 int. Returns 0 on unparseable input — keeps the average
    # math going without crashing.
    def _coerce_score(v) -> int:
        if isinstance(v, bool):  # bool is a subclass of int, exclude first
            return 0
        if isinstance(v, (int, float)):
            try:
                return max(0, min(100, int(v)))
            except (ValueError, TypeError):
                return 0
        if isinstance(v, str):
            import re as _re
            m = _re.search(r"-?\d+(?:\.\d+)?", v)
            if m:
                try:
                    return max(0, min(100, int(float(m.group(0)))))
                except (ValueError, TypeError):
                    return 0
        return 0

    # Run all models in parallel — sequential would take 30s × N models
    # which exceeds Render's gateway timeout (~100s) for any N > 3.
    # asyncio.gather with return_exceptions=True so a single slow/failing
    # model doesn't kill the whole audit.
    async def _audit_one(mid: str) -> Dict[str, Any]:
        try:
            response_text = await ai_generate(audit_prompt, model_ids=[mid])
            return {
                "model_id": mid,
                "ok": True,
                "report": _to_report_dict(response_text),
                "raw_response_excerpt": (response_text or "")[:600],
            }
        except Exception as e:
            return {
                "model_id": mid,
                "ok": False,
                "error": str(e)[:300],
            }

    raw_results = await asyncio.gather(
        *[_audit_one(mid) for mid in audit_ids],
        return_exceptions=True,
    )
    results_per_model: List[Dict[str, Any]] = []
    for mid, res in zip(audit_ids, raw_results):
        if isinstance(res, Exception):
            results_per_model.append({
                "model_id": mid,
                "ok": False,
                "error": str(res)[:300],
            })
        else:
            results_per_model.append(res)

    # Aggregate: union of issues, average score, majority verdict on ready.
    # A model is "successful" only if it returned a non-empty dict report.
    successful = [
        r for r in results_per_model
        if r["ok"] and isinstance(r.get("report"), dict) and r["report"]
    ]
    if not successful:
        raise HTTPException(
            status_code=500,
            detail="هیچ مدلی نتوانست audit را به JSON قابل تجزیه برساند.",
        )

    def _collect(field: str) -> List[str]:
        seen: List[str] = []
        for r in successful:
            raw_list = r["report"].get(field) or []
            if not isinstance(raw_list, list):
                continue
            for item in raw_list:
                text = item if isinstance(item, str) else (
                    str(item) if item is not None else ""
                )
                text = text.strip()
                if text and text not in seen:
                    seen.append(text)
        return seen

    def _collect_objects(field: str) -> List[Dict[str, str]]:
        """Same as _collect but for object lists (files_to_modify,
        files_to_delete). De-duped by path. If multiple models flag the
        same path, the first model's notes win."""
        seen_paths: Dict[str, Dict[str, str]] = {}
        for r in successful:
            raw_list = r["report"].get(field) or []
            if not isinstance(raw_list, list):
                continue
            for item in raw_list:
                if not isinstance(item, dict):
                    # Sometimes the AI emits a plain string here too —
                    # try to salvage as a path.
                    if isinstance(item, str):
                        path = _parse_clean_path(item)
                        if path and path not in seen_paths:
                            seen_paths[path] = {"path": path}
                    continue
                path = str(item.get("path") or "").strip()
                # Clean off any prose the AI tacked on
                clean = _parse_clean_path(path) or path
                if not clean or clean in seen_paths:
                    continue
                # Track which models flagged it so user sees consensus
                seen_paths[clean] = {
                    "path": clean,
                    "issue": str(item.get("issue") or "").strip()[:500],
                    "suggestion": str(item.get("suggestion") or "").strip()[:500],
                    "reason": str(item.get("reason") or "").strip()[:500],
                }
        return list(seen_paths.values())

    avg_score = round(
        sum(_coerce_score(r["report"].get("overall_score")) for r in successful)
        / len(successful)
    )
    ready_votes = sum(
        1 for r in successful if bool(r["report"].get("ready_to_push"))
    )
    goal_match_votes = sum(
        1 for r in successful if bool(r["report"].get("matches_goal"))
    )

    aggregated = {
        "models_consulted": len(audit_ids),
        # 🆕 expose the actual model IDs so frontend can show
        # "این audit توسط: claude, gemini انجام شد" — answer to the
        # user's question "همون مدلی که انتخاب شده کار انجام می‌ده؟"
        "model_ids_used": list(audit_ids),
        "models_succeeded": len(successful),
        "overall_score_avg": avg_score,
        "ready_to_push_majority": ready_votes > len(successful) / 2,
        "ready_to_push_votes": f"{ready_votes}/{len(successful)}",
        "matches_goal_majority": goal_match_votes > len(successful) / 2,
        "missing_critical_files": _collect("missing_critical_files"),
        "files_to_modify": _collect_objects("files_to_modify"),
        "files_to_delete": _collect_objects("files_to_delete"),
        "structural_issues": _collect("structural_issues"),
        "quality_concerns": _collect("quality_concerns"),
        "goal_mismatch_reasons": _collect("goal_mismatch_reasons"),
        "suggestions_before_push": _collect("suggestions_before_push"),
    }

    return {
        "success": True,
        "project_id": project_id,
        "aggregated": aggregated,
        "per_model": results_per_model,
    }


class FileToModify(BaseModel):
    path: str
    issue: str = ""
    suggestion: str = ""


class ApplyAuditFixesRequest(BaseModel):
    """🆕 Optional inputs to drive the auto-fix. Full CRUD:

      - missing_files: paths to ADD (generate via AI). If omitted and
        upgrade_to_fullstack is False, runs audit() first to discover.
      - files_to_modify: existing files to REGENERATE with audit context
        (the AI's "issue" + "suggestion" notes are fed into the new
        prompt so the regenerated content addresses the specific
        problem the audit flagged).
      - files_to_delete: paths to REMOVE. Both from disk and from
        project.files metadata. Only acted on when explicitly listed —
        never auto-derived from audit.
      - upgrade_to_fullstack: switch to fullstack template + add any
        missing template files (idempotent).

    Detective-1 scenario maps to: upgrade_to_fullstack=true AND
    files_to_modify=[{path: "backend/app/main.py", issue: "..."}, …]
    AND files_to_delete=[] (or whatever user picks).
    """
    missing_files: List[str] = []
    files_to_modify: List[FileToModify] = []
    files_to_delete: List[str] = []
    upgrade_to_fullstack: bool = False
    model_ids: List[str] = []  # ai-generate fallback chain


def _parse_clean_path(raw: str) -> Optional[str]:
    """Audit findings are free-form strings like
       'frontend/src/app/page.tsx چون پروژه نیاز به UI دارد'
    Extract just the path prefix. Returns None if no plausible path."""
    if not raw or not isinstance(raw, str):
        return None
    # First token that contains a '/' or ends in a known code extension
    import re as _re
    m = _re.match(r"[`'\"]?([A-Za-z0-9_\-./]+(?:\.[A-Za-z]{1,8}))", raw.strip())
    if not m:
        return None
    candidate = m.group(1).strip(" '\"`")
    # Reject obvious non-paths
    if " " in candidate or candidate.startswith(".") and "/" not in candidate:
        return None
    if "/" not in candidate and "." not in candidate:
        return None
    return candidate


@router.post("/projects/{project_id}/apply-fixes")
async def apply_audit_fixes(
    project_id: str, request: Optional[ApplyAuditFixesRequest] = None,
):
    """🛠 Apply auto-fixes from a prior audit result.

    Generates the missing files (from `request.missing_files` or from a
    fresh audit), optionally promotes the project_type to "fullstack" if
    the audit said the goal needs a UI but the structure only had
    backend.

    Idempotent: files that already exist are skipped, NOT overwritten.
    The user already trusted those files when they made the project; the
    auto-fix shouldn't silently mutate them.
    """
    from ...services.simple_creator import get_simple_creator
    creator = get_simple_creator()
    project = creator.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="پروژه یافت نشد")

    req = request or ApplyAuditFixesRequest()

    # 1) Determine which files to generate.
    files_to_create: List[str] = []
    audit_summary: Optional[Dict[str, Any]] = None
    if req.missing_files:
        # Caller passed explicit list — use it as-is, but still parse
        # paths defensively (the AI might have prefixed reasons).
        for raw in req.missing_files:
            clean = _parse_clean_path(raw)
            if clean and clean not in files_to_create:
                files_to_create.append(clean)
    elif (
        not req.upgrade_to_fullstack
        and not req.files_to_modify
        and not req.files_to_delete
    ):
        # No explicit list AND no other intent → run a fresh audit
        # to discover missing files. Other paths (upgrade, modify,
        # delete) have their own explicit input so we skip the
        # audit step to save AI tokens.
        try:
            audit_resp = await audit_project(
                project_id, AuditProjectRequest(model_ids=req.model_ids),
            )
            audit_summary = audit_resp.get("aggregated") or {}
            for raw in audit_summary.get("missing_critical_files") or []:
                clean = _parse_clean_path(raw)
                if clean and clean not in files_to_create:
                    files_to_create.append(clean)
        except HTTPException:
            raise
        except Exception as e:
            logger.warning(f"apply-fixes: inline audit failed: {e}")

    # 2) Promote to fullstack if requested — extends files_to_create with
    # the fullstack template's missing entries (idempotent).
    promoted = False
    if req.upgrade_to_fullstack and project.project_type != "fullstack":
        fullstack_struct = creator._get_default_structure("fullstack")
        existing_paths = {f.path for f in project.files}
        for spec in fullstack_struct.get("files") or []:
            p = spec.get("path") if isinstance(spec, dict) else None
            if p and p not in existing_paths and p not in files_to_create:
                files_to_create.append(p)
        # Update the type + structure metadata
        project.project_type = "fullstack"
        project.structure = {
            **(project.structure or {}),
            "directories": list(
                set((project.structure or {}).get("directories", []) or [])
                | set(fullstack_struct.get("directories", []) or [])
            ),
            "entry_point": fullstack_struct.get("entry_point"),
            "run_command": fullstack_struct.get("run_command"),
        }
        promoted = True

    if (
        not files_to_create and not promoted
        and not req.files_to_modify and not req.files_to_delete
    ):
        return {
            "success": True,
            "project_id": project_id,
            "files_added": [],
            "files_modified": [],
            "files_deleted": [],
            "files_skipped": [],
            "promoted_to_fullstack": False,
            "audit_summary": audit_summary,
            "note": "هیچ مورد قابل‌اصلاحی پیدا نشد.",
        }

    # 3) Per-category execution. Order: delete → modify → add. Deletes
    # first so the modify/add steps see an accurate "already exists"
    # state. Modify before add so an existing file the user wanted to
    # regenerate doesn't accidentally get treated as "already exists".
    existing_paths_set = {f.path for f in project.files}
    files_added: List[Dict[str, str]] = []
    files_modified: List[Dict[str, str]] = []
    files_deleted: List[Dict[str, str]] = []
    files_skipped: List[Dict[str, str]] = []

    # 🆕 (model attribution) — wrap ai_generate_with_meta and capture
    # which model actually answered each call. We snapshot the last
    # used model right before each _generate_file invocation so we
    # know which model produced THAT file. Defensive against test
    # mocks / future utils that may not return the (content, model)
    # tuple — fall back gracefully to no-attribution.
    _last_model: Dict[str, str] = {"id": ""}

    async def _ai_gen(prompt: str):
        result = await ai_generate_with_meta(
            prompt, model_ids=req.model_ids,
        )
        if isinstance(result, tuple) and len(result) == 2:
            content, used = result
            _last_model["id"] = str(used or "")
            return content
        # Mock or legacy util returned a bare string
        _last_model["id"] = ""
        return result

    project_dir = creator.workspace / project.id
    project_dir.mkdir(parents=True, exist_ok=True)

    # 3a) DELETE — remove from disk + drop from project.files. Only
    # acted on when explicitly listed by the caller; we never auto-derive
    # delete intent from audit (too destructive to do silently).
    for raw_path in (req.files_to_delete or []):
        clean = _parse_clean_path(raw_path) or raw_path
        # Defense against path traversal: stay inside project_dir
        full_path = (project_dir / clean).resolve()
        try:
            full_path.relative_to(project_dir.resolve())
        except ValueError:
            files_skipped.append({
                "path": clean, "reason": "path outside project workspace",
            })
            continue
        if not full_path.exists():
            files_skipped.append({
                "path": clean, "reason": "file not found",
            })
            continue
        try:
            if full_path.is_file():
                full_path.unlink()
            # Drop from project.files
            project.files = [f for f in project.files if f.path != clean]
            existing_paths_set.discard(clean)
            files_deleted.append({"path": clean})
        except Exception as e:
            files_skipped.append({
                "path": clean, "reason": f"delete failed: {str(e)[:200]}",
            })

    # 3b) MODIFY — regenerate existing files with audit context. We feed
    # the AI a prompt that includes the issue + suggestion notes so the
    # regenerated content addresses the specific problem the audit
    # flagged, not just a fresh "write me main.py" prompt.
    for spec in (req.files_to_modify or []):
        # `spec` is a FileToModify (pydantic model)
        target_path = (
            _parse_clean_path(spec.path) or spec.path
        ) if hasattr(spec, "path") else None
        if not target_path:
            files_skipped.append({"path": "?", "reason": "no path"})
            continue
        existing = next(
            (f for f in project.files if f.path == target_path), None,
        )
        if existing is None:
            # Not present — fall back to "add" behavior so the user's
            # intent isn't silently dropped.
            files_to_create.append(target_path)
            continue
        try:
            issue = (spec.issue or "").strip() if hasattr(spec, "issue") else ""
            sugg = (spec.suggestion or "").strip() if hasattr(spec, "suggestion") else ""
            mod_prompt_extra = (
                f"\n\n📌 این فایل قبلاً وجود دارد و audit مشخص کرد:\n"
                f"- مشکل: {issue or '(ذکر نشد)'}\n"
                f"- پیشنهاد: {sugg or '(ذکر نشد)'}\n"
                f"محتوای فعلی (مرجع):\n```\n{(existing.content or '')[:2000]}\n```\n"
                f"محتوای جدید را بنویس که مشکل را برطرف کند ولی منطق درست "
                f"قبلی را حفظ کند."
            )
            # _generate_file takes (name, desc, type, path, file_desc, ai_gen);
            # we pass the regeneration context as file_desc so it lands
            # inside the AI prompt.
            _last_model["id"] = ""
            new_content = await creator._generate_file(
                project.name,
                project.description + mod_prompt_extra,
                project.project_type,
                target_path,
                f"regenerate to address: {issue}",
                _ai_gen,
            )
            used_model = _last_model["id"]
            full_path = project_dir / target_path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            import aiofiles as _aiofiles
            async with _aiofiles.open(full_path, "w") as fh:
                await fh.write(new_content)
            from datetime import datetime as _dt_mod
            existing.content = new_content
            existing.generated_by = used_model
            existing.generated_at = _dt_mod.now().isoformat()
            files_modified.append({
                "path": target_path,
                "size": len(new_content),
                "issue_addressed": issue[:200],
                "generated_by": used_model,
            })
        except Exception as e:
            files_skipped.append({
                "path": target_path,
                "reason": f"modify failed: {str(e)[:200]}",
            })

    # 3c) ADD — generate missing files. Skip silently if a path now
    # exists (might be the case if delete+add raced on the same path).
    for path in files_to_create:
        if path in existing_paths_set:
            files_skipped.append({"path": path, "reason": "already exists"})
            continue
        try:
            _last_model["id"] = ""
            content = await creator._generate_file(
                project.name,
                project.description,
                project.project_type,
                path,
                "",  # file_desc — audit didn't always give one
                _ai_gen,
            )
            used_model = _last_model["id"]
            full_path = project_dir / path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            import aiofiles as _aiofiles
            async with _aiofiles.open(full_path, "w") as fh:
                await fh.write(content)
            from ...services.simple_creator import ProjectFile as _ProjectFile
            from datetime import datetime as _dt_now
            project.files.append(_ProjectFile(
                path=path,
                content=content,
                language=creator._detect_language(path),
                generated_by=used_model,
                generated_at=_dt_now.now().isoformat(),
            ))
            existing_paths_set.add(path)
            files_added.append({
                "path": path,
                "language": creator._detect_language(path),
                "size": len(content),
                "generated_by": used_model,
            })
        except Exception as e:
            files_skipped.append({"path": path, "reason": str(e)[:300]})

    # 4) Persist the updated project meta
    try:
        await creator._save_project_meta(project)
    except Exception as e:
        logger.warning(f"apply-fixes: save_project_meta failed: {e}")

    return {
        "success": True,
        "project_id": project_id,
        "files_added": files_added,
        "files_modified": files_modified,
        "files_deleted": files_deleted,
        "files_skipped": files_skipped,
        "promoted_to_fullstack": promoted,
        "new_project_type": project.project_type,
        "total_files_now": len(project.files),
        "audit_summary": audit_summary,
    }


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
