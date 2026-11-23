"""PM-INS-0033: «📥 از کرومِ من» — the owner's Chrome session reaches the server via a single-use, host-bound ticket."""

import json

from fastapi.testclient import TestClient

from app.services import manual_login as ML

HOST = "detective-1-frontend.onrender.com"


def _dump(origin=f"https://{HOST}"):
    return {
        "origin": origin, "href": origin + "/dash", "title": "Dash", "cookie": "a=1; theme=dark",
        "localStorage": {"tok": "SECRET-LS"},
        "indexedDB": [{"name": "firebaseLocalStorageDb", "version": 1, "stores": [
            {"name": "firebaseLocalStorage", "keyPath": "fbase_key", "autoIncrement": False, "indexes": [],
             "records": [{"value": {"fbase_key": "firebase:authUser:k", "value": {"uid": "SECRET-UID"}}}]},
            {"name": "kv", "keyPath": None, "autoIncrement": False, "indexes": [],
             "records": [{"key": "k1", "value": {"a": 1}}]}]}],
    }


def test_ticket_is_single_use_and_host_bound(tmp_path, monkeypatch):
    monkeypatch.setenv("MANUAL_LOGIN_DIR", str(tmp_path))
    t = ML.issue_import_ticket(HOST)["token"]
    assert t not in "".join(p.read_text() for p in tmp_path.iterdir())  # only the hash is stored
    meta = ML.import_from_browser(t, json.dumps(_dump()))
    assert meta["source"] == "chrome" and meta["cookies"] == 2 and meta["indexed_db"] == 2 and meta["local_storage"] == 1
    raw = "".join(p.read_text() for p in tmp_path.iterdir())
    assert "SECRET-LS" not in raw and "SECRET-UID" not in raw  # encrypted on disk
    st = ML.state_for_url(f"https://{HOST}/people")
    idb = st["origins"][0]["indexedDB"][0]["stores"]
    assert idb[0]["keyPath"] == "fbase_key" and "key" not in idb[0]["records"][0]
    assert idb[1]["records"][0]["key"] == "k1" and "keyPath" not in idb[1]
    try:
        ML.import_from_browser(t, json.dumps(_dump()))
        raise AssertionError("ticket reused")
    except ValueError:
        pass


def test_ticket_rejects_another_site_and_expiry(tmp_path, monkeypatch):
    monkeypatch.setenv("MANUAL_LOGIN_DIR", str(tmp_path))
    t = ML.issue_import_ticket(HOST)["token"]
    try:
        ML.import_from_browser(t, json.dumps(_dump("https://evil.example")))
        raise AssertionError("wrong host accepted")
    except ValueError:
        pass
    assert ML.state_for_url("https://evil.example/") is None
    t2 = ML.issue_import_ticket(HOST)["token"]
    d = json.loads((tmp_path / ML.TICKETS_FILE).read_text())
    for v in d.values():
        v["exp"] = 1
    (tmp_path / ML.TICKETS_FILE).write_text(json.dumps(d))
    assert ML.consume_import_ticket(t2) is None


def test_saved_list_and_forget(tmp_path, monkeypatch):
    monkeypatch.setenv("MANUAL_LOGIN_DIR", str(tmp_path))
    ML.import_from_browser(ML.issue_import_ticket(HOST)["token"], json.dumps(_dump()))
    ML.save_state("quran.example", {"cookies": [], "origins": []})
    hosts = {x["host"]: x for x in ML.list_saved()}
    assert set(hosts) == {HOST, "quran.example"} and "blob" not in hosts[HOST]
    assert ML.forget(HOST) and [x["host"] for x in ML.list_saved()] == ["quran.example"]


def test_import_route_is_public_but_ticket_guarded(tmp_path, monkeypatch):
    from app.main import app

    monkeypatch.setenv("MANUAL_LOGIN_DIR", str(tmp_path))
    monkeypatch.setenv("ADMIN_EMAILS", "owner@example.com")  # wall on
    monkeypatch.setenv("AUTH_DISABLED", "0")
    c = TestClient(app)
    r = c.post("/api/inspector-agent/login/import", data={"t": "imp_bad", "d": "{}"})
    assert r.status_code == 400 and "بلیت" in r.text
    t = ML.issue_import_ticket(HOST)["token"]
    r = c.post("/api/inspector-agent/login/import", data={"t": t, "d": json.dumps(_dump())})
    assert r.status_code == 200 and "✅" in r.text and "SECRET" not in r.text
    # the ticket and the saved list stay behind the wall
    assert c.post("/api/inspector-agent/login/import-ticket", json={"url": f"https://{HOST}/"}).status_code == 401
    assert c.get("/api/inspector-agent/login/saved").status_code == 401
