"""
Oversight Verifier
==================
موتور verification مستقل از execution.

این موتور **نمی‌داند** کار از چه طریق انجام شده — فقط وضعیت فعلی پروژه را
با acceptance criteria تسک مقایسه می‌کند و یک Report می‌سازد.

اگر done در چند verify متوالی تأیید شد (`confirmation_streak`)، به‌صورت نهایی done.
"""

from __future__ import annotations

import time
import uuid
import logging
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

import aiohttp

from .oversight_service import (
    GITHUB_API,
    STORAGE_DIR,
    get_oversight_service,
    OversightTask,
    OversightReport,
    WatchedProject,
    now_iso,
    get_github_token,
)

logger = logging.getLogger(__name__)

VERIFICATION_DONE = "done"
VERIFICATION_PARTIAL = "partial"
VERIFICATION_NOT_DONE = "not_done"
VERIFICATION_REGRESSED = "regressed"
VERIFICATION_ERROR = "error"


# ===========================================================================
# 🔬 Bug C6 — Verify v6 — module-level _classify_step_for_probe با ۱۰ قاعده
# ===========================================================================
# طبق پرامپت C6 (AC #5): تابع باید identifier های زیر را در ۱۰ قاعدهٔ explicit
# پوشش دهد: "backend", "frontend", "fullstack", "infra", "test_only",
# "doc_only", "manual_only". این نسخهٔ ماژول‌سطح در کنار نسخهٔ nested
# (که فقط ui_eligible|backend_only برمی‌گرداند) قرار می‌گیرد.

_C6_CLASSIFY_RULES = (
    # rule 1 — test_only: scope صریحاً test یا pytest است (priority بالا)
    ("test_only", ("pytest", "unittest", "tests/", "test_", "_test.py", "test suite")),
    # rule 2 — doc_only: مستندسازی، README، docs/
    ("doc_only", ("readme", "docs/", "documentation", "docstring", "comment-only", "markdown")),
    # rule 3 — manual_only: نیاز به بازبینی دستی، vision-only، subjective
    ("manual_only", ("manual review", "visual inspection", "subjective", "look and feel", "design only", "manual_only")),
    # rule 4 — infra: deployment, CI, docker, env, config
    ("infra", ("docker", "kubernetes", "ci/cd", ".env", "deployment", "infrastructure", "render.yaml", "github action", "workflow")),
    # rule 5 — frontend: tsx/jsx، UI element، React/Next
    ("frontend", ("tsx", "jsx", "react", "next.js", "page.tsx", "component", "frontend/", "ui element", "modal", "panel", "<button>", "<form>", "<input>")),
    # rule 6 — backend: Python, FastAPI, endpoint, model
    ("backend", ("@router", "fastapi", "pydantic", "sqlalchemy", "dataclass", "schema migration", "ast parse", "subprocess", "asyncio", "background task", "endpoint", "service.py", "verifier.py")),
    # rule 7 — fullstack: هم UI و هم backend keyword
    ("fullstack", ("end-to-end", "fullstack", "full-stack", "ui + api", "ui+api")),
    # ۳ قاعدهٔ implicit بر اساس scoring (rules 8, 9, 10 پایین در _classify_step_for_probe):
    # rule 8 — fullstack: اگر هم UI و هم backend hit داشت
    # rule 9 — frontend (default برای frontend-only)
    # rule 10 — backend (default برای backend-only)
)


def _classify_step_for_probe(step: Any) -> str:
    """طبقه‌بندی یک step/AC به یکی از ۷ category (که در ۱۰ قاعده اعمال می‌شود).

    خروجی یکی از: "backend", "frontend", "fullstack", "infra", "test_only",
    "doc_only", "manual_only".

    ۱۰ قاعدهٔ صریح — اولین match wins:
    1. test_only (explicit test keywords)
    2. doc_only (documentation only)
    3. manual_only (subjective/visual review)
    4. infra (deployment/CI/config)
    5. frontend (UI/tsx/React)
    6. backend (Python/FastAPI/endpoint)
    7. fullstack (explicit fullstack marker)
    8. fullstack (implicit: هم UI و هم backend hit)
    9. frontend (frontend-only fallback)
    10. backend (backend-only fallback / default)

    classification result در context.trace هنگام verify v6 log می‌شود.
    """
    if isinstance(step, dict):
        text = " ".join([
            str(step.get("text", "")),
            str(step.get("title", "")),
            str(step.get("scope", "")),
            str(step.get("description", "")),
        ]).lower()
    else:
        text = str(step or "").lower()
    if not text.strip():
        return "manual_only"

    # rules 1-7 — explicit keyword match (priority order)
    for category, keywords in _C6_CLASSIFY_RULES:
        if any(kw in text for kw in keywords):
            return category

    # rules 8-10 — implicit scoring fallback
    # شمارش UI/backend keyword ها
    _ui_kw = ("button", "click", "screen", "page", "panel", "modal", "input", "view", "render", "props", "state hook")
    _be_kw = ("endpoint", "api/", "service", "function", "class ", "dataclass", "database", "model", "/api/")
    _ui_hits = sum(1 for k in _ui_kw if k in text)
    _be_hits = sum(1 for k in _be_kw if k in text)
    if _ui_hits >= 2 and _be_hits >= 2:
        return "fullstack"
    if _ui_hits > _be_hits:
        return "frontend"
    return "backend"


def _gh_headers(token: str) -> Dict[str, str]:
    return {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "ai-creator-verifier/1.0",
        **({"Authorization": f"Bearer {token}"} if token else {}),
    }


async def _fetch_file(
    session: aiohttp.ClientSession,
    repo: str,
    path: str,
    headers: Dict[str, str],
    branch: Optional[str] = None,
    max_bytes: int = 500_000,  # 🔴 (extraction-100pct-fix) 40KB→500KB — verifier نیاز به محتوای کامل فایل داره
) -> Optional[str]:
    import base64

    url = f"{GITHUB_API}/repos/{repo}/contents/{path}"
    if branch:
        url += f"?ref={branch}"
    try:
        async with session.get(url, headers=headers, timeout=30) as r:
            if r.status != 200:
                return None
            data = await r.json()
        if not isinstance(data, dict) or data.get("type") != "file" or not data.get("content"):
            return None
        try:
            decoded = base64.b64decode(data["content"]).decode("utf-8", errors="ignore")
        except Exception:
            return None
        if len(decoded) > max_bytes:
            # 🔴 (extraction-100pct-fix v3) — از helper مشترک استفاده می‌کنیم
            # تا فرمت truncation در همهٔ سایت‌ها یکسان باشه.
            from .oversight_extraction import _truncation_marker
            _orig = len(decoded)
            logger.warning(
                f"[verifier _fetch_file] فایل {_orig:,} byte بود، فقط "
                f"{max_bytes:,} byte اول fetch شد. {_orig - max_bytes:,} "
                f"byte از دست رفت — verification ممکنه بر اساس محتوای ناقص باشه."
            )
            decoded = decoded[:max_bytes] + _truncation_marker(
                _orig, max_bytes, what=f"file fetch by verifier"
            )
        return decoded
    except Exception:
        return None


async def _fetch_target_files(
    repo: str, paths: List[str], branch: Optional[str], token: str
) -> Dict[str, Optional[str]]:
    if not paths:
        return {}
    out: Dict[str, Optional[str]] = {}
    headers = _gh_headers(token)
    async with aiohttp.ClientSession() as session:
        for p in paths[:20]:  # حداکثر ۲۰ فایل
            content = await _fetch_file(session, repo, p, headers, branch)
            out[p] = content
    return out


async def _fetch_repo_tree(
    repo: str, branch: Optional[str], token: str, max_paths: int = 400
) -> List[str]:
    """لیست مسیرهای فایل‌های پروژه از git tree (recursive).

    خروجی فقط شامل code/config files است (نه binaries، نه vendored deps).
    استفاده برای fuzzy matching: اگر AI در پرامپت اسم فایل خاصی ذکر کرده
    ولی آن فایل وجود ندارد، verifier می‌تواند با کمک این لیست فایل‌های
    هم‌ارز با نقش مشابه را پیشنهاد دهد.
    """
    headers = _gh_headers(token)
    url = f"{GITHUB_API}/repos/{repo}/git/trees/{branch or 'main'}?recursive=1"
    skip_prefixes = (
        "node_modules/", "venv/", ".venv/", "vendor/", "dist/", "build/",
        ".next/", ".git/", "__pycache__/", ".pytest_cache/", ".mypy_cache/",
        "coverage/", ".idea/", ".vscode/",
    )
    skip_suffixes = (
        ".pyc", ".pyo", ".so", ".dll", ".exe", ".bin", ".lock",
        ".png", ".jpg", ".jpeg", ".gif", ".ico", ".svg", ".pdf",
        ".woff", ".woff2", ".ttf", ".eot", ".mp4", ".mp3",
    )
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, timeout=30) as r:
                if r.status != 200:
                    return []
                data = await r.json()
        tree = data.get("tree") or []
        paths: List[str] = []
        for item in tree:
            if item.get("type") != "blob":
                continue
            p = item.get("path") or ""
            if not p:
                continue
            if any(p.startswith(pre) for pre in skip_prefixes):
                continue
            if any(p.endswith(suf) for suf in skip_suffixes):
                continue
            paths.append(p)
            if len(paths) >= max_paths:
                break
        return paths
    except Exception:
        return []


def _ac_text_of(ac: Any) -> str:
    """🔬 (Runtime Verify Stage 1) — متن AC را برمی‌گرداند، خواه str قدیمی،
    خواه dict جدید با فیلد text."""
    if isinstance(ac, dict):
        return str(ac.get("text") or "").strip()
    return str(ac).strip() if ac is not None else ""


def _jaccard_word_similarity(a: str, b: str) -> float:
    """🆕 (Verify v7 §D) شباهت Jaccard بر اساس مجموعهٔ کلمات.

    خروجی 0.0..1.0. اگر هر دو خالی → 0.0.
    """
    if not a or not b:
        return 0.0
    set_a = set(w for w in a.lower().split() if len(w) >= 3)
    set_b = set(w for w in b.lower().split() if len(w) >= 3)
    if not set_a or not set_b:
        return 0.0
    inter = set_a & set_b
    union = set_a | set_b
    return len(inter) / len(union)


def _resolve_done_remaining_contradictions_v7(
    done_parts: List[Any],
    remaining_parts: List[Any],
    *,
    step_code_verdicts: Optional[Dict[int, Dict[str, Any]]] = None,
    task_steps_list: Optional[List[Dict[str, Any]]] = None,
    task: Any = None,
) -> List[Any]:
    """🆕 (Verify v7 §D) رفع تناقض done ↔ remaining در خروجی AI verifier.

    هر آیتمی که هم در done_parts و هم (مشابهاً) در remaining_parts هست،
    یک تناقض است. سیاست:
      - اگر code-aware برای step مرتبط verdict=implemented داده → آیتم
        از remaining حذف می‌شود (done برنده می‌شود)
      - اگر probe نامتناسب با task_type باعث false-positive شده →
        آیتم از remaining حذف می‌شود
      - در غیر این صورت در remaining می‌ماند

    مقدار آستانهٔ تشخیص تناقض: Jaccard ≥ 0.5 یا substring بزرگ.
    تمام تصمیم‌ها در logger ثبت می‌شوند.
    """
    if not remaining_parts:
        return list(remaining_parts)

    # مجموعهٔ متن done_parts (lower-case، فقط str)
    done_texts: List[str] = []
    for d in (done_parts or []):
        if isinstance(d, dict):
            t = str(d.get("text") or d.get("ac") or "")
        else:
            t = str(d or "")
        if t.strip():
            done_texts.append(t.strip().lower())

    # اگر step_code_verdicts وجود دارد و verdict implemented است،
    # تسک‌های مرتبط را به‌عنوان قطعاً done در نظر می‌گیریم
    code_aware_implemented_texts: List[str] = []
    if step_code_verdicts and task_steps_list:
        for s in task_steps_list:
            sid = s.get("id")
            try:
                sid_int = int(sid) if sid is not None else None
            except Exception:
                sid_int = None
            if sid_int is not None:
                cav = step_code_verdicts.get(sid_int)
                if cav and cav.get("verdict") == "implemented":
                    title = (s.get("title") or s.get("scope") or "").strip()
                    if title:
                        code_aware_implemented_texts.append(title.lower())

    # 🆕 (audit pass) — early-return فقط وقتی *هیچ* سیگنالی برای merge
    # نداریم (نه done_parts متنی، نه code-aware implemented). قبلاً
    # `if not done_texts: return ...` بود که باعث می‌شد code-aware
    # path هرگز اجرا نشود اگر done_parts خالی بود — حتی وقتی
    # step_code_verdicts صریحاً implemented برمی‌گرداند. این bug latent
    # از روز اول test_resolver_code_aware_implemented_wins را fail
    # می‌کرد ولی دیده نشده بود.
    if not done_texts and not code_aware_implemented_texts:
        return list(remaining_parts)

    cleaned_remaining: List[Any] = []
    removed_log: List[str] = []
    for r in remaining_parts:
        if isinstance(r, dict):
            r_text = str(r.get("text") or r.get("ac") or "")
        else:
            r_text = str(r or "")
        r_lower = r_text.strip().lower()
        if not r_lower:
            cleaned_remaining.append(r)
            continue

        # 1) چک تناقض با done_parts
        # 🆕 (Verify v8 Tighten) — Jaccard threshold از 0.5 → 0.7 بالاتر برده
        # شد. 0.5 خیلی liberal بود و آیتم‌های متفاوت ولی هم‌کلمه را اشتباهاً
        # ادغام می‌کرد (مثلاً "endpoint /chat-cloud-code اضافه نشده" را با
        # "endpoint /chat اضافه شده" یکی می‌گرفت). 0.7 نیاز به overlap
        # واقعی دارد.
        is_in_done = False
        for d_lower in done_texts:
            # substring بزرگ (≥40 char — قبلاً 30 بود)
            if len(r_lower) >= 40 and r_lower in d_lower:
                is_in_done = True
                break
            if len(d_lower) >= 40 and d_lower in r_lower:
                is_in_done = True
                break
            # Jaccard ≥ 0.7 (قبلاً 0.5 بود)
            sim = _jaccard_word_similarity(r_lower, d_lower)
            if sim >= 0.7:
                is_in_done = True
                break
        if is_in_done:
            removed_log.append(f"contradict_done: {r_text[:80]}")
            continue

        # 2) چک code-aware: implemented (همان threshold tighten)
        is_implemented = False
        for impl_lower in code_aware_implemented_texts:
            if len(impl_lower) >= 30 and impl_lower in r_lower:
                is_implemented = True
                break
            sim = _jaccard_word_similarity(r_lower, impl_lower)
            if sim >= 0.7:
                is_implemented = True
                break
        if is_implemented:
            removed_log.append(f"code_aware_implemented: {r_text[:80]}")
            continue

        cleaned_remaining.append(r)

    if removed_log:
        try:
            logger.info(
                f"v7 contradiction resolver: removed {len(removed_log)} item(s) "
                f"from remaining_parts due to done/code-aware match: "
                f"{'; '.join(removed_log[:5])}"
            )
        except Exception:
            pass
    return cleaned_remaining


def _evaluate_acs_against_files(
    acceptance_criteria: List[Any],
    file_contents: Dict[str, Optional[str]],
    repo_tree: List[str],
) -> List[Dict[str, Any]]:
    """شواهد ماشینی per-AC: برای هر AC، تعداد hit کلمات کلیدی در هر فایل.
    این یک baseline deterministic به AI verifier می‌دهد — AI نمی‌تواند ادعا
    کند فایل وجود ندارد یا قابلیت پیاده نشده، اگر hit‌ها واقعی هستند.

    🔬 (Runtime Verify Stage 1) — AC می‌تواند str یا dict باشد. متن از
    `_ac_text_of` استخراج می‌شود.

    خروجی per AC:
    {
      "ac": str,                              # متن AC (truncated)
      "keywords": [str],                      # کلمات کلیدی استخراجی
      "hits_in_files": {file: hit_count},     # فایل‌هایی که hit دارند
      "hits_in_tree": [str],                  # فایل‌هایی در tree با اسم مرتبط
      "likely_done": bool,                    # heuristic: hit_count >= 2
      "verdict_hint": str,                    # راهنما برای AI
    }
    """
    out: List[Dict[str, Any]] = []
    for ac in acceptance_criteria:
        ac_text = _ac_text_of(ac)
        ac_keywords = _build_keywords_from_acs([ac_text])
        hits_in_files: Dict[str, int] = {}
        matched_keywords_per_file: Dict[str, List[str]] = {}
        # شمارش hit در محتوای فایل‌ها
        for file_path, content in file_contents.items():
            if not content:
                continue
            content_lower = content.lower()
            file_hit_count = 0
            file_matched: List[str] = []
            for kw in ac_keywords:
                kw_lower = kw.lower()
                if kw_lower in content_lower:
                    file_hit_count += content_lower.count(kw_lower)
                    file_matched.append(kw)
            if file_hit_count > 0:
                hits_in_files[file_path] = file_hit_count
                matched_keywords_per_file[file_path] = file_matched[:5]
        # جستجوی نام فایل‌های مرتبط در tree
        hits_in_tree: List[str] = []
        for kw in ac_keywords[:8]:
            kw_lower = kw.lower()
            for tree_path in repo_tree:
                tp_lower = tree_path.lower()
                if kw_lower in tp_lower and tree_path not in hits_in_tree:
                    hits_in_tree.append(tree_path)
                    if len(hits_in_tree) >= 8:
                        break
            if len(hits_in_tree) >= 8:
                break

        total_hits = sum(hits_in_files.values())
        likely_done = total_hits >= 2 or len(hits_in_files) >= 2 or len(hits_in_tree) >= 2

        verdict_hint = ""
        if likely_done:
            top_files = sorted(hits_in_files.items(), key=lambda x: -x[1])[:3]
            top_str = ", ".join(f"{f}({n})" for f, n in top_files)
            verdict_hint = (
                f"احتمالاً DONE — {total_hits} hit در {len(hits_in_files)} فایل ({top_str}). "
                f"chunks در ادامه را بررسی کن — اگر کد مرتبط دیدی، done بنویس."
            )
        elif hits_in_tree:
            verdict_hint = (
                f"احتمال DONE — اسم {len(hits_in_tree)} فایل با کلمات AC match دارد ({', '.join(hits_in_tree[:3])}). "
                f"اگر content این فایل‌ها در chunks موجود است، بررسی کن."
            )
        else:
            verdict_hint = (
                f"احتمال NOT_DONE — هیچ فایلی hit نداشت و هیچ نام فایلی match نکرد. "
                f"کلمات کلیدی AC: {', '.join(ac_keywords[:8])}"
            )

        out.append({
            "ac": ac_text[:2000],  # 🔴 (extraction-100pct-fix) 200→2000 — AC کامل لازمه برای verifier
            "keywords": ac_keywords[:20],  # 8→20 — کلمات کلیدی بیشتر برای match
            "hits_in_files": hits_in_files,
            "matched_keywords_per_file": matched_keywords_per_file,
            "hits_in_tree": hits_in_tree,
            "likely_done": likely_done,
            "verdict_hint": verdict_hint,
        })
    return out


def _format_machine_evidence_for_prompt(machine_evidence: List[Dict[str, Any]]) -> str:
    """قالب‌بندی شواهد ماشینی برای تزریق به verify_prompt."""
    if not machine_evidence:
        return ""
    lines = ["## 🤖 شواهد ماشینی per-AC (deterministic — این را اول بخوان)\n"]
    lines.append(
        "این تحلیل توسط کد ما (نه AI) انجام شده — کلمات کلیدی هر AC را در محتوای فایل‌ها\n"
        "و در ساختار repo جستجو کرده‌ایم. **اگر hit وجود دارد، پیش‌فرض done است**.\n"
        "تو فقط با شواهد قطعی کد می‌توانی not_done بگویی.\n"
    )
    for i, m in enumerate(machine_evidence, 1):
        lines.append(f"\n### AC {i}: {m['ac'][:150]}")
        lines.append(f"- کلمات کلیدی AC: `{', '.join(m['keywords'])}`")
        if m["hits_in_files"]:
            top = sorted(m["hits_in_files"].items(), key=lambda x: -x[1])[:5]
            lines.append("- 📊 hit در فایل‌ها:")
            for f, n in top:
                kws = m["matched_keywords_per_file"].get(f, [])
                lines.append(f"  - `{f}` → **{n} hit** (کلمات: {', '.join(kws)})")
        else:
            lines.append("- 📊 hit در فایل‌ها: هیچ")
        if m["hits_in_tree"]:
            lines.append(f"- 📁 فایل‌های با نام match: `{', '.join(m['hits_in_tree'][:5])}`")
        lines.append(f"- 🤖 hint: **{m['verdict_hint']}**")
    return "\n".join(lines)


