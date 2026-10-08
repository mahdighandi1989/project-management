"""«نظارت و سرکشی» — the owner's inspection sheets over this app's own screens.

Ported from the sibling projects ALLIN1 (`backend/app/routers/inspection.py`)
and Detective-1 (`backend/detective/routers/inspection.py`); both are read-only
references and were not touched.

THE LOOP
    owner draws a box on any screen (or files a «درخواستِ عمومی»)
      →  a sheet is filed with the way BACK to it
      →  the scheduled supervisor (Claude Code Routine) reads the queue, does the
         work, answers UNDER the sheet with outcome + dependency walk (+ the
         after-picture for a claimed fix)
      →  the owner looks and ticks  →  the next round files it into a binder.

WHO IS THE SUPERVISOR — this app has no user login, so identity is a token:
the Routine sends ``X-Supervisor-Token`` equal to ``SUPERVISOR_TOKEN`` on the
server (falling back to ``EXTERNAL_TOOL_TOKEN``, already on Render). Everyone
else is the owner. The guards below are what make that distinction matter.

WHAT THIS ROUTER REFUSES
  * ``outcome='fixed'`` with no after-shot → 422.
  * the supervisor calling approve / delete / urgent → 403.
  * an outcome from anyone but the supervisor → 422.
  * a supervisor reply while an attached file is still UNREAD → 422, naming
    the file and what is left.
  * a remote URL as a shot → dropped (only data-URLs: no SSRF).

STORAGE — «در بک‌اند چیزی رو نگه ندار»: files and screenshots are spooled only
while in flight and then moved to the project's Google Drive folder by
``services/inspection_files.py``; rows keep the reference and the link.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel, Field, ValidationError
from sqlalchemy import func
from sqlalchemy.orm import Session

from ...core.database import get_db
from ...models.inspection import (
    BINDER_CAPACITY,
    EXTRACT_LABEL,
    KIND_GENERAL,
    KIND_SPOT,
    OUTCOME_FIXED,
    OUTCOME_NEEDS_OWNER,
    OUTCOMES,
    STATUS_ANSWERED,
    STATUS_APPROVED,
    STATUS_FILED,
    STATUS_OPEN,
    URGENT_CLAIM_TTL_S,
    InspectionBinder,
    InspectionFile,
    InspectionReport,
    InspectionShot,
    InspectionSurface,
    InspectionUpload,
    file_read_debt,
    sheet_glow,
)
from ...models.setting import Setting
from ...services import gdrive
from ...services import inspection_files as ifiles
from ...services.supervisor_rounds import next_round, record_round

router = APIRouter(prefix="/inspection", tags=["inspection"])

MAX_TEXT = 8000
MAX_SHOT_CHARS = 12_000_000
MAX_ACTIVE = int(os.environ.get("INSPECTION_MAX_ACTIVE", "500"))
_DATA_URL = "data:image/"
_ALLOWED_MIME = ("image/png", "image/jpeg", "image/webp")

#: The Routines' schedule, as configured in claude.ai. The countdown MEASURES the
#: urgent round from its knocks; these are what the board shows until then and
#: what the «روتین‌ها» tab documents. Keep in step with docs/supervisor/README.md.
FULL_CRON = os.environ.get("SUPERVISOR_FULL_CRON", "37 0 * * 2,5")
URGENT_CRON = os.environ.get("SUPERVISOR_URGENT_CRON", "11 */3 * * *")
ROUND_LOG_KEY = "inspection.urgent_rounds"
FULL_LOG_KEY = "inspection.full_rounds"
INVENTORY_KEY = "inspection.code_inventory"


# ---------------------------------------------------------------------------
# identity
# ---------------------------------------------------------------------------
def _supervisor_secret() -> str:
    return ((os.environ.get("SUPERVISOR_TOKEN") or "").strip()
            or (os.environ.get("EXTERNAL_TOOL_TOKEN") or "").strip())


def is_supervisor(request: Request) -> bool:
    # a supervisor SESSION (the Routine's headless browser) counts too
    if getattr(request.state, "auth_role", "") == "supervisor":
        return True
    secret = _supervisor_secret()
    got = (request.headers.get("x-supervisor-token") or "").strip()
    return bool(secret and got and hmac.compare_digest(secret, got))


def _who(request: Request) -> str:
    return "supervisor" if is_supervisor(request) else "owner"


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def _now() -> datetime:
    return datetime.utcnow()


def _iso(dt: Optional[datetime], plus: int = 0) -> Optional[str]:
    """Always zoned (the DB keeps naive UTC), so the browser can subtract."""
    if dt is None:
        return None
    return (dt + timedelta(seconds=plus)).replace(microsecond=0).isoformat() + "Z"


def _clean(v: Any, limit: int = MAX_TEXT) -> str:
    return str(v or "").replace("\x00", "")[:limit].strip()


def _headline(text: str) -> str:
    first = next((ln for ln in text.split("\n") if ln.strip()), "بدونِ عنوان")
    return first.strip()[:120]


def _notes(r: InspectionReport) -> List[dict]:
    try:
        v = json.loads(r.notes_json or "[]")
        return v if isinstance(v, list) else []
    except Exception:  # noqa: BLE001 - a corrupt row must not break the page
        return []


def _deps(r: InspectionReport) -> List[dict]:
    try:
        v = json.loads(r.deps_json or "[]")
        return v if isinstance(v, list) else []
    except Exception:  # noqa: BLE001
        return []


def _json_or_none(raw: str):
    try:
        return json.loads(raw) if (raw or "").strip() else None
    except Exception:  # noqa: BLE001
        return None


async def _body(request: Request, model):
    """Parse a JSON body whatever its Content-Type.

    The app's frontend talks to this API cross-origin through Cloudflare; the
    binding lesson in ``experiences/cloudflare-403-on-chunked-cross-origin-post.md``
    is to accept ``application/octet-stream`` as well as JSON, so a large body
    (a screenshot) can be sent in whichever shape gets through."""
    raw = await request.body()
    try:
        data = json.loads(raw) if raw else {}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"بدنهٔ درخواست JSON معتبر نیست: {exc}") from exc
    try:
        return model.model_validate(data)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=exc.errors()[:5]) from exc


def _split_data_url(shot: Optional[str]) -> Optional[tuple]:
    if not isinstance(shot, str) or not shot.startswith(_DATA_URL):
        return None
    if len(shot) > MAX_SHOT_CHARS:
        raise HTTPException(status_code=413, detail=(
            f"تصویر بیش از حد بزرگ است ({len(shot) // 1_000_000} مگابایت). صفحه تصویرها را پیش از "
            "ارسال کوچک می‌کند؛ صفحه را تازه کن و دوباره بچسبان."))
    try:
        mime, data = ifiles.decode_data_url(shot)
    except Exception:  # noqa: BLE001
        return None
    if mime not in _ALLOWED_MIME or not data:
        return None
    return mime, data


def _report_or_404(db: Session, report_id: str) -> InspectionReport:
    r = db.query(InspectionReport).filter(InspectionReport.id == report_id).first()
    if r is None:
        raise HTTPException(status_code=404, detail="گزارش پیدا نشد")
    return r


def _store_shot(db: Session, r: InspectionReport, note_id: str, kind: str, shot: Optional[str]) -> Optional[str]:
    parsed = _split_data_url(shot)
    if parsed is None:
        return None
    mime, data = parsed
    if not ifiles.spool_has_room(len(data)):
        raise HTTPException(status_code=507, detail=(
            "فضای موقتِ سرور پر است چون گوگل درایو هنوز وصل نیست و فایل‌ها منتظرند. "
            "از «نظارت و سرکشی › فضای ذخیره‌سازی» درایو را وصل کن."))
    sid = uuid.uuid4().hex[:24]
    n = db.query(func.count(InspectionShot.id)).filter(InspectionShot.report_id == r.id).scalar() or 0
    path = ifiles.write_shot_spool(sid, data, mime)
    db.add(InspectionShot(
        id=sid, report_id=r.id, note_id=note_id, kind=kind, mime=mime, byte_size=len(data),
        md5=hashlib.md5(data).hexdigest(),  # noqa: S324 - Drive integrity check
        ref=ifiles.shot_ref(r.number, int(n) + 1), store="pending", spool_path=path,
        store_note="در صفِ انتقال به گوگل درایو"))
    return sid


def _file_dict(f) -> dict:
    total = int(f.text_chars or 0)
    got = int(f.read_chars or 0)
    return {
        "id": f.id, "report_id": f.report_id, "note_id": f.note_id or "", "ref": f.ref or "",
        "filename": f.filename or "", "mime": f.mime or "",
        "byte_size": int(f.byte_size or 0), "size_label": ifiles.human_size(f.byte_size or 0),
        "caption": f.caption or "", "uploaded_by": f.uploaded_by or "",
        "created_at": _iso(f.created_at),
        # where the bytes are RIGHT NOW — never silent
        "store": f.store or "", "store_note": f.store_note or "",
        "durable": (f.store or "") == "drive",
        "drive_link": f.drive_link or "", "drive_path": f.drive_path or "",
        "drive_folder_link": f.drive_folder_link or "",
        "text_drive_link": f.text_drive_link or "",
        # what there is to read
        "extract_status": f.extract_status or "pending",
        "extract_label": EXTRACT_LABEL.get(f.extract_status or "pending", ""),
        "extract_note": f.extract_note or "",
        "text_chars": total, "page_count": int(f.page_count or 0),
        "text_truncated": bool(f.text_truncated),
        # the proof, in the open
        "read_chars": got,
        "read_percent": (round(100 * got / total) if total else None),
        "fully_read": bool(total and got >= total),
        "read_at": _iso(f.read_at), "read_by": f.read_by or "", "viewed_at": _iso(f.viewed_at),
    }


def _files_by_report(db: Session, ids: List[str]) -> dict:
    out: dict = {rid: [] for rid in ids}
    if not ids:
        return out
    for f in db.query(InspectionFile).filter(InspectionFile.report_id.in_(ids)).order_by(
            InspectionFile.created_at).all():
        out.setdefault(f.report_id, []).append(f)
    return out


def _shots_by_report(db: Session, ids: List[str]) -> dict:
    out: dict = {rid: {} for rid in ids}
    if not ids:
        return out
    for s in db.query(InspectionShot).filter(InspectionShot.report_id.in_(ids)).all():
        out.setdefault(s.report_id, {})[s.id] = {
            "ref": s.ref or "", "kind": s.kind, "store": s.store, "store_note": s.store_note or "",
            "drive_link": s.drive_link or "", "byte_size": int(s.byte_size or 0)}
    return out


def _claim_expired(r: InspectionReport) -> bool:
    if r.urgent_claimed_at is None:
        return True
    return (_now() - r.urgent_claimed_at).total_seconds() > URGENT_CLAIM_TTL_S


def _urgent_state(r: InspectionReport) -> dict:
    claimed = r.urgent_claimed_at is not None and not _claim_expired(r)
    return {
        "urgent": r.urgent_at is not None and r.urgent_done_at is None,
        "urgent_at": _iso(r.urgent_at),
        "urgent_done_at": _iso(r.urgent_done_at),
        "urgent_in_progress": claimed and r.urgent_done_at is None,
        "urgent_claimed_by": (r.urgent_claimed_by or "") if claimed else "",
        "urgent_claimed_at": _iso(r.urgent_claimed_at) if claimed else None,
        "urgent_claim_expires_at": _iso(r.urgent_claimed_at, URGENT_CLAIM_TTL_S) if claimed else None,
    }


def _to_dict(r: InspectionReport, files: Optional[list] = None, shots: Optional[dict] = None) -> dict:
    notes = _notes(r)
    return {
        "id": r.id, "number": r.number, "ref": ifiles.report_ref(r.number),
        "kind": r.kind or KIND_SPOT,
        "created_at": _iso(r.created_at), "updated_at": _iso(r.updated_at),
        "status": r.status, "title": r.title or "", "created_by": r.created_by or "",
        "page": r.page or "", "page_label": r.page_label or "",
        "section_id": r.section_id or "", "section_label": r.section_label or "",
        "reopen": r.reopen or "", "url": r.url or "",
        "dom_path": r.dom_path or "", "covered_text": r.covered_text or "",
        "rect": _json_or_none(r.rect_json), "viewport": _json_or_none(r.viewport_json),
        "geometry": _json_or_none(r.geometry_json),
        "notes": notes, "dependencies": _deps(r),
        "glow": sheet_glow(r.status, notes),
        **_urgent_state(r),
        "files": [_file_dict(f) for f in (files or [])],
        "read_debt": file_read_debt(files or []),
        "shots": shots or {},
        "binder": ({"id": r.binder_id, "number": r.binder_number, "page": r.binder_page}
                   if r.binder_id else None),
        "filed_at": _iso(r.filed_at),
    }


def _full(db: Session, r: InspectionReport) -> dict:
    return _to_dict(r, files=_files_by_report(db, [r.id]).get(r.id, []),
                    shots=_shots_by_report(db, [r.id]).get(r.id, {}))


def _many(db: Session, rows: list) -> list:
    ids = [r.id for r in rows]
    fmap, smap = _files_by_report(db, ids), _shots_by_report(db, ids)
    return [_to_dict(r, files=fmap.get(r.id, []), shots=smap.get(r.id, {})) for r in rows]


def _setting(db: Session, key: str) -> Optional[str]:
    row = db.query(Setting).filter(Setting.key == key).first()
    return row.value if row else None


def _put_setting(db: Session, key: str, value: str, description: str = "") -> None:
    row = db.query(Setting).filter(Setting.key == key).first()
    if row is None:
        db.add(Setting(key=key, value=value, value_type="json", category="inspection",
                       description=description or "«نظارت و سرکشی»"))
    else:
        row.value = value
        row.updated_at = _now()


def _next_round(db: Session) -> dict:
    from datetime import timezone

    return next_round(datetime.now(timezone.utc), _setting(db, ROUND_LOG_KEY))


def _note_round(db: Session, key: str = ROUND_LOG_KEY) -> None:
    from datetime import timezone

    _put_setting(db, key, record_round(_setting(db, key), datetime.now(timezone.utc)),
                 "ضربانِ دورهای ناظر (برای شمارش‌گرِ «دورِ بعدی»)")
    db.commit()


# ---------------------------------------------------------------------------
# reading
# ---------------------------------------------------------------------------
@router.get("/whoami")
def whoami(request: Request):
    """The supervisor's first call: am I recognised? (without revealing anything)"""
    return {"ok": True, "role": _who(request), "supervisor": is_supervisor(request),
            "supervisor_token_configured": bool(_supervisor_secret()),
            "token_source": ("SUPERVISOR_TOKEN" if (os.environ.get("SUPERVISOR_TOKEN") or "").strip()
                             else "EXTERNAL_TOOL_TOKEN" if _supervisor_secret() else None)}


