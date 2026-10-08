# -*- coding: utf-8 -*-
"""«نظارت و سرکشی» — the guards that make the board trustworthy, and the rule
that bytes end up in Google Drive and NOT on this server.

Runs on a throw-away SQLite file with only the inspection router mounted, so it
never touches the development database and needs no network: Drive is faked.
"""
import hashlib
import json
import os
import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

TOKEN = "test-supervisor-token"
SUP = {"X-Supervisor-Token": TOKEN}
PNG = ("data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQ"
       "DwAEhQGAhKmMIQAAAABJRU5ErkJggg==")


@pytest.fixture()
def env(monkeypatch):
    tmp = tempfile.mkdtemp(prefix="insp-")
    monkeypatch.setenv("SUPERVISOR_TOKEN", TOKEN)
    monkeypatch.setenv("INSPECTION_SPOOL_DIR", os.path.join(tmp, "spool"))
    monkeypatch.setenv("INSPECTION_SYNC_DISABLED", "1")
    for k in ("GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET", "GOOGLE_DRIVE_REFRESH_TOKEN"):
        monkeypatch.delenv(k, raising=False)

    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from app.core import database
    from app.core.database import Base, get_db
    from app.models import inspection as _m  # noqa: F401  (registers the tables)
    from app.models import setting as _s  # noqa: F401
    from app.api.routes import inspection

    engine = create_engine(f"sqlite:///{tmp}/t.db", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine, tables=[
        t for name, t in Base.metadata.tables.items()
        if name.startswith("inspection_") or name == "settings"])
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    monkeypatch.setattr(database, "SessionLocal", Session)

    def _db():
        db = Session()
        try:
            yield db
        finally:
            db.close()

    app = FastAPI()
    app.include_router(inspection.router, prefix="/api")
    app.dependency_overrides[get_db] = _db
    client = TestClient(app)
    return {"client": client, "Session": Session, "tmp": tmp}


def _spot(page="/projects", label="پروژه‌ها"):
    return {"page": page, "page_label": label, "section_id": "", "section_label": "",
            "reopen": page, "url": page, "dom_path": "main > div", "covered_text": "دکمه",
            "rect": {"x": 1, "y": 2, "w": 30, "h": 40}, "viewport": {"w": 1200, "h": 800},
            "geometry": {"doc": {"x": 1, "y": 2, "w": 30, "h": 40},
                         "anchor": {"path": "main > div", "rect": {"x": 0, "y": 0, "w": 100, "h": 100},
                                    "rel": {"x": 0.01, "y": 0.02, "w": 0.3, "h": 0.4}}}}


def _create(c, text="این دکمه کار نمی‌کند", **kw):
    body = {"text": text, "spot": _spot(), "shot": PNG}
    body.update(kw)
    r = c.post("/api/inspection", json=body)
    assert r.status_code == 200, r.text
    return r.json()["report"]


def test_create_list_and_reference(env):
    c = env["client"]
    rep = _create(c)
    assert rep["number"] == 1 and rep["ref"] == "PM-INS-0001"
    assert rep["status"] == "open" and rep["glow"]["tone"] == "open"
    assert rep["notes"][0]["by"] == "owner" and rep["notes"][0]["shot_id"]
    shot = rep["shots"][rep["notes"][0]["shot_id"]]
    # Drive is not connected in tests → the picture waits on the spool, and SAYS so
    assert shot["store"] == "pending" and shot["ref"] == "PM-INS-0001-S01"
    lst = c.get("/api/inspection").json()
    assert lst["counts"]["open"] == 1 and len(lst["reports"]) == 1
    assert c.get(f"/api/inspection/shots/{rep['notes'][0]['shot_id']}").status_code == 200


def test_general_request_has_its_own_place(env):
    c = env["client"]
    r = c.post("/api/inspection", json={"text": "یک قابلیتِ تازه می‌خواهم", "kind": "general"})
    assert r.status_code == 200, r.text
    rep = r.json()["report"]
    assert rep["kind"] == "general" and rep["page"] == "/inspection"
    assert c.get("/api/inspection").json()["general_open"] == 1


