"""Compact prompt for the «بازرس ویژه» chat on weaker / smaller models (2026-11-15, owner: «اونم انجام بده»).

Why: the 12 «دستورات عمومی سیستم» alone are ~25 000 characters (one rule is 8 600) and the agent system prompt adds
~9 000 more. A large model follows that; a small or cheap one drowns in it — it forgets the output format, copies
examples, or runs out of context before it has read a single file. The full text stays the source of truth (the
panel `/general-instructions` and the strong models use it unchanged); here every rule has a short form that keeps
its *decisions and formats* and drops the long examples:

  * ``is_compact_model`` — which models get the compact prompt (context window ≤ 131k or not a frontier family;
    ``INSPECTOR_COMPACT_PROMPT=1|0`` forces it on/off for every model);
  * ``compact_general_instructions`` — the 12 rules in ~4 000 characters (keyed by the rule ``id``; a rule without a
    short form keeps its full text, so a new rule is never silently dropped);
  * ``build_repo_map`` — instead of «📁 dir (N files) — e.g. a, b», the real file names, the directories that match
    the user's words first, inside a character budget — so the model calls read_file on paths that exist;
  * ``agent_system_compact`` — the agent (tool-calling) system prompt in ~3 000 characters; the Render / Postgres
    tool manuals are added only when the request or logs are about deploys / databases.
"""

from __future__ import annotations

import os
import re
from collections import defaultdict
from typing import Dict, Iterable, List, Optional

# ── which models ─────────────────────────────────────────────────────────────────────────────────────────────────────
_FRONTIER = ("claude", "gpt-5", "gpt-4.1", "gpt-4o", "o1", "o3", "o4", "gemini-2.5-pro", "gemini-3", "grok-4")
_SMALL_HINTS = ("mini", "nano", "flash", "lite", "small", "haiku", "8b", "7b", "3b", "1b", "14b", "free")


def is_compact_model(model_id: str, context_window: Optional[int] = None) -> bool:
    force = os.environ.get("INSPECTOR_COMPACT_PROMPT", "").strip().lower()
    if force in ("1", "true", "yes", "on"):
        return True
    if force in ("0", "false", "no", "off"):
        return False
    m = (model_id or "").lower()
    if context_window and context_window <= 131_072:
        return True
    if any(h in m for h in _SMALL_HINTS):
        return True
    return not any(m.startswith(p) or f"/{p}" in m for p in _FRONTIER)