@router.get("")
@router.get("/")
def list_reports(
    status: Optional[str] = Query(None),
    reopen: Optional[str] = Query(None),
    page: Optional[str] = Query(None),
    kind: Optional[str] = Query(None),
    include_filed: bool = Query(False),
    limit: int = Query(500, ge=1, le=3000),
    db: Session = Depends(get_db),
):
    q = db.query(InspectionReport)
    if status:
        q = q.filter(InspectionReport.status == status)
    elif not include_filed:
        q = q.filter(InspectionReport.status != STATUS_FILED)
    if reopen:
        q = q.filter(InspectionReport.reopen == reopen)
    if page:
        q = q.filter(InspectionReport.page == page)
    if kind:
        q = q.filter(InspectionReport.kind == kind)
    rows = q.order_by(InspectionReport.number.desc()).limit(limit).all()
    counts = {s: 0 for s in (STATUS_OPEN, STATUS_ANSWERED, STATUS_APPROVED, STATUS_FILED)}
    for s, n in db.query(InspectionReport.status, func.count(InspectionReport.id)).group_by(
            InspectionReport.status).all():
        counts[s] = int(n or 0)
    general = db.query(func.count(InspectionReport.id)).filter(
        InspectionReport.kind == KIND_GENERAL, InspectionReport.status != STATUS_FILED).scalar() or 0
    urgent = db.query(func.count(InspectionReport.id)).filter(
        InspectionReport.urgent_at.isnot(None), InspectionReport.urgent_done_at.is_(None),
        InspectionReport.status != STATUS_FILED).scalar() or 0
    return {"ok": True, "reports": _many(db, rows), "counts": counts,
            "general_open": int(general), "urgent_waiting": int(urgent),
            "binder_capacity": BINDER_CAPACITY}


