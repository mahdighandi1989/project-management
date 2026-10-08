"""«نظارت و سرکشی» — the owner's inspection sheets over this app's own screens.

Modelled on the inspection systems of the owner's two sibling projects
(ALLIN1 and Detective-1, read-only references). The loop is the same:

    owner draws a box on any screen (or files a general request)
      →  a sheet is filed with the way BACK to it (route + section + selector +
         fractions of the anchor element + document pixels + screenshot)
      →  the scheduled supervisor (a Claude Code Routine) reads the queue, does
         the work, answers UNDER the sheet with an outcome, its dependency walk
         and — for a claimed fix — an after-picture
      →  the owner looks and ticks it (blue)
      →  the next round (periodic OR urgent) files it into a binder.

THE RULES THIS SHAPE ENFORCES (each paid for in a sibling project):

  1. ``status`` is where the conversation is; ``outcome`` is what actually
     happened. The colour of the badge is derived from the outcome, never from
     the fact that somebody replied.
  2. ``outcome='fixed'`` needs the after-picture that proves it (API guard).
  3. Only the owner ticks. The supervisor's token is refused by the approve,
     delete and urgent endpoints.
  4. Attached files must be READ in full before the supervisor may answer.

WHAT IS DIFFERENT HERE — THE OWNER'S STORAGE RULE (2026-10-08)
-------------------------------------------------------------
«بعد از تمام شدن کار باید فایل‌ها در پوشهٔ این پروژه [در گوگل درایو] ثبت بشه با
رفرنس مشخص و در فولدر و جای مشخص و لینک شه … و در بک‌اند چیزی رو نگه ندار».

So no bytes live in these rows. A file or screenshot is SPOOLED to disk only
while it is in flight; once Drive confirms the upload (same MD5) the local copy
is deleted and the row keeps only the reference: ``drive_id``, ``drive_link``,
``drive_path`` and a human ``ref`` like ``PM-INS-0007-F03``. The extracted text
the supervisor reads goes to Drive too, as a sidecar ``.txt`` next to the file.
``store`` says where the bytes are RIGHT NOW and is never silent:

    drive    — durable, in the project folder, local copy gone
    pending  — waiting on disk for Drive (not connected yet, or a retry)
    failed   — the last attempt failed; ``store_note`` says why; retried later
"""

from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text

from ..core.database import Base

# ---------------------------------------------------------------------------
# The life of a sheet — where it is in the conversation, NOT how it went.
# ---------------------------------------------------------------------------
STATUS_OPEN = "open"            # ثبت شد، منتظرِ ناظر
STATUS_ANSWERED = "answered"    # ناظر زیرش نوشت (هر جوابی، حتی «نشد»)
STATUS_APPROVED = "approved"    # مالک تیک زد
STATUS_FILED = "filed"          # بایگانی شد
STATUSES = (STATUS_OPEN, STATUS_ANSWERED, STATUS_APPROVED, STATUS_FILED)

STATUS_LABEL = {
    STATUS_OPEN: "در انتظارِ ناظر",
    STATUS_ANSWERED: "ناظر پاسخ داد",
    STATUS_APPROVED: "تأییدِ مالک",
    STATUS_FILED: "بایگانی‌شده",
}

# ---------------------------------------------------------------------------
# What ACTUALLY happened — the supervisor's verdict on its own work. There is
# deliberately NO value meaning «I think I fixed it».
# ---------------------------------------------------------------------------
OUTCOME_FIXED = "fixed"
OUTCOME_PARTIAL = "partial"
OUTCOME_NEEDS_OWNER = "needs-owner"
OUTCOME_NOT_DONE = "not-done"
OUTCOMES = (OUTCOME_FIXED, OUTCOME_PARTIAL, OUTCOME_NEEDS_OWNER, OUTCOME_NOT_DONE)

OUTCOME_LABEL = {
    OUTCOME_FIXED: "✓ درست شد",
    OUTCOME_PARTIAL: "◑ نیمه‌کاره",
    OUTCOME_NEEDS_OWNER: "؟ منتظرِ انتخابِ مالک",
    OUTCOME_NOT_DONE: "✗ درست نشد",
}

