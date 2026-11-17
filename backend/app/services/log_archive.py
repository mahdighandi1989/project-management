"""Old log rows → Google Drive, then out of the database (PM-INS-0024 «الف», owner decision 2026-11-17).

The 1 GB Render disk was 78.6 % full; the database alone was 485 MB, ~170 MB of it render_logs (+ indexes) and 96 MB ai_logs.
The «retention 48 h» setting of render logs never ran (its cleanup existed only as a manual endpoint) and even when run it
wrote the «archive» back INTO the same database. Now:

* `preview()` — how many rows / bytes each table would move, oldest/newest, nothing changed;
* `run(confirm=True)` — in batches, oldest first: gzipped JSON-lines uploaded to Drive
  («project-management/بایگانیِ سرور/<table>/»); only after Drive confirms are exactly those rows deleted; each file is
  indexed in `log_drive_archives` (time range, count, services/providers, link);
* the 6-hourly disk janitor runs it with the configured retention (render_logs: «retention_hours» of the render-log
  settings, 48 h by default; ai_logs: 30 days) — so the tables stop growing;
* `search()` — finds lines in the archived files (downloads the files that overlap the time range, cached) so the old
  logs stay readable inside the app.

Drive not connected ⇒ nothing is deleted. The database file does not shrink without VACUUM (it needs as much free space
as the whole file); the freed pages are reused, so growth stops.
"""

from __future__ import annotations

import gzip
import json
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

BATCH = 20_000
AI_LOG_DAYS = 30
_CACHE: Dict[str, List[dict]] = {}
_CACHE_ORDER: List[str] = []


def _tables():
    from ..models.ai_log import AILog
    from ..models.render_log import RenderLog
    return {
        "render_logs": (RenderLog, RenderLog.timestamp, "service_id",
                        lambda r: {"id": r.id, "service_id": r.service_id, "service_name": r.service_name,
                                   "timestamp": r.timestamp.isoformat() if r.timestamp else None, "level": r.level,
                                   "message": r.message, "deploy_id": r.deploy_id, "instance_id": r.instance_id}),
        "ai_logs": (AILog, AILog.created_at, "provider",
                    lambda r: {"id": r.id, "provider": r.provider, "model": r.model, "request_type": r.request_type,
                               "prompt": r.prompt, "response": r.response, "project_id": r.project_id,
                               "debate_id": r.debate_id, "input_tokens": r.input_tokens,
                               "output_tokens": r.output_tokens, "total_tokens": r.total_tokens, "cost": r.cost,
                               "latency_ms": r.latency_ms, "status": r.status, "error_message": r.error_message,
                               "created_at": r.created_at.isoformat() if r.created_at else None,
                               "extra_data": r.extra_data}),
    }


def default_cutoffs(db) -> Dict[str, datetime]:
    now = datetime.utcnow()
    hours = 48
    try:
        from ..models.render_log import RenderLogSettings
        s = db.query(RenderLogSettings).first()
        if s and s.retention_hours:
            hours = max(24, int(s.retention_hours))
    except Exception:  # noqa: BLE001
        pass
    return {"render_logs": now - timedelta(hours=hours), "ai_logs": now - timedelta(days=AI_LOG_DAYS)}


def preview(db, cutoffs: Optional[Dict[str, datetime]] = None) -> Dict[str, Any]:
    from sqlalchemy import func
    cutoffs = cutoffs or default_cutoffs(db)
    out: Dict[str, Any] = {}
    for name, (model, ts, _grp, _row) in _tables().items():
        cut = cutoffs.get(name)
        total = db.query(func.count()).select_from(model).scalar() or 0
        if cut is None:
            out[name] = {"total": total, "to_move": 0}
            continue
        q = db.query(func.count(), func.min(ts), func.max(ts)).filter(ts < cut)
        n, oldest, newest = q.one()
        out[name] = {"total": total, "to_move": int(n or 0), "cutoff": cut.isoformat(),
                     "oldest": oldest.isoformat() if oldest else None,
                     "newest_moved": newest.isoformat() if newest else None}
    try:
        from . import gdrive
        out["drive_connected"] = bool(gdrive.is_connected(db))
    except Exception:  # noqa: BLE001
        out["drive_connected"] = False
    return out


def _upload(db, table: str, rows: List[dict], start: datetime, end: datetime) -> Optional[dict]:
    from . import gdrive
    raw = ("\n".join(json.dumps(r, ensure_ascii=False, default=str) for r in rows)).encode("utf-8")
    data = gzip.compress(raw)
    name = f"{table}_{start:%Y%m%d-%H%M%S}_{end:%Y%m%d-%H%M%S}_{len(rows)}.jsonl.gz"
    parent = gdrive.ensure_folder(db, ["بایگانیِ سرور", table])
    res = gdrive.upload_bytes(db, data, name=name, mime="application/gzip", parent=parent,
                              description=f"{len(rows)} rows of {table} from {start} to {end} (PM-INS-0024)")
    if not (res and res.get("id")):
        return None
    return {"id": res["id"], "link": res.get("link") or "", "name": name, "compressed": len(data), "raw": len(raw)}


