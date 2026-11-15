"""«جزوه و دفتر کار» + live «what changed» feeds (owner, 2026-11-15 — plan items 9, 10, 11).

Everything is read LIVE from GitHub ``main`` through ``services/repo_docs.py`` (the backend image on
Render has no ``docs/`` folder), so the home page, the help circle and the handbook reader always show
what is on GitHub, with no extra deploy.

    GET /api/handbook/recent                — newest WORKLOG entries + newest commits (home page «تازه‌ها»)
    GET /api/handbook/changes?files=a,b     — commits that touched those files (help circle «تغییراتِ اخیر»)
"""

from __future__ import annotations

import asyncio
import re
from typing import Any

from fastapi import APIRouter, Query

from ...services import repo_docs
from ...services.assistant import WORKLOG_PATH, worklog_sections

router = APIRouter(prefix="/handbook", tags=["Handbook"])

_SAFE_PATH = re.compile(r"^[A-Za-z0-9_\-./\[\]]{1,200}$")


def _signature(body: str) -> str:
    m = re.search(r"\*\*(?:امضا|Signed)[^*]*:\*\*\s*`([^`]+)`\s*·\s*(\d{4}-\d{2}-\d{2})", body)
    return f"{m.group(1)} · {m.group(2)}" if m else ""


@router.get("/recent")
async def recent(limit: int = Query(6, ge=1, le=30)) -> dict[str, Any]:
    entries: list[dict[str, Any]] = []
    source = ""
    try:
        text, source = await asyncio.to_thread(repo_docs.read_text, WORKLOG_PATH)
        for s in reversed(worklog_sections(text)[-limit:]):
            tags = sorted(set(re.findall(r"\*\*\[([A-Z]+)\]\*\*", s["body"])))
            entries.append({"title": s["title"], "signed": _signature(s["body"]), "tags": tags})
    except FileNotFoundError:
        pass
    commits = await asyncio.to_thread(repo_docs.recent_commits, limit * 2)
    return {"worklog": entries, "commits": commits, "source": source, "repo": repo_docs.repo()}


@router.get("/changes")
async def changes(files: str = Query(..., description="comma-separated repo paths"),
                  limit: int = Query(12, ge=1, le=50)) -> dict[str, Any]:
    paths = [p.strip().lstrip("/") for p in files.split(",") if p.strip()][:8]
    paths = [p for p in paths if _SAFE_PATH.match(p) and ".." not in p]
    results = await asyncio.gather(*(asyncio.to_thread(repo_docs.recent_commits, limit, p) for p in paths))
    seen: dict[str, dict[str, Any]] = {}
    for p, commits in zip(paths, results):
        for c in commits:
            item = seen.setdefault(c["sha"], {**c, "files": []})
            item["files"].append(p)
    items = sorted(seen.values(), key=lambda c: c.get("date") or "", reverse=True)[:limit]
    return {"files": paths, "commits": items, "repo": repo_docs.repo()}


# =====================================================================================================
# «جزوه و دفتر کار» — the reader (owner, 2026-11-15, plan item 11; pattern: Detective-1 /handbook, read-only)
# =====================================================================================================
# Documents are DISCOVERED live from GitHub (a new .md in one of these folders appears by itself):
#   docs/handbook/*.md         — جزوه (HANDBOOK first, PROGRESS second, then the rest by title)
#   docs/WORKLOG.md            — دفتر کار
#   docs/supervisor/*.md       — ناظرِ خودکار (README, RUNLOG, OPEN_ITEMS, …)
#   experiences/*.md           — درس‌ها (README excluded)
# plus two documents GENERATED live, so nothing is missed even when nobody wrote a log line:
#   CHANGELOG — every commit on main (any session, model, routine or human), grouped by day
#   ACTIVITY  — what the app's own models did: AI calls per day × model, «اتاق فرمان» runs/verifies, assistant chats
# `order`: "date" (newest matters most — TOC newest first) or "content" (document order).

from fastapi import HTTPException  # noqa: E402
from fastapi.responses import PlainTextResponse  # noqa: E402

_SLUG_RE = re.compile(r"^[A-Za-z0-9_\-]{1,80}$")

SOURCES: list[tuple[str, str, str]] = [
    # (folder, group label, slug prefix)
    ("docs/handbook", "جزوه", ""),
    ("docs/supervisor", "ناظرِ خودکار", "supervisor-"),
    ("experiences", "درس‌ها", "lesson-"),
]
DATE_ORDERED = {"WORKLOG", "PROGRESS", "CHANGELOG", "ACTIVITY", "supervisor-RUNLOG"}
FIRST = {"HANDBOOK": 0, "PROGRESS": 1, "WORKLOG": 2, "OVERSIGHT": 3, "CHANGELOG": 4, "ACTIVITY": 5}
GENERATED = {
    "CHANGELOG": ("🔀 تاریخچهٔ تغییرات (همهٔ کامیت‌ها، خودکار)", "دفتر کار"),
    "ACTIVITY": ("🤖 فعالیتِ مدل‌ها در برنامه (خودکار)", "دفتر کار"),
}