@router.get("/queue")
def queue(request: Request, db: Session = Depends(get_db)):
    """What the supervisor OWES an answer on — the first job of every round.

    A sheet is finished only when the work is DONE WITH PROOF (``fixed`` + its
    after picture) or parked on the owner's decision (``needs-owner``).
    Everything else — partial, not-done, a reply with no outcome — is still owed
    and comes back next round."""
    if is_supervisor(request):
        _note_round(db, FULL_LOG_KEY)
    rows = db.query(InspectionReport).filter(
        InspectionReport.status.in_([STATUS_OPEN, STATUS_ANSWERED])).order_by(InspectionReport.number).all()
    reports = _many(db, rows)
    unanswered = [r for r in reports if r["status"] == STATUS_OPEN]
    unfinished = [r for r in reports if r["status"] == STATUS_ANSWERED
                  and (r.get("glow") or {}).get("tone") not in (OUTCOME_FIXED, OUTCOME_NEEDS_OWNER)]
    return {
        "ok": True,
        "owed": len(unanswered) + len(unfinished),
        "unanswered": len(unanswered),
        "unfinished": len(unfinished),
        "unfinished_numbers": [r["number"] for r in unfinished],
        "waiting_for_owner": len(rows) - len(unanswered) - len(unfinished),
        "to_file": db.query(func.count(InspectionReport.id)).filter(
            InspectionReport.status == STATUS_APPROVED).scalar() or 0,
        "files_to_read": sum(len(r["read_debt"]) for r in reports),
        "files_not_in_drive": sum(1 for r in reports for f in r["files"] if not f["durable"]),
        "reports": reports,
    }


@router.get("/urgent")
def urgent_queue(db: Session = Depends(get_db)):
    """The fast queue, oldest request first — the order the owner pressed them."""
    rows = db.query(InspectionReport).filter(
        InspectionReport.urgent_at.isnot(None), InspectionReport.urgent_done_at.is_(None),
        InspectionReport.status != STATUS_FILED).order_by(InspectionReport.urgent_at).all()
    out = []
    for i, d in enumerate(_many(db, rows)):
        d["position"] = i + 1
        d["claimable"] = _claim_expired(rows[i])
        out.append(d)
    return {"ok": True, "waiting": len(out), "reports": out, "next_round": _next_round(db)}


class ClaimIn(BaseModel):
    by: str = Field("", max_length=80)


@router.post("/urgent/claim")
async def claim_next_urgent(request: Request, db: Session = Depends(get_db)):
    """Take the NEXT urgent sheet, one at a time. Also the round's heartbeat."""
    if not is_supervisor(request):
        raise HTTPException(status_code=403, detail="صفِ فوری را فقط ناظر برمی‌دارد")
    payload = await _body(request, ClaimIn)
    _note_round(db)
    rows = db.query(InspectionReport).filter(
        InspectionReport.urgent_at.isnot(None), InspectionReport.urgent_done_at.is_(None),
        InspectionReport.status != STATUS_FILED).order_by(InspectionReport.urgent_at).all()
    nxt = next((r for r in rows if _claim_expired(r)), None)
    if nxt is None:
        return {"ok": True, "report": None, "waiting": len(rows), "busy": len(rows)}
    nxt.urgent_claimed_at = _now()
    nxt.urgent_claimed_by = _clean(payload.by, 80) or "supervisor"
    db.commit()
    db.refresh(nxt)
    return {"ok": True, "waiting": len(rows), "report": _full(db, nxt)}


@router.get("/schedule")
def schedule(db: Session = Depends(get_db)):
    """The Routines as configured, and what has been MEASURED of them."""
    from datetime import timezone

    full_log = _setting(db, FULL_LOG_KEY)
    try:
        last_full = (json.loads(full_log) or [None])[-1] if full_log else None
    except ValueError:
        last_full = None
    return {
        "ok": True,
        "urgent": {"cron_utc": URGENT_CRON, "next_round": _next_round(db),
                   "prompt": "docs/supervisor/URGENT_PROMPT.md"},
        "full": {"cron_utc": FULL_CRON, "last_seen": last_full,
                 "prompt": "docs/supervisor/PROMPT.md",
                 "next_at": _next_cron(FULL_CRON, datetime.now(timezone.utc))},
        "archive": "docs/supervisor/archive/",
    }


def _next_cron(cron: str, now) -> Optional[str]:
    """Next fire time of a simple ``M H * * DOW`` cron (UTC) — enough for the board."""
    try:
        m, h, _dom, _mon, dow = cron.split()
        minute, hour = int(m), int(h)
        allowed = {int(x) % 7 for x in dow.split(",")} if dow != "*" else set(range(7))
    except Exception:  # noqa: BLE001 - an unusual cron is shown as text only
        return None
    base = now.replace(second=0, microsecond=0)
    for days in range(0, 9):
        cand = (base + timedelta(days=days)).replace(hour=hour, minute=minute)
        if cand > now and (cand.isoweekday() % 7) in allowed:
            return cand.isoformat()
    return None


@router.get("/binders")
def binders(db: Session = Depends(get_db)):
    out = []
    numbers = {r.id: (r.number, r.title) for r in db.query(
        InspectionReport.id, InspectionReport.number, InspectionReport.title).all()}
    for b in db.query(InspectionBinder).order_by(InspectionBinder.number.desc()).all():
        ids = _json_or_none(b.report_ids_json) or []
        out.append({"id": b.id, "number": b.number, "label": b.label, "subtitle": b.subtitle,
                    "opened_at": _iso(b.opened_at), "closed_at": _iso(b.closed_at),
                    "capacity": BINDER_CAPACITY, "count": len(ids),
                    "pages": [{"page": i + 1, "report_id": rid, "number": numbers.get(rid, (0, ""))[0],
                               "title": numbers.get(rid, (0, ""))[1]} for i, rid in enumerate(ids)]})
    return {"ok": True, "binders": out}


# ---------------------------------------------------------------------------
# storage (Google Drive)
# ---------------------------------------------------------------------------
def _usage(db: Session) -> dict:
    def tally(model) -> dict:
        res = {}
        for store, n, b in db.query(model.store, func.count(model.id),
                                    func.coalesce(func.sum(model.byte_size), 0)).group_by(model.store).all():
            res[store or "?"] = {"count": int(n), "bytes": int(b), "label": ifiles.human_size(b)}
        return res

    return {"files": tally(InspectionFile), "shots": tally(InspectionShot), "spool": ifiles.spool_usage(),
            "max_file_mb": ifiles.MAX_MB}


@router.get("/storage")
def storage_status(db: Session = Depends(get_db)):
    return {"ok": True, "drive": gdrive.status(db), "usage": _usage(db)}


