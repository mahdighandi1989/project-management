"""
Oversight Upload Session Service
=================================
چندفایلی، chunked، resumable، تا 500MB هر فایل.

این service برای **پیوست به تسک‌های /oversight** طراحی شده — جدا از
upload.py عمومی که فایل را یک‌جا در RAM می‌خواند.

ویژگی‌ها:
- streaming chunk-by-chunk به disk با aiofiles (RAM ثابت ~5MB)
- persistent state در JSON → restart-safe
- file_order بر اساس ترتیب آپلود (اولین = order=1)
- cleanup automatic فایل‌های temp orphan
- atomic operations (lock per-session)

State machine:
  pending      → سشن ایجاد شد، هیچ chunk نیامده
  uploading    → chunkها در حال دریافت
  completed    → آپلود تمام، آمادهٔ extraction
  extracting   → service استخراج روی این session کار می‌کند
  extracted    → استخراج تمام، temp_path حذف شد، فقط متادیتا
  failed       → خطا (شامل reason)
  cancelled    → کاربر لغو کرد

Schema هر session:
  {
    "id": "uuid",
    "task_draft_id": "client-side group id برای ربط چند فایل به یک تسک",
    "original_filename": "...",
    "mime_type": "...",
    "total_size": 12345678,        # bytes
    "bytes_received": 5242880,
    "status": "uploading",
    "temp_path": "/.../oversight_uploads/<id>.bin",
    "file_order": 1,                # ترتیب آپلود در همان task_draft_id
    "created_at": "ISO",
    "updated_at": "ISO",
    "completed_at": null,
    "extracted_at": null,
    "extraction_progress": {},      # توسط extraction service پر می‌شود
    "error": null,
  }
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import aiofiles

from .oversight_service import STORAGE_DIR, now_iso  # reuse infrastructure

logger = logging.getLogger(__name__)

# ─────────── ثوابت ───────────
UPLOAD_DIR: Path = STORAGE_DIR / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
SESSIONS_FILE: Path = STORAGE_DIR / "upload_sessions.json"

# سقف هر فایل — هم‌راستا با Settings.MAX_UPLOAD_SIZE
DEFAULT_MAX_FILE_BYTES: int = 500 * 1024 * 1024  # 500MB

# chunk size پیشنهادی به client
CLIENT_CHUNK_SIZE: int = 5 * 1024 * 1024  # 5MB

# مدت orphan retention — فایل‌های temp بدون فعالیت >24h پاک می‌شوند
ORPHAN_TTL_HOURS: int = 24

VALID_STATUSES = {
    "pending", "uploading", "completed", "extracting",
    "extracted", "failed", "cancelled",
}


@dataclass
class UploadSession:
    id: str
    task_draft_id: str
    original_filename: str
    mime_type: str
    total_size: int
    bytes_received: int = 0
    status: str = "pending"
    temp_path: str = ""
    file_order: int = 1
    created_at: str = field(default_factory=now_iso)
    updated_at: str = field(default_factory=now_iso)
    completed_at: Optional[str] = None
    extracted_at: Optional[str] = None
    extraction_progress: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    # 🆕 لینک به تسک واقعی (پس از create_task)
    task_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def is_terminal(self) -> bool:
        return self.status in ("extracted", "failed", "cancelled")


# ====================================================================
# Service singleton
# ====================================================================

class UploadSessionService:
    def __init__(self) -> None:
        self._sessions: Dict[str, UploadSession] = {}
        self._lock = asyncio.Lock()
        self._per_session_locks: Dict[str, asyncio.Lock] = {}
        self._load()

    # ── persistence ──
    def _load(self) -> None:
        if not SESSIONS_FILE.exists():
            return
        try:
            data = json.loads(SESSIONS_FILE.read_text(encoding="utf-8"))
            for item in data:
                try:
                    s = UploadSession(**item)
                    self._sessions[s.id] = s
                except Exception as e:
                    logger.warning(f"upload_sessions: skip malformed entry: {e}")
        except Exception as e:
            logger.warning(f"upload_sessions: load failed: {e}")

    def _save(self) -> None:
        try:
            tmp = SESSIONS_FILE.with_suffix(".json.tmp")
            tmp.write_text(
                json.dumps([s.to_dict() for s in self._sessions.values()],
                           ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            tmp.replace(SESSIONS_FILE)
        except Exception as e:
            logger.warning(f"upload_sessions: save failed: {e}")

    def _get_session_lock(self, session_id: str) -> asyncio.Lock:
        # یک lock مجزا per session — جلوگیری از تداخل chunkهای parallel
        lk = self._per_session_locks.get(session_id)
        if lk is None:
            lk = asyncio.Lock()
            self._per_session_locks[session_id] = lk
        return lk

    # ── API ──
    async def start_session(
        self,
        *,
        task_draft_id: str,
        original_filename: str,
        mime_type: str,
        total_size: int,
        file_order: Optional[int] = None,
    ) -> UploadSession:
        if total_size <= 0:
            raise ValueError("total_size باید مثبت باشد")
        if total_size > DEFAULT_MAX_FILE_BYTES:
            raise ValueError(
                f"فایل بزرگ‌تر از سقف {DEFAULT_MAX_FILE_BYTES // (1024*1024)}MB است"
            )
        if not original_filename.strip():
            raise ValueError("original_filename خالی است")
        if not task_draft_id.strip():
            raise ValueError("task_draft_id خالی است")

        sid = str(uuid.uuid4())
        # فایل‌نام امن — فقط extension اصلی نگه داشته می‌شود
        ext = ""
        try:
            ext = os.path.splitext(original_filename)[1].lower()
            # whitelist ساده — جلوگیری از path traversal یا executable upload
            ext = "".join(c for c in ext if c.isalnum() or c == ".")[:10]
        except Exception:
            ext = ""
        temp_path = UPLOAD_DIR / f"{sid}{ext or '.bin'}"

        # auto file_order — اگر داده نشده، آخرین + 1 برای همین task_draft_id
        async with self._lock:
            if file_order is None:
                existing = [
                    s for s in self._sessions.values()
                    if s.task_draft_id == task_draft_id
                ]
                file_order = (max((s.file_order for s in existing), default=0) + 1)

            s = UploadSession(
                id=sid,
                task_draft_id=task_draft_id,
                original_filename=original_filename[:300],
                mime_type=(mime_type or "application/octet-stream").lower()[:100],
                total_size=total_size,
                status="pending",
                temp_path=str(temp_path),
                file_order=int(file_order),
            )
            self._sessions[sid] = s
            # فایل temp خالی بساز
            try:
                temp_path.touch()
            except Exception as e:
                logger.warning(f"upload_sessions: touch temp failed: {e}")
                raise
            self._save()
        return s

    def get(self, session_id: str) -> Optional[UploadSession]:
        return self._sessions.get(session_id)

    def list_by_draft(self, task_draft_id: str) -> List[UploadSession]:
        out = [s for s in self._sessions.values() if s.task_draft_id == task_draft_id]
        out.sort(key=lambda s: s.file_order)
        return out

    def list_by_task(self, task_id: str) -> List[UploadSession]:
        out = [s for s in self._sessions.values() if s.task_id == task_id]
        out.sort(key=lambda s: s.file_order)
        return out

    async def append_chunk(
        self,
        session_id: str,
        offset: int,
        data: bytes,
    ) -> UploadSession:
        s = self._sessions.get(session_id)
        if s is None:
            raise KeyError("session یافت نشد")
        if s.is_terminal():
            raise ValueError(f"session در وضعیت {s.status} است — chunk پذیرفته نمی‌شود")
        if offset < 0:
            raise ValueError("offset منفی")
        if offset != s.bytes_received:
            # client باید resume کند — به offset فعلی برگردد
            raise ValueError(
                f"offset mismatch: expected {s.bytes_received}, got {offset}. "
                f"از همان offset فعلی ادامه بده."
            )
        if s.bytes_received + len(data) > s.total_size:
            raise ValueError("داده بیش از total_size اعلام‌شده است")

        lock = self._get_session_lock(session_id)
        async with lock:
            # append به temp file با aiofiles — streaming، RAM ثابت
            async with aiofiles.open(s.temp_path, "ab") as f:
                await f.write(data)
            s.bytes_received += len(data)
            s.status = "uploading" if s.bytes_received < s.total_size else "completed"
            s.updated_at = now_iso()
            if s.status == "completed":
                s.completed_at = now_iso()
            async with self._lock:
                self._save()
        return s

    async def mark_completed(self, session_id: str) -> UploadSession:
        s = self._sessions.get(session_id)
        if s is None:
            raise KeyError("session یافت نشد")
        if s.bytes_received != s.total_size:
            raise ValueError(
                f"upload ناقص است: {s.bytes_received}/{s.total_size} bytes دریافت شده"
            )
        async with self._lock:
            s.status = "completed"
            s.completed_at = s.completed_at or now_iso()
            s.updated_at = now_iso()
            self._save()
        return s

    async def cancel(self, session_id: str) -> Optional[UploadSession]:
        s = self._sessions.get(session_id)
        if s is None:
            return None
        async with self._lock:
            s.status = "cancelled"
            s.updated_at = now_iso()
            # حذف temp
            try:
                p = Path(s.temp_path)
                if p.exists():
                    p.unlink()
            except Exception as e:
                logger.warning(f"cancel: failed to unlink {s.temp_path}: {e}")
            self._save()
        return s

    async def attach_to_task(self, session_ids: List[str], task_id: str) -> int:
        """پس از create_task، session‌های مرتبط را به task_id ربط بده."""
        n = 0
        async with self._lock:
            for sid in session_ids:
                s = self._sessions.get(sid)
                if s and not s.task_id:
                    s.task_id = task_id
                    s.updated_at = now_iso()
                    n += 1
            if n:
                self._save()
        return n

    async def set_status(
        self,
        session_id: str,
        status: str,
        *,
        error: Optional[str] = None,
        extraction_progress: Optional[Dict[str, Any]] = None,
    ) -> Optional[UploadSession]:
        if status not in VALID_STATUSES:
            raise ValueError(f"status نامعتبر: {status}")
        s = self._sessions.get(session_id)
        if s is None:
            return None
        async with self._lock:
            s.status = status
            s.updated_at = now_iso()
            if error is not None:
                s.error = error
            if extraction_progress is not None:
                s.extraction_progress = extraction_progress
            if status == "extracted":
                s.extracted_at = now_iso()
                # فایل اصلی دیگر نیاز نیست — حذف disk
                try:
                    p = Path(s.temp_path)
                    if p.exists():
                        p.unlink()
                        logger.info(f"upload: deleted temp after extraction: {s.temp_path}")
                except Exception as e:
                    logger.warning(f"set_status extracted: cleanup failed: {e}")
            self._save()
        return s

    async def cleanup_orphans(self, ttl_hours: int = ORPHAN_TTL_HOURS) -> int:
        """حذف temp file هایی که >ttl_hours بدون activity مانده‌اند."""
        cutoff = datetime.now(timezone.utc).timestamp() - ttl_hours * 3600
        removed = 0
        async with self._lock:
            to_delete: List[str] = []
            for sid, s in self._sessions.items():
                try:
                    upd_ts = datetime.fromisoformat(
                        s.updated_at.replace("Z", "+00:00")
                    ).timestamp()
                except Exception:
                    upd_ts = 0.0
                if (
                    s.status in ("pending", "uploading", "failed", "cancelled")
                    and upd_ts < cutoff
                ):
                    # حذف temp + session
                    try:
                        p = Path(s.temp_path)
                        if p.exists():
                            p.unlink()
                    except Exception:
                        pass
                    to_delete.append(sid)
            for sid in to_delete:
                self._sessions.pop(sid, None)
                self._per_session_locks.pop(sid, None)
                removed += 1
            if removed:
                self._save()
        # اضافی: فایل‌های temp روی disk که در sessions نیستند را هم پاک کن
        try:
            known_paths = {Path(s.temp_path).resolve() for s in self._sessions.values()}
            for f in UPLOAD_DIR.iterdir():
                if f.is_file() and f.resolve() not in known_paths:
                    # فایل orphan روی disk
                    try:
                        mtime = f.stat().st_mtime
                        if mtime < cutoff:
                            f.unlink()
                            removed += 1
                    except Exception:
                        pass
        except Exception as e:
            logger.debug(f"orphan disk scan failed: {e}")
        return removed


# ──── singleton ────
_service_instance: Optional[UploadSessionService] = None


def get_upload_session_service() -> UploadSessionService:
    global _service_instance
    if _service_instance is None:
        _service_instance = UploadSessionService()
    return _service_instance
