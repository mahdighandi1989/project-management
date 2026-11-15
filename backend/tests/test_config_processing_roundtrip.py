# -*- coding: utf-8 -*-
"""«مدل‌ها و تنظیمات › پیکربندی» saves through PUT /api/config/processing and reads back from GET /api/config
(2026-11-15: the page used to PUT /api/config, which does not exist, and read flat keys that never existed)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def test_processing_config_round_trip(tmp_path, monkeypatch):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from app.api.routes import config as routes
    from app.services import dynamic_config as dc

    from dataclasses import replace

    real = dc.get_config_service()
    monkeypatch.setattr(real, "_save_config", lambda *a, **k: None)  # never touch the config file
    monkeypatch.setattr(real._config, "processing", replace(real._config.processing))  # restored after the test
    monkeypatch.setattr(routes, "get_config_service", lambda: real)

    app = FastAPI()
    app.include_router(routes.router, prefix="/api")
    c = TestClient(app)
    body = {"max_tokens_per_model": 2048, "default_temperature": 0.3, "request_timeout": 90, "retry_count": 2}
    r = c.put("/api/config/processing", json=body)
    assert r.status_code == 200 and r.json()["success"], r.text
    p = c.get("/api/config").json()["config"]["processing"]
    for k, v in body.items():
        assert p[k] == v
    assert c.put("/api/config", json=body).status_code == 405  # the old (wrong) call really is not a route
