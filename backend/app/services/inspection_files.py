"""Attachments and screenshots on «نظارت و سرکشی» sheets — read them, then MOVE
them to Google Drive and keep nothing here.

WHAT THE OWNER ASKED FOR
------------------------
* «بتونم انواع فایل‌ها و فرمت‌ها رو براش اپلود کنم» — any type.
* the supervisor must read the WHOLE file (sibling rule: «حجم هم باعث نشه ناظر
  نتونه بگه من نمیخونمش»). So the text is extracted ONCE, at upload, and served
  in slices whose progress the server counts.
* «در بک‌اند چیزی رو نگه ندار» — after the work is done the bytes (and the
  extracted text) live in the project's Drive folder with a clear reference,
  and the row keeps only that reference and link.

THE PIPELINE
------------
    browser ──append chunks──▶ spool file on the persistent disk (in flight)
            ──finish──▶ extract text → spool .txt beside it → InspectionFile row
            ──worker──▶ Drive: <ref> — <name>  +  <ref> — <name>.متن.txt
                        verify MD5 → set store='drive' → DELETE both spool files

When Drive is not connected the row says so (``store='pending'`` + reason) and
the worker retries every few minutes; the moment Drive is connected everything
pending moves and the disk is emptied. Nothing is ever silently «kept».

Extraction never reports «no text» when it means «I could not try»:
``ok | empty | unsupported | failed | image | pending`` (and the legacy
``media``, now re-extracted to a transcript) are distinct, each with a
Persian reason, because a reader who cannot tell them apart treats all of them
as «nothing to see».
"""

from __future__ import annotations

import base64
import hashlib
import io
import logging
import os
import queue
import re
import threading
import time
from collections import OrderedDict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Iterator, Optional

logger = logging.getLogger("app.inspection_files")

#: Per-file ceiling. The spool shares the 1 GB Render disk with the database,
#: so this and SPOOL_MAX_MB below are what keep an unconnected Drive from
#: filling it.
MAX_MB = int(os.environ.get("INSPECTION_MAX_FILE_MB", "100"))
MAX_BYTES = MAX_MB * 1024 * 1024
SPOOL_MAX_MB = int(os.environ.get("INSPECTION_SPOOL_MAX_MB", "500"))
#: One appended piece from the browser.
CHUNK_BYTES = 4 * 1024 * 1024

MAX_TEXT_CHARS = int(os.environ.get("INSPECTION_MAX_TEXT_CHARS", str(20_000_000)))
SLICE_CHARS = int(os.environ.get("INSPECTION_SLICE_CHARS", "400000"))
MAX_SLICE_CHARS = int(os.environ.get("INSPECTION_MAX_SLICE_CHARS", "2000000"))

_IMAGE_EXT = (".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp", ".tif", ".tiff",
              ".svg", ".heic", ".heif", ".avif", ".ico")
_MEDIA_EXT = (".mp3", ".wav", ".ogg", ".oga", ".m4a", ".aac", ".flac", ".opus", ".webm",
              ".mp4", ".mov", ".mkv", ".avi", ".m4v", ".3gp")
_TEXTY_EXT = (".txt", ".md", ".markdown", ".csv", ".tsv", ".json", ".yaml", ".yml",
              ".xml", ".html", ".htm", ".log", ".ini", ".cfg", ".toml", ".sql",
              ".py", ".js", ".ts", ".tsx", ".jsx", ".css", ".sh", ".bat", ".rst",
              ".env.example", ".srt", ".vtt", ".rtf")


# ---------------------------------------------------------------------------
# naming
# ---------------------------------------------------------------------------
def safe_filename(name: str) -> str:
    """Safe for Drive and a URL, still recognisable (Persian is KEPT)."""
    name = (name or "").strip().replace("\\", "/").split("/")[-1]
    name = re.sub(r"[\x00-\x1f\r\n\t]", "", name)
    name = re.sub(r'[<>:"|?*]', "_", name).strip(" .")
    return (name or "file")[:200]


def report_ref(number: int) -> str:
    return f"PM-INS-{int(number):04d}"


def file_ref(number: int, index: int) -> str:
    return f"{report_ref(number)}-F{int(index):02d}"


def shot_ref(number: int, index: int) -> str:
    return f"{report_ref(number)}-S{int(index):02d}"


