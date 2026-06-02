"""
🎬 Inspector Recording Service — مدیریت جلسات ضبط ویدئو از تب بازرس ویژه.

سرویس singleton که state جلسات ضبط را در RAM نگه می‌دارد (نه DB).
هر جلسه شامل فایل‌های موقت در `/tmp/inspector_recordings/{session_id}/`:
  - audio_chunks/ (mp4/webm chunks سمت کلاینت)
  - video_chunks/ (فقط در حالت B — getDisplayMedia)
  - frames/      (فقط در حالت A — Playwright screencast)
  - events.json  (تعاملات کاربر)
  - transcript.txt, visual_summary.json, prompt.md (پس از processing)
  - final.webm (فایل نهایی پس از مونتاژ)

پس از ارسال موفق به Telegram یا cancel کاربر، فولدر کاملاً حذف می‌شود.
هیچ persistence در DB. session پس از ۱۲۰ دقیقه idle خودکار cleanup می‌شود.

این فایل **Commit 1 — Foundation**: state management + cleanup. هیچ AI
processing، هیچ Playwright، هیچ Telegram. آن‌ها در commit های بعدی اضافه
می‌شوند.
"""
from __future__ import annotations

import asyncio
import logging
import os
import shutil
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional

logger = logging.getLogger(__name__)

RecordingMode = Literal["A", "B"]
SessionPhase = Literal[
    "initializing",       # session ساخته شد، Playwright/MediaRecorder در حال آماده‌سازی
    "recording",          # در حال ضبط
    "stopping",           # کاربر [stop] زد، در حال ارسال آخرین chunks
    "processing",         # transcribe + vision + prompt synthesis
    "ready_for_preview",  # کاربر می‌تواند preview ببیند و [ارسال نهایی] بزند
    "finalizing",         # ارسال به Telegram + ساخت تسک
    "completed",          # کار تمام
    "cancelled",          # کاربر cancel کرد
    "expired",            # >120m idle → auto-cancel
    "errored",            # خطای فنی
]

RECORDINGS_ROOT = Path("/tmp/inspector_recordings")
MAX_SESSION_AGE_MIN = 120
MAX_RECORDING_MIN = 60


@dataclass
class AudioConfig:
    mic: bool = True
    system: bool = False
    mic_device_id: Optional[str] = None


@dataclass
class InteractionEvent:
    ts_ms: int  # ms از شروع ضبط
    type: str   # click | scroll | navigation | inferred_click | inferred_scroll
    details: Dict[str, Any] = field(default_factory=dict)
    source: str = "postmessage"  # postmessage | inferred | dom


