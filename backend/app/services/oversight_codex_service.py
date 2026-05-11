"""
Project Codex Service
=====================
شناسنامهٔ خودکار پروژه (Project Codex):
برای هر فایل/دایرکتوری/فیچر مهم، توضیح می‌دهد:
  - این چیست؟
  - چه می‌کند؟
  - برای چه اهدافی استفاده می‌شود؟
  - چگونه با سایر بخش‌ها مرتبط است؟
  - در صورت حذف چه چیزی می‌شکند؟

Storage: storage/oversight/codex/{watched_id}.json
Delta updates: فقط فایل‌های تغییر کرده دوباره تحلیل می‌شوند.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from .oversight_service import (
    STORAGE_DIR,
    get_oversight_service,
    now_iso,
    _read_json,
    _write_json,
)

logger = logging.getLogger(__name__)

CODEX_DIR = STORAGE_DIR / "codex"
try:
    CODEX_DIR.mkdir(parents=True, exist_ok=True)
except Exception:
    pass


def _codex_path(watched_id: str) -> Path:
    return CODEX_DIR / f"{watched_id}.json"


def read_codex(watched_id: str) -> Dict[str, Any]:
    return _read_json(_codex_path(watched_id), {}) or {}


def write_codex(watched_id: str, data: Dict[str, Any]) -> None:
    _write_json(_codex_path(watched_id), data)


def _guess_kind_from_path(p: str) -> str:
    """تشخیص kind از path/نام فایل — وقتی structure از deep scan موجود نیست.

    کاربرد: fallback برای refresh_codex زمانی که kinds از deep_scan نداریم.
    """
    pl = (p or "").lower()
    name = pl.rsplit("/", 1)[-1]
    # config files
    if name in {
        "package.json", "tsconfig.json", "pyproject.toml", "requirements.txt",
        "next.config.js", "next.config.mjs", "tailwind.config.js",
        "tailwind.config.ts", "vite.config.ts", "vite.config.js",
        "docker-compose.yml", "dockerfile", "render.yaml", ".env.example",
    } or pl.endswith(("/dockerfile", ".env.example")):
        return "config"
    # entry points
    if name in {"main.py", "app.py", "index.ts", "index.tsx", "index.js", "server.py", "manage.py"}:
        return "entry"
    # migration
    if "/migrations/" in pl or "/alembic/" in pl:
        return "migration"
    # by path
    if "/routes/" in pl or "/api/" in pl or pl.endswith(("_router.py", "_routes.py")):
        return "route"
    if "/services/" in pl or pl.endswith("_service.py"):
        return "service"
    if "/models/" in pl or pl.endswith("_model.py") or pl.endswith("/models.py"):
        return "model"
    if "/middleware/" in pl or pl.endswith("_middleware.py"):
        return "middleware"
    if "/components/" in pl or pl.endswith((".tsx", ".jsx")):
        return "component"
    if "/hooks/" in pl or "/use" in name:
        return "hook"
    if "/pages/" in pl or "/app/" in pl and pl.endswith("page.tsx"):
        return "page"
    # by extension fallback
    if pl.endswith((".py", ".ts", ".js", ".tsx", ".jsx", ".go", ".rs", ".java")):
        return "source"
    return "other"


async def refresh_codex(
    watched_id: str,
    *,
    model_id: Optional[str] = None,
    max_files: int = 40,
    only_changed: bool = True,
) -> Dict[str, Any]:
    """به‌روزرسانی Codex یک پروژه — delta-based.

    خروجی همیشه شامل model_used و وضعیت دقیق است تا کاربر بفهمد چه اتفاقی افتاد.
    """
    service = get_oversight_service()
    watched = service._find_watched(watched_id)
    if watched is None:
        raise ValueError("پروژه یافت نشد")

    # تشخیص مدل واقعی که استفاده خواهد شد — برای شفافیت در پاسخ
    actual_model_id = model_id
    available_models_info: List[str] = []
    try:
        from .ai_manager import get_ai_manager
        ai_mgr = get_ai_manager()
        available = ai_mgr.get_available_models() or []
        available_models_info = [m.id for m in available]
        if not available:
            raise RuntimeError(
                "هیچ مدل AI فعالی نیست. ابتدا در /settings یک کلید API "
                "(OpenAI/Anthropic/Gemini/DeepSeek) وارد کنید."
            )
        if model_id and model_id not in {m.id for m in available}:
            # مدل درخواست‌شده در دسترس نیست — fallback به اولین مدل فعال
            logger.warning(
                f"refresh_codex: model {model_id} در دسترس نیست. "
                f"available={[m.id for m in available]}. fallback به {available[0].id}"
            )
            actual_model_id = available[0].id
        elif not model_id:
            actual_model_id = available[0].id
    except RuntimeError:
        raise
    except Exception as _e:
        logger.warning(f"refresh_codex: cannot resolve actual model: {_e}")
        actual_model_id = model_id or "default"

    # خواندن structure از deep scan (اگر موجود)
    structure = _read_json(STORAGE_DIR / "structure" / f"{watched_id}.json", None)
    used_deep_structure = False
    if not structure:
        # fallback: build_project_context
        ctx = await service.build_project_context(watched.repo_full_name)
        files_sample = ctx.get("files_sample") or []
        # 🆕 fallback kinds از روی path/extension — نه همه "other"
        kinds = {p: _guess_kind_from_path(p) for p in files_sample}
        stacks = []
        readme = ctx.get("readme") or ""
    else:
        used_deep_structure = True
        files_sample = structure.get("files") or []
        kinds = structure.get("kinds") or {}
        stacks = structure.get("stacks") or []
        readme = ""
        # اگر structure موجود ولی kinds خالی، fallback بزن
        if not kinds and files_sample:
            kinds = {p: _guess_kind_from_path(p) for p in files_sample}

    if not files_sample:
        raise RuntimeError(
            "هیچ فایلی در پروژه پیدا نشد. ممکن است token GitHub منقضی شده باشد "
            "یا ریپو خصوصی بدون دسترسی است."
        )

    existing = read_codex(watched_id)
    existing_files: Dict[str, Any] = existing.get("files") or {}

    # انتخاب فایل‌های مهم
    important_kinds = {
        "entry", "page", "route", "service", "model",
        "middleware", "component", "hook", "config", "migration",
        # 🆕 source هم به‌عنوان کاندید (وقتی deep scan نکرده‌ایم)
        "source",
    }
    candidate_files = [p for p in files_sample if kinds.get(p) in important_kinds]
    # 🆕 اگر بازم خالی شد (پروژهٔ بسیار غیرعادی)، حداقل ۲۰ فایل اول
    if not candidate_files:
        logger.warning(
            f"refresh_codex: هیچ فایل با kind مهم پیدا نشد ({len(files_sample)} فایل کل) — "
            f"استفاده از ۲۰ فایل اول"
        )
        candidate_files = files_sample[:20]
    candidate_files = candidate_files[:max_files]

    if only_changed:
        # ساده: فایل‌هایی که هنوز در existing نیستند
        candidate_files = [p for p in candidate_files if p not in existing_files] or candidate_files[:10]

    user_goal = watched.user_notes or ""

    # ساخت پرامپت برای AI
    files_listing = "\n".join(f"- {p} ({kinds.get(p, 'other')})" for p in candidate_files)
    prompt = f"""تو نویسندهٔ مستندات نرم‌افزار هستی. وظیفه‌ات نوشتن «شناسنامه» (Codex) برای فایل‌های زیر است.

