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
    prompt: str,
    model_ids: Optional[List[str]] = None,
    *,
    max_tokens: int = 4000,
) -> tuple:
    """🆕 (model attribution) — same as ai_generate but returns a
    (content, used_model_id) tuple so callers can record which model
    actually answered. The fallback chain semantics are unchanged: try
    each model_id in order, return on first success.

    The simple_creator's _tracked_ai_generate unpacks this tuple to
    populate ProjectFile.generated_by, which the UI then displays per
    file. Without this attribution the user couldn't tell which of
    their selected models produced which file.

    🆕 `max_tokens` override — audit needs more headroom (8000) than
    file-generation (4000) because its JSON output enumerates per-file
    issues + suggestions. Truncated audit responses (at 4000) come back
    as malformed JSON → user sees "couldn't parse" with no signal as
    to why. Callers should bump this for any long-form JSON response.
    """
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
                max_tokens=max_tokens,
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


async def ai_generate(
    prompt: str,
    model_ids: Optional[List[str]] = None,
    *,
    max_tokens: int = 4000,
) -> str:
    """Back-compat shim — returns just the content string.

    Existing callers (audit prompt generation, _detect_project_type,
    idea_to_prompt) don't care which model answered; they only need
    the text. For attribution-aware callers use ai_generate_with_meta.
    """
    content, _model = await ai_generate_with_meta(
        prompt, model_ids, max_tokens=max_tokens,
    )
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

    # 🐛 (audit fix) — Render key از env یا Settings DB
    render_key = _get_render_api_key_value()
    if not render_key:
        raise HTTPException(status_code=400, detail="کلید Render تنظیم نشده. به /settings برو و کلید رو وارد کن.")

    # دریافت deploy manager
    deploy_manager = get_deploy_manager()
    deploy_manager.configure_render(render_key)

    # 🐛 (deploy-to-render fix) — اولویت‌بندی منبع repo:
    #   1) override صریح از request (کاربر URL داده)
    #   2) repo جدای پروژه (از push_to_github، مثلاً Detective-1)
    #   3) fallback به github_storage داخلی (ai-workspace-data) — آخرین
    #      راه چاره، چون اگر این مسیر طی شود root_dir باید subpath داشته
    #      باشد، در حالی که حالت ۲ پروژه در root repo جدا است.
    github_repo_url = None
    source_kind = "none"  # "request" | "project" | "internal_storage"
    github_branch = (request.github_branch if request else "main") or "main"
    # subpath فقط برای fallback به repo داخلی استفاده می‌شود.
    # برای repo جدا که از push_to_github آمده، پروژه در root است.
    root_dir = ""

    if request and request.github_repo_url:
        github_repo_url = request.github_repo_url
        source_kind = "request"
        # برای override کاربر هم پیش‌فرض root خالی (پروژه‌های push شدهٔ کاربر
        # معمولاً در root repo هستند)
        root_dir = ""
    elif project.github_repo_url:
        # حالت معمول: کاربر قبلاً «GitHub به push» را زده — اطلاعات repo
        # جدا را روی project داریم.
        github_repo_url = project.github_repo_url
        source_kind = "project"
        github_branch = project.github_default_branch or github_branch
        root_dir = ""  # پروژه در root repo جدا است (Detective-1 use case)
    else:
        # 🆕 (deploy-to-render fix v2) — Smart fallback قبل از internal
        # storage: اگر کاربر قبلاً push کرده ولی پیش از این فیکس
        # (project.json قدیمی فاقد github_*)، یا «push» را با کد قدیم زده،
        # نام estimated repo را با GitHub API چک کن. اگر repo با نام پروژه
        # وجود داشت، از همان استفاده کن — تا کاربر مجبور به re-push نشود.
        try:
            token = _get_github_token_value()
            if token:
                import aiohttp
                guessed_name = _normalize_repo_name(project.name)
                async with aiohttp.ClientSession() as _s:
                    async with _s.get(
                        "https://api.github.com/user",
                        headers={
                            "Authorization": f"Bearer {token}",
                            "Accept": "application/vnd.github+json",
                        },
                    ) as _ur:
                        if _ur.status == 200:
                            _u = await _ur.json()
                            _owner = _u.get("login")
                            if _owner:
                                async with _s.get(
                                    f"https://api.github.com/repos/{_owner}/{guessed_name}",
                                    headers={
                                        "Authorization": f"Bearer {token}",
                                        "Accept": "application/vnd.github+json",
                                    },
                                ) as _rr:
                                    if _rr.status == 200:
                                        _ri = await _rr.json()
                                        github_repo_url = _ri.get("html_url")
                                        github_branch = (
                                            _ri.get("default_branch") or github_branch
                                        )
                                        source_kind = "github_lookup"
                                        root_dir = ""
                                        # یک بار روی project ذخیره کن تا
                                        # دفعهٔ بعد به این مسیر کند نیاز نباشد.
                                        try:
                                            project.github_owner = _owner
                                            project.github_repo = guessed_name
                                            project.github_repo_url = github_repo_url
                                            project.github_default_branch = github_branch
                                            await creator._save_project_meta(project)
                                        except Exception as _save_e:
                                            logger.warning(
                                                f"deploy: backfill github_* "
                                                f"on project failed: {_save_e}"
                                            )
        except Exception as _lookup_e:
            logger.warning(f"deploy: GitHub repo lookup failed: {_lookup_e}")

        # fallback آخر: repo داخلی data — root باید subpath داشته باشد
        if not github_repo_url:
            github_storage = get_github_storage()
            if github_storage.token and github_storage.owner and github_storage.repo:
                github_repo_url = f"https://github.com/{github_storage.owner}/{github_storage.repo}"
                source_kind = "internal_storage"
                root_dir = f"ai-workspace/projects/{project_id}/generated"

    if not github_repo_url:
        # اگر GitHub repo نداریم، راهنمای دستی بده
        return {
            "success": True,
            "deployed": False,
            "message": "برای Deploy خودکار، اول پروژه رو به GitHub push کن.",
            "project_id": project_id,
            "instructions": [
                "۱. روی دکمهٔ «GitHub به push» همین صفحه کلیک کن",
                "۲. صبر کن repo ساخته و فایل‌ها push شوند",
                "۳. سپس «Deploy به Render» را دوباره بزن",
            ]
        }

    try:
        # Deploy به Render
        deployment = await deploy_manager.quick_deploy(
            project_id=project_id,
            project_name=project.name,
            project_type=project.project_type,
            github_repo_url=github_repo_url,
            github_branch=github_branch,
            root_dir=root_dir,
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
# 🆕 (creator parity with inspector) — AI multi-service deploy
# ─────────────────────────────────────────────────────────────────────────────
# Inspector tab has a much better deploy flow: AI reads the repo,
# decides how many services (fullstack → 2), what type (static_site for
# Vite SPA, web_service for FastAPI/Express), build/start commands, env
# vars. Creator only did a single-service docker deploy → fullstack
# projects like Detective-1 broke.
#
# This endpoint reuses the inspector helper `_ai_analyze_repo_only` (the
# DB-less variant) so Creator gets the same intelligence without touching
# the Project DB model. Per-service plan (free/starter) is forwarded to
# the Render API.


class DeployRenderAIRequest(BaseModel):
    """درخواست deploy هوشمند با AI."""
    plan: str = "starter"  # "free" | "starter" — برای الان فقط در پاسخ نگاه‌داشته
    env_vars_overrides: dict = {}  # {service_name: {KEY: value}}


@router.post("/projects/{project_id}/deploy/render-ai")
async def deploy_project_render_ai(
    project_id: str,
    request: DeployRenderAIRequest = DeployRenderAIRequest(),
):
    """Deploy یک پروژه به Render با تحلیل AI — همانند Inspector.

    تفاوت با /projects/{id}/deploy:
      - برای fullstack ها چند سرویس می‌سازد (frontend + backend جدا)
      - static_site (Vite SPA) را تشخیص می‌دهد و درست تنظیم می‌کند
      - build/start/publish path را AI تصمیم می‌گیرد
      - env vars را از .env/.env.example استخراج می‌کند و خالی‌ها را
        به کاربر گزارش می‌دهد
    """
    from ...services.simple_creator import get_simple_creator
    from ...services.deploy_service import RenderDeployService

    creator = get_simple_creator()
    project = creator.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="پروژه یافت نشد")

    # 🐛 (audit fix) — Render API key باید از Settings DB هم خوانده شود،
    # نه فقط env var. Inspector این کار را می‌کرد (api_key_render در
    # Settings table). کاربر معمولاً از پنل /settings کلید را وارد می‌کند
    # که در DB ذخیره می‌شود — اگر فقط env را چک کنیم، 400 می‌دهیم در
    # حالی که کلید واقعاً موجود است.
    render_key = _get_render_api_key_value()
    if not render_key:
        raise HTTPException(
            status_code=400,
            detail=(
                "کلید Render تنظیم نشده. به /settings برو و کلید رو "
                "وارد کن، یا RENDER_API_KEY را در environment ست کن."
            ),
        )

    # ── ۱) اطلاعات repo — همان منطق deploy_project ──
    # برای Creator فقط حالت "project field" + "github_lookup" قابل
    # قبول است. internal_storage در حالت AI معنا ندارد چون AI روی repo
    # واقعی پروژه (Detective-1) کار می‌کند نه روی repo داخلی data.
    owner = project.github_owner
    repo_name = project.github_repo
    repo_url = project.github_repo_url
    branch = project.github_default_branch or "main"

    if not (owner and repo_name and repo_url):
        # smart lookup مشابه deploy_project
        token = _get_github_token_value()
        if token:
            try:
                import aiohttp
                guessed = _normalize_repo_name(project.name)
                async with aiohttp.ClientSession() as _s:
                    async with _s.get(
                        "https://api.github.com/user",
                        headers={
                            "Authorization": f"Bearer {token}",
                            "Accept": "application/vnd.github+json",
                        },
                    ) as _ur:
                        if _ur.status == 200:
                            _u = await _ur.json()
                            _o = _u.get("login")
                            if _o:
                                async with _s.get(
                                    f"https://api.github.com/repos/{_o}/{guessed}",
                                    headers={
                                        "Authorization": f"Bearer {token}",
                                        "Accept": "application/vnd.github+json",
                                    },
                                ) as _rr:
                                    if _rr.status == 200:
                                        _ri = await _rr.json()
                                        owner = _o
                                        repo_name = guessed
                                        repo_url = _ri.get("html_url")
                                        branch = _ri.get("default_branch") or branch
                                        # backfill برای دفعهٔ بعد
                                        try:
                                            project.github_owner = owner
                                            project.github_repo = repo_name
                                            project.github_repo_url = repo_url
                                            project.github_default_branch = branch
                                            await creator._save_project_meta(project)
                                        except Exception:
                                            pass
            except Exception as _e:
                logger.warning(f"deploy-render-ai: lookup failed: {_e}")

    if not (owner and repo_name and repo_url):
        return {
            "success": False,
            "error": "no_github_repo",
            "message": (
                "این پروژه هنوز روی GitHub push نشده. اول روی دکمهٔ "
                "«GitHub به push» کلیک کن، صبر کن کامل شود، سپس دوباره Deploy بزن."
            ),
        }

    # ── ۲) تحلیل AI ──
    github_token = _get_github_token_value() or ""
    try:
        from .render_logs import _ai_analyze_repo_only
        ai_result = await _ai_analyze_repo_only(
            owner=owner, repo=repo_name, branch=branch,
            github_token=github_token, github_url=repo_url,
            model_id=None,  # fallback به gemini-2.0-flash
        )
    except Exception as e:
        logger.exception(f"deploy-render-ai: AI analyze failed: {e}")
        raise HTTPException(
            status_code=500, detail=f"خطا در تحلیل AI: {str(e)[:200]}",
        )

    services_plan_raw = ai_result.get("services", [])
    analysis_text = ai_result.get("analysis", "")
    model_used = ai_result.get("model_used", "unknown")

    # 🐛 (infra-filter fix) — AI گاهی postgres/redis/neo4j/minio/qdrant
    # را به‌عنوان web_service Docker در plan می‌گذارد (چون در
    # docker-compose پروژه هستند). Render این‌ها را به‌عنوان web_service
    # نمی‌سازد → ۵ خطا در ساخت. درست: postgres/redis توسط
    # provision_postgres / provision_redis (Render managed) ساخته شوند،
    # neo4j/minio/qdrant external هستند (Render پشتیبانی ندارد).
    # این filter سرویس‌های infra را از services_plan حذف می‌کند.
    _INFRA_KEYWORDS = (
        "postgres", "postgresql", "pgvector",
        "redis", "keyvalue",
        "neo4j", "minio", "qdrant", "mongo", "mongodb",
        "rabbitmq", "kafka", "elasticsearch", "elastic",
        "mysql", "mariadb",
    )

    def _is_infra_service(svc: dict) -> bool:
        name = (svc.get("name") or "").lower()
        role = (svc.get("role") or "").lower()
        for kw in _INFRA_KEYWORDS:
            if kw in name or kw in role:
                return True
        return False

    services_plan = [s for s in services_plan_raw if not _is_infra_service(s)]
    infra_skipped = [s for s in services_plan_raw if _is_infra_service(s)]

    if not services_plan:
        return {
            "success": False,
            "error": "ai_no_services",
            "analysis": analysis_text,
            "model_used": model_used,
            "message": (
                "AI نتوانست تشخیص دهد کدام سرویس‌ها باید ساخته شوند. "
                "لاگ‌های backend را برای جزئیات ببین."
            ),
        }

    # ── ۳) 🆕 (empty-dockerfile guard) قبل از create_service، Dockerfile
    # موثر هر سرویس را روی GitHub چک کن. اگر خالی است (Creator engine
    # گاهی Dockerfile placeholder تولید می‌کند که فقط چند بایت دارد)،
    # Render در build fail می‌دهد با
    # `error: failed to solve: the Dockerfile cannot be empty`.
    # تشخیص بده و runtime را به native (Python برای backend، Vite
    # static_site برای frontend) override کن.
    from .render_logs import _read_github_file
    docker_overrides: Dict[str, Dict[str, Any]] = {}
    for svc in services_plan:
        svc_name = svc.get("name", "app")
        svc_root = svc.get("root_dir", ".")
        svc_role = (svc.get("role", "") or "").lower()
        # Dockerfile path نسبت به root repo
        dockerfile_path = (
            "Dockerfile" if svc_root in (".", "", None)
            else f"{svc_root.rstrip('/')}/Dockerfile"
        )
        df_content = await _read_github_file(
            owner, repo_name, dockerfile_path, branch, github_token,
        )
        # Dockerfile موثر بودن: > 100 byte و حداقل یک خط non-comment
        df_usable = False
        if df_content:
            stripped_lines = [
                ln.strip() for ln in df_content.splitlines()
                if ln.strip() and not ln.strip().startswith("#")
            ]
            df_usable = len(df_content) > 100 and len(stripped_lines) >= 2
        if df_usable:
            continue  # Dockerfile خوب است، تغییری نده

        # Dockerfile قابل استفاده نیست → بر اساس role override کن
        if svc_role == "frontend":
            # احتمالاً Vite/React SPA → static_site
            override = {
                "service_type": "static_site",
                "build_command": (
                    "npm install && npm run build && "
                    "echo '/*    /index.html   200' > dist/_redirects"
                ),
                "start_command": None,
                "publish_path": "dist",
                "project_type": "vite",
                "notes_append": (
                    "⚠️ Dockerfile خالی بود — به static_site (Vite) تبدیل شد. "
                    "اگر پروژه Next.js است، باید Dockerfile معتبر در repo قرار دهی."
                ),
            }
        elif svc_role == "backend":
            # احتمالاً FastAPI/Flask/Django → Python native
            override = {
                "service_type": "web_service",
                "build_command": (
                    "pip install --upgrade pip setuptools && "
                    "pip install -r requirements.txt"
                ),
                "start_command": (
                    "uvicorn main:app --host 0.0.0.0 --port $PORT"
                ),
                "publish_path": None,
                "project_type": "fastapi",
                "notes_append": (
                    "⚠️ Dockerfile خالی بود — به Python native (FastAPI) تبدیل شد. "
                    "اگر start command درست نیست، در Render dashboard اصلاح کن."
                ),
            }
        else:
            # نقش نامعلوم → نمی‌توان override کرد، گزارش بده
            override = {
                "skip_with_error": (
                    f"Dockerfile خالی است و role=`{svc_role}` نامعلوم — "
                    f"override خودکار ممکن نیست."
                ),
            }
        docker_overrides[svc_name] = override

    # ── ۴) 🆕 (env auto-fill) — برای هر سرویس، env vars را resolve کن:
    # API keys از Settings DB، SECRET_KEY ها تولید، cross-service ها
    # mark می‌شوند. خروجی: env_resolution[svc_name] = {var: {value, source, ...}}
    env_resolution: Dict[str, Dict[str, Dict[str, Any]]] = {}
    for svc in services_plan:
        svc_name = svc.get("name", "app")
        per_var: Dict[str, Dict[str, Any]] = {}
        # request override به‌عنوان user-supplied value
        ovr = (request.env_vars_overrides or {}).get(svc_name, {}) or {}
        for k, v in (svc.get("env_vars") or {}).items():
            initial = (ovr.get(k) if k in ovr else v) or ""
            per_var[k] = _resolve_env_var(k, str(initial or ""))
        env_resolution[svc_name] = per_var

    # ── 🆕 ۴.۵) Auto-provision Postgres + Redis اگر هر سرویس به آن‌ها نیاز
    # دارد. این بخش زمان‌بر است (۱-۳ دقیقه polling تا available) ولی
    # خواستهٔ کاربر این است: «نباید کاری دستی انجام شود». Render API
    # رایگان Postgres و Key Value (Redis) را پشتیبانی می‌کند.
    # تشخیص: اگر بین env vars (کل سرویس‌ها) `DATABASE_URL` یا
    # `POSTGRES_*` یا `REDIS_URL` یا `CELERY_*_URL` وجود دارد و source
    # آن `external` است (نشانهٔ خالی-بودن)، یک instance بساز و
    # connectionString را در همهٔ سرویس‌های نیازمند پر کن.
    provisioned: Dict[str, Dict[str, Any]] = {}
    _need_postgres = False
    _need_redis = False
    _PG_VAR_KEYWORDS = ("DATABASE_URL", "POSTGRES_URL", "DB_URL")
    _REDIS_VAR_KEYWORDS = (
        "REDIS_URL", "CELERY_BROKER_URL", "CELERY_RESULT_BACKEND",
        "CELERY_BACKEND_URL",
    )
    for _svc_name, per_var in env_resolution.items():
        for _k, _info in per_var.items():
            _ku = _k.upper()
            if any(p in _ku for p in _PG_VAR_KEYWORDS):
                if _info.get("source") in ("external", "unknown") and not _info.get("resolved"):
                    _need_postgres = True
            if any(p in _ku for p in _REDIS_VAR_KEYWORDS):
                if _info.get("source") in ("external", "unknown") and not _info.get("resolved"):
                    _need_redis = True

    if _need_postgres or _need_redis:
        # یک نام پایه از project برای resource ها
        _base_name = (
            project.github_repo
            or _normalize_repo_name(project.name)
            or project_id
        ).lower().replace("_", "-")[:40]
        _provision_svc = RenderDeployService(render_key)
        try:
            if _need_postgres:
                pg_result = await _provision_svc.provision_postgres(
                    name=f"{_base_name}-db",
                )
                if pg_result.get("success") and pg_result.get("connectionString"):
                    provisioned["postgres"] = {
                        "id": pg_result["id"],
                        "name": pg_result["name"],
                        "connection_string": pg_result["connectionString"],
                    }
                    # توزیع روی env_resolution
                    for _svc_name, per_var in env_resolution.items():
                        for _k, _info in per_var.items():
                            if any(p in _k.upper() for p in _PG_VAR_KEYWORDS):
                                if not _info.get("resolved"):
                                    _info["value"] = pg_result["connectionString"]
                                    _info["source"] = "render_provisioned"
                                    _info["resolved"] = True
                else:
                    logger.warning(
                        f"provision_postgres failed: {pg_result.get('error')}"
                    )
            if _need_redis:
                rd_result = await _provision_svc.provision_redis(
                    name=f"{_base_name}-redis",
                )
                if rd_result.get("success") and rd_result.get("connectionString"):
                    provisioned["redis"] = {
                        "id": rd_result["id"],
                        "name": rd_result["name"],
                        "connection_string": rd_result["connectionString"],
                    }
                    for _svc_name, per_var in env_resolution.items():
                        for _k, _info in per_var.items():
                            if any(p in _k.upper() for p in _REDIS_VAR_KEYWORDS):
                                if not _info.get("resolved"):
                                    _info["value"] = rd_result["connectionString"]
                                    _info["source"] = "render_provisioned"
                                    _info["resolved"] = True
                else:
                    logger.warning(
                        f"provision_redis failed: {rd_result.get('error')}"
                    )
        finally:
            await _provision_svc.close()

    # ── ۵) ساخت هر سرویس روی Render — ترتیب: backend اول (تا URL آن
    # برای frontend در دسترس باشد)، static و web_service فرعی بعد.
    def _service_sort_key(s: dict) -> int:
        role = (s.get("role") or "").lower()
        if role == "backend":
            return 0
        if role == "frontend":
            return 2
        return 1  # سایر نقش‌ها وسط

    ordered_services = sorted(services_plan, key=_service_sort_key)
    # نقشهٔ backend URL ها برای cross-service ref
    backend_urls: Dict[str, str] = {}

    deploy_svc = RenderDeployService(render_key)
    created: List[Dict[str, Any]] = []
    errors: List[Dict[str, Any]] = []
    try:
        for svc in ordered_services:
            svc_name = svc.get("name", "app")
            svc_type = svc.get("service_type", "web_service")
            svc_role = (svc.get("role") or "").lower()

            # 🆕 اعمال docker override اگر Dockerfile خالی بود
            do = docker_overrides.get(svc_name, {})
            if do.get("skip_with_error"):
                errors.append({
                    "name": svc_name,
                    "role": svc.get("role", "app"),
                    "error": do["skip_with_error"],
                })
                continue
            project_type_param = do.get("project_type") or svc.get("role", "app")
            service_type_param = do.get("service_type") or svc_type
            build_cmd_param = do.get("build_command") or svc.get("build_command")
            start_cmd_param = (
                do.get("start_command")
                if "start_command" in do else svc.get("start_command")
            )
            publish_path_param = (
                do.get("publish_path")
                if "publish_path" in do else svc.get("publish_path")
            )

            # 🆕 جمع‌آوری env vars resolved، شامل cross-service fill برای
            # frontend (NEXT_PUBLIC_API_URL = backend URL اگر backend
            # قبلاً deploy شده).
            resolved = env_resolution.get(svc_name, {})
            final_envs: Dict[str, str] = {}
            for var_name, info in resolved.items():
                if info["resolved"]:
                    final_envs[var_name] = info["value"]
                    continue
                # cross-service: اگر backend موجود است، استفاده کن
                if info["source"] == "cross_service" and backend_urls:
                    backend_url = next(iter(backend_urls.values()))
                    final_envs[var_name] = backend_url
                    info["value"] = backend_url
                    info["source"] = "cross_service_resolved"
                    info["resolved"] = True
                else:
                    # هنوز خالی — Render خواهد دید
                    final_envs[var_name] = info.get("value", "")

            result = await deploy_svc.create_service(
                name=svc_name,
                project_type=project_type_param,
                github_repo_url=repo_url,
                github_branch=branch,
                root_dir=svc.get("root_dir", "."),
                build_command=build_cmd_param,
                start_command=start_cmd_param,
                service_type=service_type_param,
                publish_path=publish_path_param,
                env_vars=final_envs if final_envs else None,
            )
            if result.get("success"):
                final_notes = svc.get("notes", "") or ""
                if do.get("notes_append"):
                    final_notes = (
                        f"{final_notes}\n{do['notes_append']}".strip()
                    )
                # اگر backend است، URL را برای frontend بعدی نگه دار
                svc_url = result.get("url") or ""
                if svc_role == "backend" and svc_url:
                    backend_urls[svc_name] = svc_url
                created.append({
                    "name": result.get("name"),
                    "service_id": result.get("service_id"),
                    "role": svc.get("role", "app"),
                    "service_type": service_type_param,
                    "dashboard_url": result.get("dashboard_url"),
                    "url": svc_url,
                    "notes": final_notes,
                    "docker_overridden": bool(do.get("notes_append")),
                    "env_resolution": resolved,  # برای frontend نمایش
                })
            else:
                errors.append({
                    "name": svc_name,
                    "role": svc.get("role", "app"),
                    "error": result.get("error", "unknown"),
                })
    finally:
        await deploy_svc.close()

    # 🆕 (env auto-fill) — خلاصهٔ resolve:
    #   auto_resolved: لیست env های که خودکار پر شدند (source != external/unknown)
    #   still_manual:  لیست env های که هنوز نیاز به اقدام کاربر دارند، با hint
    auto_resolved: List[Dict[str, str]] = []
    still_manual: List[Dict[str, str]] = []
    for svc_name, per_var in env_resolution.items():
        for k, info in per_var.items():
            if info["resolved"]:
                auto_resolved.append({
                    "service": svc_name,
                    "var": k,
                    "source": info["source"],
                    # مقدار را نمایش نمی‌دهیم (sensitivity) — فقط منبع
                })
            else:
                still_manual.append({
                    "service": svc_name,
                    "var": k,
                    "source": info["source"],
                    "hint": info.get("hint", ""),
                })

    return {
        "success": len(created) > 0,
        "created": created,
        "errors": errors,
        "analysis": analysis_text,
        "model_used": model_used,
        "project_name": project.name,
        "github_url": repo_url,
        "branch": branch,
        "auto_resolved": auto_resolved,
        "still_manual": still_manual,
        # 🆕 (auto-provision) — Postgres/Redis ای که خودکار ساخته شدند
        "provisioned": provisioned,
        # 🆕 (infra-filter) — سرویس‌های infra که از plan AI حذف شدند
        # (به‌جای ساخت اشتباه به‌عنوان web_service). فقط برای اطلاع
        # کاربر؛ postgres/redis از طریق provisioned ساخته می‌شوند،
        # neo4j/minio/qdrant external می‌مانند.
        "infra_skipped": [
            {"name": s.get("name", "?"), "role": s.get("role", "?")}
            for s in infra_skipped
        ],
        # backward compat — frontend قدیم empty_env_vars را می‌خواند
        "empty_env_vars": [
            f"{x['service']}: {x['var']}" for x in still_manual
        ],
        "plan": request.plan,
        "message": (
            f"✅ {len(created)} سرویس ساخته شد"
            + (f" | 🗄 {len(provisioned)} resource ساخته شد" if provisioned else "")
            + (f" | 🔐 {len(auto_resolved)} env خودکار" if auto_resolved else "")
            + (f" | ⚠️ {len(still_manual)} env دستی" if still_manual else "")
            + (f" | ❌ {len(errors)} خطا" if errors else "")
        ),
    }


