"""
🪄 Idea → Strong Prompt برای موتور خالق

این ماژول idea خام کاربر (به زبان طبیعی) را به یک پرامپت ساختاریافتهٔ
حرفه‌ای تبدیل می‌کند که در `simple_creator.create_project()` برای تولید
فایل‌ها استفاده می‌شود.

flow:
1. کاربر idea می‌نویسد (مثل «ربات تلگرام برای لیست خرید»)
2. این تابع را با مدل انتخاب‌شده call می‌کنیم
3. AI خروجی JSON ساختاریافته با ۱۲ فیلد می‌دهد
4. در صورت parse fail، fallback graceful اعمال می‌شود
5. full_prompt_text با build_strong_prompt قالب‌بندی می‌شود
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Awaitable, Callable, Dict, List, Optional

from .oversight_strong_prompt import build_strong_prompt

logger = logging.getLogger(__name__)


def _build_meta_prompt(
    *, idea: str, name: str, project_type: str, technologies: List[str]
) -> str:
    """ساخت meta-prompt که به AI گفته می‌شود تا idea را به strong prompt تبدیل کند."""
    tech_str = ", ".join(technologies) if technologies else "(کاربر تکنولوژی خاصی پیشنهاد نداده — خودت انتخاب کن)"
    return f"""تو یک معمار نرم‌افزار حرفه‌ای هستی. وظیفه‌ات این است که ایدهٔ خام کاربر را به یک پرامپت ساختاریافتهٔ حرفه‌ای برای تولید پروژه تبدیل کنی.

# ایدهٔ خام کاربر:
\"\"\"
{idea.strip()}
\"\"\"

# اطلاعات اولیه:
- نام پروژهٔ پیشنهادی: {name}
- نوع پروژه: {project_type}
- تکنولوژی‌های پیشنهادی کاربر: {tech_str}

# وظیفهٔ تو
ایده را با دقت تحلیل کن و یک پرامپت غنی تولید کن که شامل:
1. عنوان کوتاه پروژه (title)
2. توضیح بازنویسی‌شدهٔ ساختاریافته (structured_description) — مفصل و حرفه‌ای، نه کپی idea خام
3. تکنولوژی‌های پیشنهادی نهایی (tech_stack) — تکمیل اگر کاربر فقط بخشی داده
4. ویژگی‌های کلیدی (key_features) — به‌صورت bullet point
5. داستان‌های کاربر (user_stories) — "به‌عنوان <نقش>، می‌خواهم <اقدام>، تا <هدف>"
6. خلاصهٔ معماری (architecture_summary) — چگونگی ترکیب لایه‌ها
7. ساختار فایل پیشنهادی (file_structure_hint) — لیست مسیر فایل‌ها/پوشه‌ها
8. endpoint‌ها/route‌ها (endpoints_or_routes) — برای API/web (اگر مرتبط)
9. مدل‌های داده (data_models) — schemas اصلی (اگر مرتبط)
10. الزامات غیرکارکردی (non_functional_requirements) — امنیت، performance، test
11. هشدارها (warnings) — موارد مبهم/ناقص در idea که AI خودش حدس زد

# خروجی فقط JSON خام (بدون ```، بدون commentary)
{{
  "title": "string کوتاه (max 80 char)",
  "structured_description": "توضیح کامل (200-500 کاراکتر)",
  "tech_stack": ["dep1", "dep2", "..."],
  "key_features": ["feature 1", "feature 2", "..."],
  "user_stories": ["story 1", "story 2", "..."],
  "architecture_summary": "توضیح معماری (100-300 کاراکتر)",
  "file_structure_hint": ["main.py", "models/user.py", "..."],
  "endpoints_or_routes": [
    {{"method": "POST", "path": "/api/login", "description": "..."}}
  ],
  "data_models": [
    {{"name": "User", "fields": ["id: int", "email: str", "..."]}}
  ],
  "non_functional_requirements": ["JWT auth", "test coverage 80%", "..."],
  "warnings": ["نکته‌ای که در idea مبهم بود..."]
}}