class ConnectIn(BaseModel):
    code: str = Field("", max_length=2000)
    refresh_token: str = Field("", max_length=2000)


@router.post("/storage/drive/connect")
async def drive_connect(request: Request, db: Session = Depends(get_db)):
    if is_supervisor(request):
        raise HTTPException(status_code=403, detail="اتصالِ درایو کارِ مالک است")
    body = await _body(request, ConnectIn)
    try:
        if body.code.strip():
            st = gdrive.connect(db, body.code.strip())
        elif body.refresh_token.strip():
            st = gdrive.connect_refresh_token(db, body.refresh_token.strip())
        else:
            raise HTTPException(status_code=422, detail="کدِ تأیید یا refresh token لازم است")
    except gdrive.DriveError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None
    ifiles.kick()  # move everything that was waiting
    return {"ok": True, "drive": st, "usage": _usage(db)}


@router.post("/storage/drive/disconnect")
def drive_disconnect(request: Request, db: Session = Depends(get_db)):
    if is_supervisor(request):
        raise HTTPException(status_code=403, detail="قطعِ درایو کارِ مالک است")
    gdrive.disconnect(db)
    return {"ok": True, "drive": gdrive.status(db), "usage": _usage(db)}


@router.post("/storage/sync")
def storage_sync(db: Session = Depends(get_db)):
    """Push everything waiting to Drive now (also runs on its own every few minutes)."""
    res = ifiles.sync_pending(limit=200)
    return {"ok": True, "result": res, "drive": gdrive.status(db), "usage": _usage(db)}


# ---------------------------------------------------------------------------
# the surface map — «همهٔ صفحات و زیرصفحات و مختصاتِ دقیقِ همه‌جا»
# ---------------------------------------------------------------------------
_ID_SEG = re.compile(r"^(\d+|[0-9a-f]{8}-[0-9a-f-]{27,}|[0-9a-f]{16,}|[A-Za-z0-9_-]{20,})$", re.I)


def route_pattern(path: str) -> str:
    """`/projects/42/files` → `/projects/[id]/files` — one row per screen, not per record."""
    raw = (path or "/").split("?")[0].split("#")[0].rstrip("/") or "/"
    parts = [("[id]" if _ID_SEG.match(p) else p) for p in raw.split("/")]
    return "/".join(parts) or "/"


def _surface_id(route: str, tab: str) -> str:
    return hashlib.sha1(f"{route}|{tab}".encode()).hexdigest()[:24]


class SurfaceIn(BaseModel):
    path: str = Field(..., max_length=800)
    route: str = Field("", max_length=300)
    tab: str = Field("", max_length=120)
    label: str = Field("", max_length=200)
    title: str = Field("", max_length=300)
    viewport: Optional[dict] = None
    doc_size: Optional[dict] = None
    elements: List[dict] = Field(default_factory=list, max_length=3000)


def _element_key(e: dict) -> str:
    return f"{e.get('kind', '')}|{_clean(e.get('label'), 80)}|{_clean(e.get('selector'), 300)}"


@router.post("/surfaces")
async def register_surface(request: Request, db: Session = Depends(get_db)):
    """A browser (the owner's, or the supervisor's headless scan) reports the map
    of the screen it is on. Upserted by route pattern + tab; what appeared or
    disappeared since the previous snapshot is kept, so «چه چیزی تازه اضافه شد»
    is answerable."""
    body = await _body(request, SurfaceIn)
    route = route_pattern(body.route or body.path)
    tab = _clean(body.tab, 120)
    sid = _surface_id(route, tab)
    elements = []
    for e in body.elements[:3000]:
        if not isinstance(e, dict):
            continue
        rect = e.get("rect") if isinstance(e.get("rect"), dict) else {}
        elements.append({
            "kind": _clean(e.get("kind"), 20), "label": _clean(e.get("label"), 160),
            "selector": _clean(e.get("selector"), 400), "section": _clean(e.get("section"), 160),
            "rect": {k: round(float(rect.get(k) or 0), 1) for k in ("x", "y", "w", "h")},
            "href": _clean(e.get("href"), 300),
        })
    counts: dict = {}
    for e in elements:
        counts[e["kind"]] = counts.get(e["kind"], 0) + 1
    row = db.query(InspectionSurface).filter(InspectionSurface.id == sid).first()
    now = _now()
    keys = {_element_key(e) for e in elements}
    if row is None:
        row = InspectionSurface(id=sid, route=route, tab=tab, first_seen=now, visits=0,
                                new_keys_json="[]", removed_keys_json="[]")
        db.add(row)
    else:
        before = {_element_key(e) for e in (_json_or_none(row.elements_json) or [])}
        if before and keys != before:
            row.new_keys_json = json.dumps(sorted(keys - before)[:300], ensure_ascii=False)
            row.removed_keys_json = json.dumps(sorted(before - keys)[:300], ensure_ascii=False)
    row.sample_path = _clean(body.path, 800)
    row.label = _clean(body.label, 200) or row.label or route
    row.title = _clean(body.title, 300)
    row.last_seen = now
    row.visits = int(row.visits or 0) + 1
    row.seen_by = "supervisor-scan" if is_supervisor(request) else "owner-browser"
    row.viewport_json = json.dumps(body.viewport or {}, ensure_ascii=False)
    row.doc_size_json = json.dumps(body.doc_size or {}, ensure_ascii=False)
    row.counts_json = json.dumps(counts, ensure_ascii=False)
    row.elements_json = json.dumps(elements, ensure_ascii=False)
    db.commit()
    return {"ok": True, "id": sid, "route": route, "tab": tab, "elements": len(elements),
            "new": len(_json_or_none(row.new_keys_json) or [])}


def _surface_summary(s: InspectionSurface) -> dict:
    return {"id": s.id, "route": s.route, "tab": s.tab, "label": s.label or s.route, "title": s.title or "",
            "sample_path": s.sample_path or "", "source_file": s.source_file or "",
            "declared": bool(s.declared), "first_seen": _iso(s.first_seen), "last_seen": _iso(s.last_seen),
            "seen_by": s.seen_by or "", "visits": int(s.visits or 0),
            "counts": _json_or_none(s.counts_json) or {},
            "new_count": len(_json_or_none(s.new_keys_json) or []),
            "removed_count": len(_json_or_none(s.removed_keys_json) or []),
            "viewport": _json_or_none(s.viewport_json), "doc_size": _json_or_none(s.doc_size_json)}


@router.get("/surfaces")
def list_surfaces(db: Session = Depends(get_db)):
    rows = db.query(InspectionSurface).order_by(InspectionSurface.route, InspectionSurface.tab).all()
    open_by_page: dict = {}
    for r in db.query(InspectionReport.page, func.count(InspectionReport.id)).filter(
            InspectionReport.status != STATUS_FILED).group_by(InspectionReport.page).all():
        open_by_page[route_pattern(r[0] or "/")] = open_by_page.get(route_pattern(r[0] or "/"), 0) + int(r[1])
    out = []
    for s in rows:
        d = _surface_summary(s)
        d["open_reports"] = open_by_page.get(s.route, 0) if not s.tab else 0
        out.append(d)
    inv = _json_or_none(_setting(db, INVENTORY_KEY) or "")
    return {"ok": True, "surfaces": out,
            "inventory": {k: v for k, v in (inv or {}).items() if k != "pages"} if inv else None}


@router.get("/surfaces/{surface_id}")
def get_surface(surface_id: str, db: Session = Depends(get_db)):
    s = db.query(InspectionSurface).filter(InspectionSurface.id == surface_id).first()
    if s is None:
        raise HTTPException(status_code=404, detail="این صفحه هنوز ثبت نشده")
    d = _surface_summary(s)
    d["elements"] = _json_or_none(s.elements_json) or []
    d["new_keys"] = _json_or_none(s.new_keys_json) or []
    d["removed_keys"] = _json_or_none(s.removed_keys_json) or []
    return {"ok": True, "surface": d}