def test_fixed_needs_after_picture_and_only_supervisor_sets_outcome(env):
    c = env["client"]
    rep = _create(c)
    rid = rep["id"]
    # the owner cannot record an outcome
    r = c.post(f"/api/inspection/{rid}/notes", json={"text": "درست شد", "outcome": "fixed", "after_shot": PNG})
    assert r.status_code == 422
    # the supervisor cannot claim «fixed» without the picture
    r = c.post(f"/api/inspection/{rid}/notes", headers=SUP, json={"text": "درست شد", "outcome": "fixed"})
    assert r.status_code == 422
    r = c.post(f"/api/inspection/{rid}/notes", headers=SUP, json={
        "text": "۱) انجام شد", "outcome": "fixed", "after_shot": PNG,
        "dependencies": [{"name": "GET /api/projects", "status": "ok"}], "commits": ["abc1234"]})
    assert r.status_code == 200, r.text
    rep = r.json()["report"]
    assert rep["status"] == "answered" and rep["glow"]["tone"] == "fixed"
    assert rep["dependencies"][0]["name"] == "GET /api/projects"
    # an owner follow-up turns it back to «open» (amber) — the conversation is not settled
    r = c.post(f"/api/inspection/{rid}/notes", json={"text": "هنوز رنگش عوض نشده"})
    assert r.json()["report"]["status"] == "open"


def test_only_owner_ticks_and_round_files_into_binder(env):
    c = env["client"]
    rid = _create(c)["id"]
    assert c.post(f"/api/inspection/{rid}/status", headers=SUP, json={"status": "approved"}).status_code == 403
    assert c.delete(f"/api/inspection/{rid}", headers=SUP).status_code == 403
    r = c.post(f"/api/inspection/{rid}/status", json={"status": "approved"})
    assert r.json()["report"]["glow"]["tone"] == "approved"
    r = c.post("/api/inspection/file", headers=SUP)
    assert r.json()["filed"] == 1
    rep = c.get(f"/api/inspection/{rid}").json()["report"]
    assert rep["status"] == "filed" and rep["binder"]["number"] == 1 and rep["binder"]["page"] == 1
    assert c.get("/api/inspection/binders").json()["binders"][0]["count"] == 1
    # a filed sheet is closed for notes
    assert c.post(f"/api/inspection/{rid}/notes", json={"text": "x"}).status_code == 422


def _upload(c, rid, name, data: bytes, mime="text/plain", note_id=""):
    st = c.post(f"/api/inspection/{rid}/intake/start",
                json={"filename": name, "mime": mime, "size": len(data), "caption": "نمونه", "note_id": note_id})
    assert st.status_code == 200, st.text
    uid = st.json()["upload_id"]
    half = len(data) // 2
    for off, piece in ((0, data[:half]), (half, data[half:])):
        if piece:
            r = c.post(f"/api/inspection/intake/{uid}/append?offset={off}", content=piece,
                       headers={"Content-Type": "application/octet-stream"})
            assert r.status_code == 200, r.text
    # an out-of-order piece is refused with the offset to resume from
    r = c.post(f"/api/inspection/intake/{uid}/append?offset=0", content=b"x",
               headers={"Content-Type": "application/octet-stream"})
    assert r.status_code in (409, 413)
    fin = c.post(f"/api/inspection/intake/{uid}/finish")
    assert fin.status_code == 200, fin.text
    return fin.json()["file"]


