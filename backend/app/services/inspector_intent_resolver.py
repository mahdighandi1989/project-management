"""
🆕 (inspector-scan) Intent resolver — تصمیم می‌گیرد آیا یک پیام Inspector
chat باید scan موردی deep را trigger کند، و اگر بله، پارامترهای آن را از
context موجود استخراج می‌کند.

سیاست (heuristic سبک):
- اگر پیام شامل کلیدواژه‌های اصلاح/تحلیل/درست‌کن باشد → trigger
- اگر backend_logs اخیر شامل stack trace باشد → trigger
- در غیر این صورت → no_anchor

استخراج پارامترها:
- focus_notes: متن پیام کاربر + خلاصهٔ ۳ خط آخر error logs
- custom_paths: از URL، stack trace، linked_task.target_files، نام فایل‌ها
  در پیام
- selected_sections: اگر custom_paths خالی است، از URL/backend استنباط می‌شود
- include_dependencies: همیشه True در این مسیر
- visual_debug: اگر screenshots وجود دارد یا mode == "visual_debug"
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


# ─── کلیدواژه‌های trigger ─────────────────────────────────────────
# 🔴 ریشهٔ واقعی مشکل «scan با ۹۶ proposal بی‌ربط» این نبود که trigger keywords
# اشتباه بودند، بلکه scan وقتی فعال می‌شد، **scope را نمی‌شناخت** و همه پاس‌ها
# را روی کل پروژه می‌زد. trigger keywords دوباره گسترده شدند ولی scope filtering
# پایین‌تر در oversight_deep_scan_service اعمال می‌شود (پاس‌های نامربوط skip).
_TRIGGER_KEYWORDS_FA = (
    "بررسی کن", "اصلاح کن", "درست کن", "این باگ", "مشکل دار",
    "خطا داره", "خطا میده", "این کار نمی", "این کار نمیکن", "این کار نمیکنه",
    "این چرا", "این رو ببین", "اعمال کن", "پیاده کن", "پیاده‌سازی",
    "refactor", "بهینه", "ارتقا", "ارتقاء", "این رو درست", "رفع",
    "این رو حل", "حل کن", "این رو بهبود", "بهبود بده", "این مشکل",
    "چه مشکلی", "چی مشکلی", "این صفحه چه", "این صفحه چی",
    "ایراد داره", "ایراد دار", "بهینه کن", "بازنویسی کن",
    # vague + feature/upgrade keywords
    "شکست خورد", "بالا نیومد", "بالا نیامد", "دیپلوی نشد", "بیلد خراب",
    "بیلد نشد", "ارور داد", "ارور میده", "ارور می‌دهد", "down شده",
    "اضافه کن", "اضافه‌ش کن", "اضافه میکنی", "قابلیت", "ویژگی",
    "امکان", "بتونم", "بتوانم", "بتونه", "بتواند",
    "این رو بساز", "بسازش", "merge کن", "integrate", "این رو ادغام",
    "ارتقا بده", "ارتقا بدم", "راه اندازی", "راه‌اندازی", "راه بندازی",
    "راه بنداز", "بالا بیار", "بالا بیاور",
    # explicit scan (بالاترین confidence)
    "اسکن کن", "اسکن عمیق", "اسکن موردی", "اودیت کن", "audit کن",
    "بررسی عمیق", "تحلیل کامل پروژه", "گزارش کامل", "بازرسی کامل",
)
_TRIGGER_KEYWORDS_EN = (
    "fix", "bug", "broken", "not working", "doesn't work", "doesnt work",
    "investigate", "refactor", "improve", "apply", "implement",
    "solve", "diagnose", "debug this", "this issue", "why does",
    "add feature", "add support", "implement support", "add ability",
    "introduce", "deploy failed", "build failed", "ci failed",
    "deployment broken", "build broken", "feature add",
    "scan deep", "deep scan", "audit", "full scan", "selective scan",
)

# کلیدواژه‌های قوی برای vague-intent fallback.
_STRONG_KEYWORDS = {
    "شکست خورد", "بالا نیومد", "دیپلوی نشد", "بیلد خراب", "بیلد نشد",
    "ارور داد", "اضافه کن", "قابلیت", "امکان", "ارتقا بده",
    "راه اندازی", "راه‌اندازی", "بالا بیار",
    "deploy failed", "build failed", "ci failed", "add feature",
    "add support", "introduce", "deep scan",
}


def _is_strong_keyword(k: str) -> bool:
    return k.strip().lower() in {s.lower() for s in _STRONG_KEYWORDS}


# 🆕 (v2 M1) — stopwords برای استخراج keyword
_STOPWORDS_FA = {
    "این", "که", "از", "به", "در", "می", "ها", "را", "اون", "من", "ما",
    "تو", "شما", "است", "هست", "بود", "اگر", "حتی", "ولی", "چون", "چه",
    "چی", "کجا", "کنه", "کنم", "بکن", "کنیم", "کنه",
    # 🆕 (v2 audit) — verb-tense markers که semantic precision را پایین می‌آورند
    "شده", "شد", "میشه", "میشود", "می‌شود", "می‌شد", "بشه", "بشود",
    "نشد", "نشده", "بوده", "خواهد", "خواست", "بشم", "بشیم",
}
_STOPWORDS_EN = {
    "the", "and", "for", "with", "this", "that", "from", "but", "are",
    "was", "will", "what", "where", "when", "how", "have", "has", "had",
    "you", "your", "they", "their", "there", "here",
}


def _extract_focus_keywords(text: str) -> List[str]:
    """استخراج اسم‌های مهم برای semantic search — برای vague-intent fallback."""
    if not text:
        return []
    tokens = re.findall(r"[\w\-؀-ۿ]{3,}", text.lower())
    stops = _STOPWORDS_FA | _STOPWORDS_EN
    out: List[str] = []
    seen = set()
    for t in tokens:
        if t in stops or t.isdigit():
            continue
        if t not in seen:
            seen.add(t)
            out.append(t)
    return out[:12]


# 🆕 (clarify-first) — pattern های error های infrastructure که scan **نباید**
# trigger شود برایشان. این error ها معمولاً یک fix هدفمند دارند (set env var،
# graceful degradation، یا restart) و scan ۱۲-pass فقط overhead است.
# مستقیم به smart-chat می‌روند که می‌تواند ask_user با گزینه‌های trade-off
# نمایش دهد.
_INFRA_ERROR_PATTERNS = (
    "ConnectionRefusedError",
    "connect call failed",
    "could not connect to server",
    "Connection refused",
    "[Errno 111]",
    "asyncpg.exceptions.ConnectionFailureError",
    "psycopg2.OperationalError",
    "redis.exceptions.ConnectionError",
    "Errno 110",  # Connection timed out
    "ConnectTimeoutError",
    "DNSLookupError",
    "Name or service not known",
    "Temporary failure in name resolution",
)


# 🆕 (clarify-first v3) — خطاهای build/packaging روی Render/Docker. این‌ها
# تقریباً همیشه یک fix هدفمند دارند (runtime.txt برای نسخهٔ Python، یا pin
# کردن یک package)، نه scan کل پروژه. مستقیم به smart-chat.
_BUILD_ERROR_PATTERNS = (
    "maturin failed",
    "Read-only file system",
    "Failed to build wheel",
    "metadata-generation-failed",
    "Cargo metadata failed",
    "cargo metadata",
    "Getting requirements to build wheel",
    "Preparing metadata (pyproject.toml) did not run successfully",
    "error: subprocess-exited-with-error",
    "Failed to build tiktoken",
    "pydantic-core",  # معمولاً با خطای Rust compile در Python 3.13/3.14
    "cp314",
    "cp313",
    "python3.14",
    "python3.13",
    "Build failed 😞",
    "==> Build failed",
)


# 🆕 (clarify-first v3) — خطاهای قطعی کد که یک محل دقیق دارند (stack trace
# به فایل:خط اشاره می‌کند). این‌ها یک fix هدفمند تک‌فایلی دارند و scan ۱۲-pass
# روی کل پروژه فقط ۴۰+ proposal بی‌ربط تولید می‌کند. مستقیم به smart-chat.
_DETERMINISTIC_CODE_ERRORS = (
    "AttributeError",
    "has no attribute",
    "ImportError",
    "ModuleNotFoundError",
    "cannot import name",
    "NameError",
    "is not defined",  # NameError signature (دقیق‌تر از "name '")
    "SyntaxError",
    "IndentationError",
    "TypeError:",
    "KeyError:",
    "NoneType' object",
    "object has no attribute",
    "ImproperlyConfigured",
    "No module named",
)


def _scan_text_in_logs(backend_logs: Optional[List[Dict[str, Any]]], patterns) -> Optional[str]:
    """جستجوی patterns در ۳۰ پیام آخر backend_logs. اولین match را برمی‌گرداند."""
    if not backend_logs:
        return None
    for entry in backend_logs[-30:]:
        msg = ""
        if isinstance(entry, dict):
            msg = str(entry.get("message", "") or entry.get("content", "") or "")
        elif isinstance(entry, str):
            msg = entry
        if not msg:
            continue
        for pat in patterns:
            if pat in msg:
                return pat
    return None


def _has_infra_connection_error(backend_logs: Optional[List[Dict[str, Any]]]) -> Optional[str]:
    """اگر backend_logs شامل یکی از infrastructure connection errors است،
    pattern matched را برگردان. در غیر این صورت None.
    """
    return _scan_text_in_logs(backend_logs, _INFRA_ERROR_PATTERNS)


def _has_deterministic_code_error(
    backend_logs: Optional[List[Dict[str, Any]]],
    user_message: str = "",
) -> Optional[str]:
    """خطای قطعی کد (AttributeError و...) در logs یا پیام کاربر؟"""
    p = _scan_text_in_logs(backend_logs, _DETERMINISTIC_CODE_ERRORS)
    if p:
        return p
    # همچنین در متن پیام کاربر چک کن (کاربر ممکن است error را paste کند)
    for pat in _DETERMINISTIC_CODE_ERRORS:
        if pat in (user_message or ""):
            return pat
    return None


def _has_build_error(
    backend_logs: Optional[List[Dict[str, Any]]],
    user_message: str = "",
) -> Optional[str]:
    """خطای build/packaging (maturin، pydantic-core، Read-only fs و...)؟"""
    p = _scan_text_in_logs(backend_logs, _BUILD_ERROR_PATTERNS)
    if p:
        return p
    for pat in _BUILD_ERROR_PATTERNS:
        if pat in (user_message or ""):
            return pat
    return None


# 🆕 (v3 simple-op detection) — اگر درخواست کاربر یک عملیات ساده روی
# یک فایل مشخص است (مثل «runtime.txt بساز»، «این خط را به requirements
# اضافه کن»)، **scan نباید trigger شود** — directly به smart-chat برود.
# scan ۱۲-pass به‌صورت ذاتی scope broad می‌گیرد و برای fix دقیق و کوچک
# اشتباه است.
# Verb های file-creation
_CREATE_VERBS_FA = ("بساز", "ایجاد کن", "ساختن", "ایجاد", "بسازش")
_CREATE_VERBS_EN = ("create", "make", "generate", "build")

# Pattern برای filename — هر چیزی شامل دات و extension، یا نام‌های شناخته‌شده
# بدون extension (Dockerfile، Makefile، …)
_FILENAME_RE = re.compile(
    r"(?:^|[\s`'\"(/])("
    r"(?:[\w-]+/)*[\w.-]+\.[a-z]{1,5}"  # با extension
    r"|Dockerfile|Makefile|Procfile|Caddyfile|Vagrantfile|Rakefile"  # بدون extension
    r"|\.env(?:\.\w+)?|\.gitignore|\.dockerignore|\.npmrc"  # dotfiles
    r")(?:[\s`'\";.,)]|$)",
    re.IGNORECASE,
)


def _is_simple_file_op(message: str) -> bool:
    """آیا پیام کاربر یک عملیات file-level ساده است که scan لازم ندارد؟

    تشخیص ساده:
    1. پیام شامل filename صریح (با extension یا نام شناخته‌شده مثل Dockerfile)
    2. پیام شامل verb file-creation (بساز/ایجاد کن/create/make/...)
    3. پیام کوتاه‌تر از ۵۰۰۰ کاراکتر (در حالت structured prompt)
    4. **و** پیام شامل کلیدواژه‌های scope-broad نیست (auth، bug، investigate)

    مثال‌های مثبت:
    - «فایل runtime.txt بساز با محتوای python-3.11.10»
    - «create Dockerfile with these contents»
    - «بساز فایل .env.example»

    مثال‌های منفی:
    - «این صفحه باگ دارد، بررسی کن» (هیچ filename یا create verb)
    - «امکان dark-mode اضافه کن» (feature، broad scope)
    - «deploy fail شد» (vague)
    """
    if not message or len(message) > 5000:
        return False

    msg_low = message.lower()

    # کلیدواژه‌های scope-broad — اگر این‌ها هستند، simple نیست
    broad_markers = (
        "بررسی کن", "investigate", "audit", "review",
        "این صفحه", "این فایل", "این feature", "اضافه کن قابلیت",
        "amer شد", "fail شد", "نمی‌کنه", "ارور",
    )
    if any(bm in msg_low for bm in broad_markers):
        return False

    # filename صریح موجود؟
    has_filename = bool(_FILENAME_RE.search(message))
    if not has_filename:
        return False

    # verb file-creation موجود؟
    has_create_verb = any(v in message for v in _CREATE_VERBS_FA) or \
                      any(v in msg_low for v in _CREATE_VERBS_EN)
    if has_create_verb:
        return True

    # patterns add-line-to-file
    if re.search(
        r"(?:خط|line|محتوای).{0,80}(?:به|to)\s+",
        message, re.IGNORECASE,
    ):
        return True

    return False


# 🆕 (v3 chat-history) — تشخیص اینکه آیا پیام جدید ادامهٔ context قبلی
# است یا یک سؤال/درخواست مستقل. اگر continuation، خلاصه‌ای از context
# قبلی به focus_notes می‌رود تا scan با اشراف به history کار کند.
# اگر مستقل، فقط user_message استفاده می‌شود تا scan روی context بی‌ربط
# منحرف نشود.

# نشانگرهای ارجاعی صریح (کلیدواژه‌هایی که نشان می‌دهند پیام فعلی به
# چیزی در گذشته اشاره می‌کند)
_CONTINUATION_MARKERS_FA = (
    "هم", "دیگه", "اون", "اون رو", "اون یکی", "بعدی", "این یکی",
    "همچنین", "همینطور", "همون", "همانطور", "ادامه بده", "ادامه‌ش",
    "و این", "و فایل", "و اون", "بقیه", "بقیه‌ش", "بقیه‌اش",
    "قبلی", "قبل", "بالا گفت", "بالا گفتم", "گفته بودم",
)
_CONTINUATION_MARKERS_EN = (
    "also", "too", "next one", "the other", "as well", "previously",
    "earlier", "above", "continue", "rest", "remaining", "that file",
    "those files", "the same", "and the",
)


def _is_likely_continuation(user_message: str, chat_history: List[Dict[str, Any]]) -> bool:
    """heuristic: آیا پیام جدید به context قبلی ارجاع دارد؟"""
    if not chat_history or not user_message:
        return False
    msg_low = user_message.lower()
    # نشانگر ارجاعی صریح
    for m in _CONTINUATION_MARKERS_FA:
        if m in user_message:
            return True
    for m in _CONTINUATION_MARKERS_EN:
        if m in msg_low:
            return True
    # heuristic keyword overlap: اگر >=۲ کلیدواژه مشترک با ۳ پیام آخر
    # (پس از فیلتر stopwords)، احتمالاً ادامهٔ همان موضوع است
    msg_keywords = set(_extract_focus_keywords(user_message))
    if not msg_keywords:
        return False
    recent_text = " ".join(
        (m.get("content") or "")[:1500]
        for m in chat_history[-6:]  # ۶ پیام آخر (۳ user + ۳ assistant معمولاً)
        if m.get("role") in ("user", "assistant")
    )
    hist_keywords = set(_extract_focus_keywords(recent_text))
    return len(msg_keywords & hist_keywords) >= 2


# 🆕 (v3 chat-history) — regex برای فایل‌های bare (بدون /) که در پیام
# assistant ذکر می‌شوند. این نسبت به `_INLINE_PATH_RE` lenient تر است
# چون می‌خواهیم فایل‌های ساده مثل `auth.ts`, `db.py` را هم گیر بیاوریم.
# روی پیام user این lenient regex خطرناک است (false positive) ولی روی
# پیام assistant معمولاً assistant فایل واقعی را ذکر می‌کند.
_BARE_FILENAME_RE = re.compile(
    r"(?:^|[\s`\"'(\[])"
    r"([A-Za-z_][\w-]{0,40}\.(?:py|tsx?|jsx?|mjs|cjs|css|scss|json|ya?ml|sql|md))"
    r"(?=[\s`\"',.;:\)\]]|$)",
    re.IGNORECASE,
)


def _extract_paths_from_prior_assistant_msgs(chat_history: List[Dict[str, Any]]) -> List[str]:
    """فایل‌هایی که در پیام‌های assistant قبلی session ذکر شده‌اند.

    وقتی کاربر می‌گوید «اون فایل قبلی رو هم درست کن» و انکر صریحی ندارد،
    این فایل‌ها به عنوان scope ضمنی استفاده می‌شوند.

    استخراج هم برای:
    - مسیرهای کامل (مثل `frontend/src/foo.tsx`) از طریق `_INLINE_PATH_RE`
    - filename های bare (مثل `auth.ts`) از طریق `_BARE_FILENAME_RE`
    """
    if not chat_history:
        return []
    paths: List[str] = []
    seen = set()
    # ۵ پیام آخر assistant را بررسی کن
    assistant_msgs = [m for m in chat_history if m.get("role") == "assistant"][-5:]
    for m in assistant_msgs:
        content = m.get("content") or ""
        # مسیرهای کامل
        for match in _INLINE_PATH_RE.findall(content):
            p = match if not isinstance(match, tuple) else match[0]
            p = p.strip()
            if p and p not in seen:
                seen.add(p)
                paths.append(p)
        # filename های bare — فقط در صورتی که مسیر کامل match نشد یا کمتر بود
        for match in _BARE_FILENAME_RE.findall(content):
            p = match.strip() if isinstance(match, str) else (match[0] if match else "")
            if p and p not in seen:
                seen.add(p)
                paths.append(p)
    return paths[:10]


def _summarize_recent_chat(chat_history: List[Dict[str, Any]], limit: int = 3) -> str:
    """خلاصه‌ای از آخرین پیام‌های user + assistant برای focus_notes context."""
    if not chat_history:
        return ""
    # فقط user و assistant، حداکثر `limit` جفت آخر
    relevant = [m for m in chat_history if m.get("role") in ("user", "assistant")]
    if not relevant:
        return ""
    tail = relevant[-(limit * 2):]
    lines: List[str] = []
    for m in tail:
        role = m.get("role", "user")
        content = (m.get("content") or "").strip()
        if not content:
            continue
        # truncate per-message
        snippet = content[:400] + ("…" if len(content) > 400 else "")
        prefix = "👤 کاربر" if role == "user" else "🤖 مدل"
        lines.append(f"{prefix}: {snippet}")
    return "\n".join(lines)

# ─── الگوهای استخراج فایل از stack trace / متن ─────────────────────
# Python tracebacks
_PY_STACK_RE = re.compile(r'File\s+"([^"]+\.py)"', re.IGNORECASE)
# JS/TS stack traces (e.g. at ./src/foo.tsx:12:5)
_JS_STACK_RE = re.compile(
    r'(?:at\s+|in\s+|from\s+)?[\(\s]([\w./\\-]+\.(?:tsx?|jsx?|mjs|cjs))(?::\d+)?',
    re.IGNORECASE,
)
# نام فایل که کاربر صریحاً در پیام می‌آورد (مثلاً frontend/src/foo.tsx)
_INLINE_PATH_RE = re.compile(
    # شامل `./foo/bar.py` و `/foo/bar.py` و `foo/bar.py`
    r'(?:^|[\s`"\'(])((?:\./|/)?(?:[\w.-]+/){1,}[\w.-]+\.(?:py|tsx?|jsx?|mjs|cjs|css|scss|md|json|ya?ml|sql))',
    re.IGNORECASE,
)

# ─── نگاشت URL/route به فایل ────────────────────────────────────
# این نگاشت یک heuristic سادهٔ Next.js است. اگر در پروژه ساختار متفاوتی
# باشد، خروجی همچنان مفید است (مدل scan آن را تأیید/تصحیح می‌کند).
_NEXT_ROUTE_BASES = (
    "frontend/src/app",
    "frontend/app",
    "src/app",
    "app",
)


@dataclass
class ResolvedScanIntent:
    """نتیجهٔ intent resolution."""

    should_scan: bool
    reason: str = ""  # "explicit_keyword" | "stack_trace_present" | "no_trigger" | "no_anchor" | "semantic_only_vague"
    focus_notes: str = ""
    custom_paths: List[str] = field(default_factory=list)
    selected_sections: Optional[List[str]] = None
    include_dependencies: bool = True
    visual_debug: bool = False
    confidence: float = 0.0
    matched_keywords: List[str] = field(default_factory=list)
    extracted_files_from_logs: List[str] = field(default_factory=list)
    # 🆕 (v2 M1) — وقتی کاربر intent قوی دارد ولی هیچ anchor واضحی نیست،
    # scan با semantic search روی tree + محتوای dep files محدود می‌شود
    # به top 30 فایل match. مطابق درخواست کاربر: «جاهایی که به درخواست
    # من شبیه‌تر هست».
    semantic_search_only: bool = False
    semantic_keywords: List[str] = field(default_factory=list)
    # 🆕 (v3 chat-history) — آیا این پیام ادامهٔ context قبلی session است؟
    # اگر True، scan هم به context قبلی توجه دارد. اگر False، فقط درخواست
    # فعلی استفاده می‌شود تا context بی‌ربط منحرف‌کننده نباشد.
    is_continuation: bool = False


def _has_trigger_keyword(text: str) -> List[str]:
    """کلیدواژه‌های trigger پیدا شده در text را برمی‌گرداند."""
    if not text:
        return []
    text_low = text.lower()
    matched: List[str] = []
    for kw in _TRIGGER_KEYWORDS_FA:
        if kw in text:
            matched.append(kw)
    for kw in _TRIGGER_KEYWORDS_EN:
        if kw in text_low:
            matched.append(kw)
    return matched


def _extract_files_from_logs(logs: List[Dict[str, Any]], limit: int = 30) -> List[str]:
    """فایل‌های ذکر شده در stack traceهای backend/frontend logs."""
    if not logs:
        return []
    found: List[str] = []
    seen = set()
    for entry in logs[-limit:]:
        text = ""
        if isinstance(entry, dict):
            text = " ".join(
                str(entry.get(k, "")) for k in ("message", "stack", "stack_trace", "text", "msg", "body")
            )
        elif isinstance(entry, str):
            text = entry
        if not text:
            continue
        for m in _PY_STACK_RE.findall(text):
            if m not in seen:
                seen.add(m)
                found.append(m)
        for m in _JS_STACK_RE.findall(text):
            if m not in seen:
                seen.add(m)
                found.append(m)
    return found


def _extract_inline_paths(message: str) -> List[str]:
    """مسیرهای فایل که کاربر در پیام صریحاً نوشته."""
    if not message:
        return []
    matches = _INLINE_PATH_RE.findall(message)
    seen = set()
    result = []
    for m in matches:
        if m not in seen:
            seen.add(m)
            result.append(m)
    return result


def _url_to_route_candidates(url: str) -> List[str]:
    """تبدیل یک URL/route مثل `/oversight` به مسیرهای محتمل فایل.

    (audit fix I6) — segment های dynamic (عددی یا UUID مانند) به
    placeholderهای Next.js مثل `[id]` و `[slug]` نگاشت می‌شوند تا فایل‌های
    جعلی مانند `frontend/src/app/projects/123/page.tsx` در scope وارد نشوند.
    """
    if not url:
        return []
    path = url
    if "://" in path:
        try:
            from urllib.parse import urlparse
            path = urlparse(url).path
        except Exception:
            pass
    path = path.strip("/").split("?", 1)[0].split("#", 1)[0]
    if not path:
        # root → page.tsx
        candidates: List[str] = []
        for base in _NEXT_ROUTE_BASES:
            candidates.append(f"{base}/page.tsx")
            candidates.append(f"{base}/page.jsx")
        return candidates

    segments = path.split("/")

    # (audit fix I6) — segment dynamic را به `[id]` / `[slug]` تبدیل کن.
    # Heuristic: عددی صرف، UUID-shape، یا hex hash → احتمالاً id.
    _uuid_re = re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")
    _hex_re = re.compile(r"^[0-9a-fA-F]{12,}$")
    def _is_dynamic(seg: str) -> bool:
        if not seg:
            return False
        if seg.isdigit():
            return True
        if _uuid_re.match(seg):
            return True
        if _hex_re.match(seg):
            return True
        return False

    literal_segments = list(segments)
    dynamic_segments = [
        "[id]" if _is_dynamic(s) else s for s in segments
    ]

    candidates: List[str] = []
    for base in _NEXT_ROUTE_BASES:
        # هم مسیر literal و هم نسخهٔ با [id] را اضافه کن
        for segs in {tuple(literal_segments), tuple(dynamic_segments)}:
            joined = "/".join(segs)
            candidates.append(f"{base}/{joined}/page.tsx")
            candidates.append(f"{base}/{joined}/page.jsx")
            candidates.append(f"{base}/{joined}.tsx")
            candidates.append(f"{base}/{joined}.jsx")
    return candidates


def _summarize_logs(logs: List[Dict[str, Any]], limit: int = 3) -> str:
    """آخرین چند خط مهم لاگ‌ها را خلاصه می‌کند برای focus_notes."""
    if not logs:
        return ""
    lines: List[str] = []
    for entry in logs[-limit:]:
        if isinstance(entry, dict):
            text = entry.get("message") or entry.get("text") or entry.get("msg") or ""
            level = entry.get("level") or entry.get("severity") or ""
            if text:
                lines.append(f"[{level}] {str(text)[:200]}" if level else str(text)[:200])
        elif isinstance(entry, str):
            lines.append(entry[:200])
    return "\n".join(lines)


def resolve_intent_from_chat_context(
    *,
    user_message: str,
    backend_logs: Optional[List[Dict[str, Any]]] = None,
    console_logs: Optional[List[Dict[str, Any]]] = None,
    frontend_url: Optional[str] = None,
    page_url: Optional[str] = None,
    api_paths: Optional[List[str]] = None,
    linked_task: Optional[Dict[str, Any]] = None,
    screenshots: Optional[List[Dict[str, Any]]] = None,
    mode: str = "chat",  # "chat" | "visual_debug"
    chat_history: Optional[List[Dict[str, Any]]] = None,  # 🆕 [{role, content}]
) -> ResolvedScanIntent:
    """تشخیص intent + استخراج پارامترهای scan.

    این تابع pure است (هیچ I/O ندارد)، پس قابل تست واحد.
    """
    user_message = (user_message or "").strip()
    if not user_message:
        return ResolvedScanIntent(should_scan=False, reason="empty_message")

    # 🆕 (clarify-first) — اگر این پیام پاسخ کاربر به یک سوال ask_user قبلی
    # است (با تگ [user_clarification ...])، scan را trigger نکن. این یک
    # continuation است و باید مستقیم به smart-chat برود تا با context قبلی
    # تصمیم نهایی گرفته شود.
    if user_message.startswith("[user_clarification"):
        return ResolvedScanIntent(
            should_scan=False,
            reason="user_clarification_reply",
            focus_notes=user_message,
            is_continuation=True,
        )

    # 🆕 (clarify-first v3) — Infrastructure connection errors (DB, Redis,
    # external services) NEVER deserve a 12-pass scan. They almost always
    # need a targeted fix (env var, graceful degradation, retry/timeout).
    # Route directly to smart-chat which can ask user trade-off via ask_user.
    _infra_pattern = _has_infra_connection_error(backend_logs)
    if _infra_pattern:
        return ResolvedScanIntent(
            should_scan=False,
            reason=f"infra_connection_error:{_infra_pattern}",
            focus_notes=(
                f"خطای connection شناسایی شد: '{_infra_pattern}'. این یک infrastructure issue است "
                f"(env var ست نشده، سرویس بالا نیست، یا timeout). نیاز به scan کل پروژه نیست — "
                f"یک fix هدفمند کافی است. در پاسخ به کاربر باید با ask_user سه گزینه پیشنهاد دهی: "
                f"(۱) graceful degradation در کد (سرویس را optional کن)، "
                f"(۲) ست کردن env var واقعی در Render، "
                f"(۳) حذف کامل وابستگی به این سرویس اگر لازم نیست. "
                f"کاربر باید انتخاب کند، نه که حدس بزنی."
            ),
        )

    # 🆕 (clarify-first v3) — خطای قطعی کد (AttributeError، ImportError،
    # ModuleNotFoundError، SyntaxError، ...) یک محل دقیق دارد. scan کل پروژه
    # ۴۰+ proposal بی‌ربط می‌سازد. مستقیم smart-chat که فایل دقیق را می‌خواند
    # و fix هدفمند می‌سازد.
    _code_err = _has_deterministic_code_error(backend_logs, user_message)
    if _code_err:
        return ResolvedScanIntent(
            should_scan=False,
            reason=f"deterministic_code_error:{_code_err}",
            focus_notes=(
                f"خطای قطعی کد شناسایی شد: '{_code_err}'. این خطا یک محل دقیق در stack trace دارد "
                f"و یک fix هدفمند تک‌فایلی نیاز دارد — نه scan کل پروژه. "
                f"فایل ذکرشده در stack trace (و importهای مرتبط) را بخوان، علت دقیق را پیدا کن "
                f"و فقط همان را fix کن. هرگز scope را به کل پروژه گسترش نده. "
                f"اگر چند راه‌حل معقول دارد، با ask_user بپرس."
            ),
        )

    # 🆕 (clarify-first v3) — خطای build/packaging (maturin، pydantic-core،
    # Read-only filesystem، Python 3.13/3.14 wheel). راه‌حل تقریباً همیشه
    # runtime.txt است. scan کل پروژه بی‌فایده است. مستقیم smart-chat هدفمند.
    _build_err = _has_build_error(backend_logs, user_message)
    if _build_err:
        return ResolvedScanIntent(
            should_scan=False,
            reason=f"build_error:{_build_err}",
            focus_notes=(
                f"خطای build/packaging شناسایی شد: '{_build_err}'. این یک مشکل ساخت است که "
                f"معمولاً با تنظیم نسخهٔ Python در runtime.txt (مثلاً python-3.12.7) حل می‌شود — "
                f"نه scan کل پروژه. اگر log شامل maturin/Rust/Read-only filesystem یا cp313/cp314 "
                f"است، علت Python 3.13+ است و wheel ندارد؛ runtime.txt را به python-3.12.7 ست کن. "
                f"اول چک کن runtime.txt موجود است یا نه (اگر هست modify، اگر نیست create). "
                f"🔴 مهم: اگر runtime.txt و Dockerfile از قبل python-3.12.x را مشخص کرده‌اند ولی "
                f"build همچنان از python3.14 در مسیر `.venv/bin/python3.14` استفاده می‌کند، یعنی "
                f"Render یک build بومی (native pip/venv) انجام می‌دهد و Dockerfile را نادیده می‌گیرد — "
                f"در این حالت render.yaml یا تنظیم env اعمال نشده. fix: یا env var `PYTHON_VERSION=3.12.7` "
                f"را در render.yaml/Dockerfile اضافه کن، یا مطمئن شو runtime.txt دقیقاً در root directory "
                f"سرویس قرار دارد و render.yaml به‌درستی linked است. اگر مطمئن نیستی کدام راه درست است، "
                f"با ask_user گزینه‌ها را با trade-off ارائه بده. هرگز maturin/setuptools-rust به "
                f"requirements اضافه نکن. scope را به کل پروژه گسترش نده."
            ),
        )

    # 🆕 (v3 simple-op gate) — اولویت اول: اگر درخواست یک عملیات ساده
    # روی فایل مشخص است (مثل «runtime.txt بساز»)، scan ۱۲-pass overkill
    # است و نتایج بی‌ربط می‌دهد. مستقیماً به smart-chat می‌رود.
    if _is_simple_file_op(user_message):
        return ResolvedScanIntent(
            should_scan=False,
            reason="simple_file_op",
            focus_notes=user_message,
        )

    # 🆕 (v2 M1) — focus_notes را زودتر بسازیم تا در مسیر vague-fallback
    # هم در دسترس باشد. قبلاً تنها در بخش پایانی ساخته می‌شد.
    _focus_parts: List[str] = [user_message]

    # 🆕 (v3 chat-history) — اگر پیام جدید ادامهٔ context قبلی است،
    # خلاصه‌ای از ۳ پیام آخر را به focus_notes اضافه کن. در غیر این صورت
    # عمداً context قبلی را نادیده بگیر تا scan روی موضوع جدید متمرکز
    # باشد بدون آلودگی.
    _is_continuation = _is_likely_continuation(user_message, chat_history or [])
    if _is_continuation:
        _hist_summary = _summarize_recent_chat(chat_history or [], limit=3)
        if _hist_summary:
            _focus_parts.append(
                f"\n[📜 context پیشین این session (ادامهٔ همان موضوع):]\n"
                f"{_hist_summary}\n"
                f"⚠️ scan باید این context را برای فهم درخواست در نظر بگیرد، "
                f"ولی فقط روی درخواست **اخیر** کاربر متمرکز شود."
            )

    _early_log_summary = _summarize_logs(backend_logs or [], limit=3)
    if _early_log_summary:
        _focus_parts.append(f"\n[خلاصهٔ backend logs اخیر:]\n{_early_log_summary}")
    _early_console = _summarize_logs(console_logs or [], limit=3)
    if _early_console:
        _focus_parts.append(f"\n[خلاصهٔ console logs اخیر:]\n{_early_console}")
    if api_paths:
        _focus_parts.append(f"\n[endpoint های مرتبط:] {', '.join(str(p) for p in api_paths[:8])}")
    focus_notes = "\n".join(_focus_parts)

    # 1) تشخیص trigger
    matched = _has_trigger_keyword(user_message)
    has_stack_in_logs = bool(_extract_files_from_logs(backend_logs or []) or _extract_files_from_logs(console_logs or []))
    has_screenshots = bool(screenshots) or mode == "visual_debug"

    # هر یک از این سه شرط برای trigger کافی است. visual_debug + screenshot
    # هم به‌تنهایی trigger است چون کاربر صریحاً ابزار بصری را به کار برده —
    # یعنی قصد بررسی دارد.
    should_scan = bool(matched) or has_stack_in_logs or (
        mode == "visual_debug" and bool(screenshots) and len(user_message) >= 3
    )

    if not should_scan:
        return ResolvedScanIntent(
            should_scan=False,
            reason="no_trigger",
            matched_keywords=matched,
        )

    # 2) استخراج custom_paths از همهٔ منابع
    candidates: List[str] = []

    # 2a) فایل‌هایی که کاربر در پیام نوشته
    candidates.extend(_extract_inline_paths(user_message))

    # 2b) فایل‌های ذکر شده در stack traces
    files_from_be = _extract_files_from_logs(backend_logs or [])
    files_from_fe = _extract_files_from_logs(console_logs or [])
    candidates.extend(files_from_be)
    candidates.extend(files_from_fe)

    # 2c) از URL route فایل صفحه را حدس بزن
    for url in [page_url, frontend_url]:
        if url:
            candidates.extend(_url_to_route_candidates(url))

    # 2d) از linked task
    if linked_task and isinstance(linked_task, dict):
        linked_files = linked_task.get("target_files") or []
        if isinstance(linked_files, list):
            for lf in linked_files:
                if isinstance(lf, str):
                    candidates.append(lf)

    # dedup + normalize
    seen = set()
    custom_paths: List[str] = []
    for c in candidates:
        cn = c.strip().replace("\\", "/")
        if cn and cn not in seen:
            seen.add(cn)
            custom_paths.append(cn)

    # 3) selected_sections: اگر custom_paths خالی است، از URLs استنباط کن
    selected_sections: Optional[List[str]] = None
    if not custom_paths:
        secs = set()
        if backend_logs or any("/api/" in (p or "") for p in (api_paths or [])):
            secs.add("backend")
        if frontend_url or page_url or console_logs:
            secs.add("frontend")
        # 🆕 (v3 chat-history) — اگر continuation است، chat history خودش
        # یک anchor است. از scan قبلی فایل‌ها قابل استخراج هستند.
        # paths از scan_complete های قبلی برداشت کنیم.
        if not secs and _is_continuation and chat_history:
            try:
                prior_paths = _extract_paths_from_prior_assistant_msgs(chat_history)
                if prior_paths:
                    custom_paths.extend(prior_paths)
            except Exception:
                pass
        if secs:
            selected_sections = sorted(secs)
        elif custom_paths:
            # ممکن است continuation فایل‌های قبلی را برگرداند
            pass
        elif matched and any(_is_strong_keyword(k) for k in matched):
            # 🆕 (v2 M1) — کاربر کلیدواژهٔ قوی استفاده کرده ولی هیچ
            # URL/log/فایل صریحی نداده. به جای no_anchor، با semantic
            # search روی tree فایل‌های شبیه‌ترین را پیدا می‌کنیم. این
            # دقیقاً پاسخ به درخواست «در جاهایی که شبیه‌تره» است.
            _focus_combined = ((user_message or "") + " " + focus_notes).strip()
            _sem_kws = _extract_focus_keywords(_focus_combined)
            if not _sem_kws:
                # حتی keyword استخراج نشد — fallback به no_anchor
                return ResolvedScanIntent(
                    should_scan=False,
                    reason="no_anchor",
                    matched_keywords=matched,
                )
            # build focus_notes اگر هنوز ساخته نشده
            _final_focus = focus_notes if focus_notes else (user_message or "")
            return ResolvedScanIntent(
                should_scan=True,
                reason="semantic_only_vague",
                focus_notes=_final_focus,
                custom_paths=[],
                selected_sections=None,  # عمداً None — تصمیم با scan layer
                include_dependencies=True,
                visual_debug=has_screenshots,
                confidence=0.55 + (0.1 if has_screenshots else 0.0),
                matched_keywords=matched,
                extracted_files_from_logs=[],
                semantic_search_only=True,
                semantic_keywords=_sem_kws,
                is_continuation=_is_continuation,
            )
        else:
            # هیچ سرنخی برای scope وجود ندارد — should_scan را خاموش کن
            return ResolvedScanIntent(
                should_scan=False,
                reason="no_anchor",
                matched_keywords=matched,
            )

    # 4) focus_notes — قبلاً ساخته شد (v2 M1 — موقع پیش‌سازی برای vague fallback)

    # 5) reason
    reason = "explicit_keyword" if matched else "stack_trace_present"

    # 6) confidence
    conf = 0.5
    if matched:
        conf += 0.3
    if has_stack_in_logs:
        conf += 0.2
    if custom_paths:
        conf = min(1.0, conf + 0.1)

    return ResolvedScanIntent(
        should_scan=True,
        reason=reason,
        focus_notes=focus_notes,
        custom_paths=custom_paths[:30],  # cap reasonable
        selected_sections=selected_sections,
        include_dependencies=True,
        visual_debug=has_screenshots,
        confidence=conf,
        matched_keywords=matched,
        extracted_files_from_logs=files_from_be + files_from_fe,
        is_continuation=_is_continuation,
    )
