"""
Oversight File Extraction Service (Stage 4 + 5 combined)
=========================================================
استخراج متن از فایل‌های پیوست تسک، با persistence مرحله‌به‌مرحله.

طراحی:
- per-mime router (text, PDF, DOCX, XLSX, image, audio, video)
- هر segment که استخراج شد، **بلافاصله** در `extractions.json` ذخیره می‌شود
  → اگر backend crash کند، resume از segment بعدی ممکن است.
- خود فایل اصلی پس از اتمام (set_status='extracted') حذف می‌شود.
- مدل بصری/multimodal از `pick_best_extraction_model(mime)` انتخاب می‌شود
  → داینامیک، قابل override در /models.
- چارچوب «بدون خلاصه‌سازی»: prompt صریح می‌خواهد متن full literal.
- عناوین داینامیک: اول از مدل headings/sections می‌پرسیم بر اساس user_idea،
  سپس متن مرتبط با هر heading را extract می‌کنیم.

Schema:
  FileExtraction:
    id, task_id, session_id, file_order, original_filename, mime_type,
    total_segments (estimated), completed_segments, status, model_used,
    started_at, finished_at, error
  ExtractionSegment:
    id, extraction_id, segment_index, segment_title, text, raw_excerpt,
    page_or_timestamp, started_at, finished_at, model_used
"""

from __future__ import annotations

import asyncio
import base64
import io
import json
import logging
import os
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .oversight_service import STORAGE_DIR, now_iso
from .oversight_upload_session import (
    get_upload_session_service, UploadSession,
)
from ..core.models_registry import (
    pick_best_extraction_model, mime_to_required_capability,
    ModelCapability, get_model, MODEL_REGISTRY,
)

logger = logging.getLogger(__name__)

EXTRACTIONS_FILE: Path = STORAGE_DIR / "extractions.json"

# ─────────── سقف‌های ایمنی ───────────
MAX_PAGES_PER_PDF: int = 5000  # عملاً unlimited
MAX_PARAGRAPHS_PER_DOCX: int = 100_000
MAX_ROWS_PER_SHEET: int = 1_000_000
SEGMENT_TEXT_MAX_CHARS: int = 200_000  # هر segment تا 200K char
PER_SEGMENT_TIMEOUT_SEC: int = 300  # 5 دقیقه
INLINE_MEDIA_BYTES_LIMIT: int = 18 * 1024 * 1024  # 18MB
AV_CHUNK_SECONDS: int = 300  # 5 دقیقه per audio/video chunk
MEMORY_THRESHOLD_PCT: float = 80.0  # اگر RAM >80%, تأخیر بده

# ─────────── extraction concurrency ───────────
_EXTRACTION_SEMAPHORE = asyncio.Semaphore(1)


async def _wait_for_memory_headroom(max_wait_sec: int = 60) -> None:
    """اگر RAM سیستم بالای آستانه است، تا max_wait صبر کن (به جای OOM crash).
    در صورت عدم وجود psutil، silent pass.
    """
    try:
        import psutil
    except ImportError:
        return
    waited = 0
    while waited < max_wait_sec:
        try:
            pct = psutil.virtual_memory().percent
        except Exception:
            return
        if pct < MEMORY_THRESHOLD_PCT:
            return
        logger.warning(
            f"memory at {pct}% > {MEMORY_THRESHOLD_PCT}% — تأخیر extraction (waited {waited}s)"
        )
        await asyncio.sleep(5)
        waited += 5
    logger.warning(f"memory still high after {max_wait_sec}s — ادامه می‌دهیم (best-effort)")


def _ffmpeg_available() -> bool:
    """آیا ffmpeg در PATH هست؟"""
    import shutil
    return shutil.which("ffmpeg") is not None


async def _ffmpeg_chunk_av(
    input_path: Path,
    output_dir: Path,
    chunk_seconds: int = AV_CHUNK_SECONDS,
) -> List[Path]:
    """تقسیم audio/video به chunkهای N ثانیه‌ای. خروجی: لیست chunk paths.

    استفاده از segment muxer — copy stream، بدون re-encode → سریع و
    لاجواب لیترال. اگر ffmpeg موجود نباشد، RuntimeError.
    """
    if not _ffmpeg_available():
        raise RuntimeError("ffmpeg در PATH نیست — chunking ممکن نیست")
    output_dir.mkdir(parents=True, exist_ok=True)
    pattern = str(output_dir / "chunk_%04d" + input_path.suffix)
    # cmd: ffmpeg -i input -c copy -f segment -segment_time N -reset_timestamps 1 pattern
    cmd = [
        "ffmpeg", "-hide_banner", "-loglevel", "error",
        "-i", str(input_path),
        "-c", "copy", "-f", "segment",
        "-segment_time", str(chunk_seconds),
        "-reset_timestamps", "1",
        pattern,
    ]
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        # 🛡 (audit fix MINOR) — timeout 10 دقیقه برای chunking یک فایل بزرگ
        _, stderr = await asyncio.wait_for(proc.communicate(), timeout=600)
    except asyncio.TimeoutError:
        try:
            proc.kill()
        except Exception:
            pass
        raise RuntimeError("ffmpeg chunking timeout after 10 minutes")
    if proc.returncode != 0:
        raise RuntimeError(
            f"ffmpeg returned {proc.returncode}: {stderr.decode('utf-8', errors='ignore')[:500]}"
        )
    chunks = sorted(output_dir.glob(f"chunk_*{input_path.suffix}"))
    return chunks