def human_size(n: int) -> str:
    n = float(int(n or 0))
    for unit in ("بایت", "کیلوبایت", "مگابایت", "گیگابایت"):
        if n < 1024 or unit == "گیگابایت":
            return f"{n:.0f} {unit}" if unit == "بایت" else f"{n:.1f} {unit}"
        n /= 1024.0
    return f"{n:.1f} گیگابایت"


# ---------------------------------------------------------------------------
# spool — the ONLY place bytes touch this server, and only while in flight
# ---------------------------------------------------------------------------
def spool_dir() -> Path:
    base = os.environ.get("INSPECTION_SPOOL_DIR")
    if not base:
        from ..core.database import DATABASE_DIR

        base = os.path.join(DATABASE_DIR, "inspection_spool")
    p = Path(base)
    p.mkdir(parents=True, exist_ok=True)
    return p


def spool_usage() -> dict:
    total, count = 0, 0
    try:
        for f in spool_dir().iterdir():
            if f.is_file():
                total += f.stat().st_size
                count += 1
    except OSError:
        pass
    return {"bytes": total, "files": count, "label": human_size(total),
            "limit_mb": SPOOL_MAX_MB}


def spool_has_room(incoming: int) -> bool:
    return spool_usage()["bytes"] + max(0, int(incoming)) <= SPOOL_MAX_MB * 1024 * 1024


def _rm(path: str) -> None:
    if path:
        try:
            Path(path).unlink(missing_ok=True)
        except OSError as exc:
            logger.warning("could not remove spool file %s: %s", path, exc)


def digests(path: str) -> tuple[str, str, int]:
    sha, md5, size = hashlib.sha256(), hashlib.md5(), 0  # noqa: S324 - md5 = Drive integrity check
    with open(path, "rb") as fh:
        for piece in iter(lambda: fh.read(1024 * 1024), b""):
            sha.update(piece)
            md5.update(piece)
            size += len(piece)
    return sha.hexdigest(), md5.hexdigest(), size


# ---------------------------------------------------------------------------
# text extraction
# ---------------------------------------------------------------------------
def _pdf_text(data: bytes) -> tuple[str, int, int]:
    """Text per page, the page count, and HOW MANY PAGES ACTUALLY HAD TEXT —
    the page markers are themselves text, so a scanned PDF must not pass as
    readable because of them."""
    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(data))
    parts: list[str] = []
    with_text = 0
    total = 0
    for i, page in enumerate(reader.pages, start=1):
        try:
            t = page.extract_text() or ""
        except Exception as exc:  # one broken page must not lose the rest
            t = f"[صفحهٔ {i} خوانده نشد: {type(exc).__name__}]"
        if t.strip():
            with_text += 1
        chunk = f"\n--- صفحهٔ {i} ---\n{t}"
        parts.append(chunk)
        total += len(chunk)
        if total > MAX_TEXT_CHARS:
            parts.append(f"\n[استخراج در صفحهٔ {i} به سقفِ {MAX_TEXT_CHARS} نویسه رسید]")
            break
    return "".join(parts), len(reader.pages), with_text


def _docx_text(data: bytes) -> str:
    from docx import Document

    doc = Document(io.BytesIO(data))
    out: list[str] = [p.text for p in doc.paragraphs]
    for ti, table in enumerate(doc.tables, start=1):  # forms carry their content in tables
        out.append(f"\n--- جدولِ {ti} ---")
        for row in table.rows:
            cells = [c.text.strip() for c in row.cells]
            if any(cells):
                out.append(" | ".join(cells))
    return "\n".join(x for x in out if x is not None)


def _xlsx_text(data: bytes) -> str:
    from openpyxl import load_workbook

    wb = load_workbook(io.BytesIO(data), read_only=True, data_only=True)
    out: list[str] = []
    total = 0
    for ws in wb.worksheets:
        out.append(f"\n--- کاربرگِ «{ws.title}» ---")
        for row in ws.iter_rows(values_only=True):
            cells = ["" if v is None else str(v) for v in row]
            if any(c.strip() for c in cells):
                line = " | ".join(cells).rstrip(" |")
                out.append(line)
                total += len(line)
                if total > MAX_TEXT_CHARS:
                    out.append("[به سقفِ نویسه رسید]")
                    return "\n".join(out)
    return "\n".join(out)