# قواعد مهم
- اگر `endpoints_or_routes` یا `data_models` برای این نوع پروژه نامرتبط است، آرایهٔ خالی `[]` بگذار
- `warnings` همیشه باید موارد مبهم را ذکر کند — اگر چیزی واضح نبود، اضافه کن
- `tech_stack` باید کامل باشد: framework + DB + auth + test + ...
- زبان خروجی: فارسی برای توضیحات، انگلیسی برای نام فایل/کد
- اگر idea مبهم بود، با حدس منطقی پر کن ولی در warnings بنویس
"""


def _safe_get_list(data: Any, key: str, default: Optional[List] = None) -> List:
    """gracefully extract list field."""
    if not isinstance(data, dict):
        return default or []
    v = data.get(key)
    if isinstance(v, list):
        return v
    return default or []


def _safe_get_str(data: Any, key: str, default: str = "") -> str:
    if not isinstance(data, dict):
        return default
    v = data.get(key)
    if isinstance(v, str):
        return v.strip()
    return default


def _extract_json_robust(text: str) -> Optional[Dict[str, Any]]:
    """parse JSON با چند fallback layer.

    1. parse مستقیم
    2. حذف ```json wrappers
    3. extract first balanced { ... } block
    """
    if not text:
        return None
    cleaned = text.strip()
    # remove ``` wrappers
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[-1]
        if "```" in cleaned:
            cleaned = cleaned.rsplit("```", 1)[0]
    cleaned = cleaned.strip()
    # direct parse
    try:
        return json.loads(cleaned)
    except Exception:
        pass
    # find balanced { ... }
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start >= 0 and end > start:
        try:
            return json.loads(cleaned[start : end + 1])
        except Exception:
            pass
    return None


def _fallback_extract_from_text(text: str) -> Dict[str, Any]:
    """اگر JSON parse fail شد، با regex extract کن (graceful)."""
    out: Dict[str, Any] = {
        "title": "",
        "structured_description": "",
        "tech_stack": [],
        "key_features": [],
        "user_stories": [],
        "architecture_summary": "",
        "file_structure_hint": [],
        "endpoints_or_routes": [],
        "data_models": [],
        "non_functional_requirements": [],
        "warnings": ["JSON parse fail شد — به‌جای آن fallback regex extraction استفاده شد"],
    }
    # title: اولین خط یا "title" دار
    m = re.search(r'"title"\s*:\s*"([^"]+)"', text)
    if m:
        out["title"] = m.group(1).strip()
    else:
        first_line = text.strip().split("\n", 1)[0]
        out["title"] = first_line[:80]
    # description
    m = re.search(r'"structured_description"\s*:\s*"([^"]+)"', text)
    if m:
        out["structured_description"] = m.group(1).strip()
    else:
        out["structured_description"] = text[:500].strip()
    # arrays of strings
    for key in ("tech_stack", "key_features", "user_stories", "file_structure_hint", "non_functional_requirements", "warnings"):
        m = re.search(rf'"{key}"\s*:\s*\[([^\]]*)\]', text, re.DOTALL)
        if m:
            items = re.findall(r'"((?:[^"\\]|\\.)*)"', m.group(1))
            out[key] = [s.strip() for s in items if s.strip()]
    return out


