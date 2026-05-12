"""Stage 3a — Static probe (grep-based).

این probe همان منطق verify فعلی را به ساختار جدید probe تبدیل می‌کند:
برای یک AC با method=static، یا grep_patterns از verify_plan را در
فایل‌های repo می‌گردد، یا (اگر patterns نیست) keyword هایی از text
استخراج و در repo می‌گردد.

این probe **synchronous** است (هیچ I/O شبکه ندارد، فقط فایل‌خوانی local).
"""

from __future__ import annotations

import logging
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from .base import (
    PROBE_STATUS_FAILED,
    PROBE_STATUS_PASSED,
    PROBE_STATUS_SKIPPED,
    PROBE_STATUS_ERROR,
    ProbeContext,
    RuntimeProbeResult,
)

logger = logging.getLogger(__name__)

# فقط فایل‌های متنی را grep می‌کنیم
_TEXT_EXTENSIONS = frozenset({
    ".py", ".js", ".ts", ".tsx", ".jsx", ".json", ".yaml", ".yml",
    ".html", ".css", ".scss", ".md", ".txt", ".sql", ".sh", ".env",
    ".toml", ".ini", ".cfg", ".xml", ".vue", ".svelte", ".go", ".rs",
    ".java", ".kt", ".swift", ".rb", ".php", ".dart", ".lua", ".pl",
    ".c", ".cpp", ".h", ".hpp", ".cs",
})

# مسیرهایی که هیچ‌وقت grep نمی‌کنیم
_EXCLUDED_DIRS = frozenset({
    "node_modules", ".git", ".next", "dist", "build", "__pycache__",
    ".venv", "venv", ".pytest_cache", ".mypy_cache", "coverage",
    ".cache", ".turbo",
})

# حداکثر فایل‌هایی که grep می‌کنیم (محدودیت زمان)
_MAX_FILES_TO_SCAN = 500
_MAX_BYTES_PER_FILE = 200_000


def _build_patterns(ac: Dict[str, Any]) -> List[str]:
    """patterns برای grep را از AC استخراج کن.

    اولویت:
    1. verify_plan.grep_patterns (اگر داده شده)
    2. keywords از ac.text (CamelCase, snake_case, کلمات فارسی >= 3 حرف)
    """
    plan = ac.get("verify_plan") or {}
    patterns = plan.get("grep_patterns") or []
    if patterns and isinstance(patterns, list):
        return [str(p).strip() for p in patterns if str(p).strip()]
    # auto-derive از متن
    text = str(ac.get("text") or "")
    if not text:
        return []
    auto: List[str] = []
    # CamelCase / PascalCase
    for m in re.findall(r"\b[A-Z][a-zA-Z0-9]{3,}\b", text):
        auto.append(m)
    # snake_case
    for m in re.findall(r"\b[a-z][a-z0-9_]{4,}\b", text):
        auto.append(m)
    # کلمات فارسی >= 4 حرف
    for m in re.findall(r"[؀-ۿ]{4,}", text):
        auto.append(m)
    # dedup با حفظ ترتیب، حداکثر ۸
    seen = set()
    out: List[str] = []
    for p in auto:
        if p not in seen:
            seen.add(p)
            out.append(p)
            if len(out) >= 8:
                break
    return out


def _walk_repo_files(repo_root: Path, files_hint: Optional[List[str]] = None) -> List[Path]:
    """لیست فایل‌های متنی repo را برمی‌گرداند، با اولویت files_hint.

    اگر files_hint داده شده، اول این فایل‌ها بررسی می‌شوند سپس بقیه.
    """
    hinted: List[Path] = []
    if files_hint:
        for hint in files_hint:
            p = (repo_root / hint).resolve()
            try:
                if p.is_file() and repo_root in p.parents:
                    hinted.append(p)
            except Exception:
                continue
    seen = set(hinted)
    others: List[Path] = []
    for root, dirs, files in _safe_walk(repo_root):
        dirs[:] = [d for d in dirs if d not in _EXCLUDED_DIRS and not d.startswith(".")]
        for name in files:
            if not any(name.endswith(ext) for ext in _TEXT_EXTENSIONS):
                continue
            p = Path(root) / name
            if p in seen:
                continue
            others.append(p)
            if len(hinted) + len(others) >= _MAX_FILES_TO_SCAN:
                break
        if len(hinted) + len(others) >= _MAX_FILES_TO_SCAN:
            break
    return hinted + others