class InventoryIn(BaseModel):
    generated_at: str = Field("", max_length=60)
    commit: str = Field("", max_length=60)
    pages: List[dict] = Field(default_factory=list, max_length=2000)
    totals: dict = Field(default_factory=dict)


@router.post("/inventory")
async def post_inventory(request: Request, db: Session = Depends(get_db)):
    """The supervisor's code inventory (every page that EXISTS in the source).
    Each declared page gets a surface row, so a page nobody has opened yet is
    listed as «دیده نشده» instead of being invisible."""
    if not is_supervisor(request):
        raise HTTPException(status_code=403, detail="فهرستِ کد را فقط ناظر ثبت می‌کند")
    body = await _body(request, InventoryIn)
    declared = set()
    for p in body.pages:
        route = route_pattern(_clean(p.get("route"), 300) or "/")
        declared.add(route)
        sid = _surface_id(route, "")
        row = db.query(InspectionSurface).filter(InspectionSurface.id == sid).first()
        if row is None:
            row = InspectionSurface(id=sid, route=route, tab="", visits=0, counts_json="{}",
                                    elements_json="[]", new_keys_json="[]", removed_keys_json="[]")
            db.add(row)
        row.declared = True
        row.source_file = _clean(p.get("file"), 300)
        if not row.label or row.label == route:
            row.label = _clean(p.get("label"), 200) or route
    for row in db.query(InspectionSurface).filter(InspectionSurface.tab == "").all():
        if row.route not in declared:
            row.declared = False
    _put_setting(db, INVENTORY_KEY, json.dumps(body.model_dump(), ensure_ascii=False),
                 "فهرستِ کدِ ناظر (صفحه‌ها، مسیرها، دکمه‌ها)")
    db.commit()
    return {"ok": True, "declared": len(declared)}


@router.get("/inventory")
def get_inventory(db: Session = Depends(get_db)):
    return {"ok": True, "inventory": _json_or_none(_setting(db, INVENTORY_KEY) or "")}


# ---------------------------------------------------------------------------
# files — any type, chunked in, read fully, then moved to Drive
# ---------------------------------------------------------------------------
class IntakeStartIn(BaseModel):
    filename: str = Field(..., min_length=1, max_length=260)
    mime: str = Field("", max_length=120)
    size: int = Field(..., ge=1)
    caption: str = Field("", max_length=MAX_TEXT)
    note_id: str = Field("", max_length=40)


@router.post("/{report_id}/intake/start")
async def intake_start(report_id: str, request: Request, db: Session = Depends(get_db)):
    """Open a chunked upload for one file. Pieces are appended in order with
    ``Content-Type: application/octet-stream`` (the house pattern that survives
    Cloudflare — see experiences/)."""
    body = await _body(request, IntakeStartIn)
    r = _report_or_404(db, report_id)
    if r.status == STATUS_FILED:
        raise HTTPException(status_code=422, detail="برگهٔ بایگانی‌شده فایلِ تازه نمی‌گیرد")
    if body.size > ifiles.MAX_BYTES:
        raise HTTPException(status_code=413, detail=(
            f"حجمِ فایل از سقفِ {ifiles.MAX_MB} مگابایت بیشتر است (INSPECTION_MAX_FILE_MB روی Render)"))
    if not ifiles.spool_has_room(body.size):
        raise HTTPException(status_code=507, detail=(
            "فضای موقتِ سرور برای این فایل کافی نیست — فایل‌های قبلی منتظرِ انتقال به درایو‌اند. "
            "اول گوگل درایو را از «فضای ذخیره‌سازی» وصل کن."))
    uid = uuid.uuid4().hex[:24]
    path = str(ifiles.spool_dir() / f"upload-{uid}.part")
    Path(path).write_bytes(b"")
    db.add(InspectionUpload(id=uid, report_id=r.id, filename=ifiles.safe_filename(body.filename),
                            mime=_clean(body.mime, 120) or "application/octet-stream",
                            total_size=int(body.size), received=0, caption=_clean(body.caption),
                            note_id=_clean(body.note_id, 40), spool_path=path, status="uploading"))
    db.commit()
    return {"ok": True, "upload_id": uid, "chunk_size": ifiles.CHUNK_BYTES, "next_offset": 0}


@router.post("/intake/{upload_id}/append")
async def intake_append(upload_id: str, request: Request, offset: int = Query(..., ge=0),
                        db: Session = Depends(get_db)):
    up = db.query(InspectionUpload).filter(InspectionUpload.id == upload_id).first()
    if up is None or up.status != "uploading":
        raise HTTPException(status_code=404, detail="این آپلود باز نیست")
    if offset != int(up.received or 0):
        raise HTTPException(status_code=409, detail={"message": "offset ناهماهنگ", "expected_offset": up.received})
    data = await request.body()
    if not data:
        raise HTTPException(status_code=422, detail="تکهٔ خالی")
    if int(up.received or 0) + len(data) > int(up.total_size or 0):
        raise HTTPException(status_code=413, detail="بیش از اندازهٔ اعلام‌شده")
    with open(up.spool_path, "ab") as fh:
        fh.write(data)
    up.received = int(up.received or 0) + len(data)
    up.updated_at = _now()
    db.commit()
    return {"ok": True, "received": up.received, "next_offset": up.received,
            "complete": up.received >= up.total_size}


@router.post("/intake/{upload_id}/finish")
def intake_finish(upload_id: str, request: Request, db: Session = Depends(get_db)):
    """Extract the text, write it beside the bytes, create the file row and hand
    both to the Drive mover. The response says where the file is right now."""
    up = db.query(InspectionUpload).filter(InspectionUpload.id == upload_id).first()
    if up is None or up.status != "uploading":
        raise HTTPException(status_code=404, detail="این آپلود باز نیست")
    if int(up.received or 0) != int(up.total_size or 0):
        raise HTTPException(status_code=409, detail={"message": "آپلود کامل نشده",
                                                     "expected_offset": up.received})
    r = _report_or_404(db, up.report_id)
    sha, md5, size = ifiles.digests(up.spool_path)
    with open(up.spool_path, "rb") as fh:
        ex = ifiles.extract(fh.read(), up.filename, up.mime)
    fid = uuid.uuid4().hex[:24]
    base = ifiles.spool_dir() / f"file-{fid}"
    final_path = str(base.with_suffix(".bin"))
    os.replace(up.spool_path, final_path)
    text_path = ""
    if ex["text"]:
        text_path = str(base.with_suffix(".txt"))
        Path(text_path).write_text(ex["text"], encoding="utf-8")
    n = db.query(func.count(InspectionFile.id)).filter(InspectionFile.report_id == r.id).scalar() or 0
    row = InspectionFile(
        id=fid, report_id=r.id, note_id=up.note_id or "", uploaded_by=_who(request),
        ref=ifiles.file_ref(r.number, int(n) + 1),
        filename=up.filename, mime=up.mime, byte_size=size, sha256=sha, md5=md5, caption=up.caption or "",
        store="pending", store_note="در صفِ انتقال به گوگل درایو", spool_path=final_path,
        spool_text_path=text_path,
        extract_status=ex["status"], extract_note=ex["note"], text_chars=len(ex["text"] or ""),
        page_count=int(ex.get("page_count") or 0), text_truncated=bool(ex.get("truncated")))
    db.add(row)
    up.status, up.spool_path = "done", ""
    # New material re-opens an answered sheet: the previous answer did not see it.
    if r.status == STATUS_ANSWERED and not is_supervisor(request):
        r.status = STATUS_OPEN
    db.commit()
    db.refresh(row)
    ifiles.kick()
    return {"ok": True, "file": _file_dict(row), "report": _full(db, r)}


