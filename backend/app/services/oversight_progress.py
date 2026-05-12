"""
Oversight Progress Tracker
===========================
in-memory tracker برای progress operationهای طولانی (extraction +
idea_to_prompt + create_task) تا UI (frontend poll + Telegram editMessage)
بتواند بفهمد crash نکرده.

API:
- `track_id` (UUID یا task_draft_id) → ProgressSnapshot
- `update(track_id, stage, current, total, detail)` — non-blocking
- `get(track_id)` → snapshot (یا None)
- `complete(track_id, final_message)` — همه done

استفاده در:
- backend extraction (`_resolve_attachments_for_idea` + `extract_session`)
- frontend با polling endpoint `GET /api/oversight/progress/{track_id}`
- Telegram bot با callback `on_update` → editMessageText

Note: in-memory فقط — اگر restart کنه، progress گم می‌شود (operationهای
زنده هم interrupted می‌شوند پس مهم نیست).
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import asdict, dataclass, field
from typing import Any, Awaitable, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class ProgressSnapshot:
    track_id: str
    stage: str = "starting"        # e.g. "extracting" | "idea_to_prompt" | "create_task" | "done"
    current: int = 0
    total: int = 0
    detail: str = ""               # متن کوتاه — مثل "فایل 2/3: PDF صفحه 12/40"
    percent: float = 0.0           # 0-100
    started_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    completed: bool = False
    error: Optional[str] = None
    # خروجی نهایی (پس از complete) — مثل task_id یا extraction_id
    result: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def elapsed_seconds(self) -> float:
        return time.time() - self.started_at


# Callable that gets called on each update
ProgressCallback = Callable[[ProgressSnapshot], Awaitable[None]]


class ProgressTracker:
    """in-memory tracker، با per-track_id callbacks."""

    def __init__(self) -> None:
        self._snaps: Dict[str, ProgressSnapshot] = {}
        self._callbacks: Dict[str, List[ProgressCallback]] = {}
        self._last_pushed: Dict[str, float] = {}  # برای throttle
        self._lock = asyncio.Lock()

    def get(self, track_id: str) -> Optional[ProgressSnapshot]:
        return self._snaps.get(track_id)

    def list_active(self) -> List[ProgressSnapshot]:
        return [s for s in self._snaps.values() if not s.completed]

    async def start(
        self, track_id: str, *, stage: str = "starting", total: int = 0, detail: str = "",
    ) -> ProgressSnapshot:
        async with self._lock:
            snap = ProgressSnapshot(
                track_id=track_id, stage=stage, total=total, detail=detail,
            )
            self._snaps[track_id] = snap
            self._callbacks.setdefault(track_id, [])
            self._last_pushed[track_id] = 0.0
        return snap

    def register_callback(self, track_id: str, cb: ProgressCallback) -> None:
        """ثبت callback که هر بار update فراخوانی می‌شود (با throttle)."""
        self._callbacks.setdefault(track_id, []).append(cb)

    async def update(
        self,
        track_id: str,
        *,
        stage: Optional[str] = None,
        current: Optional[int] = None,
        total: Optional[int] = None,
        detail: Optional[str] = None,
        throttle_sec: float = 8.0,
    ) -> Optional[ProgressSnapshot]:
        """به‌روزرسانی progress. اگر throttle_sec گذشته باشد، callbackها هم
        صدا زده می‌شوند (در یک background task تا blocking نباشند).
        """
        snap = self._snaps.get(track_id)
        if snap is None:
            # شاید caller forgotten to start
            snap = await self.start(track_id, stage=stage or "starting", total=total or 0)
        async with self._lock:
            if stage is not None:
                snap.stage = stage
            if current is not None:
                snap.current = current
            if total is not None:
                snap.total = total
            if detail is not None:
                snap.detail = detail
            snap.updated_at = time.time()
            if snap.total > 0:
                snap.percent = round((snap.current / snap.total) * 100.0, 1)
            else:
                snap.percent = 0.0

            now = time.time()
            last = self._last_pushed.get(track_id, 0.0)
            should_push = (now - last) >= throttle_sec
            if should_push:
                self._last_pushed[track_id] = now

        # callbacks خارج از lock — تا callback‌های کند block نکنند
        if should_push:
            cbs = list(self._callbacks.get(track_id, []) or [])
            for cb in cbs:
                try:
                    asyncio.create_task(cb(snap))
                except Exception as e:
                    logger.debug(f"progress callback failed: {e}")
        return snap

    async def complete(
        self,
        track_id: str,
        *,
        stage: str = "done",
        detail: str = "",
        result: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
    ) -> Optional[ProgressSnapshot]:
        snap = self._snaps.get(track_id)
        if snap is None:
            return None
        async with self._lock:
            snap.stage = stage
            snap.detail = detail
            snap.result = result
            snap.error = error
            snap.completed = True
            snap.updated_at = time.time()
            if error is None and snap.total > 0:
                snap.percent = 100.0
        # final callback push — bypass throttle
        cbs = list(self._callbacks.get(track_id, []) or [])
        for cb in cbs:
            try:
                asyncio.create_task(cb(snap))
            except Exception as e:
                logger.debug(f"progress final callback failed: {e}")
        return snap

    async def cleanup(self, older_than_seconds: int = 3600) -> int:
        """حذف snapshotهای completed قدیمی."""
        async with self._lock:
            cutoff = time.time() - older_than_seconds
            old_ids = [
                tid for tid, s in self._snaps.items()
                if s.completed and s.updated_at < cutoff
            ]
            for tid in old_ids:
                self._snaps.pop(tid, None)
                self._callbacks.pop(tid, None)
                self._last_pushed.pop(tid, None)
            return len(old_ids)


# singleton
_tracker_instance: Optional[ProgressTracker] = None


def get_progress_tracker() -> ProgressTracker:
    global _tracker_instance
    if _tracker_instance is None:
        _tracker_instance = ProgressTracker()
    return _tracker_instance