def run(db, cutoffs: Optional[Dict[str, datetime]] = None, *, max_batches: int = 50,
        force_checkpoint: bool = False) -> Dict[str, Any]:
    """Archive-then-delete, oldest first. Synchronous (call it in a thread). Stops at the first Drive failure."""
    from . import gdrive
    from ..models.render_log import LogDriveArchive
    cutoffs = cutoffs or default_cutoffs(db)
    if not gdrive.is_connected(db):
        return {"ok": False, "reason": "گوگل درایو وصل نیست — هیچ چیزی حذف نشد"}
    result: Dict[str, Any] = {"ok": True}
    for name, (model, ts, grp, to_row) in _tables().items():
        cut = cutoffs.get(name)
        moved = files = 0
        err = None
        if cut is not None:
            for _ in range(max_batches):
                batch = db.query(model).filter(ts < cut).order_by(ts.asc()).limit(BATCH).all()
                if not batch:
                    break
                rows = [to_row(r) for r in batch]
                start = getattr(batch[0], ts.key)
                end = getattr(batch[-1], ts.key)
                try:
                    up = _upload(db, name, rows, start, end)
                except Exception as e:  # noqa: BLE001
                    up, err = None, f"{type(e).__name__}: {str(e)[:200]}"
                if not up:
                    err = err or "درایو آپلود را تأیید نکرد"
                    break
                ids = [r.id for r in batch]
                for i in range(0, len(ids), 500):
                    db.query(model).filter(model.id.in_(ids[i:i + 500])).delete(synchronize_session=False)
                groups = sorted({str(getattr(r, grp) or "") for r in batch} - {""})
                db.add(LogDriveArchive(table_name=name, start_time=start, end_time=end, rows_count=len(batch),
                                       services=",".join(groups)[:4000], drive_id=up["id"], drive_link=up["link"],
                                       file_name=up["name"], compressed_bytes=up["compressed"], raw_bytes=up["raw"]))
                db.commit()
                moved += len(batch)
                files += 1
        result[name] = {"moved": moved, "files": files, "error": err}
        if err:
            result["ok"] = False
    # the deletes land in the WAL first — give that space back to the disk (no data is lost; the database file itself keeps
    # its free pages and reuses them, so it stops growing)
    if any(isinstance(v, dict) and v.get("moved") for v in result.values()) or force_checkpoint:
        try:
            from sqlalchemy import text
            res = db.execute(text("PRAGMA wal_checkpoint(TRUNCATE)")).fetchone()
            result["wal_checkpoint"] = list(res) if res is not None else None
        except Exception as e:  # noqa: BLE001
            result["wal_checkpoint"] = f"{type(e).__name__}: {str(e)[:100]}"
    logger.info(f"log_archive: {result}")
    return result


def list_archives(db, table: Optional[str] = None, limit: int = 200) -> List[dict]:
    from ..models.render_log import LogDriveArchive
    q = db.query(LogDriveArchive)
    if table:
        q = q.filter(LogDriveArchive.table_name == table)
    rows = q.order_by(LogDriveArchive.start_time.desc()).limit(limit).all()
    return [{"id": a.id, "table": a.table_name, "start": a.start_time.isoformat(), "end": a.end_time.isoformat(),
             "rows": a.rows_count, "services": a.services, "link": a.drive_link, "file": a.file_name,
             "compressed_bytes": a.compressed_bytes, "raw_bytes": a.raw_bytes} for a in rows]


def _load(db, drive_id: str) -> List[dict]:
    if drive_id in _CACHE:
        return _CACHE[drive_id]
    from . import gdrive
    raw = gzip.decompress(gdrive.download_bytes(db, drive_id)).decode("utf-8")
    rows = [json.loads(line) for line in raw.splitlines() if line.strip()]
    _CACHE[drive_id] = rows
    _CACHE_ORDER.append(drive_id)
    while len(_CACHE_ORDER) > 4:
        _CACHE.pop(_CACHE_ORDER.pop(0), None)
    return rows


def search(db, *, table: str = "render_logs", q: str = "", service: str = "", level: str = "",
           since: Optional[datetime] = None, until: Optional[datetime] = None,
           limit: int = 200, max_files: int = 6) -> Dict[str, Any]:
    from ..models.render_log import LogDriveArchive
    a = db.query(LogDriveArchive).filter(LogDriveArchive.table_name == table)
    if since:
        a = a.filter(LogDriveArchive.end_time >= since)
    if until:
        a = a.filter(LogDriveArchive.start_time <= until)
    if service:
        a = a.filter(LogDriveArchive.services.contains(service))
    files = a.order_by(LogDriveArchive.start_time.desc()).limit(max_files).all()
    ql = (q or "").lower()
    hits: List[dict] = []
    for f in files:
        for r in _load(db, f.drive_id):
            text = (r.get("message") or r.get("prompt") or "") + " " + (r.get("response") or "")
            if ql and ql not in text.lower():
                continue
            if service and service not in (r.get("service_id") or r.get("provider") or ""):
                continue
            if level and (r.get("level") or r.get("status") or "") != level:
                continue
            ts = r.get("timestamp") or r.get("created_at") or ""
            if since and ts and ts < since.isoformat():
                continue
            if until and ts and ts > until.isoformat():
                continue
            hits.append(r)
            if len(hits) >= limit:
                break
        if len(hits) >= limit:
            break
    hits.sort(key=lambda r: r.get("timestamp") or r.get("created_at") or "", reverse=True)
    return {"files_searched": len(files), "hits": hits[:limit],
            "note": f"در {len(files)} فایلِ بایگانی جست‌وجو شد" + (" (حداکثر)" if len(files) == max_files else "")}