@router.delete("/intake/{upload_id}")
def intake_cancel(upload_id: str, db: Session = Depends(get_db)):
    up = db.query(InspectionUpload).filter(InspectionUpload.id == upload_id).first()
    if up is None:
        raise HTTPException(status_code=404, detail="پیدا نشد")
    if up.spool_path:
        Path(up.spool_path).unlink(missing_ok=True)
    up.status, up.spool_path = "cancelled", ""
    db.commit()
    return {"ok": True}


def _file_or_404(db: Session, file_id: str) -> InspectionFile:
    row = db.query(InspectionFile).filter(InspectionFile.id == file_id).first()
    if row is None:
        raise HTTPException(status_code=404, detail="فایل پیدا نشد")
    return row


@router.get("/files/{file_id}")
def file_meta(file_id: str, db: Session = Depends(get_db)):
    return {"ok": True, "file": _file_dict(_file_or_404(db, file_id))}


@router.get("/files/{file_id}/text")
def file_text(file_id: str, request: Request, offset: int = Query(0, ge=0), limit: int = Query(0, ge=0),
              db: Session = Depends(get_db)):
    """Serve the extracted text in slices and RECORD how far the reader got.
    Only a CONTIGUOUS read counts — jumping to the end leaves the middle unread."""
    row = _file_or_404(db, file_id)
    try:
        text = ifiles.load_text(db, row)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"متن از درایو گرفته نشد: {exc}"[:300]) from exc
    total = len(text)
    n = min(limit or ifiles.SLICE_CHARS, ifiles.MAX_SLICE_CHARS)
    part = text[offset:offset + n]
    end = offset + len(part)
    if offset <= int(row.read_chars or 0) < end:
        row.read_chars = end
        row.read_at = _now()
        row.read_by = _who(request)
        db.commit()
        db.refresh(row)
    return {"ok": True, "file_id": row.id, "ref": row.ref, "filename": row.filename or "",
            "caption": row.caption or "", "extract_status": row.extract_status or "",
            "extract_note": row.extract_note or "", "offset": offset, "returned": len(part), "text": part,
            "text_chars": total, "has_more": end < total, "next_offset": end if end < total else None,
            "read_chars": int(row.read_chars or 0),
            "fully_read": int(row.read_chars or 0) >= total and total > 0,
            "page_count": int(row.page_count or 0)}


@router.post("/files/{file_id}/extract")
def extract_file(file_id: str, request: Request, db: Session = Depends(get_db)):
    """(Re)read one attachment with today's readers — and for audio/video (or an
    archive holding some; legacy «media» rows too) produce the FULL transcript
    (services/inspection_media). The supervisor's `pull` calls it for every file
    still `pending`/`media`. New text is a new reading duty: the counter restarts."""
    from ...services import inspection_media as imedia

    row = _file_or_404(db, file_id)
    r = _report_or_404(db, row.report_id)
    try:
        data = b"".join(ifiles.iter_raw(db, row))
    except FileNotFoundError as exc:
        raise HTTPException(status_code=410, detail=str(exc)[:300]) from exc
    if not data:
        raise HTTPException(status_code=410, detail="بایت‌های این فایل در دسترس نیست")
    name, mime = row.filename or "", row.mime or ""
    ex = imedia.finish_extraction(ifiles.extract(data, name, mime), data, name, mime)
    text = ex["text"] or ""
    try:
        old = ifiles.load_text(db, row)
    except Exception:  # noqa: BLE001 - unreadable old text ⇒ treat as changed
        old = None
    if text != old:
        try:
            ifiles.replace_text(db, row, text, int(r.number or 0))
        except Exception as exc:  # noqa: BLE001
            db.rollback()
            raise HTTPException(status_code=502, detail=f"متنِ تازه ذخیره نشد: {exc}"[:300]) from exc
        row.read_chars, row.read_at = 0, None
    row.extract_status, row.extract_note = ex["status"], ex["note"]
    row.text_chars, row.text_truncated = len(text), bool(ex.get("truncated"))
    row.page_count = int(ex.get("page_count") or 0)
    db.commit()
    db.refresh(row)
    return {"ok": True, "success": True, "file": _file_dict(row)}


def _disposition(kind: str, filename: str) -> str:
    from urllib.parse import quote

    ascii_name = re.sub(r'[^A-Za-z0-9._-]+', "_", filename or "file") or "file"
    return f"{kind}; filename=\"{ascii_name}\"; filename*=UTF-8''{quote(filename or 'file')}"


@router.get("/files/{file_id}/raw")
def file_raw(file_id: str, request: Request, db: Session = Depends(get_db)):
    """The bytes themselves. Fetching this is what «looked at it» means for a
    file with no text, so it is recorded."""
    row = _file_or_404(db, file_id)
    try:
        stream = ifiles.iter_raw(db, row)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=410, detail=str(exc)[:300]) from exc
    row.viewed_at = _now()
    if not row.read_by:
        row.read_by = _who(request)
    db.commit()
    disp = "inline" if (row.mime or "").startswith(("image/", "video/", "audio/")) or row.mime == "application/pdf" \
        else "attachment"
    return StreamingResponse(stream, media_type=row.mime or "application/octet-stream",
                             headers={"Content-Disposition": _disposition(disp, row.filename),
                                      "Cache-Control": "private, max-age=300"})


@router.delete("/files/{file_id}")
def delete_file(file_id: str, request: Request, db: Session = Depends(get_db)):
    """Only the OWNER removes a sample. The Drive copy is MOVED to the project's
    «سطلِ حذف‌شده» folder — quarantine, not deletion."""
    if is_supervisor(request):
        raise HTTPException(status_code=403, detail="ناظر فایلِ نمونه را حذف نمی‌کند — این کارِ مالک است")
    row = _file_or_404(db, file_id)
    _quarantine_file(db, row)
    db.delete(row)
    db.commit()
    return {"ok": True}


def _quarantine_file(db: Session, row) -> None:
    for pid in (row.drive_id, getattr(row, "text_drive_id", "")):
        if pid:
            try:
                gdrive.move_to_trash_folder(db, pid)
            except Exception:  # noqa: BLE001 - the row goes; the Drive copy simply stays where it was
                pass
    for p in (row.spool_path, getattr(row, "spool_text_path", "")):
        if p:
            Path(p).unlink(missing_ok=True)


@router.get("/shots/{shot_id}")
def get_shot(shot_id: str, db: Session = Depends(get_db)):
    s = db.query(InspectionShot).filter(InspectionShot.id == shot_id).first()
    if s is None:
        raise HTTPException(status_code=404, detail="تصویر پیدا نشد")
    if s.spool_path and Path(s.spool_path).exists():
        data = Path(s.spool_path).read_bytes()
    elif s.drive_id:
        try:
            data = gdrive.download_bytes(db, s.drive_id)
        except gdrive.DriveError as exc:
            raise HTTPException(status_code=410, detail=str(exc)) from exc
    else:
        raise HTTPException(status_code=410, detail=s.store_note or "تصویر در دسترس نیست")
    return Response(content=data, media_type=s.mime or "image/jpeg",
                    headers={"Cache-Control": "private, max-age=86400"})


# ---------------------------------------------------------------------------
# writing
# ---------------------------------------------------------------------------
class SpotIn(BaseModel):
    page: str = Field("", max_length=300)
    page_label: str = Field("", max_length=200)
    section_id: str = Field("", max_length=160)
    section_label: str = Field("", max_length=200)
    reopen: str = Field("", max_length=400)
    url: str = Field("", max_length=800)
    dom_path: str = Field("", max_length=400)
    covered_text: str = Field("", max_length=MAX_TEXT)
    rect: Optional[dict] = None
    viewport: Optional[dict] = None
    geometry: Optional[dict] = None


