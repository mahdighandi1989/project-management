"""Stage 6 — Evidence storage helpers.

ساختار:
  <storage_root>/verify_evidence/
    <task_id>/
      <run_id>/
        manifest.json   # خلاصهٔ run + لیست فایل‌ها
        ac01_xxx/
          step1_click_1234567890.png
          step2_visible_1234567891.png
          final_1234567892.png
        ac02_yyy/
          response.json
        ...

نکات:
- این ماژول I/O فایل دارد ولی نه async — برای استفاده در FastAPI
  از asyncio.to_thread استفاده کن.
- cleanup policy: حداکثر 5 run آخر per task، حذف بقیه.
- size cap: حداکثر 50MB per run؛ بیشتر → JPEG q=70 برای screenshot ها
  (در stage 9 implement می‌شود — اینجا فقط structure).
"""

from __future__ import annotations

import json
import logging
import shutil
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


MAX_RUNS_PER_TASK = 5
MAX_BYTES_PER_RUN = 50 * 1024 * 1024


def ensure_run_dir(storage_root: Path, task_id: str, run_id: str) -> Path:
    """مسیر run را ایجاد و برمی‌گرداند."""
    d = storage_root / "verify_evidence" / task_id / run_id
    d.mkdir(parents=True, exist_ok=True)
    return d


def write_manifest(
    run_dir: Path,
    *,
    task_id: str,
    run_id: str,
    probe_results: List[Dict[str, Any]],
    started_at: str,
    finished_at: str,
) -> Path:
    """manifest.json برای یک run می‌نویسد."""
    manifest = {
        "task_id": task_id,
        "run_id": run_id,
        "started_at": started_at,
        "finished_at": finished_at,
        "probe_count": len(probe_results),
        "probes": probe_results,
    }
    mpath = run_dir / "manifest.json"
    try:
        mpath.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except Exception as e:
        logger.warning(f"write_manifest failed: {e}")
    return mpath


def cleanup_old_runs(
    storage_root: Path, task_id: str, keep: int = MAX_RUNS_PER_TASK,
) -> int:
    """run های قدیمی یک task را حذف می‌کند، فقط `keep` run آخر را نگه می‌دارد.

    خروجی: تعداد runهای حذف‌شده.
    """
    task_dir = storage_root / "verify_evidence" / task_id
    if not task_dir.is_dir():
        return 0
    try:
        runs = sorted(
            (d for d in task_dir.iterdir() if d.is_dir()),
            key=lambda d: d.stat().st_mtime,
            reverse=True,
        )
    except Exception as e:
        logger.warning(f"cleanup_old_runs list failed: {e}")
        return 0
    to_delete = runs[keep:]
    deleted = 0
    for d in to_delete:
        try:
            shutil.rmtree(d, ignore_errors=True)
            deleted += 1
        except Exception as e:
            logger.warning(f"cleanup_old_runs delete {d}: {e}")
    return deleted


def list_runs_for_task(storage_root: Path, task_id: str) -> List[Dict[str, Any]]:
    """metadata همهٔ run های یک task را برمی‌گرداند، جدیدترین اول.

    خروجی: [{run_id, started_at?, finished_at?, probe_count?, size_bytes}]
    """
    task_dir = storage_root / "verify_evidence" / task_id
    if not task_dir.is_dir():
        return []
    out: List[Dict[str, Any]] = []
    try:
        runs = sorted(
            (d for d in task_dir.iterdir() if d.is_dir()),
            key=lambda d: d.stat().st_mtime,
            reverse=True,
        )
    except Exception:
        runs = []
    for d in runs:
        entry: Dict[str, Any] = {
            "run_id": d.name,
            "mtime": d.stat().st_mtime,
        }
        mp = d / "manifest.json"
        if mp.is_file():
            try:
                m = json.loads(mp.read_text(encoding="utf-8"))
                entry["started_at"] = m.get("started_at")
                entry["finished_at"] = m.get("finished_at")
                entry["probe_count"] = m.get("probe_count")
            except Exception:
                pass
        # تخمین size
        size = 0
        try:
            for sub in d.rglob("*"):
                if sub.is_file():
                    try:
                        size += sub.stat().st_size
                    except Exception:
                        continue
        except Exception:
            pass
        entry["size_bytes"] = size
        out.append(entry)
    return out


def resolve_evidence_file(
    storage_root: Path, task_id: str, run_id: str, rel_path: str,
) -> Optional[Path]:
    """مسیر absolute یک فایل evidence را برمی‌گرداند (یا None اگر سفر مسیر مشکوک).

    محافظت در برابر path traversal: rel_path نباید شامل ".." باشد و
    باید زیر storage_root/verify_evidence/<task_id>/<run_id>/ قرار بگیرد.
    """
    if not run_id or not task_id or not rel_path:
        return None
    base = (storage_root / "verify_evidence" / task_id / run_id).resolve()
    target = (base / rel_path).resolve()
    try:
        target.relative_to(base)  # raises if outside
    except ValueError:
        logger.warning(f"resolve_evidence_file: path traversal attempt: {rel_path}")
        return None
    if not target.is_file():
        return None
    return target