# ── the 12 rules, short ──────────────────────────────────────────────────────────────────────────────────────────────
SHORT_RULES: Dict[str, str] = {
    "sys_analysis": "مستقیم تحلیل کن و راه‌حلِ عملی بده؛ هرگز از کاربر کارِ دستی (grep، اجرای دستور) نخواه.",
    "sys_intent": "پیام‌های کوتاه/عامیانه («آره»، «همونه») را با تاریخچهٔ گفت‌وگو بفهم.",
    "sys_compat": "سبک و ساختارِ موجودِ پروژه را رعایت کن؛ import ها، type ها و config های وابسته را بررسی کن.",
    "sys_retry_depth": (
        "اگر کاربر گفت «هنوز نشد»: فیکسِ قبلی ناکافی بوده — همان را تکرار نکن؛ دامنه را وسیع کن و زنجیره را دنبال کن "
        "(فرانت ⇐ API ⇐ service ⇐ model ⇐ DB؛ یا route ⇐ middleware ⇐ config ⇐ env)."),
    "sys_no_guess": (
        "نگو «دسترسی ندارم»/«دوباره بفرست»؛ با فایل‌هایی که داری کار کن. محتوای فایلِ ندیده را حدس نزن: فایلِ موجود و "
        "ندیده را در action_plan نگذار (سیستم ردش می‌کند) — در analysis بگو کدام فایل لازم است."),
    "sys_holistic_fix": (
        "یکجا و کامل حل کن: وابستگی‌ها را دنبال کن (package.json «type» ⇐ ESM/CJS ِ config ها؛ requirements ⇐ نسخهٔ "
        "Python/Dockerfile). نسخهٔ پکیجی را که از وجودش مطمئن نیستی پین نکن (از ^ استفاده کن). پیش از ثبت، build را در "
        "ذهن اجرا کن."),
    "sys_deploy_safe": (
        "کدِ خروجی باید بی‌خطا build شود (import، پرانتز، JSX، JSON). همهٔ فایل‌ها داخلِ همان JSON ِ action_plan؛ "
        "هرگز «// بقیهٔ کد». فایلِ بیش از ۲۰۰ خط ⇒ فقط modify_sections:\n"
        '{"path":"…","operation":"modify_sections","sections":[{"find":"۳ تا ۱۰ خطِ کپی‌شدهٔ دقیق از فایل","replace":"…"}]}\n'
        "find حرف‌به‌حرف (با فاصله و تورفتگی) از متنِ خوانده‌شده کپی شود — یک نویسه فرق = شکست. حذف: replace خالی. "
        "Dockerfile/اسکریپتِ deploy را بازنویسی نکن؛ build context را بفهم."),
    "sys_preserve_existing": (
        "هرگز فایلِ موجود را از صفر بازننویس و قابلیتی را حذف نکن مگر کاربر صریحاً بخواهد؛ placeholder به‌جای کارِ واقعی "
        "ممنوع. پیش از create ببین فایل هست یا نه (هست ⇒ modify). فایلی که در stack trace آمده را بی‌نقلِ محتوایش «درست» "
        "نخوان. لاگ منبعِ حقیقت است، نه توصیفِ کاربر. مشکلِ env ِ Render ⇒ در action_plan فیلدِ "
        '"render_actions": [{"type":"set_env_var","service_name":"…","key":"…","value":"…"}] (راز را حدس نزن). '
        "خطای wheel/cargo با Python 3.13+ ⇒ فقط runtime.txt با python-3.12.7."),
    "sys_clarify_first": (
        "اگر چند راهِ معقول با trade-off هست، اطلاعاتِ حیاتی/راز کم است یا اطمینانت زیرِ ۷۰٪ است، به‌جای files بپرس:\n"
        '{"ask_user":{"question":"…","type":"single|multi|text","context":"…","options":[{"id":"snake_id","label":"…",'
        '"description":"…"}],"default":"snake_id"}}\n'
        "خطای اتصال (Connection refused، could not connect، Errno 111) ⇒ همیشه ask_user با سه گزینه: graceful در کد / "
        "ست‌کردنِ env در Render / حذفِ وابستگی. پاسخِ [user_clarification …] را دوباره نپرس — اجرا کن. "
        'scope ِ واقعاً بزرگ (>۵ فایل، چند ماژول) ⇒ {"route_to":"deep_scan","reason":"…"}.'),
    "sys_exact_intent": (
        "کلمات را تحت‌اللفظی بخوان: «فقط» = فقط همان‌جا، «نباید» = ممنوع، «اضافه کن» = بی حذفِ چیزی. کارِ درستِ مرحلهٔ "
        "قبل را نشکن."),
}


def compact_general_instructions(instructions_list: Iterable[dict]) -> str:
    lines = ["\n## 📌 دستورات عمومی (خلاصه — همه لازم‌الاجرا):"]
    for idx, inst in enumerate(instructions_list, 1):
        short = SHORT_RULES.get(inst.get("id", ""))
        body = short if short else inst.get("prompt_detail", inst.get("content", ""))
        lines.append(f"{idx}. {inst.get('title', '')}: {body}")
    return "\n".join(lines) + "\n"


# ── repo map ─────────────────────────────────────────────────────────────────────────────────────────────────────────
_WORD = re.compile(r"[A-Za-z_][A-Za-z0-9_]{2,}")


def _terms(text: str) -> set:
    out = set()
    for w in _WORD.findall(text or ""):
        w = w.lower()
        out.add(w)
        out.update(p for p in re.split(r"_|(?<=[a-z])(?=[A-Z])", w) if len(p) >= 3)
    return out


