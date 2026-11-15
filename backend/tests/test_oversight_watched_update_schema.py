# -*- coding: utf-8 -*-
"""Every setting the «اتاق فرمان» card sends with PATCH /oversight/watched/{id} must survive the route schema AND be
allowed by the service (2026-11-15: 14 toggles — verify mode, the 8 Scan-v5 flags, sounds, auth recipe … — answered
200 and were silently dropped by pydantic)."""
import asyncio
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
ROOT = Path(__file__).resolve().parents[2]


def _ui_keys() -> set:
    fe = (ROOT / "frontend/src/app/oversight/page.tsx").read_text(encoding="utf-8")
    keys = set(re.findall(r"onChange\(\{[^}]*?\b([a-z_0-9]+)\s*:", fe))
    keys |= set(re.findall(r"onChange\(\{\s*([a-z_0-9]+)\s*:", fe))
    return keys


def _service_allowed() -> set:
    svc = (ROOT / "backend/app/services/oversight_service.py").read_text(encoding="utf-8")
    blk = svc[svc.index("async def update_watched"):]
    blk = blk[: blk.index("for k, v in updates.items()")]
    return set(re.findall(r'"([a-z_0-9]+)"', blk))


def test_ui_keys_are_found():
    assert {"verify_mode", "logic_audit_enabled", "scan_depth"} <= _ui_keys()


def test_every_ui_key_passes_the_schema_and_the_service():
    from app.api.routes.oversight import WatchedUpdate

    schema = set(WatchedUpdate.model_fields)
    ui = _ui_keys()
    assert not ui - schema, f"dropped by WatchedUpdate: {sorted(ui - schema)}"
    assert not ui - _service_allowed(), f"ignored by update_watched: {sorted(ui - _service_allowed())}"
    assert not schema - _service_allowed(), f"schema fields the service ignores: {sorted(schema - _service_allowed())}"


def test_patch_round_trip(monkeypatch, tmp_path):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from app.api.routes import oversight as routes
    from app.services import oversight_service as svc_mod

    svc = svc_mod.get_oversight_service()
    w = svc_mod.WatchedProject(id="w-test", repo_full_name="o/r", repo_url="https://github.com/o/r")
    monkeypatch.setattr(svc, "watched", [w])
    monkeypatch.setattr(svc, "_save_watched", lambda *a, **k: None)
    app = FastAPI()
    app.include_router(routes.router, prefix="/api")
    c = TestClient(app)
    body = {"verify_mode": "fast", "logic_audit_enabled": False, "scan_notify_sound": True,
            "runtime_auth_recipe": {"type": "form_login", "login_url": "https://x/login", "steps": []},
            "frontend_base_url": "https://f.example"}
    r = c.patch("/api/oversight/watched/w-test", json=body)
    assert r.status_code == 200, r.text
    for k, v in body.items():
        assert getattr(w, k) == v, k
    # an explicit null clears a URL; a null for a normal field is ignored
    c.patch("/api/oversight/watched/w-test", json={"frontend_base_url": None, "verify_mode": None})
    assert w.frontend_base_url is None and w.verify_mode == "fast"