# ====================================================================
# Dataclasses
# ====================================================================

@dataclass
class ExtractionSegment:
    id: str
    extraction_id: str
    segment_index: int
    segment_title: str
    text: str = ""
    raw_excerpt: str = ""
    page_or_timestamp: str = ""
    model_used: str = ""
    started_at: str = field(default_factory=now_iso)
    finished_at: Optional[str] = None
    status: str = "pending"  # pending|done|failed
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class FileExtraction:
    id: str
    task_id: Optional[str]
    session_id: str
    file_order: int
    original_filename: str
    mime_type: str
    total_segments: int = 0     # estimated (و بعد updated)
    completed_segments: int = 0
    status: str = "pending"     # pending|extracting|extracted|failed
    model_used: str = ""
    started_at: str = field(default_factory=now_iso)
    finished_at: Optional[str] = None
    error: Optional[str] = None
    # متن کامل ادغام‌شده (cache برای read سریع)
    full_text_cache: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ====================================================================
# Repository (JSON persistence)
# ====================================================================

class ExtractionRepo:
    """Repository برای FileExtraction + ExtractionSegment.

    دو لیست موازی در یک JSON ذخیره می‌شوند تا read/write atomic بمانند.
    """

    def __init__(self) -> None:
        self._extractions: Dict[str, FileExtraction] = {}
        self._segments: Dict[str, List[ExtractionSegment]] = {}  # ext_id -> [segments]
        self._lock = asyncio.Lock()
        self._load()

    def _load(self) -> None:
        if not EXTRACTIONS_FILE.exists():
            return
        try:
            data = json.loads(EXTRACTIONS_FILE.read_text(encoding="utf-8"))
            for e in data.get("extractions", []):
                try:
                    fe = FileExtraction(**e)
                    self._extractions[fe.id] = fe
                except Exception as exc:
                    logger.warning(f"extractions: skip malformed entry: {exc}")
            for ext_id, segs in (data.get("segments", {}) or {}).items():
                out: List[ExtractionSegment] = []
                for s in segs:
                    try:
                        out.append(ExtractionSegment(**s))
                    except Exception as exc:
                        logger.warning(f"extractions: skip malformed segment: {exc}")
                self._segments[ext_id] = out
        except Exception as e:
            logger.warning(f"extractions: load failed: {e}")

    def _save(self) -> None:
        try:
            data = {
                "extractions": [e.to_dict() for e in self._extractions.values()],
                "segments": {
                    ext_id: [s.to_dict() for s in segs]
                    for ext_id, segs in self._segments.items()
                },
            }
            tmp = EXTRACTIONS_FILE.with_suffix(".json.tmp")
            tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            tmp.replace(EXTRACTIONS_FILE)
        except Exception as e:
            logger.warning(f"extractions: save failed: {e}")

    async def create_extraction(self, fe: FileExtraction) -> FileExtraction:
        async with self._lock:
            self._extractions[fe.id] = fe
            self._segments.setdefault(fe.id, [])
            self._save()
        return fe

    async def update_extraction(self, extraction_id: str, **patch: Any) -> Optional[FileExtraction]:
        async with self._lock:
            fe = self._extractions.get(extraction_id)
            if fe is None:
                return None
            for k, v in patch.items():
                if hasattr(fe, k):
                    setattr(fe, k, v)
            self._save()
            return fe

    async def add_segment(self, extraction_id: str, seg: ExtractionSegment) -> ExtractionSegment:
        async with self._lock:
            self._segments.setdefault(extraction_id, []).append(seg)
            # update completed counter
            fe = self._extractions.get(extraction_id)
            if fe and seg.status == "done":
                fe.completed_segments = sum(
                    1 for s in self._segments[extraction_id] if s.status == "done"
                )
                # update full_text_cache incrementally
                fe.full_text_cache = self._build_full_text(extraction_id)
            self._save()
        return seg

    async def update_segment(self, segment_id: str, **patch: Any) -> Optional[ExtractionSegment]:
        async with self._lock:
            for ext_id, segs in self._segments.items():
                for s in segs:
                    if s.id == segment_id:
                        for k, v in patch.items():
                            if hasattr(s, k):
                                setattr(s, k, v)
                        # update parent fe
                        fe = self._extractions.get(ext_id)
                        if fe:
                            fe.completed_segments = sum(
                                1 for ss in segs if ss.status == "done"
                            )
                            fe.full_text_cache = self._build_full_text(ext_id)
                        self._save()
                        return s
        return None

    def _build_full_text(self, extraction_id: str) -> str:
        segs = self._segments.get(extraction_id) or []
        segs_sorted = sorted(segs, key=lambda s: s.segment_index)
        parts: List[str] = []
        for s in segs_sorted:
            if s.status != "done":
                continue
            head = f"## {s.segment_title}" if s.segment_title else f"## Segment {s.segment_index}"
            if s.page_or_timestamp:
                head += f"  _(at: {s.page_or_timestamp})_"
            parts.append(head)
            parts.append(s.text)
        return "\n\n".join(parts)

    def get(self, extraction_id: str) -> Optional[FileExtraction]:
        return self._extractions.get(extraction_id)

    def get_segments(self, extraction_id: str) -> List[ExtractionSegment]:
        return list(self._segments.get(extraction_id) or [])

    def list_by_task(self, task_id: str) -> List[FileExtraction]:
        out = [e for e in self._extractions.values() if e.task_id == task_id]
        out.sort(key=lambda e: e.file_order)
        return out

    def list_by_session(self, session_id: str) -> List[FileExtraction]:
        return [e for e in self._extractions.values() if e.session_id == session_id]

    def full_text(self, extraction_id: str) -> str:
        return self._build_full_text(extraction_id)