@dataclass
class RecordingSession:
    session_id: str
    project_id: str                  # watched_id یا hint برای پروژه
    project_full_name: Optional[str] # نام repo برای caption تلگرام
    mode: RecordingMode              # A یا B
    audio: AudioConfig
    target_fps: int                  # 2 برای حالت A، 15 برای حالت B
    phase: SessionPhase = "initializing"
    started_at: float = field(default_factory=time.time)
    last_activity_at: float = field(default_factory=time.time)
    finalized_at: Optional[float] = None
    # paths
    session_dir: Path = field(init=False)
    audio_dir: Path = field(init=False)
    video_dir: Path = field(init=False)
    frames_dir: Path = field(init=False)
    # counters
    audio_chunks_count: int = 0
    video_chunks_count: int = 0
    frames_count: int = 0
    interactions: List[InteractionEvent] = field(default_factory=list)
    # processing results (populated در فاز processing)
    transcript: str = ""
    transcript_language: str = ""
    transcript_model: str = ""
    visual_summary: List[Dict[str, Any]] = field(default_factory=list)
    location_timeline: List[Dict[str, Any]] = field(default_factory=list)  # mode B
    # 🆕 (Multimodal Unified Analysis) — وقتی analyze_recording_multimodal
    # موفق شد، intent extracted + key references + log signals را اینجا
    # ذخیره می‌کند تا stage_synthesize از آنها برای ساخت پرامپت قوی‌تر
    # استفاده کند (به‌جای محاسبه دوباره از خام).
    extra_context: Dict[str, Any] = field(default_factory=dict)
    prompt: str = ""
    prompt_model: str = ""
    final_video_path: Optional[Path] = None
    final_video_size_bytes: int = 0
    # logs snapshot (در فاز stop گرفته می‌شود)
    console_logs: List[Dict[str, Any]] = field(default_factory=list)
    backend_logs: List[Dict[str, Any]] = field(default_factory=list)
    # نتیجه finalize
    telegram_message_ids: List[Any] = field(default_factory=list)
    task_id: Optional[str] = None
    chat_message_sent: bool = False
    last_error: Optional[str] = None

    def __post_init__(self):
        self.session_dir = RECORDINGS_ROOT / self.session_id
        self.audio_dir = self.session_dir / "audio_chunks"
        self.video_dir = self.session_dir / "video_chunks"
        self.frames_dir = self.session_dir / "frames"
        # دایرکتوری‌ها هنگام شروع جلسه ساخته می‌شوند

    def touch(self) -> None:
        """بروزرسانی last_activity_at — برای جلوگیری از stale cleanup."""
        self.last_activity_at = time.time()

    def duration_sec(self) -> float:
        end = self.finalized_at or time.time()
        return max(0.0, end - self.started_at)

    def is_stale(self) -> bool:
        idle = (time.time() - self.last_activity_at) / 60.0
        return idle > MAX_SESSION_AGE_MIN

    def should_auto_stop(self) -> bool:
        """آیا به ۶۰ دقیقه ضبط رسیده‌ایم؟"""
        return self.phase == "recording" and self.duration_sec() / 60.0 >= MAX_RECORDING_MIN

    def to_status_dict(self) -> Dict[str, Any]:
        """خروجی صریح برای کلاینت — بدون نمایش paths داخلی."""
        return {
            "session_id": self.session_id,
            "project_id": self.project_id,
            "project_full_name": self.project_full_name,
            "mode": self.mode,
            "phase": self.phase,
            "audio": {
                "mic": self.audio.mic,
                "system": self.audio.system,
                "mic_device_id": self.audio.mic_device_id,
            },
            "target_fps": self.target_fps,
            "started_at": datetime.fromtimestamp(self.started_at, tz=timezone.utc).isoformat(),
            "duration_sec": round(self.duration_sec(), 1),
            "audio_chunks": self.audio_chunks_count,
            "video_chunks": self.video_chunks_count,
            "frames": self.frames_count,
            "interactions_count": len(self.interactions),
            "transcript_chars": len(self.transcript),
            "visual_summary_items": len(self.visual_summary),
            "prompt_chars": len(self.prompt),
            "final_video_size_mb": (
                round(self.final_video_size_bytes / (1024 * 1024), 2)
                if self.final_video_size_bytes
                else 0
            ),
            "telegram_message_ids": self.telegram_message_ids,
            "task_id": self.task_id,
            "chat_message_sent": self.chat_message_sent,
            "last_error": self.last_error,
        }


