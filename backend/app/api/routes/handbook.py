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
