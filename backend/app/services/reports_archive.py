"""Old «اتاق فرمان» reports → Google Drive (2026-11-15, owner: «موارد اختیاری را هم انجام بده»).

`reports.json` lives on the 1 GB Render disk and is rewritten on every report. Almost all of its bytes are in a few
heavy fields (the model's raw answer, evidence, verify trace, probe details). Nothing is deleted:

  * once the file passes ``REPORTS_ARCHIVE_MIN_BYTES``, every report older than ``REPORTS_ARCHIVE_MIN_AGE_DAYS`` that is
    not the latest report of its task is uploaded — whole — to Drive («project-management/بایگانیِ سرور/reports/»),
    one gzip JSON per run;
  * only after Drive confirmed the upload are the heavy fields of those reports emptied locally; the report itself
    (status, done/remaining parts, next actions, codex, read/flag) stays in the list, so every counter, filter and
    «latest report of the task» keeps working, and ``archived_to`` says where the full copy is;
  * opening such a report (``GET /api/oversight/reports/{id}``, the verify-trace endpoint) brings the full copy back
    from Drive transparently (`full_report`).

Drive not connected ⇒ nothing changes.
"""

from __future__ import annotations

import asyncio
import gzip
import json
import logging
import os
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

HEAVY_FIELDS = ("raw_response", "evidence", "verify_trace", "ac_probe_details", "config_used")
MIN_BYTES = int(os.environ.get("REPORTS_ARCHIVE_MIN_BYTES", str(5 * 1024 * 1024)))
MIN_AGE_DAYS = float(os.environ.get("REPORTS_ARCHIVE_MIN_AGE_DAYS", "30"))
MAX_PER_RUN = 3000
_CACHE: Dict[str, Dict[str, Dict[str, Any]]] = {}  # drive file id → {report id → full report}; tiny LRU
_CACHE_ORDER: List[str] = []


def _parse(ts: str) -> Optional[datetime]:
    try:
        d = datetime.fromisoformat((ts or "").replace("Z", "+00:00"))
        return d if d.tzinfo else d.replace(tzinfo=timezone.utc)
    except Exception:  # noqa: BLE001
        return None


def _heavy(r: Any) -> bool:
    return any(getattr(r, f, None) for f in HEAVY_FIELDS)


def candidates(reports: List[Any], *, min_age_days: float = MIN_AGE_DAYS, now: Optional[datetime] = None) -> List[Any]:
    """Old, not yet archived, still heavy, and not the latest report of its task."""
    now = now or datetime.now(timezone.utc)
    cutoff = now - timedelta(days=min_age_days)
    latest: Dict[str, str] = {}
    for r in reports:
        if (r.run_at or "") > latest.get(r.task_id, ""):
            latest[r.task_id] = r.run_at or ""
    out = []
    for r in reports:
        if getattr(r, "archived_to", None) or not _heavy(r):
            continue
        d = _parse(r.run_at)
        if d is None or d >= cutoff or (r.run_at or "") == latest.get(r.task_id):
            continue
        out.append(r)
        if len(out) >= MAX_PER_RUN:
            break
    return out


async def run(db=None, *, min_bytes: int = MIN_BYTES, min_age_days: float = MIN_AGE_DAYS) -> Dict[str, Any]:
    from . import oversight_service as OS

    result: Dict[str, Any] = {"archived": 0, "skipped": "", "drive_id": ""}
    try:
        size = OS.REPORTS_FILE.stat().st_size
    except OSError:
        size = 0
    if size < min_bytes:
        result["skipped"] = f"reports.json {size} B < {min_bytes} B"
        return result
    own_db = False
    from . import gdrive

    if db is None:
        from ..core.database import SessionLocal

        db, own_db = SessionLocal(), True
    try:
        if not gdrive.is_connected(db):
            result["skipped"] = "drive not connected"
            return result
        svc = OS.get_oversight_service()
        async with svc._lock:
            picked = candidates(svc.reports, min_age_days=min_age_days)
            payload = [r.to_dict() for r in picked]
        if not payload:
            result["skipped"] = "nothing old enough"
            return result
        data = gzip.compress(json.dumps(payload, ensure_ascii=False, default=str).encode("utf-8"))
        name = f"reports_{time.strftime('%Y%m%d-%H%M%S', time.gmtime())}_{len(payload)}.json.gz"

        def _upload() -> Dict[str, Any]:
            parent = gdrive.ensure_folder(db, ["بایگانیِ سرور", "reports"])
            return gdrive.upload_bytes(db, data, name=name, mime="application/gzip", parent=parent,
                                       description=f"{len(payload)} old oversight reports (full copies)")

        res = await asyncio.to_thread(_upload)
        if not (res and res.get("id")):
            result["skipped"] = "drive did not confirm the upload"
            return result
        stamp = {"drive_id": res["id"], "link": res.get("link") or "", "file": name,
                 "at": datetime.now(timezone.utc).isoformat()}
        ids = {p["id"] for p in payload}
        async with svc._lock:
            for r in svc.reports:
                if r.id in ids and not getattr(r, "archived_to", None):
                    for f in HEAVY_FIELDS:
                        setattr(r, f, "" if f == "raw_response" else ({} if f in ("evidence", "config_used") else []))
                    r.archived_to = dict(stamp)
                    result["archived"] += 1
            svc._save_reports()
        result["drive_id"] = res["id"]
        logger.info(f"reports_archive: {result['archived']} report(s) slimmed, full copies in Drive {name}")
        return result
    finally:
        if own_db:
            db.close()


def _load_archive(db, drive_id: str) -> Dict[str, Dict[str, Any]]:
    if drive_id in _CACHE:
        return _CACHE[drive_id]
    from . import gdrive

    items = json.loads(gzip.decompress(gdrive.download_bytes(db, drive_id)).decode("utf-8"))
    by_id = {d.get("id"): d for d in items if isinstance(d, dict)}
    _CACHE[drive_id] = by_id
    _CACHE_ORDER.append(drive_id)
    while len(_CACHE_ORDER) > 3:
        _CACHE.pop(_CACHE_ORDER.pop(0), None)
    return by_id


async def full_report(report: Dict[str, Any]) -> Dict[str, Any]:
    """The report with its archived heavy fields brought back from Drive (best effort: on failure the slim report
    comes back with ``archive_error``)."""
    arch = report.get("archived_to") or {}
    if not arch.get("drive_id"):
        return report
    from ..core.database import SessionLocal

    def _get() -> Optional[Dict[str, Any]]:
        db = SessionLocal()
        try:
            return _load_archive(db, arch["drive_id"]).get(report.get("id"))
        finally:
            db.close()

    try:
        full = await asyncio.to_thread(_get)
    except Exception as e:  # noqa: BLE001
        return {**report, "archive_error": f"بازیابی از درایو ممکن نشد: {str(e)[:150]}"}
    if not full:
        return {**report, "archive_error": "این گزارش در فایلِ بایگانی پیدا نشد"}
    merged = {**report}
    for f in HEAVY_FIELDS:
        merged[f] = full.get(f, merged.get(f))
    merged["restored_from_archive"] = True
    return merged
