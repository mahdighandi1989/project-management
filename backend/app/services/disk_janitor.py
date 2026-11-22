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
#: (PM-INS-0024) the owner: «هشدار وقتی از ۸۵٪ گذشت به تلگرام برود» — the home banner still warns from ALERT_PERCENT
TELEGRAM_ALERT_PERCENT = float(os.environ.get("JANITOR_TELEGRAM_PERCENT", "85"))

#: (kind, directory, unit) — unit "file": each file archived alone; "dir": each sub-directory as one .tar.gz
TARGETS: List[tuple] = [
    ("scan_bundles", "scan_v5_bundles", "file"),
    ("scan_screenshots", "scan_v5_screenshots", "dir"),
    ("inspector_context", "oversight/inspector_context", "file"),
    ("uploads", "oversight/uploads", "file"),
    # (PM-INS-0032) the verifier's screenshots/responses per task — 92MB → 98MB in five days, never left the disk
    # (only «keep the last 5 runs» per task). A task folder untouched for MIN_AGE_DAYS goes to Drive as one .tar.gz.
    ("verify_evidence", "oversight/verify_evidence", "dir"),
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
        out["breakdown"] = breakdown(root)
    except Exception as e:  # noqa: BLE001 — the report must still answer
        out["breakdown"] = {"error": f"{type(e).__name__}: {str(e)[:120]}"}
    try:
        from .oversight_service import last_write_error
        out["last_write_error"] = last_write_error()
    except Exception:  # noqa: BLE001
        pass
    try:  # (PM-INS-0032) free pages inside database.db, the owner's consumer list, and growth since the last snapshots
        out["db_space"] = db_space()
    except Exception as e:  # noqa: BLE001
        out["db_space"] = {"error": f"{type(e).__name__}: {str(e)[:120]}"}
    try:
        out["consumers"] = consumers(out, root)
        out["history"] = record_snapshot(out, root)
        out["growth"] = growth(out["history"])
    except Exception as e:  # noqa: BLE001
        out["consumers_error"] = f"{type(e).__name__}: {str(e)[:120]}"
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
    try:  # PM-INS-0024 «الف»: render_logs past their retention (48 h) and ai_logs past 30 days → Drive → out of the DB
        from . import log_archive
        from ..core.database import SessionLocal as _SL

        def _logs():
            _d = _SL()
            try:
                return log_archive.run(_d)
            finally:
                _d.close()
        result["logs"] = await asyncio.to_thread(_logs)
    except Exception as e:  # noqa: BLE001
        result["errors"].append(f"logs: {type(e).__name__}: {str(e)[:100]}")
    try:  # old oversight reports: full copies to Drive, slim copies stay (services/reports_archive.py)
        from . import reports_archive

        result["reports"] = await reports_archive.run(db)
    except Exception as e:  # noqa: BLE001
        result["errors"].append(f"reports: {type(e).__name__}: {str(e)[:100]}")
    return result


# ---------------------------------------------------------------------------------------------------------------------
# (PM-INS-0024, 2026-11-17) «بگو چه چیزی جا گرفته» + safe cleanup with preview and confirmation
# ---------------------------------------------------------------------------------------------------------------------
CACHE_DIR_NAMES = {"__pycache__", ".cache", "cache", ".pytest_cache", "tmp", ".tmp"}
LOG_SUFFIXES = (".log", ".log.1", ".log.2", ".log.gz", ".jsonl.log")
LOG_MIN_AGE_DAYS = float(os.environ.get("JANITOR_LOG_MIN_AGE_DAYS", "14"))
TMP_MIN_AGE_DAYS = 1.0


def _entries(root: Path, depth: int = 2):
    """Every file and directory down to `depth` levels below root, with its total size."""
    out = []
    stack = [(root, 0)]
    while stack:
        d, lvl = stack.pop()
        try:
            children = list(d.iterdir())
        except OSError:
            continue
        for c in children:
            try:
                if c.is_symlink():
                    continue
                out.append((c, _size(c), lvl + 1, c.is_dir()))
                if c.is_dir() and lvl + 1 < depth:
                    stack.append((c, lvl + 1))
            except OSError:
                continue
    return out


def db_tables(db_path: Optional[Path] = None, n: int = 10) -> List[Dict[str, Any]]:
    """Largest SQLite tables — exact bytes via `dbstat` when the build has it, else row counts only."""
    import sqlite3

    if db_path is None:
        try:
            from ..core.database import DATABASE_PATH
            db_path = Path(DATABASE_PATH)
        except Exception:  # noqa: BLE001
            return []
    if not db_path.is_file():
        return []
    con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True, timeout=5)
    try:
        try:
            rows = con.execute("SELECT name, SUM(pgsize) AS b FROM dbstat GROUP BY name ORDER BY b DESC LIMIT ?",
                               (n,)).fetchall()
            return [{"table": r[0], "bytes": int(r[1] or 0)} for r in rows]
        except sqlite3.Error:
            names = [r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
            out = []
            for t in names:
                try:
                    out.append({"table": t, "rows": con.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0]})
                except sqlite3.Error:
                    continue
            return sorted(out, key=lambda x: -x["rows"])[:n]
    finally:
        con.close()