def test_files_must_be_read_fully_before_the_supervisor_answers(env):
    c = env["client"]
    rid = _create(c)["id"]
    text = ("سطرِ نمونه\n" * 3000).encode("utf-8")
    f = _upload(c, rid, "نمونه.txt", text)
    assert f["extract_status"] == "ok" and f["text_chars"] > 0
    assert f["ref"] == "PM-INS-0001-F01"
    assert f["store"] == "pending" and not f["durable"] and "درایو" in f["store_note"]
    q = c.get("/api/inspection/queue", headers=SUP).json()
    assert q["files_to_read"] == 1 and q["files_not_in_drive"] == 1
    r = c.post(f"/api/inspection/{rid}/notes", headers=SUP, json={"text": "نگاه کردم", "outcome": "not-done"})
    assert r.status_code == 422 and "نمونه.txt" in r.text
    # reading only the END does not count — only a contiguous read
    c.get(f"/api/inspection/files/{f['id']}/text?offset=1000&limit=10", headers=SUP)
    assert c.get(f"/api/inspection/files/{f['id']}", headers=SUP).json()["file"]["read_chars"] == 0
    off = 0
    while True:
        page = c.get(f"/api/inspection/files/{f['id']}/text?offset={off}&limit=5000", headers=SUP).json()
        if not page["has_more"]:
            break
        off = page["next_offset"]
    assert page["fully_read"]
    r = c.post(f"/api/inspection/{rid}/notes", headers=SUP, json={"text": "خواندم؛ ۱) نشد چون…", "outcome": "not-done"})
    assert r.status_code == 200, r.text


def test_image_file_must_be_opened(env):
    c = env["client"]
    rid = _create(c)["id"]
    import base64

    png = base64.b64decode(PNG.split(",", 1)[1])
    f = _upload(c, rid, "screen.png", png, mime="image/png")
    assert f["extract_status"] == "image"
    assert c.post(f"/api/inspection/{rid}/notes", headers=SUP,
                  json={"text": "x", "outcome": "needs-owner"}).status_code == 422
    raw = c.get(f"/api/inspection/files/{f['id']}/raw", headers=SUP)
    assert raw.status_code == 200 and raw.content == png
    assert c.post(f"/api/inspection/{rid}/notes", headers=SUP,
                  json={"text": "x", "outcome": "needs-owner"}).status_code == 200


def test_follow_up_claims_only_its_own_files(env):
    c = env["client"]
    rid = _create(c)["id"]
    first = _upload(c, rid, "a.txt", b"aaa")
    second = _upload(c, rid, "b.txt", b"bbb")
    r = c.post(f"/api/inspection/{rid}/notes", json={"text": "ادامه", "file_ids": [second["id"], first["id"]],
                                                     "spot": _spot("/settings", "تنظیمات"), "shot": PNG})
    rep = r.json()["report"]
    nid = rep["notes"][-1]["id"]
    owners = {f["filename"]: f["note_id"] for f in rep["files"]}
    assert owners["b.txt"] == nid and owners["a.txt"] == nid  # both unclaimed → both claimed by this note
    assert rep["notes"][-1]["spot"]["page"] == "/settings"
    third = _upload(c, rid, "c.txt", b"ccc", note_id="")
    c.post(f"/api/inspection/{rid}/notes", json={"text": "باز هم", "file_ids": [first["id"], third["id"]]})
    rep = c.get(f"/api/inspection/{rid}").json()["report"]
    owners = {f["filename"]: f["note_id"] for f in rep["files"]}
    assert owners["a.txt"] == nid           # never pulled out from under the earlier note
    assert owners["c.txt"] == rep["notes"][-1]["id"]