@router.get("/projects/{project_id}/deploy/render-prefill")
async def deploy_project_render_prefill(project_id: str):
    """🆕 (creator free-plan UX) — اطلاعات لازم برای ریدایرکت به
    Render dashboard در حالت «پلن رایگان».

    Frontend با گرفتن این پاسخ، کاربر را به
    `dashboard.render.com/select-repo?type=web&q=<owner>/<repo>`
    می‌فرستد تا با dropdown سرویس را خودش بسازد.
    """
    from ...services.simple_creator import get_simple_creator
    creator = get_simple_creator()
    project = creator.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="پروژه یافت نشد")

    owner = project.github_owner
    repo_name = project.github_repo
    repo_url = project.github_repo_url

    if not (owner and repo_name and repo_url):
        return {
            "success": False,
            "error": "no_github_repo",
            "message": (
                "این پروژه هنوز روی GitHub push نشده. اول دکمهٔ «GitHub به push»."
            ),
        }

    full = f"{owner}/{repo_name}"
    return {
        "success": True,
        "owner": owner,
        "repo": repo_name,
        "full_name": full,
        "github_url": repo_url,
        "render_dashboard_url": (
            f"https://dashboard.render.com/select-repo?type=web&q={full}"
        ),
    }


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
    # 🐛 (audit quality fix) — previous caps were 80 files × 800 chars
    # each (~64KB max). For multi-file projects, audit was seeing only
    # the prefix of every file, so it would re-flag the same "stub
    # detected" issue even after a regen that fixed it past byte 800.
    # The user reported scores going DOWN after apply-fixes; this was
    # a major contributor.
    #
    # 🐛 (streaming-timeout fix) — first attempt bumped to 200×4000
    # (~800KB) but Claude opus then streamed the response for 60+
    # seconds on a 70-file project and hit max_tokens before completing
    # the JSON. User saw "هیچ مدلی نتوانست audit را به JSON قابل تجزیه
    # برساند" + 65s wait. Settled at 100 files × 2000 chars (~200KB) —
    # still 2.5× the original visibility but small enough that opus
    # responds in ~10s and stays within the 8000-token output budget.
    MAX_FILES = 100
    MAX_CHARS_PER_FILE = 2000

    def _audit_priority(path: str) -> int:
        """Lower = higher priority. Entry points, configs, mains first."""
        p = (path or "").lower()
        if any(p.endswith(x) for x in (
            "/main.py", "/app.py", "/index.ts", "/index.js",
            "/index.tsx", "/main.ts", "/page.tsx",
        )):
            return 0
        if any(x in p for x in (
            "config", "settings", "requirements.txt", "package.json",
            "dockerfile", "docker-compose", "pyproject.toml", "tsconfig",
        )):
            return 1
        if any(x in p for x in ("router", "route", "api/", "schema", "model")):
            return 2
        return 3

    sorted_files = sorted(project.files, key=lambda f: _audit_priority(f.path))
    file_summaries: List[str] = []
    truncated_files: List[str] = []
    for f in sorted_files[:MAX_FILES]:
        content = f.content or ""
        was_truncated = len(content) > MAX_CHARS_PER_FILE
        body = content[:MAX_CHARS_PER_FILE]
        if was_truncated:
            truncated_files.append(f.path)
            body += f"\n... [TRUNCATED — original file is {len(content)} chars]"
        file_summaries.append(
            f"### `{f.path}` ({f.language or '?'})\n```\n{body}\n```"
        )
    file_text = "\n\n".join(file_summaries)
    files_overflow = max(0, len(project.files) - MAX_FILES)
    overflow_note = (
        f"\n\n_توجه: {files_overflow} فایل به‌خاطر cap نمایش داده نشد._"
        if files_overflow else ""
    )

    # 🆕 (audit quality fix) — include previous audit context so the
    # model can verify what was supposed to be fixed and detect actual
    # regression vs hallucinated new issues. Without this, every audit
    # is independent and the model often re-flags fixed issues with
    # slightly different wording, or sees the same issue differently
    # and the verdict oscillates.
    previous_context = ""
    if project.audit_history:
        recent = project.audit_history[-3:]  # last 3 events
        lines = ["", "# 📜 تاریخچهٔ audit/apply قبلی (مهم)", ""]
        for ev in recent:
            kind = ev.get("kind", "audit")
            when = ev.get("run_at", "?")
            score = ev.get("overall_score")
            mc = ev.get("missing_count", 0)
            mod = ev.get("modify_count", 0)
            summary = (ev.get("summary") or "").strip()[:300]
            if kind == "audit":
                lines.append(
                    f"- 🔎 audit در {when}: score={score}, "
                    f"missing={mc}, modify={mod}. خلاصه: «{summary}»"
                )
            else:
                applied = ev.get("applied_paths") or []
                lines.append(
                    f"- 🔧 apply در {when}: {len(applied)} فایل اصلاح شد. "
                    f"مسیرها: {', '.join(applied[:10])}"
                    + ("..." if len(applied) > 10 else "")
                )
        lines.append("")
        lines.append(
            "👉 **مهم:** اگر apply اجرا شد، باید بررسی کنی که آیا issue های "
            "قبلی واقعاً برطرف شده‌اند. اگر همان issue را دوباره flag می‌کنی، "
            "حتماً در `summary` صریحاً بگو که این **regression** است (نه issue "
            "جدید). اگر برطرف شده، نباید دوباره در `files_to_modify` بیاد."
        )
        lines.append("")
        previous_context = "\n".join(lines)

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
{previous_context}