def _title_of(text: str, fallback: str) -> str:
    m = re.search(r"^title:\s*\"?(.+?)\"?\s*$", text[:600], re.M) if text.startswith("---") else None
    if m:
        return m.group(1)
    for line in text.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return fallback


def _catalogue() -> list[dict[str, Any]]:
    docs: list[dict[str, Any]] = []
    for folder, group, prefix in SOURCES:
        for item in repo_docs.list_dir(folder):
            name = item["name"]
            if item["type"] != "file" or not name.endswith(".md"):
                continue
            stem = name[:-3]
            if folder == "experiences" and stem.upper() == "README":
                continue
            slug = prefix + re.sub(r"[^A-Za-z0-9_\-]", "-", stem)
            docs.append({"slug": slug, "path": item["path"], "group": group})
    docs.append({"slug": "WORKLOG", "path": "docs/WORKLOG.md", "group": "دفتر کار"})
    for slug, (_, group) in GENERATED.items():
        docs.append({"slug": slug, "path": None, "group": group, "generated": True})
    for d in docs:
        d["order"] = "date" if d["slug"] in DATE_ORDERED else "content"
    return docs


def _find(slug: str) -> dict[str, Any]:
    if not _SLUG_RE.match(slug or ""):
        raise HTTPException(404, "سند یافت نشد")
    for d in _catalogue():
        if d["slug"] == slug:
            return d
    raise HTTPException(404, "سند یافت نشد")


def _changelog_md(pages: int = 3) -> str:
    commits: list[dict[str, Any]] = []
    for page in range(1, pages + 1):
        batch = repo_docs.commits_page(page, 100)
        commits += batch
        if len(batch) < 100:
            break
    out = ["# 🔀 تاریخچهٔ تغییرات — همهٔ کامیت‌های main",
           "",
           f"خودکار و زنده از GitHub (`{repo_docs.repo()}`)؛ هر تغییری — از هر سشن، مدل، روتین یا انسان — اینجا هست، "
           "حتی اگر در دفتر کار ثبت نشده باشد. کامیت‌های پشت‌سرهمِ `chore(prompt): sync` در یک سطر جمع شده‌اند.",
           ""]
    day = ""
    sync_run = 0

    def flush_sync() -> None:
        nonlocal sync_run
        if sync_run:
            out.append(f"- ⋯ {sync_run} کامیتِ همگام‌سازیِ پرامپت (`chore(prompt): sync`)")
            sync_run = 0

    for c in commits:
        d = (c.get("date") or "")[:10]
        if d != day:
            flush_sync()
            day = d
            out += ["", f"## {d}", ""]
        msg = c.get("message", "")
        if msg.startswith("chore(prompt): sync"):
            sync_run += 1
            continue
        flush_sync()
        out.append(f"- `{c.get('date', '')[11:16]}` [{c['sha']}]({c.get('url', '')}) **{c.get('author', '')}** — {msg}")
    flush_sync()
    if not commits:
        out.append("_(GitHub پاسخ نداد — دوباره تلاش کنید)_")
    return "\n".join(out)


def _activity_md() -> str:
    out = ["# 🤖 فعالیتِ مدل‌ها در برنامه",
           "",
           "خودکار و زنده از دادهٔ خودِ برنامه: هر فراخوانیِ مدل (`ai_logs`)، هر اجرا/تأییدِ «اتاق فرمان» و گفت‌وگوهای «دستیار».", ""]
    try:
        from sqlalchemy import func

        from ...core.database import SessionLocal
        from ...models.ai_log import AILog

        db = SessionLocal()
        try:
            rows = (db.query(func.date(AILog.created_at), AILog.model, AILog.status, func.count(AILog.id),
                             func.coalesce(func.sum(AILog.total_tokens), 0))
                    .group_by(func.date(AILog.created_at), AILog.model, AILog.status)
                    .order_by(func.date(AILog.created_at).desc()).limit(300).all())
        finally:
            db.close()
        out += ["## فراخوانی‌های مدل بر حسبِ روز", "", "| روز | مدل | وضعیت | تعداد | توکن |", "|---|---|---|---|---|"]
        out += [f"| {d} | {m or '?'} | {s or '?'} | {n} | {t} |" for d, m, s, n, t in rows] or ["| — | — | — | 0 | 0 |"]
    except Exception as e:  # noqa: BLE001
        out += [f"_(لاگِ مدل‌ها خوانده نشد: {type(e).__name__})_"]
    try:
        from ...services.oversight_service import get_oversight_service

        svc = get_oversight_service()
        titles = {t.id: t.title for t in svc.tasks}
        reports = sorted(svc.reports, key=lambda r: r.run_at or "", reverse=True)[:60]
        out += ["", "## «اتاق فرمان» — آخرین اجراها و تأییدها", "", "| زمان | پروژه | تسک | نتیجه | مدل |", "|---|---|---|---|---|"]
        out += [f"| {r.run_at[:16]} | {r.project_full_name} | {(titles.get(r.task_id) or r.task_id)[:60]} | {r.status} | {r.model_id or '—'} |"
                for r in reports] or ["| — | — | — | — | — |"]
        scans = [(w.repo_full_name, w.last_scan_at) for w in svc.watched if getattr(w, "last_scan_at", None)]
        if scans:
            out += ["", "### آخرین اسکن‌ها", ""] + [f"- {n}: {t[:16]}" for n, t in sorted(scans, key=lambda x: x[1], reverse=True)]
    except Exception as e:  # noqa: BLE001
        out += ["", f"_(اتاق فرمان خوانده نشد: {type(e).__name__})_"]
    try:
        from ...services import assistant

        convs = assistant.list_conversations()[:20]
        out += ["", "## «دستیار» — آخرین گفت‌وگوها", ""]
        out += [f"- {(c.get('updated_at') or '')[:16]} — {c.get('title')} ({c.get('messages_count')} پیام)" for c in convs] or ["- هنوز گفت‌وگویی نیست"]
    except Exception:  # noqa: BLE001
        pass
    return "\n".join(out)