# ──── singleton ────
_repo_instance: Optional[ExtractionRepo] = None


def get_extraction_repo() -> ExtractionRepo:
    global _repo_instance
    if _repo_instance is None:
        _repo_instance = ExtractionRepo()
    return _repo_instance


async def boot_recover_stale_extractions() -> Dict[str, int]:
    """در startup، extractionهای stale (status='extracting' بدون فعالیت) را شناسایی
    و mark failed کنیم. session مرتبط هم به 'failed' برگردانده می‌شود.

    این به کاربر اجازه می‌دهد دوباره trigger کند و از segmentهای done ادامه دهد
    (extract_session خودش resume-friendly است).
    """
    from datetime import datetime, timezone, timedelta
    repo = get_extraction_repo()
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=5)
    cleared = 0
    for fe in list(repo._extractions.values()):
        if fe.status != "extracting":
            continue
        # last activity = آخرین segment finished_at، یا started_at
        last_active = fe.started_at
        segs = repo.get_segments(fe.id)
        if segs:
            done_segs = [s for s in segs if s.finished_at]
            if done_segs:
                last_active = max(s.finished_at for s in done_segs if s.finished_at)
        try:
            ts = datetime.fromisoformat((last_active or "").replace("Z", "+00:00"))
        except Exception:
            ts = datetime.min.replace(tzinfo=timezone.utc)
        if ts < cutoff:
            await repo.update_extraction(
                fe.id,
                status="failed",
                error="boot recovery: extraction interrupted by restart",
                finished_at=datetime.now(timezone.utc).isoformat(),
            )
            # session هم به failed (تا کاربر بفهمد و دوباره trigger کند)
            try:
                from .oversight_upload_session import get_upload_session_service
                up = get_upload_session_service()
                s = up.get(fe.session_id)
                if s and s.status == "extracting":
                    await up.set_status(s.id, "completed",  # نه failed — بتواند resume
                                        error="extraction interrupted by restart")
            except Exception as e:
                logger.debug(f"boot recovery session update failed: {e}")
            cleared += 1
    return {"cleared_stale_extractions": cleared}


# ====================================================================
# Extraction service
# ====================================================================

class ExtractionError(Exception):
    pass