def breakdown(root: Optional[Path] = None, n: int = 10) -> Dict[str, Any]:
    """The `n` biggest folders and the `n` biggest files on the disk, plus the biggest database tables."""
    root = root or STORAGE_ROOT
    if not root.is_dir():
        return {"top_dirs": [], "top_files": [], "db_tables": [], "root_bytes": 0}
    ents = _entries(root, depth=2)
    rel = lambda p: str(p.relative_to(root))  # noqa: E731
    top_dirs = sorted((e for e in ents if e[3]), key=lambda e: -e[1])[:n]
    files = []
    for f in root.rglob("*"):
        try:
            if f.is_file() and not f.is_symlink():
                files.append((f, f.stat().st_size))
        except OSError:
            continue
    files.sort(key=lambda x: -x[1])
    try:
        tables = db_tables(n=n)
    except Exception as e:  # noqa: BLE001
        tables = [{"error": f"{type(e).__name__}: {str(e)[:100]}"}]
    return {
        "root_bytes": sum(e[1] for e in ents if e[2] == 1),
        "top_dirs": [{"path": rel(p), "bytes": b} for p, b, _l, _d in top_dirs],
        "top_files": [{"path": rel(p), "bytes": b} for p, b in files[:n]],
        "db_tables": tables,
    }


def cleanup_preview(root: Optional[Path] = None) -> Dict[str, Any]:
    """What a SAFE cleanup would touch — nothing changes here. Kinds:
      * cache — re-creatable caches and stale temp files: removed in place;
      * log   — log files older than LOG_MIN_AGE_DAYS: archived to Drive, then removed;
      * old_artifact — what the 6-hourly janitor would archive (scan bundles/screenshots/uploads older than MIN_AGE_DAYS):
        archived to Drive, then removed.
    The database and the JSON stores are never candidates."""
    root = root or STORAGE_ROOT
    items: List[Dict[str, Any]] = []
    if not root.is_dir():
        return {"root": str(root), "items": [], "bytes": 0}
    now = time.time()

    def add(p: Path, kind: str, action: str):
        try:
            age = (now - p.stat().st_mtime) / 86400
            items.append({"path": str(p.relative_to(root)), "kind": kind, "action": action,
                          "bytes": _size(p), "age_days": round(age, 1)})
        except OSError:
            pass

    seen: set = set()
    for p in root.rglob("*"):
        try:
            if p.is_symlink() or any(str(p).startswith(s + os.sep) for s in seen):
                continue
            if p.is_dir() and p.name in CACHE_DIR_NAMES:
                seen.add(str(p))
                add(p, "cache", "delete")
            elif p.is_file() and (p.name.endswith(".tmp") or p.name.endswith(".partial")) \
                    and (now - p.stat().st_mtime) > TMP_MIN_AGE_DAYS * 86400:
                add(p, "cache", "delete")
            elif p.is_file() and p.name.endswith(LOG_SUFFIXES) and (now - p.stat().st_mtime) > LOG_MIN_AGE_DAYS * 86400:
                add(p, "log", "archive")
        except OSError:
            continue
    for kind, rel_dir, unit in TARGETS:
        d = root / rel_dir
        if not d.is_dir():
            continue
        for it in sorted(d.iterdir()):
            try:
                if it.name.endswith(".tmp") or (unit == "file" and not it.is_file()) or (unit == "dir" and not it.is_dir()):
                    continue
                if _old(it, MIN_AGE_DAYS):
                    add(it, "old_artifact", "archive")
            except OSError:
                continue
    items.sort(key=lambda x: -x["bytes"])
    return {"root": str(root), "items": items, "bytes": sum(i["bytes"] for i in items),
            "log_min_age_days": LOG_MIN_AGE_DAYS, "artifact_min_age_days": MIN_AGE_DAYS}