def _content(d: dict[str, Any]) -> tuple[str, str]:
    if d["slug"] == "CHANGELOG":
        return _changelog_md(), "github"
    if d["slug"] == "ACTIVITY":
        return _activity_md(), "app"
    return repo_docs.read_text(d["path"])


@router.get("/docs")
async def list_docs() -> list[dict[str, Any]]:
    docs = await asyncio.to_thread(_catalogue)
    out = []
    for d in docs:
        title = GENERATED.get(d["slug"], (None,))[0]
        if not title:
            try:
                text, _ = await asyncio.to_thread(repo_docs.read_text, d["path"])
                title = _title_of(text, d["slug"])
            except FileNotFoundError:
                continue
        out.append({**d, "title": title,
                    "github_url": f"https://github.com/{repo_docs.repo()}/blob/{repo_docs.branch()}/{d['path']}" if d["path"] else None})
    groups = ["جزوه", "دفتر کار", "ناظرِ خودکار", "درس‌ها"]
    return sorted(out, key=lambda d: (groups.index(d["group"]) if d["group"] in groups else 9,
                                      FIRST.get(d["slug"], 50), d["title"]))


@router.get("/doc/{slug}")
async def get_doc(slug: str) -> dict[str, Any]:
    d = await asyncio.to_thread(_find, slug)
    try:
        text, source = await asyncio.to_thread(_content, d)
    except FileNotFoundError:
        raise HTTPException(404, "سند یافت نشد")
    return {"slug": slug, "title": GENERATED.get(slug, (None,))[0] or _title_of(text, slug), "content": text,
            "order": d["order"], "group": d["group"], "source": source, "path": d["path"],
            "github_url": f"https://github.com/{repo_docs.repo()}/blob/{repo_docs.branch()}/{d['path']}" if d["path"] else None}


@router.get("/search")
async def search(q: str = Query(..., min_length=2), limit: int = Query(40, ge=1, le=200)) -> dict[str, Any]:
    """Every line that contains the query, in every document (generated ones excluded — they are views of GitHub/app data)."""
    needle = q.strip().lower()
    hits: list[dict[str, Any]] = []
    for d in await asyncio.to_thread(_catalogue):
        if d.get("generated"):
            continue
        try:
            text, _ = await asyncio.to_thread(repo_docs.read_text, d["path"])
        except FileNotFoundError:
            continue
        heading = ""
        for line in text.splitlines():
            if line.startswith("#"):
                heading = line.lstrip("#").strip()
            if needle in line.lower():
                hits.append({"slug": d["slug"], "heading": heading, "line": line.strip()[:300]})
                if len(hits) >= limit:
                    return {"q": q, "hits": hits, "truncated": True}
    return {"q": q, "hits": hits, "truncated": False}


@router.get("/export", response_class=PlainTextResponse)
async def export(slugs: str = Query("", description="comma-separated; empty = every document")) -> PlainTextResponse:
    """One Markdown file of the chosen documents (or all of them) — «خروجی گرفتن»."""
    wanted = [s for s in slugs.split(",") if s.strip()] if slugs else None
    parts = [f"# جزوه و دفتر کار — {repo_docs.repo()}", ""]
    for d in await list_docs():
        if wanted and d["slug"] not in wanted:
            continue
        try:
            text, _ = await asyncio.to_thread(_content, d)
        except FileNotFoundError:
            continue
        parts += ["", "---", "", f"<!-- {d['slug']} — {d['path'] or 'generated'} -->", "", text]
    name = "handbook-all.md" if not wanted else f"handbook-{'-'.join(wanted)[:60]}.md"
    return PlainTextResponse("\n".join(parts), media_type="text/markdown; charset=utf-8",
                             headers={"Content-Disposition": f'attachment; filename="{name}"'})
