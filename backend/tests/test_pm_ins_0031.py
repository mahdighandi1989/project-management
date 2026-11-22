"""PM-INS-0031: «🔐 ورودِ یک‌باره» — the owner's sign-in is kept encrypted per site and reused by 📸/agent."""

import json

import pytest

from fastapi.testclient import TestClient

from app.services import manual_login as ML


def test_state_is_encrypted_per_host_and_reused(tmp_path, monkeypatch):
    monkeypatch.setenv("MANUAL_LOGIN_DIR", str(tmp_path))
    state = {"cookies": [{"name": "sid", "value": "SECRET-COOKIE", "domain": "detective-1-frontend.onrender.com",
                          "path": "/"}], "origins": []}
    meta = ML.save_state("detective-1-frontend.onrender.com", state, final_url="https://detective-1-frontend.onrender.com/dash")
    assert meta["cookies"] == 1
    raw = "".join(p.read_text() for p in tmp_path.iterdir())
    assert "SECRET-COOKIE" not in raw  # never in clear on disk
    assert ML.state_for_url("https://detective-1-frontend.onrender.com/people?x=1") == state
    assert ML.state_for_url("https://other.onrender.com/") is None
    st = ML.status_for("detective-1-frontend.onrender.com")
    assert st and not st["expired"] and "blob" not in st


def test_expired_state_is_not_used(tmp_path, monkeypatch):
    monkeypatch.setenv("MANUAL_LOGIN_DIR", str(tmp_path))
    ML.save_state("a.example", {"cookies": [], "origins": []})
    p = next(tmp_path.iterdir())
    d = json.loads(p.read_text())
    d["expires_at"] = "2000-01-01T00:00:00+00:00"
    p.write_text(json.dumps(d))
    assert ML.state_for_url("https://a.example/") is None
    assert ML.status_for("a.example")["expired"] is True
    assert ML.forget("a.example") and ML.status_for("a.example") is None


@pytest.mark.asyncio
async def test_agent_prefers_the_owners_sign_in(tmp_path, monkeypatch):
    from app.services import browser_agent as BA

    monkeypatch.setenv("MANUAL_LOGIN_DIR", str(tmp_path))
    ML.save_state("site.example", {"cookies": [], "origins": [{"origin": "https://site.example", "localStorage": []}]})
    st, note = await BA.login_state_for("https://site.example/inner")
    assert st and "🔐" in note


def test_login_routes_reject_unknown_session_and_bad_url():
    from app.main import app

    c = TestClient(app)
    r = c.post("/api/inspector-agent/login/start", json={"url": "javascript:alert(1)"})
    assert r.status_code in (400, 401)
    r = c.get("/api/inspector-agent/login/nope/frame")
    assert r.status_code in (404, 401)
