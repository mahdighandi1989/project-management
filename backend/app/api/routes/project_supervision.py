"""(PM-INS-0013) «نظارت و سرکشیِ همان پروژه» (فقط‌خواندنی) + «فیدِ رویدادِ همهٔ پروژه‌ها».

Behind the Google-login wall like every route (no PUBLIC entry). Nothing here writes.
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ...core.database import get_db
from ...services import project_supervision as ps

router = APIRouter(prefix="/project-supervision", tags=["project-supervision"])


@router.get("/repos")
def repos():
    """The repos the tab and the feed cover: every watched repo of «اتاق فرمان» + this one."""
    return {"ok": True, "repos": [{"repo": r, "self": ps.is_self(r)} for r in ps.watched_repos()]}


@router.get("/feed")
def feed(limit: int = Query(60, ge=1, le=300), per_repo: int = Query(12, ge=1, le=50),
         detail: int = Query(6, ge=0, le=20), repo: Optional[str] = Query(None)):
    if repo is not None and not ps.valid_repo(repo):
        raise HTTPException(status_code=400, detail="نامِ مخزن نامعتبر است (owner/name)")
    return ps.event_feed(limit=limit, per_repo=per_repo, detail=detail, repo=repo)


@router.get("/board")
def board(repo: str = Query(..., description="owner/name"), db: Session = Depends(get_db)):
    """One project's supervision, read-only: its live board (ours from the DB, a sibling's from its server when
    configured) + what its repo holds about its supervisor (prompt versions, pending branches, sheet commits)."""
    if not ps.valid_repo(repo):
        raise HTTPException(status_code=400, detail="نامِ مخزن نامعتبر است (owner/name)")
    if ps.is_self(repo):
        from . import inspection as insp

        b = insp.list_reports(status=None, reopen=None, page=None, kind=None, include_filed=False,
                              limit=200, db=db)
        live = {"configured": True, "ok": True, "source": "db", **ps.summarize_board(b, insp.schedule(db=db))}
    else:
        live = ps.remote_board(repo)
    return {"ok": True, "repo": repo, "self": ps.is_self(repo), "live": live, "git": ps.supervisor_in_git(repo)}