def _extract_relevant_chunks(
    content: str,
    keywords: List[str],
    lines_around: int = 60,
    max_chunks: int = 8,
    max_total_chars: int = 60000,  # 🔴 (extraction-100pct-fix) 12KB→60KB — verifier باید بخش‌های بیشتری از فایل رو ببینه
) -> str:
    """برای فایل‌های بزرگ (مثل page.tsx 4000+ خط)، فقط chunk‌های مرتبط
    با keywords را extract می‌کند به‌جای فقط N کاراکتر اول.

    رویکرد:
    1. فایل را به خط تقسیم کن
    2. خطوطی که حداقل یک keyword (case-insensitive) دارند → "hit lines"
    3. حول هر hit line، lines_around خط بالا/پایین بگیر (chunk)
    4. chunk‌های مجاور را merge کن
    5. حداکثر max_chunks chunk با مهم‌ترین hits برگردان
    """
    if not content or not keywords:
        return content[:max_total_chars] if content else ""

    lines = content.split("\n")
    if len(lines) < 200:
        # فایل کوچک — کل content برگردان
        return content[:max_total_chars]

    keywords_lower = [k.lower() for k in keywords if k and len(k) >= 3]
    if not keywords_lower:
        return content[:max_total_chars]

    # خطوط hit
    hit_lines: List[int] = []
    for i, line in enumerate(lines):
        line_lower = line.lower()
        if any(kw in line_lower for kw in keywords_lower):
            hit_lines.append(i)

    if not hit_lines:
        # هیچ hit ی پیدا نشد — اول و وسط فایل را برگردان
        first_part = "\n".join(lines[:200])
        middle_start = max(0, len(lines) // 2 - 100)
        middle_part = "\n".join(lines[middle_start:middle_start + 200])
        out = f"{first_part}\n\n... [skipped {len(lines) - 400} lines] ...\n\n{middle_part}"
        return out[:max_total_chars]

    # ساخت ranges (start, end) و merge کردن مجاورها
    ranges: List[List[int]] = []
    for h in hit_lines:
        s = max(0, h - lines_around)
        e = min(len(lines), h + lines_around)
        if ranges and s <= ranges[-1][1] + 5:
            # merge با range قبلی
            ranges[-1][1] = max(ranges[-1][1], e)
        else:
            ranges.append([s, e])

    # محدود به max_chunks مهم‌ترین (بر اساس تعداد hit‌ها در range)
    if len(ranges) > max_chunks:
        ranges_with_count: List[tuple] = []
        for r in ranges:
            count = sum(1 for h in hit_lines if r[0] <= h < r[1])
            ranges_with_count.append((count, r))
        ranges_with_count.sort(key=lambda x: -x[0])
        ranges = [r for _, r in ranges_with_count[:max_chunks]]
        ranges.sort()

    # build خروجی با line numbers
    out_parts: List[str] = []
    total = 0
    last_end = 0
    for r in ranges:
        s, e = r
        if last_end and s > last_end:
            skipped = s - last_end
            out_parts.append(f"\n... [پرش {skipped} خط] ...\n")
        chunk_lines = []
        for i in range(s, e):
            chunk_lines.append(f"{i+1:5d} | {lines[i]}")
        chunk_text = "\n".join(chunk_lines)
        if total + len(chunk_text) > max_total_chars:
            chunk_text = chunk_text[: max_total_chars - total]
            out_parts.append(chunk_text)
            break
        out_parts.append(chunk_text)
        total += len(chunk_text)
        last_end = e

    return "\n".join(out_parts)


def _build_keywords_from_acs(acceptance_criteria: List[Any], task_prompt: str = "") -> List[str]:
    """استخراج کلمات کلیدی از معیارهای پذیرش (فارسی + انگلیسی) برای جستجو در فایل‌ها.
    این کلمات کلیدی برای chunk extraction استفاده می‌شوند تا فقط بخش‌های مرتبط
    فایل‌های بزرگ به verifier داده شود.

    🔬 (Runtime Verify Stage 1) — AC می‌تواند str یا dict باشد. text را استخراج می‌کنیم.
    """
    import re
    ac_texts = [_ac_text_of(c) for c in acceptance_criteria]
    text = " ".join(ac_texts) + " " + (task_prompt or "")
    keywords: set = set()
    # کلمات کلیدی انگلیسی (CamelCase + snake_case طولانی)
    for m in re.findall(r"\b[A-Z][a-zA-Z0-9]{3,}\b", text):
        keywords.add(m)
    for m in re.findall(r"\b[a-z][a-z0-9_]{4,}\b", text):
        if "_" in m or len(m) > 6:
            keywords.add(m)
    # کلمات کلیدی فارسی (3+ کاراکتر فارسی)
    for m in re.findall(r"[؀-ۿ]{4,}", text):
        keywords.add(m)
    # حذف stopwords معمول
    stopwords = {
        "function", "class", "import", "export", "return", "const",
        "است", "این", "آن", "های", "هایی", "می‌شود", "شده", "باشد",
        "برای", "وجود", "ندارد", "دارد", "کاربر", "سیستم", "بتواند",
    }
    keywords = {k for k in keywords if k.lower() not in stopwords}
    return sorted(keywords, key=lambda x: -len(x))[:20]


def _extract_keywords_from_prompt(prompt: str, max_keywords: int = 5) -> List[str]:
    """استخراج کلیدواژه‌های کلاس/تابع از prompt (CamelCase + snake_case طولانی)."""
    import re
    if not prompt:
        return []
    # CamelCase identifiers (کلاس‌ها)
    camels = re.findall(r"\b([A-Z][a-zA-Z0-9]{4,})\b", prompt)
    # snake_case identifiers با حداقل ۲ underscore یا طول > 8
    snakes = re.findall(r"\b([a-z][a-z0-9_]{6,})\b", prompt)
    # filter رایج‌ها
    common = {
        "function", "method", "endpoint", "service", "class", "object",
        "request", "response", "result", "return", "param", "value",
        "string", "number", "boolean", "array", "object", "import",
        "export", "default", "async", "await", "promise", "callback",
        "should", "would", "could", "thing", "stuff", "should_not",
    }
    seen: set = set()
    out: List[str] = []
    for kw in camels + snakes:
        kw_low = kw.lower()
        if kw_low in common or kw in seen:
            continue
        seen.add(kw)
        out.append(kw)
        if len(out) >= max_keywords:
            break
    return out


async def _github_code_search(
    repo: str, keywords: List[str], token: str, max_per_keyword: int = 3
) -> Dict[str, List[str]]:
    """GitHub Code Search برای کلیدواژه‌ها — برمی‌گرداند {keyword: [path,...]}."""
    if not keywords or not token or "/" not in repo:
        return {}
    headers = _gh_headers(token)
    results: Dict[str, List[str]] = {}
    timeout = aiohttp.ClientTimeout(total=20)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        for kw in keywords[:5]:  # حداکثر ۵ keyword
            try:
                # GitHub Code Search syntax: <keyword>+repo:<owner>/<repo>
                q = f"{kw}+repo:{repo}"
                url = f"{GITHUB_API}/search/code?q={q}&per_page={max_per_keyword}"
                async with session.get(url, headers=headers) as r:
                    if r.status != 200:
                        continue
                    data = await r.json()
                items = (data.get("items") or [])[:max_per_keyword]
                paths = [it.get("path", "") for it in items if it.get("path")]
                if paths:
                    results[kw] = paths
            except Exception:
                continue
    return results


def _sync_prompt_checkboxes(prompt: str, steps: List[Dict[str, Any]]) -> str:
    """به‌روزرسانی markdown checkbox‌های موجود در `prompt` بر اساس وضعیت `steps`.

    Pattern: `- [ ] **مرحله N: ...**` یا `- [~] **مرحله N: ...**` یا `- [x] **مرحله N: ...**`
    map:  done → [x],  partial → [~],  not_done/pending → [ ]
    """
    if not prompt or not steps:
        return prompt
    import re as _re
    status_to_mark = {
        "done": "x",
        "partial": "~",
        "not_done": " ",
        "pending": " ",
        "error": " ",
    }
    out = prompt
    for s in steps:
        sid = s.get("id")
        if sid is None:
            continue
        mark = status_to_mark.get((s.get("status") or "pending"), " ")
        # pattern: یا [ ] یا [~] یا [x]، بعد فضای خالی، بعد **مرحله N:
        pattern = _re.compile(
            rf"-\s*\[[ x~]\]\s+(\*\*مرحله\s*{_re.escape(str(sid))}\b)",
        )
        out = pattern.sub(lambda m: f"- [{mark}] {m.group(1)}", out, count=1)
    return out


def _recover_partial_json(response: str) -> Dict[str, Any]:
    """تلاش برای استخراج فیلدهای اصلی از JSON ناقص/truncated.

    Strategy: regex برای پیدا کردن آرایه‌های `done_parts`, `remaining_parts`,
    `next_actions` و فیلدهای اسکالر `status`, `summary`, `confidence_score`
    حتی اگر JSON کلی valid نباشد. برای مواردی که `criteria_results` در وسط
    truncate شد ولی فیلدهای قبلی کامل تولید شده‌اند.
    """
    import re
    out: Dict[str, Any] = {}
    if not response:
        return out

    # status
    m = re.search(r'"status"\s*:\s*"([^"]+)"', response)
    if m:
        out["status"] = m.group(1)

    # summary (یک‌خطی، بدون \n داخلی)
    m = re.search(r'"summary"\s*:\s*"((?:[^"\\]|\\.)*)"', response)
    if m:
        out["summary"] = m.group(1).replace('\\n', '\n').replace('\\"', '"')

    # confidence_score
    m = re.search(r'"confidence_score"\s*:\s*([0-9.]+)', response)
    if m:
        try:
            out["confidence_score"] = float(m.group(1))
        except Exception:
            pass

    # arrays of strings: done_parts, remaining_parts, next_actions
    for key in ("done_parts", "remaining_parts", "next_actions"):
        m = re.search(rf'"{key}"\s*:\s*\[([^\]]*)\]', response, re.DOTALL)
        if m:
            try:
                # parse string items داخل array
                items_blob = m.group(1)
                items = re.findall(r'"((?:[^"\\]|\\.)*)"', items_blob)
                out[key] = [
                    s.replace('\\n', ' ').replace('\\"', '"').strip()
                    for s in items if s.strip()
                ]
            except Exception:
                pass

    # 🆕 (Multi-pass Checklist) — steps_status: لیست dict‌ها
    m = re.search(r'"steps_status"\s*:\s*\[(.*?)\]\s*[,}]', response, re.DOTALL)
    if m:
        try:
            steps_blob = m.group(1)
            # هر object را با brace-matching ساده extract کن
            items: List[Dict[str, Any]] = []
            depth = 0
            buf = []
            for ch in steps_blob:
                if ch == "{":
                    depth += 1
                    buf.append(ch)
                elif ch == "}":
                    depth -= 1
                    buf.append(ch)
                    if depth == 0:
                        obj_str = "".join(buf).strip()
                        buf = []
                        try:
                            import json as _json
                            items.append(_json.loads(obj_str))
                        except Exception:
                            # fallback: regex extract id/status/completion/remaining
                            entry: Dict[str, Any] = {}
                            mid = re.search(r'"id"\s*:\s*"?(\d+)"?', obj_str)
                            if mid:
                                entry["id"] = int(mid.group(1))
                            mst = re.search(r'"status"\s*:\s*"([^"]+)"', obj_str)
                            if mst:
                                entry["status"] = mst.group(1)
                            mcp = re.search(r'"completion_pct"\s*:\s*([0-9]+)', obj_str)
                            if mcp:
                                entry["completion_pct"] = int(mcp.group(1))
                            mre = re.search(r'"remaining"\s*:\s*"((?:[^"\\]|\\.)*)"', obj_str)
                            if mre:
                                entry["remaining"] = mre.group(1).replace('\\"', '"')
                            mev = re.search(r'"evidence"\s*:\s*"((?:[^"\\]|\\.)*)"', obj_str)
                            if mev:
                                entry["evidence"] = mev.group(1).replace('\\"', '"')
                            if entry:
                                items.append(entry)
                elif depth > 0:
                    buf.append(ch)
            if items:
                out["steps_status"] = items
        except Exception:
            pass

    return out


def format_done_remaining_for_message(report: Any, max_per_section: int = 5) -> str:
    """خروجی متن قابل خواندن از done_parts/remaining_parts/next_actions/confidence
    برای پیام Telegram/Email — با truncate و bullet."""
    lines: List[str] = []
    done = list(getattr(report, "done_parts", []) or [])
    remaining = list(getattr(report, "remaining_parts", []) or [])
    next_actions = list(getattr(report, "next_actions", []) or [])
    confidence = float(getattr(report, "confidence_score", 0.0) or 0.0)

    if confidence > 0:
        lines.append(f"🎯 اعتماد: *{int(confidence * 100)}%*")

    if done:
        lines.append(f"\n✅ *انجام‌شده ({len(done)}):*")
        for item in done[:max_per_section]:
            text = str(item).strip().replace("\n", " ")[:180]
            if text:
                lines.append(f"• {text}")
        if len(done) > max_per_section:
            lines.append(f"_… و {len(done) - max_per_section} مورد دیگر_")

    if remaining:
        lines.append(f"\n⏳ *باقی‌مانده ({len(remaining)}):*")
        for item in remaining[:max_per_section]:
            text = str(item).strip().replace("\n", " ")[:180]
            if text:
                lines.append(f"• {text}")
        if len(remaining) > max_per_section:
            lines.append(f"_… و {len(remaining) - max_per_section} مورد دیگر_")

    if next_actions:
        lines.append("\n🪜 *اقدامات بعدی پیشنهادی:*")
        for item in next_actions[:3]:
            text = str(item).strip().replace("\n", " ")[:180]
            if text:
                lines.append(f"• {text}")

    return "\n".join(lines)


def _find_similar_paths(
    missing_path: str, all_paths: List[str], max_results: int = 5
) -> List[str]:
    """برای فایل ذکر‌شده ولی یافت‌نشده، در tree دنبال فایل‌های با نام مشابه می‌گرد.

    معیار شباهت: stem (اسم فایل بدون پسوند و دایرکتوری) به‌صورت substring
    در path هدف بیاید، یا برعکس. همچنین فایل‌های هم‌دایرکتوری بررسی می‌شوند.
    """
    if not missing_path or not all_paths:
        return []
    import os
    stem = os.path.splitext(os.path.basename(missing_path))[0].lower()
    if len(stem) < 3:
        return []
    target_dir = os.path.dirname(missing_path).lower()
    scored: List[tuple] = []
    for p in all_paths:
        p_low = p.lower()
        p_stem = os.path.splitext(os.path.basename(p))[0].lower()
        score = 0
        if stem in p_stem or p_stem in stem:
            score += 10
        # تطابق partial: چند کاراکتر اول/آخر یکسان
        if len(stem) >= 4 and len(p_stem) >= 4:
            if stem[:4] == p_stem[:4]:
                score += 3
        # هم‌دایرکتوری بودن
        if target_dir and os.path.dirname(p_low) == target_dir:
            score += 2
        # کلمات کلیدی مشترک (split by _ / -)
        stem_tokens = set(t for t in stem.replace("-", "_").split("_") if len(t) >= 3)
        p_tokens = set(t for t in p_stem.replace("-", "_").split("_") if len(t) >= 3)
        common = stem_tokens & p_tokens
        score += len(common) * 4
        if score > 0:
            scored.append((score, p))
    scored.sort(key=lambda x: -x[0])
    return [p for _, p in scored[:max_results]]


async def _fetch_recent_commits(
    repo: str, branch: Optional[str], token: str, limit: int = 15
) -> List[Dict[str, Any]]:
    headers = _gh_headers(token)
    url = f"{GITHUB_API}/repos/{repo}/commits?per_page={limit}"
    if branch:
        url += f"&sha={branch}"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, timeout=30) as r:
                if r.status != 200:
                    return []
                data = await r.json()
                if not isinstance(data, list):
                    return []
                return [
                    {
                        "sha": c.get("sha", "")[:7],
                        "message": (c.get("commit", {}).get("message") or "").split("\n")[0][:200],
                        "date": (c.get("commit", {}).get("author") or {}).get("date", ""),
                    }
                    for c in data
                ]
    except Exception:
        return []


# ============================================================================
# 🆕 (Phase 3) — یادآور Telegram برای backfill AC + دکمه trigger
# ============================================================================

# rate-limit: حداکثر یک‌بار در ۲۴ ساعت برای کل سیستم
_BACKFILL_NEEDED_NOTIFY_LAST_AT: Optional[datetime] = None
_BACKFILL_NEEDED_NOTIFY_COOLDOWN = timedelta(hours=24)


async def _maybe_send_backfill_needed_notification() -> None:
    """اگر AC هایی هستند که نیاز به Phase 3 upgrade دارند، یک نوتیفیکیشن
    تلگرامی صدا‌دار با دکمه «اجرای force backfill» بفرست.

    rate-limit: یک‌بار در ۲۴ ساعت (تا کاربر spam نشود).
    """
    global _BACKFILL_NEEDED_NOTIFY_LAST_AT

    now = datetime.now(timezone.utc)
    if (
        _BACKFILL_NEEDED_NOTIFY_LAST_AT is not None
        and (now - _BACKFILL_NEEDED_NOTIFY_LAST_AT) < _BACKFILL_NEEDED_NOTIFY_COOLDOWN
    ):
        return

    # شمارش AC های نیاز به upgrade (همان منطق diagnostics)
    try:
        from .oversight_service import get_oversight_service
        from .verify_runtime.ac_enricher import _ac_already_classified
    except Exception:
        return

    service = get_oversight_service()
    ac_unclassified = 0
    ac_phase3_gap = 0
    tasks_needing = 0
    for t in service.tasks:
        acs = t.acceptance_criteria or []
        if not acs:
            continue
        task_needs = False
        for ac in acs:
            ac_dict = ac if isinstance(ac, dict) else {
                "text": str(ac), "verify_method": "static", "verify_plan": {},
            }
            if not _ac_already_classified(ac_dict):
                ac_unclassified += 1
                task_needs = True
            m = str(ac_dict.get("verify_method") or "static").lower()
            if m == "ui_interaction":
                _plan = ac_dict.get("verify_plan") or {}
                _steps = _plan.get("ui_steps") or []
                _real = sum(
                    1 for s in _steps if isinstance(s, dict)
                    and str(s.get("action") or "").lower() not in ("", "navigate", "screenshot")
                ) if isinstance(_steps, list) else 0
                if _real < 2:
                    ac_phase3_gap += 1
                    task_needs = True
        if task_needs:
            tasks_needing += 1

    total_gap = ac_unclassified + ac_phase3_gap
    if total_gap == 0 or tasks_needing == 0:
        return  # چیزی برای ارسال نیست

    # ارسال نوتیفیکیشن
    try:
        from .notification_service import notification_service
        msg = (
            f"🔬 *backfill AC پیشنهاد می‌شود*\n\n"
            f"{tasks_needing} تسک شامل AC هایی هستند که از قابلیت‌های Phase 3 "
            f"(action loop، vision_pair، expected_api_calls) استفاده نمی‌کنند.\n\n"
            f"📊 جزئیات:\n"
            f"• AC طبقه‌بندی نشده: {ac_unclassified}\n"
            f"• AC با plan ناقص (نیاز Phase 3 upgrade): {ac_phase3_gap}\n\n"
            f"با زدن دکمه زیر، enricher روی همه AC ها اجرا می‌شود "
            f"(force re-enrich) — حدود ۳-۵ دقیقه طول می‌کشد. نتیجه با "
            f"نوتیفیکیشن جداگانه می‌آید."
        )
        extra_buttons = [
            {"text": "🔬 اجرای force backfill", "callback_data": "backfill:run_force"},
            {"text": "✅ فقط unclassified", "callback_data": "backfill:run"},
        ]
        await notification_service.notify_event(
            "backfill_ac_needed", msg,
            subject="Backfill AC needed",
            priority="medium",
            extra_buttons=extra_buttons,
        )
        _BACKFILL_NEEDED_NOTIFY_LAST_AT = now
    except Exception as e:
        logger.debug(f"backfill_ac_needed notify failed: {e}")


# ============================================================================
# 🆕 (Phase 2) — ارسال mega-bundle.md کامل به Telegram
# ============================================================================

async def _send_mega_bundle(task: "OversightTask") -> None:
    """یک فایل bundle.html کامل از همه‌ی اطلاعات تسک + آخرین گزارش بساز
    و به‌عنوان document به Telegram بفرست.

    شامل: raw_idea + checklist + steps + prompt قدیم/جدید + همه‌ی
    probe ها (با vision/console/backend URLs/logs) + URLs aggregate.
    silent fail.

    🆕 (Phase 2) — قبل از ساخت bundle، تا ~۴۵ ثانیه poll می‌کنیم تا
    apply_followup_after_verify تمام شود و فیلد task.prompt به نسخه‌ی
    جدید آپدیت شده باشد. این تضمین می‌کند bundle شامل پرامپت بروز است،
    نه قدیمی.
    """
    import asyncio as _asyncio_lc
    import time as _time_lc

    # poll تا followup ست شود یا verify_status=done شود
    max_wait_s = 45
    poll_interval_s = 2.0
    elapsed = 0.0
    fresh_task = None
    while elapsed < max_wait_s:
        try:
            await _asyncio_lc.sleep(poll_interval_s)
            elapsed += poll_interval_s
            from .oversight_service import get_oversight_service as _gos
            svc = _gos()
            fresh_task = next((t for t in svc.tasks if t.id == task.id), None)
            if fresh_task is None:
                return
            # اگر prompt_history رشد کرد یا status=done شد، یعنی apply_followup
            # تمام شده — بسته به وضعیت bundle آماده است
            if (
                (fresh_task.prompt_history and len(fresh_task.prompt_history) > 0)
                or (fresh_task.verification_status == "done")
                or elapsed >= max_wait_s - 0.1
            ):
                break
        except Exception:
            continue

    if fresh_task is None:
        return

    # آخرین report برای این تسک
    try:
        from .oversight_service import get_oversight_service as _gos
        svc = _gos()
        last_report = None
        for r in svc.reports:
            if r.task_id == task.id:
                last_report = r
                break
        if last_report is None:
            return
    except Exception as e:
        logger.debug(f"_send_mega_bundle: fetch report failed: {e}")
        return

    # 🆕 (Phase 2 fix 2) — ابتدا PDF تلاش کن، fallback به HTML اگر Playwright
    # یا فونت در دسترس نباشد. PDF تجربه‌ی بهتری روی موبایل (تلگرام Android)
    # دارد چون مستقیماً در viewer داخلی باز می‌شود.
    try:
        from .oversight_mega_bundle import build_mega_bundle_pdf
        bundle_bytes, ext = await build_mega_bundle_pdf(fresh_task, last_report)
    except Exception as e:
        logger.debug(f"_send_mega_bundle: pdf build failed: {e}")
        # fallback to old md/html builder
        try:
            from .oversight_mega_bundle import build_mega_bundle_md
            bundle_bytes = build_mega_bundle_md(fresh_task, last_report)
            ext = ".html"
        except Exception as e2:
            logger.debug(f"_send_mega_bundle: html fallback also failed: {e2}")
            return

    if not bundle_bytes or len(bundle_bytes) < 100:
        return

    safe_tid = "".join(c if c.isalnum() else "_" for c in str(task.id))[:24]
    # extension بر اساس فرمت واقعی تولید شده — pdf یا html
    fname = f"bundle_{safe_tid}_{int(_time_lc.time())}{ext}"
    # 🆕 (Phase 2 fix 1) — caption شامل خلاصهٔ چک‌لیست به‌روز task_steps است
    # تا کاربر در همین پیام (بدون نیاز به باز کردن فایل) وضعیت مراحل را
    # ببیند. متن کامل و بخش‌های ۱-۱۰ در فایل پیوست هستند.
    try:
        from .oversight_verify_pdf import build_verify_checklist_message
        checklist_block = build_verify_checklist_message(
            fresh_task, last_report,
            char_budget=850,  # کمی پایین‌تر تا فضا برای trailer داشته باشیم
            header_override="📦 *بسته‌ی کامل verify*",
        )
        caption = (
            f"{checklist_block}\n\n"
            f"📎 جزئیات کامل (raw_idea + پرامپت قدیم/جدید + همه‌ی probe ها + "
            f"URLs + logs + analyses) در فایل پیوست."
        )
    except Exception as _ce:
        logger.debug(f"build checklist caption for bundle failed: {_ce}")
        title_for_caption = (fresh_task.title or fresh_task.id)[:80]
        caption = f"📦 بسته‌ی کامل verify — «{title_for_caption}»"

    try:
        from .notification_service import notification_service, TelegramChannel
    except Exception:
        return
    for ch in notification_service._build_channels():
        if not isinstance(ch, TelegramChannel):
            continue
        if not ch.is_configured():
            continue
        try:
            await ch.send_document(bundle_bytes, fname, caption=caption, silent=True)
        except Exception as e:
            logger.debug(f"mega bundle send_document failed: {e}")


# ============================================================================
# 🆕 (Phase 4) — Task Type Classification
# ============================================================================

# نوع تسک به route routing probe ها کمک می‌کند:
# - "ui": تسک‌های UI خالص → Smart Navigation + per-step UI probe
# - "backend": تسک‌های backend خالص → Backend Log Probe + Code-aware
# - "mixed": هر دو
# - "unknown": fallback به همه (با هزینه‌ی AI بیشتر)

_UI_KEYWORDS = (
    "button", "دکمه", "panel", "پنل", "form", "فرم", "modal", "page",
    "صفحه", "view", "تب", "tab", "sidebar", "navbar", "click", "کلیک",
    "input", "فیلد", "ui", "ux", "design", "color", "layout", "نمایش",
    "modal", "popup", "tooltip", "icon", "آیکن", "menu", "منو",
    "frontend", "فرانت", "render", "show", "display",
)

_BACKEND_KEYWORDS = (
    "endpoint", "api", "model", "مدل داده", "model data",
    "function", "تابع", "service", "سرویس", "database", "دیتابیس",
    "middleware", "cron", "thread", "lifecycle", "crud", "schema",
    "migration", "migrate", "router", "controller", "manager",
    "auth", "session", "token", "validator", "validation",
    "logger", "queue", "worker", "task scheduler", "celery",
    "backend", "بک‌اند", "بک اند", "logic", "منطق", "rebuild",
    "trigger", "post-build", "thread safety",
)


def _classify_task_type(task: "OversightTask") -> str:
    """تشخیص نوع تسک بر اساس فایل‌های هدف + متن AC.

    Returns: 'ui' | 'backend' | 'mixed' | 'unknown'

    منطق:
      1. اگر هیچ target_file و هیچ AC نیست → 'unknown'
      2. شمارش extension files: .py vs .ts/.tsx/.jsx/.js
      3. شمارش keyword در AC text
      4. ترکیب signal ها برای تصمیم
    """
    files = list(task.target_files or [])
    py_count = sum(1 for f in files if str(f).lower().endswith(".py"))
    ts_count = sum(
        1 for f in files
        if str(f).lower().endswith((".ts", ".tsx", ".jsx", ".js"))
    )

    # متن همه AC ها + task title + raw_idea
    all_text_parts = [(task.title or ""), (task.raw_idea or "")]
    for ac in (task.acceptance_criteria or []):
        if isinstance(ac, dict):
            all_text_parts.append(str(ac.get("text") or ""))
        else:
            all_text_parts.append(str(ac))
    for s in (task.task_steps or []):
        if isinstance(s, dict):
            all_text_parts.append(str(s.get("title") or ""))
            all_text_parts.append(str(s.get("scope") or ""))
    all_text = " ".join(all_text_parts).lower()

    ui_score = sum(1 for kw in _UI_KEYWORDS if kw in all_text)
    backend_score = sum(1 for kw in _BACKEND_KEYWORDS if kw in all_text)

    # هیچ signal — unknown
    if not files and ui_score == 0 and backend_score == 0:
        return "unknown"

    # فقط backend file ها + backend keyword غالب → backend
    if py_count > 0 and ts_count == 0:
        if backend_score >= ui_score:
            return "backend"
        return "mixed"

    # فقط ts/tsx + ui keyword غالب → ui
    if ts_count > 0 and py_count == 0:
        if ui_score >= backend_score:
            return "ui"
        return "mixed"

    # هم py هم ts → mixed
    if py_count > 0 and ts_count > 0:
        return "mixed"

    # فقط متن — تصمیم با ratio
    if backend_score >= ui_score * 2 and backend_score >= 2:
        return "backend"
    if ui_score >= backend_score * 2 and ui_score >= 2:
        return "ui"
    if ui_score == 0 and backend_score == 0:
        return "unknown"
    return "mixed"