class InspectorRecordingService:
    """Singleton — همه‌ی جلسات ضبط در RAM این service."""

    def __init__(self):
        self._sessions: Dict[str, RecordingSession] = {}
        self._lock = asyncio.Lock()
        RECORDINGS_ROOT.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Session lifecycle
    # ------------------------------------------------------------------

    async def start_session(
        self,
        *,
        project_id: str,
        project_full_name: Optional[str],
        mode: RecordingMode,
        audio_mic: bool = True,
        audio_system: bool = False,
        mic_device_id: Optional[str] = None,
        target_fps: Optional[int] = None,
    ) -> RecordingSession:
        if mode not in ("A", "B"):
            raise ValueError(f"mode must be 'A' or 'B', got {mode!r}")
        session_id = str(uuid.uuid4())
        if target_fps is None:
            target_fps = 2 if mode == "A" else 15
        session = RecordingSession(
            session_id=session_id,
            project_id=project_id,
            project_full_name=project_full_name,
            mode=mode,
            audio=AudioConfig(mic=audio_mic, system=audio_system, mic_device_id=mic_device_id),
            target_fps=target_fps,
        )
        # ساخت دایرکتوری‌ها
        session.audio_dir.mkdir(parents=True, exist_ok=True)
        session.video_dir.mkdir(parents=True, exist_ok=True)
        if mode == "A":
            session.frames_dir.mkdir(parents=True, exist_ok=True)
        async with self._lock:
            self._sessions[session_id] = session
        # transition به recording — در commit های بعدی Playwright/MediaRecorder در همینجا
        # شروع می‌شوند. فعلاً فقط phase را عوض می‌کنیم.
        session.phase = "recording"
        session.touch()
        logger.info(
            f"inspector_recording: session {session_id} started "
            f"(mode={mode}, project={project_full_name or project_id}, fps={target_fps})"
        )
        return session

    def get_session(self, session_id: str) -> Optional[RecordingSession]:
        return self._sessions.get(session_id)

    def _require_session(self, session_id: str) -> RecordingSession:
        s = self._sessions.get(session_id)
        if s is None:
            raise KeyError(f"session_not_found: {session_id}")
        return s

    # ------------------------------------------------------------------
    # Chunk ingestion
    # ------------------------------------------------------------------

    async def append_audio_chunk(
        self, session_id: str, seq: int, chunk_bytes: bytes
    ) -> None:
        session = self._require_session(session_id)
        if session.phase not in ("recording", "stopping"):
            raise RuntimeError(
                f"cannot append audio in phase={session.phase} (must be recording|stopping)"
            )
        path = session.audio_dir / f"chunk_{seq:06d}.webm"
        path.write_bytes(chunk_bytes)
        session.audio_chunks_count += 1
        session.touch()

    async def append_frame(
        self, session_id: str, seq: int, frame_bytes: bytes, ext: str = "png"
    ) -> None:
        """آپلود یک frame (فقط در حالت A — frontend از /api/render/inspector/screenshot
        می‌گیرد و به اینجا می‌فرستد).
        """
        session = self._require_session(session_id)
        if session.mode != "A":
            raise RuntimeError("frames فقط در حالت A پذیرفته می‌شوند")
        if session.phase not in ("recording", "stopping"):
            raise RuntimeError(
                f"cannot append frame in phase={session.phase}"
            )
        if ext not in ("png", "jpg", "jpeg", "webp"):
            ext = "png"
        path = session.frames_dir / f"frame_{seq:06d}.{ext}"
        path.write_bytes(frame_bytes)
        session.frames_count += 1
        session.touch()

    async def attach_logs_snapshot(
        self,
        session_id: str,
        *,
        console_logs: Optional[List[Dict[str, Any]]] = None,
        backend_logs: Optional[List[Dict[str, Any]]] = None,
    ) -> None:
        """frontend در /stop می‌تواند snapshot لاگ‌ها را پاس بدهد. این تابع
        آن‌ها را در session ذخیره می‌کند تا در processing استفاده شوند.
        """
        session = self._require_session(session_id)
        if console_logs:
            session.console_logs = list(console_logs)
        if backend_logs:
            session.backend_logs = list(backend_logs)
        session.touch()

    async def append_video_chunk(
        self, session_id: str, seq: int, chunk_bytes: bytes
    ) -> None:
        session = self._require_session(session_id)
        if session.mode != "B":
            raise RuntimeError("video chunks فقط در حالت B پذیرفته می‌شوند")
        if session.phase not in ("recording", "stopping"):
            raise RuntimeError(
                f"cannot append video in phase={session.phase}"
            )
        path = session.video_dir / f"chunk_{seq:06d}.webm"
        path.write_bytes(chunk_bytes)
        session.video_chunks_count += 1
        session.touch()

    async def append_interactions(
        self, session_id: str, events: List[Dict[str, Any]]
    ) -> None:
        session = self._require_session(session_id)
        if session.phase not in ("recording", "stopping"):
            # سکوت — interactions late از frontend ممکن است بعد از stop برسد
            return
        for e in events or []:
            try:
                session.interactions.append(
                    InteractionEvent(
                        ts_ms=int(e.get("ts_ms") or e.get("ts") or 0),
                        type=str(e.get("type") or "unknown"),
                        details=dict(e.get("details") or {}),
                        source=str(e.get("source") or "postmessage"),
                    )
                )
            except Exception as _e:
                logger.debug(f"skip malformed interaction: {_e}")
        session.touch()

    # ------------------------------------------------------------------
    # Transition methods
    # ------------------------------------------------------------------

    async def stop_session(
        self,
        session_id: str,
        *,
        user_note: str = "",
        run_processing: bool = True,
    ) -> RecordingSession:
        """گذار از recording → stopping → processing → ready_for_preview.

        Args:
          user_note: یادداشت اولیه کاربر — برای synthesis استفاده می‌شود
          run_processing: اگر False، فقط phase به ready_for_preview می‌رود
                          بدون اجرای vision/transcribe (برای تست‌ها)
        """
        session = self._require_session(session_id)
        if session.phase not in ("recording", "stopping"):
            logger.warning(
                f"stop_session called in phase={session.phase} — ignoring (session={session_id})"
            )
            return session
        session.phase = "stopping"
        session.touch()

        if not run_processing:
            session.phase = "ready_for_preview"
            logger.info(f"inspector_recording: session {session_id} stopped (no processing)")
            return session

        # وارد phase processing شو و pipeline را در پس‌زمینه trigger کن
        session.phase = "processing"
        logger.info(
            f"inspector_recording: session {session_id} processing started "
            f"(duration={session.duration_sec():.1f}s, audio_chunks={session.audio_chunks_count}, "
            f"frames={session.frames_count}, video_chunks={session.video_chunks_count}, "
            f"interactions={len(session.interactions)})"
        )

        # processing را sync انجام می‌دهیم چون frontend منتظر است
        # (نمی‌خواهیم با background task روی Render free tier ریسک کنیم)
        try:
            from .inspector_recording_processor import process_session
            summary = await process_session(session, user_note=user_note)
            logger.info(
                f"inspector_recording: processing done for {session_id} — "
                f"{summary}"
            )
            session.phase = "ready_for_preview"
        except Exception as e:
            logger.exception(f"processing failed for {session_id}: {e}")
            session.phase = "errored"
            session.last_error = str(e)[:500]
        session.touch()
        return session

    async def regenerate_prompt(
        self,
        session_id: str,
        *,
        edited_transcript: Optional[str] = None,
        user_note: str = "",
    ) -> RecordingSession:
        """دوباره پرامپت تولید کن — اگر کاربر transcript را اصلاح کرد یا
        یادداشت اولیه را تغییر داد.
        """
        session = self._require_session(session_id)
        if session.phase not in ("ready_for_preview", "errored"):
            raise RuntimeError(
                f"regenerate_prompt در phase={session.phase} مجاز نیست"
            )
        if edited_transcript is not None:
            session.transcript = edited_transcript[:500_000]  # safety cap
        session.touch()
        # Re-run فقط مرحله synthesis (transcribe و vision قبلاً انجام شده)
        try:
            from .inspector_recording_processor import stage_synthesize, build_final_prompt
            syn = await stage_synthesize(session, user_note=user_note)
            ai_body = syn.get("prompt") or ""
            session.prompt_model = syn.get("model_used") or ""
            session.prompt = build_final_prompt(
                session, user_note=user_note, ai_generated_body=ai_body
            )
            logger.info(
                f"inspector_recording: regenerated prompt for {session_id} "
                f"({len(session.prompt)} chars, fallback={syn.get('fallback')})"
            )
        except Exception as e:
            logger.exception(f"regenerate_prompt failed for {session_id}: {e}")
            session.last_error = f"regenerate: {str(e)[:300]}"
        return session

    async def finalize(
        self,
        session_id: str,
        *,
        user_note: str,
        send_to_oversight: bool,
        edited_transcript: Optional[str] = None,
    ) -> Dict[str, Any]:
        """ارسال به تلگرام + ساخت تسک یا چت + cleanup. delegate به ماژول
        inspector_recording_finalize.
        """
        session = self._require_session(session_id)
        if session.phase not in ("ready_for_preview", "errored"):
            raise RuntimeError(
                f"cannot finalize in phase={session.phase} (must be ready_for_preview)"
            )
        # اگر transcript ویرایش شده، prompt را regenerate کن
        if edited_transcript is not None and edited_transcript != session.transcript:
            session.transcript = edited_transcript[:500_000]
            try:
                from .inspector_recording_processor import (
                    stage_synthesize,
                    build_final_prompt,
                )
                syn = await stage_synthesize(session, user_note=user_note)
                ai_body = syn.get("prompt") or ""
                session.prompt_model = syn.get("model_used") or ""
                session.prompt = build_final_prompt(
                    session, user_note=user_note, ai_generated_body=ai_body
                )
            except Exception as e:
                logger.warning(f"finalize: pre-regenerate failed: {e}")

        session.phase = "finalizing"
        session.touch()

        try:
            from .inspector_recording_finalize import finalize_recording_session
            result = await finalize_recording_session(
                session,
                user_note=user_note,
                send_to_oversight=send_to_oversight,
            )
            logger.info(
                f"inspector_recording: finalize done for {session_id} — "
                f"task_id={result.get('task_id')} "
                f"telegram_msgs={result.get('telegram_message_ids')} "
                f"errors={result.get('errors')}"
            )
            return result
        except Exception as e:
            logger.exception(f"finalize crashed for {session_id}: {e}")
            session.phase = "errored"
            session.last_error = f"finalize: {str(e)[:300]}"
            return {
                "success": False,
                "session_id": session_id,
                "task_id": None,
                "telegram_message_ids": [],
                "chat_message_sent": False,
                "errors": [str(e)[:300]],
                "warnings": [],
                "cleanup_done": False,
            }

    async def cancel_session(self, session_id: str) -> None:
        """لغو کامل + حذف disk."""
        session = self._sessions.get(session_id)
        if session is None:
            return
        session.phase = "cancelled"
        session.touch()
        self._cleanup_disk(session)
        # نگه‌داری در RAM برای ۵ دقیقه برای debug؛ سپس cleanup
        async def _delayed_drop():
            await asyncio.sleep(300)
            self._sessions.pop(session_id, None)
        asyncio.create_task(_delayed_drop())
        logger.info(f"inspector_recording: session {session_id} cancelled + disk cleared")

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------

    def _cleanup_disk(self, session: RecordingSession) -> None:
        try:
            if session.session_dir.exists():
                shutil.rmtree(session.session_dir, ignore_errors=True)
        except Exception as e:
            logger.warning(f"cleanup_disk failed for {session.session_id}: {e}")

    async def sweep_stale(self) -> int:
        """جلسات stale (>120m idle) را cancel می‌کند. توسط scheduler صدا زده می‌شود.

        Returns تعداد جلسات cancel شده.
        """
        cancelled = 0
        async with self._lock:
            stale_ids = [
                sid for sid, s in self._sessions.items()
                if s.is_stale() and s.phase not in ("completed", "cancelled", "expired")
            ]
        for sid in stale_ids:
            session = self._sessions.get(sid)
            if session is None:
                continue
            logger.warning(
                f"inspector_recording: auto-expiring stale session {sid} "
                f"(idle={(time.time() - session.last_activity_at)/60:.1f}m, "
                f"phase={session.phase})"
            )
            session.phase = "expired"
            self._cleanup_disk(session)
            cancelled += 1
        # همچنین جلسات completed/cancelled قدیمی‌تر از ۳۰ دقیقه را از RAM حذف کن
        async with self._lock:
            now = time.time()
            to_drop = [
                sid for sid, s in self._sessions.items()
                if s.phase in ("completed", "cancelled", "expired")
                and (now - s.last_activity_at) > 30 * 60
            ]
            for sid in to_drop:
                self._sessions.pop(sid, None)
        return cancelled

    # ------------------------------------------------------------------
    # Diagnostics (برای debug — استفاده نمی‌شود در flow عادی)
    # ------------------------------------------------------------------

    def list_sessions_summary(self) -> List[Dict[str, Any]]:
        return [s.to_status_dict() for s in self._sessions.values()]


# Singleton instance
_singleton: Optional[InspectorRecordingService] = None


def get_inspector_recording_service() -> InspectorRecordingService:
    global _singleton
    if _singleton is None:
        _singleton = InspectorRecordingService()
    return _singleton
