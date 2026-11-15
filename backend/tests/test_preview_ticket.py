# -*- coding: utf-8 -*-
"""The «بازرس ویژه» screen behind the login wall (2026-11-15): a short-lived, project-scoped ticket in a
path-scoped cookie lets the iframe and its own files through — nothing else."""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def test_ticket_is_bound_to_project_and_expiry(monkeypatch):
    from app.core import auth as A

    monkeypatch.setattr(A, "_key", "k" * 40)
    t = A.preview_ticket("gh_o_r", ttl=60)
    assert A.preview_ticket_ok(t, "gh_o_r")
    assert not A.preview_ticket_ok(t, "gh_o_other")
    assert not A.preview_ticket_ok("1.abc", "gh_o_r")
    assert not A.preview_ticket_ok(A.preview_ticket("gh_o_r", ttl=-1), "gh_o_r")
    exp, sig = t.split(".")
    assert not A.preview_ticket_ok(f"{int(exp) + 999}.{sig}", "gh_o_r")  # extending the expiry breaks the signature


def test_wall_lets_only_the_proxy_get_with_its_cookie(monkeypatch):
    from app.core import auth as A

    monkeypatch.setattr(A, "_key", "k" * 40)
    t = A.preview_ticket("gh_o_r", ttl=60)
    ok = {"cookie": f"other=1; pm_preview={t}"}
    assert A.preview_allowed("/api/render/inspector/proxy/gh_o_r/_next/x.js", "GET", ok)
    assert A.preview_allowed("/api/render/inspector/proxy/gh_o_r", "GET", ok)
    assert not A.preview_allowed("/api/render/inspector/proxy/gh_o_r/x", "POST", ok)
    assert not A.preview_allowed("/api/render/inspector/proxy/gh_other/x", "GET", ok)
    assert not A.preview_allowed("/api/oversight/tasks", "GET", ok)
    assert not A.preview_allowed("/api/render/inspector/proxy/gh_o_r/x", "GET", {"cookie": "pm_preview=bad"})
    assert not A.preview_allowed("/api/render/inspector/proxy/gh_o_r/x", "GET", {})


def test_auth_wall_end_to_end(monkeypatch):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from app.core import auth as A

    monkeypatch.setattr(A, "_key", "k" * 40)
    monkeypatch.setenv("AUTH_DISABLED", "0")
    monkeypatch.setenv("ADMIN_EMAILS", "owner@example.com")
    app = FastAPI()
    app.add_middleware(A.AuthWall)

    @app.get("/api/render/inspector/proxy/{pid}/{path:path}")
    def proxy(pid: str, path: str):
        return {"pid": pid, "path": path}

    @app.get("/api/oversight/tasks")
    def tasks():
        return {"secret": True}

    c = TestClient(app)
    assert c.get("/api/render/inspector/proxy/gh_o_r/index.html").status_code == 401
    c.cookies.set("pm_preview", A.preview_ticket("gh_o_r", ttl=60))
    assert c.get("/api/render/inspector/proxy/gh_o_r/_next/app.js").json() == {"pid": "gh_o_r", "path": "_next/app.js"}
    assert c.get("/api/render/inspector/proxy/gh_other/x").status_code == 401
    assert c.get("/api/oversight/tasks").status_code == 401


def test_bridge_websocket_inspector_needs_the_ticket(monkeypatch):
    import pytest
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from starlette.websockets import WebSocketDisconnect

    from app.api.routes import render_logs
    from app.core import auth as A

    monkeypatch.setattr(A, "_key", "k" * 40)
    monkeypatch.setenv("AUTH_DISABLED", "0")
    monkeypatch.setenv("ADMIN_EMAILS", "owner@example.com")
    app = FastAPI()
    app.include_router(render_logs.router)  # its own prefix is /api/render
    c = TestClient(app)
    url = "/api/render/ws/bridge/gh_o_r"
    with c.websocket_connect(url) as ws:
        ws.send_json({"type": "register", "role": "inspector"})
        assert "ticket" in ws.receive_json()["message"]
        with pytest.raises(WebSocketDisconnect):
            ws.receive_json()
    with c.websocket_connect(url) as ws:
        ws.send_json({"type": "register", "role": "inspector", "ticket": A.preview_ticket("gh_o_r", ttl=60)})
        msg = ws.receive_json()
        assert msg.get("type") != "error", msg
    with c.websocket_connect(url) as ws:  # the reporting side is unchanged
        ws.send_json({"type": "register", "role": "bridge"})
        assert ws.receive_json().get("type") != "error"