def test_urgent_queue_claim_heartbeat_and_discharge(env):
    c = env["client"]
    a = _create(c, "اول")["id"]
    b = _create(c, "دوم")["id"]
    assert c.post(f"/api/inspection/{b}/urgent", headers=SUP).status_code == 403
    r1 = c.post(f"/api/inspection/{b}/urgent").json()
    r2 = c.post(f"/api/inspection/{a}/urgent").json()
    assert r1["position"] == 1 and r2["position"] == 2      # the order the owner pressed them
    assert r1["next_round"]["basis"] == "assumed"
    assert c.post("/api/inspection/urgent/claim", json={}).status_code == 403
    got = c.post("/api/inspection/urgent/claim", headers=SUP, json={"by": "routine"}).json()
    assert got["report"]["id"] == b
    # a second run skips the claimed one
    got2 = c.post("/api/inspection/urgent/claim", headers=SUP, json={"by": "routine"}).json()
    assert got2["report"]["id"] == a
    # the knocks were recorded → the countdown is now observed-based
    assert c.get("/api/inspection/urgent").json()["next_round"]["last_seen"]
    c.post(f"/api/inspection/{b}/notes", headers=SUP, json={"text": "نشد چون…", "outcome": "not-done"})
    rep = c.get(f"/api/inspection/{b}").json()["report"]
    assert rep["urgent"] is False and rep["urgent_done_at"]
    # the owner asking again puts it back in the fast queue
    c.post(f"/api/inspection/{b}/notes", json={"text": "دوباره نگاه کن"})
    assert c.get(f"/api/inspection/{b}").json()["report"]["urgent"] is True


def test_edit_note_keeps_original_and_guards_sides(env):
    c = env["client"]
    rep = _create(c, "متنِ اول")
    nid = rep["notes"][0]["id"]
    assert c.patch(f"/api/inspection/{rep['id']}/notes/{nid}", headers=SUP, json={"text": "x"}).status_code == 403
    r = c.patch(f"/api/inspection/{rep['id']}/notes/{nid}", json={"text": "متنِ اصلاح‌شده"})
    note = r.json()["report"]["notes"][0]
    assert note["text"] == "متنِ اصلاح‌شده" and note["original_text"] == "متنِ اول" and note["edited_at"]
    assert r.json()["report"]["title"] == "متنِ اصلاح‌شده"


def test_surface_map_records_new_elements_and_patterns(env):
    from app.api.routes.inspection import route_pattern

    assert route_pattern("/projects/42/files?tab=x") == "/projects/[id]/files"
    assert route_pattern("/project/3f34a2b1-2a8d-4ad2-904a-9835a8a5b7c9") == "/project/[id]"
    assert route_pattern("/") == "/"
    c = env["client"]
    el = lambda k, l: {"kind": k, "label": l, "selector": f"#{l}", "rect": {"x": 1, "y": 2, "w": 3, "h": 4}}
    r = c.post("/api/inspection/surfaces", json={"path": "/projects/7", "label": "پروژه", "elements": [el("button", "a")]})
    assert r.status_code == 200 and r.json()["route"] == "/projects/[id]"
    r = c.post("/api/inspection/surfaces", json={"path": "/projects/9", "elements": [el("button", "a"), el("tab", "b")]})
    assert r.json()["new"] == 1
    lst = c.get("/api/inspection/surfaces").json()["surfaces"]
    assert len(lst) == 1 and lst[0]["visits"] == 2 and lst[0]["counts"] == {"button": 1, "tab": 1}
    # the code inventory marks declared pages, including ones never opened
    assert c.post("/api/inspection/inventory", json={"pages": []}).status_code == 403
    r = c.post("/api/inspection/inventory", headers=SUP, json={"pages": [
        {"route": "/projects/[id]", "file": "frontend/src/app/projects/[id]/page.tsx"},
        {"route": "/debate", "file": "frontend/src/app/debate/page.tsx", "label": "مناظره"}]})
    assert r.json()["declared"] == 2
    lst = {s["route"]: s for s in c.get("/api/inspection/surfaces").json()["surfaces"]}
    assert lst["/debate"]["declared"] and lst["/debate"]["visits"] == 0
    detail = c.get(f"/api/inspection/surfaces/{lst['/projects/[id]']['id']}").json()["surface"]
    assert len(detail["elements"]) == 2


