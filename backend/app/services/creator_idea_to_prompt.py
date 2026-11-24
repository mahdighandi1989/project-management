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
12. محدودیت‌های صریحِ کاربر (constraints) — هر قیدی که کاربر نوشته (مثلاً «بدون بک‌اند»، «فقط HTML/CSS/JS»، «بدون فریم‌ورک») **عیناً**

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
  "warnings": ["نکته‌ای که در idea مبهم بود..."],
  "constraints": ["قیدِ صریحِ کاربر، عیناً"]
}}

# قواعد مهم
- اگر `endpoints_or_routes` یا `data_models` برای این نوع پروژه نامرتبط است، آرایهٔ خالی `[]` بگذار
- `warnings` همیشه باید موارد مبهم را ذکر کند — اگر چیزی واضح نبود، اضافه کن
- `tech_stack` فقط آنچه لازم است: اگر کاربر قیدی گذاشته (مثلاً «بدون بک‌اند»)، هیچ framework/DB/auth ِ سمتِ سرور اضافه نکن؛
  برای اپِ سادهٔ مرورگری HTML + CSS + JavaScript (ES modules) و تست با `node --test` کافی است
- قیدهای صریحِ کاربر را هرگز نقض نکن و در `constraints` عیناً بیاور
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



# ---------------------------------------------------------------------------
# (PM-INS-0040) خودسنجیِ هم‌موضوعی: پرامپتِ خروجی باید دربارهٔ همان چیزی باشد که کاربر نوشت.
# مالک شرحِ «تبدیلِ تاریخِ شمسی» داد و پرامپتِ «ماشین‌حساب» گرفت — چنین پرامپتی نباید بی‌هشدار ساخته شود.
# روش: کلیدواژه‌های متمایزِ ورودی (بدونِ واژه‌های عمومی) را در متنِ خروجی می‌جوییم؛ پوششِ کم = ناهم‌موضوع.
# ---------------------------------------------------------------------------
TOPIC_MIN_COVERAGE = 0.4
TOPIC_MAX_KEYWORDS = 40

_TOPIC_STOP = set("""
و در به از که این آن را با برای تا هم هر یک یا اما اگر نه بر چه چی شود شد باشد است هست بود کند کنم کنید کنیم
می نمی باید دارد داشته داشت های ها ای تر ترین هستند کرد کرده شده شوند بتواند بتوان توان خود هم‌چنین همچنین نیز
فقط همه هیچ بدون روی زیر پس پیش وقتی چون مثل مثلا مثلاً یعنی دیگر چند خیلی کاملا کاملاً لطفا لطفاً من ما شما او
پروژه برنامه اپ اپلیکیشن سایت وب صفحه فایل کد تست تستها ساده کاربر کاربران ساخت بساز بسازید میخواهم می‌خواهم
قابلیت ویژگی امکان نمایش دکمه حالت استفاده نیاز لازم خروجی ورودی بخش مورد شامل نام جدید اصلی درست
the a an and or of to in on for with without is are be as at by it this that from into via using use
app application project page web website site file files code test tests simple user users build make create
html css js javascript single feature features should must can will has have
""".split())

_TOPIC_SUFFIXES = ("هایی", "های", "ها", "ات", "ی")


def _topic_norm(text: str) -> str:
    t = (text or "").lower()
    t = t.replace("ي", "ی").replace("ك", "ک").replace("ۀ", "ه").replace("ة", "ه")
    t = re.sub(r"[ً-ٰٟـ]", "", t)          # اعراب و کشیده
    return t.replace("‌", " ").replace("‍", " ")      # نیم‌فاصله ⇒ مرزِ واژه


def _topic_tokens(text: str) -> List[str]:
    return re.findall(r"[a-z]+|[ء-غف-يپچژکگی]+", _topic_norm(text))


def _topic_stem(tok: str) -> str:
    for suf in _TOPIC_SUFFIXES:
        if tok.endswith(suf) and len(tok) - len(suf) >= 3:
            return tok[: -len(suf)]
    return tok


def _is_latin(tok: str) -> bool:
    return bool(tok) and "a" <= tok[0] <= "z"


def topic_check(source: str, generated: str) -> Dict[str, Any]:
    """آیا «generated» دربارهٔ همان موضوعِ «source» است؟

    status:
      - ``ok``        پوششِ کلیدواژه‌ها کافی است
      - ``mismatch``  کلیدواژه‌های اصلیِ ورودی در خروجی نیست ⇒ هشدار و نساختن
      - ``unchecked`` نشد سنجید (ورودیِ خیلی کوتاه، یا ورودیِ لاتین و خروجیِ فارسی) — «نسنجیدم» غیر از «سالم است»
    """
    keywords: List[str] = []
    seen = set()
    for tok in _topic_tokens(source):
        if len(tok) < 3 or tok in _TOPIC_STOP:
            continue
        stem = _topic_stem(tok)
        if stem in _TOPIC_STOP or stem in seen:
            continue
        seen.add(stem)
        keywords.append(stem)
        if len(keywords) >= TOPIC_MAX_KEYWORDS:
            break
    out: Dict[str, Any] = {"status": "unchecked", "ok": True, "coverage": None, "keywords_total": len(keywords),
                           "found": [], "missing": [], "threshold": TOPIC_MIN_COVERAGE, "note": ""}
    gen_tokens = _topic_tokens(generated)
    if len(keywords) < 3:
        out["note"] = "ورودی کلیدواژهٔ متمایزِ کافی برای سنجشِ هم‌موضوعی ندارد"
        return out
    if not gen_tokens:
        out.update(status="mismatch", ok=False, coverage=0.0, missing=keywords[:12], note="خروجی خالی است")
        return out
    # زبانِ ورودی و خروجی فرق دارد (مثلاً ایدهٔ انگلیسی، پرامپتِ فارسی) ⇒ تطبیقِ واژه‌به‌واژه معنا ندارد
    kw_latin = sum(1 for k in keywords if _is_latin(k)) / len(keywords)
    gen_latin = sum(1 for g in gen_tokens if _is_latin(g)) / len(gen_tokens)
    if (kw_latin > 0.7 and gen_latin < 0.3) or (kw_latin < 0.3 and gen_latin > 0.7):
        out["note"] = "زبانِ ورودی و خروجی فرق دارد — هم‌موضوعی واژه‌به‌واژه سنجیده نشد"
        return out
    have = set(gen_tokens) | {_topic_stem(g) for g in gen_tokens}
    found = [k for k in keywords if k in have]
    missing = [k for k in keywords if k not in have]
    coverage = round(len(found) / len(keywords), 3)
    ok = coverage >= TOPIC_MIN_COVERAGE
    out.update(status="ok" if ok else "mismatch", ok=ok, coverage=coverage, found=found[:20], missing=missing[:12])
    if not ok:
        out["note"] = (f"فقط {len(found)} از {len(keywords)} کلیدواژهٔ ورودی در پرامپت هست — "
                       "پرامپت احتمالاً دربارهٔ موضوعِ دیگری است")
    return out