# ============================================================================
# 🆕 (Phase 5 — bug 4) — Wiring Check
# verify فقط existence نگاه نکند — wiring/integration هم چک کند تا
# false-positive «file exists ⇒ implemented» جلوگیری شود.
# ============================================================================

def _check_file_wiring(
    step_text: str,
    target_files: List[str],
    file_contents: Dict[str, str],
    repo_tree: Optional[List[str]],
) -> Dict[str, Any]:
    """چک می‌کند آیا فایل‌های مرتبط با step، توسط جای دیگری import می‌شوند.

    این فقط برای فایل‌های python (.py) منطقی است.

    Returns:
        {
            "status": "wired" | "orphan" | "unknown",
            "detail": str,
            "matched_files": [...],
            "importers_found": int,
        }
    """
    import re as _re
    if not target_files or not file_contents:
        return {"status": "unknown", "detail": "no target_files or file_contents", "matched_files": [], "importers_found": 0}

    # match target_files با step_text (token-overlap)
    step_lower = (step_text or "").lower()
    step_tokens = set(
        t.lower() for t in _re.findall(r"[A-Za-z][A-Za-z0-9]+", step_text or "")
        if len(t) >= 3
    )
    matched: List[str] = []
    for tf in target_files:
        if not tf or not str(tf).endswith(".py"):
            continue
        basename = str(tf).rsplit("/", 1)[-1].rsplit(".", 1)[0]
        if len(basename) < 4:
            continue
        # match اگر basename یا نسخه‌ی space-shaped در step هست
        bt = set(t.lower() for t in _re.split(r"[_\-.]", basename) if len(t) >= 3)
        if basename.lower() in step_lower or (bt and bt.issubset(step_tokens)):
            matched.append(str(tf))
    if not matched:
        return {
            "status": "unknown",
            "detail": "هیچ target_file مرتبط با step text پیدا نشد",
            "matched_files": [],
            "importers_found": 0,
        }

    # برای هر matched file، آیا توسط فایل دیگری import می‌شود؟
    importers_total = 0
    orphan_files: List[str] = []
    for tf in matched:
        # ساخت import patterns — هم relative هم absolute
        # e.g. backend/app/services/scan_v5/foo.py
        # patterns: "scan_v5.foo", "scan_v5 import foo", "from .scan_v5 import foo"
        parts = str(tf).replace("\\", "/").split("/")
        basename = parts[-1].rsplit(".", 1)[0]
        if basename == "__init__":
            continue  # __init__.py auto-wired
        # generate possible import strings
        patterns: List[str] = []
        for i in range(len(parts) - 1, -1, -1):
            suffix = ".".join(parts[i:-1] + [basename])
            if suffix:
                patterns.append(suffix)
        patterns.append(basename)
        # search in همه file_contents (به جز خود فایل)
        importer_count = 0
        for fp, content in file_contents.items():
            if fp == tf:
                continue
            if not str(fp).endswith(".py"):
                continue
            # check patterns:
            #  - "import X.Y.basename"
            #  - "from X.Y import basename"
            #  - "from .Y.basename" (relative)
            #  - "from ..Y.basename" (parent-relative)
            #  - "import basename"
            _hit = False
            for pat in patterns:
                if (
                    f"import {pat}" in content
                    or f"from {pat}" in content
                    or f"from .{pat}" in content
                    or f"from ..{pat}" in content
                ):
                    _hit = True
                    break
            # نهایی: basename به‌عنوان identifier
            if not _hit:
                if (
                    f"from .{basename} " in content
                    or f"from ..{basename} " in content
                    or f"import {basename} " in content
                    or f"import {basename}\n" in content
                ):
                    _hit = True
            if _hit:
                importer_count += 1
        importers_total += importer_count
        if importer_count == 0:
            orphan_files.append(tf)

    if not orphan_files:
        return {
            "status": "wired",
            "detail": f"همه‌ی {len(matched)} فایل matched توسط ≥۱ فایل دیگر import می‌شوند",
            "matched_files": matched,
            "importers_found": importers_total,
        }

    # 🆕 (bug 35) — اگر file_contents فقط شامل خود target_files است
    # (یعنی فایل‌هایی که داریم چک می‌کنیم) و هیچ importer بالقوه‌ای داخل
    # نیست، اعلام orphan false-positive است. شواهد: اگر هیچ فایلی در
    # file_contents از matched files نیست (یعنی importers اصلاً در
    # view نیستند) → status=unknown به جای orphan.
    _non_matched_py_files = sum(
        1 for fp in file_contents.keys()
        if str(fp).endswith(".py") and fp not in matched
    )
    if _non_matched_py_files == 0:
        return {
            "status": "unknown",
            "detail": (
                f"file_contents فقط شامل target_files matched است "
                f"({len(matched)} file)؛ importer بالقوه در دسترس نیست — "
                f"نمی‌توان orphan را قطعی تشخیص داد."
            ),
            "matched_files": matched,
            "importers_found": 0,
        }
    # یا: اگر فایل‌های غیر-matched هم هستند ولی هیچ‌کدام import statement
    # ندارند (corpus ناقص است)، باز هم unknown
    _has_any_import = any(
        ("import " in (content or "")) for fp, content in file_contents.items()
        if fp not in matched and content
    )
    if not _has_any_import:
        return {
            "status": "unknown",
            "detail": (
                f"در {_non_matched_py_files} فایل غیر-matched هیچ "
                f"import statement پیدا نشد — corpus محدود است."
            ),
            "matched_files": matched,
            "importers_found": 0,
        }

    return {
        "status": "orphan",
        "detail": (
            f"{len(orphan_files)} از {len(matched)} فایل matched توسط هیچ فایل "
            f"دیگری import نمی‌شوند: {[f.rsplit('/', 1)[-1] for f in orphan_files[:3]]}"
        ),
        "matched_files": matched,
        "importers_found": importers_total,
        "orphan_files": orphan_files,
    }


# ============================================================================
# 🔬 (inspector_probe Phase 1 — relevance fix) — تشخیص route مرتبط با تسک
# ============================================================================

def _infer_route_for_step(
    step: Dict[str, Any], task: "OversightTask",
) -> Tuple[str, bool]:
    """استخراج route مرتبط با یک task_step.

    Returns: (route, is_specific) — اگر is_specific=False، نتوانستیم route
    خاصی پیدا کنیم و به / fallback شده‌ایم.

    تلاش به ترتیب:
      1) explicit URL path در scope/title (مثل /charts، /admin/users)
      2) Next.js App Router file path (app/X/page.tsx)
      3) pages/X.tsx
      4) "X page" / "X panel" / "X tab" pattern → /x (kebab)
      5) ComponentName.tsx در target_files → /component-name
      6) نگاشت کلمات کلیدی فارسی/انگلیسی
      7) fallback (is_specific=False)
    """
    import re as _re
    scope = str(step.get("scope") or "")
    title = str(step.get("title") or "")
    combined = f"{scope} {title}"
    combined_low = combined.lower()

    # 1) explicit URL path — /foo or /foo/bar (نه فقط /)
    # حداقل ۳ حرف بعد از / تا با همان "/" تنها confuse نشود
    # 🆕 (bug 32) — exclude file-extension matches (e.g., `/page.tsx`,
    # `/utils.py`). قبلاً «frontend/.../page.tsx» را به /page تبدیل می‌کرد
    # که در runtime → 404. حالا اگر بعد از match یک `.` همراه با حرف بیاید
    # (یعنی پسوند فایل)، آن match رد می‌شود.
    # همچنین کلمات generic مثل page/pages/index/utils/main رد می‌شوند.
    _GENERIC_PATH_WORDS = {
        "page", "pages", "index", "main", "app", "src", "lib",
        "utils", "helpers", "types", "components", "common",
        "dist", "build", "node_modules", "test", "tests",
    }
    # 🆕 (bug 32) — انکر سمت راست به non-path-char (و سپس exclude file ext)
    # تا regex نتواند با backtrack از "/page.tsx" ، "/pag" استخراج کند.
    for _m_url in _re.finditer(
        r"(?<!\w)/([a-z][a-z0-9_-]{2,}(?:/[a-z0-9_-]+)*)(?![a-z0-9_-])(?!\.[a-z])",
        combined_low,
    ):
        _candidate = _m_url.group(1)
        # اگر فقط یک segment است و در لیست generic، رد کن
        if "/" not in _candidate and _candidate in _GENERIC_PATH_WORDS:
            continue
        return ("/" + _candidate, True)

    # 2) Next.js App Router file path
    m1 = _re.search(r"app/([a-z0-9_\-]+(?:/[a-z0-9_\-]+)*)/page\.[jt]sx?", combined_low)
    if m1:
        route = m1.group(1).strip("/")
        if route and not route.startswith(("layout", "_app", "_document")):
            return ("/" + route, True)

    # 3) pages/X.tsx
    m2 = _re.search(r"pages/([a-z0-9_\-]+)\.[jt]sx?", combined_low)
    if m2:
        route = m2.group(1).strip("/")
        if route not in ("index", "_app", "_document"):
            return ("/" + route, True)

    # 4) "X page" / "X panel" / "X tab" / "X view" / "X screen" — extract X
    # مثال: "Routing Diagram page" → /routing-diagram
    m_pg = _re.search(
        r"\b([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+){0,2})\s+"
        r"(?:page|panel|view|tab|screen|section|dashboard)",
        combined,
    )
    if m_pg:
        name = m_pg.group(1).strip()
        # CamelCase/spaced → kebab
        # "Routing Diagram" → "routing-diagram"
        kebab = _re.sub(r"\s+", "-", name).lower()
        # for inner CamelCase
        kebab = _re.sub(r"(?<=[a-z])(?=[A-Z])", "-", kebab).lower()
        if kebab and len(kebab) >= 3:
            return ("/" + kebab, True)

    # 5) ComponentName از target_files (frontend components)
    for f in (task.target_files or []):
        f_str = str(f)
        # frontend/src/components/X/Y.tsx یا /SomeComponent.ts
        m_comp = _re.search(
            r"(?:components?|widgets?)[/\\][\w/\\]*?([A-Z][a-zA-Z0-9]+)\.(?:tsx?|jsx?)$",
            f_str,
        )
        if m_comp:
            name = m_comp.group(1)
            # skip generic names
            if name.lower() not in ("index", "main", "app", "utils", "types", "helpers"):
                kebab = _re.sub(r"(?<=[a-z])(?=[A-Z])", "-", name).lower()
                return ("/" + kebab, True)

    # 6) نگاشت کلمات کلیدی فارسی — فقط زمانی که کلمه صریحاً «صفحه/پنل/تب»
    # دنبالش بیاد (تا برای AC های backend مثل «thread lifecycle» اشتباه
    # route نسازیم).
    # 🆕 (Phase 3 fix) — keyword های generic که قبلاً false-positive route
    # می‌دادن (مثل "monitor"، "strateg") حذف شدند. اگر AC صریحاً «X page»
    # نگفته باشد، probe باید SKIPPED شود (نه route حدسی).
    fa_explicit_pages = [
        ("صفحه مناظره", "/debate"),
        ("صفحه نظارت", "/oversight"),
        ("صفحه پروژه", "/projects"),
        ("صفحه داشبورد", "/dashboard"),
        ("صفحه لاگین", "/login"),
        ("صفحه تنظیمات", "/settings"),
        ("صفحه پروفایل", "/profile"),
        ("صفحه استراتژی", "/strategies"),
        ("صفحه تونل", "/tunnels"),
        ("صفحه معاملات", "/trades"),
        ("پنل نظارت", "/oversight"),
        ("پنل استراتژی", "/strategies"),
    ]
    full_text = (scope + " " + title)
    for kw, route in fa_explicit_pages:
        if kw in full_text:
            return (route, True)

    # 7) fallback به task route — اما با علامت is_specific=False
    # نکته: keyword های انگلیسی generic حذف شدند چون باعث false-positive
    # routes می‌شدند (مثل "monitor diagram" → /monitor در حالی که پروژه
    # /monitor page ندارد). برای route قطعی، AC باید صریحاً "X page" یا
    # "/path" داشته باشد (پیش‌تر در regex ها بررسی شد).
    task_route = _infer_frontend_route_for_task(task)
    return (task_route, task_route != "/")


def _infer_frontend_route_for_task(task: "OversightTask") -> str:
    """تلاش برای استخراج یک route فرانت‌اند مرتبط با تسک.

    منطق:
      1) target_files شامل الگوهای Next.js App Router (frontend/src/app/X/page.tsx)
         یا Pages Router (pages/X.tsx) → /X
      2) prompt/raw_idea شامل URL مستقیم (مثل /debate) → آن
      3) fallback: "/"
    """
    import re as _re
    for f in (task.target_files or []):
        path = str(f or "").lower()
        # frontend/src/app/X/page.tsx  → /X
        # frontend/src/app/X/Y/page.tsx → /X/Y
        m = _re.search(r"(?:frontend/src/)?app/([^/]+(?:/[^/]+)*)/page\.[jt]sx?$", path)
        if m:
            route = m.group(1).strip("/")
            # حذف layout/_app/_document
            if route and not route.startswith(("layout", "_app", "_document")):
                return "/" + route
        # pages/X.tsx
        m2 = _re.search(r"pages/([^/]+)\.[jt]sx?$", path)
        if m2:
            route = m2.group(1).strip("/")
            if route not in ("index", "_app", "_document"):
                return "/" + route
    # سعی برای URL در prompt
    blob = ((task.prompt or "") + " " + (task.raw_idea or ""))[:2000]
    m3 = _re.search(r"(?:/oversight|/debate|/projects|/projects/\w+|/dashboard|/admin|/login|/signup|/profile|/settings)\b", blob.lower())
    if m3:
        return m3.group(0)
    return "/"


# ============================================================================
# 🔬 (inspector_probe Phase 1 — gap fix) — followup_prompt به‌عنوان .md به Telegram
# ============================================================================

async def _send_followup_prompt_as_md(task: "OversightTask") -> None:
    """اگر task.followup_prompt پر است، آن را به‌عنوان فایل .md به Telegram بفرست.

    apply_followup_after_verify یک AI call می‌زند که می‌تواند ۵-۳۰ ثانیه طول
    بکشد. به‌جای یک sleep ثابت، با polling هر ۲ ثانیه چک می‌کنیم تا حداکثر
    ۴۵ ثانیه. اگر در این بازه آماده نشد، silent skip.
    """
    import asyncio as _asyncio_lc
    fresh_followup: str = ""
    fresh_title: str = task.title or task.id
    fresh_status: str = ""

    max_wait_s = 45
    poll_interval_s = 2.0
    elapsed = 0.0

    while elapsed < max_wait_s:
        try:
            await _asyncio_lc.sleep(poll_interval_s)
            elapsed += poll_interval_s
            from .oversight_service import get_oversight_service as _gos
            svc = _gos()
            fresh = next((t for t in svc.tasks if t.id == task.id), None)
            if fresh is not None:
                fresh_followup = (fresh.followup_prompt or "").strip()
                fresh_title = (fresh.title or fresh.id) or fresh_title
                fresh_status = str(getattr(fresh, "verification_status", "") or "")
                # اگر followup ست شد یا status=done (پاک شده) خروج
                if fresh_followup and len(fresh_followup) >= 30:
                    break
                if fresh_status == "done":
                    # followup عمداً reset شده — ارسال لازم نیست
                    return
        except Exception:
            continue

    if not fresh_followup or len(fresh_followup) < 30:
        logger.debug(
            f"followup .md skipped for task {task.id}: "
            f"not ready after {max_wait_s}s (status={fresh_status})"
        )
        return

    try:
        from .notification_service import notification_service, TelegramChannel
    except Exception:
        return

    md_body = (
        f"# 📝 پرامپت ادامه — {fresh_title[:120]}\n\n"
        f"این پرامپت بر اساس آخرین verify ساخته شده. برای دور بعدی apply استفاده کن.\n\n"
        f"---\n\n"
        f"{fresh_followup}\n"
    )
    md_bytes = md_body.encode("utf-8")
    safe_tid = "".join(c if c.isalnum() else "_" for c in str(task.id))[:24]
    fname = f"followup_{safe_tid}_{int(time.time())}.md"
    caption = f"📝 پرامپت ادامه برای تسک «{fresh_title[:80]}»"

    for ch in notification_service._build_channels():
        if not isinstance(ch, TelegramChannel):
            continue
        if not ch.is_configured():
            continue
        try:
            await ch.send_document(md_bytes, fname, caption=caption, silent=True)
        except Exception as e:
            logger.debug(f"followup .md send_document failed: {e}")


# ============================================================================
# 🔬 (inspector_probe Phase 1 — gap fix) — Startup recovery برای session های orphan
# ============================================================================

def recover_orphan_auto_verify_sessions(max_age_minutes: int = 60) -> Dict[str, int]:
    """session های auto-verify که بیش از max_age_minutes پیش ساخته شده‌اند ولی
    هنوز status=active دارند را به archived تغییر بده.

    این تابع در lifespan startup فراخوانی می‌شود — اگر سرور قبل از archive
    شدن session crash کرده باشد، این تابع تمیزکاری می‌کند.

    خروجی: {archived_count, scanned_count}
    """
    try:
        from ..core.database import SessionLocal
        from ..models.inspector_session import InspectorSession
    except Exception as e:
        logger.debug(f"recover_orphan_sessions: import failed: {e}")
        return {"archived_count": 0, "scanned_count": 0}

    cutoff = datetime.utcnow() - timedelta(minutes=max_age_minutes)
    db = SessionLocal()
    archived = 0
    scanned = 0
    try:
        rows = (
            db.query(InspectorSession)
            .filter(InspectorSession.status == "active")
            .filter(InspectorSession.title.like("🤖%"))
            .all()
        )
        for r in rows:
            scanned += 1
            ca = r.created_at
            if ca is None:
                continue
            try:
                if ca.tzinfo is not None:
                    ca = ca.replace(tzinfo=None)
                if ca < cutoff:
                    r.status = "archived"
                    r.closed_at = datetime.utcnow()
                    archived += 1
            except Exception:
                continue
        if archived:
            db.commit()
            logger.info(
                f"recover_orphan_auto_verify_sessions: archived {archived} of {scanned}"
            )
    except Exception as e:
        logger.debug(f"recover_orphan_sessions query failed: {e}")
        try:
            db.rollback()
        except Exception:
            pass
    finally:
        try:
            db.close()
        except Exception:
            pass
    return {"archived_count": archived, "scanned_count": scanned}


# ============================================================================
# 🔬 (inspector_probe Phase 1) — TTL cleanup برای screenshot های orphan
# ============================================================================

def cleanup_orphan_runtime_screenshots(max_age_days: int = 3) -> Dict[str, int]:
    """screenshot هایی که بیش از max_age_days روی دیسک مانده‌اند را حذف کن.

    این تابع synchronous است (فایل‌سیستم). از داخل scheduler صدا زده می‌شود.

    خروجی: {deleted_count, deleted_bytes, scanned_count}
    """
    import os as _os
    from pathlib import Path as _Path

    try:
        from .oversight_service import STORAGE_DIR as _SD
    except Exception:
        return {"deleted_count": 0, "deleted_bytes": 0, "scanned_count": 0, "error": "STORAGE_DIR unavailable"}

    root = _Path(_SD) / "runtime_evidence"
    if not root.exists():
        return {"deleted_count": 0, "deleted_bytes": 0, "scanned_count": 0}

    threshold = time.time() - (max_age_days * 86400)
    deleted = 0
    deleted_bytes = 0
    scanned = 0
    try:
        for png in root.rglob("*.png"):
            scanned += 1
            try:
                st = png.stat()
                if st.st_mtime < threshold:
                    sz = st.st_size
                    png.unlink(missing_ok=True)
                    deleted += 1
                    deleted_bytes += sz
            except Exception:
                continue
        for jpg in root.rglob("*.jpg"):
            scanned += 1
            try:
                st = jpg.stat()
                if st.st_mtime < threshold:
                    sz = st.st_size
                    jpg.unlink(missing_ok=True)
                    deleted += 1
                    deleted_bytes += sz
            except Exception:
                continue
        # پوشه‌های خالی را هم پاک کن (best-effort)
        for d in sorted(root.rglob("*"), key=lambda p: -len(str(p))):
            try:
                if d.is_dir() and not any(d.iterdir()):
                    d.rmdir()
            except Exception:
                continue
    except Exception as e:
        logger.debug(f"cleanup_orphan_runtime_screenshots error: {e}")

    if deleted:
        logger.info(
            f"runtime_evidence TTL cleanup: deleted={deleted} files, "
            f"bytes={deleted_bytes}, scanned={scanned}"
        )
    return {"deleted_count": deleted, "deleted_bytes": deleted_bytes, "scanned_count": scanned}


# ============================================================================
# 🔬 (inspector_probe Phase 1) — ضمیمه‌ی screenshot ها به تلگرام + پاک‌سازی
# ============================================================================

def _collect_runtime_screenshot_entries(
    report: "OversightReport",
) -> List[Dict[str, Any]]:
    """لیست screenshot هایی که هنوز روی دیسک هستند را از evidence استخراج کن.

    خروجی: list of dicts با کلیدهای path + label + vision_description.
    """
    out: List[Dict[str, Any]] = []
    try:
        probes = (report.evidence or {}).get("runtime_probes") or []
    except Exception:
        return out
    if not isinstance(probes, list):
        return out
    for p in probes:
        if not isinstance(p, dict):
            continue
        ev = p.get("evidence") or {}
        if not isinstance(ev, dict):
            continue
        shots = ev.get("screenshots") or []
        if not isinstance(shots, list):
            continue
        for s in shots:
            if not isinstance(s, dict):
                continue
            path = s.get("path")
            if not path or s.get("archived_to_telegram"):
                continue
            try:
                import os as _os
                if not _os.path.isfile(path):
                    continue
            except Exception:
                continue
            out.append({
                "path": path,
                "label": s.get("label") or "screenshot",
                "vision_description": s.get("vision_description") or "",
                "ac_text": p.get("ac_text") or "",
                "_ref_probe": p,
                "_ref_shot": s,
            })
    return out


async def _send_runtime_screenshots_and_cleanup(
    task: "OversightTask",
    report: "OversightReport",
    max_send: int = 5,
) -> None:
    """screenshot های runtime را به تلگرام بفرست و در صورت موفقیت پاک کن.

    رفتار:
    - فقط تا max_send screenshot ارسال می‌شود (limit Telegram + reasonable)
    - بقیه روی دیسک می‌مانند، TTL cleanup آن‌ها را برمی‌دارد
    - photo های موفق → از دیسک پاک می‌شوند + در evidence
      archived_to_telegram=True ست می‌شود + path=None (vision_description می‌ماند)
    - اگر کانال تلگرام configured نیست → silent skip
    """
    try:
        from .notification_service import notification_service
    except Exception:
        return

    entries = _collect_runtime_screenshot_entries(report)
    if not entries:
        return
    entries = entries[:max_send]

    paths = [e["path"] for e in entries]
    captions: List[str] = []
    for e in entries:
        ac_excerpt = (e.get("ac_text") or "")[:80]
        vis = (e.get("vision_description") or "")[:300]
        cap = f"📸 {e['label']}\nAC: {ac_excerpt}"
        if vis:
            cap += f"\n👁 {vis}"
        captions.append(cap)

    try:
        results = await notification_service.send_extra_photos(
            paths, captions, silent=True,
        )
    except Exception as _e:
        logger.debug(f"send_extra_photos crashed: {_e}")
        return

    # موفق‌ها را پاک کن، evidence را آپدیت کن
    by_path = {r.get("path"): r for r in (results or []) if isinstance(r, dict)}
    import os as _os
    deleted_count = 0
    for e in entries:
        r = by_path.get(e["path"])
        if not r or not r.get("ok"):
            continue
        try:
            _os.remove(e["path"])
            deleted_count += 1
        except Exception as _de:
            logger.debug(f"unlink screenshot failed: {_de}")
        try:
            e["_ref_shot"]["archived_to_telegram"] = True
            e["_ref_shot"]["path"] = None
        except Exception:
            pass

    # یک نوت در inspector_session
    try:
        sid = (report.evidence or {}).get("auto_verify_session_id")
        if sid is None:
            # یا از اولین probe بگیر
            probes = (report.evidence or {}).get("runtime_probes") or []
            for p in probes:
                ev = (p.get("evidence") if isinstance(p, dict) else None) or {}
                if ev.get("inspector_session_id"):
                    sid = ev["inspector_session_id"]
                    break
        if sid is not None and deleted_count > 0:
            from .verify_runtime.inspector_probe import _msg as _ip_msg
            await _ip_msg(
                int(sid), "system",
                f"📦 {deleted_count} screenshot به تلگرام آرشیو شد و از دیسک پاک شد",
            )
    except Exception:
        pass

    # ذخیره نهایی reports روی دیسک تا evidence جدید (path=None) محفوظ بماند
    try:
        from .oversight_service import get_oversight_service as _gos
        service = _gos()
        async with service._lock:
            service._save_reports()  # type: ignore[attr-defined]
    except Exception:
        # برخی نسخه‌ها _save_reports ندارند یا اسم متفاوت دارند
        try:
            from .oversight_service import get_oversight_service as _gos
            service = _gos()
            async with service._lock:
                if hasattr(service, "_save_reports"):
                    service._save_reports()
                elif hasattr(service, "_save"):
                    service._save()
        except Exception as _se2:
            logger.debug(f"could not persist updated evidence: {_se2}")