# 🎯 هدف اصلی پروژه (از زبان کاربر)
{user_goal or '(کاربر یادداشتی ثبت نکرده است)'}

# پروژه
{watched.repo_full_name}
Stack: {', '.join(stacks) or '(نامشخص)'}

# فایل‌هایی که باید مستند شوند
{files_listing}

برای هر فایل، بنویس:
- what_is_it: این چیست؟ (یک جملهٔ ساده)
- what_it_does: چه می‌کند؟
- use_cases: برای چه اهدافی استفاده می‌شود؟ (لیست ۲-۴ مورد)
- relations: با کدام بخش‌های دیگر پروژه ارتباط دارد؟
- breaks_if_removed: در صورت حذف چه چیزی می‌شکند؟

# خروجی فقط JSON (بدون ``` و بدون متن اضافی)
{{
  "files": {{
    "path/to/file.ext": {{
      "what_is_it": "...",
      "what_it_does": "...",
      "use_cases": ["...", "..."],
      "relations": "...",
      "breaks_if_removed": "..."
    }}
  }}
}}"""

    try:
        # 🆕 max_tokens از 3500 به 8000 (برای 40 فایل JSON خروجی)
        response = await service._ai_generate(
            prompt, model_id=actual_model_id, max_tokens=8000, temperature=0.3
        )
    except Exception as e:
        raise RuntimeError(f"خطا در ساخت Codex (مدل {actual_model_id}): {e}")

    if not response or len(response.strip()) < 20:
        raise RuntimeError(
            f"مدل {actual_model_id} پاسخ خالی یا خیلی کوتاه برگرداند. "
            f"ممکن است quota تمام شده یا کلید API نامعتبر باشد."
        )

    parsed = service._extract_json(response) or {}
    new_entries = parsed.get("files") or {}

    if not new_entries:
        # 🆕 خطای واضح — نه silent success "0 فایل"
        raise RuntimeError(
            f"مدل {actual_model_id} نتوانست JSON معتبر تولید کند. "
            f"پاسخ خام {len(response)} کاراکتر. "
            f"لطفاً با مدل دیگری امتحان کنید یا scan کامل پروژه را اجرا کنید."
        )

    # ادغام با موجود
    merged_files = dict(existing_files)
    for path, doc in new_entries.items():
        if isinstance(doc, dict):
            doc["_updated_at"] = now_iso()
            merged_files[path] = doc

    codex = {
        "watched_id": watched_id,
        "repo": watched.repo_full_name,
        "user_goal": user_goal,
        "stacks": stacks,
        "updated_at": now_iso(),
        "files": merged_files,
        "files_count": len(merged_files),
        "model_used": actual_model_id,
        "used_deep_structure": used_deep_structure,
    }

    write_codex(watched_id, codex)

    return {
        "success": True,
        "files_documented": len(merged_files),
        "newly_added": len(new_entries),
        "candidates_analyzed": len(candidate_files),
        "stacks": stacks,
        "model_used": actual_model_id,
        "used_deep_structure": used_deep_structure,
        "available_models": available_models_info,
    }


def get_codex_for_files(watched_id: str, paths: List[str]) -> Dict[str, Any]:
    """گرفتن صفحات Codex فقط برای فایل‌های مشخص (برای استفاده در گزارش‌ها)."""
    codex = read_codex(watched_id)
    files = codex.get("files") or {}
    return {p: files.get(p) for p in paths if p in files}


# =====================================================================
# 🆕 Roadmap & README auto-generation (مهاجرت از Health analysis)
# =====================================================================

def _roadmap_path(watched_id: str) -> Path:
    return CODEX_DIR / f"{watched_id}_roadmap.json"


def _readme_path(watched_id: str) -> Path:
    return CODEX_DIR / f"{watched_id}_readme.json"


def read_roadmap(watched_id: str) -> Dict[str, Any]:
    """خواندن roadmap ذخیره شده. خالی اگر تولید نشده."""
    return _read_json(_roadmap_path(watched_id), {}) or {}


def write_roadmap(watched_id: str, data: Dict[str, Any]) -> None:
    _write_json(_roadmap_path(watched_id), data)


def read_readme_doc(watched_id: str) -> Dict[str, Any]:
    """خواندن README ذخیره شده. خالی اگر تولید نشده."""
    return _read_json(_readme_path(watched_id), {}) or {}


def write_readme_doc(watched_id: str, data: Dict[str, Any]) -> None:
    _write_json(_readme_path(watched_id), data)


async def generate_roadmap_for_watched(
    watched_id: str,
    *,
    model_id: Optional[str] = None,
    tone: str = "professional",
) -> Dict[str, Any]:
    """تولید روadmap از structure + findings + user_notes با AI.

    خروجی:
    {
      "roadmap_markdown": "...",   # markdown با checkbox list ساختاریافته
      "ideal_state": "...",         # توصیف وضعیت مطلوب پروژه
      "phases": [{name, items, eta}],
      "generated_at": iso,
      "model_used": str
    }

    ذخیره در storage/oversight/codex/{watched_id}_roadmap.json
    """
    service = get_oversight_service()
    watched = service._find_watched(watched_id)
    if watched is None:
        raise ValueError("Watched project یافت نشد")

    # context: structure + last scan findings + user_notes
    from .oversight_deep_scan_service import STRUCTURE_DIR, SCAN_RESULTS_DIR
    structure = _read_json(STRUCTURE_DIR / f"{watched_id}.json", {}) or {}
    scan_results = _read_json(SCAN_RESULTS_DIR / f"{watched_id}.json", {}) or {}

    files_count = structure.get("files_count", 0)
    stacks = ", ".join(structure.get("stacks", [])) or "نامشخص"
    findings = (scan_results.get("findings") or [])[:30]
    findings_text = "\n".join(
        f"- [{f.get('priority', '?')}] {f.get('title', '')[:120]}"
        for f in findings
    ) or "(scan هنوز اجرا نشده — روadmap بر اساس structure تنها)"

    user_goal = (watched.user_notes or "").strip()
    existing = read_roadmap(watched_id)
    prior_ideal = existing.get("ideal_state", "")
    prior_md = existing.get("roadmap_markdown", "")

    prompt = f"""تو یک معمار ارشد نرم‌افزاری هستی که یک نقشهٔ راه (roadmap)