async def _ai_extract_text(
    model_id: str,
    *,
    prompt: str,
    image_b64: Optional[str] = None,
    inline_file_data: Optional[Tuple[str, bytes]] = None,  # (mime, bytes) — for Gemini Files
    max_tokens: int = 32000,
) -> str:
    """فراخوانی AI برای استخراج متن از یک قطعه (صفحه/فریم/audio chunk).

    استفاده از ai_manager موجود — provider-agnostic. اگر مدل Gemini است،
    گزینهٔ `images` (base64) را قبول می‌کند. برای audio/video با Gemini،
    inline_file_data به‌صورت base64-inline در پیام درج می‌شود (Gemini
    حداکثر ~20MB inline قبول می‌کند — برای فایل‌های بزرگ‌تر Stage 9
    ffmpeg chunking خواهد داشت).
    """
    from .ai_manager import get_ai_manager
    from .ai_base import Message

    images: Optional[List[str]] = None
    if image_b64:
        images = [image_b64]

    # برای Gemini با audio/video، در حال حاضر inline base64 — برای فایل‌های
    # کوچک کفایت می‌کند. در Stage 9 با Files API + ffmpeg chunking.
    extra_text = ""
    if inline_file_data is not None:
        mime, raw = inline_file_data
        if len(raw) > 18 * 1024 * 1024:
            # Gemini inline limit ~20MB — برای chunkهای بزرگ‌تر، در Stage 9
            # ffmpeg به chunkهای ≤5min تقسیم می‌کند
            raise ExtractionError(
                f"chunk too large for inline ({len(raw)} bytes). Need ffmpeg chunking."
            )
        b64 = base64.b64encode(raw).decode("ascii")
        extra_text = (
            f"\n\n[فایل پیوست به‌صورت base64 با mime={mime}؛ "
            f"حجم = {len(raw)} bytes؛ متن کامل را استخراج کن.]"
        )
        # برای provider Gemini، images را برای هر inline_data استفاده می‌کنیم
        # (ai_base.Message.images هم برای image هم برای generic inline قابل
        # استفاده است در GeminiService.)
        images = (images or []) + [b64]

    mgr = get_ai_manager()
    messages = [
        Message(role="system", content=(
            "تو یک ابزار استخراج متن دقیق هستی. وظیفه‌ات:\n"
            "1) متن کامل و literal از محتوای داده‌شده استخراج کن.\n"
            "2) هیچ‌چیز را خلاصه نکن، هیچ‌چیز را drop نکن.\n"
            "3) اگر صحبت اضافی هست، آن را هم بنویس.\n"
            "4) اگر متن داخل تصویر/سند به زبان فارسی است، فارسی بنویس.\n"
            "5) اگر صدا است، transcript کامل بنویس با timestamp اگر ممکن است.\n"
        )),
        Message(role="user", content=prompt + extra_text, images=images),
    ]
    resp = await mgr.generate(
        model_id=model_id,
        messages=messages,
        max_tokens=max_tokens,
        temperature=0.1,
    )
    return (resp.content or "").strip()


async def _plan_headings(model_id: str, user_idea: str, filename: str, mime: str) -> List[str]:
    """گام «عناوین داینامیک»: قبل از استخراج، از مدل می‌خواهیم headings/sections
    حسب user_idea و mime پیشنهاد دهد. در صورت شکست، headings عمومی برمی‌گرداند.
    """
    from .ai_manager import get_ai_manager
    from .ai_base import Message
    try:
        mgr = get_ai_manager()
        messages = [
            Message(role="system", content=(
                "تو یک مشاور هستی. کاربر یک ایده داده + یک فایل پیوست. ایده + متادیتای فایل را "
                "ببین و یک لیست JSON از 3 تا 8 heading/section بساز که برای استخراج «هدفمند» "
                "از این فایل مفید باشد. ترتیب از مهم‌ترین به کم‌اهمیت‌ترین."
            )),
            Message(role="user", content=(
                f"ایدهٔ کاربر:\n{user_idea[:2000]}\n\n"
                f"فایل پیوست: {filename}  (mime={mime})\n\n"
                "خروجی فقط JSON: {\"headings\": [\"...\", \"...\"]}"
            )),
        ]
        resp = await mgr.generate(model_id=model_id, messages=messages, max_tokens=2000, temperature=0.2)
        # parse
        import re
        m = re.search(r'\{[^{}]*"headings"\s*:\s*\[.*?\]\s*\}', resp.content or "", re.DOTALL)
        if m:
            data = json.loads(m.group(0))
            hs = [str(x)[:200] for x in (data.get("headings") or [])]
            if hs:
                return hs[:8]
    except Exception as e:
        logger.debug(f"_plan_headings failed: {e}")
    # fallback عمومی
    return [
        "خلاصهٔ کلی محتوا",
        "جزئیات اصلی و نکات کلیدی",
        "اطلاعات تکمیلی و frequently mentioned items",
    ]


# ─────────────── per-mime extractors ───────────────

def _read_text_file(path: Path) -> str:
    """خواندن متن خام (txt, md, csv, log, json, ...)."""
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        raise ExtractionError(f"read text failed: {e}")