# فایل‌های تولیدشده ({len(project.files)} فایل){overflow_note}
{file_text}

# وظیفهٔ تو

تو در یک **حلقه‌ی iterative** کار می‌کنی. کاربر هر بار audit می‌زند، apply می‌کند، دوباره audit. اگر تو هر بار چیز جدیدی پیدا کنی، کاربر در حلقه‌ی بی‌پایان می‌افتد. **هدف اصلی این است که این حلقه را قطع کنی** — فقط مشکلات **واقعاً blocking** را گزارش کن.

## ✅ چه چیزی **باید** flag بشود (و فقط همین‌ها):
1. فایل **مفقود حیاتی** که بدون آن پروژه run نمی‌شود یا قابلیت اصلی هدف کار نمی‌کند
2. فایل با **syntax error / import error** که run را می‌شکند
3. فایل که **placeholder خام** است (مثل `# TODO` یا `pass` به‌تنهایی)
4. **dependency حیاتی** که در requirements/package.json نیست ولی import شده
5. **contract mismatch** آشکار بین فایل‌ها (مثل endpoint frontend → backend که وجود ندارد)

## ❌ چه چیزی **نباید** flag بشود (مهم! این‌ها باعث حلقهٔ بی‌پایان می‌شوند):
- "می‌تواند کامل‌تر/بهتر/جامع‌تر باشد" — این subjective است
- "محتوای فایل کوتاه است" — اگر کار می‌کند، کافی است
- "کلاس X می‌تواند فیلدهای بیشتری داشته باشد" — اگر کاربر چیز خاصی نخواسته، فعلی کافی است
- "ممکن است در production مشکل ایجاد کند" — مگر اینکه قطعی باشد
- "بهتر است error handling قوی‌تری اضافه شود" — نه مگر اینکه فاجعه‌بار باشد
- موارد stylistic، naming، code formatting