def cleanup_apply(paths: List[str], db=None, root: Optional[Path] = None) -> Dict[str, Any]:
    """Act ONLY on paths that a fresh preview still lists (no arbitrary path can be sent). «archive» items go to Drive
    first and are removed only when Drive confirmed the copy; Drive not connected ⇒ they stay."""
    root = root or STORAGE_ROOT
    allowed = {i["path"]: i for i in cleanup_preview(root)["items"]}
    res: Dict[str, Any] = {"removed": 0, "freed": 0, "kept": [], "skipped": [], "errors": [], "drive": False}
    own_db = False
    try:
        from . import gdrive

        if db is None:
            from ..core.database import SessionLocal
            db, own_db = SessionLocal(), True
        res["drive"] = bool(gdrive.is_connected(db))
    except Exception as e:  # noqa: BLE001
        res["errors"].append(f"drive: {type(e).__name__}")
    try:
        for rp in paths or []:
            it = allowed.get(rp)
            if it is None:
                res["skipped"].append(rp)
                continue
            p = root / rp
            try:
                if it["action"] == "archive":
                    if not res["drive"]:
                        res["kept"].append(rp)
                        continue
                    if not _archive_item(db, it["kind"], p):
                        res["kept"].append(rp)
                        continue
                shutil.rmtree(p) if p.is_dir() else p.unlink()
                res["removed"] += 1
                res["freed"] += it["bytes"]
            except Exception as e:  # noqa: BLE001
                res["errors"].append(f"{rp}: {str(e)[:120]}")
    finally:
        if own_db:
            db.close()
    return res


def _mb(b: int) -> str:
    return f"{b / 1048576:.1f}MB"


def telegram_alert(rep: Dict[str, Any]) -> Optional[str]:
    """(PM-INS-0024) the Telegram message — only when the disk passed TELEGRAM_ALERT_PERCENT (or a data write failed),
    with the biggest consumers in it so the owner knows what to clean without opening the app."""
    pct = rep.get("percent")
    if rep.get("last_write_error"):
        return f"نوشتنِ دادهٔ اتاق فرمان شکست خورد: {rep['last_write_error']}"
    if pct is None or pct < TELEGRAM_ALERT_PERCENT:
        return None
    lines = [f"دیسکِ سرور {pct}% پر است (آستانه {TELEGRAM_ALERT_PERCENT:g}%) — آزاد: {_mb(rep.get('free') or 0)}"]
    if not (rep.get("last_run") or {}).get("drive", True):
        lines.append("گوگل درایو وصل نیست — بایگانیِ خودکار ممکن نیست")
    top = (rep.get("breakdown") or {}).get("top_files") or []
    if top:
        lines.append("بزرگ‌ترین‌ها: " + "، ".join(f"{t['path']} {_mb(t['bytes'])}" for t in top[:5]))
    lines.append("پاک‌سازیِ امن (پیش‌نمایش ← تأیید): اتاق فرمان ← خلاصهٔ یک‌صفحه‌ای ← دیسک")
    return "\n".join(lines)


