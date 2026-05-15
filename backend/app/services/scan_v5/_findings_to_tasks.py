"""Phase 5 — Findings → Standard Tasks Converter.

این ماژول crucial integration گم‌شده را پر می‌کند:
Phase 5 findings (stale, anti-pattern, coherence, effectiveness,
notification audit, change-impact) → standard finding dict که در
run_deep_scan به task تبدیل می‌شود.

🆕 (Phase 5 — bug 11) — هر finding اکنون با ساختار غنی تولید می‌شود:
    title + description تفصیلی + proposed_action + acceptance_criteria
    اختصاصی + validation_commands + risks + dependency_summary
    + related_files (در صورت امکان).
این تضمین می‌کند `build_strong_prompt` پرامپت قوی و چک‌لیست تخصصی
بسازد، نه پرامپت ضعیف و چک‌لیست عمومی.

API:
    phase5_findings_to_standard(stale, anti_patterns, ...) -> List[Dict]
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def _priority_for_severity(severity: Optional[str], default: str = "medium") -> str:
    s = (severity or "").strip().lower()
    if s in ("critical", "high", "medium", "low"):
        return s
    if s == "error":
        return "high"
    if s in ("warning", "warn"):
        return "medium"
    if s == "info":
        return "low"
    return default


def _vcmds_for_file(path: str) -> List[str]:
    """validation_commands بر اساس پسوند فایل."""
    p = (path or "").lower()
    cmds: List[str] = []
    if p.endswith(".py"):
        cmds.append("python -m py_compile " + path)
        cmds.append("ruff check " + path)
        cmds.append("pytest -x")
    elif p.endswith((".ts", ".tsx")):
        cmds.append("npm run type-check")
        cmds.append("npm run lint")
        cmds.append("npm run build")
    elif p.endswith((".js", ".jsx")):
        cmds.append("npm run lint")
        cmds.append("npm run build")
    elif p.endswith((".json", ".yml", ".yaml", ".toml")):
        cmds.append("python -c \"import json; json.load(open('" + path + "'))\"" if p.endswith(".json") else "echo 'config syntax check manually'")
    return cmds


# ============================================================
# Stale → finding (per-kind specialized)
# ============================================================

def _stale_to_finding(stale_item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    kind = stale_item.get("kind", "")
    detector = stale_item.get("_detector", "")
    if not kind:
        return None
    file_ = stale_item.get("file") or ""
    label = str(stale_item.get("label", ""))[:80]
    reason = stale_item.get("reason", "") or ""

    if kind == "dead_ui_button":
        title = f"دکمه‌ی UI بدون handler: {label or '?'}"
        description = (
            f"## 📋 شرح\n"
            f"یک دکمه/کنترل UI در فایل `{file_}` پیدا شد که هیچ event handler "
            f"معنادار به آن متصل نیست (onClick، onChange، form submit، router push، "
            f"یا API call شناسایی نشد).\n\n"
            f"## 🔍 جزئیات\n"
            f"- label/متن دکمه: `{label or '?'}`\n"
            f"- فایل: `{file_}`\n"
            f"- علت تشخیص stale_detector: {reason}\n\n"
            f"## 🤔 چرا مهم است\n"
            f"دکمه بدون handler از دید کاربر کار نمی‌کند و دو حالت دارد:\n"
            f"  ۱) **dead UI**: دکمه از قبل کار می‌کرده و در refactor شکست خورده "
            f"(regression) — باید handler بازگردانده شود.\n"
            f"  ۲) **forgotten option**: دکمه placeholder بوده و هرگز پیاده‌سازی "
            f"نشده — باید یا حذف شود یا پیاده‌سازی کامل شود.\n"
            f"  ۳) **decorative**: فقط نمایشی است — باید با `aria-disabled` "
            f"یا `role=\"presentation\"` علامت شود."
        )
        proposed_action = (
            "گام ۱: مشخص کن کدام یک از سه حالت بالاست — git blame روی این خط بزن "
            "تا commit اصلی + intent اولیه را ببینی.\n"
            "گام ۲: اگر regression است، handler از commit قبلی را restore کن.\n"
            "گام ۳: اگر forgotten است، یا feature را کامل پیاده کن یا دکمه را حذف کن.\n"
            "گام ۴: اگر decorative است، attribute مناسب اضافه کن."
        )
        acceptance_criteria = [
            {
                "text": f"git blame مشخص می‌کند چرا این دکمه `{label}` فاقد handler است",
                "acceptance_signal": "git blame خروجی + توضیح در PR description"
            },
            {
                "text": "یکی از این سه حالت تعیین شده: (a) handler restore شده + کار می‌کند، (b) دکمه حذف شده، (c) به‌صورت decorative علامت‌گذاری شده",
                "acceptance_signal": "تست دستی روی UI + screenshot قبل/بعد"
            },
            {
                "text": "اگر دکمه باقی ماند، تست end-to-end (Playwright یا cypress) برای کلیک و تأیید رفتار اضافه شده",
                "acceptance_signal": "test passing + assertion روی نتیجه کلیک"
            },
        ]
        risks = (
            "اگر این دکمه از طریق DOM event delegation در فایل دیگری handle می‌شود، "
            "حذف آن سکوت می‌شکند. قبل از حذف، grep روی `data-action`، `data-testid`، "
            "یا label/text در کل کدبیس انجام شود."
        )
        task_type, priority = "bug_fix", "medium"

    elif kind == "dead_frontend_route":
        route = stale_item.get("route", "?")
        title = f"route فرانت‌اند بلااستفاده: {route}"
        description = (
            f"## 📋 شرح\n"
            f"route `{route}` در فایل `{file_}` تعریف شده ولی هیچ `Link`، "
            f"`router.push`، یا redirect در کدبیس به آن اشاره نمی‌کند.\n\n"
            f"## 🔍 جزئیات\n"
            f"- route path: `{route}`\n"
            f"- فایل: `{file_}`\n"
            f"- علت: {reason}\n\n"
            f"## 🤔 چرا مهم است\n"
            f"route orphan یعنی صفحه‌ای که فقط با تایپ مستقیم URL قابل دسترسی است. "
            f"یا فراموش شده یا منسوخ. باعث می‌شود کاربر هرگز به feature نرسد."
        )
        proposed_action = (
            f"گام ۱: بررسی کن آیا این route از طریق dynamic URL (مثل sidebar config) "
            f"اشاره می‌شود — grep روی `{route}` در کل کدبیس بزن.\n"
            f"گام ۲: اگر orphan واقعی است، یا (الف) lin/redirect در navigation اصلی "
            f"اضافه کن، یا (ب) فایل route را حذف کن.\n"
            f"گام ۳: اگر deprecated است، redirect 301 به route جدید بنویس."
        )
        acceptance_criteria = [
            {"text": f"تأیید شد که `{route}` orphan است (هیچ Link/router.push اشاره نمی‌کند)"},
            {"text": "یا navigation link اضافه شد، یا route حذف/redirect شد"},
            {"text": "تست navigation: کاربر بتواند به این صفحه (یا destination) برسد"},
        ]
        risks = "حذف route ممکن است bookmark خارجی/SEO link خارجی را بشکند. اگر SEO اهمیت دارد، redirect بنویس نه delete."
        task_type, priority = "cleanup", "medium"

    elif kind == "dead_backend_endpoint":
        method = stale_item.get("method", "?")
        path_ = str(stale_item.get("path", "?"))[:60]
        title = f"endpoint بک‌اند بلااستفاده: {method} {path_}"
        description = (
            f"## 📋 شرح\n"
            f"endpoint `{method} {path_}` در `{file_}` تعریف شده ولی هیچ "
            f"`fetch`، `axios`، `apiClient.*`، یا frontend call به آن دیده نمی‌شود.\n\n"
            f"## 🔍 جزئیات\n"
            f"- method: `{method}`\n"
            f"- path: `{path_}`\n"
            f"- فایل: `{file_}`\n"
            f"- علت: {reason}\n\n"
            f"## 🤔 چرا مهم است\n"
            f"endpoint بدون caller یا (الف) به‌صورت اشتباه orphan شده و frontend "
            f"feature روی آن broken است، یا (ب) admin/internal endpoint است که "
            f"از طریق curl/Postman فقط مصرف می‌شود (مستندسازی لازم دارد)، یا "
            f"(ج) قدیمی است و باید حذف شود (با ۴۱۰ Gone یا حذف کامل)."
        )
        proposed_action = (
            f"گام ۱: grep روی `{path_}` در frontend + scripts/ + docs/ — اگر "
            f"caller هست، اتصال را drop شده اصلاح کن.\n"
            f"گام ۲: اگر internal است، در README یا OpenAPI tag `internal` بزن.\n"
            f"گام ۳: اگر منسوخ است، حذف کن (شامل تست‌ها)."
        )
        acceptance_criteria = [
            {"text": f"مشخص شد endpoint `{method} {path_}` در کدام دسته است (orphan/internal/deprecated)"},
            {"text": "اقدام مناسب انجام شد: یا connection باز شد، یا تگ internal، یا حذف"},
            {"text": "اگر حذف شد، تست‌های مربوطه هم حذف شدند و OpenAPI به‌روز شد"},
        ]
        risks = "حذف endpoint که فقط در production مصرف می‌شود (cron/webhook خارجی) باعث silent failure می‌شود. قبل از حذف، Render logs یا nginx access logs آخرین ۳۰ روز را چک کن."
        task_type, priority = "audit", "medium"

    elif kind == "unused_file":
        title = f"فایل بدون import مرجع: {file_.rsplit('/', 1)[-1]}"
        description = (
            f"## 📋 شرح\n"
            f"فایل `{file_}` در هیچ import/require دیده نمی‌شود.\n\n"
            f"## 🤔 چرا مهم است\n"
            f"فایل orphan یا (الف) از قبل dead code است، یا (ب) entry point است "
            f"(مثل migrations، scripts، CLI) که از طریق import import نمی‌شود، یا "
            f"(ج) dynamic import می‌شود (lazy load).\n\n"
            f"## 🔍 جزئیات\n"
            f"- علت: {reason}"
        )
        proposed_action = (
            "گام ۱: grep روی نام فایل (بدون پسوند) و class/function اصلی آن.\n"
            "گام ۲: اگر CLI/script است، در README ذکر کن.\n"
            "گام ۳: اگر dead است، حذف کن (همراه با تست‌های مربوطه)."
        )
        acceptance_criteria = [
            {"text": "مشخص شد فایل dead است یا entry point/dynamic"},
            {"text": "اقدام مناسب: حذف یا مستندسازی"},
            {"text": "تست‌های مربوطه (در صورت حذف) هم حذف شدند"},
        ]
        risks = "فایل ممکن است در deployment pipeline یا CI به‌صورت direct invocation مصرف شود (مثل `python migrations/run.py`). قبل از حذف، در CI configs و scripts/ هم چک کن."
        task_type, priority = "cleanup", "low"

    elif kind == "unused_dataclass_field":
        cls = stale_item.get("class", "?")
        field = stale_item.get("field", "?")
        title = f"فیلد بلااستفاده: {cls}.{field}"
        description = (
            f"## 📋 شرح\n"
            f"فیلد `{field}` در dataclass/model `{cls}` (فایل `{file_}`) "
            f"تعریف شده ولی هرگز خوانده نمی‌شود.\n\n"
            f"## 🤔 چرا مهم است\n"
            f"یا (الف) ذخیره می‌شود برای آینده ولی هیچ‌کس مصرف نمی‌کند (waste)، "
            f"یا (ب) reader gone است (regression — قبلاً مصرف می‌شد).\n\n"
            f"## 🔍 جزئیات\n"
            f"- علت: {reason}"
        )
        proposed_action = (
            f"گام ۱: grep روی `\\.{field}` + `['{field}']` در کل کدبیس.\n"
            f"گام ۲: اگر هیچ reader نیست، یا حذف کن یا کاربردش را پیاده کن.\n"
            f"گام ۳: اگر در DB persist می‌شود، migration برای drop column بنویس."
        )
        acceptance_criteria = [
            {"text": f"تأیید شد `{field}` در هیچ reader مصرف نمی‌شود"},
            {"text": "یا حذف شد (با migration در صورت persist)، یا reader اضافه شد"},
            {"text": "تست‌های schema و serialization عبور می‌کنند"},
        ]
        risks = "اگر فیلد در API response serialize می‌شود، حذف آن breaking change برای client است. قبل از حذف، API consumers را چک کن."
        task_type, priority = "cleanup", "low"

    elif kind == "unused_env_var":
        name = stale_item.get("name", "?")
        title = f"env var بلااستفاده: {name}"
        description = (
            f"## 📋 شرح\n"
            f"env var `{name}` در `.env`/config تعریف شده ولی در هیچ "
            f"`os.getenv` یا `process.env` خوانده نمی‌شود.\n\n"
            f"## 🤔 چرا مهم است\n"
            f"یا (الف) reader حذف شده و باعث config drift می‌شود، یا (ب) leak "
            f"اطلاعات حساس به repository است (مخصوصاً اگر secret است).\n\n"
            f"## 🔍 جزئیات\n"
            f"- علت: {reason}"
        )
        proposed_action = (
            f"گام ۱: grep روی `{name}` در همه کدبیس + CI configs + Dockerfile.\n"
            f"گام ۲: اگر unused است، از `.env.example` و docs حذف کن.\n"
            f"گام ۳: اگر secret leak شده، آن را rotate کن."
        )
        acceptance_criteria = [
            {"text": f"`{name}` در هیچ کدی خوانده نمی‌شود (تأیید شده)"},
            {"text": "از `.env.example` و deployment configs حذف شد"},
            {"text": "اگر secret بوده، rotate شد و در deployment new value تنظیم شد"},
        ]
        risks = "اگر env var در CI/CD pipeline یا Dockerfile/Render config مصرف می‌شود، grep فقط روی کد ممکن است miss کند. حتماً همه‌جا چک کن."
        task_type, priority = "cleanup", "medium"

    elif kind == "stale_dependency":
        name = stale_item.get("name", "?")
        lang = stale_item.get("lang", "?")
        title = f"dependency بلااستفاده: {name} ({lang})"
        description = (
            f"## 📋 شرح\n"
            f"package `{name}` در `{file_}` declare شده ولی در هیچ import "
            f"کدبیس مصرف نمی‌شود.\n\n"
            f"## 🤔 چرا مهم است\n"
            f"dependency بلااستفاده باعث: (۱) bundle size بزرگ، (۲) attack surface "
            f"بیشتر برای vulnerabilities، (۳) supply chain risk.\n\n"
            f"## 🔍 جزئیات\n"
            f"- نام package: `{name}`\n- زبان: `{lang}`\n- علت: {reason}"
        )
        proposed_action = (
            f"گام ۱: `npm/pip list --depth=0` و grep import روی `{name}`.\n"
            f"گام ۲: اگر transitive dep ای دیگری به این نیاز دارد، نگه دار.\n"
            f"گام ۳: در غیر این صورت، uninstall + از `package.json`/`requirements.txt` حذف کن.\n"
            f"گام ۴: lockfile (`package-lock.json`/`poetry.lock`) refresh کن."
        )
        acceptance_criteria = [
            {"text": f"`{name}` در هیچ direct import مصرف نمی‌شود + هیچ transitive dep ای آن را require نمی‌کند"},
            {"text": "package از manifest حذف شد + lockfile به‌روز"},
            {"text": "build/test/CI همچنان عبور می‌کند"},
        ]
        risks = "حذف dependency که peer dependency دیگری است، خاموش break می‌کند. حتماً build کامل + test کامل بعد از حذف اجرا کن."
        task_type, priority = "cleanup", "medium"

    elif kind == "hidden_purpose":
        title = f"فایل با هدف مبهم: {file_.rsplit('/', 1)[-1]}"
        description = (
            f"## 📋 شرح\n"
            f"فایل `{file_}` هیچ docstring/comment توضیحی در بالای فایل ندارد "
            f"و نام آن purpose را روشن نمی‌کند.\n\n"
            f"## 🤔 چرا مهم است\n"
            f"کد بدون purpose maintenance hell ایجاد می‌کند — هر developer جدید "
            f"باید reverse-engineer کند.\n\n"
            f"## 🔍 جزئیات\n- علت: {reason}"
        )
        proposed_action = (
            "گام ۱: بخوان فایل و معنی واقعی‌اش را بفهم.\n"
            "گام ۲: docstring/comment ۳-۵ خطی در بالای فایل اضافه کن: "
            "purpose، inputs، outputs، side effects.\n"
            "گام ۳: اگر فایل dead است، حذف کن."
        )
        acceptance_criteria = [
            {"text": "فایل docstring/header comment ۳-۵ خطی دارد که purpose را روشن می‌کند"},
            {"text": "اگر فایل بخشی از pipeline است، در docstring به upstream/downstream اشاره شده"},
            {"text": "نام فایل (اگر مبهم) به نام معنادار rename شده"},
        ]
        risks = "rename فایل ممکن است imports زیادی را break کند — قبل از rename همه usages را پیدا و یکجا update کن."
        task_type, priority = "audit", "medium"

    elif kind == "forgotten_option":
        field_hint = stale_item.get("field_hint", "?")
        title = f"UI option با نام مبهم: {field_hint}"
        description = (
            f"## 📋 شرح\n"
            f"یک option/checkbox/toggle با نام `{field_hint}` در `{file_}` "
            f"دیده شد که نام آن کاربردش را روشن نمی‌کند.\n\n"
            f"## 🤔 چرا مهم است\n"
            f"option های فراموش‌شده باعث می‌شوند کاربر یا (الف) نفهمد چی کار می‌کند "
            f"و آن را خاموش بگذارد، یا (ب) به‌اشتباه روشن کند و رفتار غیرمنتظره ببیند.\n\n"
            f"## 🔍 جزئیات\n- علت: {reason}"
        )
        proposed_action = (
            f"گام ۱: کد را بخوان و کاربرد واقعی `{field_hint}` را بفهم.\n"
            f"گام ۲: label/title واضح در UI بگذار + tooltip توضیحی.\n"
            f"گام ۳: در README یا docs مستندسازی کن (یک خط)."
        )
        acceptance_criteria = [
            {"text": f"option `{field_hint}` label واضح فارسی/انگلیسی دارد"},
            {"text": "tooltip یا help text توضیح می‌دهد چه کاری می‌کند"},
            {"text": "default value منطقی + در README مستند شده"},
        ]
        risks = "تغییر default value می‌تواند رفتار کاربران فعلی را تغییر دهد. اگر default می‌خواهی عوض کنی، یک release note بنویس."
        task_type, priority = "audit", "low"
    else:
        title = f"stale item: {kind}"
        description = f"{reason}\n\n🎯 پیشنهاد: یا حذف، یا مستندسازی، یا تکمیل."
        proposed_action = ""
        acceptance_criteria = [{"text": "وضعیت این مورد مشخص و اقدام مناسب انجام شده"}]
        risks = ""
        task_type, priority = "audit", "low"

    target_files = [file_] if file_ else []

    return {
        "type": task_type,
        "priority": priority,
        "title": title,
        "description": description,
        "proposed_action": proposed_action,
        "acceptance_criteria": acceptance_criteria,
        "validation_commands": _vcmds_for_file(file_),
        "risks": risks,
        "dependency_summary": (
            "این مورد در پایپ‌لاین کدبیس به فایل‌های اطراف وابسته است؛ "
            "قبل از تغییر، grep روی نام symbol/path اصلی انجام شود."
        ),
        "related_files": [],
        "target_files": target_files,
        "target_locations": [{"path": p, "lines": ""} for p in target_files],
        "_pass": "phase5_stale",
        "_source": f"scan_v5/stale_detector:{detector}",
        "_stale_kind": kind,
    }


# ============================================================
# Anti-pattern → finding
# ============================================================

def _anti_pattern_to_finding(item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    kind = item.get("kind", "anti_pattern")
    file_ = item.get("file") or ""
    if not kind:
        return None
    line = item.get("line") or item.get("line_hint")
    base_reason = item.get("reason") or item.get("description", "")

    if kind == "magic_threshold":
        snippet = (item.get("snippet") or "").strip()[:120]
        title = "Magic threshold — مقدار عددی بدون توضیح"
        description = (
            f"## 📋 شرح\n"
            f"در `{file_}`{f' (line {line})' if line else ''} یک مقدار عددی "
            f"hard-coded پیدا شد که بدون توضیح/ثابت‌سازی استفاده می‌شود.\n\n"
            f"## 🔍 جزئیات\n"
            f"- snippet: `{snippet}`\n- علت: {base_reason}\n\n"
            f"## 🤔 چرا مهم است\n"
            f"magic number ها: (۱) intent را پنهان می‌کنند، (۲) تغییرشان "
            f"در آینده باعث inconsistency می‌شود (یک‌جا تغییر، جای دیگر نه)، "
            f"(۳) test کردن edge case ها را سخت می‌کند."
        )
        proposed_action = (
            "گام ۱: ثابت تعریف کن (UPPER_SNAKE) با نام معنادار.\n"
            "گام ۲: کامنت ۱-خطی بنویس چرا این مقدار انتخاب شده.\n"
            "گام ۳: اگر مقدار قابل تنظیم باید باشد، به config/env var منتقل کن."
        )
        acceptance_criteria = [
            {"text": "مقدار به constant با نام معنادار منتقل شد"},
            {"text": "comment توضیحی برای انتخاب این مقدار اضافه شد"},
            {"text": "اگر در چند جا تکرار می‌شد، همه به یک منبع وصل شدند"},
        ]
        risks = "اگر این عدد در test fixtures یا config های دیگر هم تکرار شده، باید همه با هم sync شوند."
        task_type, priority = "refactor", "medium"

    elif kind == "silent_failure":
        title = "Silent failure — except/catch بدون log در مسیر crucial"
        description = (
            f"## 📋 شرح\n"
            f"در `{file_}`{f' (line {line})' if line else ''} یک exception "
            f"handler خاموش (مثل `except: pass`) در مسیر اصلی کد پیدا شد.\n\n"
            f"## 🔍 جزئیات\n- علت: {base_reason}\n\n"
            f"## 🤔 چرا مهم است\n"
            f"silent failure خطرناک‌ترین bug است — کد به‌نظر کار می‌کند ولی "
            f"در شرایط لبه data drop می‌شود بدون اینکه کسی متوجه شود. "
            f"production incidents معمولاً ریشه‌شان همین است."
        )
        proposed_action = (
            "گام ۱: مشخص کن چه exception ای واقعاً ممکن است در این نقطه رخ دهد.\n"
            "گام ۲: یا (الف) آن exception را به‌صورت specific catch کن و "
            "log + decision بنویس، یا (ب) اجازه bdo bubble up.\n"
            "گام ۳: تست unit برای edge case (شکست عمدی این مسیر) بنویس."
        )
        acceptance_criteria = [
            {"text": "نوع exception specific شده (نه bare except/catch)"},
            {"text": "log با level مناسب (warning/error) + context کامل اضافه شد"},
            {"text": "تست unit برای edge case شکست‌خورده عبور می‌کند"},
            {"text": "اگر failure قابل recovery است، fallback مستند شده"},
        ]
        risks = "تغییر silent failure به raise ممکن است upstream caller را break کند که فرض می‌کرده این تابع همیشه return می‌کند. caller را هم چک کن."
        task_type, priority = "bug_fix", _priority_for_severity(item.get("priority") or item.get("severity"), "high")

    elif kind == "unused_data_write":
        attr = item.get("attribute", "?")
        title = f"داده‌ی بی‌مصرف: {attr}"
        description = (
            f"## 📋 شرح\n"
            f"attribute `{attr}` در `{file_}` نوشته می‌شود ولی هیچ reader "
            f"در کدبیس آن را مصرف نمی‌کند.\n\n"
            f"## 🤔 چرا مهم است\n"
            f"write بدون read یعنی یا (الف) reader حذف شده (regression)، "
            f"یا (ب) از قبل برای feature آینده گذاشته شده و فراموش شده.\n\n"
            f"## 🔍 جزئیات\n- علت: {base_reason}"
        )
        proposed_action = (
            f"گام ۱: grep روی `{attr}` در کل کدبیس + DB schema.\n"
            f"گام ۲: یا reader اضافه کن، یا write را حذف کن."
        )
        acceptance_criteria = [
            {"text": "یا reader اضافه شد، یا write حذف شد"},
            {"text": "اگر در DB persist می‌شد، migration drop column نوشته شد"},
        ]
        risks = "اگر این attribute در logs/monitoring مصرف می‌شود، grep ممکن است miss کند."
        task_type, priority = "cleanup", "low"

    elif kind == "conflicting_default":
        field = item.get("field", "?")
        title = f"تضاد default برای فیلد '{field}'"
        description = (
            f"## 📋 شرح\n"
            f"فیلد `{field}` در `{file_}` در دو یا چند جای مختلف "
            f"default value متفاوت دارد.\n\n"
            f"## 🤔 چرا مهم است\n"
            f"defaults متناقض باعث می‌شود رفتار سیستم به ترتیب اجرا/import "
            f"وابسته شود — bug های غیرقابل reproduce.\n\n"
            f"## 🔍 جزئیات\n- علت: {base_reason}"
        )
        proposed_action = (
            f"گام ۱: همه جاهایی که `{field}` default می‌گیرد لیست کن.\n"
            f"گام ۲: یک default واحد انتخاب کن و یک منبع (مثل config یا constant).\n"
            f"گام ۳: تست fixture برای رفتار پیش‌فرض بنویس."
        )
        acceptance_criteria = [
            {"text": f"`{field}` در همه‌جا از یک منبع default می‌گیرد"},
            {"text": "تست fixture رفتار پیش‌فرض را تأیید می‌کند"},
            {"text": "اگر default value تغییر کرد، migration یا backward-compat layer اضافه شد"},
        ]
        risks = "تغییر default value برای کاربران فعلی silent behavior change است — حتماً release note بنویس."
        task_type, priority = "bug_fix", "high"

    else:
        title = f"Anti-pattern: {kind}"
        description = (
            f"{base_reason}\n\n📁 file: {file_}"
            f"{f' (line {line})' if line else ''}\n\n"
            f"🎯 پیشنهاد: این الگو معمولاً منطق سیستم را در شرایط لبه می‌شکند."
        )
        proposed_action = "بازنگری منطق در این نقطه و اضافه‌کردن guard/comment مناسب."
        acceptance_criteria = [
            {"text": "ریشه anti-pattern تشخیص داده شد"},
            {"text": "یا کد اصلاح شد، یا کامنت توجیهی اضافه شد"},
            {"text": "تست edge case نوشته شد"},
        ]
        risks = ""
        task_type, priority = "bug_fix", _priority_for_severity(item.get("priority") or item.get("severity"), "medium")

    target_files = [file_] if file_ else []
    target_locations = [{"path": file_, "lines": str(line) if line else ""}] if file_ else []

    return {
        "type": task_type,
        "priority": priority,
        "title": title,
        "description": description,
        "proposed_action": proposed_action,
        "acceptance_criteria": acceptance_criteria,
        "validation_commands": _vcmds_for_file(file_),
        "risks": risks,
        "dependency_summary": "",
        "related_files": [],
        "target_files": target_files,
        "target_locations": target_locations,
        "_pass": "phase5_anti_pattern",
        "_source": f"scan_v5/anti_pattern:{item.get('_source', '?')}",
    }


# ============================================================
# Coherence → finding
# ============================================================

def _coherence_to_finding(item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    title = item.get("title") or ""
    if not title:
        return None
    cat = item.get("pipeline_category", "?")
    base_desc = item.get("description", "")
    impact = item.get("impact", "")
    fix_hint = item.get("suggested_fix", "")
    description = (
        f"## 📋 شرح ناسازگاری\n"
        f"در pipeline `{cat}` یک ناسازگاری منطقی پیدا شد:\n\n{base_desc}\n\n"
        f"## 💥 پیامد (impact)\n{impact or '(تعیین نشده — در PR بررسی کن)'}\n\n"
        f"## 🛠 پیشنهاد رفع اولیه\n{fix_hint or '(تعیین نشده)'}\n\n"
        f"## 🤔 چرا مهم است\n"
        f"coherence issue یعنی دو بخش کد فرض‌های ناسازگار دارند — معمولاً نشانه‌ی "
        f"refactor ناتمام یا feature flag rot است. این کلاس bug ها در test "
        f"معمولی پیدا نمی‌شوند چون unit test ها در silo اجرا می‌شوند."
    )
    proposed_action = (
        f"گام ۱: هر دو طرف ناسازگاری را بخوان و فرض‌هایشان را لیست کن.\n"
        f"گام ۲: تصمیم بگیر کدام طرف ground truth است — معمولاً business logic مهم‌تر است.\n"
        f"گام ۳: طرف دیگر را با ground truth align کن.\n"
        f"گام ۴: integration test برای این pipeline بنویس تا regression جلوگیری شود."
    )
    acceptance_criteria = [
        {"text": "هر دو طرف ناسازگاری شناسایی + فرض‌هایشان مستند شد"},
        {"text": "ground truth تعیین شد و طرف دیگر align شد"},
        {"text": f"integration test برای pipeline `{cat}` بدون شکست عبور می‌کند"},
        {"text": "PR description توضیح می‌دهد چرا این تصمیم گرفته شد"},
    ]
    risks = (
        "تغییر یک طرف ممکن است downstream consumers را break کند. "
        "حتماً قبل از merge، همه caller های هر دو طرف را بررسی کن."
    )
    priority = _priority_for_severity(item.get("priority"), "medium")

    return {
        "type": "logic_audit",
        "priority": priority,
        "title": f"[منطق] {title[:120]}",
        "description": description,
        "proposed_action": proposed_action,
        "acceptance_criteria": acceptance_criteria,
        "validation_commands": ["pytest", "npm run test"],
        "risks": risks,
        "dependency_summary": f"این مورد در pipeline {cat} است — همه فایل‌های این pipeline مرتبط هستند.",
        "related_files": [],
        "target_files": [],
        "target_locations": [],
        "_pass": "phase5_coherence",
        "_source": "scan_v5/coherence_analyzer",
    }


# ============================================================
# Effectiveness → finding
# ============================================================

def _effectiveness_to_finding(item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    title = item.get("title") or ""
    if not title:
        return None
    outcome_target = item.get("outcome_target", "")
    current_state = item.get("current_state", "")
    sug_action = item.get("suggested_action", "")
    description = (
        f"## 🎯 هدف مطلوب (outcome target)\n{outcome_target or '(تعیین نشده)'}\n\n"
        f"## 📊 وضعیت فعلی\n{current_state or '(تعیین نشده)'}\n\n"
        f"## 🛠 اقدام پیشنهادی\n{sug_action or '(تعیین نشده)'}\n\n"
        f"## ⚙️ ماهیت این finding\n"
        f"این یک effectiveness issue است — کد ممکن است syntactically کار کند "
        f"ولی **outcome مطلوب** (مثل: «فرم باید ایمیل ارسال کند») حاصل نمی‌شود. "
        f"verify باید outcome را اندازه بگیرد، نه فقط وجود فایل/خط."
    )
    proposed_action = (
        "گام ۱: outcome target را به‌صورت قابل اندازه‌گیری بازنویسی کن "
        "(مثلاً: «email send rate > 95% در ۱۰۰ تلاش»).\n"
        "گام ۲: کد را تغییر بده تا outcome محقق شود.\n"
        "گام ۳: یک end-to-end test که outcome را اندازه می‌گیرد بنویس."
    )
    acceptance_criteria = [
        {"text": "outcome target به‌صورت measurable بازنویسی شد"},
        {"text": "کد تغییر کرد تا outcome target محقق شود"},
        {"text": "test E2E که outcome را اندازه می‌گیرد عبور می‌کند"},
        {"text": "metric/log اضافه شد تا در production outcome rate قابل تشخیص باشد"},
    ]
    risks = (
        "بهبود outcome ممکن است latency یا cost را افزایش دهد — قبل/بعد "
        "metric ها را compare کن."
    )
    priority = _priority_for_severity(item.get("priority"), "high")

    return {
        "type": "logic_audit",
        "priority": priority,
        "title": f"[Effectiveness] {title[:120]}",
        "description": description,
        "proposed_action": proposed_action,
        "acceptance_criteria": acceptance_criteria,
        "validation_commands": ["pytest -k 'outcome or e2e'"],
        "risks": risks,
        "dependency_summary": "",
        "related_files": [],
        "target_files": [],
        "target_locations": [],
        "_pass": "phase5_effectiveness",
        "_source": "scan_v5/outcome_analyzer",
    }


# ============================================================
# Notification audit → finding
# ============================================================

def _notification_issue_to_finding(item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    kind = item.get("kind", "")
    file_ = item.get("file") or ""
    if not kind:
        return None
    event = item.get("event_type") or ""
    base_reason = item.get("reason", "")
    suggestion = item.get("suggestion") or item.get("suggested_template", "")

    if kind == "silent_flag_undefined":
        title = f"notification بدون silent flag صریح — {event or 'event ناشناخته'}"
        description = (
            f"## 📋 شرح\n"
            f"در `{file_}` یک notification call پیدا شد که `silent=` صریح "
            f"تعیین نکرده. event_type: `{event or '?'}`.\n\n"
            f"## 🤔 چرا مهم است\n"
            f"silent flag حیاتی است — تفاوت بین «کاربر را disturb کن (critical)» "
            f"و «در پس‌زمینه لاگ کن (routine)». بدون این، behavior به default "
            f"وابسته است که در آینده ممکن است تغییر کند → silent regression.\n\n"
            f"## 🔍 جزئیات\n- علت: {base_reason}"
        )
        proposed_action = (
            "گام ۱: تصمیم بگیر این event critical است یا routine.\n"
            "گام ۲: `silent=False` (critical) یا `silent=True` (routine) را صریح اضافه کن.\n"
            "گام ۳: کامنت ۱ خطی برای rationale."
        )
        acceptance_criteria = [
            {"text": "این notification call `silent=` صریح دارد"},
            {"text": "تصمیم با ماهیت event سازگار است (critical=False, routine=True)"},
            {"text": "کامنت rationale اضافه شد"},
        ]
        risks = ""
        priority = "medium"

    elif kind == "event_type_missing":
        title = f"notification بدون event_type صریح در {file_.rsplit('/', 1)[-1]}"
        description = (
            f"## 📋 شرح\n"
            f"در `{file_}` یک `notify_event` call پیدا شد که اولین پارامتر "
            f"(event_type) رشته‌ای ساده/مبهم است یا خالی.\n\n"
            f"## 🤔 چرا مهم است\n"
            f"event_type کلید routing و filter در سیستم notification است. "
            f"بدون آن، نمی‌توان آن event را به‌صورت per-event mute/customize کرد.\n\n"
            f"## 🔍 جزئیات\n- علت: {base_reason}\n- پیشنهاد: {suggestion}"
        )
        proposed_action = (
            "گام ۱: event_type معنادار snake_case انتخاب کن (مثل `task_done_user_alert`).\n"
            "گام ۲: در `notification_events.json` (اگر هست) registry به‌روز کن.\n"
            "گام ۳: UI tab notification routing را تست کن."
        )
        acceptance_criteria = [
            {"text": "event_type معنادار snake_case تعیین شد"},
            {"text": "در event registry ثبت شد"},
            {"text": "از UI tab notification settings این event قابل toggle است"},
        ]
        risks = "اگر event_type قبلاً به نام دیگری در DB ذخیره شده، rename باعث می‌شود old records orphan شوند."
        priority = "medium"

    elif kind == "silent_critical_mismatch":
        title = f"event critical '{event}' با silent=True (کاربر نمی‌بیند)"
        description = (
            f"## 📋 شرح (severity: high)\n"
            f"event `{event}` به‌عنوان critical شناخته شده ولی silent=True "
            f"دارد — یعنی کاربر هیچ alert نمی‌گیرد.\n\n"
            f"## 🤔 چرا مهم است\n"
            f"این مستقیماً یعنی critical alerts گم می‌شوند. مثلاً «task failed» "
            f"بدون صدا → کاربر نمی‌فهمد و عواقب جدی دارد.\n\n"
            f"## 🔍 جزئیات\n- علت: {base_reason}\n- پیشنهاد: {suggestion}"
        )
        proposed_action = "ساده: `silent=False` کن. یا event_type را به routine_event تغییر بده اگر اصلاً critical نیست."
        acceptance_criteria = [
            {"text": "silent=False یا event_type به routine تغییر کرد"},
            {"text": "تست manual: notification با sound می‌رسد"},
            {"text": "user notification settings respect می‌شود"},
        ]
        risks = "تغییر به silent=False باعث می‌شود کاربر صدای بیشتری بشنود — اگر این event پر-تکرار است، rate-limit اضافه کن."
        priority = "high"

    elif kind == "sound_routine_mismatch":
        title = f"event routine '{event}' با silent=False (noise)"
        description = (
            f"## 📋 شرح\n"
            f"event `{event}` به‌عنوان routine/info شناخته شده ولی silent=False "
            f"دارد — یعنی کاربر را به‌خاطر یک رویداد عادی disturb می‌کند.\n\n"
            f"## 🤔 چرا مهم است\n"
            f"sound noise باعث alert fatigue می‌شود — کاربر همه notifications "
            f"را mute می‌کند و critical ها هم گم می‌شوند.\n\n"
            f"## 🔍 جزئیات\n- علت: {base_reason}"
        )
        proposed_action = "ساده: `silent=True` کن. یا اگر event باید critical باشد، event_type را تغییر بده."
        acceptance_criteria = [
            {"text": "silent=True یا event_type به critical تغییر کرد"},
            {"text": "تست manual: notification بدون sound می‌رسد"},
        ]
        risks = ""
        priority = "medium"

    elif kind == "missing_critical_notification":
        title = f"event critical '{event}' هیچ notification ندارد"
        description = (
            f"## 📋 شرح (severity: high)\n"
            f"event `{event}` در سیستم به‌عنوان critical شناخته شده ولی هیچ "
            f"`notify_event` call برای آن پیدا نشد.\n\n"
            f"## 🤔 چرا مهم است\n"
            f"critical event بدون notification یعنی کاربر هرگز از وقوع آن "
            f"باخبر نمی‌شود. اگر «task failed» critical است ولی notification "
            f"ندارد، کاربر روزها نمی‌فهمد سیستم خاموش بوده.\n\n"
            f"## 🔍 جزئیات\n- علت: {base_reason}\n- پیشنهاد: {suggestion}"
        )
        proposed_action = (
            f"گام ۱: محل وقوع `{event}` در کد را پیدا کن.\n"
            f"گام ۲: `notification_service.notify_event(\"{event}\", message, "
            f"silent=False, priority=\"high\", ...)` اضافه کن.\n"
            f"گام ۳: template message فارسی معنادار بنویس."
        )
        acceptance_criteria = [
            {"text": f"`notify_event(\"{event}\", ...)` call در نقطه وقوع اضافه شد"},
            {"text": "message template فارسی و معنادار است"},
            {"text": "silent=False + priority=\"high\""},
            {"text": "تست: trigger مصنوعی → notification در Telegram دیده می‌شود"},
        ]
        risks = "اگر event پر-تکرار است، rate-limit اضافه کن تا spam نشود."
        priority = "high"

    else:
        title = f"audit notification: {kind}"
        description = f"{base_reason}\n\n🛠 پیشنهاد: {suggestion}"
        proposed_action = ""
        acceptance_criteria = [{"text": "این مورد بررسی و حل شد"}]
        risks = ""
        priority = _priority_for_severity(item.get("severity"), "medium")

    target_files = [file_] if file_ else []
    target_locations = [{"path": file_, "lines": str(item.get("line", ""))}] if file_ else []

    return {
        "type": "notification_audit",
        "priority": priority,
        "title": title,
        "description": description,
        "proposed_action": proposed_action,
        "acceptance_criteria": acceptance_criteria,
        "validation_commands": _vcmds_for_file(file_),
        "risks": risks,
        "dependency_summary": "این مورد روی notification pipeline تأثیر می‌گذارد — همه consumer های این event باید چک شوند.",
        "related_files": [],
        "target_files": target_files,
        "target_locations": target_locations,
        "_pass": "phase5_notification_audit",
        "_source": "scan_v5/notification_auditor",
    }


# ============================================================
# Change-impact → finding
# ============================================================

def _change_impact_to_finding(item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    if item.get("recommended_action") == "no_action":
        if item.get("risk") not in ("high", "medium"):
            return None
    changed = item.get("changed_file", "?")
    dependent = item.get("dependent_file", "?")
    risk = item.get("risk", "?")
    reason = item.get("reason", "")
    rec_action = item.get("recommended_action", "?")
    title = (
        f"🔄 {(dependent or '?').rsplit('/', 1)[-1]} نیازمند بررسی به‌خاطر "
        f"تغییر در {(changed or '?').rsplit('/', 1)[-1]}"
    )
    description = (
        f"## 📋 شرح\n"
        f"یک فایل اخیراً تغییر کرده و این فایل (dependent) به آن وابسته است. "
        f"بدون بررسی، احتمال silent regression وجود دارد.\n\n"
        f"## 🔍 جزئیات\n"
        f"- 📂 فایل تغییریافته: `{changed}`\n"
        f"- 📂 فایل وابسته (نیازمند بررسی): `{dependent}`\n"
        f"- 🔥 risk level: **{risk}**\n"
        f"- 📝 reason: {reason}\n"
        f"- 🛠 recommended action: `{rec_action}`\n\n"
        f"## 🤔 چرا مهم است\n"
        f"تغییرات در فایل upstream می‌توانند contract را عوض کنند (signature، "
        f"behavior، side-effect). فایل dependent ممکن است هنوز با فرض قدیمی "
        f"کار کند → cascading failure که در test اصلی فایل تغییریافته دیده "
        f"نمی‌شود."
    )
    proposed_action = (
        f"گام ۱: diff آخر در `{changed}` را بخوان — چی عوض شده.\n"
        f"گام ۲: کد در `{dependent}` که این تغییر را مصرف می‌کند پیدا کن.\n"
        f"گام ۳: تطبیق بده + integration test بنویس."
    )
    acceptance_criteria = [
        {"text": f"diff `{changed}` بررسی شد و تأثیر بر `{dependent}` مستند شد"},
        {"text": "کد dependent با contract جدید align شد"},
        {"text": "integration test که هر دو فایل را پوشش می‌دهد عبور می‌کند"},
    ]
    risks_str = "اگر فایل dependent در محل‌های دیگر هم استفاده می‌شود، تغییرات آن می‌تواند آن‌ها را break کند."
    priority_map = {"high": "high", "medium": "medium", "low": "low"}
    priority = priority_map.get(str(risk).lower(), "medium")

    return {
        "type": "dependency_update",
        "priority": priority,
        "title": title,
        "description": description,
        "proposed_action": proposed_action,
        "acceptance_criteria": acceptance_criteria,
        "validation_commands": _vcmds_for_file(dependent),
        "risks": risks_str,
        "dependency_summary": f"فایل `{dependent}` یکی از مصرف‌کنندگان `{changed}` است.",
        "related_files": [{"path": changed, "reason": "فایل upstream که تغییر کرده", "at_line": ""}],
        "target_files": [dependent] if dependent and dependent != "?" else [],
        "target_locations": (
            [{"path": dependent, "lines": ""}] if dependent and dependent != "?" else []
        ),
        "_pass": "phase5_change_impact",
        "_source": "scan_v5/dependency_analyzer",
    }


# ============================================================
# Main aggregator
# ============================================================

def _upstream_impact_to_finding(item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """🆕 (bug 23) — finding برای upstream-impact (deps در خطر تغییر)."""
    if not isinstance(item, dict):
        return None
    changed = item.get("changed_file", "?")
    upstream = item.get("upstream_file", "?")
    risk = item.get("risk", "?")
    reason = item.get("reason", "")
    rec_action = item.get("recommended_action", "?")
    title = (
        f"⬆️ {(upstream or '?').rsplit('/', 1)[-1]} ممکن است نیاز به update "
        f"داشته باشد به‌خاطر تغییرات در {(changed or '?').rsplit('/', 1)[-1]}"
    )
    description = (
        f"## 📋 شرح\n"
        f"یک فایل تغییر کرده و حالا از API/behavior جدیدی استفاده می‌کند که "
        f"upstream فعلی ممکن است پشتیبانی نکند.\n\n"
        f"## 🔍 جزئیات\n"
        f"- 📂 فایل تغییریافته (consumer): `{changed}`\n"
        f"- 📂 فایل upstream (producer — نیازمند update): `{upstream}`\n"
        f"- 🔥 risk: **{risk}**\n"
        f"- 📝 reason: {reason}\n"
        f"- 🛠 recommended: `{rec_action}`\n\n"
        f"## 🤔 چرا مهم است\n"
        f"اگر upstream متد/تابع/فیلد لازم را اضافه نکند، consumer در runtime "
        f"شکست می‌خورد یا silent failure می‌دهد."
    )
    acceptance_criteria = [
        {"text": f"بررسی شد `{changed}` چه API ای از `{upstream}` می‌خواهد"},
        {"text": f"اگر API در `{upstream}` نیست، اضافه شد"},
        {"text": "تست integration که هر دو سمت را پوشش می‌دهد عبور می‌کند"},
    ]
    priority_map = {"high": "high", "medium": "medium", "low": "low"}
    priority = priority_map.get(str(risk).lower(), "medium")
    return {
        "type": "upstream_update",
        "priority": priority,
        "title": title,
        "description": description,
        "proposed_action": (
            f"گام ۱: `{changed}` را بخوان و usages جدید از `{upstream}` را پیدا کن.\n"
            f"گام ۲: API contract در `{upstream}` چک کن.\n"
            f"گام ۳: اگر contract ناسازگار است، `{upstream}` را extend کن."
        ),
        "acceptance_criteria": acceptance_criteria,
        "validation_commands": _vcmds_for_file(upstream),
        "risks": f"تغییر `{upstream}` ممکن است بقیه consumers را تحت تأثیر قرار دهد — قبل از تغییر، همهٔ مصرف‌کنندگانش را check کن.",
        "dependency_summary": f"`{changed}` به `{upstream}` وابسته است.",
        "related_files": [{"path": changed, "reason": "consumer که تغییر کرده", "at_line": ""}],
        "target_files": [upstream] if upstream and upstream != "?" else [],
        "target_locations": [{"path": upstream, "lines": ""}] if upstream and upstream != "?" else [],
        "_pass": "phase5_upstream_impact",
        "_source": "scan_v5/dependency_analyzer",
    }


def _added_ripple_to_finding(item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """🆕 (bug 23) — finding برای added-file ripple (orphan / missing companion)."""
    if not isinstance(item, dict):
        return None
    added = item.get("added_file", "?")
    issue_type = str(item.get("issue_type", "")).lower()
    risk = str(item.get("risk", "medium")).lower()
    reason = item.get("reason", "")

    if issue_type == "orphan_added":
        title = f"🆕 فایل جدید `{added.rsplit('/', 1)[-1]}` به هیچ‌جا متصل نیست (orphan)"
        description = (
            f"## 📋 شرح\n"
            f"این فایل تازه اضافه شده ولی هیچ فایلی آن را import نمی‌کند.\n\n"
            f"## 🔍 جزئیات\n"
            f"- 📂 added: `{added}`\n"
            f"- 🔥 risk: **{risk}**\n"
            f"- 📝 reason: {reason}\n\n"
            f"## 🤔 چرا مهم است\n"
            f"فایل orphan معمولاً یعنی wiring فراموش شده. یا باید به جای مناسبی "
            f"متصل شود، یا اگر واقعاً لازم نیست، حذف شود."
        )
        acceptance_criteria = [
            {"text": "بررسی شد چه فایلی باید این فایل را import کند"},
            {"text": "wiring اضافه شد یا فایل حذف شد"},
            {"text": "scan بعدی این فایل را orphan گزارش نمی‌کند"},
        ]
        related = []
        target_files = [added]
    else:  # missing_companion
        comp_kind = str(item.get("companion_kind", ""))
        comp_path = str(item.get("companion_path", ""))
        title = (
            f"🧩 `{added.rsplit('/', 1)[-1]}` نیازمند {comp_kind} است "
            f"(در `{comp_path[:60]}` پیدا نشد)"
        )
        description = (
            f"## 📋 شرح\n"
            f"این فایل جدید اضافه شده ولی companion ضروری ({comp_kind}) ندارد.\n\n"
            f"## 🔍 جزئیات\n"
            f"- 📂 added: `{added}`\n"
            f"- 📂 expected companion: `{comp_path}`\n"
            f"- 🔥 risk: **{risk}**\n"
            f"- 📝 reason: {reason}\n\n"
            f"## 🤔 چرا مهم است\n"
            f"بدون companion، فایل به‌مرور isolated می‌ماند — نه تست دارد، نه consumer."
        )
        acceptance_criteria = [
            {"text": f"{comp_kind} مناسب برای `{added}` ایجاد شد"},
            {"text": "کیفیت companion: حداقل ۱ assertion/binding واقعی دارد"},
            {"text": "scan بعدی این finding را نمی‌سازد"},
        ]
        related = [{"path": added, "reason": f"فایل جدید که {comp_kind} می‌خواهد", "at_line": ""}]
        target_files = []
    priority_map = {"high": "high", "medium": "medium", "low": "low"}
    return {
        "type": "ripple_companion",
        "priority": priority_map.get(risk, "medium"),
        "title": title,
        "description": description,
        "proposed_action": (
            f"بررسی کن فایل `{added}` به چه companion ای نیاز دارد و آن را ایجاد یا متصل کن."
        ),
        "acceptance_criteria": acceptance_criteria,
        "validation_commands": _vcmds_for_file(added),
        "risks": "اگر companion ایجاد نشود، در scan های بعدی همچنان flag می‌شود.",
        "dependency_summary": f"فایل جدید `{added}` بدون companion.",
        "related_files": related,
        "target_files": target_files,
        "target_locations": [{"path": added, "lines": ""}],
        "_pass": "phase5_added_ripple",
        "_source": "scan_v5/dependency_analyzer",
    }


def phase5_findings_to_standard(
    stale: Optional[Dict[str, Any]] = None,
    anti_patterns: Optional[List[Dict[str, Any]]] = None,
    coherence_issues: Optional[List[Dict[str, Any]]] = None,
    effectiveness_issues: Optional[List[Dict[str, Any]]] = None,
    notification_audit: Optional[Dict[str, Any]] = None,
    change_impact: Optional[List[Dict[str, Any]]] = None,
    upstream_impact: Optional[List[Dict[str, Any]]] = None,
    added_ripple: Optional[List[Dict[str, Any]]] = None,
    delta: Optional[Dict[str, Any]] = None,
    inventory: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """تبدیل تمام Phase 5 findings به standard findings با ساختار غنی."""
    out: List[Dict[str, Any]] = []
    if stale:
        for s in (stale.get("structural") or []):
            try:
                f = _stale_to_finding(s)
                if f:
                    out.append(f)
            except Exception as e:
                logger.debug(f"stale → finding failed: {e}")
        for s in (stale.get("semantic") or []):
            try:
                f = _stale_to_finding(s)
                if f:
                    out.append(f)
            except Exception:
                pass
    for ap in (anti_patterns or []):
        try:
            f = _anti_pattern_to_finding(ap)
            if f:
                out.append(f)
        except Exception:
            pass
    for c in (coherence_issues or []):
        try:
            f = _coherence_to_finding(c)
            if f:
                out.append(f)
        except Exception:
            pass
    for e in (effectiveness_issues or []):
        try:
            f = _effectiveness_to_finding(e)
            if f:
                out.append(f)
        except Exception:
            pass
    if notification_audit:
        for n in (notification_audit.get("structural_issues") or []):
            try:
                f = _notification_issue_to_finding(n)
                if f:
                    out.append(f)
            except Exception:
                pass
        for n in (notification_audit.get("ai_template_issues") or []):
            try:
                f = _notification_issue_to_finding(n)
                if f:
                    out.append(f)
            except Exception:
                pass
    for ci in (change_impact or []):
        try:
            f = _change_impact_to_finding(ci)
            if f:
                out.append(f)
        except Exception:
            pass
    # 🆕 (bug 23) — upstream + added ripple
    for ui in (upstream_impact or []):
        try:
            f = _upstream_impact_to_finding(ui)
            if f:
                out.append(f)
        except Exception:
            pass
    for ar in (added_ripple or []):
        try:
            f = _added_ripple_to_finding(ar)
            if f:
                out.append(f)
        except Exception:
            pass
    return out