def _pptx_text(data: bytes) -> Optional[str]:
    try:
        from pptx import Presentation  # optional dependency
    except Exception:
        return None
    prs = Presentation(io.BytesIO(data))
    out = []
    for i, slide in enumerate(prs.slides, start=1):
        out.append(f"\n--- اسلایدِ {i} ---")
        for shp in slide.shapes:
            if getattr(shp, "has_text_frame", False):
                out.append(shp.text_frame.text)
    return "\n".join(out)


def _decode(data: bytes) -> str:
    for enc in ("utf-8-sig", "utf-8", "cp1256", "latin-1"):
        try:
            return data.decode(enc)
        except Exception:
            continue
    return data.decode("utf-8", "replace")


def extract(data: bytes, filename: str, mime: str = "") -> dict:
    """``{status, text, note, page_count, truncated}`` for one file."""
    name = (filename or "").lower()
    mime = (mime or "").lower()
    ext = Path(name).suffix

    def done(status: str, text: str = "", note: str = "", pages: int = 0, truncated: bool = False) -> dict:
        if len(text) > MAX_TEXT_CHARS:
            text = text[:MAX_TEXT_CHARS]
            truncated = True
            note = (note + " " if note else "") + (
                f"متن در {MAX_TEXT_CHARS} نویسه بریده شد — بقیه‌اش فقط در خودِ فایل است، "
                "پس باید خودِ فایل را هم باز کنی")
        return {"status": status, "text": text, "note": note, "page_count": pages, "truncated": truncated}

    from . import inspection_formats as fmt

    def extra() -> Optional[dict]:
        """Every format this function does not read itself — the whole text,
        never a sample (inspection_formats; archive members come back here)."""
        res = fmt.extract_extra(data, filename, mime, base=extract)
        return None if res is None else done(res["status"], res["text"], res["note"],
                                             int(res.get("page_count") or 0), bool(res.get("truncated")))

    try:
        if mime.startswith("image/") or ext in _IMAGE_EXT:
            return done("image", "", "تصویر است — متنی برای استخراج ندارد؛ ناظر باید بازش کند و نگاه کند")
        if mime.startswith(("audio/", "video/")) or ext in _MEDIA_EXT or fmt.is_media(name, mime):
            # was «media» (open it and listen): now «pending» until the FULL
            # transcript exists (inspection_media; POST /files/{id}/extract)
            return extra()
        if ext == ".pdf" or mime == "application/pdf":
            text, pages, with_text = _pdf_text(data)
            if with_text:
                note = f"از {pages} صفحهٔ PDF" + (
                    f" — فقط {with_text} صفحه لایهٔ متنی داشت؛ بقیه احتمالاً اسکن‌اند و باید خودِ فایل دیده شود"
                    if with_text < pages else "")
                return done("ok", text, note, pages, truncated=("به سقفِ" in text or with_text < pages))
            return done("unsupported", "", pages=pages,
                        note=f"PDF {pages} صفحه دارد ولی هیچ صفحه‌ای لایهٔ متنی ندارد (اسکن‌شده) — خودِ فایل را باز کن")
        if ext == ".docx" or "wordprocessingml" in mime:
            text = _docx_text(data)
            return done("ok", text, "از فایلِ Word") if text.strip() else done("empty", "", "فایلِ Word متنی نداشت")
        if ext == ".doc" or mime == "application/msword":
            return extra()
        if ext in (".xlsx", ".xlsm") or "spreadsheetml" in mime:
            text = _xlsx_text(data)
            return done("ok", text, "از کاربرگ") if text.strip() else done("empty", "", "کاربرگ سلولِ پُری نداشت")
        if ext == ".xls" or mime == "application/vnd.ms-excel":
            return extra()
        if ext == ".pptx" or "presentationml" in mime:
            text = _pptx_text(data)
            if text is None:
                return done("unsupported", "", "برای PowerPoint استخراج‌کننده نصب نیست — خودِ فایل را باز کن")
            return done("ok", text, "از PowerPoint") if text.strip() else done("empty", "", "اسلایدها متنی نداشتند")
        if ext == ".rtf" or mime in ("application/rtf", "text/rtf"):
            # the words, not the RTF markup (was: raw `{\\rtf1…` as «plain text»)
            return extra()
        if ext in _TEXTY_EXT or mime.startswith("text/") or mime in ("application/json", "application/xml"):
            text = _decode(data)
            return done("ok", text, "متنِ ساده") if text.strip() else done("empty", "", "فایل خالی است")
        if ext == ".zip" or mime in ("application/zip", "application/x-zip-compressed"):
            # every member, recursively, through its own reader — not a list of names
            return extra()
        found = extra()      # rtf, odt, epub, eml, msg, any real text …
        if found is not None:
            return found
        return done("unsupported", "", f"برای «{ext or mime or 'این نوع'}» استخراج‌کنندهٔ متن نداریم — "
                                       "ناظر باید خودِ فایل را از درایو باز کند و کامل ببیند")
    except Exception as exc:  # noqa: BLE001 - the reason is the useful part
        logger.warning("inspection file extract failed: %s", exc)
        return done("failed", "", f"استخراج شکست خورد: {type(exc).__name__}: {exc}"[:400])