def build_repo_map(code_files: List[str], query: str = "", max_chars: int = 3500) -> str:
    """Every directory with its real file names; directories whose paths match the request come first."""
    if not code_files:
        return ""
    q = _terms(query)
    by_dir: Dict[str, List[str]] = defaultdict(list)
    for f in code_files:
        d, _, name = f.rpartition("/")
        by_dir[d or "."].append(name)

    def score(d: str) -> tuple:
        names = by_dir[d]
        hits = sum(1 for t in q if t in d.lower()) * 3 + sum(1 for n in names for t in q if t in n.lower())
        return (-hits, d.count("/"), d)

    lines = [f"نقشهٔ مخزن ({len(code_files)} فایل؛ مسیرها واقعی‌اند — با همین مسیرها read_file بزن):"]
    used = len(lines[0])
    left_out = 0
    for d in sorted(by_dir, key=score):
        names = sorted(by_dir[d])
        line = f"{d}/: " + ", ".join(names)
        if used + len(line) + 1 > max_chars:
            room = max_chars - used - len(d) - 20
            if room > 60:  # the directory fits partly
                cut = ", ".join(names)[:room].rsplit(", ", 1)[0]
                line = f"{d}/: {cut}, … (+{len(names) - cut.count(', ') - 1})"
                lines.append(line)
                used += len(line) + 1
            else:
                left_out += len(names)
            continue
        lines.append(line)
        used += len(line) + 1
    if left_out:
        lines.append(f"… {left_out} فایلِ دیگر — list_files(filter) برای دیدنشان")
    return "\n".join(lines)


# ── agent system prompt, compact ─────────────────────────────────────────────────────────────────────────────────────
_RENDER_HINT = re.compile(r"render|deploy|دیپلوی|build|بیلد|env|متغیر|service|سرویس|runtime|python-?3|node", re.I)
_DB_HINT = re.compile(r"postgres|database|DATABASE_URL|پایگاه|دیتابیس|\bdb\b|connection refused|asyncpg|psycopg", re.I)


def agent_system_compact(owner: str, repo: str, general_text: str, repo_map: str, request_text: str = "") -> str:
    render = bool(_RENDER_HINT.search(request_text or ""))
    db = bool(_DB_HINT.search(request_text or ""))
    parts = [
        f"تو توسعه‌دهندهٔ ارشد و بازرسِ پروژهٔ {owner}/{repo} هستی. به فارسی جواب بده.",
        general_text,
        "## روش (گام‌به‌گام)\n"
        "1. خطا/لاگِ کاربر را دقیق بخوان — منبعِ حقیقت است.\n"
        "2. فایل‌های مرتبط را با read_file بخوان (فایلِ بزرگ: file_outline سپس read_file با start_line/end_line؛ "
        "search_code برای پیدا کردنِ یک نام).\n"
        "3. علتِ ریشه‌ای را پیدا کن؛ اگر config چیزی می‌گوید و لاگ چیزِ دیگری، اول این تضاد را بفهم.\n"
        "4. preflight_check(files) بزن؛ هر ایرادی (حتی در فایلِ دیگر) را در همان action_plan رفع کن.\n"
        "5. submit_action_plan(analysis, files, commit_message). اگر واقعاً فیکسِ قطعی نداری، با files=[] و "
        "توضیحِ دقیق submit کن — هرگز بی‌نتیجه تمام نکن.\n"
        "فقط فایلِ خوانده‌شده در files؛ فایلِ >۲۰۰ خط ⇒ modify_sections با find ِ کپی‌شده؛ کمترین تغییرِ لازم.",
    ]
    if render:
        parts.append(
            "## Render\n"
            "render_list_services ⇐ service_id؛ render_get_deploys / render_get_deploy_logs (لاگِ واقعیِ build — پیش از "
            "حدس). مشکلِ پلتفرمی را روی پلتفرم حل کن: render_set_env_var (مثلاً PYTHON_VERSION که runtime.txt را "
            "override می‌کند)، render_update_service_settings(build_command/start_command — این‌ها env نیستند)، سپس "
            "render_trigger_deploy(clear_cache=true). صفحهٔ placeholder/خالی با deploy ِ موفق ⇒ اول buildCommand را ببین، "
            "نه کد.")
    if db:
        parts.append(
            "## PostgreSQL\n"
            "render_list_postgres ⇐ اگر نیست render_create_postgres ⇐ یک بار render_get_postgres (polling نکن؛ اگر "
            "available نبود submit کن و بگو بعداً ادامه بدهد) ⇐ render_get_postgres_connection ⇐ "
            "render_set_env_var(DATABASE_URL) ⇐ render_trigger_deploy.")
    parts.append(
        "## بازگشت\nrevert_to_branch(target_branch) فقط وقتی کاربر صریحاً برگشت خواسته.")
    parts.append("## " + repo_map if repo_map else "")
    return "\n\n".join(p for p in parts if p)