def _safe_walk(root: Path):
    import os
    return os.walk(str(root), topdown=True)


def _grep_one_file(path: Path, patterns: List[str]) -> Dict[str, int]:
    """تعداد hit هر pattern را در یک فایل برمی‌گرداند. cap به MAX_BYTES."""
    try:
        text = path.read_text(encoding="utf-8", errors="replace")[:_MAX_BYTES_PER_FILE]
    except Exception:
        return {}
    low = text.lower()
    hits: Dict[str, int] = {}
    for p in patterns:
        c = low.count(p.lower())
        if c:
            hits[p] = c
    return hits


def run_static_probe(
    ac: Dict[str, Any],
    ctx: ProbeContext,
    ac_id: str,
) -> RuntimeProbeResult:
    """probe static را برای یک AC اجرا می‌کند.

    منطق:
    1. patterns را بساز
    2. اگر هیچ pattern نبود → skipped
    3. اگر repo_path نبود → skipped
    4. فایل‌های repo را walk کن، grep بزن
    5. اگر مجموعاً ≥2 hit در ≥1 فایل → passed
       اگر فقط 1 hit در 1 فایل → passed (ضعیف)
       اگر 0 hit → failed
    """
    start = time.monotonic()
    ac_text = str(ac.get("text") or "")
    patterns = _build_patterns(ac)
    if not patterns:
        return RuntimeProbeResult(
            ac_id=ac_id,
            ac_text=ac_text,
            method="static",
            status=PROBE_STATUS_SKIPPED,
            evidence={"reason": "هیچ pattern یا keyword قابل استخراج نبود"},
            duration_ms=int((time.monotonic() - start) * 1000),
        )

    if not ctx.repo_path:
        return RuntimeProbeResult(
            ac_id=ac_id,
            ac_text=ac_text,
            method="static",
            status=PROBE_STATUS_SKIPPED,
            evidence={"reason": "repo_path تنظیم نشده", "patterns_tried": patterns},
            duration_ms=int((time.monotonic() - start) * 1000),
        )

    repo_root = Path(ctx.repo_path).resolve()
    if not repo_root.is_dir():
        return RuntimeProbeResult(
            ac_id=ac_id,
            ac_text=ac_text,
            method="static",
            status=PROBE_STATUS_ERROR,
            evidence={"reason": "repo_path موجود نیست", "path": str(repo_root)},
            duration_ms=int((time.monotonic() - start) * 1000),
            error_message=f"repo_path not found: {repo_root}",
        )

    plan = ac.get("verify_plan") or {}
    files_hint = plan.get("files_hint") or []
    try:
        files = _walk_repo_files(repo_root, files_hint)
    except Exception as e:
        return RuntimeProbeResult(
            ac_id=ac_id,
            ac_text=ac_text,
            method="static",
            status=PROBE_STATUS_ERROR,
            evidence={"reason": f"walk failed: {e}"},
            duration_ms=int((time.monotonic() - start) * 1000),
            error_message=str(e),
        )

    hits_per_file: Dict[str, Dict[str, int]] = {}
    total_hits = 0
    files_with_hits = 0
    for f in files:
        h = _grep_one_file(f, patterns)
        if h:
            rel = str(f.relative_to(repo_root))
            hits_per_file[rel] = h
            files_with_hits += 1
            total_hits += sum(h.values())

    duration_ms = int((time.monotonic() - start) * 1000)

    if total_hits == 0:
        return RuntimeProbeResult(
            ac_id=ac_id,
            ac_text=ac_text,
            method="static",
            status=PROBE_STATUS_FAILED,
            evidence={
                "patterns": patterns,
                "files_scanned": len(files),
                "files_with_hits": 0,
                "total_hits": 0,
            },
            duration_ms=duration_ms,
        )

    # passed اگر hit واقعی پیدا شد
    return RuntimeProbeResult(
        ac_id=ac_id,
        ac_text=ac_text,
        method="static",
        status=PROBE_STATUS_PASSED,
        evidence={
            "patterns": patterns,
            "files_scanned": len(files),
            "files_with_hits": files_with_hits,
            "total_hits": total_hits,
            "top_hits": dict(sorted(
                ((p, sum(c.get(p, 0) for c in hits_per_file.values())) for p in patterns),
                key=lambda x: -x[1],
            )[:5]),
            "sample_files": list(hits_per_file.keys())[:5],
        },
        duration_ms=duration_ms,
    )
