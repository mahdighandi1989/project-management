"""Verify v6 — code_content_searcher

ابزار جستجوی محتوای فایل در مخزن GitHub. به‌جای تکیه به commit diff
(که فقط آخرین تغییرات را می‌دهد)، اینجا full file content را می‌خوانیم
و targeted grep می‌زنیم.

طبق Bug C6 v2 — گپ ۲ (file content reading به‌جای commit diff).
"""
from __future__ import annotations

import base64
import logging
import re
import unicodedata
from typing import Any, Dict, List, Optional, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from .context_builder import VerifyContext

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# fetch_file_content
# ---------------------------------------------------------------------------


async def fetch_file_content(
    repo_full_name: str,
    path: str,
    ref: str = "main",
    *,
    token: str,
    cache: Dict[str, str],
    max_size_bytes: int = 500_000,
) -> Optional[str]:
    """خواندن full file content از GitHub Contents API با cache روی sha.

    - GET /repos/{owner}/{repo}/contents/{path}?ref={ref}
    - base64 decode از field content
    - cache key: f"{path}@{ref}"
    - skip اگر size > max_size_bytes یا content-type غیر متنی (binary)
    - بازگشت None در صورت 404/403/error
    """
    if not repo_full_name or "/" not in repo_full_name or not path:
        return None
    key = f"{path}@{ref}"
    if key in cache:
        return cache[key]

    try:
        import httpx
    except ImportError:
        return None

    url = f"https://api.github.com/repos/{repo_full_name}/contents/{path}"
    params = {"ref": ref} if ref else {}
    headers = {"Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"token {token}"

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(url, params=params, headers=headers)
        if r.status_code in (404, 403):
            return None
        if r.status_code != 200:
            return None
        data = r.json()
        # GitHub Contents API may return list for directories — skip
        if isinstance(data, list):
            return None
        size = int(data.get("size", 0) or 0)
        if size > max_size_bytes:
            return None
        encoding = (data.get("encoding") or "").lower()
        if encoding != "base64":
            return None
        raw_b64 = (data.get("content") or "").replace("\n", "")
        try:
            raw_bytes = base64.b64decode(raw_b64)
        except Exception:
            return None
        # تشخیص binary: اگر NUL در ابتدا بود → skip
        if b"\x00" in raw_bytes[:1024]:
            return None
        try:
            content = raw_bytes.decode("utf-8", errors="replace")
        except Exception:
            return None
        cache[key] = content
        return content
    except Exception as _e:
        logger.debug(f"fetch_file_content failed for {path}@{ref}: {_e}")
        return None


# ---------------------------------------------------------------------------
# grep_token_in_files
# ---------------------------------------------------------------------------


async def grep_token_in_files(
    token: str,
    paths: List[str],
    repo_full_name: str,
    ref: str,
    *,
    github_token: str,
    cache: Dict[Tuple[str, str], List[Dict[str, Any]]],
    file_content_cache: Dict[str, str],
    context_lines: int = 2,
    max_matches_per_file: int = 5,
) -> List[Dict[str, Any]]:
    """جستجوی case-insensitive یک token در لیست فایل‌ها.

    خروجی: [{path, line_number, snippet, before_lines, after_lines}, ...]
    cache روی key=(path, token) برای جلوگیری از grep تکراری.
    """
    if not token:
        return []
    results: List[Dict[str, Any]] = []
    pat = re.compile(re.escape(token), re.IGNORECASE)
    for path in paths:
        key = (path, token)
        if key in cache:
            results.extend(cache[key])
            continue
        content = await fetch_file_content(
            repo_full_name, path, ref, token=github_token,
            cache=file_content_cache,
        )
        if not content:
            cache[key] = []
            continue
        lines = content.split("\n")
        per_file: List[Dict[str, Any]] = []
        for m in pat.finditer(content):
            # تبدیل offset به line number
            line_no = content.count("\n", 0, m.start()) + 1
            i = line_no - 1
            before = lines[max(0, i - context_lines):i]
            snippet = lines[i] if 0 <= i < len(lines) else ""
            after = lines[i + 1:i + 1 + context_lines]
            per_file.append({
                "path": path,
                "line_number": line_no,
                "snippet": snippet[:300],
                "before_lines": before[-context_lines:],
                "after_lines": after[:context_lines],
            })
            if len(per_file) >= max_matches_per_file:
                break
        cache[key] = per_file
        results.extend(per_file)
    return results


# ---------------------------------------------------------------------------
# extract_identifiers — استخراج identifier از متن AC
# ---------------------------------------------------------------------------


# stop-words (cap ~۱۰۰) — انگلیسی + فارسی common
_STOP_WORDS_EN = {
    "the", "and", "for", "this", "that", "user", "users", "system", "change",
    "changes", "add", "added", "adding", "remove", "removed", "fix", "fixed",
    "update", "updated", "create", "created", "make", "should", "must", "will",
    "with", "without", "have", "has", "had", "from", "into", "onto", "upon",
    "after", "before", "during", "since", "until", "while", "when", "where",
    "what", "which", "who", "how", "but", "not", "yet", "also", "only", "just",
    "very", "more", "less", "most", "least", "some", "any", "all", "each",
    "every", "few", "many", "much", "such", "same", "new", "old", "good", "bad",
    "best", "worst", "first", "last", "next", "prev", "previous", "current",
    "feature", "features", "page", "pages", "screen", "screens", "button",
    "buttons", "click", "clicks", "show", "shows", "shown", "display", "displays",
    "displayed", "view", "views", "viewed", "data", "info", "field", "fields",
    "value", "values", "result", "results", "list", "lists", "item", "items",
}
_STOP_WORDS_FA = {
    "بهبود", "تغییر", "تغییرات", "سیستم", "سامانه", "پروژه", "افزودن",
    "اضافه", "حذف", "ایجاد", "ساخت", "اصلاح", "نمایش", "صفحه", "صفحات",
    "دکمه", "کلیک", "نشان", "میدان", "فیلد", "داده", "اطلاعات", "ویژگی",
    "ویژگی‌ها", "قابلیت", "قابلیت‌ها", "نتیجه", "نتایج", "لیست", "آیتم",
    "آیتم‌ها", "مورد", "موارد", "مرحله", "مراحل", "گام", "گام‌ها", "بخش",
    "بخش‌ها", "تابع", "توابع", "کلاس", "متغیر", "متغیرها", "فایل", "فایل‌ها",
    "مدل", "وقتی", "اگر", "وگرنه", "همچنین", "بعد", "قبل", "هنگام", "این",
    "آن", "که", "را", "از", "به", "در", "با", "بدون", "برای", "تا", "یا",
    "و", "نه", "هم", "می", "نمی", "است", "بود", "شد", "شده", "خواهد", "باید",
    "باشد", "هست", "نیست", "اینکه", "آنکه", "چون", "زیرا", "هر", "هیچ",
    "همه", "بعضی", "خیلی", "کم", "زیاد", "بیشتر", "کمتر", "خوب", "بد",
    "جدید", "قدیمی", "اول", "آخر", "بعدی", "قبلی",
}
_STOP_WORDS = _STOP_WORDS_EN | _STOP_WORDS_FA


def extract_identifiers(text: str) -> List[str]:
    """استخراج identifier های قابل grep از یک متن AC.

    خروجی: top-K=15 unique identifier sorted desc by specificity.

    🆕 (v2 — کاستی ۱) چهار مثال concrete:

    >>> # مثال ۱: ورودی فارسی + identifier پایتون
    >>> text = "اضافه کردن فیلد `view_preferences` به مدل WatchedProject"
    >>> extract_identifiers(text)
    ['view_preferences', 'WatchedProject']

    >>> # مثال ۲: ورودی انگلیسی + camelCase
    >>> text = "Add useViewPrefs hook for fetching preferences"
    >>> extract_identifiers(text)  # 'Add' حذف چون stop-word
    ['useViewPrefs', 'fetching', 'preferences']

    >>> # مثال ۳: ورودی mixed با file path
    >>> text = "تابع _record_title_change در oversight_service.py"
    >>> extract_identifiers(text)
    ['_record_title_change', 'oversight_service']

    >>> # مثال ۴: کلمات generic — باید filter شوند
    >>> text = "بهبود سیستم نمایش"
    >>> extract_identifiers(text)
    []
    """
    if not text:
        return []
    candidates: Dict[str, float] = {}  # identifier -> specificity score

    # 1) file_path (highest specificity)
    for m in re.finditer(r"\b([\w/.\-]+\.(?:py|tsx?|jsx?|json|yaml|md))\b", text):
        full_path = m.group(1)
        # extract basename بدون extension به‌عنوان identifier
        base = full_path.rsplit("/", 1)[-1]
        stem = base.rsplit(".", 1)[0]
        if stem and stem.lower() not in _STOP_WORDS:
            score = len(stem) * 1.0 + 4.0  # file_path bonus
            _add_candidate(candidates, stem, score)

    # 2) dunder names (very specific) — _foo_bar
    for m in re.finditer(r"\b(_[a-z][a-z0-9_]+)\b", text):
        ident = m.group(1)
        if ident.lower() in _STOP_WORDS:
            continue
        if not _has_underscore_or_long(ident):
            continue
        score = len(ident) * 1.0 + 3.0  # dunder bonus
        _add_candidate(candidates, ident, score)

    # 3) snake_case — must have _ or length>=4
    for m in re.finditer(r"\b([a-z][a-z0-9_]{2,})\b", text):
        ident = m.group(1)
        if ident.startswith("_"):
            continue  # caught by dunder
        if ident.lower() in _STOP_WORDS:
            continue
        if "_" not in ident and len(ident) < 4:
            continue
        score = len(ident) * 1.0
        if "_" in ident:
            score += 2.0  # snake_case bonus
        _add_candidate(candidates, ident, score)

    # 4) camelCase — lowercase start, contains uppercase later
    for m in re.finditer(r"\b([a-z][a-zA-Z0-9]{3,})\b", text):
        ident = m.group(1)
        if ident.lower() in _STOP_WORDS:
            continue
        if not any(c.isupper() for c in ident[1:]):
            continue
        score = len(ident) * 1.0
        _add_candidate(candidates, ident, score)

    # 5) PascalCase
    for m in re.finditer(r"\b([A-Z][a-zA-Z0-9]{3,})\b", text):
        ident = m.group(1)
        if ident.lower() in _STOP_WORDS:
            continue
        score = len(ident) * 1.0
        _add_candidate(candidates, ident, score)

    # 6) function_call hint — name(  (ضعیف، فقط اضافه‌کننده)
    for m in re.finditer(r"\b(\w+)\s*\(", text):
        ident = m.group(1)
        if not ident or len(ident) < 3:
            continue
        if ident.lower() in _STOP_WORDS:
            continue
        if ident in candidates:
            candidates[ident] += 0.5  # bump
        # نه ایجاد جدید — اگر already match نشده، احتمالاً generic است

    # sort and cap to top-K=15 unique
    sorted_idents = sorted(
        candidates.items(),
        key=lambda kv: (-kv[1], kv[0]),  # desc by score, asc by name
    )
    out: List[str] = []
    seen_lower: set = set()
    for ident, _score in sorted_idents:
        key = ident.lower()
        if key in seen_lower:
            continue
        seen_lower.add(key)
        out.append(ident)
        if len(out) >= 15:
            break
    return out


def _add_candidate(d: Dict[str, float], ident: str, score: float) -> None:
    """اضافه‌کننده‌ی identifier به dict با اعمال max score."""
    prev = d.get(ident, 0.0)
    d[ident] = max(prev, score)


def _has_underscore_or_long(ident: str) -> bool:
    """snake_case معیار: یا underscore داشته باشد یا طول ≥4 (بدون _ شروع)."""
    if "_" in ident.strip("_"):
        return True
    return len(ident.lstrip("_")) >= 4


# ---------------------------------------------------------------------------
# smart_grep_for_ac
# ---------------------------------------------------------------------------


async def smart_grep_for_ac(
    ac_text: str,
    target_files: List[str],
    repo_full_name: str,
    ref: str,
    *,
    context: "VerifyContext",
) -> Dict[str, List[Dict[str, Any]]]:
    """grep هدفمند یک AC در فایل‌های هدف.

    1) استخراج identifiers از ac_text با extract_identifiers
    2) top-K=15 (sort by specificity, از قبل تنظیم شده)
    3) برای هر identifier در همهٔ target_files
    4) خروجی: {identifier: [match, ...]}

    اگر identifier هیچ‌چیزی نبود (همه stop-words)، dict خالی → fallback به AI
    در orchestrator.
    """
    identifiers = extract_identifiers(ac_text)
    cap = context.config.max_identifiers_per_ac if context else 15
    identifiers = identifiers[:max(1, cap)]
    if not identifiers:
        return {}

    try:
        from ..github_storage import get_github_token
        github_token = get_github_token() or ""
    except Exception:
        github_token = ""

    out: Dict[str, List[Dict[str, Any]]] = {}
    for ident in identifiers:
        matches = await grep_token_in_files(
            ident,
            target_files,
            repo_full_name,
            ref,
            github_token=github_token,
            cache=context.file_grep_cache,
            file_content_cache=context.file_content_cache,
        )
        context.grep_calls_count += 1
        if matches:
            out[ident] = matches
    return out


__all__ = [
    "fetch_file_content",
    "grep_token_in_files",
    "smart_grep_for_ac",
    "extract_identifiers",
]
