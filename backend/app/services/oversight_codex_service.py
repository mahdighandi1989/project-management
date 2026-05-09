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


async def refresh_codex(
    watched_id: str,
    *,
    model_id: Optional[str] = None,
    max_files: int = 40,
    only_changed: bool = True,
) -> Dict[str, Any]:
    """به‌روزرسانی Codex یک پروژه — delta-based."""
    service = get_oversight_service()
    watched = service._find_watched(watched_id)
    if watched is None:
        raise ValueError("پروژه یافت نشد")

    # خواندن structure از deep scan (اگر موجود)
    structure = _read_json(STORAGE_DIR / "structure" / f"{watched_id}.json", None)
    if not structure:
        # fallback: build_project_context
        ctx = await service.build_project_context(watched.repo_full_name)
        files_sample = ctx.get("files_sample") or []
        kinds = {p: "other" for p in files_sample}
        stacks = []
        readme = ctx.get("readme") or ""
    else:
        files_sample = structure.get("files") or []
        kinds = structure.get("kinds") or {}
        stacks = structure.get("stacks") or []
        readme = ""

    existing = read_codex(watched_id)
    existing_files: Dict[str, Any] = existing.get("files") or {}

    # انتخاب فایل‌های مهم
    important_kinds = {
        "entry", "page", "route", "service", "model",
        "middleware", "component", "hook", "config", "migration",
    }
    candidate_files = [p for p in files_sample if kinds.get(p) in important_kinds]
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
        response = await service._ai_generate(
            prompt, model_id=model_id, max_tokens=3500, temperature=0.3
        )
    except Exception as e:
        raise RuntimeError(f"خطا در ساخت Codex: {e}")

    parsed = service._extract_json(response) or {}
    new_entries = parsed.get("files") or {}

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
    }

    write_codex(watched_id, codex)

    return {
        "success": True,
        "files_documented": len(merged_files),
        "newly_added": len(new_entries),
        "stacks": stacks,
    }


def get_codex_for_files(watched_id: str, paths: List[str]) -> Dict[str, Any]:
    """گرفتن صفحات Codex فقط برای فایل‌های مشخص (برای استفاده در گزارش‌ها)."""
    codex = read_codex(watched_id)
    files = codex.get("files") or {}
    return {p: files.get(p) for p in paths if p in files}
