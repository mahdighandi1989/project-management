"""🧠 REST endpoints for Knowledge Center (مرکز دانش).

Endpoints:
  GET    /api/knowledge-center/entries        list + search/sort/filter/pagination
  GET    /api/knowledge-center/entries/{id}   single entry
  DELETE /api/knowledge-center/entries/{id}   delete (de-index + optionally repo)
  POST   /api/knowledge-center/sync           pull from all watched repos
  POST   /api/knowledge-center/bootstrap      ensure folders exist on all watched
  POST   /api/knowledge-center/ensure/{wid}   ensure folder for one watched project
  POST   /api/knowledge-center/import         upload chat file → extract + merge
"""

from __future__ import annotations

import logging
from typing import List, Optional

from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile
from pydantic import BaseModel

from ...services.knowledge_center_service import get_knowledge_center_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/knowledge-center", tags=["knowledge-center"])


# ─────────────────────────────────────────────────────────────────────────────
# List + facets
# ─────────────────────────────────────────────────────────────────────────────


@router.get("/entries")
async def list_entries(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    search: str = Query("", description="full-text search on title/summary/tags/project"),
    tag: str = Query("", description="filter by single tag"),
    project_id: str = Query("", description="filter by watched project id"),
    source_type: str = Query("", description="manual / chat-import / claude-code-task"),
    sort: str = Query(
        "updated_desc",
        description="updated_desc | updated_asc | title_asc | title_desc | created_desc | size_desc",
    ),
):
    """List entries with search/sort/filter/pagination (req #5)."""
    svc = get_knowledge_center_service()
    return svc.list_entries(
        page=page, per_page=per_page, search=search, tag=tag,
        project_id=project_id, source_type=source_type, sort=sort,
    )


@router.get("/entries/{entry_id}")
async def get_entry(entry_id: str):
    svc = get_knowledge_center_service()
    entry = svc.get_entry(entry_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="entry_not_found")
    return entry


# ─────────────────────────────────────────────────────────────────────────────
# Delete (req #2)
# ─────────────────────────────────────────────────────────────────────────────


class DeleteEntryRequest(BaseModel):
    delete_from_repo: bool = True


@router.delete("/entries/{entry_id}")
async def delete_entry(
    entry_id: str, payload: Optional[DeleteEntryRequest] = None,
):
    svc = get_knowledge_center_service()
    delete_from_repo = payload.delete_from_repo if payload else True
    return await svc.delete_entry(entry_id, delete_from_repo=delete_from_repo)


# ─────────────────────────────────────────────────────────────────────────────
# Sync + bootstrap
# ─────────────────────────────────────────────────────────────────────────────


@router.post("/sync")
async def sync_entries():
    """Pull every experiences/*.md from every watched repo into the index."""
    svc = get_knowledge_center_service()
    return await svc.sync_from_projects()


@router.post("/bootstrap")
async def bootstrap_all_watched():
    """Create `experiences/` + README in every watched project that lacks it
    (req #3: existing projects)."""
    svc = get_knowledge_center_service()
    return await svc.bootstrap_existing()


@router.post("/ensure/{watched_id}")
async def ensure_folder_for_watched(watched_id: str):
    """Manually trigger folder creation for one watched project."""
    from ...services.oversight_service import get_oversight_service
    osv = get_oversight_service()
    w = next((x for x in osv.watched if x.id == watched_id), None)
    if w is None:
        raise HTTPException(status_code=404, detail="watched_not_found")
    svc = get_knowledge_center_service()
    return await svc.ensure_folder_for_project(
        project_id=w.id, project_full_name=w.repo_full_name,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Import chat file (req #7 — panel upload + format alignment)
# ─────────────────────────────────────────────────────────────────────────────


@router.post("/import")
async def import_chat(
    file: UploadFile = File(...),
    target_project_id: str = Form(""),
    model_ids: str = Form(""),  # comma-separated
):
    """Accept a chat export (txt/md/html/pdf) and extract experiences
    into the target project's experiences/ folder.

    target_project_id is optional. If empty, the entries land in the
    global index without a repo write (user can manually drop them
    later).
    model_ids: comma-separated list. If empty, defaults to all
    available models in the user's setup.
    """
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="empty_file")
    mid_list: List[str] = [
        m.strip() for m in (model_ids or "").split(",") if m.strip()
    ]
    target_full_name: Optional[str] = None
    target_pid: Optional[str] = None
    if target_project_id:
        from ...services.oversight_service import get_oversight_service
        osv = get_oversight_service()
        w = next(
            (x for x in osv.watched if x.id == target_project_id), None,
        )
        if w is not None:
            target_full_name = w.repo_full_name
            target_pid = w.id
    svc = get_knowledge_center_service()
    return await svc.import_chat_file(
        filename=file.filename or "upload.txt",
        content_bytes=content,
        target_project_id=target_pid,
        target_project_full_name=target_full_name,
        model_ids=mid_list or None,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Status
# ─────────────────────────────────────────────────────────────────────────────


@router.get("/status")
async def status():
    """Quick health check + counts for dashboard cards."""
    svc = get_knowledge_center_service()
    res = svc.list_entries(page=1, per_page=1)
    facets = res.get("facets") or {}
    return {
        "ok": True,
        "total_entries": res.get("total", 0),
        "tags_count": len(facets.get("tags") or []),
        "projects_count": len(facets.get("projects") or []),
        "sources": dict(facets.get("sources") or []),
    }
