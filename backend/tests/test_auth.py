# -*- coding: utf-8 -*-
"""Sign-in with Google and the wall in front of the API (app/core/auth.py)."""
import os
import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

OWNER = "owner@example.com"


@pytest.fixture()
def env(monkeypatch):
    tmp = tempfile.mkdtemp(prefix="auth-")
    monkeypatch.setenv("AUTH_DISABLED", "0")
    monkeypatch.setenv("ADMIN_EMAILS", OWNER)
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "cid.apps.googleusercontent.com")
    monkeypatch.setenv("SECRET_KEY", "x" * 40)
    monkeypatch.setenv("SUPERVISOR_TOKEN", "sup-secret")
    monkeypatch.setenv("EXTERNAL_TOOL_TOKEN", "ext-secret")
    monkeypatch.setenv("INSPECTION_SPOOL_DIR", os.path.join(tmp, "spool"))
    monkeypatch.setenv("INSPECTION_SYNC_DISABLED", "1")

    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from app.core import auth as A
    from app.core import database
    from app.core.database import Base, get_db
    from app.models import app_user, inspection as _i, setting as _s  # noqa: F401
    from app.api.routes import auth as auth_routes, inspection

    monkeypatch.setattr(A, "_key", None)
    engine = create_engine(f"sqlite:///{tmp}/t.db", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine, tables=[t for n, t in Base.metadata.tables.items()
                                                  if n.startswith("inspection_") or n in ("settings", "app_users")])
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    monkeypatch.setattr(database, "SessionLocal", Session)

    def _db():
        db = Session()
        try:
            yield db
        finally:
            db.close()

    app = FastAPI()
    app.add_middleware(A.AuthWall)
    app.include_router(auth_routes.router, prefix="/api")
    app.include_router(inspection.router, prefix="/api")

    @app.get("/api/external/prompts/next")
    def ext():
        return {"ok": True}

    app.dependency_overrides[get_db] = _db

    def fake_google(credential):
        email = credential.split(":", 1)[1]
        return {"sub": "g-" + email, "email": email, "name": "N", "picture": ""}

    monkeypatch.setattr(A, "verify_google_credential", fake_google)
    return TestClient(app)


def _login(c, email):
    return c.post("/api/auth/google", json={"credential": "fake-google-credential:" + email})


def test_wall_blocks_without_session_and_public_paths_stay_open(env):
    c = env
    assert c.get("/api/inspection").status_code == 401
    cfg = c.get("/api/auth/config").json()
    assert cfg["auth_enforced"] is True and cfg["google_client_id"]
    assert c.options("/api/inspection").status_code != 401


def test_owner_signs_in_and_sees_everything(env):
    c = env
    r = _login(c, OWNER)
    assert r.status_code == 200, r.text
    tok = r.json()["access_token"]
    h = {"Authorization": f"Bearer {tok}"}
    assert c.get("/api/inspection", headers=h).status_code == 200
    me = c.get("/api/auth/me", headers=h).json()
    assert me["role"] == "owner" and me["user"]["email"] == OWNER
    # media links may carry the token in the query on GET only
    assert c.get(f"/api/inspection?access_token={tok}").status_code == 200
    assert c.post(f"/api/inspection?access_token={tok}", json={"text": "x"}).status_code == 401


def test_stranger_is_pending_until_owner_approves(env):
    c = env
    r = _login(c, "someone@example.com")
    assert r.status_code == 403 and "تأیید" in r.json()["detail"]
    owner = {"Authorization": "Bearer " + _login(c, OWNER).json()["access_token"]}
    users = c.get("/api/auth/users", headers=owner).json()["users"]
    sid = next(u["id"] for u in users if u["email"] == "someone@example.com")
    assert c.patch(f"/api/auth/users/{sid}", headers=owner, json={"status": "approved"}).status_code == 200
    r = _login(c, "someone@example.com")
    assert r.status_code == 200
    member = {"Authorization": "Bearer " + r.json()["access_token"]}
    assert c.get("/api/inspection", headers=member).status_code == 200
    assert c.get("/api/auth/users", headers=member).status_code == 403
    # blocking revokes the session at once
    c.patch(f"/api/auth/users/{sid}", headers=owner, json={"status": "blocked"})
    assert c.get("/api/inspection", headers=member).status_code == 401


def test_logout_all_revokes_tokens(env):
    c = env
    h = {"Authorization": "Bearer " + _login(c, OWNER).json()["access_token"]}
    assert c.post("/api/auth/logout-all", headers=h).status_code == 200
    assert c.get("/api/inspection", headers=h).status_code == 401


def test_machine_callers_keep_working(env):
    c = env
    assert c.get("/api/external/prompts/next", headers={"X-External-Token": "ext-secret"}).status_code == 200
    assert c.get("/api/external/prompts/next", headers={"X-External-Token": "wrong"}).status_code == 401
    assert c.get("/api/inspection/whoami", headers={"X-Supervisor-Token": "sup-secret"}).json()["supervisor"]
    # the supervisor's browser session counts as the supervisor, never as the owner
    s = c.post("/api/auth/supervisor-session", headers={"X-Supervisor-Token": "sup-secret"}).json()["access_token"]
    sh = {"Authorization": f"Bearer {s}"}
    assert c.get("/api/inspection/whoami", headers=sh).json()["supervisor"] is True
    assert c.post("/api/auth/supervisor-session").status_code == 403
    rep = c.post("/api/inspection", headers={"Authorization": "Bearer " + _login(c, OWNER).json()["access_token"]},
                 json={"text": "x", "kind": "general"}).json()["report"]
    assert c.post(f"/api/inspection/{rep['id']}/status", headers=sh, json={"status": "approved"}).status_code == 403


def test_wall_is_off_until_owners_are_configured(env, monkeypatch):
    monkeypatch.setenv("ADMIN_EMAILS", "")
    assert env.get("/api/inspection").status_code == 200
    monkeypatch.setenv("ADMIN_EMAILS", OWNER)
    monkeypatch.setenv("AUTH_DISABLED", "1")
    assert env.get("/api/inspection").status_code == 200