# ---------------------------------------------------------------------------
# Drive push — the step that empties the disk
# ---------------------------------------------------------------------------
def push_file(db, row, report_number: int, report_title: str = "") -> bool:
    """Move one file (and its text sidecar) to Drive. True when it is there.

    Verified, then freed: the spool copy is deleted ONLY after Drive reports the
    same MD5 we computed. A move that cannot be verified keeps the local copy."""
    from . import gdrive

    if row.store == "drive":
        return True
    if not row.spool_path or not Path(row.spool_path).exists():
        row.store, row.store_note = "failed", "فایلِ موقت روی سرور پیدا نشد و در درایو هم نیست"
        return False
    if not gdrive.is_connected(db):
        row.store = "pending"
        row.store_note = ("گوگل درایو هنوز متصل نیست — فایل موقتاً روی دیسکِ سرور منتظر است و به‌محضِ "
                          "اتصال خودکار به پوشهٔ پروژه منتقل و از سرور پاک می‌شود")
        return False
    try:
        parts = gdrive.report_folder_parts(report_number)
        parent = gdrive.ensure_folder(db, parts)
        name = f"{row.ref} — {row.filename}" if row.ref else row.filename
        desc = f"{row.ref} · گزارشِ {report_number}" + (f" — {report_title}" if report_title else "")
        if row.caption:
            desc += f"\nتوضیحِ مالک: {row.caption}"
        with open(row.spool_path, "rb") as fh:
            placed = gdrive.upload(db, fh, name=name, mime=row.mime or "application/octet-stream",
                                   parent=parent, size=int(row.byte_size or 0), description=desc)
        if placed.get("md5") and row.md5 and placed["md5"] != row.md5:
            row.store = "failed"
            row.store_note = "تطابقِ MD5 با درایو نشد — نسخهٔ موقت نگه داشته شد تا دوباره تلاش شود"
            return False
        text_id, text_link = "", ""
        if row.spool_text_path and Path(row.spool_text_path).exists():
            with open(row.spool_text_path, "rb") as fh:
                size = os.fstat(fh.fileno()).st_size
                tp = gdrive.upload(db, fh, name=f"{name}.متن.txt", mime="text/plain; charset=utf-8",
                                   parent=parent, size=size, description=f"متنِ استخراج‌شدهٔ {row.ref}")
            text_id, text_link = tp["id"], tp["link"]
        row.store = "drive"
        row.store_note = ""
        row.push_attempts = int(row.push_attempts or 0) + 1
        row.drive_id, row.drive_link = placed["id"], placed["link"]
        row.text_drive_id, row.text_drive_link = text_id, text_link
        row.drive_path = "/".join(parts + [name])
        row.drive_folder_link = gdrive.folder_link(parent)
        row.pushed_at = datetime.utcnow()
        sp, tp_ = row.spool_path, row.spool_text_path
        row.spool_path, row.spool_text_path = "", ""
        db.commit()
        _rm(sp)
        _rm(tp_)
        return True
    except Exception as exc:  # noqa: BLE001 - record and retry later
        db.rollback()
        row.push_attempts = int(row.push_attempts or 0) + 1
        row.store = "failed"
        row.store_note = f"انتقال به درایو شکست خورد (تلاشِ {row.push_attempts}): {exc}"[:400]
        logger.warning("inspection file → Drive failed: %s", exc)
        return False