مدون برای پروژه می‌سازی.

# پروژه
{watched.repo_full_name}
- تعداد فایل: {files_count}
- Stack: {stacks}
- هدف اصلی کاربر: {user_goal or '(تعریف نشده)'}

# یافته‌های آخرین deep scan ({len(findings)} مورد)
{findings_text}

{"# روadmap قبلی (برای حفظ پیشرفت)" + chr(10) + prior_md[:2000] if prior_md else ""}
{"# Ideal state قبلی" + chr(10) + prior_ideal[:1000] if prior_ideal else ""}

# وظیفهٔ تو
خروجی JSON با ساختار زیر بساز ({tone} tone):

{{
  "ideal_state": "پاراگراف ۳-۵ جمله‌ای: پروژه در حالت ایده‌آل به چه شکل است؟ چه قابلیت‌هایی دارد؟ کاربران چطور از آن استفاده می‌کنند؟",
  "phases": [
    {{
      "name": "فاز اول: پایه‌گذاری",
      "eta": "۱-۲ هفته",
      "items": [
        {{"text": "رفع اسپلش امنیتی X", "completed": false, "priority": "high"}},
        ...
      ]
    }},
    {{
      "name": "فاز دوم: تثبیت",
      "eta": "۳-۴ هفته",
      "items": [...]
    }},
    {{
      "name": "فاز سوم: گسترش",
      "eta": "۲ ماه",
      "items": [...]
    }}
  ],
  "roadmap_markdown": "## فاز اول: پایه‌گذاری (۱-۲ هفته)\\n- [ ] رفع اسپلش امنیتی X\\n- [x] (اگر قبلاً انجام شده)\\n\\n## فاز دوم: تثبیت\\n..."
}}

