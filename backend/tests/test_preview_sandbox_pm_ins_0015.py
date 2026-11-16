# -*- coding: utf-8 -*-
"""PM-INS-0015 — the previewed project must never share AI Creator's origin.

Every proxy response carries CSP `sandbox` WITHOUT allow-same-origin (opaque origin ⇒ window.parent.localStorage and
pm.auth.token unreachable); the page gets an in-memory storage shim BEFORE its own scripts; the ticket cookie is
SameSite=None so the sandboxed page's own files still pass the wall.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


class _Resp:
    def __init__(self, text, ct):
        self.text, self.content, self.status_code = text, text.encode(), 200
        self.headers = {"content-type": ct}


def _app(tmp_path, monkeypatch, body, ct):
    import httpx
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from app.api.routes import render_logs
    from app.core.database import Base, get_db
    from app.models.render_log import RenderService

    engine = create_engine(f"sqlite:///{tmp_path}/t.db", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine, tables=[Base.metadata.tables["render_services"]])
    S = sessionmaker(bind=engine)
    db = S()
    db.add(RenderService(id="srv-1", name="quran-frontend", type="static_site", project_id="gh_o_quran",
                         service_url="https://quran.example"))
    db.commit(); db.close()

    class FakeClient:
        def __init__(self, *a, **k): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *a): return False
        async def get(self, url, headers=None): return _Resp(body, ct)

    monkeypatch.setattr(httpx, "AsyncClient", FakeClient)
    app = FastAPI()
    app.include_router(render_logs.router)

    def _db():
        d = S()
        try:
            yield d
        finally:
            d.close()
    app.dependency_overrides[get_db] = _db
    return TestClient(app)


def test_html_is_sandboxed_and_shim_runs_first(tmp_path, monkeypatch):
    html = '<html><head><script src="/app.js"></script></head><body>x</body></html>'
    r = _app(tmp_path, monkeypatch, html, "text/html").get("/api/render/inspector/proxy/gh_o_quran/")
    csp = r.headers.get("content-security-policy", "")
    assert csp.startswith("sandbox ") and "allow-scripts" in csp and "allow-same-origin" not in csp
    head = r.text.split("<head>", 1)[1]
    assert head.startswith('<script data-inspector-storage-shim="true">'), "shim must precede the page's scripts"
    assert head.index("storage-shim") < head.index("/api/render/inspector/proxy/gh_o_quran/app.js")


def test_assets_are_sandboxed_too(tmp_path, monkeypatch):
    r = _app(tmp_path, monkeypatch, "console.log(1)", "application/javascript").get(
        "/api/render/inspector/proxy/gh_o_quran/app.js")
    assert "allow-same-origin" not in r.headers["content-security-policy"]
    assert r.headers["content-security-policy"].startswith("sandbox")


def test_shim_injection_without_head():
    from app.api.routes.render_logs import _inject_storage_shim

    assert _inject_storage_shim("<p>x</p>").startswith("<script data-inspector-storage-shim")
    out = _inject_storage_shim('<HTML lang="fa"><body></body></HTML>')
    assert out.startswith('<HTML lang="fa"><head><script data-inspector-storage-shim')


def test_iframe_and_ticket_cookie_are_wired():
    root = Path(__file__).resolve().parents[2] / "frontend" / "src"
    page = (root / "app" / "projects" / "[id]" / "page.tsx").read_text(encoding="utf-8")
    import re
    sandboxes = re.findall(r'sandbox="([^"]*)"', page)
    assert sandboxes and all("allow-same-origin" not in s for s in sandboxes)
    ticket = (root / "lib" / "previewTicket.ts").read_text(encoding="utf-8")
    assert "samesite=none; secure" in ticket
    auth = (root / "lib" / "auth.tsx").read_text(encoding="utf-8")
    assert "FOREIGN_PREVIEW_KEY_PREFIXES = ['quran.']" in auth and "purgeForeignPreviewKeys()" in auth
