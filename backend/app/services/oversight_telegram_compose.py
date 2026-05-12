"""
Oversight Telegram Compose Service
===================================
state machine برای buffer کردن پیام‌های ترکیبی (متن + صوت + ویدئو + عکس +
سند + ...) که کاربر از طریق ربات تلگرام می‌فرستد، تا زمانی که **خودش**
دکمهٔ submit را بزند.

اصول طراحی:
- تا submit، **هیچ تسک/پروژه ساخته نمی‌شود** — فقط buffer در حافظه + JSON.
- ترتیب رسیدن آیتم‌ها = order (که در backend = file_order).
- ترکیب text + file در یک buffer (هم mixed).
- auto-enter: اگر کاربر در phase idle است و media می‌فرستد، compose
  بدون نیاز به دستور صریح شروع می‌شود.
- TTL ۳۰ دقیقه + boot recovery از compose_buffers.json.

modes:
- "task"     → پس از submit، create_task برای watched_id انتخابی
- "project"  → پس از submit، new_project flow (Stage 5)

محل قرارگیری: services/ (در کنار سایر oversight_*).
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from .oversight_service import STORAGE_DIR

logger = logging.getLogger(__name__)

COMPOSE_FILE: Path = STORAGE_DIR / "compose_buffers.json"
COMPOSE_TTL_SECONDS: int = 30 * 60  # ۳۰ دقیقه

# nمدیا types که Telegram می‌فرستد و ما ساپورت می‌کنیم
SUPPORTED_MEDIA_TYPES = frozenset({
    "voice",         # voice recording (.ogg)
    "video_note",    # circular video
    "video",         # regular video
    "photo",         # gallery / camera photo
    "audio",         # uploaded audio file
    "document",      # any document
    "animation",     # gif / animated mp4
    "text",          # plain text message
})


@dataclass
class ComposeItem:
    """یک آیتم در buffer — می‌تواند متن یا فایل باشد."""
    order: int                 # ترتیب رسیدن (1-based)
    type: str                  # عضوی از SUPPORTED_MEDIA_TYPES
    added_at: float = field(default_factory=time.time)
    # برای متن:
    text: Optional[str] = None
    # برای فایل:
    telegram_file_id: Optional[str] = None
    telegram_file_path: Optional[str] = None  # path روی Telegram CDN
    filename: Optional[str] = None
    mime_type: Optional[str] = None
    size_bytes: Optional[int] = None
    upload_session_id: Optional[str] = None  # پس از download + start_session
    # برای video/photo aspect:
    width: Optional[int] = None
    height: Optional[int] = None
    duration_seconds: Optional[float] = None  # voice/video
    # خطا (اگر download fail کرد):
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def is_file(self) -> bool:
        return self.type in SUPPORTED_MEDIA_TYPES and self.type != "text"


@dataclass
class ComposeBuffer:
    """buffer در حال جمع‌آوری برای یک chat_id واحد.

    یک کاربر می‌تواند هم‌زمان روی یک buffer کار کند. اگر کاربر `/cancel`
    بزند یا TTL بگذرد، buffer پاک می‌شود.
    """
    chat_id: str
    mode: str = "task"                # "task" | "project"
    watched_id: Optional[str] = None  # برای mode='task' — پروژهٔ هدف
    task_draft_id: str = field(default_factory=lambda: f"draft-{uuid.uuid4().hex[:12]}")
    items: List[ComposeItem] = field(default_factory=list)
    started_at: float = field(default_factory=time.time)
    last_activity_at: float = field(default_factory=time.time)
    expires_at: float = field(default_factory=lambda: time.time() + COMPOSE_TTL_SECONDS)
    # status message id که با هر آیتم edit می‌شود (single inline status)
    status_message_id: Optional[int] = None
    # ReplyKeyboard آیا فعال است؟
    reply_keyboard_active: bool = False
    # اگر کاربر submit زده و در حال پردازش است — برای جلوگیری از double-submit
    submitting: bool = False
    # 🆕 (audit fix) — اگر کاربر مدلی را از طریق toggle inline در این session
    # موقتاً فعال کرده، model_id آن اینجا نگه داشته می‌شود تا پس از اتمام
    # extraction خودکار revert شود. اگر None باشد، مدل از قبل enabled بوده
    # و revert لازم نیست.
    temp_activated_model_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["items"] = [it.to_dict() for it in self.items]
        return d

    def is_expired(self) -> bool:
        return time.time() > self.expires_at

    def touch(self) -> None:
        self.last_activity_at = time.time()
        self.expires_at = self.last_activity_at + COMPOSE_TTL_SECONDS

    def next_order(self) -> int:
        return len(self.items) + 1

    def file_items_sorted(self) -> List[ComposeItem]:
        return sorted([it for it in self.items if it.is_file()], key=lambda x: x.order)

    def text_items_sorted(self) -> List[ComposeItem]:
        return sorted([it for it in self.items if it.type == "text"], key=lambda x: x.order)

    def total_files(self) -> int:
        return sum(1 for it in self.items if it.is_file())

    def total_size_bytes(self) -> int:
        return sum((it.size_bytes or 0) for it in self.items if it.is_file())

    def session_ids_in_order(self) -> List[str]:
        return [
            it.upload_session_id for it in self.file_items_sorted()
            if it.upload_session_id
        ]


# ====================================================================
# Service singleton
# ====================================================================

class ComposeService:
    def __init__(self) -> None:
        self._buffers: Dict[str, ComposeBuffer] = {}
        self._lock = asyncio.Lock()
        self._load()

    def _load(self) -> None:
        if not COMPOSE_FILE.exists():
            return
        try:
            data = json.loads(COMPOSE_FILE.read_text(encoding="utf-8"))
            for item in data:
                try:
                    items_raw = item.pop("items", []) or []
                    buf = ComposeBuffer(**item)
                    buf.items = [ComposeItem(**i) for i in items_raw]
                    if not buf.is_expired():
                        self._buffers[buf.chat_id] = buf
                except Exception as e:
                    logger.warning(f"compose: skip malformed buffer: {e}")
        except Exception as e:
            logger.warning(f"compose: load failed: {e}")

    def _save(self) -> None:
        try:
            tmp = COMPOSE_FILE.with_suffix(".json.tmp")
            tmp.write_text(
                json.dumps(
                    [b.to_dict() for b in self._buffers.values()],
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            tmp.replace(COMPOSE_FILE)
        except Exception as e:
            logger.warning(f"compose: save failed: {e}")

    # ── public API ──

    def get(self, chat_id: str) -> Optional[ComposeBuffer]:
        b = self._buffers.get(chat_id)
        if b is None:
            return None
        if b.is_expired():
            return None
        return b

    def has_active(self, chat_id: str) -> bool:
        return self.get(chat_id) is not None

    async def start(
        self,
        chat_id: str,
        *,
        mode: str = "task",
        watched_id: Optional[str] = None,
        replace: bool = False,
    ) -> ComposeBuffer:
        """شروع یک compose جدید. اگر buffer قبلی موجود است:
          - replace=True → آن را cancel (با cleanup sessions) و جدید بساز
          - replace=False → همان قبلی برگردان
        """
        async with self._lock:
            existing = self._buffers.get(chat_id)
            if existing and not existing.is_expired():
                if not replace:
                    return existing
                # cancel old (in lock)
                await self._cancel_inner(chat_id, save=False)
            buf = ComposeBuffer(
                chat_id=chat_id,
                mode=mode,
                watched_id=watched_id,
            )
            self._buffers[chat_id] = buf
            self._save()
            return buf

    async def add_item(self, chat_id: str, item: ComposeItem) -> Optional[ComposeBuffer]:
        async with self._lock:
            b = self._buffers.get(chat_id)
            if b is None or b.is_expired():
                return None
            if b.submitting:
                # در حال submit — آیتم جدید رد می‌شود (یا می‌توان به buffer جدید رفت)
                return None
            item.order = b.next_order()
            b.items.append(item)
            b.touch()
            self._save()
            return b

    async def set_watched(self, chat_id: str, watched_id: Optional[str]) -> Optional[ComposeBuffer]:
        async with self._lock:
            b = self._buffers.get(chat_id)
            if b is None:
                return None
            b.watched_id = watched_id
            b.touch()
            self._save()
            return b

    async def set_status_message_id(self, chat_id: str, message_id: int) -> None:
        async with self._lock:
            b = self._buffers.get(chat_id)
            if b is not None:
                b.status_message_id = message_id
                self._save()

    async def set_reply_keyboard_active(self, chat_id: str, active: bool) -> None:
        async with self._lock:
            b = self._buffers.get(chat_id)
            if b is not None:
                b.reply_keyboard_active = active
                self._save()

    async def set_temp_activated_model(self, chat_id: str, model_id: Optional[str]) -> None:
        """🆕 (audit fix) — ثبت/پاک کردن model_id که موقتاً برای این session فعال شد."""
        async with self._lock:
            b = self._buffers.get(chat_id)
            if b is not None:
                b.temp_activated_model_id = model_id
                self._save()

    async def mark_submitting(self, chat_id: str, value: bool = True) -> Optional[ComposeBuffer]:
        async with self._lock:
            b = self._buffers.get(chat_id)
            if b is None:
                return None
            b.submitting = value
            self._save()
            return b

    async def _cancel_inner(self, chat_id: str, *, save: bool = True) -> Optional[ComposeBuffer]:
        """درون lock — cancel + cleanup upload sessions."""
        b = self._buffers.pop(chat_id, None)
        if b is None:
            return None
        # cleanup هر upload session که هنوز در سرور است
        try:
            from .oversight_upload_session import get_upload_session_service
            up_svc = get_upload_session_service()
            for it in b.items:
                if it.upload_session_id:
                    try:
                        await up_svc.cancel(it.upload_session_id)
                    except Exception as e:
                        logger.debug(f"compose cancel: upload cancel failed: {e}")
        except Exception as e:
            logger.debug(f"compose cancel: upload service unavailable: {e}")
        if save:
            self._save()
        return b

    async def cancel(self, chat_id: str) -> Optional[ComposeBuffer]:
        async with self._lock:
            return await self._cancel_inner(chat_id, save=True)

    async def finalize_after_submit(self, chat_id: str) -> Optional[ComposeBuffer]:
        """پس از submit موفق — buffer از list حذف می‌شود (sessions حفظ می‌شوند
        چون به task ربط داده شده‌اند).
        """
        async with self._lock:
            b = self._buffers.pop(chat_id, None)
            self._save()
            return b

    async def cleanup_expired(self) -> int:
        """حذف bufferهای منقضی (+ cleanup sessions)."""
        async with self._lock:
            expired_ids = [
                cid for cid, b in self._buffers.items() if b.is_expired()
            ]
            for cid in expired_ids:
                await self._cancel_inner(cid, save=False)
            if expired_ids:
                self._save()
            return len(expired_ids)


# singleton
_compose_service_instance: Optional[ComposeService] = None


def get_compose_service() -> ComposeService:
    global _compose_service_instance
    if _compose_service_instance is None:
        _compose_service_instance = ComposeService()
    return _compose_service_instance