# ============================================================================
# 🔬 (inspector_probe Phase 1) — مدیریت چرخه‌حیات auto-verify inspector_session
# ============================================================================

def _resolve_inspector_project_id(
    task: "OversightTask",
    watched: Optional["WatchedProject"],
) -> str:
    """تشخیص project_id که در InspectorSession ذخیره می‌شود.

    منطق دو-مرحله:
      الف) تلاش برای resolve به Project.id محلی (از طریق resolve_project_for_task)
           تا session در تب «بازرس ویژه» همان پروژه نمایش داده شود.
      ب) در صورت شکست (پروژه‌ی محلی نیست)، fallback به repo_full_name
         (session ذخیره می‌شود ولی در UI ظاهر نخواهد بود).
    """
    try:
        from ..core.database import SessionLocal
        from .oversight_service import get_oversight_service
        service = get_oversight_service()
        db = SessionLocal()
        try:
            info = service.resolve_project_for_task(db, str(task.id))
        finally:
            try:
                db.close()
            except Exception:
                pass
        if isinstance(info, dict) and info.get("matched") and info.get("project_id"):
            return str(info["project_id"])
    except Exception as e:
        logger.debug(f"_resolve_inspector_project_id: resolve failed: {e}")
    # fallback
    if watched and getattr(watched, "repo_full_name", None):
        return str(watched.repo_full_name)
    return str(getattr(task, "project_full_name", "") or "unknown")


async def _create_auto_verify_inspector_session(
    *, task: "OversightTask", watched: Optional["WatchedProject"],
) -> Optional[int]:
    """ایجاد یک InspectorSession جدید با عنوان «🤖 auto-verify · …».

    خروجی: id session جدید، یا None در صورت شکست.
    این تابع هیچ exception ای بیرون نمی‌اندازد.
    """
    project_id = _resolve_inspector_project_id(task, watched)
    safe_title = (task.title or task.id)[:50]
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")
    title = f"🤖 auto-verify · {safe_title} · {ts}"

    def _create_sync() -> Optional[int]:
        try:
            from ..core.database import SessionLocal
            from ..models.inspector_session import InspectorSession
        except Exception as e:
            logger.debug(f"auto-verify session import failed: {e}")
            return None
        db = SessionLocal()
        try:
            sess = InspectorSession(
                project_id=project_id, status="active", title=title,
            )
            db.add(sess)
            db.commit()
            db.refresh(sess)
            return int(sess.id)
        except Exception as e:
            logger.debug(f"auto-verify session insert failed: {e}")
            try:
                db.rollback()
            except Exception:
                pass
            return None
        finally:
            try:
                db.close()
            except Exception:
                pass

    try:
        import asyncio as _asyncio_local
        sid = await _asyncio_local.to_thread(_create_sync)
        if sid is not None:
            logger.info(f"auto-verify session created id={sid} for task={task.id}")
        return sid
    except Exception as e:
        logger.debug(f"auto-verify session create wrapper failed: {e}")
        return None


async def _archive_auto_verify_inspector_session(session_id: int) -> None:
    """status را به «archived» تغییر بده. silent fail."""
    def _archive_sync() -> None:
        try:
            from ..core.database import SessionLocal
            from ..models.inspector_session import InspectorSession
            from datetime import datetime as _dt
        except Exception:
            return
        db = SessionLocal()
        try:
            sess = db.query(InspectorSession).filter(
                InspectorSession.id == session_id
            ).first()
            if sess is None:
                return
            sess.status = "archived"
            sess.closed_at = _dt.utcnow()
            db.commit()
        except Exception as e:
            logger.debug(f"archive session failed: {e}")
            try:
                db.rollback()
            except Exception:
                pass
        finally:
            try:
                db.close()
            except Exception:
                pass

    try:
        import asyncio as _asyncio_local
        await _asyncio_local.to_thread(_archive_sync)
    except Exception:
        pass


