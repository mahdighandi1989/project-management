"""PM-INS-0018 — «🔍 تشخیص» از همان نشانیِ واقعیِ پیش‌نمایش می‌خواند؛ دکمه‌های تحلیل همیشه در دسترس."""

import inspect
import json
import pathlib
import types

from app.api.routes import render_logs as RL


def _p(**kw):
    base = dict(deploy_url=None, preview_url=None, extra_data=None)
    base.update(kw)
    return types.SimpleNamespace(**base)


def test_explicit_preview_url_wins():
    url = "https://quran-web-app-8rwy.onrender.com"
    assert RL._resolve_bridge_preview_url(_p(), url) == url
    assert RL._resolve_bridge_preview_url(_p(deploy_url="https://old.example"), url) == url


def test_falls_back_to_project_then_extra_data_and_rejects_junk():
    assert RL._resolve_bridge_preview_url(_p(deploy_url="https://d.example"), None) == "https://d.example"
    assert RL._resolve_bridge_preview_url(_p(extra_data=json.dumps({"frontend_url": "https://f.example"}))) == "https://f.example"
    assert RL._resolve_bridge_preview_url(_p(), "javascript:alert(1)") is None
    assert RL._resolve_bridge_preview_url(_p(extra_data="not json")) is None


def test_endpoint_takes_preview_url_and_frontend_sends_it():
    assert "preview_url" in inspect.signature(RL.debug_bridge_injection).parameters
    page = (pathlib.Path(__file__).resolve().parents[2] / "frontend/src/app/projects/[id]/page.tsx").read_text(encoding="utf-8")
    assert "debug-bridge/${projectId}${_pv ? `?preview_url=" in page
    assert 'data-testid="inspector-quick-actions"' in page
