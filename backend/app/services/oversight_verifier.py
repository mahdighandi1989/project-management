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

# خروجی فقط JSON
{{
  "status": "done | partial | not_done | regressed | error",
  "criteria_results": [
    {{ "criterion": "...", "met": true, "evidence": "..." }}
  ],
  "done_parts": ["..."],
  "remaining_parts": ["..."],
  "evidence": {{ "commits": ["sha"], "files": ["path"], "issues": [] }},
  "next_actions": ["پیشنهاد قدم‌های بعدی اگر done نباشد"],
  "confidence_score": 0.0,
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

    return {
        "task": task.to_dict(),
        "report": report.to_dict(),
        "streak": task.confirmation_streak,
        "streak_required": streak_required,
        "final": task.verification_status == "done",
        "followup_available": bool(task.followup_prompt),
        "followup_round": task.followup_round,
    }