## 🎯 درجهٔ سختگیری امتیاز
- **80-100**: کار می‌کند و هدف کاربر را برآورده می‌کند. مشکل blocking ندارد → **ready_to_push = true**
- **60-79**: کار می‌کند ولی یک یا دو فایل واقعاً ناقص است
- **40-59**: مشکل واقعی دارد (run نمی‌شود یا قابلیت اصلی غایب)
- **0-39**: پروژه خراب است

**اگر بین دو امتیاز شک داری، امتیاز بالاتر را بده.** سختگیری بی‌مورد = حلقهٔ بی‌پایان.

## ⚠️ نکات مهم
- اگر یک فایل با `[TRUNCATED]` نشان داده شد، **هرگز** آن را به‌عنوان «ناقص» flag نکن. فقط محتوای ظاهر شده را بخوان.
- اگر تاریخچه نشان می‌دهد فایلی **همین الان** apply شده، آن را در `files_to_modify` نیار مگر اینکه واقعاً broken باشد.
- اگر تاریخچه نشان می‌دهد که قبلاً همان issue را flag کرده‌ای و apply شده، **مجدداً flag نکن** — مدل ممکن است متفاوت اجرا کرده باشد، ولی اگر کار می‌کند، رهایش کن.
- اگر امتیاز قبلی بالای ۷۵ بود، **نباید** الان زیر ۷۵ بدهی مگر اینکه فاجعهٔ آشکاری رخ داده.

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
            # 🐛 (streaming-timeout fix) — audit JSON is long-form: one
            # file_to_modify entry can easily be 200+ tokens, and complex
            # projects need 10-30 such entries plus missing_files +
            # structural_issues. 4000-token cap truncated the JSON
            # mid-object → "couldn't parse" 500 after 60s of streaming.
            # 8000 leaves headroom for verbose audits without blowing
            # past the model's context window.
            response_text = await ai_generate(
                audit_prompt, model_ids=[mid], max_tokens=8000,
            )
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
        # 🐛 (visibility fix) — when JSON parse fails, the user previously
        # saw a blank "couldn't parse" toast with no clue why. Now we
        # surface each model's raw response excerpt + ok/error flag so
        # they can see whether the model was truncated, returned prose,
        # or errored out entirely. Frontend renders these in the modal.
        excerpts = []
        for r in results_per_model:
            if r.get("ok"):
                excerpt = (r.get("raw_response_excerpt") or "")[:400]
                excerpts.append(
                    f"• {r.get('model_id', '?')}: {excerpt or '(empty)'}"
                )
            else:
                excerpts.append(
                    f"• {r.get('model_id', '?')} ❌ "
                    f"{str(r.get('error') or 'unknown')[:300]}"
                )
        detail_msg = (
            "هیچ مدلی نتوانست audit را به JSON قابل تجزیه برساند. "
            "ممکن است پاسخ truncate شده باشد (پرامپت کوتاه‌تر کنید یا "
            "تعداد فایل کمتر) یا مدل به‌جای JSON متن آزاد برگردانده.\n\n"
            "پاسخ هر مدل:\n" + "\n".join(excerpts)
        )
        raise HTTPException(status_code=500, detail=detail_msg)

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

    missing_collected = _collect("missing_critical_files")
    modify_collected = _collect_objects("files_to_modify")
    delete_collected = _collect_objects("files_to_delete")

    # 🆕 (regression detection) — compare with the most recent audit in
    # history. If score went DOWN materially or new issues appeared on
    # files that were just applied, flag prominently in the UI.
    previous_audit = None
    for ev in reversed(project.audit_history or []):
        if ev.get("kind") == "audit":
            previous_audit = ev
            break
    regression_warning = None
    if previous_audit:
        prev_score = previous_audit.get("overall_score") or 0
        delta = avg_score - prev_score
        if delta <= -5:
            regression_warning = (
                f"⚠️ امتیاز نسبت به audit قبلی {abs(delta)} امتیاز پایین آمد "
                f"({prev_score} → {avg_score}). یا apply اشتباه عمل کرده، یا "
                f"مدل audit دارد دچار اختلاف رأی می‌شود. خلاصهٔ مدل‌ها را "
                f"بخوان و در صورت تردید با مدل‌های متفاوت دوباره audit کن."
            )

    # 🆕 (oscillation / convergence detection) — user reported screen
    # of audit→apply→audit→apply cycle where scores oscillated 58→62→58
    # and modify_count grew 15→16→19. The audit kept finding "new"
    # issues because no concrete bar for "done" existed.
    #
    # Detect this: look at the last 3 audit events. If their scores are
    # within ±5 of each other and modify_count is similar, the user is
    # stuck. Emit a convergence_notice telling them the project is
    # probably good enough and further auditing won't help.
    convergence_notice = None
    recent_audits = [
        ev for ev in (project.audit_history or [])
        if ev.get("kind") == "audit"
    ][-3:]
    if len(recent_audits) >= 2:
        # include the current audit's score in the comparison
        recent_scores = [
            ev.get("overall_score") or 0 for ev in recent_audits
        ] + [avg_score]
        recent_mod_counts = [
            ev.get("modify_count") or 0 for ev in recent_audits
        ] + [len(modify_collected)]
        score_range = max(recent_scores) - min(recent_scores)
        # 🐛 (convergence threshold fix) — initial logic also required
        # modify_count to be within ±5, but user's actual screen showed
        # 15→13→16→19 (range 6) while score oscillated 58→62→62→58 (range
        # 4). That's the *textbook* oscillation pattern — score stuck,
        # AI inventing new "issues" each round — but the mod_range gate
        # blocked the notice from firing. Drop the mod_range cap; the
        # score-range gate (≤5 across 3-4 audits) is already a strong
        # enough signal of "not improving". Bumped score floor to 55
        # so we don't tell a project with 50 it's "good enough".
        applies_between = sum(
            1 for ev in (project.audit_history or [])
            if ev.get("kind") == "apply"
            and ev.get("run_at", "") >= (recent_audits[0].get("run_at") or "")
        )
        if (
            score_range <= 5
            and applies_between >= 1
            and avg_score >= 55
        ):
            convergence_notice = (
                f"🎯 **پروژه به همگرایی رسیده.** {len(recent_scores)} "
                f"audit آخر امتیازی بین {min(recent_scores)} تا "
                f"{max(recent_scores)} داده و با وجود {applies_between} "
                f"apply مداخله‌ای، تعداد اصلاحات (در محدودهٔ "
                f"{min(recent_mod_counts)} تا {max(recent_mod_counts)}) "
                f"کاهش معناداری ندارد. این یعنی AI هر بار چیز جدیدی "
                f"پیدا می‌کند ولی پروژه واقعاً بهبود نمی‌کند — احتمالاً "
                f"به کیفیت قابل قبول رسیده و audit بیشتر فقط نظر شخصی "
                f"مدل را اضافه می‌کند. می‌توانی push کنی، یا چند issue "
                f"واقعاً مهم را دستی انتخاب کنی و بقیه را نادیده بگیری."
            )

    # Pull a representative summary from the highest-scoring model so the
    # history entry stays informative without storing per-model raw text.
    rep = max(
        successful,
        key=lambda r: _coerce_score(r["report"].get("overall_score")),
    )
    rep_summary = str(rep["report"].get("summary") or "").strip()[:600]

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
        "missing_critical_files": missing_collected,
        "files_to_modify": modify_collected,
        "files_to_delete": delete_collected,
        "structural_issues": _collect("structural_issues"),
        "quality_concerns": _collect("quality_concerns"),
        "goal_mismatch_reasons": _collect("goal_mismatch_reasons"),
        "suggestions_before_push": _collect("suggestions_before_push"),
        # 🆕 regression + convergence context for the UI
        "convergence_notice": convergence_notice,
        "previous_score": previous_audit.get("overall_score") if previous_audit else None,
        "score_delta": (
            avg_score - (previous_audit.get("overall_score") or 0)
            if previous_audit else None
        ),
        "regression_warning": regression_warning,
        "summary": rep_summary,
    }

    # 🆕 (audit history) — persist a compact event so the next audit
    # can compare. Cap at 20 entries to keep meta file small.
    from datetime import datetime as _dt_audit
    project.audit_history.append({
        "run_at": _dt_audit.now().isoformat(timespec="seconds"),
        "kind": "audit",
        "overall_score": avg_score,
        "missing_count": len(missing_collected),
        "modify_count": len(modify_collected),
        "delete_count": len(delete_collected),
        "models_used": list(audit_ids),
        "summary": rep_summary,
    })
    project.audit_history = project.audit_history[-20:]
    try:
        await creator._save_project_meta(project)
    except Exception:
        # Don't fail the audit just because we couldn't persist history.
        pass

    return {
        "success": True,
        "project_id": project_id,
        "aggregated": aggregated,
        "per_model": results_per_model,
        "audit_history": project.audit_history,
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

    # 🆕 (audit history) — record the apply event so the next audit can
    # verify what was supposed to be fixed and detect false regression.
    from datetime import datetime as _dt_apply
    applied_paths = (
        [f["path"] for f in files_added]
        + [f["path"] for f in files_modified]
        + [f["path"] if isinstance(f, dict) else f for f in files_deleted]
    )
    project.audit_history.append({
        "run_at": _dt_apply.now().isoformat(timespec="seconds"),
        "kind": "apply",
        "applied_paths": applied_paths,
        "added_count": len(files_added),
        "modified_count": len(files_modified),
        "deleted_count": len(files_deleted),
        "skipped_count": len(files_skipped),
        "models_used": list(req.model_ids or []),
    })
    project.audit_history = project.audit_history[-20:]

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
        "audit_history": project.audit_history,
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


# 🆕 (env auto-fill) — patterns برای resolve خودکار env vars.
# هدف: کاربر نیاز به وارد کردن دستی کلیدهایی که سیستم در Settings دارد،
# نباشد. سه لایه:
#   1) Settings DB lookup — برای کلیدهای API شناخته‌شده
#   2) Auto-generate — برای SECRET_KEY / JWT_SECRET / تصادفی
#   3) Cross-service reference — برای NEXT_PUBLIC_API_URL (backend → frontend)
# هر چیز دیگر (DATABASE_URL, NEO4J_*, REDIS_URL) به‌عنوان "external"
# علامت زده می‌شود تا کاربر در پنل Render خودش دست بگیرد.

# Map: env var name pattern → Settings DB key
_ENV_VAR_DB_LOOKUPS = {
    "OPENAI_API_KEY": "api_key_openai",
    "OPENAI_KEY": "api_key_openai",
    "OPEN_AI_KEY": "api_key_openai",
    "ANTHROPIC_API_KEY": "api_key_claude",
    "CLAUDE_API_KEY": "api_key_claude",
    "GOOGLE_API_KEY": "api_key_gemini",
    "GEMINI_API_KEY": "api_key_gemini",
    "GOOGLE_GENAI_API_KEY": "api_key_gemini",
    "DEEPSEEK_API_KEY": "api_key_deepseek",
    "PERPLEXITY_API_KEY": "api_key_perplexity",
    "GITHUB_TOKEN": "api_key_github",
    "GH_TOKEN": "api_key_github",
    "RENDER_API_KEY": "api_key_render",
}

# Pattern های auto-generate شدنی: نام شامل این کلمات باشد → token_urlsafe
_ENV_VAR_AUTOGEN_PATTERNS = (
    "SECRET_KEY", "JWT_SECRET", "SESSION_SECRET", "APP_SECRET",
    "ENCRYPTION_KEY", "SIGNING_KEY", "CSRF_SECRET",
)

# Pattern های مرتبط با cross-service backend URL
_ENV_VAR_BACKEND_URL_PATTERNS = (
    "NEXT_PUBLIC_API_URL", "VITE_API_URL", "REACT_APP_API_URL",
    "API_BASE_URL", "BACKEND_URL", "API_URL",
)

# Pattern های external که نمی‌توان خودکار resolve کرد (نیاز به سرویس
# مدیریت‌شده). در پاسخ با hint مناسب به کاربر گزارش می‌شوند.
_ENV_VAR_EXTERNAL_HINTS = {
    "DATABASE_URL": "یک PostgreSQL در Render dashboard بساز (New + Postgres) و connection string را کپی کن",
    "DB_URL": "یک PostgreSQL در Render dashboard بساز و connection string را کپی کن",
    "POSTGRES_URL": "یک PostgreSQL در Render dashboard بساز",
    "REDIS_URL": "یک Key Value (Redis) در Render dashboard بساز",
    "CELERY_BROKER_URL": "همان REDIS_URL است (یا یک Redis جدا برای broker)",
    "CELERY_RESULT_BACKEND": "همان REDIS_URL است (یا یک Redis جدا برای backend)",
    "NEO4J_URI": "یک حساب Neo4j Aura رایگان بساز (neo4j.com/cloud/aura) و bolt URL را وارد کن",
    "NEO4J_USERNAME": "Neo4j Aura (پیش‌فرض: neo4j)",
    "NEO4J_PASSWORD": "Neo4j Aura — رمز موقع ساخت instance نمایش داده می‌شود",
    "MONGODB_URI": "یک MongoDB Atlas رایگان بساز",
    "MONGO_URL": "یک MongoDB Atlas رایگان بساز",
}


def _is_placeholder_value(value: str) -> bool:
    """🐛 (placeholder fix) — AI گاهی values مثل `{{GENERATED_SECRET_KEY}}`
    یا `<your-key>` یا `change-me` در env_vars می‌گذارد. این‌ها non-empty
    هستند ولی نباید به‌عنوان user-supplied تفسیر شوند. ست user-supplied
    تفسیر شدن یعنی app هنگام run با literal `{{POSTGRES_PASSWORD}}`
    crash می‌کند. این تابع آن‌ها را شناسایی می‌کند تا resolve منطقی
    خودکار جای آن‌ها اجرا شود."""
    import re as _re_ph
    v = (value or "").strip()
    if not v:
        return True
    # patterns رایج placeholder
    if v.startswith("{{") and v.endswith("}}"):
        return True
    if v.startswith("<") and v.endswith(">"):
        return True
    if _re_ph.match(r"^your[-_]", v, _re_ph.IGNORECASE):
        return True
    if _re_ph.match(r"^change[-_]?me$", v, _re_ph.IGNORECASE):
        return True
    if _re_ph.match(r"^placeholder$", v, _re_ph.IGNORECASE):
        return True
    if _re_ph.match(r"^xxx+$", v, _re_ph.IGNORECASE):
        return True
    if v.upper() in ("TODO", "FIXME", "TBD", "REPLACE_ME", "FILL_ME"):
        return True
    return False


def _resolve_env_var(name: str, current_value: str = "") -> Dict[str, Any]:
    """تلاش برای resolve خودکار یک env var.

    Returns:
      {
        "value": str,        # مقدار resolved (یا current_value اگر نشد)
        "source": str,       # "user" | "db_lookup" | "autogen" | "external" | "cross_service"
        "hint": str,         # برای source="external"، راهنمای کاربر
        "resolved": bool,    # آیا automatic resolved شد
      }
    """
    # 🐛 اگر کاربر مقدار «واقعی» داده، احترام بگذار. ولی placeholder های
    # AI (مثل {{GENERATED_SECRET_KEY}}) را به‌عنوان user-supplied نگیر.
    if current_value and current_value.strip() and not _is_placeholder_value(current_value):
        return {
            "value": current_value, "source": "user",
            "hint": "", "resolved": True,
        }

    name_upper = (name or "").upper().strip()

    # Layer 1: Settings DB lookup
    db_key = _ENV_VAR_DB_LOOKUPS.get(name_upper)
    if db_key:
        try:
            from ...models.setting import Setting
            from ...core.database import SessionLocal
            db = SessionLocal()
            try:
                v = Setting.get_value(db, db_key)
                if v:
                    return {
                        "value": str(v), "source": "db_lookup",
                        "hint": "", "resolved": True,
                    }
            finally:
                db.close()
        except Exception:
            pass

    # Layer 2: Auto-generate برای SECRET_KEY و معادل‌ها
    for pat in _ENV_VAR_AUTOGEN_PATTERNS:
        if pat in name_upper:
            import secrets
            return {
                "value": secrets.token_urlsafe(48), "source": "autogen",
                "hint": "", "resolved": True,
            }

    # Layer 3: Cross-service marker (در زمان resolve فعلی هنوز نداریم،
    # caller backend URL را در پاس دوم پر می‌کند).
    for pat in _ENV_VAR_BACKEND_URL_PATTERNS:
        if pat in name_upper:
            return {
                "value": "", "source": "cross_service",
                "hint": "بعد از deploy backend خودکار set می‌شود",
                "resolved": False,
            }

    # Layer 4: External hint
    if name_upper in _ENV_VAR_EXTERNAL_HINTS:
        return {
            "value": "", "source": "external",
            "hint": _ENV_VAR_EXTERNAL_HINTS[name_upper],
            "resolved": False,
        }

    # Unknown — pass through empty
    return {
        "value": "", "source": "unknown",
        "hint": "این env var را در Render dashboard دستی وارد کن",
        "resolved": False,
    }


def _get_render_api_key_value() -> str:
    """🆕 (audit fix) — دریافت Render API key از env یا Settings DB.

    کاربر معمولاً از پنل /settings کلید را وارد می‌کند که در Settings
    table با key=`api_key_render` ذخیره می‌شود. تابع قدیمی `deploy_project`
    و `deploy_project_render_ai` فقط env را چک می‌کردند → 400 می‌دادند
    حتی وقتی کلید واقعاً در DB موجود بود. Inspector این مشکل را نداشت
    چون مستقیماً از DB می‌خواند.
    """
    key = os.environ.get("RENDER_API_KEY", "").strip()
    if key:
        return key
    try:
        from ...models.setting import Setting
        from ...core.database import SessionLocal
        db = SessionLocal()
        try:
            for k in ("api_key_render", "render_api_key", "RENDER_API_KEY"):
                v = Setting.get_value(db, k)
                if v:
                    os.environ["RENDER_API_KEY"] = v
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
            # 🐛 (push-empty-files fix) — `get_project_files` فقط
            # path/size/language می‌داد. اگر content از آن می‌خواندیم،
            # همیشه خالی بود → repo با Dockerfile/package.json/
            # requirements.txt خالی push می‌شد → deploy fail. علت
            # واقعی failed deploy Detective-1.
            # حالا content را explicit از disk می‌خوانیم.
            content = f.get("content") or ""
            if not content:
                try:
                    disk_content = await creator.get_file_content(
                        project_id, file_path,
                    )
                    if disk_content is not None:
                        content = disk_content
                except Exception:
                    pass
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

    # 🆕 (deploy-to-render fix) — اطلاعات repo جدا را روی project ذخیره
    # کن تا دکمهٔ «Deploy به Render» بداند به کدام repo وصل شود (و نه
    # repo داخلی ai-workspace-data که فقط ذخیرهٔ پرامپت‌هاست).
    # حتی اگر بعضی فایل‌ها fail شدند، repo ساخته شده و قابل deploy است
    # — پس اطلاعات را ذخیره می‌کنیم.
    try:
        project.github_owner = owner
        project.github_repo = desired_repo
        project.github_repo_url = repo_html_url
        project.github_default_branch = default_branch
        await creator._save_project_meta(project)
    except Exception as _meta_e:
        logger.warning(f"saving github repo info on project failed: {_meta_e}")

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