async def verify_task(
    task_id: str,
    *,
    model_id: Optional[str] = None,
    triggered_by: str = "manual",
    include_runtime: bool = True,
    verify_v6: bool = True,
) -> Dict[str, Any]:
    """اجرای verify روی یک تسک — مستقل از execution.

    include_runtime: اگر False، فقط grep + AI (verify سریع، بدون probe).
    اگر True (پیش‌فرض)، probe های runtime نیز اجرا می‌شوند.

    verify_v6: اگر True (پیش‌فرض)، علاوه بر مسیر v5 موجود، iterative
    orchestrator v6 (3-tier escalation) روی AC ها اجرا می‌شود و نتایج
    در report.verify_trace + report.ac_probe_details ثبت می‌گردد +
    report.verify_version='v6'. اگر False، مسیر کاملاً v5 (backward compat).
    """
    service = get_oversight_service()
    task = next((t for t in service.tasks if t.id == task_id), None)
    if task is None:
        raise ValueError("تسک یافت نشد")
    watched = service._find_watched(task.watched_id) if task.watched_id else None
    if watched is None and task.project_full_name:
        # fallback: شاید watched id ندارد ولی full_name دارد
        watched = next(
            (w for w in service.watched if w.repo_full_name == task.project_full_name),
            None,
        )

    token = get_github_token()

    # 1) فایل‌های هدف
    target_files = list(task.target_files or [])
    if not target_files and task.prompt:
        from .oversight_strong_prompt import extract_target_files
        target_files = extract_target_files(task.prompt)

    # 2) معیارها
    acceptance_criteria = list(task.acceptance_criteria or [])
    if not acceptance_criteria and task.prompt:
        from .oversight_strong_prompt import extract_acceptance_criteria
        acceptance_criteria = extract_acceptance_criteria(task.prompt)

    if not acceptance_criteria:
        acceptance_criteria = [
            "تغییرات لازم در پروژه اعمال شده باشد",
            "هیچ تستی fail نشود",
            "linter بدون warning عبور کند",
        ]

    # 3) محتوای فعلی فایل‌ها
    # PR-aware mode: اگر تسک از طریق Inspector apply-action اجرا شده و PR
    # هنوز merge نشده، فایل‌ها باید از branch همان PR خوانده شوند تا verify
    # **قبل از merge** هم امکان‌پذیر باشد. اگر pr_branch دیگر روی repo
    # موجود نباشد (delete شده پس از merge)، fallback به branch اصلی و
    # از آنجا fetch می‌شود.
    file_contents: Dict[str, Optional[str]] = {}
    recent_commits: List[Dict[str, Any]] = []
    default_branch = (watched.default_branch if watched else None) or "main"
    repo_full_name = watched.repo_full_name if watched else task.project_full_name

    # تشخیص branch مورد استفاده برای verify
    applied_evidence = task.applied_evidence or {}
    pr_branch = applied_evidence.get("pr_branch") or ""
    pr_url = applied_evidence.get("pr_url") or ""
    branch = pr_branch or default_branch
    branch_source = "pr_branch" if pr_branch else "default"

    if token and repo_full_name and "/" in repo_full_name:
        try:
            file_contents = await _fetch_target_files(
                repo_full_name, target_files, branch, token
            )
            # اگر pr_branch ست بود ولی هیچ فایلی fetch نشد، احتمالاً branch
            # دیگر موجود نیست (merge + delete). به default fallback می‌کنیم.
            if pr_branch and (not file_contents or all(v is None for v in file_contents.values())):
                logger.info(
                    f"verify: pr_branch '{pr_branch}' بدون نتیجه — fallback به '{default_branch}'"
                )
                branch = default_branch
                branch_source = "default_fallback_after_pr_branch_missing"
                file_contents = await _fetch_target_files(
                    repo_full_name, target_files, branch, token
                )
        except Exception as e:
            logger.warning(f"verify: fetch files failed: {e}")
            # تلاش fallback اگر pr_branch fetch ناموفق بود
            if pr_branch and branch == pr_branch:
                try:
                    branch = default_branch
                    branch_source = "default_fallback_after_pr_error"
                    file_contents = await _fetch_target_files(
                        repo_full_name, target_files, branch, token
                    )
                except Exception as e2:
                    logger.warning(f"verify: default branch fetch هم شکست خورد: {e2}")
        try:
            recent_commits = await _fetch_recent_commits(repo_full_name, branch, token)
        except Exception as e:
            logger.warning(f"verify: fetch commits failed: {e}")

    # 3.5) repo tree برای fuzzy matching — کمک می‌کند verifier فایل‌های هم‌ارز
    # با نام متفاوت را هم تشخیص دهد (مثلاً پرامپت idea.py خواسته ولی پروژه
    # از oversight_service.py استفاده کرده)
    repo_tree: List[str] = []
    if token and repo_full_name and "/" in repo_full_name:
        try:
            repo_tree = await _fetch_repo_tree(repo_full_name, branch, token)
        except Exception as e:
            logger.warning(f"verify: fetch tree failed: {e}")

    # 3.6) GitHub Code Search — برای کلیدواژه‌های مهم (کلاس‌ها/توابع) که در
    # prompt ذکر شده‌اند، ببین در کجاهای repo استفاده می‌شوند. این کمک می‌کند
    # verifier حتی اگر فایل صریح نباشد، فایل‌های متن‌به‌متن مرتبط را پیدا کند.
    keyword_search: Dict[str, List[str]] = {}
    keywords: List[str] = []
    if token and repo_full_name and "/" in repo_full_name:
        try:
            keywords = _extract_keywords_from_prompt(task.prompt or "", max_keywords=5)
            if keywords:
                keyword_search = await _github_code_search(
                    repo_full_name, keywords, token, max_per_keyword=3
                )
        except Exception as e:
            logger.debug(f"verify: code search failed: {e}")

    # 🆕 کلمات کلیدی برای chunk extraction — هم AC و هم prompt
    # این کلمات برای برش هوشمند فایل‌های بزرگ (مثل page.tsx 4000+ خط) به‌کار می‌روند
    chunk_keywords = _build_keywords_from_acs(acceptance_criteria, task.prompt or "")

    # 3.7) 🆕 UI/frontend file injection — اگر AC یا prompt شامل کلمات
    # frontend-related باشد (UI، component، دکمه، page، نمایش، فرانت‌اند، ...)
    # حتماً فایل‌های اصلی frontend را به context اضافه کن، چون اغلب اوقات
    # target_files فقط backend files بود ولی AC مربوط به UI است.
    frontend_keywords = [
        "ui", "component", "page", "tsx", "frontend", "فرانت", "فرانت‌اند",
        "دکمه", "نمایش", "کپی", "panel", "view", "modal",
    ]
    prompt_lower = (task.prompt or "").lower() + " ".join(_ac_text_of(c) for c in acceptance_criteria).lower()
    needs_frontend = any(kw in prompt_lower for kw in frontend_keywords)
    auto_frontend_files: List[str] = []
    if needs_frontend and repo_tree:
        # فایل‌های page.tsx اصلی + components را پیدا کن (محدود به ۵ فایل)
        candidates = [
            p for p in repo_tree
            if (p.endswith("/page.tsx") or p.endswith("/page.jsx"))
            or "components/" in p and (p.endswith(".tsx") or p.endswith(".jsx"))
        ]
        # اولویت: فایل‌هایی که نام prompt در path است
        prompt_words = set()
        for kw in keywords[:5] if 'keywords' in dir() and keywords else []:
            prompt_words.add(kw.lower())
        scored = []
        for p in candidates:
            score = 1
            p_low = p.lower()
            if "/oversight" in p_low or "oversight" in p_low:
                score += 3
            if any(w in p_low for w in prompt_words):
                score += 2
            scored.append((score, p))
        scored.sort(key=lambda x: -x[0])
        auto_frontend_files = [p for _, p in scored[:5]]
        if auto_frontend_files and token:
            try:
                fe_contents = await _fetch_target_files(
                    repo_full_name, auto_frontend_files, branch, token
                )
                for k, v in fe_contents.items():
                    file_contents[k] = v
            except Exception as e:
                logger.debug(f"verify: fetch frontend files failed: {e}")

    # 4) ساخت پرامپت verifier — برای هر فایل یافت‌نشده، فایل‌های هم‌ارز را
    # از tree پیدا و محتوای آن‌ها را نیز fetch می‌کنیم
    fuzzy_resolved: Dict[str, List[str]] = {}  # missing_path -> similar_paths
    extra_files_to_fetch: List[str] = []
    for p in target_files:
        if file_contents.get(p) is None and repo_tree:
            similar = _find_similar_paths(p, repo_tree, max_results=3)
            if similar:
                fuzzy_resolved[p] = similar
                for sp in similar:
                    if sp not in target_files and sp not in extra_files_to_fetch:
                        extra_files_to_fetch.append(sp)

    if extra_files_to_fetch and token and repo_full_name and "/" in repo_full_name:
        try:
            extra_contents = await _fetch_target_files(
                repo_full_name, extra_files_to_fetch[:10], branch, token
            )
            for k, v in extra_contents.items():
                file_contents[k] = v
        except Exception as e:
            logger.warning(f"verify: fetch fuzzy-matched files failed: {e}")

    files_blob_parts: List[str] = []
    for p in target_files:
        c = file_contents.get(p)
        if c is None:
            similar = fuzzy_resolved.get(p, [])
            if similar:
                files_blob_parts.append(
                    f"=== {p} ===\n[فایل با این نام دقیق وجود ندارد — "
                    f"اما این فایل‌های هم‌نقش/هم‌ارز در repo یافت شدند: {', '.join(similar)}. "
                    f"محتوایشان در ادامه آمده — بررسی کن آیا نقش مورد نظر را برآورده می‌کنند.]"
                )
            else:
                files_blob_parts.append(f"=== {p} ===\n[فایل یافت نشد]")
        else:
            # 🆕 chunk extraction هوشمند — اگر فایل بزرگ است (>10000 char)،
            # فقط بخش‌های مرتبط با کلمات کلیدی AC را بگیر، نه فقط N char اول
            # 🔴 (extraction-100pct-fix v2) — برگشت threshold از 50K به 15K،
            # نگه داشتن max_total_chars=60K. فایل‌های 15-50KB هم باید chunk
            # بشن چون چندین فایل × 30KB = context overflow در verifier.
            # 60KB chunks (به‌جای 12KB قبلی) همچنان context کافی می‌ده.
            if len(c) > 15000 and chunk_keywords:
                chunk = _extract_relevant_chunks(c, chunk_keywords, lines_around=80, max_total_chars=60000)
                files_blob_parts.append(
                    f"=== {p} ({len(c.splitlines())} line file — chunk‌های مرتبط با AC) ===\n{chunk}"
                )
            else:
                files_blob_parts.append(f"=== {p} ===\n{c[:8000]}")
    # محتوای فایل‌های هم‌ارز را هم اضافه کن (با chunk extraction برای فایل‌های بزرگ)
    for sp in extra_files_to_fetch[:10]:
        c = file_contents.get(sp)
        if c is not None:
            if len(c) > 10000 and chunk_keywords:
                chunk = _extract_relevant_chunks(c, chunk_keywords, lines_around=60, max_total_chars=10000)
                files_blob_parts.append(f"=== {sp} (هم‌ارز — chunk مرتبط) ===\n{chunk}")
            else:
                files_blob_parts.append(f"=== {sp} (فایل هم‌ارز) ===\n{c[:8000]}")
    # فایل‌های کشف‌شده با code search برای keywords مهم
    code_search_files: List[str] = []
    for kw, paths in keyword_search.items():
        for p in paths:
            if p not in target_files and p not in extra_files_to_fetch and p not in code_search_files:
                code_search_files.append(p)
    if code_search_files and token and repo_full_name and "/" in repo_full_name:
        try:
            extra2 = await _fetch_target_files(repo_full_name, code_search_files[:5], branch, token)
            for k, v in extra2.items():
                file_contents[k] = v
                if v is not None:
                    # لیست keywords که این فایل را برگرداندند
                    matched_kws = [kw for kw, ps in keyword_search.items() if k in ps]
                    files_blob_parts.append(
                        f"=== {k} (یافت‌شده با کلیدواژه‌های: {', '.join(matched_kws)}) ===\n{v[:6000]}"
                    )
        except Exception as e:
            logger.debug(f"verify: fetch code-search files failed: {e}")
    # 🆕 فایل‌های frontend که خودکار اضافه شده‌اند (وقتی AC مربوط به UI است)
    # 🚨 برای page.tsx اصلی (که می‌تواند 4000+ خط باشد)، حتماً chunk extraction استفاده کنیم
    for fe_path in auto_frontend_files:
        if fe_path in target_files or fe_path in extra_files_to_fetch:
            continue
        c = file_contents.get(fe_path)
        if c is not None:
            if len(c) > 10000 and chunk_keywords:
                chunk = _extract_relevant_chunks(c, chunk_keywords, lines_around=80, max_chunks=10, max_total_chars=15000)
                files_blob_parts.append(
                    f"=== {fe_path} (UI file — chunk‌های مرتبط با AC از {len(c.splitlines())} خط) ===\n{chunk}"
                )
            else:
                files_blob_parts.append(
                    f"=== {fe_path} (UI file — auto-added چون AC مربوط به فرانت‌اند است) ===\n{c[:8000]}"
                )
    files_blob = "\n\n".join(files_blob_parts) or "(فایل هدفی مشخص نیست — بر اساس کل پرامپت بررسی کن)"

    # خلاصهٔ ساختار repo برای دید کلی AI
    tree_blob = ""
    if repo_tree:
        # محدود به مسیرهای کد (backend/frontend/src/services/...) و حداکثر 200 خط
        meaningful = [p for p in repo_tree if any(
            seg in p for seg in ("backend/", "frontend/", "src/", "app/", "services/",
                                  "routes/", "components/", "pages/", "lib/", "utils/")
        )][:200]
        if meaningful:
            tree_blob = "\n".join(meaningful)

    commits_blob = "\n".join(
        f"- {c['sha']} ({c['date'][:10]}) {c['message']}" for c in recent_commits[:10]
    ) or "(کامیتی یافت نشد)"

    # 🤖 شواهد ماشینی per-AC — قبل از فرستادن به AI، خود ما کلمات AC را در
    # فایل‌ها grep می‌کنیم. این به AI hint قاطع می‌دهد که AC کدام در کجا
    # احتمالاً پیاده شده — و جلوگیری از not_done کاذب.
    machine_evidence = _evaluate_acs_against_files(
        acceptance_criteria, file_contents, repo_tree
    )
    machine_evidence_blob = _format_machine_evidence_for_prompt(machine_evidence)

    # 🔬 (Runtime Verify Stage 5) — probe های runtime را اجرا کن (Playwright/HTTP/pytest)
    # هر probe که شکست خورد، fail-soft می‌شود — verify ادامه می‌دهد.
    # نتایج به prompt verify اضافه می‌شود تا AI شواهد runtime را در ارزیابی
    # خود لحاظ کند.
    runtime_probe_results: List[Any] = []
    runtime_evidence_blob = ""
    runtime_override_hints: Dict[str, str] = {}  # ac_text → "passed" | "failed"
    # 🆕 (Phase 4 fix #17) — code-aware verdicts for task_steps —
    # populated در runtime block، استفاده‌شده در (a) prompt verifier
    # و (b) post-AI programmatic override روی steps_status
    step_code_verdicts: Dict[int, Dict[str, Any]] = {}
    runtime_run_id: Optional[str] = None
    # 🔬 (debug visibility) — توضیح اینکه چرا/چطور runtime block اجرا شد
    runtime_status_note: str = "did_not_run"
    try:
        import os as _os
        import uuid as _uuid
        from pathlib import Path as _Path
        runtime_enabled = (
            include_runtime and
            _os.environ.get("RUNTIME_VERIFY_ENABLED", "true").lower() != "false"
        )
        if not include_runtime:
            runtime_status_note = "skipped (include_runtime=false)"
        elif not runtime_enabled:
            runtime_status_note = "disabled by RUNTIME_VERIFY_ENABLED env"
        elif not acceptance_criteria:
            runtime_status_note = "no acceptance_criteria to probe"
        if runtime_enabled and acceptance_criteria:
            from .verify_runtime import (
                run_probes_for_task,
                enrich_acs_with_verify_plans,
            )
            from .verify_runtime.ac_enricher import _ac_already_classified
            from .verify_runtime.storage import (
                ensure_run_dir, write_manifest, cleanup_old_runs,
            )

            # 🔬 (Stage 5 fix) — اگر AC این تسک هنوز classify نشده (همه static)
            # و base URL داریم، AI را فراخوانی کن تا method ها را تشخیص دهد
            # (یعنی AC هایی که UI/API هستند درست probe بخورند، نه static skipped).
            try:
                needs_enrich = any(
                    not _ac_already_classified(ac if isinstance(ac, dict) else {"text": str(ac), "verify_method": "static", "verify_plan": {}})
                    for ac in acceptance_criteria
                )
                has_base_url = bool(
                    (watched and (getattr(watched, "frontend_base_url", None) or getattr(watched, "backend_base_url", None)))
                )
                if needs_enrich and has_base_url:
                    logger.info(
                        f"verify {task.id}: AC ها classify نشده‌اند — AI enricher را فراخوانی می‌کنیم"
                    )
                    enriched = await enrich_acs_with_verify_plans(
                        acceptance_criteria,
                        title=task.title,
                        description=task.raw_idea or task.prompt[:500],
                        target_files=list(task.target_files or []),
                        model_id=model_id,
                    )
                    if enriched:
                        # ذخیرهٔ AC جدید روی task (در lock)
                        async with service._lock:
                            task.acceptance_criteria = enriched
                            task.updated_at = now_iso()
                            service._save_tasks()
                        acceptance_criteria = enriched
            except Exception as _ee:
                logger.warning(f"AC on-the-fly enrichment failed: {_ee}")

            runtime_run_id = f"run_{int(time.time() * 1000)}_{_uuid.uuid4().hex[:6]}"
            run_dir = ensure_run_dir(
                _Path(STORAGE_DIR), str(task.id), runtime_run_id,
            )
            runtime_started_at = now_iso()

            # 🔬 (inspector_probe Phase 1) — یک inspector_session موقت بساز
            # تا probe ها بتوانند اقدامات قدم‌به‌قدم را در تب «بازرس ویژه» نشان دهند.
            # اگر ساخت شکست خورد، probe ها بدون session اجرا می‌شوند (graceful).
            auto_verify_session_id: Optional[int] = None
            auto_verify_project_id: Optional[str] = None
            try:
                auto_verify_project_id = _resolve_inspector_project_id(task, watched)
                auto_verify_session_id = await _create_auto_verify_inspector_session(
                    task=task, watched=watched,
                )
            except Exception as _se:
                logger.debug(f"auto-verify session create failed: {_se}")

            # 🛡 (critical fix) — `run_probes_for_task` فقط `task.acceptance_criteria`
            # را می‌خواند. اگر آن خالی باشد و AC از پرامپت extract شده باشد، probe
            # هرگز fire نمی‌شود. به جای آن، از run_probes_for_acs استفاده می‌کنیم
            # که مستقیماً لیست AC را می‌گیرد.
            from .verify_runtime import run_probes_for_acs, build_probe_context
            _probe_ctx = build_probe_context(
                task_id=str(task.id),
                run_id=runtime_run_id,
                repo_path=(
                    getattr(watched, "runtime_repo_path", None) if watched else None
                ),
                frontend_base_url=(
                    getattr(watched, "frontend_base_url", None) if watched else None
                ),
                backend_base_url=(
                    getattr(watched, "backend_base_url", None) if watched else None
                ),
                auth_type=(
                    (getattr(watched, "runtime_auth", None) or {}).get("type")
                    if watched else None
                ),
                auth_value=(
                    (getattr(watched, "runtime_auth", None) or {}).get("value")
                    if watched else None
                ),
                evidence_dir=str(run_dir),
                inspector_session_id=auto_verify_session_id,
                verify_model_id=model_id,
                watched_id=str(watched.id) if watched else None,
            )
            # 🔐 (Phase 3) — اگر watched recipe دارد، storage_state بگیر/تازه کن
            # و در ProbeContext بگذار تا probe ها به صفحات با لاگین دسترسی
            # داشته باشند. شکست در این مرحله probe را block نمی‌کند — فقط
            # بدون auth ادامه می‌دهیم.
            try:
                if watched and getattr(watched, "runtime_auth_recipe", None):
                    from .verify_runtime.auth_runner import (
                        obtain_or_refresh_storage_state,
                    )
                    _auth_state = await obtain_or_refresh_storage_state(watched)
                    if _auth_state:
                        _probe_ctx.storage_state = _auth_state
                        if auto_verify_session_id:
                            try:
                                from .verify_runtime.inspector_probe import _msg as _ip_msg
                                await _ip_msg(
                                    auto_verify_session_id, "system",
                                    "🔐 auth recipe اجرا شد — storage_state آماده",
                                )
                            except Exception:
                                pass
                    else:
                        if auto_verify_session_id:
                            try:
                                from .verify_runtime.inspector_probe import _msg as _ip_msg
                                await _ip_msg(
                                    auto_verify_session_id, "system",
                                    "⚠️ auth recipe در دسترس نیست یا شکست خورد — "
                                    "probe ها بدون لاگین ادامه می‌دهند",
                                )
                            except Exception:
                                pass
            except Exception as _aue:
                logger.warning(f"auth_runner integration failed: {_aue}")

            runtime_probe_results = await run_probes_for_acs(
                acceptance_criteria, _probe_ctx,
            )

            # 🆕 (Phase 4) — Task type classification
            # تعیین می‌کند کدام Phase 4 probe ها روی این تسک اجرا شوند.
            task_type = "unknown"
            try:
                task_type = _classify_task_type(task)
                if auto_verify_session_id:
                    try:
                        from .verify_runtime.inspector_probe import _msg as _ip_msg
                        await _ip_msg(
                            auto_verify_session_id, "system",
                            f"🏷 task_type classified as: {task_type}",
                        )
                    except Exception:
                        pass
            except Exception as _cte:
                logger.debug(f"task_type classify failed: {_cte}")

            # 🆕 (Phase 4) — Code-aware Verifier per AC (همیشه برای task
            # هایی که حداقل یک AC و repo دارند اجرا می‌شود — مستقل از type)
            code_probe_results: List[Any] = []
            # (step_code_verdicts بالا، در scope تابع، تعریف شده تا
            # هم در prompt verifier و هم در post-AI override در دسترس باشد)
            try:
                if (acceptance_criteria or task.task_steps) and watched and getattr(watched, "repo_full_name", None):
                    from .verify_runtime.code_aware_verifier import (
                        analyze_acs_with_commit_diffs,
                    )
                    from .verify_runtime.base import (
                        RuntimeProbeResult as _RPR,
                        PROBE_STATUS_PASSED as _PASSED,
                        PROBE_STATUS_FAILED as _FAILED,
                        PROBE_STATUS_SKIPPED as _SKIPPED,
                    )
                    _token = get_github_token()
                    if _token:
                        # 1) acceptance_criteria کلی
                        # 🆕 (Bug C6 v6) cap از 10 به 200 (هماهنگ با
                        # _MAX_TOTAL_ACS) — task های با AC های زیاد
                        # نباید AC های بعد از 10ام را از code-aware
                        # محروم کنند.
                        if acceptance_criteria:
                            _code_analysis = await analyze_acs_with_commit_diffs(
                                task=task,
                                acs=list(acceptance_criteria)[:200],
                                repo_full_name=watched.repo_full_name,
                                token=_token,
                                verify_model_id=model_id,
                            )
                            _verdict_to_status = {
                                "implemented": _PASSED,
                                "partial": _FAILED,
                                "not_found": _FAILED,
                                "unclear": _SKIPPED,
                            }
                            for _ca in _code_analysis:
                                _ca_idx = _ca.get("ac_index", 0)
                                _ca_verdict = _ca.get("code_verdict", "unclear")
                                _ca_status = _verdict_to_status.get(_ca_verdict, _SKIPPED)
                                code_probe_results.append(_RPR(
                                    ac_id=f"code_ac{_ca_idx}",
                                    ac_text=_ca.get("ac_text", ""),
                                    method="code_analysis",
                                    status=_ca_status,
                                    evidence={
                                        "code_verdict": _ca_verdict,
                                        "matching_commits": _ca.get("matching_commits", []),
                                        "key_changes": _ca.get("key_changes", []),
                                        "reason": _ca.get("reason", ""),
                                        "probe_type": "code_aware_phase4",
                                    },
                                    duration_ms=0,
                                ))

                        # 2) task_steps — حیاتی برای checklist
                        # هر task_step را به‌عنوان یک AC در نظر می‌گیریم
                        # 🆕 (Bug C6 v6) cap از 40 به 200 → task های meta با
                        # ۵۲+ step (مثل meta-test verify v6) همه step ها
                        # code-aware می‌گیرند و programmatic-upgrade می‌توانند
                        # داشته باشند. code_aware_verifier داخل خودش batching
                        # می‌کند (هر batch ≤10 AC، تعداد batch ها بدون cap).
                        _steps_list = list(task.task_steps or [])
                        if _steps_list:
                            _step_acs = [
                                {
                                    "text": (
                                        f"{s.get('title', '')} — "
                                        f"{s.get('scope', '')[:300]}"
                                    ).strip(),
                                    "_step_id": s.get("id", i + 1),
                                }
                                for i, s in enumerate(_steps_list[:200])
                                if isinstance(s, dict)
                            ]
                            if _step_acs:
                                _steps_analysis = await analyze_acs_with_commit_diffs(
                                    task=task,
                                    acs=_step_acs,
                                    repo_full_name=watched.repo_full_name,
                                    token=_token,
                                    verify_model_id=model_id,
                                )
                                for _i, _sa in enumerate(_steps_analysis):
                                    _step_id = (
                                        _step_acs[_i].get("_step_id")
                                        if _i < len(_step_acs) else None
                                    )
                                    if _step_id is None:
                                        continue
                                    # 🆕 (Phase 5 — bug 4 fix) — Wiring Check:
                                    # کد existence ≠ کد wired into pipeline. اگر
                                    # target_file وجود دارد ولی هیچ فایل دیگری
                                    # آن را import نمی‌کند (یا فقط __init__.py)،
                                    # implementation orphan است. downgrade به
                                    # "partial" با reason صریح تا verify
                                    # false-positive ندهد.
                                    _ca_verdict_raw = _sa.get("code_verdict", "unclear")
                                    _ca_reason_raw = _sa.get("reason", "")
                                    # 🆕 (bug 36) — wiring_check downgrade
                                    # غیرفعال شد. علت: file_contents در
                                    # verify فقط شامل target_files است (نه
                                    # importer ها). برای meta-task هایی که
                                    # target_files همگی در یک package هستند،
                                    # هیچ importer در view نیست → wiring_check
                                    # همه را orphan اعلام می‌کرد و downgrade
                                    # می‌داد. bug 35 یک guard نرم اضافه کرد
                                    # ولی شرایطش در عمل تقریباً همیشه
                                    # برآورده می‌شود (هر .py دارای "import ").
                                    # برای verify، اعتماد به code-aware
                                    # کافی است؛ wiring فقط برای deep_scan
                                    # که corpus کامل دارد، معنا دارد.
                                    if False and _ca_verdict_raw == "implemented":
                                        try:
                                            _step_text = _step_acs[_i].get("text", "")
                                            _wiring_status = _check_file_wiring(
                                                step_text=_step_text,
                                                target_files=list(task.target_files or []),
                                                file_contents=file_contents,
                                                repo_tree=repo_tree,
                                            )
                                            if _wiring_status["status"] == "orphan":
                                                _ca_verdict_raw = "partial"
                                                _ca_reason_raw = (
                                                    f"⚠️ wiring-check: "
                                                    f"{_wiring_status['detail']} — "
                                                    f"کد ساخته شده ولی integration ناقص. "
                                                    f"اصلی: {_ca_reason_raw[:150]}"
                                                )
                                        except Exception as _wce:
                                            logger.debug(f"wiring_check failed: {_wce}")
                                    step_code_verdicts[int(_step_id)] = {
                                        "verdict": _ca_verdict_raw,
                                        "reason": _ca_reason_raw,
                                        "matching_commits": _sa.get("matching_commits", [])[:3],
                                        "key_changes": _sa.get("key_changes", [])[:3],
                                    }
                        if auto_verify_session_id:
                            try:
                                from .verify_runtime.inspector_probe import _msg as _ip_msg
                                _summary = (
                                    f"🔍 code-aware: {len(code_probe_results)} AC analyzed "
                                    f"({sum(1 for r in code_probe_results if r.status == _PASSED)}p / "
                                    f"{sum(1 for r in code_probe_results if r.status == _FAILED)}f / "
                                    f"{sum(1 for r in code_probe_results if r.status == _SKIPPED)}s)"
                                )
                                if step_code_verdicts:
                                    _step_imp = sum(
                                        1 for v in step_code_verdicts.values()
                                        if v.get("verdict") == "implemented"
                                    )
                                    _summary += (
                                        f" + steps: {_step_imp}/{len(step_code_verdicts)} implemented"
                                    )
                                await _ip_msg(auto_verify_session_id, "system", _summary)
                            except Exception:
                                pass
            except Exception as _cae:
                logger.debug(f"code_aware_verifier failed: {_cae}")

            # 🆕 (Phase 4) — Backend Log Probe برای AC های backend-flavor
            # فقط اگر task_type in (backend, mixed, unknown)
            backend_log_probe_results: List[Any] = []
            _bp_diag = {
                "total_acs": 0, "skipped_ui": 0, "skipped_no_signal": 0,
                "ran": 0, "task_type_ok": False, "block_exception": None,
            }
            try:
                _bp_diag["task_type_ok"] = task_type in ("backend", "mixed", "unknown")
                if _bp_diag["task_type_ok"] and acceptance_criteria:
                    from .verify_runtime.backend_log_probe import run_backend_log_probe
                    from .verify_runtime.backend_log_probe import (
                        _extract_endpoints_from_text, _extract_python_symbols,
                    )
                    # 🆕 (Phase 4 fix) — signal extraction از کل task context
                    # نه فقط ac.text. AC های کلی (مثل "تست‌ها بدون خطا") در
                    # متن خود endpoint ندارند ولی task_steps + target_files
                    # دارند، پس از همان full context decision می‌گیریم.
                    _task_context_text = (
                        (task.title or "") + " "
                        + " ".join(
                            f"{s.get('title', '')} {s.get('scope', '')}"
                            for s in (task.task_steps or [])
                            if isinstance(s, dict)
                        ) + " "
                        + " ".join(str(f) for f in (task.target_files or []))
                    )
                    _task_eps = _extract_endpoints_from_text(_task_context_text)
                    _task_syms = _extract_python_symbols(_task_context_text)
                    _task_has_backend_signal = bool(_task_eps or _task_syms)

                    _bp_diag["total_acs"] = len(acceptance_criteria)
                    _bp_count = 0
                    for _ac_idx, _ac in enumerate(acceptance_criteria):
                        if _bp_count >= 5:
                            break
                        _ac_text = (
                            _ac.get("text") if isinstance(_ac, dict) else str(_ac)
                        ) or ""
                        _ac_method = (
                            _ac.get("verify_method") if isinstance(_ac, dict) else "static"
                        ) or ""
                        if str(_ac_method).lower() == "ui_interaction":
                            _bp_diag["skipped_ui"] += 1
                            continue
                        # signal یا در ac.text، یا در task context کلی
                        _eps = _extract_endpoints_from_text(_ac_text)
                        _syms = _extract_python_symbols(_ac_text)
                        if not _eps and not _syms and not _task_has_backend_signal:
                            _bp_diag["skipped_no_signal"] += 1
                            continue
                        _bp_res = await run_backend_log_probe(
                            _ac if isinstance(_ac, dict) else {"text": _ac_text},
                            _probe_ctx, f"blp_ac{_ac_idx}", task,
                        )
                        if _bp_res is not None:
                            backend_log_probe_results.append(_bp_res)
                            _bp_count += 1
                            _bp_diag["ran"] += 1
            except Exception as _ble:
                _bp_diag["block_exception"] = f"{type(_ble).__name__}: {str(_ble)[:120]}"
                logger.debug(f"backend_log_probe block failed: {_ble}")
            # 🆕 (Phase 4 fix) — همیشه diagnostic بفرست تا اگر probe ها
            # ظاهر نشدند، علتش روشن باشد (no logs / no signal / ui only)
            if auto_verify_session_id:
                try:
                    from .verify_runtime.inspector_probe import _msg as _ip_msg
                    if not _bp_diag["task_type_ok"]:
                        await _ip_msg(
                            auto_verify_session_id, "system",
                            f"📊 backend-log: skipped (task_type={task_type} نیازی نبود)",
                        )
                    elif _bp_diag["block_exception"]:
                        await _ip_msg(
                            auto_verify_session_id, "system",
                            f"📊 backend-log: ⚠️ exception: {_bp_diag['block_exception']}",
                        )
                    elif _bp_diag["ran"] > 0:
                        _verdicts = [
                            (r.evidence or {}).get("verdict", "?")
                            for r in backend_log_probe_results
                        ]
                        await _ip_msg(
                            auto_verify_session_id, "system",
                            f"📊 backend-log: {_bp_diag['ran']} AC analyzed — "
                            f"verdicts={_verdicts} "
                            f"(skipped: {_bp_diag['skipped_ui']} ui, "
                            f"{_bp_diag['skipped_no_signal']} no-signal)",
                        )
                    else:
                        await _ip_msg(
                            auto_verify_session_id, "system",
                            f"📊 backend-log: 0 probes ran — "
                            f"total_acs={_bp_diag['total_acs']}, "
                            f"skipped_ui={_bp_diag['skipped_ui']}, "
                            f"skipped_no_signal={_bp_diag['skipped_no_signal']}",
                        )
                except Exception:
                    pass

            # 🔬 (inspector_probe Phase 2 — per-step probes) — اگر تسک
            # task_steps دارد، برای هر مرحله یک probe جداگانه با route
            # مرتبط با همان مرحله اجرا کن. این probe ها prepend به
            # runtime_probe_results می‌شوند تا در گزارش بالای بقیه ظاهر شوند.
            step_probe_results: List[Any] = []
            try:
                _ts_list = list(task.task_steps or [])
                if _ts_list and _probe_ctx.frontend_base_url:
                    from .verify_runtime.inspector_probe import (
                        run_inspector_probe as _run_step_probe,
                    )
                    # 🆕 (Phase 3 fix) — برای هر step، AC مشابه را با شباهت
                    # متنی پیدا کن و plan غنی آن را استفاده کن (به‌جای
                    # navigate-only). این کاری می‌کند action loop واقعاً
                    # برای step probes هم فعال شود.
                    _all_acs = list(task.acceptance_criteria or [])

                    def _ac_text_low(_a: Any) -> str:
                        if isinstance(_a, dict):
                            return str(_a.get("text") or "").lower()
                        return str(_a or "").lower()

                    def _find_matching_ac(_step_title: str, _step_scope: str) -> Optional[Dict[str, Any]]:
                        """بهترین AC با ui_interaction plan را برای این step پیدا کن."""
                        _title_low = (_step_title or "").lower()
                        _scope_low = (_step_scope or "").lower()
                        _step_tokens = set(
                            tok for tok in (_title_low + " " + _scope_low).split()
                            if len(tok) >= 4
                        )
                        if not _step_tokens:
                            return None
                        _best: Optional[Dict[str, Any]] = None
                        _best_score = 0
                        for _ac in _all_acs:
                            if not isinstance(_ac, dict):
                                continue
                            if str(_ac.get("verify_method") or "").lower() != "ui_interaction":
                                continue
                            _plan = _ac.get("verify_plan") or {}
                            _steps = _plan.get("ui_steps") or []
                            # فقط plan های با حداقل ۲ step غیر-navigate
                            _real = sum(
                                1 for s in _steps if isinstance(s, dict)
                                and str(s.get("action") or "").lower() not in ("", "navigate", "screenshot")
                            ) if isinstance(_steps, list) else 0
                            if _real < 2:
                                continue
                            _ac_low = _ac_text_low(_ac)
                            _ac_tokens = set(
                                tok for tok in _ac_low.split() if len(tok) >= 4
                            )
                            _score = len(_step_tokens & _ac_tokens)
                            if _score > _best_score:
                                _best_score = _score
                                _best = _ac
                        # حداقل ۲ token مشترک تا match قابل اعتماد باشد
                        if _best is not None and _best_score >= 2:
                            return _best
                        return None

                    # 🆕 (bug 33) — per-step classifier: اگر step فقط backend
                    # است (مثل «Schema migration در OversightTask»)، UI probe
                    # اصلاً اجرا نشود چون feature روی UI نیست و vision قطعاً
                    # «feature missing» خواهد گفت. در عوض همان step را برای
                    # backend_log_probe می‌فرستیم.
                    def _classify_step_for_probe(step: Dict[str, Any]) -> str:
                        """Returns: 'ui_eligible' | 'backend_only'"""
                        _scope_low = str(step.get("scope") or "").lower()
                        _title_low = str(step.get("title") or "").lower()
                        _combined = _scope_low + " " + _title_low
                        _ui_hits = sum(1 for kw in _UI_KEYWORDS if kw in _combined)
                        _be_hits = sum(1 for kw in _BACKEND_KEYWORDS if kw in _combined)
                        # کلمات backend-specific (Schema migration, dataclass, AST,
                        # subprocess, ...) که قطعاً UI ندارند
                        _strong_backend_terms = (
                            "schema migration", "dataclass", "ast parse",
                            "subprocess", "asyncio", "pytest", "import graph",
                            "background task", "scheduler", "thread",
                            "system prompt", "ai prompt", "@router",
                            "fastapi", "pydantic", "sqlalchemy",
                        )
                        _strong_be = any(t in _combined for t in _strong_backend_terms)
                        if _strong_be and _ui_hits == 0:
                            return "backend_only"
                        if _be_hits >= 2 and _ui_hits == 0:
                            return "backend_only"
                        return "ui_eligible"

                    # حداکثر ۱۲ مرحله — متناسب با cap چک‌لیست ۳۰ که هرکدام
                    # ~1 دقیقه طول می‌کشد، 12 → ~12 دقیقه عمر مفید برای probe
                    for _step in _ts_list[:12]:
                        try:
                            _smart_nav_result: Optional[Dict[str, Any]] = None
                            _sroute, _route_specific = _infer_route_for_step(_step, task)
                            _sid = _step.get("id", 0)
                            _stitle = str(_step.get("title") or "")[:80]
                            _sscope = str(_step.get("scope") or "")[:200]
                            # 🆕 (bug 33) — backend-only step → skip UI probe
                            _step_class = _classify_step_for_probe(_step)
                            if _step_class == "backend_only":
                                if auto_verify_session_id:
                                    try:
                                        from .verify_runtime.inspector_probe import _msg as _ip_msg
                                        await _ip_msg(
                                            auto_verify_session_id, "system",
                                            f"⏭ step #{_sid} ({_stitle[:50]}) → backend-only "
                                            f"(UI probe skipped — code-aware + backend-log کافی است)",
                                        )
                                    except Exception:
                                        pass
                                # یک probe result با status=skipped می‌سازیم تا
                                # در bundle مشخص باشد (و verify درست محاسبه کند)
                                from .verify_runtime.base import (
                                    RuntimeProbeResult, PROBE_STATUS_SKIPPED,
                                )
                                runtime_probe_results.append(
                                    RuntimeProbeResult(
                                        ac_id=f"step_{_sid}",
                                        ac_text=f"(step probe #{_sid}) {_stitle}",
                                        method="ui_interaction",
                                        status=PROBE_STATUS_SKIPPED,
                                        evidence={
                                            "skip_reason": "backend_only — UI probe دور زده شد",
                                            "step_id": _sid,
                                            "step_title": _stitle,
                                            "probe_type": "skipped_backend_only",
                                        },
                                        duration_ms=0,
                                        error_message=None,
                                    )
                                )
                                continue

                            # 🆕 (Phase 4 fix) — Smart Navigation همیشه قبل
                            # از matched-AC check اجرا شود، تا حتی AC هایی که
                            # match می‌شوند ولی route آنها generic است،
                            # بتوانند از nav menu لینک واقعی بگیرند.
                            if not _route_specific and _probe_ctx.frontend_base_url:
                                try:
                                    from .verify_runtime.navigation_helper import (
                                        try_smart_navigation_for_step,
                                    )
                                    _smart_nav_result = await try_smart_navigation_for_step(
                                        ac_text=f"{_stitle}\n{_sscope}",
                                        base_url=_probe_ctx.frontend_base_url or "",
                                        storage_state=_probe_ctx.storage_state,
                                        verify_model_id=_probe_ctx.verify_model_id,
                                    )
                                    _sn_conf = (_smart_nav_result or {}).get("confidence", "?")
                                    _sn_links = (_smart_nav_result or {}).get("links_count", 0)
                                    if _smart_nav_result and _smart_nav_result.get("href"):
                                        _sroute = _smart_nav_result["href"]
                                        _route_specific = True
                                        if auto_verify_session_id:
                                            try:
                                                from .verify_runtime.inspector_probe import _msg as _ip_msg
                                                await _ip_msg(
                                                    auto_verify_session_id, "system",
                                                    f"🧭 smart-nav step #{_sid}: AI لینک «{_smart_nav_result.get('chosen_text', '')[:40]}» "
                                                    f"→ {_sroute} (confidence={_sn_conf}, links={_sn_links})",
                                                )
                                            except Exception:
                                                pass
                                    else:
                                        if auto_verify_session_id:
                                            try:
                                                from .verify_runtime.inspector_probe import _msg as _ip_msg
                                                await _ip_msg(
                                                    auto_verify_session_id, "system",
                                                    f"🧭 smart-nav step #{_sid}: no match "
                                                    f"(confidence={_sn_conf}, links_scanned={_sn_links}, "
                                                    f"reason={str((_smart_nav_result or {}).get('reason', ''))[:120]})",
                                                )
                                            except Exception:
                                                pass
                                except Exception as _snerr:
                                    logger.debug(f"smart_nav failed: {_snerr}")

                            # 🆕 (Phase 3 fix) — به‌جای plan navigate-only،
                            # plan AC مشابه را اگر هست استفاده کن
                            _matched_ac = _find_matching_ac(_stitle, _sscope)
                            if _matched_ac is not None:
                                _matched_plan = dict(_matched_ac.get("verify_plan") or {})
                                # مطمئن شو navigate به route step اشاره دارد
                                _existing_steps = _matched_plan.get("ui_steps") or []
                                # اگر اولین step navigate نبود، یکی اضافه کن
                                if (not _existing_steps
                                    or not isinstance(_existing_steps[0], dict)
                                    or str(_existing_steps[0].get("action") or "") != "navigate"):
                                    _existing_steps = (
                                        [{"action": "navigate", "url": _sroute}]
                                        + list(_existing_steps)
                                    )
                                _matched_plan["ui_steps"] = _existing_steps
                                _matched_plan["base"] = "frontend"
                                _matched_plan["step_id"] = _sid
                                _matched_plan["step_title"] = _stitle
                                _matched_plan["step_scope"] = _sscope
                                _matched_plan["_recipe_source"] = "matched_ac"
                                _synth_ac = {
                                    "text": f"(step probe #{_sid}) {_stitle}",
                                    "verify_method": "ui_interaction",
                                    "verify_plan": _matched_plan,
                                }
                            else:
                                # 🆕 (Phase 3 final fix) — اگر route خاصی پیدا
                                # نکردیم (به / fallback شده) و هیچ matched AC
                                # هم نداریم و smart_nav هم (که بالاتر اجرا شد)
                                # نتوانست، یعنی واقعاً نمی‌توانیم این step را
                                # با اطمینان probe کنیم.
                                if not _route_specific:
                                    # ساخت یک synthetic skipped result بدون
                                    # واقعاً اجرای probe
                                    from .verify_runtime.base import (
                                        RuntimeProbeResult, PROBE_STATUS_SKIPPED,
                                    )
                                    _step_res = RuntimeProbeResult(
                                        ac_id=f"step_{_sid}",
                                        ac_text=f"(step probe #{_sid}) {_stitle}",
                                        method="ui_interaction",
                                        status=PROBE_STATUS_SKIPPED,
                                        evidence={
                                            "inspector_session_id": _probe_ctx.inspector_session_id,
                                            "reason": "نتوانست route خاص برای این step پیدا کند",
                                            "step_id": _sid,
                                            "step_title": _stitle,
                                            "step_inferred_route": _sroute,
                                            "_recipe_source": "skipped_no_route",
                                            "probe_type": "inspector_phase3",
                                        },
                                        duration_ms=0,
                                    )
                                    step_probe_results.append(_step_res)
                                    if auto_verify_session_id:
                                        try:
                                            from .verify_runtime.inspector_probe import _msg as _ip_msg
                                            await _ip_msg(
                                                auto_verify_session_id, "system",
                                                f"⏭ step #{_sid} skipped — route خاصی پیدا نشد",
                                            )
                                        except Exception:
                                            pass
                                    continue  # بریم step بعدی
                                _synth_ac = {
                                    "text": f"(step probe #{_sid}) {_stitle}",
                                    "verify_method": "ui_interaction",
                                    "verify_plan": {
                                        "base": "frontend",
                                        "ui_steps": [
                                            {"action": "navigate", "url": _sroute},
                                        ],
                                        "step_id": _sid,
                                        "step_title": _stitle,
                                        "step_scope": _sscope,
                                        "_recipe_source": "fallback_navigate",
                                    },
                                }
                            _step_res = await _run_step_probe(
                                _synth_ac, _probe_ctx, f"step_{_sid}",
                            )
                            if _step_res is not None:
                                if isinstance(_step_res.evidence, dict):
                                    _step_res.evidence["step_id"] = _sid
                                    _step_res.evidence["step_title"] = _stitle
                                    _step_res.evidence["step_inferred_route"] = _sroute
                                    # 🆕 (Phase 4) — اگر smart_nav موفق بود،
                                    # تصمیم AI را به evidence اضافه کن
                                    if _smart_nav_result and _smart_nav_result.get("href"):
                                        _step_res.evidence["smart_nav"] = {
                                            "chosen_text": _smart_nav_result.get("chosen_text"),
                                            "chosen_href": _smart_nav_result.get("href"),
                                            "confidence": _smart_nav_result.get("confidence"),
                                            "reason": _smart_nav_result.get("reason"),
                                            "links_count": _smart_nav_result.get("links_count"),
                                            "duration_ms": _smart_nav_result.get("duration_ms"),
                                        }
                                step_probe_results.append(_step_res)
                        except Exception as _ssee:
                            logger.debug(
                                f"step probe #{_step.get('id', '?')} failed: {_ssee}"
                            )
            except Exception as _se_outer:
                logger.debug(f"per-step probes block failed: {_se_outer}")

            # 🔬 (inspector_probe Phase 1 — system check) — مستقل از AC ها،
            # یک probe «صفحه مرتبط با تسک» اجرا شود تا اگر هیچ AC نوع ui_interaction
            # نبود، هم گزارش screenshot/vision/console/backend log از صفحه‌ای
            # که واقعاً به تسک ربط دارد داشته باشیم. این probe synthetic است و
            # در task.acceptance_criteria ذخیره نمی‌شود.
            try:
                if _probe_ctx.frontend_base_url:
                    from .verify_runtime.inspector_probe import (
                        run_inspector_probe as _run_sys_probe,
                    )
                    # تلاش برای استخراج route مرتبط با تسک از target_files
                    _route = _infer_frontend_route_for_task(task)
                    _sys_ac_text = (
                        f"(auto-verify system probe) صفحه‌ی «{_route}» قابل دسترسی است"
                        if _route != "/" else
                        "(auto-verify system probe) صفحه اصلی deployed قابل دسترسی است"
                    )
                    _sys_ac = {
                        "text": _sys_ac_text,
                        "verify_method": "ui_interaction",
                        "verify_plan": {
                            "base": "frontend",
                            "ui_steps": [{"action": "navigate", "url": _route}],
                        },
                    }
                    _sys_res = await _run_sys_probe(_sys_ac, _probe_ctx, "system_home")
                    if _sys_res is not None:
                        # prepend تا در گزارش بالای لیست probe ها ظاهر شود
                        runtime_probe_results.insert(0, _sys_res)
                else:
                    logger.debug("system inspector probe skipped: no frontend_base_url")
            except Exception as _spe:
                logger.debug(f"system inspector probe failed: {_spe}")

            # 🔬 (inspector_probe Phase 2) — ادغام step probes:
            # ترتیب نهایی: [system_probe, step_probe_1..N, AC_probe_1..M]
            # system probe (اگر هست) در index 0 می‌ماند، step probes بعد آن
            # و قبل از AC probes می‌آیند.
            if step_probe_results:
                _has_system = bool(
                    runtime_probe_results
                    and isinstance(runtime_probe_results[0].evidence, dict)
                    and runtime_probe_results[0].ac_id == "system_home"
                )
                _insert_at = 1 if _has_system else 0
                for _idx, _spr in enumerate(step_probe_results):
                    runtime_probe_results.insert(_insert_at + _idx, _spr)

            # 🆕 (Phase 4) — append code_aware + backend_log probe results
            # بعد از همه‌ی probe های UI، نتایج تحلیل کد و log را اضافه کن.
            if code_probe_results:
                runtime_probe_results.extend(code_probe_results)
            if backend_log_probe_results:
                runtime_probe_results.extend(backend_log_probe_results)

            # manifest.json + size cap enforcement
            try:
                from .verify_runtime.storage import enforce_size_cap
                # size cap قبل از manifest، تا اگر حذف شد، manifest تازه باشد
                _cap = enforce_size_cap(run_dir)
                if _cap.get("compressed") or _cap.get("deleted"):
                    logger.info(
                        f"verify {task.id}: size cap — "
                        f"compressed={_cap.get('compressed')}, deleted={_cap.get('deleted')}, "
                        f"{_cap.get('initial_bytes')}b → {_cap.get('final_bytes')}b"
                    )
                write_manifest(
                    run_dir,
                    task_id=str(task.id),
                    run_id=runtime_run_id,
                    probe_results=[r.to_dict() for r in runtime_probe_results],
                    started_at=runtime_started_at,
                    finished_at=now_iso(),
                )
                cleanup_old_runs(_Path(STORAGE_DIR), str(task.id), keep=5)
            except Exception as _me:
                logger.debug(f"manifest write/cleanup failed: {_me}")
            if runtime_probe_results:
                rt_lines = [
                    "# 🔬 شواهد Runtime (probe های اجرا شده)",
                    "",
                    "**این شواهد دقیق‌تر از تحلیل کد است.** اگر probe می‌گوید passed،",
                    "بسیار محتمل است AC done باشد. اگر probe می‌گوید failed، AC nicht done است.",
                    "",
                ]
                for r in runtime_probe_results:
                    # 🆕 (Phase 2) — تشخیص step probe و header مخصوص
                    _is_step = isinstance(r.evidence, dict) and r.evidence.get("step_id")
                    _is_system = (r.ac_id == "system_home")
                    if _is_step:
                        rt_lines.append(
                            f"### 🪜 [step #{r.evidence.get('step_id')}] "
                            f"{r.evidence.get('step_title', '')} — {r.status}"
                            f" (route={r.evidence.get('step_inferred_route', '')})"
                        )
                    elif _is_system:
                        rt_lines.append(f"### 🏠 [system probe] — {r.status}")
                    else:
                        rt_lines.append(f"### {r.summary()}")
                    rt_lines.append(f"  - AC: «{r.ac_text[:200]}»")
                    if r.evidence:
                        # خلاصهٔ شواهد — حذف فیلدهای حجیم/بی‌فایده برای AI
                        ev = {k: v for k, v in r.evidence.items()
                              if k not in (
                                  "step_results", "screenshots",
                                  "stdout_excerpt", "stderr_excerpt",
                                  "network_calls",  # حجیم — backend_urls_called کافیست
                              )}
                        # vision را در یک خط جدا برای خوانایی بهتر AI
                        _shots = r.evidence.get("screenshots") or []
                        if isinstance(_shots, list):
                            for _s in _shots:
                                if isinstance(_s, dict) and _s.get("vision_description"):
                                    rt_lines.append(
                                        f"  - 👁 vision ({_s.get('label', 'screenshot')}): "
                                        f"{str(_s['vision_description'])[:500]}"
                                    )
                        if ev:
                            rt_lines.append(f"  - evidence: {ev}")
                    rt_lines.append("")
                    # override hint برای AI — برای step probe، در sets جدا
                    if _is_step:
                        # step probes را به آن AC که در remaining است map نکن
                        # (شواهد runtime نباید AI را گیج کند)
                        pass
                    elif r.status == "passed":
                        runtime_override_hints[r.ac_text[:200]] = "passed"
                    elif r.status == "failed":
                        runtime_override_hints[r.ac_text[:200]] = "failed"
                runtime_evidence_blob = "\n".join(rt_lines)
                runtime_status_note = (
                    f"ran ({len(runtime_probe_results)} probes: "
                    f"{sum(1 for r in runtime_probe_results if r.status == 'passed')}p/"
                    f"{sum(1 for r in runtime_probe_results if r.status == 'failed')}f/"
                    f"{sum(1 for r in runtime_probe_results if r.status == 'skipped')}s/"
                    f"{sum(1 for r in runtime_probe_results if r.status == 'error')}e)"
                )
                logger.info(
                    f"verify {task.id}: runtime probes ran — "
                    f"{sum(1 for r in runtime_probe_results if r.status == 'passed')} passed, "
                    f"{sum(1 for r in runtime_probe_results if r.status == 'failed')} failed, "
                    f"{sum(1 for r in runtime_probe_results if r.status == 'skipped')} skipped, "
                    f"{sum(1 for r in runtime_probe_results if r.status == 'error')} errors"
                )
    except Exception as _re:
        logger.warning(f"runtime probes block failed: {_re}", exc_info=False)
        runtime_probe_results = []
        runtime_evidence_blob = ""
    finally:
        # 🔬 (inspector_probe Phase 1) — session را archive کن (silent fail)
        try:
            _avs_id = locals().get("auto_verify_session_id")
            if _avs_id is not None:
                await _archive_auto_verify_inspector_session(int(_avs_id))
        except Exception as _ae:
            logger.debug(f"archive auto-verify session failed: {_ae}")

    user_goal = (watched.user_notes if watched else "") or ""

    ac_lines = "\n".join(f"- {_ac_text_of(c)}" for c in acceptance_criteria)

    # 🆕 (Multi-pass Checklist) — اگر تسک task_steps دارد، برای verifier هم
    # checklist می‌سازیم تا هر مرحله را جداگانه ارزیابی کند.
    task_steps_list: List[Dict[str, Any]] = list(task.task_steps or [])
    steps_blob = ""
    steps_json_template = ""
    if task_steps_list:
        steps_lines = [
            "# 📋 چک‌لیست مراحل تسک (مهم — هر مرحله را جداگانه ارزیابی کن)",
            "",
            "تسک به مراحل مشخص تقسیم شده. علاوه بر AC کلی، **برای هر مرحله جداگانه**",
            "وضعیت آن را در `steps_status` خروجی برگردان: `done` (کامل)، `partial`",
            "(ناقص — چیزی باقی مانده)، یا `not_done` (هنوز شروع نشده).",
            "اگر `partial` بود، حتماً در فیلد `remaining` بنویس **چه چیزی هنوز باقی مانده**.",
            "",
        ]
        for s in task_steps_list:
            cur = (s.get("status") or "pending")
            sid_int = int(s.get("id", 0))
            # 🆕 (Phase 4 fix #17) — اگر code_aware verdict برای این step
            # داریم، آن را به‌عنوان "🤖 شواهد ماشینی" کنار توضیح step
            # بگذار تا AI verifier نهایی هنگام تصمیم در checklist از آن
            # استفاده کند.
            _cav = step_code_verdicts.get(sid_int)
            _cav_line = ""
            if _cav:
                _v = _cav.get("verdict", "unclear")
                _emoji = {"implemented": "✅", "partial": "🟡",
                          "not_found": "❌", "unclear": "❓"}.get(_v, "·")
                _commits = _cav.get("matching_commits") or []
                _commits_s = ", ".join(f"`{c}`" for c in _commits[:3])
                _cav_line = (
                    f"\n  🤖 code-aware: {_emoji} `{_v}` "
                    f"— {_cav.get('reason', '')[:200]}"
                    + (f" (commits: {_commits_s})" if _commits else "")
                )
            steps_lines.append(
                f"- **مرحله {s.get('id')}** ({cur}): "
                f"{(s.get('title') or '')[:120]} — "
                f"{(s.get('scope') or '')[:280]}"
                f"{_cav_line}"
            )
        # 🆕 (Phase 4 fix #17) — راهنمای استفاده از code-aware verdicts
        if step_code_verdicts:
            steps_lines.insert(5, (
                "🤖 **شواهد code-aware برای هر step** (در زیر هر مرحله):\n"
                "- اگر verdict = `implemented` → status باید `done` باشد "
                "(مگر شواهد runtime ضد قوی دیدی).\n"
                "- اگر verdict = `partial` → status باید `partial`.\n"
                "- اگر verdict = `not_found` → status `not_done` مگر "
                "خودت در chunks فایل را پیدا کنی.\n"
                "- اگر verdict = `unclear` → بر اساس شواهد دیگر تصمیم بگیر.\n"
                "**هرگز** فقط بر اساس عدم دیدن feature در UI screenshot "
                "نگو not_done — اگر code-aware گفته implemented، صفحه/کد آن "
                "موجود است، شاید در UI دیده نشود (backend internal).\n"
            ))
        steps_blob = "\n".join(steps_lines)
        # ساخت template نمونه (id‌ها واقعی) برای کاهش خطای AI
        sample_ids = [str(s.get("id", i + 1)) for i, s in enumerate(task_steps_list[:3])]
        sample_lines = ",\n    ".join(
            f'{{"id": {sid}, "status": "done|partial|not_done", "completion_pct": 0, "remaining": "...", "evidence": "..."}}'
            for sid in sample_ids
        )
        steps_json_template = (
            ',\n  "steps_status": [\n    '
            + sample_lines
            + (",\n    ..." if len(task_steps_list) > 3 else "")
            + "\n  ]"
        )

    verify_prompt = f"""تو یک QA حرفه‌ای هستی. وظیفه‌ات بررسی این است که آیا کارهای خواسته‌شده در پرامپت تسک واقعاً در وضعیت فعلی پروژه انجام شده‌اند یا نه — **بدون اهمیت دادن به اینکه چه کسی یا با چه ابزاری انجام داده**. فقط وضعیت فعلی را با معیارهای پذیرش مقایسه کن.

# 🧠 اصل ارزیابی (مهم — قبل از تصمیم بخوان)
- **تطابق معنایی، نه literal**: اگر کد به شکل متفاوت ولی **هم‌ارز** نوشته شده — یعنی همان نتیجه را تولید می‌کند، همان رفتار را دارد، همان معیار پذیرش را برآورده می‌کند — این **done** است. نباید بخواهی exactly مطابق پرامپت باشد.
- **نام فایل‌ها/کلاس‌ها/سرویس‌ها مهم نیست — نقش و رفتار مهم است**: اگر پرامپت گفته «فایل `idea.py` بساز» ولی پروژه از `oversight_service.py` با همان نقش (تعریف Idea/Task) استفاده کرده، این **done** است. اگر پرامپت گفته «کلاس `AITaskExecutor` بساز» ولی پروژه از یک سرویس با نام دیگر (مثل `runtime_executor` یا `apply_action`) که **همان کار** را می‌کند استفاده کرده، **done** است. اگر پرامپت گفته «`SmartVerifier`» ولی پروژه از `oversight_verifier` استفاده می‌کند، **done** است. اگر پرامپت گفته «پیاده‌سازی scheduler» ولی پروژه از `background_scheduler` یا منطق scheduling embedded در service دیگری استفاده می‌کند، **done** است.
- **🎯 الگوی Next.js / SPA — بسیار مهم**: اگر پرامپت گفته «کامپوننت `XyzPanel.tsx` یا `XyzForm.tsx` بساز» ولی پروژه از Next.js App Router استفاده می‌کند، تمام آن منطق ممکن است در یک فایل `app/<route>/page.tsx` پیاده شده باشد (نه فایل کامپوننت جدا). این **done** است. به عنوان مثال:
  - پرامپت: «`OversightPanel.tsx` بساز» → پروژه: `frontend/src/app/oversight/page.tsx` با همان UI = **done**
  - پرامپت: «`IdeaForm.tsx` بساز» → پروژه: form ای داخل `app/oversight/page.tsx` که ایده می‌گیرد = **done**
  - پرامپت: «`SettingsPanel.tsx` بساز» → پروژه: `app/settings/page.tsx` = **done**
- **الگوی endpoint اختصاصی vs همگانی**: اگر پرامپت گفته «endpoint `/projects/{id}/ideas` بساز» ولی پروژه از `/oversight/tasks` با field `watched_id` (یا معادل project_id) استفاده می‌کند که **همان کار** را می‌کند، **done** است. تخصیص دقیق path مهم نیست؛ توانایی ثبت ایده با اتصال به پروژه مهم است.
- **قبل از گفتن "فایل/کلاس X وجود ندارد"**: حتماً repo tree (که در ادامه می‌آید) را اسکن کن. به دنبال اسامی similar (با substring، token overlap، یا روی نقش مشترک) بگرد. اگر هر سرویسی با نقش مشابه (executor, verifier, scheduler, validator, ...) موجود است، این بخش done است.
- **هرگز** صرفاً به این دلیل که نام دقیقاً همان چیزی نیست که پرامپت اولیه گفته، not_done نگو. پرامپت اولیه ممکن است نام‌گذاری ideal را پیشنهاد داده باشد، ولی تیم ممکن است معماری متفاوتی انتخاب کرده باشد. **رفتار = done، نه نام**.

# 🔬 روش بررسی (بسیار مهم — قبل از تصمیم بخوان)
**ترتیب اعتماد: 🤖 شواهد ماشینی (بالاترین) > chunk‌های فایل > tree > پرامپت اولیه**

🚨 **قانون طلایی**: اگر «🤖 شواهد ماشینی» (بخش بعدی این پرامپت) برای یک AC
نشان دهد hit‌هایی در فایل‌ها وجود دارد، **پیش‌فرض همان AC done است**. تو
فقط در صورتی می‌توانی not_done بگویی که با خواندن chunk‌ها مطمئن شوی کد
موجود آن AC را برآورده نمی‌کند (نه اینکه نام دقیق نمی‌بینی، بلکه کد رفتار
متفاوتی دارد).

برای هر AC این مراحل را به ترتیب انجام بده:
1. **اول**: نگاه کن به «🤖 شواهد ماشینی» — اگر `verdict_hint = "احتمالاً DONE"`
   با hit‌های قابل توجه (≥2)، **done** بنویس مگر اینکه دلیل قوی برای not_done
   داشته باشی.
2. **دوم**: chunk‌های مربوطه را بخوان — اگر متن یا کد مرتبط یافت کردی
   (متن دکمه، نام تابع، JSX، endpoint، …)، **done** را تأیید کن.
3. **سوم**: اگر هم hit صفر بود و هم در tree نام مرتبط نبود، آنگاه not_done.

❌ **هرگز** این بهانه‌ها برای not_done قابل قبول نیستند:
- "فایل با نام دقیق X.py وجود ندارد" (نام مهم نیست — رفتار مهم است)
- "این کد در فایل دیگری است" (مهم نیست کجاست — مهم وجود دارد یا نه)
- "ساختار با پرامپت اولیه فرق دارد" (پرامپت اولیه فقط پیشنهاد بود)
- "پیاده‌سازی متفاوت از انتظار است" (اگر AC را برآورده می‌کند، done است)

✅ **only valid not_done**: کد در هیچ‌جای repo وجود ندارد و هیچ نشانه‌ای
از آن قابلیت در فایل‌ها/tree/code search نیست. حداقل ۲ بار chunks را
دوباره بررسی کن قبل از گفتن not_done.

**مثال واقعی**:
- AC: «قابلیت کپی پرامپت در UI پیاده‌سازی شده»
- اگر در chunk‌های `page.tsx` متن «📋 کپی پرامپت» یا `onCopyPrompt` یا `navigator.clipboard.writeText` پیدا کردی → **done**
- اگر AC: «فرم ثبت ایده» و chunk‌ها `<textarea`, `setIdea`, `generatePrompt` دارند → **done** (حتی بدون فایل `IdeaForm.tsx`)
- اگر AC: «archive خودکار done‌ها» و chunk‌ها `archived`, `auto-archive`, `setArchived` دارند → **done**
- **اگر کاربر دستی تغییر داد** ولی نتیجه به acceptance criteria رسید → **done**.
- **اگر AI نسخهٔ متفاوت ولی قابل قبول‌تر نوشت** (مثلاً استفاده از pattern مدرن‌تر، error handling بهتر، یا decomposition متفاوت) → **done**.
- فقط زمانی **not_done** بگو که AC ها واقعاً (از نظر رفتاری) برآورده نشده‌اند یا کد رفتار غلط دارد.
- اگر بخشی از AC ها برآورده شده ولی بخشی نه → **partial**.
- اگر تغییرات نسبت به قبل وضع را بدتر کرده → **regressed**.

# 🎯 هدف اصلی پروژه (از زبان کاربر — معیار راهنما)
{user_goal or '(کاربر یادداشتی ثبت نکرده)'}

# تسک
عنوان: {task.title}
نوع: {task.type}
اولویت: {task.priority}
{('سوابق اجرا: این تسک از طریق Inspector apply-action اجرا شده — PR: ' + pr_url + (' (شاخه: ' + pr_branch + ')' if pr_branch else '') + f'. فایل‌های مرتبط از branch `{branch}` خوانده شده‌اند (منبع: {branch_source}).') if pr_url else ('شاخه‌ای که فایل‌ها از آن خوانده شده: `' + branch + '`.')}

پرامپت کامل تسک:
\"\"\"
{task.prompt[:6000]}
\"\"\"

{runtime_evidence_blob}

# معیارهای پذیرش (Acceptance Criteria)
{ac_lines}

{steps_blob}

{machine_evidence_blob}

# محتوای فعلی فایل‌های مرتبط (از repository)
{files_blob[:20000]}

# 🗂 ساختار پروژه (مسیرهای کلیدی repo — برای کشف فایل‌های هم‌نقش)
**این لیست را با دقت اسکن کن قبل از گفتن "فایل وجود ندارد".**
اگر در پرامپت فایل خاصی ذکر شده ولی در «محتوای فعلی فایل‌ها» یافت نشده،
حتماً در این tree دنبال فایل‌های هم‌نقش بگرد. مثال: اگر پرامپت idea.py
خواسته ولی فقط `oversight_service.py` (که مدل Idea را تعریف می‌کند) وجود
دارد، **این done است نه not_done**.

```
{tree_blob[:8000] if tree_blob else '(tree در دسترس نیست — تنها بر اساس فایل‌های ارائه‌شده قضاوت کن)'}
```

# کامیت‌های اخیر
{commits_blob}

# وظیفه
هر معیار پذیرش را جداگانه بررسی کن:
- آیا در وضعیت فعلی پروژه برآورده شده؟ (بله/خیر/تا حدی)

سپس وضعیت کلی را تعیین کن:
- "done" = همهٔ معیارها برآورده شده
- "partial" = بخشی از معیارها برآورده شده
- "not_done" = هیچ تغییر معناداری انجام نشده
- "regressed" = نسبت به قبل بدتر شده
- "error" = در بررسی خطا داشتی

# 📋 قواعد پر کردن done_parts و remaining_parts (بسیار مهم — رعایت کن)
- **done_parts** = فهرست بخش‌های مشخص (نه paragraph) که در وضعیت فعلی repo
  انجام شده‌اند. هر آیتم یک جملهٔ کوتاه (حداکثر 150 کاراکتر). اگر کاری
  انجام نشده، آرایهٔ خالی `[]` بگذار، نه null.
- **remaining_parts** = فهرست بخش‌هایی که هنوز انجام نشده‌اند. هر آیتم
  یک جملهٔ کوتاه (حداکثر 150 کاراکتر). اگر همه انجام شده، `[]` بگذار.
- **هر معیار پذیرش (AC) باید دقیقاً در یکی از این دو لیست منعکس شود** —
  نه هر دو، نه هیچ‌کدام.
- **next_actions** = اگر status="done" نیست، حداقل یک قدم بعدی concrete.
  هر آیتم یک جمله، حداکثر 150 کاراکتر.
- **confidence_score** = عدد بین 0.0 و 1.0 — اگر مطمئن هستی نزدیک 1.0،
  اگر شک داری 0.5-0.7، اگر نمی‌توانی قضاوت کنی زیر 0.3.
- **اگر status="partial"** ولی remaining_parts خالی باشد، در logs ثبت
  می‌شود که AI خطا داشته — باید حتماً remaining_parts را پر کنی.
- 🚨 **قاعدهٔ سازگاری حیاتی (Consistency Rule)**: اگر در `steps_status`
  حتی **یک** مرحله را با `status: "done"` و `remaining: "..."` غیرخالی
  مشخص کردی، **اشتباه است**. یا مرحله را `partial` کن (با remaining
  پر شده)، یا remaining را خالی بگذار (`""`). همچنین اگر `remaining_parts`
  لیست بیرونی هر آیتمی دارد، **حتماً** حداقل یک مرحلهٔ مرتبط در
  `steps_status` نباید `done` باشد. مثال غلط: همهٔ steps `done` ولی
  `remaining_parts` = `["X هنوز اضافه نشده"]` ← این تناقض است و
  سیستم به‌طور خودکار تنزل می‌دهد. مثال درست: اگر چیزی واقعاً باقی
  مانده، آن step را `partial` بگذار و `remaining_parts` را هم پر کن
  با همان آیتم. **این قانون اجرا می‌شود — وگرنه auto-archive بلاک
  می‌شود.**
- **آیتم‌های لیست‌ها فارسی باشند** (مگر نام فایل/کد).
- **محدودیت طول حیاتی برای جلوگیری از truncation**:
  - هر `evidence` در `criteria_results` حداکثر **80 کاراکتر** (فقط نام فایل/تابع کلیدی).
  - هر آیتم `done_parts`/`remaining_parts` حداکثر **140 کاراکتر**.
  - `summary` حداکثر **250 کاراکتر**.
  - **`criteria_results` کاملاً حذف شد** — دیگر آن را در خروجی نگذار. کل اطلاعات معیارها در `done_parts`/`remaining_parts` می‌آید (هر AC یک آیتم در یکی از این دو لیست).
  - **خیلی مهم**: JSON باید کامل (با `}}` نهایی) برگردد و فشرده باشد.

# خروجی فقط JSON (بدون code block markdown — فقط JSON خام)
{{
  "status": "done | partial | not_done | regressed | error",
  "done_parts": ["جملهٔ کوتاه دربارهٔ کار انجام‌شده 1", "..."],
  "remaining_parts": ["جملهٔ کوتاه دربارهٔ کار باقی‌مانده 1", "..."],
  "evidence": {{ "commits": ["sha"], "files": ["path"], "issues": [] }},
  "next_actions": ["قدم بعدی concrete 1", "..."],
  "confidence_score": 0.95,
  "summary": "خلاصه یک‌پاراگرافی"{steps_json_template}
}}"""

    try:
        # 🆕 max_tokens از 7000 به 10000 افزایش — برای task‌هایی با ۱۰+ AC
        # که حتی با محدودیت 80 کاراکتر هر evidence، JSON طولانی می‌شود.
        # همراه با کاهش criteria_results به max 3 (در prompt)، باید کافی باشد.
        response = await service._ai_generate(
            verify_prompt, model_id=model_id, max_tokens=10000, temperature=0.1
        )
        # detection بهبود یافته: اگر هر criterion.evidence به نظر cut شده
        # (مثلاً با کاما تمام نشده، با حرف غیر مرتبط تمام شده)، retry با
        # max_tokens بیشتر و instruction خلاصه‌نویسی
        def _looks_truncated(resp: str) -> bool:
            if not resp or len(resp) < 100:
                return False
            stripped = resp.rstrip()
            # حالت بدیهی: JSON ناتمام
            if not stripped.endswith(("}", "]", "}\n", "]\n")):
                return True
            # حالت ظریف: JSON با } بسته شده ولی string‌های داخلی truncated
            # شاخص: تعداد } و { برابر نیست در نسخهٔ raw
            try:
                opens = stripped.count("{")
                closes = stripped.count("}")
                if opens != closes:
                    return True
            except Exception:
                pass
            return False

        if _looks_truncated(response):
            logger.warning("verify response به نظر truncated است — retry با max_tokens=10000")
            try:
                response = await service._ai_generate(
                    verify_prompt + "\n\n# ⚠️ مهم: evidence هر criterion را حداکثر 100 کاراکتر بنویس تا JSON کامل برگردد.",
                    model_id=model_id,
                    max_tokens=10000,
                    temperature=0.1,
                )
            except Exception:
                pass
    except Exception as e:
        logger.exception("verify ai_generate failed")
        # ذخیرهٔ گزارش error
        report = OversightReport(
            id=str(uuid.uuid4()),
            task_id=task.id,
            watched_id=task.watched_id,
            project_full_name=task.project_full_name,
            run_at=now_iso(),
            status=VERIFICATION_ERROR,
            done_parts=[],
            remaining_parts=[_ac_text_of(c) for c in acceptance_criteria],
            evidence={"error": str(e)},
            next_actions=["تلاش مجدد در دور verify بعدی"],
            confidence_score=0.0,
            raw_response="",
            model_id=model_id or "",
        )
        async with service._lock:
            service.reports.insert(0, report)
            service._save_reports()
            # 🚨 (sweeper loop fix CRITICAL) — task.verification_status باید
            # به یک حالت terminal برسد. اگر در applied_externally_pending_verify
            # بماند، sweeper آن را دوباره و دوباره پیک می‌کند → workflow های
            # cancelled bin می‌شوند (کاربر این loop را گزارش داد). status=error
            # سیگنال صریح به consumer ها می‌دهد که verify خراب شد و باید
            # دستی review شود.
            task.verification_status = "error"
            task.updated_at = now_iso()
            service._save_tasks()
        return {
            "task": task.to_dict(),
            "report": report.to_dict(),
            # 🚨 schema لازم برای _verify_then_chain — اگر این فیلدها نباشند،
            # caller exception می‌خورد یا default های اشتباه می‌گیرد.
            "status_val": "error",
            "final": False,
            "streak": getattr(task, "confirmation_streak", 0),
            "streak_required": 2,
            "followup_available": False,
            "followup_round": getattr(task, "followup_round", 0),
        }

    parsed = service._extract_json(response) or {}
    # 🆕 partial JSON recovery — اگر کل parse fail کرد یا فیلدهای مهم ناقص است،
    # تلاش کن آرایه‌های اصلی (done_parts, remaining_parts, next_actions, status,
    # summary, confidence_score) را مستقیماً با regex extract کنی. این برای
    # مواردی که JSON در criteria_results truncate شد ولی بقیه فیلدها در ابتدای
    # JSON کامل تولید شده‌اند، ضروری است.
    if not parsed or not parsed.get("status"):
        try:
            recovered = _recover_partial_json(response)
            if recovered:
                # merge: parsed مقدم است (اگر JSON کامل بود) ولی recovered fallback
                for k, v in recovered.items():
                    if k not in parsed or not parsed[k]:
                        parsed[k] = v
        except Exception as _e:
            logger.debug(f"partial JSON recovery failed: {_e}")
    # 🆕 (audit) criteria_results دیگر در خروجی expected نیست — اگر AI همچنان
    # تولید کرد، آن را drop کن (چون ممکن است truncated باشد و JSON ناقص نشان
    # دهد). اطلاعات کامل معیارها در done_parts/remaining_parts است.
    if "criteria_results" in parsed:
        del parsed["criteria_results"]
    status_val = parsed.get("status") or VERIFICATION_PARTIAL
    if status_val not in (
        VERIFICATION_DONE,
        VERIFICATION_PARTIAL,
        VERIFICATION_NOT_DONE,
        VERIFICATION_REGRESSED,
        VERIFICATION_ERROR,
    ):
        status_val = VERIFICATION_PARTIAL

    # 🔬 (Runtime Verify Stage 5) — Runtime probe override policy:
    # اگر probe ها نتیجهٔ روشن دادند، نظر AI را override کن. این برای
    # حذف false-positive (AI گفت done ولی runtime fail است) و
    # false-negative (AI گفت not_done ولی runtime pass است) ضروری است.
    if runtime_probe_results:
        runtime_failed = [
            r for r in runtime_probe_results if r.status == "failed"
        ]
        runtime_passed = [
            r for r in runtime_probe_results if r.status == "passed"
        ]
        # اگر ≥۱ probe runtime fail شد و AI گفت done → به partial تنزل
        if runtime_failed and status_val == VERIFICATION_DONE:
            logger.info(
                f"verify {task.id}: AI گفت done ولی {len(runtime_failed)} probe runtime fail شد — "
                f"به partial override می‌کنیم"
            )
            status_val = VERIFICATION_PARTIAL
            # remaining_parts را با AC هایی که runtime fail شدند پر کن
            failed_acs = [r.ac_text for r in runtime_failed]
            existing_remaining = list(parsed.get("remaining_parts") or [])
            for fa in failed_acs:
                if fa and fa not in existing_remaining:
                    existing_remaining.append(fa)
            parsed["remaining_parts"] = existing_remaining[:10]
        # اگر **همهٔ** probe ها runtime pass شدند (با حداقل 1 probe non-skipped
        # و هیچ failed) و AI گفت not_done یا partial → به done ارتقا.
        # این طبق spec: «اگر runtime ✅ ولی AI گفت not_done → AI override کن به done»
        elif (
            len(runtime_passed) >= 1
            and not runtime_failed
            and not any(r.status == "error" for r in runtime_probe_results)
            and status_val in (VERIFICATION_NOT_DONE, VERIFICATION_PARTIAL)
        ):
            logger.info(
                f"verify {task.id}: AI گفت {status_val} ولی {len(runtime_passed)} probe "
                f"runtime همه pass و هیچ probe fail/error نداریم — به done override می‌کنیم"
            )
            status_val = VERIFICATION_DONE
            # done_parts را با AC هایی که runtime pass شدند پر کن
            existing_done = list(parsed.get("done_parts") or [])
            for rp in runtime_passed:
                if rp.ac_text and rp.ac_text not in existing_done:
                    existing_done.append(rp.ac_text)
            parsed["done_parts"] = existing_done[:20]
            # remaining_parts را خالی کن
            parsed["remaining_parts"] = []

    touched_codex: Dict[str, Any] = {}
    if watched and target_files:
        try:
            from .oversight_codex_service import get_codex_for_files

            touched_codex = get_codex_for_files(watched.id, target_files) or {}
        except Exception:
            touched_codex = {}

    report = OversightReport(
        id=str(uuid.uuid4()),
        task_id=task.id,
        watched_id=task.watched_id,
        project_full_name=task.project_full_name,
        run_at=now_iso(),
        status=status_val,
        done_parts=parsed.get("done_parts") or [],
        remaining_parts=_resolve_done_remaining_contradictions_v7(
            parsed.get("done_parts") or [],
            parsed.get("remaining_parts") or [],
            step_code_verdicts=step_code_verdicts,
            task_steps_list=task_steps_list,
            task=task,
        ),
        evidence=parsed.get("evidence") or {},
        next_actions=parsed.get("next_actions") or [],
        confidence_score=float(parsed.get("confidence_score") or 0.0),
        raw_response=response[:8000],
        model_id=model_id or "",
        user_goal=user_goal,
        touched_codex=touched_codex,
    )

    # 🆕 criteria_results دیگر ذخیره نمی‌شود (drop شد در parser بالا)
    # تمام اطلاعات معیارها در done_parts/remaining_parts است
    if parsed.get("summary"):
        report.evidence["summary"] = parsed["summary"]

    # 🔬 (Bug C6 — Verify v6) integration با iterative_orchestrator + trace.
    # اگر verify_v6=True (پیش‌فرض)، orchestrator v6 روی AC ها اجرا می‌شود.
    # نتایج در report.verify_trace + ac_probe_details ثبت می‌گردد و سپس
    # یک reconciliation محافظه‌کارانه با thresholds سفت می‌تواند status_val
    # که از مسیر v5 آمده را upgrade/downgrade کند (وقتی v6 با اعتماد بالا
    # verdict متفاوتی دارد).
    if verify_v6:
        try:
            from .verify_runtime.context_builder import build_verify_context, VerifyConfig
            from .verify_runtime.iterative_orchestrator import (
                iterative_verify_step, aggregate_verdicts,
            )
            from .verify_runtime.ac_cache_service import (
                check_ac_cache, update_ac_cache,
            )

            cfg_dict = getattr(watched, "verify_v6_config", None) if watched else None
            v6_config = VerifyConfig.from_dict(cfg_dict)
            v6_ctx = await build_verify_context(task, watched, config=v6_config)

            ac_probe_details: List[Dict[str, Any]] = []
            for _i, _ac in enumerate(acceptance_criteria):
                classification = _classify_step_for_probe(_ac)
                v6_ctx.append_trace({
                    "phase": "classify_ac",
                    "ac_index": _i,
                    "classification": classification,
                })
                # cache check (بهبود ۷)
                cached = check_ac_cache(
                    _ac, v6_ctx,
                    classification=classification,
                    target_files=target_files,
                )
                if cached is not None:
                    v6_ctx.append_trace({
                        "phase": "cache_hit",
                        "ac_index": _i,
                        "verdict": cached.verdict,
                    })
                    ac_probe_details.append({
                        "ac_index": _i,
                        "ac_text": _ac_text_of(_ac)[:200],
                        "classification": classification,
                        "final_verdict": cached.verdict,
                        "final_confidence": cached.confidence,
                        "cache_hit": True,
                        "iterations": [],
                    })
                    continue
                # iterative verify (با timeout کلی برای ایمنی)
                try:
                    final_result, all_iters = await asyncio.wait_for(
                        iterative_verify_step(_ac, v6_ctx, max_iterations=v6_config.max_iterations),
                        timeout=180,
                    )
                except asyncio.TimeoutError:
                    final_result = None
                    all_iters = []
                    v6_ctx.append_trace({
                        "phase": "iteration_timeout",
                        "ac_index": _i,
                    })
                if final_result is not None:
                    ac_probe_details.append({
                        "ac_index": _i,
                        "ac_text": _ac_text_of(_ac)[:200],
                        "classification": classification,
                        "final_verdict": final_result.verdict,
                        "final_confidence": final_result.confidence,
                        "cache_hit": False,
                        "iterations": [
                            {
                                "probe_name": r.probe_name,
                                "verdict": r.verdict,
                                "confidence": r.confidence,
                                "elapsed_ms": r.elapsed_ms,
                            } for r in all_iters
                        ],
                    })
                    # update cache
                    try:
                        await update_ac_cache(
                            _ac, final_result, v6_ctx,
                            classification=classification,
                            target_files=target_files,
                        )
                    except Exception as _ce:
                        logger.warning(f"update_ac_cache failed: {_ce}")

            # ست trace + version + config_used + ac_probe_details
            report.verify_trace = list(v6_ctx.trace)
            report.ac_probe_details = ac_probe_details
            report.verify_version = "v6"
            report.config_used = v6_config.to_dict()

            # 🆕 (C6 v6 reconciliation) — v6 verdict ها را با status_val مسیر
            # v5 تطبیق بده. سیاست محافظه‌کارانه با thresholds سفت:
            #   - UPGRADE  (not_done/partial → done): v6 done_ratio ≥ 0.8 و
            #     avg_conf ≥ 0.85 و total ≥ 1
            #   - DOWNGRADE (done → partial): v6 not_done_ratio ≥ 0.5 و
            #     avg_conf ≥ 0.85 و total ≥ 2 (داون‌گرید نیاز به شواهد بیشتر دارد)
            #   - Per-AC sync: هر AC که v6 با conf ≥ 0.85 done گفت، اگر در
            #     report.remaining_parts بود → به done_parts منتقل شود
            # نتیجه در report.evidence["v6_reconciliation"] ثبت می‌شود.
            _v6_concrete = [
                d for d in ac_probe_details
                if str(d.get("final_verdict") or "") in ("done", "partial", "not_done")
            ]
            _v6_total = len(_v6_concrete)
            if _v6_total >= 1:
                _v6_done = sum(1 for d in _v6_concrete if d.get("final_verdict") == "done")
                _v6_not_done = sum(1 for d in _v6_concrete if d.get("final_verdict") == "not_done")
                _v6_confs = [
                    float(d.get("final_confidence") or 0.0) for d in _v6_concrete
                ]
                _v6_avg_conf = sum(_v6_confs) / len(_v6_confs) if _v6_confs else 0.0
                _v6_done_ratio = _v6_done / _v6_total if _v6_total else 0.0
                _v6_not_done_ratio = _v6_not_done / _v6_total if _v6_total else 0.0

                _reconciliation_actions: List[str] = []
                _prev_status_val = status_val
                # نکتهٔ ایمنی: در تسک‌های دارای task_steps_list، چک
                # all_steps_done در ادامه می‌تواند upgrade شده را برگرداند
                # (چون step status های فردی از AI parse هنوز ممکن است
                # not_done باشند). بنابراین aggregate upgrade فقط زمانی
                # اعمال می‌شود که task_steps_list خالی باشد. مسیر تسک‌های
                # task_steps همچنان از step_code_verdicts (programmatic
                # upgrade سنتی) برای reconciliation سطح step بهره می‌برد.
                _aggregate_reconciliation_allowed = not bool(task_steps_list)

                # UPGRADE
                if (
                    _aggregate_reconciliation_allowed
                    and status_val in (VERIFICATION_NOT_DONE, VERIFICATION_PARTIAL)
                    and _v6_done_ratio >= 0.8
                    and _v6_avg_conf >= 0.85
                ):
                    status_val = VERIFICATION_DONE
                    report.status = VERIFICATION_DONE
                    _reconciliation_actions.append(
                        f"upgrade {_prev_status_val} → done "
                        f"(v6: {_v6_done}/{_v6_total} done @ avg_conf={_v6_avg_conf:.2f})"
                    )
                    logger.info(
                        f"verify {task.id}: v6 reconciliation UPGRADED "
                        f"{_prev_status_val} → done "
                        f"(done_ratio={_v6_done_ratio:.2f}, avg_conf={_v6_avg_conf:.2f})"
                    )
                # DOWNGRADE
                elif (
                    _aggregate_reconciliation_allowed
                    and status_val == VERIFICATION_DONE
                    and _v6_not_done_ratio >= 0.5
                    and _v6_avg_conf >= 0.85
                    and _v6_total >= 2
                ):
                    status_val = VERIFICATION_PARTIAL
                    report.status = VERIFICATION_PARTIAL
                    _reconciliation_actions.append(
                        f"downgrade done → partial "
                        f"(v6: {_v6_not_done}/{_v6_total} not_done @ avg_conf={_v6_avg_conf:.2f})"
                    )
                    logger.info(
                        f"verify {task.id}: v6 reconciliation DOWNGRADED "
                        f"done → partial "
                        f"(not_done_ratio={_v6_not_done_ratio:.2f}, avg_conf={_v6_avg_conf:.2f})"
                    )
                elif not _aggregate_reconciliation_allowed:
                    _reconciliation_actions.append(
                        "aggregate-upgrade-skipped (task_steps present — "
                        "step_code_verdicts خود کار reconciliation سطح step را انجام می‌دهد)"
                    )

                # Per-AC sync: انتقال AC های v6-done از remaining → done
                _moved_to_done: List[str] = []
                for _det in _v6_concrete:
                    if _det.get("final_verdict") != "done":
                        continue
                    if float(_det.get("final_confidence") or 0.0) < 0.85:
                        continue
                    _ac_t = str(_det.get("ac_text") or "").strip()
                    if len(_ac_t) < 8:
                        continue
                    _existing_remaining = list(report.remaining_parts or [])
                    _new_remaining: List[Any] = []
                    _matched = False
                    for _rp in _existing_remaining:
                        _rp_text = str(_rp).strip()
                        if _ac_t in _rp_text or (
                            len(_rp_text) >= 8 and _rp_text in _ac_t
                        ):
                            _matched = True
                            continue
                        _new_remaining.append(_rp)
                    if _matched:
                        report.remaining_parts = _new_remaining
                        _entry = (
                            f"✓ {_ac_t[:120]} "
                            f"(v6: done conf={float(_det.get('final_confidence') or 0.0):.2f})"
                        )
                        _existing_done = list(report.done_parts or [])
                        if _entry not in _existing_done:
                            _existing_done.append(_entry)
                            report.done_parts = _existing_done
                        _moved_to_done.append(_ac_t[:80])
                if _moved_to_done:
                    _reconciliation_actions.append(
                        f"moved {len(_moved_to_done)} AC از remaining → done"
                    )

                report.evidence["v6_reconciliation"] = {
                    "v5_status_before": _prev_status_val,
                    "status_after": status_val,
                    "v6_total_acs": _v6_total,
                    "v6_done": _v6_done,
                    "v6_not_done": _v6_not_done,
                    "v6_avg_confidence": round(_v6_avg_conf, 3),
                    "actions": _reconciliation_actions,
                    "moved_to_done": _moved_to_done[:10],
                }
                v6_ctx.append_trace({
                    "phase": "v6_reconciliation",
                    "v5_before": _prev_status_val,
                    "status_after": status_val,
                    "actions": _reconciliation_actions,
                })
                report.verify_trace = list(v6_ctx.trace)
        except Exception as _v6e:
            logger.warning(f"verify_v6 orchestrator failed (graceful fallback to v5): {_v6e}")
            report.verify_version = "v5"

    # 🔬 (Runtime Verify Stage 5+6) — probe results را در evidence ذخیره کن
    # همیشه runtime_status را ذخیره می‌کنیم (حتی وقتی probe نخورد) تا
    # کاربر بفهمد چرا (مثلاً RUNTIME_VERIFY_ENABLED=false یا empty AC).
    report.evidence["runtime_status"] = runtime_status_note
    if runtime_probe_results:
        report.evidence["runtime_probes"] = [
            r.to_dict() for r in runtime_probe_results
        ]
        report.evidence["runtime_probes_summary"] = {
            "total": len(runtime_probe_results),
            "passed": sum(1 for r in runtime_probe_results if r.status == "passed"),
            "failed": sum(1 for r in runtime_probe_results if r.status == "failed"),
            "skipped": sum(1 for r in runtime_probe_results if r.status == "skipped"),
            "error": sum(1 for r in runtime_probe_results if r.status == "error"),
        }
        if runtime_run_id:
            report.evidence["runtime_run_id"] = runtime_run_id
    # 🔬 (inspector_probe Phase 1) — اطلاعات لازم برای لینک به تب بازرس ویژه
    _avs_id_local = locals().get("auto_verify_session_id")
    if _avs_id_local is not None:
        report.evidence["auto_verify_session_id"] = _avs_id_local
    _avp_id_local = locals().get("auto_verify_project_id")
    if _avp_id_local:
        report.evidence["auto_verify_project_id"] = _avp_id_local

    # 🛡 fallback warning: اگر AI status=partial داد ولی remaining_parts خالی،
    # یا status=not_done ولی همه پر، یک warning log کن
    if status_val == VERIFICATION_PARTIAL and not report.remaining_parts:
        logger.warning(
            f"verify: status=partial ولی remaining_parts خالی است (task={task.id}). "
            f"AI verifier prompt را رعایت نکرده. fallback: استفاده از acceptance_criteria."
        )
        report.remaining_parts = [_ac_text_of(c) for c in acceptance_criteria[:5]]
    if status_val == "not_done" and not report.remaining_parts:
        report.remaining_parts = [_ac_text_of(c) for c in acceptance_criteria[:5]]

    # به‌روزرسانی task
    streak_required = 2
    if watched and getattr(watched, "confirmation_streak_required", None):
        streak_required = max(1, int(watched.confirmation_streak_required))

    # 🆕 (Multi-pass Checklist) — اگر task_steps دارد، استاتوس هر مرحله را
    # از parsed["steps_status"] روی task.task_steps اعمال کن.
    steps_status_raw = parsed.get("steps_status") or []
    all_steps_done = False
    if task_steps_list and isinstance(steps_status_raw, list):
        # index by id
        status_by_id: Dict[Any, Dict[str, Any]] = {}
        for entry in steps_status_raw:
            if not isinstance(entry, dict):
                continue
            sid = entry.get("id")
            if sid is None:
                continue
            try:
                status_by_id[int(sid)] = entry
            except Exception:
                status_by_id[sid] = entry

        updated_steps: List[Dict[str, Any]] = []
        completion_sum = 0
        done_count = 0
        # 🆕 (Phase 4 fix #17) — programmatic override stats
        _step_overrides: List[str] = []
        for s in task_steps_list:
            sid = s.get("id")
            try:
                sid_key = int(sid)
            except Exception:
                sid_key = sid
            new_entry = dict(s)
            upd = status_by_id.get(sid_key) or status_by_id.get(str(sid_key)) or {}
            new_status = (upd.get("status") or s.get("status") or "pending").strip().lower()
            if new_status not in ("done", "partial", "not_done", "pending", "error"):
                new_status = "pending"

            # 🆕 (Phase 4 fix #17) — programmatic override:
            # اگر code_aware برای این step verdict داده، AI verdict را
            # با آن چک کن. اگر AI گفت not_done ولی code_aware گفت
            # implemented (یا برعکس)، code_aware را اولویت بده — چون
            # AI verifier نهایی گاهی فقط روی UI screenshot قضاوت می‌کند
            # و backend internal features را نمی‌بیند.
            try:
                _step_id_int = int(sid) if sid is not None else None
            except Exception:
                _step_id_int = None
            _cav = (
                step_code_verdicts.get(_step_id_int)
                if _step_id_int is not None else None
            )
            _override_applied = False
            if _cav:
                _ca_verdict = _cav.get("verdict", "unclear")
                _ca_reason = _cav.get("reason", "")[:200]
                _orig_status = new_status
                # implemented → done (مگر AI شواهد قوی ضد داشته باشد)
                if _ca_verdict == "implemented" and new_status in ("not_done", "pending"):
                    new_status = "done"
                    _override_applied = True
                    _step_overrides.append(
                        f"step {sid}: AI={_orig_status} → done "
                        f"(code-aware: implemented; {_ca_reason})"
                    )
                # partial → partial (اگر AI گفت not_done)
                elif _ca_verdict == "partial" and new_status == "not_done":
                    new_status = "partial"
                    _override_applied = True
                    _step_overrides.append(
                        f"step {sid}: AI=not_done → partial "
                        f"(code-aware: partial; {_ca_reason})"
                    )
                # اگر AI گفت done ولی code-aware گفت not_found، AI بمونه
                # (شاید AI کد را در chunks خوانده، code_aware فقط commit window می‌بیند)

            # completion_pct
            try:
                pct = int(upd.get("completion_pct", s.get("completion_pct", 0)) or 0)
            except Exception:
                pct = 0
            if new_status == "done":
                pct = 100
            elif new_status == "not_done":
                pct = 0
            elif new_status == "partial":
                pct = max(1, min(99, pct or 50))
            # 🆕 (Consistency Tighten §1) — اگر AI گفت done ولی فیلد remaining
            # غیرخالی برگرداند (مثلاً "اضافه نشده", "ناقص", "هنوز ...")، این
            # یک تناقض درون-step است. سیاست: AI به remaining خودش بیشتر اعتماد
            # شود — به partial تنزل بده. این جلوی این bug را می‌گیرد که AI
            # ۹/۹ ✅ بزند ولی در remaining هر step چیزی برای انجام نشده ذکر کند.
            _step_remaining_text = (upd.get("remaining") or "").strip()
            if new_status == "done" and len(_step_remaining_text) >= 10:
                _lower = _step_remaining_text.lower()
                # اگر متن remaining "ندارد/none/n/a" نیست → واقعاً کار باقی مانده
                if not any(
                    tok in _lower for tok in (
                        "ندارد", "نیست", "none", "n/a", "n\\a", "هیچ", "no remaining"
                    )
                ):
                    logger.info(
                        f"verify {task.id}: step {sid} — AI گفت done ولی "
                        f"remaining='{_step_remaining_text[:80]}' دارد → "
                        f"به partial تنزل می‌دهیم."
                    )
                    new_status = "partial"
                    pct = max(1, min(99, pct or 60))
            new_entry["status"] = new_status
            new_entry["completion_pct"] = pct
            new_entry["remaining"] = (upd.get("remaining") or "").strip() if new_status != "done" else ""
            # 🆕 (Phase 4 fix #17 cosmetic) — وقتی override fire می‌کند،
            # evidence text را هم به code-aware reason به‌روز کن — تا
            # کاربر تناقض بین status=✅ و evidence="اعمال نشده" نبیند.
            if _override_applied and _cav:
                _ca_commits = _cav.get("matching_commits") or []
                _ev_parts = [
                    f"🤖 code-aware: {_cav.get('verdict')}",
                    _cav.get("reason", "")[:200],
                ]
                if _ca_commits:
                    _ev_parts.append(f"commits: {', '.join(_ca_commits[:3])}")
                new_entry["evidence"] = " — ".join(p for p in _ev_parts if p)[:300]
            elif upd.get("evidence"):
                new_entry["evidence"] = str(upd.get("evidence"))[:300]
            new_entry["last_verified_at"] = now_iso()
            if new_status == "done":
                done_count += 1
                if not new_entry.get("completed_at"):
                    new_entry["completed_at"] = now_iso()
            else:
                new_entry["completed_at"] = None
            completion_sum += pct
            updated_steps.append(new_entry)
        # log overrides
        if _step_overrides:
            logger.info(
                f"verify {task.id}: {len(_step_overrides)} step status "
                f"overrides applied from code-aware: {_step_overrides[:5]}"
            )
            # 🆕 (Phase 5 cosmetic fix) — وقتی override fires، report.remaining_parts
            # و report.done_parts را هم sync کن. در غیر اینصورت کاربر چک‌لیست
            # 10/10 done می‌بیند ولی "باقی‌مانده (5)" در PDF نمایش داده می‌شود
            # که گمراه‌کننده است.
            try:
                _upgraded_step_titles = []
                for _us in updated_steps:
                    if _us.get("status") == "done":
                        _t = (_us.get("title") or "").strip()
                        if _t:
                            _upgraded_step_titles.append(_t)
                _existing_done = list(getattr(report, "done_parts", []) or [])
                _existing_remaining = list(getattr(report, "remaining_parts", []) or [])

                # حذف عناوین upgrade شده از remaining_parts
                _new_remaining = []
                for _rp in _existing_remaining:
                    _rp_text = str(_rp).strip()
                    # match approximate: عنوان step در remaining_parts باشد
                    _matched = any(
                        _t in _rp_text or _rp_text in _t
                        for _t in _upgraded_step_titles
                        if len(_t) >= 8
                    )
                    if not _matched:
                        _new_remaining.append(_rp)
                # افزودن عناوین upgrade شده به done_parts (با prefix شناسایی)
                _new_done = list(_existing_done)
                for _t in _upgraded_step_titles:
                    _entry = f"✓ {_t} (code-aware: implemented)"
                    if _entry not in _new_done:
                        _new_done.append(_entry)

                report.remaining_parts = _new_remaining
                report.done_parts = _new_done
                logger.info(
                    f"verify {task.id}: sync done/remaining after override — "
                    f"removed {len(_existing_remaining) - len(_new_remaining)} from remaining"
                )
            except Exception as _sync_e:
                logger.debug(f"done/remaining sync failed: {_sync_e}")

        # overall %
        total_steps = len(updated_steps)
        overall_pct = int(round(completion_sum / total_steps)) if total_steps else 0
        all_steps_done = total_steps > 0 and done_count == total_steps
        # apply — به‌جای mutation مستقیم روی task، نتایج را در متغیر نگه می‌داریم
        # تا داخل service._lock اعمال شوند (جلوگیری از race با خواننده‌های همزمان).
        _checklist_computed_steps = updated_steps
        _checklist_overall_pct = overall_pct

        # 🆕 (Consistency Guard §2 — جلوگیری از auto-archive کاذب) — اگر
        # per-step verifier گفت همهٔ مراحل done است ولی AI overall verifier
        # هنوز remaining_parts غیرخالی برگردانده (بعد از contradiction
        # resolver و code-aware sync بالا)، این یک تناقض جدی است: یا AI
        # per-step خوش‌بینانه قضاوت کرده، یا کلیه acceptance criteria در
        # task_steps نگاشت نشده‌اند. در هر دو حالت، auto-archive کردن
        # یک تسک ناقص رخ می‌دهد. سیاست: تنزل به partial، یک step را به
        # partial برگردان (آخرین step) تا overall_pct < 100 شود و
        # all_steps_done = False شود تا bypass_streak فعال نشود.
        _remaining_after_sync = [
            r for r in (getattr(report, "remaining_parts", []) or [])
            if str(r).strip()
        ]
        _remaining_count_after_sync = len(_remaining_after_sync)
        if all_steps_done and _remaining_count_after_sync > 0:
            logger.warning(
                f"verify {task.id}: consistency mismatch — per-step "
                f"checklist {done_count}/{total_steps} done ولی "
                f"remaining_parts (پس از resolver) {_remaining_count_after_sync} "
                f"مورد دارد. جلوگیری از auto-archive کاذب: تنزل به partial."
            )
            # یک step done را به partial تنزل بده تا کاربر در UI ببیند
            # کدام مرحله هنوز کامل نیست + overall_pct < 100 شود.
            for _us in reversed(updated_steps):
                if _us.get("status") == "done":
                    _us["status"] = "partial"
                    _us["completion_pct"] = 80
                    _us["remaining"] = (
                        f"تأیید کلی AI {_remaining_count_after_sync} مورد "
                        f"باقی‌مانده پیدا کرده — بازبینی لازم: "
                        + "; ".join(str(r)[:60] for r in _remaining_after_sync[:3])
                    )[:500]
                    _us["completed_at"] = None
                    done_count -= 1
                    break
            total_steps = len(updated_steps)
            completion_sum = sum(
                int(_s.get("completion_pct", 0) or 0) for _s in updated_steps
            )
            overall_pct = (
                int(round(completion_sum / total_steps)) if total_steps else 0
            )
            all_steps_done = False
            status_val = VERIFICATION_PARTIAL
            report.status = VERIFICATION_PARTIAL
            _checklist_computed_steps = updated_steps
            _checklist_overall_pct = overall_pct

        # 🆕 اگر AI همه را done نشان داد ولی status کلی را done نگفت، در صورت
        # کامل بودن چک‌لیست، status_val را به done بالا ببر تا transition عادی
        # streak/auto-done اجرا شود (verifier ممکن است محافظه‌کار باشد).
        if all_steps_done and status_val != VERIFICATION_DONE:
            status_val = VERIFICATION_DONE
        # 🆕 برعکس: اگر AI status=done گفت ولی همهٔ مراحل done نیستند،
        # به partial تنزل بده — تسک واقعاً تمام نشده.
        elif (not all_steps_done) and status_val == VERIFICATION_DONE and total_steps > 0:
            logger.info(
                f"verify: AI گفت done ولی {done_count}/{total_steps} مرحله done است — "
                f"به partial تنزل می‌دهیم."
            )
            status_val = VERIFICATION_PARTIAL
            # report.status هم به‌روز شود
            report.status = VERIFICATION_PARTIAL

        # 🆕 markdown checkbox state — محاسبه بیرون lock، اعمال داخل lock
        try:
            _checklist_synced_prompt: Optional[str] = _sync_prompt_checkboxes(
                task.prompt or "", updated_steps
            )
        except Exception as _e:
            logger.debug(f"sync prompt checkboxes failed: {_e}")
            _checklist_synced_prompt = None
    else:
        _checklist_computed_steps = None
        _checklist_overall_pct = None
        _checklist_synced_prompt = None

    async with service._lock:
        # 🔒 اعمال نتایج checklist روی task (داخل lock — atomic با بقیهٔ به‌روزرسانی‌ها)
        if _checklist_computed_steps is not None:
            task.task_steps = _checklist_computed_steps
            if _checklist_overall_pct is not None:
                task.overall_completion_pct = _checklist_overall_pct
            if _checklist_synced_prompt is not None and _checklist_synced_prompt != task.prompt:
                task.prompt = _checklist_synced_prompt

        service.reports.insert(0, report)
        task.last_verification_report_id = report.id
        task.last_verified_at = now_iso()
        task.verification_history.append(
            {
                "report_id": report.id,
                "verified_at": report.run_at,
                "status": status_val,
                "triggered_by": triggered_by,
                "summary": parsed.get("summary") or "",
            }
        )
        # محدودیت تاریخچه
        if len(task.verification_history) > 30:
            task.verification_history = task.verification_history[-30:]

        if status_val == VERIFICATION_DONE:
            # 🆕 (Auto-Archive Hard Guard) — defense in depth: حتی اگر تمام
            # منطق بالا decide کرده done است، اگر report.remaining_parts هنوز
            # غیرخالی است، auto-archive ممنوع. این تضمین می‌کند که هیچ تسکی
            # با "جزئیات می‌گوید X مورد باقی‌مانده" آرشیو نشود.
            _final_remaining = [
                r for r in (getattr(report, "remaining_parts", []) or [])
                if str(r).strip()
            ]
            if _final_remaining:
                logger.warning(
                    f"verify {task.id}: hard-guard blocked auto-archive — "
                    f"status_val=done ولی {len(_final_remaining)} مورد در "
                    f"remaining_parts باقی است. تنزل به partial."
                )
                status_val = VERIFICATION_PARTIAL
                report.status = VERIFICATION_PARTIAL
                task.confirmation_streak = 0
                task.verification_status = "partial"
                task.status = "awaiting_review"
            else:
                task.confirmation_streak += 1
                # 🆕 (audit fix) — وقتی task_steps دارد و *همهٔ* مراحل done شدند
                # (per-step verified)، streak guard دور زده می‌شود. این سیگنال
                # دقیق‌تر از یک verify کلی است و کاربر منتظر «verify بعدی»
                # نمی‌ماند برای کاری که ۱۰۰٪ checklist تأیید شده.
                bypass_streak = bool(
                    all_steps_done and (task.task_steps or [])
                )
                # 🚨 (auto-runner loop fix) — auto-runner یک deep verify کامل
                # (با runtime probes و iterative orchestrator) اجرا می‌کند.
                # وقتی این verify عمیق می‌گوید DONE، شرط streak دو-باره معنا
                # ندارد — فقط باعث یک Claude run اضافه (+token+wait) می‌شد و
                # کاربر همان checklist را دوباره در Telegram می‌دید. حالا
                # برای trigger های auto-runner، streak دور زده می‌شود.
                bypass_for_auto_runner = (
                    isinstance(triggered_by, str)
                    and triggered_by.startswith("claude_auto_runner")
                )
                if (
                    task.confirmation_streak >= streak_required
                    or bypass_streak
                    or bypass_for_auto_runner
                ):
                    task.verification_status = "done"
                    task.status = "done"
                    # 🆕 (P3) auto-archive وقتی هم status هم verification_status = done
                    # تسک از فهرست فعال حذف می‌شود ولی در آرشیو قابل مشاهده است
                    if not getattr(task, "archived", False):
                        task.archived = True
                        task.archived_at = now_iso()
                else:
                    task.verification_status = "partial"
                    task.status = "awaiting_review"
        elif status_val == VERIFICATION_PARTIAL:
            task.confirmation_streak = 0
            task.verification_status = "partial"
            task.status = "awaiting_review"
        elif status_val == VERIFICATION_REGRESSED:
            task.confirmation_streak = 0
            task.verification_status = "regressed"
            task.status = "pending"
        elif status_val == VERIFICATION_NOT_DONE:
            task.confirmation_streak = 0
            task.verification_status = "pending"
            # اگر کاربر گفته بود externally applied ولی نتیجه not_done → برگرد به pending
            if task.manually_marked_applied_at:
                task.verification_status = "needs_clarification"
            task.status = "pending" if task.status not in ("running", "cancelled") else task.status
        else:
            task.verification_status = "needs_clarification"

        task.updated_at = now_iso()
        service._save_reports()
        service._save_tasks()
        # 🆕 (Prompt-GitHub Sync) — همگام‌سازی خودکار توسط _save_tasks
        # (verify_status تغییر کرد → task.updated_at > github_prompt_synced_at
        # → dirty → sync خودکار)

    # 🔁 Follow-up prompt: پس از append تاریخچه، اگر status != done
    # یک پرامپت "ادامه" ساخته و روی task ست می‌شود تا کاربر در دور
    # بعدی بتواند آن را copy/apply کند. اگر done شد، followup reset می‌شود.
    try:
        await service.apply_followup_after_verify(task.id, report)
        # تسک به‌روزشده را دوباره بخوان (followup_prompt حالا ست شده)
        task = next((t for t in service.tasks if t.id == task.id), task)
    except Exception as _e:
        logger.warning(f"apply_followup_after_verify failed: {_e}")

    # 🆕 (C5 — بند ۱۱) — Title re-evaluation بعد از هر verify
    # هر بار که verify اجرا شود، عنوان بازنگری می‌شود (مگر manual_title_override).
    # AI call سبک، ~۴s، با مدل extraction. اگر fail شد، صدمه‌ای به verify نمی‌زند.
    try:
        await service._ai_reassess_title(task, triggered_by="verify_reassess")
        # task ممکن است به‌روز شده باشد — دوباره بخوان
        task = next((t for t in service.tasks if t.id == task.id), task)
    except Exception as _e:
        logger.debug(f"title reassess (post-verify) failed for {task.id}: {_e}")

    # event hook
    try:
        await service._emit(
            "task.verified",
            {"task": task.to_dict(), "report": report.to_dict(), "triggered_by": triggered_by},
        )
    except Exception:
        pass

    # 🔔 notification — در background اجرا می‌شود تا API verify بدون انتظار
    # برای PDF generation (که ممکن است چند ثانیه طول بکشد) پاسخ دهد.
    async def _send_verify_notification_bg(_task: "OversightTask", _report: "OversightReport") -> None:
        try:
            from .notification_service import notification_service
            from .oversight_verify_pdf import (
                build_verify_checklist_message,
                build_verify_report_pdf,
            )
            # نگاشت status → event دقیق
            status_to_event = {
                "done": "verify_done",
                "partial": "verify_partial",
                "not_done": "verify_not_done",
                "regressed": "verify_regressed",
                "needs_clarification": "verify_clarification",
            }
            event = status_to_event.get(_task.verification_status, "verify_done")

            # 🆕 (Checklist Notification) — متن چک‌لیستی کوتاه به‌عنوان caption،
            # و PDF کامل (شامل متن کامل پرامپت + جزئیات همهٔ مراحل) به‌عنوان پیوست.
            msg_text = build_verify_checklist_message(_task, _report)
            # streak تکمیلی در caption
            if _task.confirmation_streak and streak_required > 1 and "streak:" not in msg_text:
                msg_text += f"\n🔁 streak: {_task.confirmation_streak}/{streak_required}"

            # تولید PDF (best-effort — اگر failed، attachment=None و فقط متن می‌رود)
            attachment_payload: Optional[Dict[str, Any]] = None
            try:
                pdf_bytes, pdf_filename = await build_verify_report_pdf(_task, _report)
                attachment_payload = {
                    "bytes": pdf_bytes,
                    "filename": pdf_filename,
                }
            except Exception as _pdf_err:
                logger.warning(f"verify pdf generation failed: {_pdf_err}")
                attachment_payload = None

            # PR link اگر موجود — applied_evidence ممکن است dict/None/خراب باشد
            extra_buttons = None
            ae = _task.applied_evidence
            if isinstance(ae, dict):
                pr_url = ae.get("pr_url")
                if pr_url:
                    extra_buttons = [{"text": "🔀 دیدن PR", "url": pr_url}]
            # priority برای gate و hashtag
            priority = _task.priority or "low"
            # regressed همیشه بحرانی محسوب می‌شود
            if _task.verification_status == "regressed":
                priority = "critical"

            await notification_service.notify_event(
                event,
                msg_text,
                subject=f"Verify {_task.verification_status}",
                priority=priority,
                project_name=_task.project_full_name,
                watched_id=_task.watched_id,
                extra_hashtags=[_task.type] if _task.type else None,
                extra_buttons=extra_buttons,
                attachment=attachment_payload,
            )

            # 🔬 (inspector_probe Phase 1) — ضمیمه کردن screenshot های auto-verify
            # به همان نوتیفیکیشن (به‌عنوان پیام‌های پی‌درپی photo). در صورت موفقیت
            # ارسال هر screenshot، فایل آن از دیسک پاک می‌شود و در evidence نشان
            # archived_to_telegram=True ست می‌گردد. اگر تلگرام شکست بخورد، فایل
            # روی دیسک می‌ماند و TTL cleanup در آینده آن را برمی‌دارد.
            try:
                await _send_runtime_screenshots_and_cleanup(_task, _report)
            except Exception as _se:
                logger.debug(f"send runtime screenshots failed: {_se}")
            # 🆕 (Phase 2 fix) — followup_prompt جداگانه دیگر فرستاده نمی‌شود
            # چون mega-bundle شامل آن است (بخش ۵ + ۶ بسته شامل پرامپت
            # فعلی و کل تاریخچه). اگر کاربر می‌خواهد فقط پرامپت ادامه را
            # ببیند، در bundle.html همان بخش ۵ کافی است.
            try:
                await _send_mega_bundle(_task)
            except Exception as _mbe:
                logger.debug(f"send mega bundle failed: {_mbe}")
            # 🆕 (Phase 3) — اگر AC هایی هستن که نیاز به upgrade Phase 3 دارن،
            # یک‌بار به کاربر در تلگرام یادآور بزن با دکمه‌ی trigger.
            # rate-limit: حداکثر یک‌بار در هر ۲۴ ساعت
            try:
                await _maybe_send_backfill_needed_notification()
            except Exception as _bne:
                logger.debug(f"backfill_needed notification failed: {_bne}")
        except Exception as e:
            logger.debug(f"notification skipped: {e}")

    try:
        # snapshot از task فعلی بگیر — اگر بعد از این تغییری روی task شد،
        # background task نسخهٔ خوانده‌شده در همین لحظه را می‌فرستد.
        import asyncio as _asyncio
        _asyncio.create_task(_send_verify_notification_bg(task, report))
    except Exception as _e:
        logger.debug(f"schedule notification failed: {_e}")

    # 🆕 (C7v2 Sections 4+5) — auto-sync + review در انتهای verify
    # غیر-blocking نسبت به نتیجهٔ verify؛ هر شکستی فقط log می‌شود.
    if task.watched_id:
        try:
            _svc = get_oversight_service()
            _sync_r = await _svc.sync_to_inspector_memory_training(task.watched_id)
            logger.info(
                f"verify_task end → sync: mem={_sync_r.get('created_memory_count', 0)}, "
                f"train={_sync_r.get('created_training_count', 0)}"
            )
        except Exception as _se:
            logger.warning(f"verify_task: sync_to_inspector failed: {_se}")
        try:
            _svc2 = get_oversight_service()
            _rev_r = await _svc2.review_auto_synced_fields(task.watched_id)
            logger.info(
                f"verify_task end → review: strengthened={_rev_r.get('strengthened_count', 0)}, "
                f"archived={_rev_r.get('archived_count', 0)}"
            )
        except Exception as _re:
            logger.warning(f"verify_task: review_auto_synced_fields failed: {_re}")

    return {
        "task": task.to_dict(),
        "report": report.to_dict(),
        "streak": task.confirmation_streak,
        "streak_required": streak_required,
        "final": task.verification_status == "done",
        "followup_available": bool(task.followup_prompt),
        "followup_round": task.followup_round,
        # 🚨 (auto-runner loop fix) — raw status_val قبل از mutation وضعیت
        # task. به _verify_then_chain اجازه می‌دهد بفهمد "verify done ولی
        # streak<required" را با "partial واقعی" اشتباه نگیرد.
        "status_val": status_val,
    }