async def idea_to_strong_prompt_for_creator(
    *,
    idea: str,
    name: str,
    project_type: str = "auto",
    technologies: Optional[List[str]] = None,
    ai_generate: Callable[..., Awaitable[str]],
    model_ids: Optional[List[str]] = None,
    user_idea: Optional[str] = None,
) -> Dict[str, Any]:
    """تبدیل idea خام کاربر به strong prompt آمادهٔ تولید پروژه.

    Args:
        idea: متن idea کاربر (به زبان طبیعی)
        name: نام پروژه
        project_type: نوع (fastapi/nextjs/.../auto)
        technologies: تکنولوژی‌های پیشنهادی کاربر (اختیاری)
        ai_generate: callable async که (prompt, model_ids=None) → str
        model_ids: لیست مدل‌ها به ترتیب اولویت برای fallback
        user_idea: (PM-INS-0040) متنِ خودِ کاربر در فرم — بدونِ متنِ پیوست‌ها و پروژه‌های مرجع که به `idea`
            افزوده شده؛ خودسنجیِ هم‌موضوعی با همین سنجیده و همین در `source_idea` برگردانده می‌شود

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
    # (PM-INS-0029) the creator engine reads the owner's solved lessons («مرکز دانش») as well
    _kc = {"block": "", "line": "", "entries": []}
    try:
        from .knowledge_center_service import experience_context as _kc_ctx
        _kc = await _kc_ctx(f"{name} {idea}", "creator", "", limit=3, fetch_body=False)
        if _kc.get("block"):
            meta_prompt += "\n\n" + _kc["block"]
    except Exception:  # noqa: BLE001
        pass

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
    # (PM-INS-0025) the user's explicit constraints are LAW — detected from their own words (not guessed) plus what the
    # model copied; a «بدونِ بک‌اند» idea must not come back with FastAPI/DB/endpoints
    from .creator_selfcheck import detect_constraints, clean_technologies
    _cons = detect_constraints(idea)
    constraints = [str(c) for c in _safe_get_list(parsed, "constraints") if c]
    for ph in _cons.get("phrases") or []:
        if not any(ph in c for c in constraints):
            constraints.append(ph)
    if _cons.get("no_backend"):
        tech_stack = clean_technologies(tech_stack, _cons) or ["HTML", "CSS", "JavaScript (ES modules)", "node:test"]
        endpoints, data_models = [], []
        file_structure = [f for f in file_structure if not (isinstance(f, str) and f.endswith((".py", "requirements.txt")))]

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
    if constraints:
        description_full += "\n\n## ⛔ محدودیت‌های صریحِ کاربر (قانون — نقض نکن)\n" + "\n".join(f"- {c}" for c in constraints)
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
        new_project=True,
    )

    # (PM-INS-0040) خودسنجی: بخش‌هایی که **مدل** نوشته (نه رونوشتِ عینِ ایده در «🧭 هدف») باید هم‌موضوعِ ورودی باشند
    _src = (user_idea or "").strip()
    if not _src or _src.startswith("[ایدهٔ متنی همراه نیست"):
        _src = idea.strip()
    _model_written = "\n".join(
        [title, structured_desc, arch_summary]
        + [str(x) for x in key_features] + [str(x) for x in user_stories] + [str(x) for x in non_func]
        + [str(x) for x in file_structure]
    )
    topic = topic_check(_src, _model_written)
    if topic["status"] == "mismatch":
        logger.warning(
            "idea_to_strong_prompt: topic mismatch — coverage=%s missing=%s", topic.get("coverage"), topic.get("missing"))
        warnings = [f"⛔ پرامپت با شرحِ ورودی هم‌موضوع نیست: {topic['note']} (نیافته: {'، '.join(topic['missing'][:8])})"] + list(warnings)

    return {
        "topic_check": topic,
        "source_name": name.strip(),
        "source_idea": (user_idea or idea).strip(),
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
        "constraints": constraints,
        "full_prompt_text": full_prompt_text + (("\n\n" + _kc["block"] + "\n\n" + _kc["line"]) if _kc.get("block") else ""),
        "experiences_used": _kc.get("line") or "",
        "model_used": model_used,
        "warnings": warnings,
        "raw_idea": idea.strip(),
    }