class CreateIn(BaseModel):
    text: str = Field(..., min_length=1, max_length=MAX_TEXT)
    kind: str = Field(KIND_SPOT, max_length=12)
    spot: SpotIn = Field(default_factory=SpotIn)
    shot: Optional[str] = None
    urgent: bool = False


@router.post("")
@router.post("/")
async def create_report(request: Request, db: Session = Depends(get_db)):
    payload = await _body(request, CreateIn)
    text = _clean(payload.text)
    if not text:
        raise HTTPException(status_code=422, detail="متنِ گزارش خالی است")
    active = db.query(func.count(InspectionReport.id)).filter(InspectionReport.status != STATUS_FILED).scalar() or 0
    if active >= MAX_ACTIVE:
        raise HTTPException(status_code=422, detail=f"سقفِ {MAX_ACTIVE} برگهٔ باز پر است — اول چند تا را تأیید و بایگانی کن")
    top = db.query(func.max(InspectionReport.number)).scalar() or 0
    kind = KIND_GENERAL if payload.kind == KIND_GENERAL else KIND_SPOT
    s = payload.spot
    if kind == KIND_GENERAL and not s.page:
        s = SpotIn(page="/inspection", page_label="درخواستِ عمومی", section_id="general",
                   section_label="بدونِ محلِ مشخص", reopen="/inspection#general", url="/inspection")
    rid = uuid.uuid4().hex[:24]
    nid = uuid.uuid4().hex[:16]
    r = InspectionReport(
        id=rid, number=int(top) + 1, status=STATUS_OPEN, kind=kind, title=_headline(text),
        created_by=_who(request),
        page=_clean(s.page, 300), page_label=_clean(s.page_label, 200),
        section_id=_clean(s.section_id, 160), section_label=_clean(s.section_label, 200),
        reopen=_clean(s.reopen, 400), url=_clean(s.url, 800), dom_path=_clean(s.dom_path, 400),
        covered_text=_clean(s.covered_text),
        rect_json=json.dumps(s.rect or {}, ensure_ascii=False),
        viewport_json=json.dumps(s.viewport or {}, ensure_ascii=False),
        geometry_json=json.dumps(s.geometry, ensure_ascii=False) if s.geometry else "",
        notes_json="[]", deps_json="[]")
    db.add(r)
    db.flush()
    shot_id = _store_shot(db, r, nid, "before", payload.shot)
    r.notes_json = json.dumps([{"id": nid, "by": "owner", "at": _iso(_now()), "text": text,
                                "author": _who(request), "shot_id": shot_id}], ensure_ascii=False)
    if payload.urgent and not is_supervisor(request):
        r.urgent_at = _now()
    db.commit()
    db.refresh(r)
    if shot_id:
        ifiles.kick()
    return {"ok": True, "report": _full(db, r)}


class NoteIn(BaseModel):
    text: str = Field(..., min_length=1, max_length=MAX_TEXT)
    shot: Optional[str] = None
    outcome: Optional[str] = Field(None, max_length=16)
    after_shot: Optional[str] = None
    commits: List[str] = Field(default_factory=list, max_length=20)
    dependencies: List[dict] = Field(default_factory=list, max_length=60)
    spot: Optional[SpotIn] = None
    file_ids: List[str] = Field(default_factory=list, max_length=40)


@router.post("/{report_id}/notes")
async def add_note(report_id: str, request: Request, db: Session = Depends(get_db)):
    """A follow-up under a sheet — from the owner (re-opens it, turns it amber
    again) or from the supervisor (an answer with an outcome)."""
    payload = await _body(request, NoteIn)
    r = _report_or_404(db, report_id)
    if r.status == STATUS_FILED:
        raise HTTPException(status_code=422, detail="برگهٔ بایگانی‌شده بسته است — برای موضوعِ تازه برگهٔ تازه بساز")
    text = _clean(payload.text)
    if not text:
        raise HTTPException(status_code=422, detail="متنِ یادداشت خالی است")
    reviewer = is_supervisor(request)
    if payload.outcome is not None:
        if not reviewer:
            raise HTTPException(status_code=422, detail="«نتیجه» را فقط ناظر ثبت می‌کند")
        if payload.outcome not in OUTCOMES:
            raise HTTPException(status_code=422, detail="نتیجهٔ نامعتبر")
        if payload.outcome == OUTCOME_FIXED and not _split_data_url(payload.after_shot):
            raise HTTPException(status_code=422, detail=(
                "«درست شد» بدونِ تصویرِ بعدش پذیرفته نمی‌شود — یا تصویر بفرست یا نتیجه را "
                "«نیمه‌کاره»/«درست نشد» بگذار"))
    if reviewer:
        debt = file_read_debt(db.query(InspectionFile).filter(InspectionFile.report_id == r.id).all())
        if debt:
            parts = []
            for d in debt[:6]:
                if d["reason"] == "text":
                    parts.append(f"«{d['filename']}»: {d['remaining']} نویسه از {d['text_chars']} خوانده نشده")
                elif d["reason"] == "truncated":
                    parts.append(f"«{d['filename']}»: متنش بریده شده بود، خودِ فایل را هم باز کن")
                else:
                    parts.append(f"«{d['filename']}»: هنوز باز نشده")
            raise HTTPException(status_code=422, detail=(
                "پیش از پاسخ باید فایل‌های پیوستِ برگه را کامل بخوانی — " + "؛ ".join(parts)
                + ". متن را از /api/inspection/files/{id}/text تکه‌تکه بگیر (و برای فایلِ بی‌متن، /raw را باز کن)"))

    nid = uuid.uuid4().hex[:16]
    shot_id = _store_shot(db, r, nid, "before", payload.shot)
    after_id = _store_shot(db, r, nid, "after", payload.after_shot) if reviewer else None
    note = {"id": nid, "by": "reviewer" if reviewer else "owner", "at": _iso(_now()), "text": text,
            "author": _who(request), "shot_id": shot_id}
    if payload.spot is not None:
        sp = payload.spot
        note["spot"] = {
            "page": _clean(sp.page, 300), "page_label": _clean(sp.page_label, 200),
            "section_id": _clean(sp.section_id, 160), "section_label": _clean(sp.section_label, 200),
            "reopen": _clean(sp.reopen, 400), "url": _clean(sp.url, 800), "dom_path": _clean(sp.dom_path, 400),
            "covered_text": _clean(sp.covered_text, MAX_TEXT),
            "rect": sp.rect if isinstance(sp.rect, dict) else None,
            "viewport": sp.viewport if isinstance(sp.viewport, dict) else None,
            "geometry": sp.geometry if isinstance(sp.geometry, dict) else None,
        }
    if reviewer:
        note["outcome"] = payload.outcome
        note["after_shot_id"] = after_id
        note["commits"] = [_clean(c, 60) for c in (payload.commits or [])][:20]
    notes = _notes(r)
    notes.append(note)
    r.notes_json = json.dumps(notes, ensure_ascii=False)
    # claim the files uploaded FOR this note (only unclaimed files of this sheet)
    wanted = [_clean(x, 40) for x in (payload.file_ids or []) if _clean(x, 40)][:40]
    if wanted:
        for fr in db.query(InspectionFile).filter(InspectionFile.id.in_(wanted),
                                                  InspectionFile.report_id == r.id).all():
            if not (fr.note_id or ""):
                fr.note_id = nid
    if reviewer and payload.dependencies:
        deps = _deps(r)
        for d in payload.dependencies[:60]:
            if isinstance(d, dict):
                deps.append({"name": _clean(d.get("name"), 160), "status": _clean(d.get("status"), 20),
                             "note": _clean(d.get("note"), 300)})
        r.deps_json = json.dumps(deps, ensure_ascii=False)
    if reviewer:
        if r.status in (STATUS_OPEN, STATUS_ANSWERED):
            r.status = STATUS_ANSWERED
        if r.urgent_at is not None and r.urgent_done_at is None:
            r.urgent_done_at = _now()
            r.urgent_claimed_at = None
            r.urgent_claimed_by = ""
    else:
        if r.urgent_done_at is not None:
            r.urgent_done_at = None   # asking again: back in the fast queue at its ORIGINAL place
        if r.status in (STATUS_ANSWERED, STATUS_APPROVED):
            r.status = STATUS_OPEN    # the owner writing again means it is not settled
    db.commit()
    db.refresh(r)
    if shot_id or after_id:
        ifiles.kick()
    return {"ok": True, "report": _full(db, r)}