def test_whoami_and_schedule(env):
    c = env["client"]
    assert c.get("/api/inspection/whoami").json()["supervisor"] is False
    assert c.get("/api/inspection/whoami", headers=SUP).json()["supervisor"] is True
    s = c.get("/api/inspection/schedule").json()
    assert s["urgent"]["cron_utc"] and s["full"]["prompt"] == "docs/supervisor/PROMPT.md"
    st = c.get("/api/inspection/storage").json()
    assert st["drive"]["connected"] is False and "GOOGLE_CLIENT_ID" in " ".join(st["drive"]["missing"])


def test_push_to_drive_verifies_and_empties_the_disk(env, monkeypatch):
    """«در بک‌اند چیزی رو نگه ندار»: once Drive has the bytes (same MD5), the
    spool copy and the text sidecar are gone and only the reference remains."""
    c = env["client"]
    rid = _create(c)["id"]
    f = _upload(c, rid, "گزارش.txt", "متنِ مهم".encode("utf-8"))

    from app.services import gdrive, inspection_files as ifiles
    from app.models.inspection import InspectionFile, InspectionShot

    uploaded = []

    def fake_upload(db, src, *, name, mime, parent, size, description=""):
        data = src.read()
        uploaded.append((name, parent, len(data)))
        return {"id": f"drv-{len(uploaded)}", "link": f"https://drive.google.com/file/d/drv-{len(uploaded)}",
                "md5": hashlib.md5(data).hexdigest()}

    monkeypatch.setattr(gdrive, "is_connected", lambda db: True)
    monkeypatch.setattr(gdrive, "ensure_folder", lambda db, parts: "folder-" + "-".join(parts[-1:]))
    monkeypatch.setattr(gdrive, "upload", fake_upload)
    res = ifiles.sync_pending()
    assert res["files"] == 1 and res["shots"] == 1 and res["failed"] == 0
    db = env["Session"]()
    row = db.query(InspectionFile).filter(InspectionFile.id == f["id"]).one()
    assert row.store == "drive" and row.drive_id and row.text_drive_id
    assert row.spool_path == "" and row.spool_text_path == ""
    assert "PM-INS-0001-F01" in row.drive_path and "نظارت و سرکشی" in row.drive_path
    shot = db.query(InspectionShot).one()
    assert shot.store == "drive" and shot.spool_path == ""
    db.close()
    # nothing left on this server's disk
    left = [p.name for p in Path(os.environ["INSPECTION_SPOOL_DIR"]).iterdir()]
    assert left == [], left
    names = [u[0] for u in uploaded]
    assert any(n.startswith("PM-INS-0001-F01 — گزارش.txt") and n.endswith(".متن.txt") for n in names)


def test_push_keeps_local_copy_when_md5_disagrees(env, monkeypatch):
    c = env["client"]
    rid = _create(c, shot=None)["id"]
    f = _upload(c, rid, "x.txt", b"abc")
    from app.services import gdrive, inspection_files as ifiles
    from app.models.inspection import InspectionFile

    monkeypatch.setattr(gdrive, "is_connected", lambda db: True)
    monkeypatch.setattr(gdrive, "ensure_folder", lambda db, parts: "folder")
    monkeypatch.setattr(gdrive, "upload", lambda db, src, **kw: {"id": "d", "link": "l", "md5": "0" * 32})
    ifiles.sync_pending()
    db = env["Session"]()
    row = db.query(InspectionFile).filter(InspectionFile.id == f["id"]).one()
    assert row.store == "failed" and row.spool_path and Path(row.spool_path).exists()
    db.close()


def test_extract_distinguishes_no_text_states():
    from app.services.inspection_files import extract

    assert extract(b"", "a.png", "image/png")["status"] == "image"
    assert extract(b"", "a.mp4", "video/mp4")["status"] == "media"
    assert extract(b"abc", "a.bin", "application/octet-stream")["status"] == "unsupported"
    assert extract(b"   ", "a.txt", "text/plain")["status"] == "empty"
    assert extract("سلام".encode(), "a.md", "")["status"] == "ok"
    assert extract(b"not a pdf", "a.pdf", "application/pdf")["status"] == "failed"