def needs_alert(rep: Dict[str, Any]) -> Optional[str]:
    pct = rep.get("percent")
    if pct is not None and pct >= ALERT_PERCENT:
        return f"دیسکِ سرور {pct}% پر است" + ("" if (rep.get("last_run") or {}).get("drive") else " و گوگل درایو وصل نیست — بایگانی ممکن نیست")
    if rep.get("last_write_error"):
        return f"نوشتنِ دادهٔ اتاق فرمان شکست خورد: {rep['last_write_error']}"
    return None


# ---------------------------------------------------------------------------------------------------------------------
# (PM-INS-0032, 2026-11-22) «دیسک دوباره دارد پر می‌شود» — a permanent gauge, the consumer list the owner named, growth
# over time (snapshots), free pages inside database.db, a guarded VACUUM, and in-app search of what went to Drive.
# ---------------------------------------------------------------------------------------------------------------------
import json as _json
import threading as _threading

HISTORY_FILE = "disk_history.json"
HISTORY_MAX = 120                 # one snapshot every ≥ 6 h ⇒ ~30 days
HISTORY_EVERY_S = 6 * 3600
#: the margin kept free while a VACUUM rewrites the database through the WAL (and tasks.json's tmp copy still fits)
VACUUM_MARGIN = 64 * 1048576

#: (label, relative paths) — the owner's list in PM-INS-0032, in their order; whatever is left is «سایر»
CONSUMER_GROUPS: List[tuple] = [
    ("پایگاه‌داده (database.db)", ["database.db"]),
    ("WAL ِ پایگاه‌داده", ["database.db-wal", "database.db-shm", "database.db-journal"]),
    ("tasks.json (تسک‌های اتاق فرمان)", ["oversight/tasks.json"]),
    ("reports.json (گزارش‌های اتاق فرمان)", ["oversight/reports.json"]),
    ("شواهدِ راستی‌آزمایی (verify_evidence)", ["oversight/verify_evidence"]),
    ("نتیجه‌های اسکن و ساختار", ["oversight/scan_results", "oversight/structure", "scan_v5_bundles"]),
    ("اسکرین‌شات‌ها", ["scan_v5_screenshots", "screenshots", "oversight/screenshots"]),
    ("نمایهٔ مرکزِ دانش", ["oversight/knowledge_center.json", "knowledge_center", "oversight/knowledge_center"]),
    ("کلون‌های مخزن و workspaces", ["workspaces", "repos", "repo_cache", "clones", "projects"]),
    ("سایرِ JSONهای اتاق فرمان", ["oversight/extractions.json", "oversight/watched_projects.json",
                                  "oversight/upload_sessions.json"]),
]


def db_space(db_path: Optional[Path] = None) -> Dict[str, Any]:
    """Pages inside the SQLite file: what is in use and what is free (deleted rows leave free pages that only a VACUUM
    gives back to the disk — after the 24 log move the file stayed 508MB)."""
    import sqlite3

    if db_path is None:
        from ..core.database import DATABASE_PATH
        db_path = Path(DATABASE_PATH)
    if not db_path.is_file():
        return {}
    con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True, timeout=5)
    try:
        q = lambda s: con.execute(s).fetchone()[0]  # noqa: E731
        ps, pc, fl = int(q("PRAGMA page_size")), int(q("PRAGMA page_count")), int(q("PRAGMA freelist_count"))
        jm, av = str(q("PRAGMA journal_mode")), int(q("PRAGMA auto_vacuum"))
    finally:
        con.close()
    wal = Path(str(db_path) + "-wal")
    return {"file_bytes": db_path.stat().st_size, "page_size": ps, "page_count": pc, "free_pages": fl,
            "free_bytes": fl * ps, "used_bytes": (pc - fl) * ps, "wal_bytes": wal.stat().st_size if wal.is_file() else 0,
            "journal_mode": jm, "auto_vacuum": av}