class EditNoteIn(BaseModel):
    text: str = Field(..., min_length=1, max_length=MAX_TEXT)


@router.patch("/{report_id}/notes/{note_id}")
async def edit_note(report_id: str, note_id: str, request: Request, db: Session = Depends(get_db)):
    """Correct what a note SAYS, in place — the original is kept on the note."""
    payload = await _body(request, EditNoteIn)
    r = _report_or_404(db, report_id)
    if r.status == STATUS_FILED:
        raise HTTPException(status_code=422, detail="برگهٔ بایگانی‌شده ویرایش نمی‌شود")
    text = _clean(payload.text)
    if not text:
        raise HTTPException(status_code=422, detail="متنِ یادداشت خالی است")
    notes = _notes(r)
    target = next((n for n in notes if n.get("id") == note_id), None)
    if target is None:
        raise HTTPException(status_code=404, detail="یادداشت پیدا نشد")
    mine = "reviewer" if is_supervisor(request) else "owner"
    if (target.get("by") or "owner") != mine:
        raise HTTPException(status_code=403, detail="یادداشتِ طرفِ مقابل ویرایش نمی‌شود — یادداشتِ تازه بنویس")
    if not target.get("original_text"):
        target["original_text"] = target.get("text", "")
    target["text"] = text
    target["edited_at"] = _iso(_now())
    if notes and notes[0].get("id") == note_id:
        r.title = _headline(text)
    r.notes_json = json.dumps(notes, ensure_ascii=False)
    if mine == "owner" and r.status == STATUS_ANSWERED:
        r.status = STATUS_OPEN
    db.commit()
    db.refresh(r)
    return {"ok": True, "report": _full(db, r)}


class StatusIn(BaseModel):
    status: str = Field(..., max_length=12)


@router.post("/{report_id}/status")
async def set_status(report_id: str, request: Request, db: Session = Depends(get_db)):
    """The owner's tick (and un-tick). The supervisor is refused here."""
    payload = await _body(request, StatusIn)
    want = (payload.status or "").strip()
    if want not in (STATUS_OPEN, STATUS_APPROVED):
        raise HTTPException(status_code=422, detail="فقط «open» یا «approved» پذیرفته می‌شود")
    if is_supervisor(request):
        raise HTTPException(status_code=403, detail="تیکِ تأیید فقط دستِ مالک است — ناظر نمی‌تواند کارِ خودش را تأیید کند")
    r = _report_or_404(db, report_id)
    if r.status == STATUS_FILED:
        raise HTTPException(status_code=422, detail="برگهٔ بایگانی‌شده بسته است")
    r.status = want
    db.commit()
    db.refresh(r)
    return {"ok": True, "report": _full(db, r)}


@router.post("/{report_id}/urgent")
def mark_urgent(report_id: str, request: Request, db: Session = Depends(get_db)):
    """The owner asks for this one NOW. Re-pressing keeps the original place."""
    if is_supervisor(request):
        raise HTTPException(status_code=403, detail="درخواستِ فوری کارِ مالک است، نه ناظر")
    r = _report_or_404(db, report_id)
    if r.status == STATUS_FILED:
        raise HTTPException(status_code=422, detail="برگهٔ بایگانی‌شده نوبتِ فوری نمی‌گیرد")
    if r.urgent_at is None or r.urgent_done_at is not None:
        r.urgent_at = _now()
        r.urgent_done_at = None
        r.urgent_claimed_at = None
        r.urgent_claimed_by = ""
        db.commit()
        db.refresh(r)
    ahead = db.query(func.count(InspectionReport.id)).filter(
        InspectionReport.urgent_at.isnot(None), InspectionReport.urgent_done_at.is_(None),
        InspectionReport.status != STATUS_FILED, InspectionReport.urgent_at < r.urgent_at).scalar() or 0
    return {"ok": True, "position": int(ahead) + 1, "next_round": _next_round(db), "report": _full(db, r)}


@router.delete("/{report_id}/urgent")
def unmark_urgent(report_id: str, request: Request, db: Session = Depends(get_db)):
    if is_supervisor(request):
        raise HTTPException(status_code=403, detail="لغوِ فوری کارِ مالک است")
    r = _report_or_404(db, report_id)
    r.urgent_at = None
    r.urgent_claimed_at = None
    r.urgent_claimed_by = ""
    r.urgent_done_at = None
    db.commit()
    db.refresh(r)
    return {"ok": True, "report": _full(db, r)}


@router.post("/file")
def file_approved(db: Session = Depends(get_db)):
    """Move every ticked (blue) sheet into a binder. Run by EVERY supervisor
    round — periodic and urgent — so the owner's page stays clean."""
    rows = db.query(InspectionReport).filter(InspectionReport.status == STATUS_APPROVED).order_by(
        InspectionReport.number).all()
    if not rows:
        return {"ok": True, "filed": 0, "pages": []}
    binders_ = db.query(InspectionBinder).order_by(InspectionBinder.number).all()
    current = next((b for b in reversed(binders_) if b.closed_at is None), None)
    touched = []
    for r in rows:
        ids = (_json_or_none(current.report_ids_json) or []) if current else []
        if current is None or len(ids) >= BINDER_CAPACITY:
            if current is not None:
                current.closed_at = _now()
            n = max((b.number for b in binders_), default=0) + 1
            current = InspectionBinder(id=uuid.uuid4().hex[:24], number=n, label=f"زونکنِ نظارت — شمارهٔ {n}",
                                       subtitle="برگه‌های تأییدشدهٔ نظارت و سرکشی", report_ids_json="[]")
            db.add(current)
            binders_ = list(binders_) + [current]
            ids = []
        ids.append(r.id)
        current.report_ids_json = json.dumps(ids, ensure_ascii=False)
        r.status = STATUS_FILED
        r.binder_id = current.id
        r.binder_number = current.number
        r.binder_page = len(ids)
        r.filed_at = _now()
        touched.append({"number": r.number, "binder": current.number, "page": len(ids)})
    db.commit()
    return {"ok": True, "filed": len(touched), "pages": touched}


# NOTE — every literal path above this line must stay ABOVE `/{report_id}`.
@router.get("/{report_id}")
def get_report(report_id: str, db: Session = Depends(get_db)):
    return {"ok": True, "report": _full(db, _report_or_404(db, report_id))}


@router.delete("/{report_id}")
def delete_report(report_id: str, request: Request, db: Session = Depends(get_db)):
    """Owner only. Rows go; Drive copies are QUARANTINED in «سطلِ حذف‌شده»."""
    if is_supervisor(request):
        raise HTTPException(status_code=403, detail="ناظر نمی‌تواند برگه حذف کند")
    r = _report_or_404(db, report_id)
    for s in db.query(InspectionShot).filter(InspectionShot.report_id == report_id).all():
        if s.drive_id:
            try:
                gdrive.move_to_trash_folder(db, s.drive_id)
            except Exception:  # noqa: BLE001
                pass
        if s.spool_path:
            Path(s.spool_path).unlink(missing_ok=True)
        db.delete(s)
    removed = 0
    for f in db.query(InspectionFile).filter(InspectionFile.report_id == report_id).all():
        _quarantine_file(db, f)
        db.delete(f)
        removed += 1
    db.delete(r)
    db.commit()
    return {"ok": True, "files_removed": removed}