async def idea_to_strong_prompt_for_creator(
    *,
    idea: str,
    name: str,
    project_type: str = "auto",
    technologies: Optional[List[str]] = None,
    ai_generate: Callable[..., Awaitable[str]],
    model_ids: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """تبدیل idea خام کاربر به strong prompt آمادهٔ تولید پروژه.

    Args:
        idea: متن idea کاربر (به زبان طبیعی)
        name: نام پروژه
        project_type: نوع (fastapi/nextjs/.../auto)
        technologies: تکنولوژی‌های پیشنهادی کاربر (اختیاری)
        ai_generate: callable async که (prompt, model_ids=None) → str
        model_ids: لیست مدل‌ها به ترتیب اولویت برای fallback

    Returns:
        dict با ۱۳ فیلد (طبق spec)
    """
    if not (idea and idea.strip()):
        raise ValueError("idea خالی است")
    if not (name and name.strip()):
        raise ValueError("name خالی است")

    techs = list(technologies or [])
    meta_prompt = _build_meta_prompt(
        idea=idea, name=name, project_type=project_type, technologies=techs,
    )

    # call AI با fallback (ai_generate خودش chain را handle می‌کند)
    raw_response = ""
    model_used = "unknown"
    last_error: Optional[str] = None
    try:
        # ai_generate signature: (prompt, model_ids=None) -> str
        raw_response = await ai_generate(meta_prompt, model_ids=model_ids)
        if raw_response:
            # تخمین مدل (در ai_generate.simple_projects، model_ids[0] که موفق شد)
            model_used = (model_ids[0] if model_ids else "default") + " (or fallback)"
    except Exception as e:
        last_error = str(e)
        logger.warning(f"idea_to_strong_prompt: ai_generate failed: {e}")

    if not raw_response:
        raise RuntimeError(
            f"AI generate failed برای idea_to_prompt: {last_error or 'no response'}"
        )

    # parse
    parsed = _extract_json_robust(raw_response)
    if not parsed:
        logger.warning("idea_to_strong_prompt: JSON parse fail — fallback regex")
        parsed = _fallback_extract_from_text(raw_response)

    # normalize fields با defaults
    title = _safe_get_str(parsed, "title") or (idea[:80].strip())
    structured_desc = _safe_get_str(parsed, "structured_description") or idea[:500].strip()
    tech_stack = _safe_get_list(parsed, "tech_stack") or techs or []
    key_features = _safe_get_list(parsed, "key_features")
    user_stories = _safe_get_list(parsed, "user_stories")
    arch_summary = _safe_get_str(parsed, "architecture_summary")
    file_structure = _safe_get_list(parsed, "file_structure_hint")
    endpoints = _safe_get_list(parsed, "endpoints_or_routes")
    data_models = _safe_get_list(parsed, "data_models")
    non_func = _safe_get_list(parsed, "non_functional_requirements")
    warnings = _safe_get_list(parsed, "warnings")

    # ساخت full_prompt_text با build_strong_prompt (یکدست با سایر بخش‌ها)
    related_files: List[Dict[str, Any]] = []
    for fp in file_structure[:20]:
        if isinstance(fp, str):
            related_files.append({"path": fp, "reason": "از structure پیشنهادی AI"})
        elif isinstance(fp, dict):
            related_files.append(fp)

    # تبدیل endpoints/data_models به متن قابل خواندن
    extra_context_lines: List[str] = []
    if endpoints:
        extra_context_lines.append("\n## 🔌 endpoints/routes:")
        for ep in endpoints[:30]:
            if isinstance(ep, dict):
                m = ep.get("method", "")
                p = ep.get("path", "")
                d = ep.get("description", "")
                extra_context_lines.append(f"- {m} `{p}` — {d}")
            else:
                extra_context_lines.append(f"- {ep}")
    if data_models:
        extra_context_lines.append("\n## 🗃 data models:")
        for dm in data_models[:30]:
            if isinstance(dm, dict):
                n = dm.get("name", "")
                fields = dm.get("fields", [])
                extra_context_lines.append(f"- **{n}**: {', '.join(fields) if isinstance(fields, list) else fields}")
            else:
                extra_context_lines.append(f"- {dm}")

    description_full = structured_desc
    if extra_context_lines:
        description_full += "\n" + "\n".join(extra_context_lines)

    full_prompt_text = build_strong_prompt(
        title=title,
        user_goal=idea.strip(),
        description=description_full,
        proposed_action=f"ساخت پروژهٔ {project_type} با نام {name}",
        target_files=[],
        target_locations=[],
        related_files=related_files,
        dependency_summary="",
        tech_context=", ".join(tech_stack) if tech_stack else "",
        before_after_examples=[],
        validation_commands=[],
        acceptance_criteria=key_features + non_func,
        risks="",
        type_="feature_request",
        priority="medium",
        estimate="medium",
    )

    return {
        "title": title,
        "structured_description": structured_desc,
        "tech_stack": tech_stack,
        "key_features": key_features,
        "user_stories": user_stories,
        "architecture_summary": arch_summary,
        "file_structure_hint": file_structure,
        "endpoints_or_routes": endpoints,
        "data_models": data_models,
        "non_functional_requirements": non_func,
        "full_prompt_text": full_prompt_text,
        "model_used": model_used,
        "warnings": warnings,
        "raw_idea": idea.strip(),
    }
