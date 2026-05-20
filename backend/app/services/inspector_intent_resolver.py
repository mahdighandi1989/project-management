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
_TRIGGER_KEYWORDS_FA = (
    "بررسی کن", "اصلاح کن", "درست کن", "این باگ", "مشکل دار",
    "خطا داره", "خطا میده", "این کار نمی", "این کار نمیکن", "این کار نمیکنه",
    "این چرا", "این رو ببین", "اعمال کن", "پیاده کن", "پیاده‌سازی",
    "refactor", "بهینه", "ارتقا", "ارتقاء", "این رو درست", "رفع",
    "این رو حل", "حل کن", "این رو بهبود", "بهبود بده", "این مشکل",
    "چه مشکلی", "چی مشکلی", "این صفحه چه", "این صفحه چی",
    "ایراد داره", "ایراد دار", "بهینه کن", "بازنویسی کن",
)
_TRIGGER_KEYWORDS_EN = (
    "fix", "bug", "broken", "not working", "doesn't work", "doesnt work",
    "investigate", "refactor", "improve", "apply", "implement",
    "solve", "diagnose", "debug this", "this issue", "why does",
)

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
    r'(?:^|[\s`"\'(])((?:[\w-]+/){1,}[\w.-]+\.(?:py|tsx?|jsx?|mjs|cjs|css|scss|md|json|ya?ml|sql))',
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
    reason: str = ""  # "explicit_keyword" | "stack_trace_present" | "no_trigger" | "no_anchor"
    focus_notes: str = ""
    custom_paths: List[str] = field(default_factory=list)
    selected_sections: Optional[List[str]] = None
    include_dependencies: bool = True
    visual_debug: bool = False
    confidence: float = 0.0
    matched_keywords: List[str] = field(default_factory=list)
    extracted_files_from_logs: List[str] = field(default_factory=list)


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
    """تبدیل یک URL/route مثل `/oversight` به مسیرهای محتمل فایل."""
    if not url:
        return []
    # path قسمت از URL
    path = url
    if "://" in path:
        try:
            from urllib.parse import urlparse
            path = urlparse(url).path
        except Exception:
            pass
    path = path.strip("/")
    if not path:
        path = "page"  # root → page.tsx

    # روت‌های Next.js معمولاً به page.tsx ختم می‌شوند
    candidates: List[str] = []
    for base in _NEXT_ROUTE_BASES:
        candidates.append(f"{base}/{path}/page.tsx")
        candidates.append(f"{base}/{path}/page.jsx")
        candidates.append(f"{base}/{path}.tsx")
        candidates.append(f"{base}/{path}.jsx")
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
) -> ResolvedScanIntent:
    """تشخیص intent + استخراج پارامترهای scan.

    این تابع pure است (هیچ I/O ندارد)، پس قابل تست واحد.
    """
    user_message = (user_message or "").strip()
    if not user_message:
        return ResolvedScanIntent(should_scan=False, reason="empty_message")

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
        if secs:
            selected_sections = sorted(secs)
        else:
            # هیچ سرنخی برای scope وجود ندارد — should_scan را خاموش کن
            return ResolvedScanIntent(
                should_scan=False,
                reason="no_anchor",
                matched_keywords=matched,
            )

    # 4) focus_notes: پیام + خلاصهٔ logs
    parts: List[str] = [user_message]
    log_summary = _summarize_logs(backend_logs or [], limit=3)
    if log_summary:
        parts.append(f"\n[خلاصهٔ backend logs اخیر:]\n{log_summary}")
    console_summary = _summarize_logs(console_logs or [], limit=3)
    if console_summary:
        parts.append(f"\n[خلاصهٔ console logs اخیر:]\n{console_summary}")
    if api_paths:
        parts.append(f"\n[endpoint های مرتبط:] {', '.join(str(p) for p in api_paths[:8])}")
    focus_notes = "\n".join(parts)

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
    )