def push_shot(db, row, report_number: int) -> bool:
    from . import gdrive

    if row.store == "drive":
        return True
    if not row.spool_path or not Path(row.spool_path).exists():
        row.store, row.store_note = "failed", "تصویرِ موقت روی سرور پیدا نشد"
        return False
    if not gdrive.is_connected(db):
        row.store = "pending"
        row.store_note = "گوگل درایو هنوز متصل نیست — تصویر موقتاً روی سرور منتظر است"
        return False
    try:
        parts = gdrive.report_folder_parts(report_number, "تصویرها")
        parent = gdrive.ensure_folder(db, parts)
        ext = {"image/png": "png", "image/webp": "webp"}.get(row.mime or "", "jpg")
        name = f"{row.ref or row.id}-{row.kind}.{ext}"
        with open(row.spool_path, "rb") as fh:
            placed = gdrive.upload(db, fh, name=name, mime=row.mime or "image/jpeg", parent=parent,
                                   size=int(row.byte_size or 0))
        if placed.get("md5") and row.md5 and placed["md5"] != row.md5:
            row.store, row.store_note = "failed", "تطابقِ MD5 نشد — نسخهٔ موقت نگه داشته شد"
            return False
        sp = row.spool_path
        row.store, row.store_note = "drive", ""
        row.drive_id, row.drive_link = placed["id"], placed["link"]
        row.drive_path = "/".join(parts + [name])
        row.spool_path = ""
        db.commit()
        _rm(sp)
        return True
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        row.store = "failed"
        row.store_note = f"انتقال به درایو شکست خورد: {exc}"[:400]
        return False


# ---------------------------------------------------------------------------
# reading back — from the spool while in flight, from Drive afterwards
# ---------------------------------------------------------------------------
_TEXT_CACHE: "OrderedDict[str, str]" = OrderedDict()
_TEXT_CACHE_MAX = int(os.environ.get("INSPECTION_TEXT_CACHE_CHARS", str(40_000_000)))
_cache_lock = threading.Lock()


def load_text(db, row) -> str:
    """The extracted text of one file — whole, from wherever it lives now."""
    if row.spool_text_path and Path(row.spool_text_path).exists():
        return Path(row.spool_text_path).read_text(encoding="utf-8")
    if not row.text_drive_id:
        return ""
    with _cache_lock:
        if row.id in _TEXT_CACHE:
            _TEXT_CACHE.move_to_end(row.id)
            return _TEXT_CACHE[row.id]
    from . import gdrive

    text = gdrive.download_bytes(db, row.text_drive_id).decode("utf-8", "replace")
    with _cache_lock:
        _TEXT_CACHE[row.id] = text
        while sum(len(v) for v in _TEXT_CACHE.values()) > _TEXT_CACHE_MAX and len(_TEXT_CACHE) > 1:
            _TEXT_CACHE.popitem(last=False)
    return text


def replace_text(db, row, text: str, report_number: int) -> None:
    """Put a NEW extracted text where this file's text lives (re-extraction /
    full transcript). Spool first; a file already in Drive gets a new sidecar
    there and the old one goes to the project's «سطلِ حذف‌شده» (quarantine)."""
    from . import gdrive

    with _cache_lock:
        _TEXT_CACHE.pop(row.id, None)
    if row.store != "drive":
        if not text:
            _rm(row.spool_text_path)
            row.spool_text_path = ""
            return
        path = row.spool_text_path or str(spool_dir() / f"file-{row.id}.txt")
        Path(path).write_text(text, encoding="utf-8")
        row.spool_text_path = path
        return
    old = row.text_drive_id or ""
    row.text_drive_id, row.text_drive_link = "", ""
    if text:
        parent = gdrive.ensure_folder(db, gdrive.report_folder_parts(report_number))
        name = f"{row.ref} — {row.filename}" if row.ref else row.filename
        data = text.encode("utf-8")
        tp = gdrive.upload(db, io.BytesIO(data), name=f"{name}.متن.txt", mime="text/plain; charset=utf-8",
                           parent=parent, size=len(data), description=f"متنِ استخراج‌شدهٔ {row.ref}")
        row.text_drive_id, row.text_drive_link = tp["id"], tp["link"]
    if old:
        try:
            gdrive.move_to_trash_folder(db, old)
        except Exception:  # noqa: BLE001 - the old sidecar simply stays where it was
            pass