async def _render_pdf_page_to_b64(path: Path, page_num: int) -> Optional[str]:
    """رندر یک صفحهٔ PDF به PNG → base64.

    🆕 (Stage 9) — برای صفحات scan-only که pypdf متن استخراج نمی‌کند.
    ابتدا pdftoppm (poppler) را امتحان می‌کنیم (نتیجهٔ بهتر، سریع‌تر).
    اگر در دسترس نبود، fallback به render via Pillow + پیغام.

    خروجی: PNG base64 string، یا None اگر هیچ ابزار rendering موجود نباشد.
    """
    import shutil, tempfile
    pdftoppm = shutil.which("pdftoppm")
    if pdftoppm:
        with tempfile.TemporaryDirectory() as tmp:
            out_prefix = Path(tmp) / "p"
            cmd = [
                pdftoppm,
                "-png", "-r", "150",
                "-f", str(page_num), "-l", str(page_num),
                str(path), str(out_prefix),
            ]
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.PIPE,
            )
            try:
                # 🛡 (audit fix MINOR) — timeout سخت تا روی PDF مخدوش hang نکند
                _, stderr = await asyncio.wait_for(proc.communicate(), timeout=30)
            except asyncio.TimeoutError:
                try:
                    proc.kill()
                except Exception:
                    pass
                logger.warning(f"pdftoppm timeout on page {page_num} after 30s")
                return None
            if proc.returncode != 0:
                logger.debug(
                    f"pdftoppm exit {proc.returncode}: {stderr.decode('utf-8', errors='ignore')[:200]}"
                )
                return None
            # pdftoppm naming: p-1.png یا p-01.png …
            candidates = sorted(Path(tmp).glob("p-*.png"))
            if not candidates:
                return None
            try:
                return base64.b64encode(candidates[0].read_bytes()).decode("ascii")
            except Exception:
                return None
    # fallback نهایی — هیچ rendering در دسترس نیست
    return None


def _extract_pdf_pages(path: Path) -> List[Tuple[int, str]]:
    """استخراج text-only از PDF با pypdf. صفحه‌های scan شده فقط با AI extract
    می‌شوند (در main routing). خروجی: [(page_num, text)] فقط صفحاتی که
    pypdf توانست متن استخراج کند.
    """
    try:
        from pypdf import PdfReader
    except ImportError:
        raise ExtractionError("pypdf نصب نیست (Stage 1 dep)")
    try:
        reader = PdfReader(str(path))
        out: List[Tuple[int, str]] = []
        for i, page in enumerate(reader.pages[:MAX_PAGES_PER_PDF], start=1):
            try:
                text = (page.extract_text() or "").strip()
            except Exception:
                text = ""
            out.append((i, text))
        return out
    except Exception as e:
        raise ExtractionError(f"pypdf failed: {e}")


def _extract_docx_paragraphs(path: Path) -> List[str]:
    try:
        import docx
    except ImportError:
        raise ExtractionError("python-docx نصب نیست (Stage 1 dep)")
    try:
        d = docx.Document(str(path))
        out: List[str] = []
        for p in d.paragraphs[:MAX_PARAGRAPHS_PER_DOCX]:
            t = (p.text or "").strip()
            if t:
                out.append(t)
        # tables هم
        for table in d.tables:
            for row in table.rows:
                cells = [c.text.strip() for c in row.cells]
                line = " | ".join(cells)
                if line.strip(" |"):
                    out.append(line)
        return out
    except Exception as e:
        raise ExtractionError(f"python-docx failed: {e}")


def _extract_xlsx_sheets(path: Path) -> List[Tuple[str, str]]:
    """خروجی: [(sheet_name, csv_like_text)]"""
    try:
        from openpyxl import load_workbook
    except ImportError:
        raise ExtractionError("openpyxl نصب نیست (Stage 1 dep)")
    try:
        wb = load_workbook(str(path), read_only=True, data_only=True)
        out: List[Tuple[str, str]] = []
        for sheet in wb.worksheets:
            rows: List[str] = []
            for i, row in enumerate(sheet.iter_rows(values_only=True)):
                if i >= MAX_ROWS_PER_SHEET:
                    break
                cells = [str(c) if c is not None else "" for c in row]
                rows.append("\t".join(cells))
            out.append((sheet.title, "\n".join(rows)))
        return out
    except Exception as e:
        raise ExtractionError(f"openpyxl failed: {e}")


# ─────────────── main entry ───────────────

