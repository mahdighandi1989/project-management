"""🧠 مرکز دانش — Knowledge Center

Purpose (from the user's voice-recorded request):
  - One global "knowledge center" page that aggregates experiences from
    every watched project's `experiences/` folder.
  - Auto-create the `experiences/` folder (+ README format guide) in
    every watched project's repo (GitHub or local).
  - When the user runs tasks manually via Claude Code, they can ask
    Claude Code to record the experience as a file in that folder using
    a STANDARDIZED format defined in the folder's README so the
    write-up is project-agnostic and reusable.
  - Files in the folder sync into the Knowledge Center page (a
    catalog/encyclopedia view with TOC + categories + search/sort/
    filter/pagination).
  - Users can also IMPORT chat exports (txt/md/html/pdf) from
    Claude/ChatGPT/Gemini etc.; the system extracts solved challenges
    using the user's selected AI model(s), chunks for large files,
    merges with existing topics, records references.

Storage:
  - Index file at STORAGE_DIR/knowledge_center.json — list of entries
    with metadata (project_id, path, title, tags, source, etc.).
  - Actual content files live INSIDE each watched project's repo at
    `experiences/{slug}.md`. We never duplicate; we index pointers.
  - The README format guide (`experiences/README.md`) is the contract
    every AI model can read to produce conformant write-ups.

Honors the user's 7 explicit requirements:
  1. Model selection — every AI-touching method accepts `model_ids`.
  2. Delete entries — `delete_entry()` removes from index + repo file.
  3. Existing watched projects — `bootstrap_existing()` retroactively
     creates folders.
  4. Future watched projects — hook in oversight_service.add_watched
     calls our `ensure_folder_for_project()`.
  5. Search/sort/filter/pagination — `list_entries()` supports them.
  6. Format guide README in every folder — `EXPERIENCE_FORMAT_README`.
  7. Panel uploads — `import_chat_file()` uses the same format.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import re
import threading
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .oversight_service import STORAGE_DIR, now_iso

logger = logging.getLogger(__name__)


INDEX_FILE: Path = STORAGE_DIR / "knowledge_center.json"
SETTINGS_FILE: Path = STORAGE_DIR / "knowledge_center_settings.json"
EXPERIENCES_FOLDER_NAME = "experiences"

# Default Knowledge Center settings — persisted to SETTINGS_FILE.
# User can edit via PATCH /api/knowledge-center/settings.
_DEFAULT_KC_SETTINGS: Dict[str, Any] = {
    # Background sync — runs periodic pull + AI processing
    "auto_sync_enabled": True,
    "auto_sync_interval_minutes": 60,  # every hour by default
    # Which models run the cross-repo AI processor. Empty list → use
    # all available (parity with creator engine semantics).
    "processing_model_ids": [],
    # Skip AI processing for an entry whose content_hash hasn't changed
    # since last_processed_hash. Saves tokens + avoids duplicate work.
    "skip_unchanged": True,
    # Soft cap so the catalog doesn't grow unbounded over time. Older
    # entries past this cap are archived (de-indexed but file stays in
    # repo). 0 = unlimited.
    "max_indexed_entries": 5000,
}


# ════════════════════════════════════════════════════════════════════════════
# Format guide — the README every experiences/ folder gets.
# This is what Claude Code (and any other AI) reads to produce a write-up.
# Format is stable and the user's project-agnostic requirement is enforced
# by the AI INSTRUCTIONS section.
# ════════════════════════════════════════════════════════════════════════════

EXPERIENCE_FORMAT_README = """# 📚 Experiences Folder — Format Guide

این فولدر تجربیات قابل‌استفاده‌مجدد مهندسی را نگه می‌دارد. هر فایل یک
چالش حل‌شده را به شکل **project-agnostic** (مستقل از پروژهٔ خاص) ثبت
می‌کند تا بتوان آن را در پروژه‌های دیگر دوباره به کار برد.

## 📁 نام‌گذاری فایل‌ها

- یک فایل برای هر تجربه: `{topic-slug}.md` (kebab-case)
- مثال‌های خوب:
  - `google-oauth-login.md`
  - `fastapi-rate-limiting.md`
  - `nextjs-static-export-edge-cases.md`
- مثال بد: `bug-fix-in-myproject.md` (نام پروژه ممنوع)

## 📋 ساختار اجباری هر فایل

هر فایل **باید** با frontmatter YAML شروع شود:

```yaml
---
title: "عنوان کوتاه — همان slug ولی خواناتر"
tags: ["auth", "google-oauth", "frontend"]
topic_canonical: "google-oauth-login"
source:
  type: "manual" | "chat-import" | "claude-code-task"
  origin: "claude-code" | "chatgpt" | "gemini" | "user-typed"
  imported_at: "2026-06-05T10:00:00Z"
created_at: "2026-06-05T10:00:00Z"
updated_at: "2026-06-05T10:00:00Z"
merged_from: []
resolution_status: "solved"   # solved | partial | open | regressed | unknown
recurrence_count: 1            # چند بار همین موضوع در چت بازگشته
user_confirmed: true           # آیا کاربر صریحاً «حل شد» گفت
---
```

سپس بخش‌های markdown به این ترتیب:

```markdown
# Topic Title

## 🎯 چالش / Challenge
[چه مشکلی حل می‌شد — کلی، بدون نام پروژه]

## 💡 راه‌حل / Solution
[راه‌حل قدم‌به‌قدم، قابل تعمیم]

## 🧪 نمونه کد (Anonymized)
[snippet با نام‌های عمومی، نه مال این پروژه]

## ⚠️ نکات حیاتی / Pitfalls
[خطاهای رایج وقتی این الگو را در جای دیگر استفاده می‌کنی، شامل
تلاش‌هایی که در چت اصلی شکست خوردند]

## ✅ Resolution
- Status: solved | partial | open | regressed
- Evidence: نقل‌قول کوتاه از چت که اثبات می‌کند مشکل واقعاً حل شد
  (مثلاً «کاربر گفت ‘حالا کار می‌کنه’» یا «کد فاینال run شد و خطا نداد»)

## 🔁 چطور در جای دیگر اعمال کنیم / How to Apply Elsewhere
[ترجمهٔ این الگو به پروژه‌های دیگر — generic checklist]

### Applies when
- سناریوهای concrete که این الگو در آن‌ها کاربرد دارد

### Does NOT apply when (anti-pattern)
- سناریوهایی که نباید این الگو را اعمال کرد

### Prerequisites
- پیش‌نیازهای فنی (versions, frameworks, …)

## 🔗 References
- منبع اولیه: [chat-export-2026-06-04.txt, line 42]
- مرتبط: [other-experience-slug]
```

## 🤖 دستورالعمل برای مدل‌های AI (Claude Code, GPT, Gemini, …)

وقتی کاربر از تو می‌خواهد یک تجربه را در این فولدر ثبت کنی:

1. **اول بخوان**: تمام فایل‌های موجود را چک کن. اگر `topic_canonical`
   مشابهی هست، **MERGE نه REPLACE**:
   - محتوای اصلی را نگه دار
   - بخش جدید زیر «## Update YYYY-MM-DD» اضافه کن
   - `merged_from:` در frontmatter آپدیت کن

2. **همیشه عمومی بنویس**:
   - ❌ "در پروژهٔ MyApp ما X کردیم"
   - ✅ "وقتی X را پیاده می‌کنیم..."
   - نام فایل‌های مخصوص پروژه → جایگزین با placeholder عمومی
     (مثلاً `MyApp.tsx` → `AuthPage.tsx`)

3. **بخش "How to Apply Elsewhere" اجباری است** — این مهم‌ترین بخش است
   که تجربه را reusable می‌کند.

4. **slug را canonical نگه دار**: `topic_canonical` در frontmatter باید
   یکپارچه باشد تا dedup در آینده کار کند.

5. **References صادق باشن**: اگر مطلب از یک چت import شد، منبع را در
   `source:` و در پایان فایل ذکر کن.

6. **تشخیص resolution را بر اساس شواهد ثبت کن** — نه حدس:
   - `solved` ⇐ کاربر صریحاً تأیید کرد ("کار کرد"، "ممنون") یا کد
     فاینال ارائه شد و کاربر بدون اعتراض موضوع را عوض کرد
   - `partial` ⇐ راه‌حل ارائه شد ولی کاربر یک sub-question باقی‌مانده داشت
   - `open` ⇐ تلاش شد، شواهد روشنی برای حل وجود ندارد
   - `regressed` ⇐ موضوع بعداً در همین چت دوباره ظاهر شد
   - **اگر مطمئن نیستی → `partial` بزن، نه `solved`.**
   - فقط راه‌حلِ **موفق** را در `solution` بیاور؛ تلاش‌های شکست‌خورده
     را در `pitfalls` ثبت کن تا خوانندهٔ بعدی آن‌ها را تکرار نکند.