قوانین:
- اگر روadmap قبلی موجود است، item های completed را با `[x]` نگه دار
- اولویت بالا: critical/security findings از scan
- هر فاز ۳-۸ item داشته باشد
- متن فارسی و حرفه‌ای
- فقط JSON خالص (بدون ``` و توضیح)
"""

    try:
        response = await service._ai_generate(
            prompt, model_id=model_id, max_tokens=3500, temperature=0.3
        )
    except Exception as e:
        raise RuntimeError(f"خطا در تولید روadmap: {e}")

    parsed = service._extract_json(response) or {}
    roadmap_md = parsed.get("roadmap_markdown", "") or ""
    ideal_state = parsed.get("ideal_state", "") or ""
    phases = parsed.get("phases") or []

    if not roadmap_md and not phases:
        # fallback minimal — اگر AI structure نداد
        roadmap_md = f"## نقشهٔ راه\n\nهدف: {user_goal or 'تعریف نشده'}\n\n- [ ] تعریف ideal state\n- [ ] انجام scan کامل\n"
        ideal_state = ideal_state or "هنوز تعریف نشده — لطفاً دستی ویرایش کنید."

    data = {
        "watched_id": watched_id,
        "repo": watched.repo_full_name,
        "roadmap_markdown": roadmap_md,
        "ideal_state": ideal_state,
        "phases": phases,
        "generated_at": now_iso(),
        "model_used": model_id or "default",
        "tone": tone,
    }
    write_roadmap(watched_id, data)
    return data


async def generate_readme_for_watched(
    watched_id: str,
    *,
    model_id: Optional[str] = None,
    sections: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """تولید README از structure + key files با AI."""
    service = get_oversight_service()
    watched = service._find_watched(watched_id)
    if watched is None:
        raise ValueError("Watched project یافت نشد")

    sections = sections or ["overview", "setup", "usage", "structure", "contributing"]

    from .oversight_deep_scan_service import STRUCTURE_DIR
    structure = _read_json(STRUCTURE_DIR / f"{watched_id}.json", {}) or {}

    files_count = structure.get("files_count", 0)
    stacks = ", ".join(structure.get("stacks", [])) or "نامشخص"
    files_sample = (structure.get("files") or [])[:30]
    files_text = "\n".join(f"- {p}" for p in files_sample)

    user_goal = (watched.user_notes or "").strip()
    sections_str = ", ".join(sections)

    prompt = f"""تو یک technical writer حرفه‌ای هستی. یک README با کیفیت بالا
برای پروژهٔ زیر بساز.

# پروژه
{watched.repo_full_name}
- Stack: {stacks}
- تعداد فایل: {files_count}
- هدف اصلی: {user_goal or '(تعریف نشده)'}

# نمونه فایل‌ها
{files_text}

# بخش‌های موردنیاز
{sections_str}

خروجی فقط JSON خالص:
{{
  "readme_markdown": "# عنوان پروژه\\n\\n...کل README در markdown..."
}}

قوانین:
- ساختار استاندارد README (badges، توضیح، installation، usage، ...)
- فارسی + technical terms انگلیسی
- code blocks مناسب
- table اگر منطقی است
- حداقل ۸۰۰ کلمه
"""

    try:
        response = await service._ai_generate(
            prompt, model_id=model_id, max_tokens=3500, temperature=0.4
        )
    except Exception as e:
        raise RuntimeError(f"خطا در تولید README: {e}")

    parsed = service._extract_json(response) or {}
    readme_md = parsed.get("readme_markdown", "") or response[:5000]

    data = {
        "watched_id": watched_id,
        "repo": watched.repo_full_name,
        "readme_markdown": readme_md,
        "sections": sections,
        "generated_at": now_iso(),
        "model_used": model_id or "default",
    }
    write_readme_doc(watched_id, data)
    return data


def toggle_roadmap_item(watched_id: str, item_id: str) -> Optional[Dict[str, Any]]:
    """تاگل completed یک item در روadmap.

    item_id فرمت: "phase_index:item_index" (مثال: "0:2" = آیتم سوم فاز اول)
    یا یک ID مستقل اگر phases آن را داشت.
    """
    data = read_roadmap(watched_id)
    if not data:
        return None
    phases = data.get("phases") or []
    try:
        phase_idx, item_idx = item_id.split(":", 1)
        pi, ii = int(phase_idx), int(item_idx)
        if 0 <= pi < len(phases) and 0 <= ii < len(phases[pi].get("items", [])):
            phases[pi]["items"][ii]["completed"] = not phases[pi]["items"][ii].get("completed", False)
            data["phases"] = phases
            data["updated_at"] = now_iso()
            # روadmap_markdown هم به‌روز شود (regenerate از phases)
            md_lines = []
            for ph in phases:
                md_lines.append(f"## {ph.get('name', 'فاز')}" + (f" ({ph['eta']})" if ph.get("eta") else ""))
                for it in ph.get("items", []):
                    chk = "[x]" if it.get("completed") else "[ ]"
                    md_lines.append(f"- {chk} {it.get('text', '')}")
                md_lines.append("")
            data["roadmap_markdown"] = "\n".join(md_lines)
            write_roadmap(watched_id, data)
            return data
    except (ValueError, IndexError, KeyError):
        pass
    return None
