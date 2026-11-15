# -*- coding: utf-8 -*-
"""PM-INS-0002 (2026-11-15): with cloud_code (OAuth, no API-key service) as the only enabled model, the inspector
must still see it as usable — in /inspector/models and in auto-select — instead of «مدلی انتخاب نشده»."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.api.routes import render_logs as rl  # noqa: E402
from app.services import cloud_code_service, oauth_model_registry  # noqa: E402


def test_oauth_ready_needs_dispatcher_and_token(monkeypatch):
    monkeypatch.setattr(oauth_model_registry, "get_oauth_dispatcher", lambda mid: object() if mid == "cloud_code" else None)
    monkeypatch.setattr(cloud_code_service, "cloud_code_is_configured", lambda: True)
    assert rl._oauth_model_ready("cloud_code") is True
    assert rl._oauth_model_ready("gemini-2.0-flash") is False
    monkeypatch.setattr(cloud_code_service, "cloud_code_is_configured", lambda: False)
    assert rl._oauth_model_ready("cloud_code") is False


def test_oauth_ready_never_raises(monkeypatch):
    def boom(_mid):
        raise RuntimeError("x")
    monkeypatch.setattr(oauth_model_registry, "get_oauth_dispatcher", boom)
    assert rl._oauth_model_ready("cloud_code") is False


def test_used_in_models_list_and_smart_select():
    src = Path(rl.__file__).read_text(encoding="utf-8")
    assert "provider_available = _oauth_model_ready(model_id)" in src
    assert "return _oauth_model_ready(model_id)" in src