async def extract_session(
    session_id: str,
    *,
    user_idea: str = "",
    preferred_model_id: Optional[str] = None,
    db_enabled_ids: Optional[List[str]] = None,
) -> FileExtraction:
    """استخراج یک upload session را شروع می‌کند. atomic، resumable.

    اگر extraction قبلی برای این session موجود است و status='extracting'،
    از آخرین completed_segment ادامه می‌دهد.
    خروجی: FileExtraction در حالت نهایی (extracted یا failed).
    """
    upload_svc = get_upload_session_service()
    repo = get_extraction_repo()

    session = upload_svc.get(session_id)
    if session is None:
        raise ExtractionError(f"session {session_id} یافت نشد")
    if session.status not in ("completed", "extracting"):
        raise ExtractionError(
            f"session در وضعیت {session.status} است — completed لازم است"
        )

    # serialize کن — هم‌زمان فقط یک extraction (atomic check-create-run)
    async with _EXTRACTION_SEMAPHORE:
        # 🆕 (audit fix CRITICAL) — check-create داخل semaphore تا race condition
        # نداشته باشیم. اگر دو caller هم‌زمان trigger کنند، دومی صبر می‌کند
        # و سپس extraction قبلی را resume می‌کند.
        existing = repo.list_by_session(session_id)
        fe = existing[0] if existing else None
        if fe is None:
            model = pick_best_extraction_model(
                session.mime_type,
                preferred_model_id=preferred_model_id,
                db_enabled_ids=db_enabled_ids,
            )
            if model is None:
                raise ExtractionError(
                    f"هیچ مدل بصری enabled برای mime {session.mime_type} پیدا نشد — "
                    f"از /models یک مدل multimodal فعال کن"
                )
            fe = FileExtraction(
                id=str(uuid.uuid4()),
                task_id=session.task_id,
                session_id=session.id,
                file_order=session.file_order,
                original_filename=session.original_filename,
                mime_type=session.mime_type,
                model_used=model.id,
                status="extracting",
            )
            await repo.create_extraction(fe)

        try:
            await upload_svc.set_status(session.id, "extracting")
            await repo.update_extraction(fe.id, status="extracting", started_at=now_iso())
            await _run_extraction(fe, session, user_idea, repo)
            # success
            await repo.update_extraction(
                fe.id, status="extracted", finished_at=now_iso(),
                error=None,
            )
            await upload_svc.set_status(session.id, "extracted")
        except ExtractionError as e:
            logger.warning(f"extraction failed for {session.id}: {e}")
            await repo.update_extraction(fe.id, status="failed", error=str(e)[:500],
                                          finished_at=now_iso())
            await upload_svc.set_status(session.id, "failed", error=str(e)[:500])
            raise
        except Exception as e:
            logger.exception(f"extraction unexpected error for {session.id}")
            await repo.update_extraction(fe.id, status="failed", error=str(e)[:500],
                                          finished_at=now_iso())
            await upload_svc.set_status(session.id, "failed", error=str(e)[:500])
            raise

    return fe