def consumers(rep: Dict[str, Any], root: Optional[Path] = None) -> List[Dict[str, Any]]:
    """The owner's groups with their bytes (largest first) + «سایر»; database.db carries its free pages beside it."""
    root = root or STORAGE_ROOT
    out: List[Dict[str, Any]] = []
    counted = 0
    for label, rels in CONSUMER_GROUPS:
        b = 0
        for r in rels:
            p = root / r
            try:
                b += _size(p) if p.exists() and not p.is_symlink() else 0
            except OSError:
                continue
        counted += b
        row: Dict[str, Any] = {"label": label, "paths": rels, "bytes": b}
        if rels == ["database.db"]:
            ds = rep.get("db_space") or {}
            if ds.get("free_bytes") is not None:
                row["free_inside"] = ds["free_bytes"]
        out.append(row)
    rb = (rep.get("breakdown") or {}).get("root_bytes")
    if isinstance(rb, int) and rb > counted:
        out.append({"label": "سایر", "paths": [], "bytes": rb - counted})
    return sorted(out, key=lambda x: -x["bytes"])


def _history_path(root: Path) -> Path:
    return root / HISTORY_FILE


def record_snapshot(rep: Dict[str, Any], root: Optional[Path] = None, *, force: bool = False) -> List[Dict[str, Any]]:
    """Keep one small snapshot every ≥ 6 h (percent, free, each consumer) so «what grew since …» has an answer."""
    root = root or STORAGE_ROOT
    p = _history_path(root)
    try:
        hist = _json.loads(p.read_text(encoding="utf-8")) if p.is_file() else []
    except (OSError, ValueError):
        hist = []
    now = time.time()
    if force or not hist or now - float(hist[-1].get("ts") or 0) >= HISTORY_EVERY_S:
        snap = {"ts": int(now), "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now)),
                "percent": rep.get("percent"), "free": rep.get("free"), "used": rep.get("used"),
                "db_free_pages": (rep.get("db_space") or {}).get("free_bytes"),
                "groups": {c["label"]: c["bytes"] for c in rep.get("consumers") or []}}
        hist = (hist + [snap])[-HISTORY_MAX:]
        try:
            if root.is_dir():
                tmp = p.with_suffix(".tmp")
                tmp.write_text(_json.dumps(hist, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
                tmp.replace(p)
        except OSError:
            pass
    return hist


def growth(hist: List[Dict[str, Any]]) -> Dict[str, Any]:
    """First snapshot → last: how each group changed (largest growth first)."""
    if len(hist) < 2:
        return {"since": hist[0]["at"] if hist else None, "groups": [], "note": "تاریخچه تازه شروع شده"}
    a, b = hist[0], hist[-1]
    names = set(a.get("groups") or {}) | set(b.get("groups") or {})
    rows = [{"label": n, "before": (a.get("groups") or {}).get(n, 0), "after": (b.get("groups") or {}).get(n, 0)}
            for n in names]
    for r in rows:
        r["delta"] = r["after"] - r["before"]
    return {"since": a.get("at"), "until": b.get("at"), "percent_before": a.get("percent"),
            "percent_after": b.get("percent"), "groups": sorted(rows, key=lambda r: -r["delta"])}


def status(rep: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """The compact answer for the coordinator and the gauges: %, free, level, top consumers, reclaimable, growth."""
    rep = rep or report()
    pct = rep.get("percent")
    level = "ok" if pct is None or pct < ALERT_PERCENT else ("critical" if pct >= TELEGRAM_ALERT_PERCENT else "warn")
    ds = rep.get("db_space") or {}
    return {
        "percent": pct, "total": rep.get("total"), "used": rep.get("used"), "free": rep.get("free"),
        "level": level, "alert_percent": ALERT_PERCENT, "telegram_percent": TELEGRAM_ALERT_PERCENT,
        "alert": needs_alert(rep),
        "top": [{"label": c["label"], "bytes": c["bytes"], **({"free_inside": c["free_inside"]} if "free_inside" in c else {})}
                for c in (rep.get("consumers") or [])[:6]],
        "db_reclaimable": ds.get("free_bytes"),
        "growth": rep.get("growth"),
        "vacuum": vacuum_plan(rep),
        "last_run": rep.get("last_run"),
    }


# ---- guarded VACUUM ---------------------------------------------------------------------------------------------------
_VAC: Dict[str, Any] = {"state": "idle"}
_VAC_LOCK = _threading.Lock()


def vacuum_plan(rep: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Can a VACUUM run now? In WAL mode it writes the whole compacted database into the WAL first, so the disk needs
    ≈ used pages + tasks.json (its tmp copy is written beside it on every save) + a margin. Nothing changes here."""
    rep = rep or {}
    ds = rep.get("db_space") or db_space()
    if not ds:
        return {"possible": False, "reason": "پایگاه‌داده پیدا نشد"}
    free = rep.get("free")
    if free is None:
        try:
            free = shutil.disk_usage(STORAGE_ROOT if STORAGE_ROOT.exists() else ".").free
        except OSError:
            free = 0
    tasks = STORAGE_ROOT / "oversight" / "tasks.json"
    tasks_b = tasks.stat().st_size if tasks.is_file() else 0
    need = int(ds["used_bytes"] * 1.1) + tasks_b + VACUUM_MARGIN
    try:  # the backup copy goes to /tmp first — on the same disk it needs its own room too
        import tempfile
        from ..core.database import DATABASE_PATH
        if os.stat(tempfile.gettempdir()).st_dev == os.stat(os.path.dirname(DATABASE_PATH) or ".").st_dev:
            need += ds["used_bytes"]
    except Exception:  # noqa: BLE001
        pass
    plan = {"reclaimable": ds["free_bytes"], "db_bytes": ds["file_bytes"], "after_bytes": ds["used_bytes"],
            "needs_free": need, "free": free, "possible": bool(free >= need and ds["free_bytes"] >= 32 * 1048576),
            "state": dict(_VAC)}
    if ds["free_bytes"] < 32 * 1048576:
        plan["reason"] = "فضای آزادِ داخلِ پایگاه‌داده کمتر از ۳۲MB است — ارزشِ VACUUM ندارد"
    elif not plan["possible"]:
        plan["reason"] = (f"برای VACUUM ِ امن {_mb(need)} فضای آزاد لازم است (≈ دادهٔ زندهٔ پایگاه‌داده ×۱٫۱ در WAL + "
                          f"نسخهٔ موقتِ tasks.json + ۶۴MB حاشیه)؛ الان {_mb(free)} آزاد است")
    return plan


def _vacuum_worker(db_path: Path) -> None:
    import gzip
    import sqlite3
    import tempfile

    from . import gdrive
    from ..core.database import SessionLocal

    tmpdir = Path(tempfile.gettempdir())
    copy = tmpdir / f"pm-db-backup-{int(time.time())}.db"
    gz = copy.with_suffix(".db.gz")
    db = SessionLocal()
    try:
        _VAC.update(state="backup", step="نسخهٔ فشرده در /tmp")
        con = sqlite3.connect(str(db_path), timeout=60)
        try:
            con.execute("VACUUM INTO ?", (str(copy),))
        finally:
            con.close()
        with open(copy, "rb") as src, gzip.open(gz, "wb", compresslevel=6) as dst:
            shutil.copyfileobj(src, dst, 1024 * 1024)
        copy.unlink(missing_ok=True)
        _VAC.update(step="آپلودِ پشتیبان به درایو")
        parent = gdrive.ensure_folder(db, ["بایگانیِ سرور", "database_backups"])
        with open(gz, "rb") as fh:
            res = gdrive.upload(db, fh, name=f"database-{time.strftime('%Y%m%d-%H%M%S', time.gmtime())}.db.gz",
                                mime="application/gzip", parent=parent, size=gz.stat().st_size,
                                description="PM-INS-0032 backup before VACUUM")
        if not (res and res.get("id")):
            raise RuntimeError("درایو پشتیبان را تأیید نکرد — VACUUM اجرا نشد")
        _VAC.update(backup={"id": res["id"], "link": res.get("link"), "bytes": gz.stat().st_size})
        gz.unlink(missing_ok=True)
        # re-check the guard right before the rewrite (the disk may have changed during the upload)
        plan = vacuum_plan({"db_space": db_space(db_path)})
        if not plan["possible"]:
            raise RuntimeError(plan.get("reason") or "شرطِ فضای آزاد برقرار نیست")
        _VAC.update(state="vacuum", step="VACUUM")
        before = db_path.stat().st_size
        con = sqlite3.connect(str(db_path), timeout=120)
        try:
            con.execute("PRAGMA busy_timeout=120000")
            con.execute("VACUUM")
            con.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        finally:
            con.close()
        _VAC.update(state="done", step="", before=before, after=db_path.stat().st_size,
                    at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
    except Exception as e:  # noqa: BLE001 — SQLite rolls a failed VACUUM back; the database is untouched
        _VAC.update(state="failed", error=f"{type(e).__name__}: {str(e)[:200]}")
    finally:
        for f in (copy, gz):
            try:
                f.unlink(missing_ok=True)
            except OSError:
                pass
        db.close()


def vacuum_start(confirm: bool) -> Dict[str, Any]:
    """Backup (VACUUM INTO /tmp → gzip → Drive, confirmed) then VACUUM + WAL truncate — only when `vacuum_plan` allows."""
    from . import gdrive
    from ..core.database import DATABASE_PATH, SessionLocal

    plan = vacuum_plan()
    if not confirm:
        return {"started": False, "plan": plan, "reason": "confirm لازم است"}
    if not plan["possible"]:
        return {"started": False, "plan": plan, "reason": plan.get("reason")}
    db = SessionLocal()
    try:
        if not gdrive.is_connected(db):
            return {"started": False, "plan": plan, "reason": "گوگل درایو وصل نیست — بی‌پشتیبان VACUUM نمی‌شود"}
    finally:
        db.close()
    with _VAC_LOCK:
        if _VAC.get("state") in ("backup", "vacuum"):
            return {"started": False, "plan": plan, "reason": "یک VACUUM در جریان است"}
        _VAC.clear()
        _VAC.update(state="backup", started=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
    _threading.Thread(target=_vacuum_worker, args=(Path(DATABASE_PATH),), daemon=True, name="db-vacuum").start()
    return {"started": True, "plan": plan}


# ---- what went to Drive, searchable from the app --------------------------------------------------------------------
ARCHIVE_KINDS = [k for k, _r, _u in TARGETS] + ["database_backups", "render_logs", "ai_logs", "reports"]


def drive_archives(db, q: str = "", kind: str = "", limit: int = 100) -> Dict[str, Any]:
    """Files under «بایگانیِ سرور/<kind>» on Drive, newest first, filtered by a name fragment."""
    import httpx

    from . import gdrive

    if not gdrive.is_connected(db):
        return {"drive": False, "files": []}
    kinds = [kind] if kind else ARCHIVE_KINDS
    files: List[Dict[str, Any]] = []
    errors: List[str] = []
    for k in kinds:
        try:
            fid = gdrive.ensure_folder(db, ["بایگانیِ سرور", k])
            query = f"'{fid}' in parents and trashed = false"
            if q:
                query += f" and (name contains '{gdrive._q(q)}' or fullText contains '{gdrive._q(q)}')"
            r = httpx.get(f"{gdrive.API}/files", params={
                "q": query, "orderBy": "createdTime desc", "pageSize": min(limit, 200),
                "fields": "files(id,name,size,createdTime,webViewLink,description)"}, headers=gdrive._h(db), timeout=30)
            if r.status_code != 200:
                errors.append(f"{k}: HTTP {r.status_code}")
                continue
            for f in r.json().get("files") or []:
                files.append({"kind": k, "id": f["id"], "name": f.get("name"), "bytes": int(f.get("size") or 0),
                              "created": f.get("createdTime"), "link": f.get("webViewLink"),
                              "description": f.get("description") or ""})
        except Exception as e:  # noqa: BLE001
            errors.append(f"{k}: {type(e).__name__}")
    files.sort(key=lambda f: f.get("created") or "", reverse=True)
    return {"drive": True, "files": files[:limit], "errors": errors}