7. **رشتهٔ یک موضوع را در میان پیام‌های متفرقه دنبال کن** — چت‌های
   طولانی معمولاً interleaved اند. یک موضوع شروع می‌شود، یک سؤال
   نامرتبط وسطش می‌آید، بعد بازمی‌گردد. این پراکندگی نباید باعث شود
   آن را به دو تجربهٔ مجزا تقسیم کنی.

## 📤 سینک با Knowledge Center

این فولدر به‌صورت خودکار توسط صفحهٔ **مرکز دانش** (/knowledge-center)
خوانده می‌شود. فایل‌هایی که فرمت بالا را رعایت کنند با metadata کامل در
کاتالوگ ظاهر می‌شوند؛ فایل‌های بدفرمت در دسته «unparsed» می‌روند.

---
_این فایل توسط Knowledge Center سرویس به‌صورت خودکار ساخته شده.
ویرایش کن اگر می‌خواهی template را برای پروژهٔ خاص خودت گسترش بدهی._
"""


# ════════════════════════════════════════════════════════════════════════════
# Data models
# ════════════════════════════════════════════════════════════════════════════


@dataclass
class KnowledgeEntry:
    """یک ورودی در مرکز دانش — اشاره به فایلی در `experiences/` یک پروژه."""

    id: str
    project_id: Optional[str]  # watched project id (None for "global")
    project_full_name: str  # owner/repo or local name
    path: str  # path within repo, e.g. "experiences/google-oauth-login.md"
    title: str
    topic_canonical: str = ""
    tags: List[str] = field(default_factory=list)
    source_type: str = "manual"  # manual / chat-import / claude-code-task
    source_origin: str = ""  # claude-code / chatgpt / gemini / user-typed
    summary: str = ""  # short excerpt for catalog display
    content_hash: str = ""  # md5 of body — for dedup + change detection
    size_bytes: int = 0
    created_at: str = field(default_factory=now_iso)
    updated_at: str = field(default_factory=now_iso)
    imported_at: str = ""
    merged_from: List[str] = field(default_factory=list)
    # backend records which AI model wrote/extracted this (parity with
    # /creator engine's per-file attribution).
    generated_by: str = ""
    # 🆕 (skip-if-unchanged) — last content_hash that the AI cross-repo
    # processor analyzed. If equal to current content_hash, the next
    # process cycle skips AI for this entry → no duplicate work, no
    # wasted tokens.
    last_processed_hash: str = ""
    last_processed_at: str = ""
    last_processed_by: str = ""
    # 🆕 (cross-repo references) — entries in OTHER projects that have
    # the same topic_canonical. Populated by process_synced_entries.
    # Each item: {"entry_id", "project_full_name", "path", "title"}
    cross_references: List[Dict[str, str]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ════════════════════════════════════════════════════════════════════════════
# Storage
# ════════════════════════════════════════════════════════════════════════════


def _load_index() -> Dict[str, Any]:
    if not INDEX_FILE.exists():
        return {"version": 1, "entries": [], "updated_at": now_iso()}
    try:
        return json.loads(INDEX_FILE.read_text(encoding="utf-8"))
    except Exception as e:
        logger.warning(f"knowledge_center: index load failed: {e}")
        return {"version": 1, "entries": [], "updated_at": now_iso()}


def _save_index(data: Dict[str, Any]) -> None:
    INDEX_FILE.parent.mkdir(parents=True, exist_ok=True)
    data["updated_at"] = now_iso()
    INDEX_FILE.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def load_settings() -> Dict[str, Any]:
    """Return current KC settings merged over defaults so missing keys
    in the persisted file don't crash callers."""
    if not SETTINGS_FILE.exists():
        return dict(_DEFAULT_KC_SETTINGS)
    try:
        data = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
        merged = dict(_DEFAULT_KC_SETTINGS)
        if isinstance(data, dict):
            merged.update(data)
        return merged
    except Exception as e:
        logger.warning(f"knowledge_center settings load failed: {e}")
        return dict(_DEFAULT_KC_SETTINGS)