#: The two kinds of sheet. A general request points at no place on screen.
KIND_SPOT = "spot"
KIND_GENERAL = "general"

#: How many sheets one binder holds before a new one is started.
BINDER_CAPACITY = 40

#: How long a claim on an urgent sheet is honoured before another run may take it.
URGENT_CLAIM_TTL_S = 45 * 60


class InspectionReport(Base):
    """One sheet: where the owner was, what they saw, and the conversation on it."""

    __tablename__ = "inspection_reports"

    id = Column(String(40), primary_key=True)
    #: Sequential, so the owner and the supervisor can say «گزارشِ ۷».
    number = Column(Integer, index=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    status = Column(String(12), index=True, default=STATUS_OPEN, nullable=False)
    #: `spot` (a box on a screen) or `general` (a request with no place yet).
    kind = Column(String(12), default=KIND_SPOT)
    title = Column(String(200), default="")
    created_by = Column(String(80), default="")

    # --- WHERE IN THE INTERFACE -------------------------------------------
    page = Column(String(300), default="", index=True)
    page_label = Column(String(200), default="")
    section_id = Column(String(160), default="")
    section_label = Column(String(200), default="")
    #: THE load-bearing field: one string that puts the supervisor back here.
    reopen = Column(String(400), default="", index=True)
    #: The full URL (with query string) the owner was on — tabs live in queries.
    url = Column(String(800), default="")
    dom_path = Column(String(400), default="")
    covered_text = Column(Text, default="")
    rect_json = Column(Text, default="")
    viewport_json = Column(Text, default="")
    #: The precise record: document pixels, scroll, dpr, and the anchor
    #: element's verified selector with the box as FRACTIONS of it.
    geometry_json = Column(Text, default="")

    #: The conversation: a JSON list of notes.
    notes_json = Column(Text, default="[]")
    #: What the supervisor found this sheet depends on.
    deps_json = Column(Text, default="[]")

    # --- «همین الان برو سراغش» — the fast queue -------------------------
    urgent_at = Column(DateTime, nullable=True, index=True)
    urgent_claimed_at = Column(DateTime, nullable=True)
    urgent_claimed_by = Column(String(80), default="")
    urgent_done_at = Column(DateTime, nullable=True)

    #: Set when filed.
    binder_id = Column(String(40), default="")
    binder_number = Column(Integer, default=0)
    binder_page = Column(Integer, default=0)
    filed_at = Column(DateTime, nullable=True)


class InspectionShot(Base):
    """A screenshot belonging to one note. Metadata only — bytes go to Drive."""

    __tablename__ = "inspection_shots"

    id = Column(String(40), primary_key=True)
    report_id = Column(String(40), index=True, nullable=False)
    note_id = Column(String(40), index=True, default="")
    #: `before` = what the owner saw · `after` = the supervisor's proof of a fix.
    kind = Column(String(10), default="before")
    mime = Column(String(40), default="image/jpeg")
    byte_size = Column(Integer, default=0)
    md5 = Column(String(32), default="")
    ref = Column(String(40), default="")
    created_at = Column(DateTime, default=datetime.utcnow)

    store = Column(String(12), default="pending")
    store_note = Column(Text, default="")
    drive_id = Column(String(120), default="")
    drive_link = Column(String(400), default="")
    drive_path = Column(String(400), default="")
    #: Only while in flight; emptied the moment Drive has it.
    spool_path = Column(String(400), default="")


class InspectionFile(Base):
    """ANY file attached to a sheet, the reference to where it lives, and the
    proof the supervisor read it."""

    __tablename__ = "inspection_files"

    id = Column(String(40), primary_key=True)
    report_id = Column(String(40), index=True, nullable=False)
    note_id = Column(String(40), index=True, default="")
    uploaded_by = Column(String(80), default="")
    created_at = Column(DateTime, default=datetime.utcnow)
    #: Human reference written on the sheet and in the Drive filename.
    ref = Column(String(40), default="", index=True)

    filename = Column(String(260), default="")
    mime = Column(String(120), default="application/octet-stream")
    byte_size = Column(Integer, default=0)
    sha256 = Column(String(64), default="")
    md5 = Column(String(32), default="")
    caption = Column(Text, default="")

    # --- where the bytes are ------------------------------------------------
    store = Column(String(12), default="pending")
    store_note = Column(Text, default="")
    drive_id = Column(String(120), default="")
    drive_link = Column(String(400), default="")
    drive_path = Column(String(400), default="")
    drive_folder_link = Column(String(400), default="")
    #: The extracted text lives in Drive too, as a sidecar next to the file.
    text_drive_id = Column(String(120), default="")
    text_drive_link = Column(String(400), default="")
    #: Only while in flight; emptied the moment Drive has them.
    spool_path = Column(String(400), default="")
    spool_text_path = Column(String(400), default="")
    pushed_at = Column(DateTime, nullable=True)
    push_attempts = Column(Integer, default=0)

    # --- what the supervisor must read -------------------------------------
    #: ok · empty · unsupported · failed · image · pending — never merged
    extract_status = Column(String(12), default="pending")
    extract_note = Column(Text, default="")
    text_chars = Column(Integer, default=0)
    page_count = Column(Integer, default=0)
    text_truncated = Column(Boolean, default=False)

    # --- the proof it was read ---------------------------------------------
    read_chars = Column(Integer, default=0)
    read_at = Column(DateTime, nullable=True)
    read_by = Column(String(80), default="")
    viewed_at = Column(DateTime, nullable=True)


class InspectionUpload(Base):
    """A chunked upload in flight (octet-stream appends, resumable by offset).

    Exists only between «start» and «finish»; the bytes are on the spool disk
    and become an `InspectionFile` (and then a Drive file) at «finish»."""

    __tablename__ = "inspection_uploads"

    id = Column(String(40), primary_key=True)
    report_id = Column(String(40), index=True, nullable=False)
    filename = Column(String(260), default="")
    mime = Column(String(120), default="application/octet-stream")
    total_size = Column(Integer, default=0)
    received = Column(Integer, default=0)
    caption = Column(Text, default="")
    note_id = Column(String(40), default="")
    spool_path = Column(String(400), default="")
    status = Column(String(12), default="uploading")  # uploading · done · cancelled
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class InspectionBinder(Base):
    """A binder in the archive: where ticked sheets go to rest."""

    __tablename__ = "inspection_binders"

    id = Column(String(40), primary_key=True)
    number = Column(Integer, nullable=False)
    label = Column(String(120), default="")
    subtitle = Column(String(240), default="")
    opened_at = Column(DateTime, default=datetime.utcnow)
    closed_at = Column(DateTime, nullable=True)
    report_ids_json = Column(Text, default="[]")


class InspectionSurface(Base):
    """«بتونه همهٔ صفحات و زیرصفحات و مختصاتِ دقیقِ همه‌جا رو بشناسه و ثبت کنه».

    One row per screen (route pattern + tab), holding the LATEST measured map of
    it: headings, tabs, sections, buttons, inputs and links, each with a verified
    selector and its document rectangle. Rows are written by two observers —
    the owner's own browser as they walk the app, and the supervisor's headless
    scan each full round — so a page added tomorrow appears here the first time
    anyone opens it, without anybody editing a list.

    ``declared`` comes from the code inventory (pages that exist in the source),
    so a page that exists but was never seen is visible too, as «دیده نشده».
    """

    __tablename__ = "inspection_surfaces"

    id = Column(String(64), primary_key=True)
    route = Column(String(300), index=True, default="")
    tab = Column(String(120), default="")
    sample_path = Column(String(800), default="")
    label = Column(String(200), default="")
    title = Column(String(300), default="")
    source_file = Column(String(300), default="")
    declared = Column(Boolean, default=False)
    first_seen = Column(DateTime, nullable=True)
    last_seen = Column(DateTime, nullable=True)
    seen_by = Column(String(40), default="")
    visits = Column(Integer, default=0)
    viewport_json = Column(Text, default="")
    doc_size_json = Column(Text, default="")
    counts_json = Column(Text, default="{}")
    elements_json = Column(Text, default="[]")
    #: Element keys that appeared in the latest snapshot and were not in the one
    #: before — «چه چیزی تازه اضافه شده».
    new_keys_json = Column(Text, default="[]")
    removed_keys_json = Column(Text, default="[]")


# ---------------------------------------------------------------------------
# Reading duty
# ---------------------------------------------------------------------------
READABLE = ("ok",)
EXTRACT_LABEL = {
    "ok": "متن استخراج شد — ناظر باید کاملش را بخواند",
    "empty": "فایل باز شد ولی متنی نداشت",
    "unsupported": "برای این نوع، استخراجِ متن نداریم — ناظر باید خودِ فایل را باز کند",
    "failed": "استخراج شکست خورد — دلیلش ثبت شده",
    "image": "تصویر است — ناظر باید نگاهش کند (متنی برای خواندن ندارد)",
    "media": "صوت/ویدئو است — ناظر باید خودِ فایل را باز کند",
    "pending": "هنوز استخراج نشده",
}


def file_read_debt(files: list) -> list:
    """Which attached files a supervisor still owes a read on, and how much.

    An empty list is the only thing that lets a supervisor answer the sheet.
    Deliberately NOT «read_chars > 0»: a reviewer that fetched the first slice
    of a 90-page sample and stopped has not read it."""
    debt = []
    for f in files or []:
        status = str(getattr(f, "extract_status", "") or "")
        name = str(getattr(f, "filename", "") or "?")
        fid = getattr(f, "id", "")
        if status in READABLE:
            total = int(getattr(f, "text_chars", 0) or 0)
            got = int(getattr(f, "read_chars", 0) or 0)
            if total and got < total:
                debt.append({"file_id": fid, "filename": name, "reason": "text",
                             "read_chars": got, "text_chars": total, "remaining": total - got})
            elif getattr(f, "text_truncated", False) and getattr(f, "viewed_at", None) is None:
                debt.append({"file_id": fid, "filename": name, "reason": "truncated",
                             "read_chars": got, "text_chars": total, "remaining": 1})
        elif status in ("image", "unsupported", "media", "failed"):
            if getattr(f, "viewed_at", None) is None:
                debt.append({"file_id": fid, "filename": name, "reason": "unopened",
                             "read_chars": 0, "text_chars": 0, "remaining": 1})
    return debt


def sheet_glow(status: str, notes: list) -> dict:
    """THE BADGE THE OWNER SEES — derived, never stored.

    Green only when the supervisor says it is fixed AND attached the picture
    that proves it. ``approved`` (the owner's own tick) wins over everything."""
    if status == STATUS_APPROVED:
        return {"key": STATUS_APPROVED, "label": STATUS_LABEL[STATUS_APPROVED], "tone": "approved"}
    if status == STATUS_FILED:
        return {"key": STATUS_FILED, "label": STATUS_LABEL[STATUS_FILED], "tone": "filed"}
    if status == STATUS_OPEN:
        return {"key": STATUS_OPEN, "label": STATUS_LABEL[STATUS_OPEN], "tone": "open"}
    last = next((n for n in reversed(notes or []) if n.get("by") == "reviewer"), None)
    outcome = (last or {}).get("outcome")
    if not outcome:
        return {"key": "stale", "label": "پاسخ — بدونِ نتیجه", "tone": "stale"}
    if outcome == OUTCOME_FIXED and not (last or {}).get("after_shot_id"):
        return {"key": OUTCOME_PARTIAL, "label": "ادعای انجام، بدونِ تصویرِ بعدش",
                "tone": OUTCOME_PARTIAL, "outcome": OUTCOME_PARTIAL}
    return {"key": outcome, "label": OUTCOME_LABEL.get(outcome, outcome), "tone": outcome,
            "outcome": outcome}
