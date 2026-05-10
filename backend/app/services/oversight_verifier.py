"""
Oversight Verifier
==================
موتور verification مستقل از execution.

این موتور **نمی‌داند** کار از چه طریق انجام شده — فقط وضعیت فعلی پروژه را
با acceptance criteria تسک مقایسه می‌کند و یک Report می‌سازد.

اگر done در چند verify متوالی تأیید شد (`confirmation_streak`)، به‌صورت نهایی done.
"""

from __future__ import annotations

import uuid
import logging
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

import aiohttp

from .oversight_service import (
    GITHUB_API,
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
    max_bytes: int = 40000,
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
            decoded = decoded[:max_bytes] + "\n... [TRUNCATED]"
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


async def verify_task(
    task_id: str,
    *,
    model_id: Optional[str] = None,
    triggered_by: str = "manual",
) -> Dict[str, Any]:
    """اجرای verify روی یک تسک — مستقل از execution."""
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
    if token and repo_full_name and "/" in repo_full_name:
        try:
            keywords = _extract_keywords_from_prompt(task.prompt or "", max_keywords=5)
            if keywords:
                keyword_search = await _github_code_search(
                    repo_full_name, keywords, token, max_per_keyword=3
                )
        except Exception as e:
            logger.debug(f"verify: code search failed: {e}")

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
            files_blob_parts.append(f"=== {p} ===\n{c[:8000]}")
    # محتوای فایل‌های هم‌ارز را هم اضافه کن
    for sp in extra_files_to_fetch[:10]:
        c = file_contents.get(sp)
        if c is not None:
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

    user_goal = (watched.user_notes if watched else "") or ""

    ac_lines = "\n".join(f"- {c}" for c in acceptance_criteria)

    verify_prompt = f"""تو یک QA حرفه‌ای هستی. وظیفه‌ات بررسی این است که آیا کارهای خواسته‌شده در پرامپت تسک واقعاً در وضعیت فعلی پروژه انجام شده‌اند یا نه — **بدون اهمیت دادن به اینکه چه کسی یا با چه ابزاری انجام داده**. فقط وضعیت فعلی را با معیارهای پذیرش مقایسه کن.

# 🧠 اصل ارزیابی (مهم — قبل از تصمیم بخوان)
- **تطابق معنایی، نه literal**: اگر کد به شکل متفاوت ولی **هم‌ارز** نوشته شده — یعنی همان نتیجه را تولید می‌کند، همان رفتار را دارد، همان معیار پذیرش را برآورده می‌کند — این **done** است. نباید بخواهی exactly مطابق پرامپت باشد.
- **نام فایل‌ها mhم نیست — نقش‌شان مهم است**: اگر پرامپت گفته «فایل `idea.py` بساز» ولی پروژه از `oversight_service.py` با همان نقش (تعریف Idea/Task) استفاده کرده، این **done** است. اگر پرامپت گفته `OversightPanel.tsx` ولی پروژه از `oversight/page.tsx` استفاده کرده، باز هم **done**. به ساختار repository (که در ادامه می‌آید) نگاه کن و فایل‌های هم‌نقش را شناسایی کن. **هرگز** صرفاً به این دلیل که نام فایل دقیقاً همان چیزی نیست که پرامپت گفته، نگو not_done.
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

# معیارهای پذیرش (Acceptance Criteria)
{ac_lines}

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
- **آیتم‌های لیست‌ها فارسی باشند** (مگر نام فایل/کد).

# خروجی فقط JSON (بدون code block markdown — فقط JSON خام)
{{
  "status": "done | partial | not_done | regressed | error",
  "criteria_results": [
    {{ "criterion": "...", "met": true, "evidence": "..." }}
  ],
  "done_parts": ["جملهٔ کوتاه دربارهٔ کار انجام‌شده 1", "..."],
  "remaining_parts": ["جملهٔ کوتاه دربارهٔ کار باقی‌مانده 1", "..."],
  "evidence": {{ "commits": ["sha"], "files": ["path"], "issues": [] }},
  "next_actions": ["قدم بعدی concrete 1", "..."],
  "confidence_score": 0.95,
  "summary": "خلاصه یک‌پاراگرافی"
}}"""

    try:
        response = await service._ai_generate(
            verify_prompt, model_id=model_id, max_tokens=2500, temperature=0.1
        )
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
            remaining_parts=acceptance_criteria,
            evidence={"error": str(e)},
            next_actions=["تلاش مجدد در دور verify بعدی"],
            confidence_score=0.0,
            raw_response="",
            model_id=model_id or "",
        )
        async with service._lock:
            service.reports.insert(0, report)
            service._save_reports()
        return {"task": task.to_dict(), "report": report.to_dict()}

    parsed = service._extract_json(response) or {}
    status_val = parsed.get("status") or VERIFICATION_PARTIAL
    if status_val not in (
        VERIFICATION_DONE,
        VERIFICATION_PARTIAL,
        VERIFICATION_NOT_DONE,
        VERIFICATION_REGRESSED,
        VERIFICATION_ERROR,
    ):
        status_val = VERIFICATION_PARTIAL

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
        remaining_parts=parsed.get("remaining_parts") or [],
        evidence=parsed.get("evidence") or {},
        next_actions=parsed.get("next_actions") or [],
        confidence_score=float(parsed.get("confidence_score") or 0.0),
        raw_response=response[:8000],
        model_id=model_id or "",
        user_goal=user_goal,
        touched_codex=touched_codex,
    )

    # ذخیرهٔ نتایج معیارها در evidence
    if parsed.get("criteria_results"):
        report.evidence["criteria_results"] = parsed["criteria_results"]
    if parsed.get("summary"):
        report.evidence["summary"] = parsed["summary"]

    # 🛡 fallback warning: اگر AI status=partial داد ولی remaining_parts خالی،
    # یا status=not_done ولی همه پر، یک warning log کن
    if status_val == VERIFICATION_PARTIAL and not report.remaining_parts:
        logger.warning(
            f"verify: status=partial ولی remaining_parts خالی است (task={task.id}). "
            f"AI verifier prompt را رعایت نکرده. fallback: استفاده از acceptance_criteria."
        )
        report.remaining_parts = list(acceptance_criteria[:5])
    if status_val == "not_done" and not report.remaining_parts:
        report.remaining_parts = list(acceptance_criteria[:5])

    # به‌روزرسانی task
    streak_required = 2
    if watched and getattr(watched, "confirmation_streak_required", None):
        streak_required = max(1, int(watched.confirmation_streak_required))

    async with service._lock:
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
            task.confirmation_streak += 1
            if task.confirmation_streak >= streak_required:
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

    # 🔁 Follow-up prompt: پس از append تاریخچه، اگر status != done
    # یک پرامپت "ادامه" ساخته و روی task ست می‌شود تا کاربر در دور
    # بعدی بتواند آن را copy/apply کند. اگر done شد، followup reset می‌شود.
    try:
        await service.apply_followup_after_verify(task.id, report)
        # تسک به‌روزشده را دوباره بخوان (followup_prompt حالا ست شده)
        task = next((t for t in service.tasks if t.id == task.id), task)
    except Exception as _e:
        logger.warning(f"apply_followup_after_verify failed: {_e}")

    # event hook
    try:
        await service._emit(
            "task.verified",
            {"task": task.to_dict(), "report": report.to_dict(), "triggered_by": triggered_by},
        )
    except Exception:
        pass

    # 🔔 notification — silent skip اگر env تنظیم نشده باشد
    try:
        from .notification_service import notification_service
        # نگاشت status → event دقیق
        status_to_event = {
            "done": "verify_done",
            "partial": "verify_partial",
            "not_done": "verify_not_done",
            "regressed": "verify_regressed",
            "needs_clarification": "verify_clarification",
        }
        event = status_to_event.get(task.verification_status, "verify_done")
        status_emoji = {
            "done": "✅", "partial": "🟡", "not_done": "❌",
            "regressed": "🔴", "needs_clarification": "🟠",
        }.get(task.verification_status, "ℹ️")

        msg_lines = [
            f"{status_emoji} *Verify: {task.verification_status}*",
            f"📌 _{task.title[:120]}_",
            f"📁 `{task.project_full_name}`",
            f"🔖 priority: *{task.priority}* • نوع: `{task.type}`",
        ]
        # streak اطلاعاتی
        if task.confirmation_streak and streak_required > 1:
            msg_lines.append(f"🔁 streak: {task.confirmation_streak}/{streak_required}")
        # خلاصهٔ گزارش
        if report.evidence:
            summary = report.evidence.get("summary") or report.evidence.get("ai_summary")
            if summary:
                msg_lines.append(f"\n💬 {str(summary)[:300]}")
        # done/remaining/next_actions/confidence — لیست‌های ساختاریافته
        details = format_done_remaining_for_message(report, max_per_section=5)
        if details:
            msg_lines.append(details)
        # PR link اگر موجود
        extra_buttons = None
        if task.applied_evidence:
            pr_url = task.applied_evidence.get("pr_url")
            if pr_url:
                extra_buttons = [{"text": "🔀 دیدن PR", "url": pr_url}]
        # priority برای gate و hashtag
        priority = task.priority or "low"
        # regressed همیشه بحرانی محسوب می‌شود
        if task.verification_status == "regressed":
            priority = "critical"

        await notification_service.notify_event(
            event,
            "\n".join(msg_lines),
            subject=f"Verify {task.verification_status}",
            priority=priority,
            project_name=task.project_full_name,
            watched_id=task.watched_id,
            extra_hashtags=[task.type] if task.type else None,
            extra_buttons=extra_buttons,
        )
    except Exception as e:
        logger.debug(f"notification skipped: {e}")

    return {
        "task": task.to_dict(),
        "report": report.to_dict(),
        "streak": task.confirmation_streak,
        "streak_required": streak_required,
        "final": task.verification_status == "done",
        "followup_available": bool(task.followup_prompt),
        "followup_round": task.followup_round,
    }