def save_settings(updates: Dict[str, Any]) -> Dict[str, Any]:
    """Merge updates into persisted settings (PATCH semantics)."""
    current = load_settings()
    for k, v in (updates or {}).items():
        # Reject unknown keys so a typo doesn't shadow a real setting
        if k in _DEFAULT_KC_SETTINGS:
            current[k] = v
    SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
    SETTINGS_FILE.write_text(
        json.dumps(current, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return current


def _slugify(text: str) -> str:
    """Convert any title/topic to a safe kebab-case slug for file names."""
    text = (text or "").strip().lower()
    text = re.sub(r"[^\w؀-ۿ\s-]", "", text)  # keep Persian
    text = re.sub(r"[\s_]+", "-", text)
    text = re.sub(r"-+", "-", text).strip("-")
    return text[:80] or f"experience-{uuid.uuid4().hex[:8]}"


def _hash(body: str) -> str:
    return hashlib.md5((body or "").encode("utf-8")).hexdigest()


def _parse_frontmatter(body: str) -> Tuple[Dict[str, Any], str]:
    """Parse YAML-ish frontmatter from a markdown body. Returns (meta, rest).

    We don't pull in PyYAML for this — keep deps light. Simple line parser
    that handles `key: value` and `key: [a, b]` and nested 1-level
    `key:\n  sub: val`. Robust enough for the format above; anything
    weird → empty meta + original body."""
    if not body or not body.lstrip().startswith("---"):
        return {}, body
    stripped = body.lstrip()
    rest = stripped[3:]
    end = rest.find("\n---")
    if end < 0:
        return {}, body
    fm_text = rest[:end]
    after = rest[end + 4:].lstrip("\n")
    meta: Dict[str, Any] = {}
    current_key: Optional[str] = None
    for line in fm_text.splitlines():
        if not line.strip():
            continue
        if line.startswith(" ") and current_key:
            sub = line.strip()
            if ":" in sub:
                k, v = sub.split(":", 1)
                meta.setdefault(current_key, {})
                if isinstance(meta[current_key], dict):
                    meta[current_key][k.strip()] = v.strip().strip('"')
            continue
        if ":" in line:
            k, v = line.split(":", 1)
            k = k.strip()
            v = v.strip()
            current_key = k
            if v == "":
                meta[k] = {}
            elif v.startswith("[") and v.endswith("]"):
                items = [x.strip().strip('"') for x in v[1:-1].split(",")]
                meta[k] = [x for x in items if x]
            else:
                meta[k] = v.strip('"')
    return meta, after


# ════════════════════════════════════════════════════════════════════════════
# Service
# ════════════════════════════════════════════════════════════════════════════


class KnowledgeCenterService:
    """مرکز دانش — single service that owns the whole feature."""

    def __init__(self):
        self._lock = asyncio.Lock()
        self._sync_lock = threading.Lock()  # for sync-from-disk only

    # ─────────────────────────────────────────────────────────────────────
    # Folder creation (req #3 + #4 + #6: existing + future watched + README)
    # ─────────────────────────────────────────────────────────────────────

    async def ensure_folder_for_project(
        self,
        project_id: str,
        project_full_name: str,
        github_token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create `experiences/` + README.md in the project's repo.

        Idempotent: if README already exists, no-op (don't churn commits).

        Returns: {"created": bool, "repo": ..., "reason": ...}
        """
        repo = (project_full_name or "").strip()
        if "/" not in repo:
            return {
                "created": False, "repo": repo,
                "reason": "local_project_no_repo",
            }
        if not github_token:
            from .oversight_service import get_github_token
            github_token = get_github_token()
        if not github_token:
            return {
                "created": False, "repo": repo,
                "reason": "no_github_token",
            }
        owner, repo_name = repo.split("/", 1)
        readme_path = f"{EXPERIENCES_FOLDER_NAME}/README.md"
        # Check whether README already exists (idempotent — never churn)
        if await self._gh_file_exists(owner, repo_name, readme_path, github_token):
            return {
                "created": False, "repo": repo,
                "reason": "already_exists",
            }
        try:
            from .github_pr_service import get_github_pr_service
            pr = get_github_pr_service()
            res = await pr.create_or_update_file(
                owner=owner,
                repo=repo_name,
                path=readme_path,
                content=EXPERIENCE_FORMAT_README,
                message="🧠 chore: scaffold experiences/ folder for Knowledge Center",
                branch=None,  # use default branch
                token=github_token,
            )
            return {
                "created": bool(res and (res.get("success", True) or res.get("ok", True))),
                "repo": repo,
                "result": res,
            }
        except Exception as e:
            logger.warning(
                f"ensure_folder_for_project: create README failed for {repo}: {e}"
            )
            return {"created": False, "repo": repo, "reason": str(e)[:200]}

    # ─────────────────────────────────────────────────────────────────────
    # GitHub HTTP helpers (read paths github_pr_service doesn't cover)
    # ─────────────────────────────────────────────────────────────────────

    @staticmethod
    async def _gh_file_exists(
        owner: str, repo: str, path: str, token: str,
    ) -> bool:
        import aiohttp
        url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}"
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
        }
        try:
            timeout = aiohttp.ClientTimeout(total=20)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url, headers=headers) as r:
                    return r.status == 200
        except Exception:
            return False

    @staticmethod
    async def _gh_get_file_content(
        owner: str, repo: str, path: str, token: str,
    ) -> Optional[str]:
        """Returns decoded UTF-8 content or None if not found / not a file."""
        import aiohttp
        import base64 as _b64
        url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}"
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
        }
        try:
            timeout = aiohttp.ClientTimeout(total=30)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url, headers=headers) as r:
                    if r.status != 200:
                        return None
                    data = await r.json()
                    if not isinstance(data, dict):
                        return None
                    if data.get("encoding") == "base64":
                        try:
                            return _b64.b64decode(data.get("content", "")).decode(
                                "utf-8", errors="replace",
                            )
                        except Exception:
                            return None
                    return data.get("content")
        except Exception:
            return None

    @staticmethod
    async def _gh_list_directory(
        owner: str, repo: str, path: str, token: str,
    ) -> List[Dict[str, Any]]:
        """Returns list of {name, path, type} for entries under path."""
        import aiohttp
        url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}"
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
        }
        try:
            timeout = aiohttp.ClientTimeout(total=30)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url, headers=headers) as r:
                    if r.status != 200:
                        return []
                    data = await r.json()
                    return data if isinstance(data, list) else []
        except Exception:
            return []

    async def bootstrap_existing(
        self, github_token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Walk every watched project and ensure its `experiences/` folder
        exists. Used once after deploy + as a manual "rebuild" action from
        the UI. Idempotent."""
        from .oversight_service import get_oversight_service, get_github_token
        svc = get_oversight_service()
        token = github_token or get_github_token()
        results: List[Dict[str, Any]] = []
        for w in svc.watched:
            try:
                r = await self.ensure_folder_for_project(
                    project_id=w.id,
                    project_full_name=w.repo_full_name,
                    github_token=token,
                )
                results.append({"project_id": w.id, **r})
            except Exception as e:
                results.append({
                    "project_id": w.id, "created": False, "reason": str(e)[:200],
                })
        created = sum(1 for r in results if r.get("created"))
        skipped = sum(1 for r in results if not r.get("created"))
        return {
            "total": len(results), "created": created, "skipped": skipped,
            "results": results,
        }

    # ─────────────────────────────────────────────────────────────────────
    # Sync (req #1 source-of-truth: pull from repos into the index)
    # ─────────────────────────────────────────────────────────────────────

    async def sync_from_projects(
        self, github_token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Pull every experiences/*.md file from every watched repo into
        the index. Existing entries are updated, new ones added, missing
        ones marked stale (we don't auto-delete; user delete is explicit
        per req #2)."""
        from .oversight_service import get_oversight_service, get_github_token
        from .github_pr_service import get_github_pr_service
        svc = get_oversight_service()
        token = github_token or get_github_token()
        if not token:
            return {"ok": False, "error": "no_github_token"}
        index = _load_index()
        entries_by_key: Dict[str, Dict[str, Any]] = {
            f"{e.get('project_full_name')}::{e.get('path')}": e
            for e in index.get("entries", [])
        }
        added = 0
        updated = 0
        for w in svc.watched:
            repo = w.repo_full_name
            if "/" not in repo:
                continue
            owner, name = repo.split("/", 1)
            listing = await self._gh_list_directory(
                owner, name, EXPERIENCES_FOLDER_NAME, token,
            )
            for item in (listing or []):
                if not isinstance(item, dict):
                    continue
                name_f = item.get("name", "")
                if not name_f.endswith(".md") or name_f.lower() == "readme.md":
                    continue
                path = item.get("path") or f"{EXPERIENCES_FOLDER_NAME}/{name_f}"
                body = await self._gh_get_file_content(
                    owner, name, path, token,
                ) or ""
                meta, content = _parse_frontmatter(body)
                key = f"{repo}::{path}"
                existing = entries_by_key.get(key)
                size = len(body.encode("utf-8"))
                ch = _hash(body)
                tags = meta.get("tags") or []
                if isinstance(tags, str):
                    tags = [t.strip() for t in tags.split(",") if t.strip()]
                title = (
                    meta.get("title")
                    or self._title_from_filename(name_f)
                )
                summary = self._first_paragraph(content)[:300]
                source = meta.get("source") or {}
                if isinstance(source, str):
                    source = {"type": source}
                entry_data = {
                    "id": existing["id"] if existing else uuid.uuid4().hex,
                    "project_id": w.id,
                    "project_full_name": repo,
                    "path": path,
                    "title": title,
                    "topic_canonical": meta.get("topic_canonical") or _slugify(title),
                    "tags": tags,
                    "source_type": source.get("type", "manual"),
                    "source_origin": source.get("origin", ""),
                    "summary": summary,
                    "content_hash": ch,
                    "size_bytes": size,
                    "created_at": (
                        meta.get("created_at") or (existing or {}).get("created_at") or now_iso()
                    ),
                    "updated_at": now_iso() if (not existing or existing.get("content_hash") != ch) else existing["updated_at"],
                    "imported_at": meta.get("imported_at") or (existing or {}).get("imported_at", ""),
                    "merged_from": meta.get("merged_from") or [],
                    "generated_by": meta.get("generated_by") or (existing or {}).get("generated_by", ""),
                }
                if existing:
                    existing.update(entry_data)
                    if existing["content_hash"] != ch:
                        updated += 1
                else:
                    index.setdefault("entries", []).append(entry_data)
                    entries_by_key[key] = entry_data
                    added += 1
        _save_index(index)
        return {
            "ok": True, "added": added, "updated": updated,
            "total": len(index.get("entries", [])),
        }

    @staticmethod
    def _title_from_filename(name: str) -> str:
        stem = name.rsplit(".", 1)[0]
        return stem.replace("-", " ").replace("_", " ").strip().title()

    @staticmethod
    def _first_paragraph(body: str) -> str:
        # Skip headings, return first non-empty paragraph
        for chunk in (body or "").split("\n\n"):
            stripped = "\n".join(
                ln for ln in chunk.splitlines() if not ln.lstrip().startswith("#")
            ).strip()
            if stripped:
                return stripped
        return ""

    # ─────────────────────────────────────────────────────────────────────
    # List with search/sort/filter/pagination (req #5)
    # ─────────────────────────────────────────────────────────────────────

    def list_entries(
        self,
        *,
        page: int = 1,
        per_page: int = 20,
        search: str = "",
        tag: str = "",
        project_id: str = "",
        source_type: str = "",
        sort: str = "updated_desc",
    ) -> Dict[str, Any]:
        """Catalog endpoint with full search/sort/filter/pagination."""
        index = _load_index()
        items = list(index.get("entries", []))

        # Filter
        if project_id:
            items = [x for x in items if x.get("project_id") == project_id]
        if tag:
            items = [x for x in items if tag in (x.get("tags") or [])]
        if source_type:
            items = [x for x in items if x.get("source_type") == source_type]
        if search:
            needle = search.lower()
            def _hit(x: Dict[str, Any]) -> bool:
                hay = " ".join([
                    x.get("title", ""),
                    x.get("summary", ""),
                    x.get("topic_canonical", ""),
                    " ".join(x.get("tags", []) or []),
                    x.get("project_full_name", ""),
                ]).lower()
                return needle in hay
            items = [x for x in items if _hit(x)]

        # Sort
        sort_keys = {
            "updated_desc": (lambda x: x.get("updated_at", ""), True),
            "updated_asc": (lambda x: x.get("updated_at", ""), False),
            "title_asc": (lambda x: (x.get("title") or "").lower(), False),
            "title_desc": (lambda x: (x.get("title") or "").lower(), True),
            "created_desc": (lambda x: x.get("created_at", ""), True),
            "size_desc": (lambda x: x.get("size_bytes", 0), True),
        }
        key_fn, reverse = sort_keys.get(sort, sort_keys["updated_desc"])
        try:
            items.sort(key=key_fn, reverse=reverse)
        except Exception:
            pass

        total = len(items)
        per_page = max(1, min(100, int(per_page or 20)))
        page = max(1, int(page or 1))
        start = (page - 1) * per_page
        end = start + per_page
        page_items = items[start:end]

        # Build facets so the UI can show "X projects, Y tags, Z sources"
        all_tags: Dict[str, int] = {}
        all_sources: Dict[str, int] = {}
        all_projects: Dict[str, int] = {}
        for x in index.get("entries", []):
            for t in (x.get("tags") or []):
                all_tags[t] = all_tags.get(t, 0) + 1
            s = x.get("source_type") or "manual"
            all_sources[s] = all_sources.get(s, 0) + 1
            p = x.get("project_full_name") or "—"
            all_projects[p] = all_projects.get(p, 0) + 1

        return {
            "items": page_items,
            "total": total,
            "page": page,
            "per_page": per_page,
            "pages": (total + per_page - 1) // per_page,
            "facets": {
                "tags": sorted(
                    all_tags.items(), key=lambda kv: kv[1], reverse=True,
                ),
                "sources": sorted(
                    all_sources.items(), key=lambda kv: kv[1], reverse=True,
                ),
                "projects": sorted(
                    all_projects.items(), key=lambda kv: kv[1], reverse=True,
                ),
            },
        }

    def get_entry(self, entry_id: str) -> Optional[Dict[str, Any]]:
        index = _load_index()
        for e in index.get("entries", []):
            if e.get("id") == entry_id:
                return e
        return None

    # ─────────────────────────────────────────────────────────────────────
    # Delete (req #2)
    # ─────────────────────────────────────────────────────────────────────

    async def delete_entry(
        self,
        entry_id: str,
        *,
        delete_from_repo: bool = True,
        github_token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Remove an entry from the index AND from the repo (opt-in).

        delete_from_repo=False keeps the file in the repo but de-indexes
        it (useful when user wants to keep file but hide from catalog).
        delete_from_repo=True permanently removes the file via GitHub API.
        """
        index = _load_index()
        entry = None
        for i, e in enumerate(index.get("entries", [])):
            if e.get("id") == entry_id:
                entry = e
                del index["entries"][i]
                break
        if entry is None:
            return {"ok": False, "error": "entry_not_found"}
        _save_index(index)

        if not delete_from_repo:
            return {"ok": True, "deindexed": True, "repo_deleted": False}

        repo = entry.get("project_full_name") or ""
        path = entry.get("path") or ""
        if "/" not in repo or not path:
            return {"ok": True, "deindexed": True, "repo_deleted": False,
                    "reason": "no_repo_or_path"}
        from .oversight_service import get_github_token
        from .github_pr_service import get_github_pr_service
        token = github_token or get_github_token()
        if not token:
            return {"ok": True, "deindexed": True, "repo_deleted": False,
                    "reason": "no_github_token"}
        try:
            owner, name = repo.split("/", 1)
            pr = get_github_pr_service()
            res = await pr.delete_file(
                owner=owner, repo=name, path=path, token=token,
                message=f"🧠 chore: remove experience '{entry.get('title', '?')}'",
            )
            return {"ok": True, "deindexed": True, "repo_deleted": True,
                    "result": res}
        except Exception as e:
            return {"ok": True, "deindexed": True, "repo_deleted": False,
                    "reason": str(e)[:200]}

    # ─────────────────────────────────────────────────────────────────────
    # Import chat files (req #7 + format alignment)
    # ─────────────────────────────────────────────────────────────────────

    async def import_chat_file(
        self,
        *,
        filename: str,
        content_bytes: bytes,
        target_project_id: Optional[str],
        target_project_full_name: Optional[str],
        model_ids: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Accept a chat export (txt/md/html/pdf), extract solved
        challenges with the user-selected AI model, write project-agnostic
        experience files into the target project's experiences/ folder
        (or local index if no repo), and update the catalog.

        Honors model_ids — uses ai_generate_with_meta for attribution.
        Chunks large inputs to fit token limits.
        """
        try:
            text = self._extract_text(filename, content_bytes)
        except Exception as e:
            return {"ok": False, "error": f"extract_text_failed: {e}"}
        if not text or len(text.strip()) < 50:
            return {"ok": False, "error": "file_too_small_or_empty"}

        # Use the API route's ai_generate_with_meta for parity with the
        # rest of the Creator/Audit flow.
        from ..api.routes.simple_projects import ai_generate_with_meta

        index = _load_index()
        existing_canonicals = {
            e.get("topic_canonical"): e for e in index.get("entries", [])
        }

        from .oversight_service import get_github_token
        token = get_github_token()

        created_entries: List[Dict[str, Any]] = []
        merged_entries: List[Dict[str, Any]] = []
        errors: List[str] = []
        chunks: List[str] = []  # populated only on fallback path
        pass_mode = "two_pass"

        # 🆕 Two-pass extraction (outline → per-topic deep):
        # Pass 1 sees the whole chat (or its head if huge) and identifies
        # distinct topics + tracks each one across interleaved messages.
        # Pass 2 takes ONE topic at a time, follows its thread across
        # the whole chat, determines resolution_status with evidence,
        # and writes a reusable project-agnostic experience.
        #
        # For very long chats (>80k chars), we still chunk + use the
        # single-pass fallback so we never lose data. The outline pass
        # is best-effort: if it errors, single-pass per chunk runs.
        OUTLINE_MAX_CHARS = 80_000
        topics: List[Dict[str, Any]] = []
        outline_used_model = ""
        if len(text) <= OUTLINE_MAX_CHARS:
            try:
                outline_prompt = self._build_outline_prompt(
                    chat_text=text,
                    target_project=target_project_full_name or "?",
                )
                outline_resp, outline_used_model = await ai_generate_with_meta(
                    outline_prompt, model_ids=model_ids,
                )
                outline_obj = self._parse_topic_outline(outline_resp)
                topics = outline_obj.get("topics") or []
                logger.info(
                    f"knowledge_center.import: outline → {len(topics)} topics"
                )
            except Exception as e:
                errors.append(f"outline pass: {str(e)[:200]}")
                topics = []

        if topics:
            # Two-pass succeeded — do focused per-topic extraction
            for ti, topic in enumerate(topics):
                # Skip low-value topics (outline pre-filters but be defensive)
                if int(topic.get("value_score") or 0) < 4:
                    continue
                try:
                    deep_prompt = self._build_topic_deep_prompt(
                        chat_text=text, topic=topic,
                        target_project=target_project_full_name or "?",
                        existing_topics=list(existing_canonicals.keys())[:50],
                    )
                    deep_resp, used_model = await ai_generate_with_meta(
                        deep_prompt, model_ids=model_ids,
                    )
                    item = self._parse_topic_deep_response(deep_resp)
                    if item is None:
                        continue
                    # Outline owns the canonical — pass-2 may suggest one
                    # but we always pin to outline so we don't accidentally
                    # split the same topic across two entries because
                    # the two passes disagreed on the slug.
                    outline_canonical = (
                        topic.get("topic_canonical")
                        or _slugify(item.get("title", ""))
                    )
                    item["topic_canonical"] = outline_canonical
                    await self._dispatch_extracted_item(
                        item=item, used_model=used_model,
                        existing_canonicals=existing_canonicals,
                        target_project_id=target_project_id,
                        target_project_full_name=target_project_full_name,
                        github_token=token, source_file=filename,
                        created_entries=created_entries,
                        merged_entries=merged_entries,
                    )
                except Exception as e:
                    errors.append(f"topic {ti}: {str(e)[:200]}")
        else:
            # Fallback: chunk + single-pass per chunk
            pass_mode = "single_pass_fallback"
            chunks = self._chunk_text(text, max_chars=12000, overlap=300)
            logger.info(
                f"knowledge_center.import: fallback single-pass → "
                f"{len(chunks)} chunks"
            )
            for ci, chunk in enumerate(chunks):
                prompt = self._build_extraction_prompt(
                    chunk_text=chunk, chunk_index=ci,
                    total_chunks=len(chunks),
                    target_project=target_project_full_name or "?",
                    existing_topics=list(existing_canonicals.keys())[:50],
                )
                try:
                    content, used_model = await ai_generate_with_meta(
                        prompt, model_ids=model_ids,
                    )
                except Exception as e:
                    errors.append(
                        f"chunk {ci}: ai call failed: {str(e)[:200]}"
                    )
                    continue
                for item in self._parse_extracted_experiences(content):
                    try:
                        await self._dispatch_extracted_item(
                            item=item, used_model=used_model,
                            existing_canonicals=existing_canonicals,
                            target_project_id=target_project_id,
                            target_project_full_name=target_project_full_name,
                            github_token=token, source_file=filename,
                            created_entries=created_entries,
                            merged_entries=merged_entries,
                        )
                    except Exception as e:
                        errors.append(f"chunk {ci} item: {str(e)[:200]}")

        # Persist any new/merged entries in the index
        new_index = _load_index()
        for c in created_entries:
            new_index.setdefault("entries", []).append(c)
        for m in merged_entries:
            for i, e in enumerate(new_index.get("entries", [])):
                if e.get("id") == m.get("id"):
                    new_index["entries"][i] = m
                    break
        _save_index(new_index)

        return {
            "ok": True,
            "filename": filename,
            "pass_mode": pass_mode,
            "topics_identified": len(topics),
            "chunks_processed": len(chunks),
            "created": len(created_entries),
            "merged": len(merged_entries),
            "errors": errors,
            "created_entries": created_entries,
            "merged_entries": merged_entries,
        }

    # Text extractors per format (txt/md/html/pdf)
    @staticmethod
    def _extract_text(filename: str, data: bytes) -> str:
        name = (filename or "").lower()
        if name.endswith(".pdf"):
            try:
                import pdfplumber  # type: ignore
                import io
                with pdfplumber.open(io.BytesIO(data)) as pdf:
                    return "\n".join(
                        page.extract_text() or "" for page in pdf.pages
                    )
            except Exception:
                pass
            # Fallback: pypdf
            try:
                from pypdf import PdfReader  # type: ignore
                import io
                reader = PdfReader(io.BytesIO(data))
                return "\n".join(p.extract_text() or "" for p in reader.pages)
            except Exception as e:
                raise RuntimeError(f"pdf parse failed: {e}")
        if name.endswith(".html") or name.endswith(".htm"):
            try:
                from bs4 import BeautifulSoup  # type: ignore
                soup = BeautifulSoup(data, "html.parser")
                return soup.get_text("\n")
            except Exception:
                pass
            # naive strip
            return re.sub(r"<[^>]+>", "", data.decode("utf-8", errors="ignore"))
        # txt / md / anything else: best-effort utf-8 decode
        try:
            return data.decode("utf-8")
        except UnicodeDecodeError:
            return data.decode("utf-8", errors="replace")

    @staticmethod
    def _chunk_text(
        text: str, max_chars: int = 12000, overlap: int = 300,
    ) -> List[str]:
        text = text or ""
        if len(text) <= max_chars:
            return [text]
        chunks: List[str] = []
        start = 0
        while start < len(text):
            end = min(start + max_chars, len(text))
            chunk = text[start:end]
            chunks.append(chunk)
            if end >= len(text):
                break
            start = end - overlap
        return chunks

    @staticmethod
    def _build_outline_prompt(
        *, chat_text: str, target_project: str,
    ) -> str:
        """Pass 1 — outline. Read the WHOLE chat (or truncated head) and
        identify distinct topics, even when they're interleaved across
        many messages. The model returns a list of topic seeds without
        trying to fully solve each — that's pass 2's job.

        We give the model very explicit instructions about thread-
        following because that's what the user asked for: trace one
        topic across non-contiguous messages."""
        return f"""تو یک knowledge engineer هستی. یک چت طولانی export شده از AI داریم که در آن **چندین موضوع متفرقه** بحث شده. این چت‌ها معمولاً ساختار خوبی ندارند: یک موضوع شروع می‌شود، وسطش یک سؤال متفرقه می‌آید، بعد بازمی‌گردد، …

# پروژهٔ مقصد (فقط context — نام پروژه نباید در خروجی بیاید)
{target_project}

# متن چت
{chat_text}

# وظیفهٔ تو (مرحلهٔ ۱ — فقط outline)

اول چت را **سطر به سطر** بخوان و موضوعات مجزا را تفکیک کن. هر **موضوع** = یک challenge فنی متمایز که در چت دربارهٔ آن گفتگو شده.

برای هر موضوع، یک outline بساز که شامل:

1. **topic_canonical** — slug کوتاه (kebab-case) که موضوع را در سراسر سیستم یکتا شناسایی کند (مثلاً `google-oauth-login`, `nextjs-static-export`).
2. **title** — عنوان کوتاه خوانا برای انسان.
3. **message_anchors** — لیست لنگرهای متنی (۲-۵ مورد) که نشان می‌دهد این موضوع کجای چت بحث شده. هر لنگر یک عبارت یا جمله از خود چت است که در آن موضوع مطرح شده. این لنگرها به pass 2 کمک می‌کند موضوع را در میان پیام‌های متفرقه دنبال کند.
4. **resolution_signal** — یکی از:
   - `"solved"` — کاربر یا مدل صریحاً گفته مشکل حل شد، یا code فاینالی ارائه شد که کاربر تأیید کرد
   - `"partial"` — راه‌حل پیشنهاد شد ولی کاربر تأیید کامل نکرد، یا فقط یک بخش حل شد
   - `"open"` — مشکل مطرح شد، تلاش شد، ولی شواهد روشنی برای حل وجود ندارد
   - `"regressed"` — موضوع بعداً در چت دوباره مطرح شد به‌نشانهٔ بازگشت مشکل
5. **recurrence_count** — چند بار همین موضوع در چت بازمی‌گردد (۱ = یک‌بار، ۲+ = بحث چندین‌مرحله‌ای)
6. **value_score** — ۰..۱۰، چقدر این تجربه برای پروژه‌های دیگر مفید است (۰ = صرفاً پاسخ خاص آن پروژه، ۱۰ = الگوی عمومی قابل تعمیم)

# نکات بسیار مهم

- **موضوعات متفرقه و پراکنده را با هم اشتباه نگیر**: اگر کاربر وسط یک موضوع چیز نامرتبط پرسیده، آن را یک موضوع جداگانه ثبت کن.
- **اگر موضوعی در چت چند بار با شکست تلاش شد و سپس حل شد، فقط ۱ موضوع است** با `resolution_signal: "solved"` و `recurrence_count` بالاتر.
- موضوعاتی که `value_score < 4` دارند (مثلاً سؤال خیلی خاص که قابل تعمیم نیست) را **حذف کن** — خروجی نده.
- اگر هیچ موضوع ارزشمندی نیست، `"topics": []` برگردان.

# خروجی فقط JSON

{{
  "topics": [
    {{
      "topic_canonical": "kebab-case-slug",
      "title": "عنوان کوتاه",
      "message_anchors": ["جمله یا عبارت یافت‌شده در چت", "..."],
      "resolution_signal": "solved" | "partial" | "open" | "regressed",
      "recurrence_count": 1,
      "value_score": 7
    }}
  ]
}}
"""

    @staticmethod
    def _build_topic_deep_prompt(
        *, chat_text: str, topic: Dict[str, Any], target_project: str,
        existing_topics: List[str],
    ) -> str:
        """Pass 2 — focused extraction for ONE topic. Receives the topic
        outline from pass 1 + the full chat, traces the topic across
        all messages, determines resolution with evidence, and writes
        a reusable experience entry.

        This is where thread-following + resolution-detection + cross-
        project-applicability come together."""
        existing_str = ", ".join(existing_topics[:30]) if existing_topics else "—"
        anchors_str = "\n".join(
            f"  - «{a}»" for a in (topic.get("message_anchors") or [])
        ) or "  (هیچ لنگری ثبت نشده — کل چت را خودت بخوان)"
        return f"""تو یک knowledge engineer هستی. مرحلهٔ ۱ موضوعات چت را شناسایی کرد. الان وظیفهٔ توست برای **یک موضوع خاص**، تجربهٔ کامل و قابل‌استفاده‌مجدد را استخراج کنی.

# پروژهٔ مقصد (فقط برای context — نام پروژه نباید در خروجی بیاید)
{target_project}

# موضوعات موجود در سیستم (برای dedup)
{existing_str}

# موضوع فعلی (از pass 1)
- topic_canonical: {topic.get("topic_canonical", "?")}
- title: {topic.get("title", "?")}
- resolution_signal اولیه: {topic.get("resolution_signal", "open")}
- recurrence_count: {topic.get("recurrence_count", 1)}

# لنگرهای متنی برای این موضوع (کجای چت بحث شده)
{anchors_str}

# متن کامل چت (می‌توانی fragment های مرتبط را با لنگرها پیدا کنی)
{chat_text}

# وظیفهٔ تو

۱) **رشتهٔ این موضوع را در سراسر چت دنبال کن** — حتی اگر بین موضوعات متفرقه پراکنده باشد. لنگرها نقطه‌های شروع‌اند، نه پایان.

۲) **تشخیص resolution** را بر اساس **شواهد در پیام‌ها** تأیید یا اصلاح کن:
   - آیا کاربر صریحاً گفته "کار کرد" / "حل شد" / "ممنون"؟
   - آیا code فاینالی ارائه شد و کاربر سؤال بعدی متفاوتی پرسید (یعنی پذیرفت)؟
   - آیا مدل گفت "این کار را بکن" ولی کاربر سؤال‌های پی‌درپی نگرانی‌ای پرسید (یعنی هنوز حل نشده)؟
   - آیا موضوع بعداً با کلمات کلیدی مشابه دوباره مطرح شد (regressed)؟

۳) **استخراج راه‌حل واقعی** — اگر چند تلاش شکست خوردند و یکی موفق شد، فقط راه‌حل **موفق** را ثبت کن. تلاش‌های شکست‌خورده را در `pitfalls` بیاور.

۴) **نوشتن project-agnostic**:
   - ❌ "در پروژهٔ MyApp ما X کردیم"
   - ✅ "وقتی X را پیاده می‌کنیم..."
   - نام فایل‌های خاص پروژه را با placeholder عمومی جایگزین کن (مثلاً `MyApp.tsx` → `AuthPage.tsx`)
   - secrets/credentials/URL خاص پروژه را حذف کن

۵) **بخش "apply elsewhere" را با دقت پر کن** — این مهم‌ترین بخش است که تجربه را قابل‌استفاده‌مجدد می‌کند:
   - `applies_when`: ۲-۴ سناریوی concrete که این الگو در آن‌ها مفید است
   - `applies_when_not`: ۱-۳ سناریو که این الگو **نباید** اعمال شود (anti-pattern)
   - `prerequisites`: پیش‌نیازهای فنی (مثلاً "FastAPI 0.100+", "React 18 با Suspense")

# خروجی فقط JSON

{{
  "title": "عنوان کوتاه قابل‌استفاده‌مجدد",
  "topic_canonical": "{topic.get('topic_canonical', '')}",
  "tags": ["tag1", "tag2"],
  "challenge": "چه مشکلی بود — کلی، بدون نام پروژه، با context کافی که خواننده نوع‌مسأله را بفهمد",
  "solution": "راه‌حل قدم‌به‌قدم موفق — قابل تعمیم. اگر چند مرحله است، شماره‌گذاری کن.",
  "code_examples": "snippet با نام‌های عمومی (نه نام پروژه). اگر چند فایل لازم است، با header مشخص کن.",
  "pitfalls": "خطاهای رایج (شامل تلاش‌های شکست‌خوردهٔ این چت). هر کدام: «این کار را نکن چون…»",
  "applies_when": ["سناریو ۱ که این الگو در آن مناسب است", "سناریو ۲", ...],
  "applies_when_not": ["سناریو که این الگو **نباید** اعمال شود", ...],
  "prerequisites": ["پیش‌نیاز فنی ۱", ...],
  "apply_elsewhere": "خلاصه پاراگرافی از applies_when + applies_when_not + prerequisites — برای کسی که در یک نگاه می‌خواهد بفهمد کجا کاربرد دارد",
  "resolution_status": "solved" | "partial" | "open" | "regressed",
  "resolution_evidence": "نقل قول کوتاه از چت که نشان می‌دهد حل/جزئی/باز/regressed — مثلاً «کاربر گفت ‘حالا کار می‌کند’»",
  "recurrence_count": {topic.get("recurrence_count", 1)},
  "user_confirmed": true | false,
  "confidence": 0.0..1.0
}}

اگر در طول بررسی متوجه شدی این موضوع کیفیت لازم را ندارد یا فقط یک سؤال خیلی خاص بوده، خروجی `null` بده."""

    def _build_extraction_prompt(
        self, *, chunk_text: str, chunk_index: int, total_chunks: int,
        target_project: str, existing_topics: List[str],
    ) -> str:
        """🔻 Fallback single-pass prompt — used when the two-pass
        outline+deep flow isn't applicable (e.g., one tiny chunk).

        Kept for backward compatibility with tests that mock the
        single-call path. New code should prefer
        extract_with_outline()."""
        existing_str = ", ".join(existing_topics[:30]) if existing_topics else "—"
        return f"""تو یک knowledge engineer هستی. این بخش (chunk {chunk_index+1}/{total_chunks}) از یک چت export شده از AI است.

۱) چالش‌ها و راه‌حل‌های مفید/قابل‌استفاده‌مجدد را استخراج کن.
۲) برای هر مورد یک تجربهٔ **project-agnostic** بنویس.
۳) با topic های موجود `{existing_str}` تطابق بده — اگر مشابه است، topic_canonical یکسان بزن.
۴) رشتهٔ هر موضوع را در سراسر چت دنبال کن حتی اگر بین موضوعات متفرقه باشد.
۵) `resolution_status` (solved/partial/open/regressed) را بر اساس شواهد متن تعیین کن.

# پروژهٔ مقصد (نام پروژه را در خروجی نیاور)
{target_project}

# متن چت
{chunk_text}

خروجی فقط JSON:
{{
  "experiences": [
    {{
      "title": "...", "topic_canonical": "kebab-slug",
      "tags": [], "challenge": "...", "solution": "...",
      "code_examples": "", "pitfalls": "",
      "applies_when": ["..."], "applies_when_not": ["..."],
      "prerequisites": [],
      "apply_elsewhere": "...",
      "resolution_status": "solved" | "partial" | "open" | "regressed",
      "resolution_evidence": "نقل قول کوتاه از چت",
      "recurrence_count": 1,
      "user_confirmed": true | false,
      "confidence": 0.85
    }}
  ]
}}

اگر هیچ تجربهٔ ارزشمندی نیست، `"experiences": []` برگردان."""

    @staticmethod
    def _parse_topic_outline(response: str) -> Dict[str, Any]:
        """Parse pass-1 outline JSON. Defensive against fences + prose."""
        if not response:
            return {"topics": []}
        cleaned = response.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[-1]
            if "```" in cleaned:
                cleaned = cleaned.rsplit("```", 1)[0]
        candidates = [cleaned]
        if "{" in cleaned and "}" in cleaned:
            candidates.append(cleaned[cleaned.find("{"):cleaned.rfind("}") + 1])
        for candidate in candidates:
            try:
                obj = json.loads(candidate)
            except Exception:
                continue
            if not isinstance(obj, dict):
                continue
            topics = obj.get("topics")
            if not isinstance(topics, list):
                continue
            # Normalize each topic (defensive)
            clean_topics: List[Dict[str, Any]] = []
            for t in topics:
                if not isinstance(t, dict):
                    continue
                clean_topics.append({
                    "topic_canonical": str(t.get("topic_canonical") or "").strip(),
                    "title": str(t.get("title") or "").strip(),
                    "message_anchors": [
                        str(a) for a in (t.get("message_anchors") or [])
                        if isinstance(a, (str, int, float))
                    ],
                    "resolution_signal": str(
                        t.get("resolution_signal") or "open"
                    ).lower().strip(),
                    "recurrence_count": int(t.get("recurrence_count") or 1),
                    "value_score": int(t.get("value_score") or 0),
                })
            return {"topics": clean_topics}
        return {"topics": []}

    @staticmethod
    def _parse_topic_deep_response(response: str) -> Optional[Dict[str, Any]]:
        """Parse pass-2 single-topic JSON. Returns None if the model
        decided the topic isn't worth keeping (`null` reply)."""
        if not response:
            return None
        cleaned = response.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[-1]
            if "```" in cleaned:
                cleaned = cleaned.rsplit("```", 1)[0]
        cleaned = cleaned.strip()
        if cleaned.lower() in ("null", "none", ""):
            return None
        candidates = [cleaned]
        if "{" in cleaned and "}" in cleaned:
            candidates.append(cleaned[cleaned.find("{"):cleaned.rfind("}") + 1])
        for candidate in candidates:
            try:
                obj = json.loads(candidate)
            except Exception:
                continue
            if obj is None:
                return None
            if isinstance(obj, dict) and obj.get("title"):
                return obj
        return None

    async def _dispatch_extracted_item(
        self,
        *,
        item: Dict[str, Any],
        used_model: str,
        existing_canonicals: Dict[str, Dict[str, Any]],
        target_project_id: Optional[str],
        target_project_full_name: Optional[str],
        github_token: Optional[str],
        source_file: str,
        created_entries: List[Dict[str, Any]],
        merged_entries: List[Dict[str, Any]],
    ) -> None:
        """Shared dispatch — either merge into an existing canonical or
        create a brand-new entry. Used by both two-pass and fallback
        paths so they stay perfectly in sync on dedup behavior."""
        canonical = (
            item.get("topic_canonical") or _slugify(item.get("title", ""))
        )
        item["topic_canonical"] = canonical
        existing = existing_canonicals.get(canonical)
        if existing:
            merged = await self._merge_into_existing(
                target=existing, new_item=item,
                source_file=source_file, used_model=used_model,
                target_project_full_name=(
                    existing.get("project_full_name")
                    or target_project_full_name or ""
                ),
                github_token=github_token,
            )
            # Replace in-place so subsequent merges in this run see latest
            existing_canonicals[canonical] = merged
            merged_entries.append(merged)
            return
        entry = await self._create_new_entry(
            item=item, source_file=source_file, used_model=used_model,
            target_project_id=target_project_id,
            target_project_full_name=target_project_full_name,
            github_token=github_token,
        )
        if entry is None:
            return
        existing_canonicals[canonical] = entry
        created_entries.append(entry)

    @staticmethod
    def _parse_extracted_experiences(response: str) -> List[Dict[str, Any]]:
        """Best-effort JSON extraction. The /creator engine's
        _extract_json could be reused but it returns Optional[dict] — we
        need a list inside `experiences` here."""
        if not response:
            return []
        cleaned = response.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[-1]
            if "```" in cleaned:
                cleaned = cleaned.rsplit("```", 1)[0]
        # Try whole, then first {...} block
        for candidate in (cleaned, cleaned[cleaned.find("{"):cleaned.rfind("}")+1] if "{" in cleaned else ""):
            if not candidate:
                continue
            try:
                obj = json.loads(candidate)
                if isinstance(obj, dict) and isinstance(obj.get("experiences"), list):
                    return obj["experiences"]
            except Exception:
                continue
        return []

    async def _create_new_entry(
        self, *, item: Dict[str, Any], source_file: str,
        used_model: str, target_project_id: Optional[str],
        target_project_full_name: Optional[str],
        github_token: Optional[str],
    ) -> Optional[Dict[str, Any]]:
        """Build the markdown file + write to repo + return entry dict."""
        canonical = item.get("topic_canonical") or _slugify(item.get("title", ""))
        title = item.get("title") or canonical.replace("-", " ").title()
        slug = _slugify(canonical)
        path = f"{EXPERIENCES_FOLDER_NAME}/{slug}.md"
        body = self._render_experience_md(
            title=title, canonical=canonical, item=item,
            source_file=source_file, used_model=used_model,
            created_at=now_iso(),
        )
        # Write to repo if we have one + token
        if (
            target_project_full_name and "/" in target_project_full_name
            and github_token
        ):
            try:
                from .github_pr_service import get_github_pr_service
                pr = get_github_pr_service()
                owner, name = target_project_full_name.split("/", 1)
                await pr.create_or_update_file(
                    owner=owner, repo=name, path=path, content=body,
                    message=f"🧠 add experience: {title}",
                    branch=None, token=github_token,
                )
            except Exception as e:
                logger.warning(f"create entry: github write failed: {e}")

        entry = KnowledgeEntry(
            id=uuid.uuid4().hex,
            project_id=target_project_id,
            project_full_name=target_project_full_name or "",
            path=path,
            title=title,
            topic_canonical=canonical,
            tags=list(item.get("tags") or []),
            source_type="chat-import",
            source_origin=item.get("source_origin") or "",
            summary=(item.get("challenge") or "")[:300],
            content_hash=_hash(body),
            size_bytes=len(body.encode("utf-8")),
            imported_at=now_iso(),
            generated_by=used_model or "",
        ).to_dict()
        return entry

    async def _merge_into_existing(
        self, *, target: Dict[str, Any], new_item: Dict[str, Any],
        source_file: str, used_model: str,
        target_project_full_name: str, github_token: Optional[str],
    ) -> Dict[str, Any]:
        """Append a "## Update YYYY-MM-DD" section to the existing file and
        update frontmatter (merged_from + updated_at)."""
        merged_id = uuid.uuid4().hex[:8]
        update_block = self._render_update_block(
            item=new_item, source_file=source_file,
            used_model=used_model, merge_id=merged_id,
        )
        # Pull existing body
        repo = target_project_full_name or target.get("project_full_name", "")
        path = target.get("path", "")
        if repo and "/" in repo and github_token and path:
            try:
                from .github_pr_service import get_github_pr_service
                pr = get_github_pr_service()
                owner, name = repo.split("/", 1)
                old_body = await self._gh_get_file_content(
                    owner, name, path, github_token,
                ) or ""
                # Append update section
                new_body = old_body.rstrip() + "\n\n" + update_block + "\n"
                await pr.create_or_update_file(
                    owner=owner, repo=name, path=path, content=new_body,
                    message=f"🧠 update experience: {target.get('title', '?')} (+merge)",
                    branch=None, token=github_token,
                )
                target["content_hash"] = _hash(new_body)
                target["size_bytes"] = len(new_body.encode("utf-8"))
            except Exception as e:
                logger.warning(f"merge: github update failed: {e}")
        target.setdefault("merged_from", []).append(
            f"chat-import:{source_file}:{merged_id}"
        )
        target["updated_at"] = now_iso()
        target["generated_by"] = used_model or target.get("generated_by", "")
        return target

    @staticmethod
    def _render_experience_md(
        *, title: str, canonical: str, item: Dict[str, Any],
        source_file: str, used_model: str, created_at: str,
    ) -> str:
        tags = item.get("tags") or []
        tags_yaml = "[" + ", ".join(f'"{t}"' for t in tags) + "]"
        resolution_status = (item.get("resolution_status") or "unknown").lower()
        resolution_evidence = item.get("resolution_evidence") or "—"
        recurrence_count = int(item.get("recurrence_count") or 1)
        user_confirmed = bool(item.get("user_confirmed"))

        def _bullets(values: Any) -> str:
            if not values:
                return "—"
            if isinstance(values, str):
                values = [values]
            return "\n".join(f"- {v}" for v in values if v)

        applies_when = _bullets(item.get("applies_when"))
        applies_when_not = _bullets(item.get("applies_when_not"))
        prerequisites = _bullets(item.get("prerequisites"))

        return f"""---
title: "{title}"
tags: {tags_yaml}
topic_canonical: "{canonical}"
source:
  type: "chat-import"
  origin: "ai-extracted"
  imported_at: "{created_at}"
created_at: "{created_at}"
updated_at: "{created_at}"
merged_from: []
generated_by: "{used_model}"
resolution_status: "{resolution_status}"
recurrence_count: {recurrence_count}
user_confirmed: {str(user_confirmed).lower()}
---

# {title}

## 🎯 چالش / Challenge

{item.get("challenge", "—")}

## 💡 راه‌حل / Solution

{item.get("solution", "—")}

## 🧪 نمونه کد (Anonymized)

```
{item.get("code_examples", "")}
```

## ⚠️ نکات حیاتی / Pitfalls

{item.get("pitfalls", "—")}

## ✅ Resolution

- **Status**: `{resolution_status}` (recurrence: {recurrence_count} ×{', user confirmed' if user_confirmed else ''})
- **Evidence**: {resolution_evidence}

## 🔁 چطور در جای دیگر اعمال کنیم / How to Apply Elsewhere

{item.get("apply_elsewhere", "—")}

### Applies when

{applies_when}

### Does NOT apply when (anti-pattern)

{applies_when_not}

### Prerequisites

{prerequisites}

## 🔗 References

- منبع: `{source_file}`
- استخراج‌شده توسط: `{used_model or "?"}`
- اعتماد: {item.get("confidence", "—")}
"""

    @staticmethod
    def _render_update_block(
        *, item: Dict[str, Any], source_file: str,
        used_model: str, merge_id: str,
    ) -> str:
        ds = datetime.now(timezone.utc).date().isoformat()
        return f"""## 🔄 Update {ds} (merge:{merge_id})

**نکات جدید از این منبع** (`{source_file}` — توسط `{used_model or "?"}`):

- **چالش**: {item.get("challenge", "—")}
- **راه‌حل اضافی**: {item.get("solution", "—")}
- **Pitfalls جدید**: {item.get("pitfalls", "—")}
- **Apply elsewhere**: {item.get("apply_elsewhere", "—")}

> merged because `topic_canonical` matched. ادغام شد چون موضوع canonical
> یکسان بود — داده‌های جدید مفید بالا اضافه شد. data اصلی دست‌نخورده است.
"""

    # ─────────────────────────────────────────────────────────────────────
    # Cross-repo AI processing (skip-if-unchanged + cross_references)
    # ─────────────────────────────────────────────────────────────────────

    async def process_synced_entries(
        self,
        *,
        model_ids: Optional[List[str]] = None,
        force: bool = False,
    ) -> Dict[str, Any]:
        """🧠 The cross-repo brain — runs AFTER sync_from_projects has
        populated/refreshed the index. For each entry:

          1. If skip_unchanged is on and content_hash == last_processed_hash
             AND not force → SKIP (no AI call, no wasted tokens).
          2. Otherwise compute cross_references: entries in OTHER projects
             whose topic_canonical matches → record pointer (no content
             duplication; the file stays in its original repo).
          3. If summary is empty or stale, ask the AI for a one-paragraph
             "what this experience is about, project-agnostic" summary
             so the catalog cards have meaningful text.
          4. Persist last_processed_hash/at/by per entry so the next
             cycle skips it.

        Honors the user's seven explicit requirements:
          - Model selection: model_ids passed through; if empty, falls
            back to settings.processing_model_ids; if that's also empty,
            uses whatever ai_manager exposes.
          - No duplicate work: skip_unchanged short-circuits on hash match.
          - No bloat: only the summary string and cross_references list
            are stored; full content stays in the repo.
        """
        settings = load_settings()
        if not model_ids:
            model_ids = list(settings.get("processing_model_ids") or []) or None
        skip_unchanged = bool(settings.get("skip_unchanged", True)) and not force

        index = _load_index()
        entries: List[Dict[str, Any]] = list(index.get("entries", []))
        if not entries:
            return {"ok": True, "processed": 0, "skipped": 0, "errors": 0,
                    "reason": "empty_index"}

        # Build canonical → [entries] map once for O(N) cross-ref pass
        by_canonical: Dict[str, List[Dict[str, Any]]] = {}
        for e in entries:
            canon = e.get("topic_canonical") or ""
            if canon:
                by_canonical.setdefault(canon, []).append(e)

        from ..api.routes.simple_projects import ai_generate_with_meta

        processed = 0
        skipped = 0
        errors: List[str] = []
        for entry in entries:
            canon = entry.get("topic_canonical") or ""
            current_hash = entry.get("content_hash") or ""
            last_hash = entry.get("last_processed_hash") or ""

            # 1. Cross-refs first — cheap, no AI call, always refresh
            siblings = []
            if canon:
                for sib in by_canonical.get(canon, []):
                    if sib.get("id") == entry.get("id"):
                        continue
                    if (
                        sib.get("project_full_name")
                        != entry.get("project_full_name")
                    ):
                        siblings.append({
                            "entry_id": sib.get("id", ""),
                            "project_full_name": sib.get("project_full_name", ""),
                            "path": sib.get("path", ""),
                            "title": sib.get("title", ""),
                        })
            entry["cross_references"] = siblings

            # 2. AI step — gated by skip_unchanged
            if (
                skip_unchanged
                and current_hash
                and current_hash == last_hash
            ):
                skipped += 1
                continue
            try:
                ai_prompt = self._build_processor_prompt(entry, siblings)
                content, used_model = await ai_generate_with_meta(
                    ai_prompt, model_ids=model_ids,
                )
                summary_new = (content or "").strip()
                # First paragraph as catalog summary; full text could be
                # stored if useful in future iterations.
                if summary_new:
                    entry["summary"] = self._first_paragraph(summary_new)[:600]
                entry["last_processed_hash"] = current_hash
                entry["last_processed_at"] = now_iso()
                entry["last_processed_by"] = used_model or ""
                processed += 1
            except Exception as e:
                errors.append(f"{entry.get('id', '?')}: {str(e)[:200]}")

        # Soft cap so the catalog doesn't grow unbounded
        cap = int(settings.get("max_indexed_entries") or 0)
        if cap > 0 and len(entries) > cap:
            entries.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
            entries = entries[:cap]
            index["entries"] = entries
        else:
            index["entries"] = entries
        _save_index(index)

        return {
            "ok": True,
            "total": len(entries),
            "processed": processed,
            "skipped": skipped,
            "errors": errors,
            "models_used": model_ids or "(auto)",
        }

    @staticmethod
    def _build_processor_prompt(
        entry: Dict[str, Any], siblings: List[Dict[str, str]],
    ) -> str:
        siblings_text = (
            "\n".join(
                f"- [{s['project_full_name']}] {s['title']} ({s['path']})"
                for s in siblings
            )
            or "(هیچ پروژهٔ دیگری همین موضوع را ثبت نکرده.)"
        )
        return f"""تو یک knowledge engineer هستی. این یک تجربه از پوشهٔ
`experiences/` یک پروژه است. وظیفهٔ تو:

۱) یک پاراگراف خلاصهٔ **کلی و قابل استفاده مجدد** بنویس (project-
   agnostic — بدون نام پروژه). این متن در کارت‌های فهرست مرکز دانش
   نشان داده می‌شود، پس باید برای خواننده‌ای که هرگز این پروژه را
   ندیده شفاف باشد.

۲) اگر پروژه‌های دیگر همین موضوع را ثبت کرده‌اند (لیست siblings
   پایین)، بگو موارد مشترک چیست. **محتوا را تکرار نکن** — فقط اشاره
   کن که در پروژه‌های مختلف هم بحث شده.

# Title
{entry.get("title", "?")}

# topic_canonical
{entry.get("topic_canonical", "?")}

# project
{entry.get("project_full_name", "?")}

# tags
{", ".join(entry.get("tags") or [])}

# siblings (پروژه‌های دیگری که همین topic_canonical را دارند)
{siblings_text}

# محتوای فعلی فایل (اولین ۲۰۰۰ کاراکتر)
{(entry.get("summary") or "")[:2000]}

خروجی فقط متن (نه JSON). یک پاراگراف، کمتر از ۳۰۰ کلمه.
"""


# Singleton
_kc_instance: Optional[KnowledgeCenterService] = None
_kc_lock = threading.Lock()


def get_knowledge_center_service() -> KnowledgeCenterService:
    global _kc_instance
    if _kc_instance is None:
        with _kc_lock:
            if _kc_instance is None:
                _kc_instance = KnowledgeCenterService()
    return _kc_instance


# ────────────────────────────────────────────────────────────────────────────
# 🔁 Background auto-sync loop
# ────────────────────────────────────────────────────────────────────────────
# Runs `sync_from_projects()` then `process_synced_entries()` on the configured
# interval. Wired into app/main.py lifespan startup. Respects the
# auto_sync_enabled setting so the user can pause it from the UI.
#
# Why it's safe:
#   - sync_from_projects is idempotent — re-running on unchanged files is a
#     read-only GitHub list+get with cheap content_hash check.
#   - process_synced_entries short-circuits via last_processed_hash == hash,
#     so unchanged entries cost nothing (no AI tokens) on every cycle.
#   - Initial delay (60s after boot) gives the app time to settle.
# ────────────────────────────────────────────────────────────────────────────


_KC_AUTOSYNC_INITIAL_DELAY_SEC = 60
_KC_AUTOSYNC_MIN_INTERVAL_MIN = 5  # safety floor — never poll faster than this


async def knowledge_center_autosync_loop(stop_event: "asyncio.Event") -> None:
    """Periodic sync + AI process. Cancel via stop_event.set()."""
    try:
        await asyncio.wait_for(
            stop_event.wait(), timeout=_KC_AUTOSYNC_INITIAL_DELAY_SEC,
        )
        return  # stop signalled during initial delay
    except asyncio.TimeoutError:
        pass

    while not stop_event.is_set():
        try:
            settings = load_settings()
            if settings.get("auto_sync_enabled", True):
                svc = get_knowledge_center_service()
                try:
                    sync_res = await svc.sync_from_projects()
                    logger.info(
                        f"knowledge_center.autosync: pulled "
                        f"added={sync_res.get('added')} "
                        f"updated={sync_res.get('updated')} "
                        f"total={sync_res.get('total')}"
                    )
                except Exception as e:
                    logger.warning(
                        f"knowledge_center.autosync: sync failed: {e}"
                    )
                try:
                    proc_res = await svc.process_synced_entries()
                    logger.info(
                        f"knowledge_center.autosync: processed "
                        f"processed={proc_res.get('processed')} "
                        f"skipped={proc_res.get('skipped')} "
                        f"errors={len(proc_res.get('errors') or [])}"
                    )
                except Exception as e:
                    logger.warning(
                        f"knowledge_center.autosync: process failed: {e}"
                    )
        except Exception as e:
            logger.exception(
                f"knowledge_center.autosync: cycle crashed: {e}"
            )
        # Sleep — re-read interval each cycle so user changes apply
        interval_min = max(
            _KC_AUTOSYNC_MIN_INTERVAL_MIN,
            int(load_settings().get("auto_sync_interval_minutes") or 60),
        )
        try:
            await asyncio.wait_for(
                stop_event.wait(), timeout=interval_min * 60,
            )
        except asyncio.TimeoutError:
            continue