def iter_raw(db, row) -> Iterator[bytes]:
    """The original bytes, streamed. Raises FileNotFoundError with a reason."""
    if row.spool_path and Path(row.spool_path).exists():
        def local() -> Iterator[bytes]:
            with open(row.spool_path, "rb") as fh:
                yield from iter(lambda: fh.read(1024 * 1024), b"")
        return local()
    if row.drive_id:
        from . import gdrive

        try:
            return gdrive.iter_download(db, row.drive_id)
        except gdrive.DriveError as exc:
            raise FileNotFoundError(str(exc)) from exc
    raise FileNotFoundError("فایل نه روی سرور است نه در درایو — " + (row.store_note or "دلیلی ثبت نشده"))


def write_shot_spool(shot_id: str, data: bytes, mime: str) -> str:
    ext = {"image/png": ".png", "image/webp": ".webp"}.get(mime, ".jpg")
    path = spool_dir() / f"shot-{shot_id}{ext}"
    path.write_bytes(data)
    return str(path)


def decode_data_url(shot: str) -> tuple[str, bytes]:
    head, payload = shot.split(",", 1)
    mime = head[5:].split(";")[0]
    return mime, base64.b64decode(payload)


# ---------------------------------------------------------------------------
# the background mover
# ---------------------------------------------------------------------------
_jobs: "queue.Queue[str]" = queue.Queue()
_worker: Optional[threading.Thread] = None
_worker_lock = threading.Lock()
SYNC_EVERY_S = int(os.environ.get("INSPECTION_SYNC_EVERY_S", "300"))
STALE_UPLOAD = timedelta(hours=24)


def sync_pending(limit: int = 50) -> dict:
    """Push everything still waiting, and clear abandoned uploads. Idempotent."""
    from ..core.database import SessionLocal
    from ..models.inspection import InspectionFile, InspectionReport, InspectionShot, InspectionUpload
    from . import gdrive

    out = {"files": 0, "shots": 0, "failed": 0, "abandoned_uploads": 0, "connected": False}
    db = SessionLocal()
    try:
        # abandoned chunked uploads — the browser went away mid-file
        cutoff = datetime.utcnow() - STALE_UPLOAD
        for up in db.query(InspectionUpload).filter(InspectionUpload.status == "uploading",
                                                    InspectionUpload.updated_at < cutoff).all():
            _rm(up.spool_path)
            up.status, up.spool_path = "cancelled", ""
            out["abandoned_uploads"] += 1
        db.commit()
        out["connected"] = gdrive.is_connected(db)
        if not out["connected"]:
            return out
        numbers = {r.id: (r.number, r.title or "") for r in db.query(
            InspectionReport.id, InspectionReport.number, InspectionReport.title).all()}
        for f in db.query(InspectionFile).filter(InspectionFile.store.in_(("pending", "failed"))
                                                 ).order_by(InspectionFile.created_at).limit(limit).all():
            n, t = numbers.get(f.report_id, (0, ""))
            if push_file(db, f, n, t):
                out["files"] += 1
            else:
                out["failed"] += 1
            db.commit()
        for s in db.query(InspectionShot).filter(InspectionShot.store.in_(("pending", "failed"))
                                                 ).order_by(InspectionShot.created_at).limit(limit).all():
            n, _t = numbers.get(s.report_id, (0, ""))
            if push_shot(db, s, n):
                out["shots"] += 1
            else:
                out["failed"] += 1
            db.commit()
        return out
    finally:
        db.close()


def _run() -> None:
    last_full = 0.0
    while True:
        try:
            _jobs.get(timeout=30)
            # coalesce a burst (several files of one sheet) into one sweep
            while not _jobs.empty():
                _jobs.get_nowait()
            sync_pending()
            last_full = time.time()
        except queue.Empty:
            if time.time() - last_full >= SYNC_EVERY_S:
                try:
                    sync_pending()
                except Exception as exc:  # noqa: BLE001
                    logger.warning("inspection periodic sync failed: %s", exc)
                last_full = time.time()
        except Exception as exc:  # noqa: BLE001 - the mover must never die
            logger.warning("inspection sync failed: %s", exc)


def start_worker() -> None:
    global _worker
    if os.environ.get("INSPECTION_SYNC_DISABLED") == "1":
        return
    with _worker_lock:
        if _worker is None or not _worker.is_alive():
            _worker = threading.Thread(target=_run, name="inspection-drive-sync", daemon=True)
            _worker.start()


def kick() -> None:
    """Ask the mover to sweep soon (after a new file or shot was spooled)."""
    start_worker()
    _jobs.put("go")
