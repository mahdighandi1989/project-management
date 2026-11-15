"""Disk janitor — the Render disk is 1 GB and also holds the database (owner decision, 2026-11-15; CLAUDE.md rule 6).

What grows without limit (audit of «اتاق فرمان», docs/handbook/OVERSIGHT.md §12 item 4): scan PDF bundles, scan
screenshots, the inspector's base64 screenshot contexts, finished upload files, and the JSON stores (reports …).

Rule — NOTHING is deleted without an archive copy (CLAUDE.md rules 3 and 6):
  * Google Drive connected ⇒ every old artifact is uploaded to the project's Drive folder
    «project-management/بایگانیِ سرور/<kind>/» (md5 checked by Drive) and only then removed from the disk;
  * Drive not connected ⇒ nothing is removed; the report says so and an alert goes out when the disk is filling.
Only re-creatable caches (an extraction's `full_text_cache`, which duplicates its own segments) are dropped in place.

Runs from the oversight scheduler every 6 h, and on demand (`POST /api/oversight/disk/janitor`).
"""

from __future__ import annotations

import io
import logging
import os
import shutil
import tarfile
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

STORAGE_ROOT = Path(os.environ.get("STORAGE_ROOT", "storage"))
MIN_AGE_DAYS = float(os.environ.get("JANITOR_MIN_AGE_DAYS", "7"))
ALERT_PERCENT = float(os.environ.get("JANITOR_ALERT_PERCENT", "80"))

#: (kind, directory, unit) — unit "file": each file archived alone; "dir": each sub-directory as one .tar.gz
TARGETS: List[tuple] = [
    ("scan_bundles", "scan_v5_bundles", "file"),
    ("scan_screenshots", "scan_v5_screenshots", "dir"),
    ("inspector_context", "oversight/inspector_context", "file"),
    ("uploads", "oversight/uploads", "file"),
]

_last: Dict[str, Any] = {}


def _size(p: Path) -> int:
    if p.is_file():
        return p.stat().st_size
    return sum(f.stat().st_size for f in p.rglob("*") if f.is_file()) if p.is_dir() else 0


def _old(p: Path, min_age_days: float) -> bool:
    newest = p.stat().st_mtime
    if p.is_dir():
        for f in p.rglob("*"):
            newest = max(newest, f.stat().st_mtime)
    return (time.time() - newest) > min_age_days * 86400


def report(root: Optional[Path] = None) -> Dict[str, Any]:
    root = root or STORAGE_ROOT
    out: Dict[str, Any] = {"root": str(root), "kinds": {}}
    try:
        du = shutil.disk_usage(root if root.exists() else ".")
        out.update(total=du.total, used=du.used, free=du.free, percent=round(du.used * 100 / du.total, 1))
    except OSError:
        pass
    for kind, rel, _ in TARGETS:
        d = root / rel
        out["kinds"][kind] = {"bytes": _size(d), "items": len(list(d.iterdir())) if d.is_dir() else 0}
    out["json_stores"] = {f.name: f.stat().st_size for f in sorted((root / "oversight").glob("*.json"))} \
        if (root / "oversight").is_dir() else {}
    out["last_run"] = _last or None
    try:
        from .oversight_service import last_write_error
        out["last_write_error"] = last_write_error()
    except Exception:  # noqa: BLE001
        pass
    return out


def _archive_item(db, kind: str, item: Path) -> bool:
    """Upload one file (or a directory as .tar.gz) to Drive. True only when Drive confirmed it."""
    from . import gdrive

    parent = gdrive.ensure_folder(db, ["بایگانیِ سرور", kind])
    if item.is_dir():
        buf = io.BytesIO()
        with tarfile.open(fileobj=buf, mode="w:gz") as tar:
            tar.add(str(item), arcname=item.name)
        data = buf.getvalue()
        res = gdrive.upload_bytes(db, data, name=f"{item.name}.tar.gz", mime="application/gzip", parent=parent,
                                  description=f"server archive of {kind}/{item.name}")
    else:
        with open(item, "rb") as fh:
            res = gdrive.upload(db, fh, name=item.name, mime="application/octet-stream", parent=parent,
                                size=item.stat().st_size, description=f"server archive of {kind}")
    return bool(res and res.get("id"))


async def drop_extraction_caches() -> int:
    """`full_text_cache` duplicates an extraction's own segments (`full_text()` rebuilds it) — drop it, through the
    in-memory repo so its next save does not write it back."""
    try:
        from .oversight_extraction import get_extraction_repo
    except Exception:  # noqa: BLE001
        return 0
    repo = get_extraction_repo()
    freed = 0
    async with repo._lock:
        for fe in repo._extractions.values():
            if fe.full_text_cache and repo._segments.get(fe.id):
                freed += len(fe.full_text_cache.encode("utf-8"))
                fe.full_text_cache = ""
        if freed:
            repo._save()
    return freed


def run(db=None, root: Optional[Path] = None, min_age_days: Optional[float] = None) -> Dict[str, Any]:
    """Archive-then-remove old artifacts. Returns what was done (also kept for `report()`)."""
    root = root or STORAGE_ROOT
    age = MIN_AGE_DAYS if min_age_days is None else min_age_days
    result: Dict[str, Any] = {"at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "archived": 0, "freed": 0,
                              "errors": [], "drive": False, "kept_without_drive": 0}
    own_db = False
    try:
        from . import gdrive

        if db is None:
            from ..core.database import SessionLocal
            db, own_db = SessionLocal(), True
        result["drive"] = bool(gdrive.is_connected(db))
    except Exception as e:  # noqa: BLE001
        result["errors"].append(f"drive: {type(e).__name__}")
    try:
        for kind, rel, unit in TARGETS:
            d = root / rel
            if not d.is_dir():
                continue
            for item in sorted(d.iterdir()):
                if item.name.endswith(".tmp") or (unit == "file" and not item.is_file()) or (unit == "dir" and not item.is_dir()):
                    continue
                try:
                    if not _old(item, age):
                        continue
                except OSError:
                    continue
                if not result["drive"]:
                    result["kept_without_drive"] += 1
                    continue
                size = _size(item)
                try:
                    if _archive_item(db, kind, item):
                        shutil.rmtree(item) if item.is_dir() else item.unlink()
                        result["archived"] += 1
                        result["freed"] += size
                except Exception as e:  # noqa: BLE001 — keep the file; try next time
                    result["errors"].append(f"{kind}/{item.name}: {str(e)[:120]}")
                    if len(result["errors"]) > 20:
                        break
    finally:
        if own_db:
            db.close()
    _last.clear()
    _last.update(result)
    return result


async def run_all(db=None, root: Optional[Path] = None, min_age_days: Optional[float] = None) -> Dict[str, Any]:
    """The whole janitor: file archiving in a thread (Drive uploads block), then the in-memory cache drop."""
    import asyncio

    result = await asyncio.to_thread(run, db, root, min_age_days)
    try:
        result["freed"] += await drop_extraction_caches()
    except Exception as e:  # noqa: BLE001
        result["errors"].append(f"extractions: {type(e).__name__}")
    return result


def needs_alert(rep: Dict[str, Any]) -> Optional[str]:
    pct = rep.get("percent")
    if pct is not None and pct >= ALERT_PERCENT:
        return f"دیسکِ سرور {pct}% پر است" + ("" if (rep.get("last_run") or {}).get("drive") else " و گوگل درایو وصل نیست — بایگانی ممکن نیست")
    if rep.get("last_write_error"):
        return f"نوشتنِ دادهٔ اتاق فرمان شکست خورد: {rep['last_write_error']}"
    return None