async def _run_extraction(
    fe: FileExtraction,
    session: UploadSession,
    user_idea: str,
    repo: ExtractionRepo,
) -> None:
    """منطق per-mime routing. هر segment به‌محض اتمام در repo ذخیره می‌شود."""
    path = Path(session.temp_path)
    if not path.exists():
        raise ExtractionError(f"temp file یافت نشد: {session.temp_path}")

    mime = (session.mime_type or "").lower()
    completed = {s.segment_index for s in repo.get_segments(fe.id) if s.status == "done"}

    async def _persist_segment(idx: int, title: str, text: str, page_ts: str = "") -> None:
        # truncate طولانی‌های بسیار بزرگ — جلوگیری از JSON عظیم
        if len(text) > SEGMENT_TEXT_MAX_CHARS:
            text = text[:SEGMENT_TEXT_MAX_CHARS] + "\n…[TRUNCATED at limit]"
        seg = ExtractionSegment(
            id=str(uuid.uuid4()),
            extraction_id=fe.id,
            segment_index=idx,
            segment_title=title[:200],
            text=text,
            raw_excerpt=text[:300],
            page_or_timestamp=page_ts,
            model_used=fe.model_used,
            status="done",
            finished_at=now_iso(),
        )
        await repo.add_segment(fe.id, seg)

    # ─────────── routing ───────────
    if mime.startswith("text/") or mime in ("application/json", "application/xml"):
        text = _read_text_file(path)
        # یک segment کل فایل (یا تقسیم بر اساس heading اگر بزرگ است)
        if 0 not in completed:
            await _persist_segment(0, fe.original_filename, text, "")
        await repo.update_extraction(fe.id, total_segments=1)
        return

    if mime == "application/pdf":
        pages = _extract_pdf_pages(path)
        await repo.update_extraction(fe.id, total_segments=len(pages))
        # برای صفحاتی که pypdf متن نگرفت → AI extraction (Gemini)
        for page_num, txt in pages:
            if page_num in completed:
                continue
            await _wait_for_memory_headroom()
            if txt.strip():
                await _persist_segment(page_num, f"صفحه {page_num}", txt, f"page={page_num}")
            else:
                # 🆕 (Stage 9) — صفحه scan-only: render شده با Gemini Vision
                # خواندن صفحه به‌صورت image و ارسال به مدل
                try:
                    img_b64 = await _render_pdf_page_to_b64(path, page_num)
                except Exception as e:
                    img_b64 = None
                    logger.warning(f"PDF page {page_num} render failed: {e}")
                if img_b64 is None:
                    await _persist_segment(
                        page_num, f"صفحه {page_num} (scan)",
                        "[این صفحه scan-only است و render تصویری ناموفق بود. "
                        "اگر pypdf نسخهٔ متن استخراج نمی‌کند، احتمالاً encrypted/کیفیت پایین است.]",
                        f"page={page_num}",
                    )
                    continue
                prompt = (
                    f"این تصویر صفحهٔ {page_num} از یک PDF است. "
                    "متن کامل و literal این صفحه را OCR کن — هیچ‌چیز را خلاصه نکن، "
                    "هیچ خطی drop نشود. اگر متن فارسی است، فارسی بنویس."
                )
                try:
                    text = await asyncio.wait_for(
                        _ai_extract_text(fe.model_used, prompt=prompt, image_b64=img_b64, max_tokens=16000),
                        timeout=PER_SEGMENT_TIMEOUT_SEC,
                    )
                except asyncio.TimeoutError:
                    text = f"[timeout بعد از {PER_SEGMENT_TIMEOUT_SEC}s — page {page_num}]"
                except Exception as e:
                    text = f"[OCR خطا: {str(e)[:200]}]"
                await _persist_segment(page_num, f"صفحه {page_num} (OCR)", text, f"page={page_num}")
        return

    if mime in (
        "application/msword",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ):
        paragraphs = _extract_docx_paragraphs(path)
        # هر 50 پاراگراف یک segment (تا حجم متعادل بماند)
        CHUNK = 50
        groups = [paragraphs[i:i + CHUNK] for i in range(0, len(paragraphs), CHUNK)]
        await repo.update_extraction(fe.id, total_segments=len(groups))
        for idx, g in enumerate(groups, start=1):
            if idx in completed:
                continue
            text = "\n\n".join(g)
            await _persist_segment(idx, f"بخش {idx}", text, f"paragraphs {idx*CHUNK-CHUNK+1}..{idx*CHUNK}")
        return

    if mime in (
        "application/vnd.ms-excel",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ):
        sheets = _extract_xlsx_sheets(path)
        await repo.update_extraction(fe.id, total_segments=len(sheets))
        for idx, (name, text) in enumerate(sheets, start=1):
            if idx in completed:
                continue
            await _persist_segment(idx, f"شیت: {name}", text, f"sheet={name}")
        return

    if mime.startswith("image/"):
        # base64 → Gemini → full literal description
        headings = await _plan_headings(fe.model_used, user_idea, fe.original_filename, mime)
        # کل تصویر = یک segment (یا چند segment per heading)
        await repo.update_extraction(fe.id, total_segments=len(headings))
        try:
            raw = path.read_bytes()
            b64 = base64.b64encode(raw).decode("ascii")
        except Exception as e:
            raise ExtractionError(f"image read failed: {e}")
        for idx, h in enumerate(headings, start=1):
            if idx in completed:
                continue
            await _wait_for_memory_headroom()
            prompt = (
                f"در این تصویر، **متن کامل و literal** مرتبط با heading زیر را استخراج کن:\n"
                f"  HEADING: {h}\n\n"
                f"اگر متن داخل تصویر هست، literal بنویس. اگر صحنه/object است، توصیف کامل بده.\n"
                f"هیچ‌چیز را خلاصه نکن."
            )
            try:
                text = await asyncio.wait_for(
                    _ai_extract_text(fe.model_used, prompt=prompt, image_b64=b64, max_tokens=16000),
                    timeout=PER_SEGMENT_TIMEOUT_SEC,
                )
            except asyncio.TimeoutError:
                text = f"[timeout بعد از {PER_SEGMENT_TIMEOUT_SEC}s]"
            except Exception as e:
                text = f"[خطا: {str(e)[:200]}]"
            await _persist_segment(idx, h, text, "image")
        return

    if mime.startswith("audio/") or mime.startswith("video/"):
        size = path.stat().st_size if path.exists() else 0
        # 🆕 (Stage 9) — برای فایل‌های بزرگ، ffmpeg chunking 5-دقیقه‌ای
        if size > INLINE_MEDIA_BYTES_LIMIT:
            if not _ffmpeg_available():
                # ffmpeg در سیستم نیست — به‌جای fail، placeholder بسازیم
                # تا کاربر بداند چرا
                await repo.update_extraction(fe.id, total_segments=1)
                await _persist_segment(
                    1, fe.original_filename,
                    "[فایل بزرگ‌تر از 18MB و ffmpeg در سیستم نصب نیست. "
                    "برای استخراج کامل، ffmpeg را نصب کنید یا فایل را به chunk های ≤18MB "
                    "خرد کنید و دوباره آپلود کنید.]",
                    f"size={size}B",
                )
                return
            # chunk
            chunks_dir = path.parent / f"{path.stem}_chunks"
            try:
                chunk_files = await _ffmpeg_chunk_av(path, chunks_dir, AV_CHUNK_SECONDS)
            except Exception as e:
                raise ExtractionError(f"ffmpeg chunking failed: {e}")
            if not chunk_files:
                raise ExtractionError("ffmpeg تولید chunk نکرد")
            # عناوین فقط بر اساس user_idea
            base_headings = await _plan_headings(
                fe.model_used, user_idea, fe.original_filename, mime
            )
            heading_default = base_headings[0] if base_headings else "محتوای کامل"
            await repo.update_extraction(fe.id, total_segments=len(chunk_files))
            try:
                for idx, ch_path in enumerate(chunk_files, start=1):
                    if idx in completed:
                        continue
                    await _wait_for_memory_headroom()
                    try:
                        ch_bytes = ch_path.read_bytes()
                    except Exception as e:
                        await _persist_segment(idx, f"chunk {idx}", f"[خواندن chunk: {e}]",
                                                f"t={idx*AV_CHUNK_SECONDS-AV_CHUNK_SECONDS}s..")
                        continue
                    prompt = (
                        f"این chunk شمارهٔ {idx} از یک فایل "
                        f"{('صوتی' if mime.startswith('audio/') else 'ویدئویی')} است "
                        f"(تقریباً ثانیه {idx*AV_CHUNK_SECONDS-AV_CHUNK_SECONDS} تا {idx*AV_CHUNK_SECONDS}).\n"
                        f"raw transcript کامل و literal این chunk را بنویس. هیچ‌چیز را خلاصه نکن.\n"
                        f"اگر دیالوگ هست، با هویت گوینده‌ها (اگر مشخص). اگر صحنه است، توصیف صریح."
                    )
                    try:
                        text = await asyncio.wait_for(
                            _ai_extract_text(
                                fe.model_used, prompt=prompt,
                                inline_file_data=(mime, ch_bytes),
                                max_tokens=16000,
                            ),
                            timeout=PER_SEGMENT_TIMEOUT_SEC,
                        )
                    except asyncio.TimeoutError:
                        text = f"[timeout بعد از {PER_SEGMENT_TIMEOUT_SEC}s — chunk {idx}]"
                    except Exception as e:
                        text = f"[خطا: {str(e)[:200]}]"
                    ts = f"t={(idx-1)*AV_CHUNK_SECONDS}s..{idx*AV_CHUNK_SECONDS}s"
                    await _persist_segment(idx, f"chunk {idx}: {heading_default}", text, ts)
            finally:
                # cleanup chunks
                try:
                    for f in chunk_files:
                        try:
                            f.unlink()
                        except Exception:
                            pass
                    try:
                        chunks_dir.rmdir()
                    except Exception:
                        pass
                except Exception:
                    pass
            return
        # فایل کوچک — inline base64 (همان مسیر قبلی)
        try:
            raw = path.read_bytes()
        except Exception as e:
            raise ExtractionError(f"audio/video read failed: {e}")
        headings = await _plan_headings(fe.model_used, user_idea, fe.original_filename, mime)
        await repo.update_extraction(fe.id, total_segments=len(headings))
        for idx, h in enumerate(headings, start=1):
            if idx in completed:
                continue
            await _wait_for_memory_headroom()
            prompt = (
                f"در این فایل {('صوتی' if mime.startswith('audio/') else 'تصویری/ویدئویی')}، "
                f"**رونویسی/توصیف کامل و literal** مرتبط با heading زیر را بنویس:\n"
                f"  HEADING: {h}\n\n"
                f"اگر گفتگو هست، literal transcript. اگر صحنه است، توصیف. هیچ‌چیز را خلاصه نکن."
            )
            try:
                text = await asyncio.wait_for(
                    _ai_extract_text(
                        fe.model_used, prompt=prompt,
                        inline_file_data=(mime, raw),
                        max_tokens=16000,
                    ),
                    timeout=PER_SEGMENT_TIMEOUT_SEC,
                )
            except asyncio.TimeoutError:
                text = f"[timeout بعد از {PER_SEGMENT_TIMEOUT_SEC}s]"
            except Exception as e:
                text = f"[خطا: {str(e)[:200]}]"
            await _persist_segment(idx, h, text, mime)
        return

    # ─── fallback: mime ناشناخته ───
    # سعی کن text بخوانی؛ اگر شد خوب، نه → خطا
    try:
        text = _read_text_file(path)
    except Exception:
        text = ""
    if text:
        await repo.update_extraction(fe.id, total_segments=1)
        await _persist_segment(0, fe.original_filename, text, "raw")
        return
    raise ExtractionError(f"mime ناشناخته و قابل استخراج نیست: {mime}")
