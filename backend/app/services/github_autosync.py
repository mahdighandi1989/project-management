"""(PM-INS-0014) سینکِ خودکارِ همهٔ پروژه‌های GitHub — بی‌کلیکِ دستی.

پیش از این «سینک خودکار» فقط یک تیک در ``extra_data.sync_settings`` بود که هیچ کدی آن را
اجرا نمی‌کرد؛ پروژه‌ها ماه‌ها روی نسخهٔ کهنه ماندند (قرآن: ۷ فایل در برابرِ صدها). این حلقه
هر چند دقیقه برای هر پروژهٔ ``github_import`` یک درخواستِ سبک می‌زند (آخرین کامیتِ شاخهٔ
پیش‌فرض + برچسبِ خصوصی/عمومی از خودِ GitHub). کامیتِ تازه ⇒ سینکِ افزایشی (فقط فایل‌هایی که
sha شان عوض شده دانلود می‌شوند؛ حذف‌ها هم ثبت و اعمال می‌شوند).

متغیرهای محیطی: ``GITHUB_AUTOSYNC_INTERVAL_SEC`` (پیش‌فرض ۱۸۰)، ``GITHUB_AUTOSYNC_ENABLED``
(``0`` ⇒ خاموش). وضعیت در ``extra_data.github_sync`` ذخیره و روی صفحهٔ پروژه نشان داده می‌شود.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
from datetime import datetime
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

INITIAL_DELAY_SEC = 60


def _interval() -> int:
    try:
        return max(60, int(os.environ.get("GITHUB_AUTOSYNC_INTERVAL_SEC", "") or 180))
    except ValueError:
        return 180


def _enabled() -> bool:
    return (os.environ.get("GITHUB_AUTOSYNC_ENABLED", "1") or "1").strip().lower() not in ("0", "false", "off", "no")


def _now() -> str:
    return datetime.utcnow().isoformat() + "Z"


def _load(project) -> Dict[str, Any]:
    try:
        meta = json.loads(project.extra_data) if project.extra_data else {}
        return meta if isinstance(meta, dict) else {}
    except (ValueError, TypeError):
        return {}


def _known_shas(project, files_paths) -> Dict[str, str]:
    """sha ِ هر فایل از سینکِ قبلی — فقط برای فایل‌هایی که واقعاً در پایگاه هستند."""
    try:
        tree = (json.loads(project.structure) or {}).get("file_tree") or []
    except (ValueError, TypeError):
        tree = []
    have = set(files_paths)
    return {t["path"]: t.get("sha") for t in tree if t.get("path") in have and t.get("sha")}


def _save_state(project_id: str, **fields) -> None:
    from ..core.database import SessionLocal
    from ..models.project import Project

    db = SessionLocal()
    try:
        p = db.query(Project).filter(Project.id == project_id).first()
        if not p:
            return
        meta = _load(p)
        gs = meta.get("github_sync") if isinstance(meta.get("github_sync"), dict) else {}
        priv = fields.pop("private", None)
        if priv is not None:
            meta["private"] = bool(priv)
            meta["private_checked_at"] = _now()
        gs.update(fields)
        meta["github_sync"] = gs
        p.extra_data = json.dumps(meta, ensure_ascii=False)
        db.commit()
    finally:
        db.close()


async def sync_project(project_id: str, *, force: bool = False, trigger: str = "auto") -> Dict[str, Any]:
    """یک پروژه: کامیتِ تازه دارد؟ ⇒ سینکِ افزایشی. ``force`` ⇒ همیشه سینک."""
    from ..core.database import SessionLocal
    from ..models.project import Project, ProjectFile
    from .github_import import get_github_import_service

    db = SessionLocal()
    try:
        p = db.query(Project).filter(Project.id == project_id).first()
        if not p or p.project_type != "github_import":
            return {"success": False, "error": "پروژهٔ GitHub نیست"}
        meta = _load(p)
        owner, repo = meta.get("owner"), meta.get("repo")
        if not owner or not repo:
            return {"success": False, "error": "اطلاعات GitHub ناقص است"}
        paths = [r[0] for r in db.query(ProjectFile.file_path).filter(ProjectFile.project_id == project_id).all()]
        known = _known_shas(p, paths)
        gs = meta.get("github_sync") if isinstance(meta.get("github_sync"), dict) else {}
    finally:
        db.close()

    token = os.environ.get("GITHUB_TOKEN", "") or None
    svc = get_github_import_service()
    access = await svc.check_repo_access(owner, repo, token)
    if not access.get("success"):
        _save_state(project_id, last_checked_at=_now(), error=access.get("error") or "GitHub در دسترس نبود")
        return {"success": False, "error": access.get("error")}
    info = access["repo_info"]
    branch = info.get("default_branch") or "main"
    head = await svc.get_branch_head(owner, repo, branch, token)
    if not force and head and head == gs.get("last_synced_sha"):
        _save_state(project_id, last_checked_at=_now(), head_sha=head, behind=False, error=None,
                    private=info.get("private"))
        return {"success": True, "skipped": True, "reason": "بدونِ کامیتِ تازه", "head_sha": head}

    result = await svc.import_repository(url_or_path=f"{owner}/{repo}", token=token, include_files=True,
                                         known_shas=known)
    if not result.get("success"):
        _save_state(project_id, last_checked_at=_now(), head_sha=head, behind=True,
                    error=result.get("error") or "سینک ناموفق")
        return {"success": False, "error": result.get("error")}
    if result.get("tree_error"):
        _save_state(project_id, last_checked_at=_now(), head_sha=head, behind=True,
                    error=f"درختِ فایل‌ها خوانده نشد: {result['tree_error']}")
        return {"success": False, "error": result["tree_error"]}
    result["sync_trigger"] = trigger
    saved = await svc.save_imported_project(result)
    # (PM-INS-0026) new files ⇒ check the memory against the real stack (stale framework instructions are archived)
    try:
        from .memory_stack_review import review as _review_memory
        db2 = SessionLocal()
        try:
            saved["memory_review"] = _review_memory(db2, project_id)
        finally:
            db2.close()
    except Exception as e:  # noqa: BLE001
        logger.warning(f"memory_stack_review after sync {project_id}: {e}")
    return {**saved, "head_sha": result.get("head_sha"), "skipped": False}


async def sync_all(*, force: bool = False, trigger: str = "auto") -> Dict[str, Any]:
    from ..core.database import SessionLocal
    from ..models.project import Project

    db = SessionLocal()
    try:
        ids = [r[0] for r in db.query(Project.id).filter(Project.project_type == "github_import").all()]
    finally:
        db.close()
    out: Dict[str, Any] = {}
    for pid in ids:
        try:
            out[pid] = await sync_project(pid, force=force, trigger=trigger)
        except Exception as e:  # یک پروژهٔ خراب بقیه را نگه ندارد
            logger.warning(f"github_autosync {pid}: {e}")
            out[pid] = {"success": False, "error": str(e)}
    return out


async def github_autosync_loop(stop_event: "asyncio.Event", interval_seconds: Optional[int] = None) -> None:
    try:
        await asyncio.wait_for(stop_event.wait(), timeout=INITIAL_DELAY_SEC)
        return
    except asyncio.TimeoutError:
        pass
    while not stop_event.is_set():
        if _enabled():
            try:
                res = await sync_all()
                synced = [k for k, v in res.items() if v.get("success") and not v.get("skipped")]
                if synced:
                    logger.info(f"🔄 github_autosync: synced {synced}")
            except Exception as e:
                logger.warning(f"github_autosync loop: {e}")
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=interval_seconds or _interval())
        except asyncio.TimeoutError:
            pass
