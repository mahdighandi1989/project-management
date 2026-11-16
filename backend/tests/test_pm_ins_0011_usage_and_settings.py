# -*- coding: utf-8 -*-
"""(PM-INS-0011) «مدل‌ها و تنظیمات»: every AI call is counted in «مصرف AI» (success, failure, OAuth), the usage summary
speaks UTC explicitly, and the Render log fetch is bounded."""
import asyncio
import sys
from datetime import datetime, timedelta
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def _manager(monkeypatch, service):
    from app.core.models_registry import ModelProvider
    from app.services import ai_manager as am

    mgr = object.__new__(am.AIManager)
    mgr._services = {ModelProvider.DEEPSEEK: service}
    mgr._init_errors = {}
    monkeypatch.setattr(mgr, "get_enabled_status", lambda model_id: True, raising=False)
    logged = []

    async def fake_log(**kw):
        logged.append(kw)

    monkeypatch.setattr(mgr, "_log_ai_usage_async", fake_log)
    return mgr, logged


class _OkService:
    async def generate(self, model_id, messages, max_tokens, temperature, **kw):
        from app.services.ai_base import AIResponse
        return AIResponse(model_id=model_id, content="ok", tokens_used=120)


class _FailService:
    async def generate(self, model_id, messages, max_tokens, temperature, **kw):
        raise RuntimeError("Incorrect API key provided")


def _run(coro):
    async def main():
        out = await coro
        await asyncio.sleep(0)  # let the scheduled log task run
        await asyncio.sleep(0)
        return out
    return asyncio.run(main())


def test_successful_call_is_logged(monkeypatch):
    from app.services.ai_base import Message

    mgr, logged = _manager(monkeypatch, _OkService())
    r = _run(mgr.generate("deepseek-chat", [Message(role="user", content="hi")], allow_fallback=False))
    assert r.content == "ok"
    assert len(logged) == 1 and logged[0]["model_id"] == "deepseek-chat" and logged[0]["response"].tokens_used == 120


def test_failed_call_is_logged_as_error_and_still_raises(monkeypatch):
    from app.services.ai_base import Message

    mgr, logged = _manager(monkeypatch, _FailService())

    async def go():
        with pytest.raises(RuntimeError):
            await mgr.generate("deepseek-chat", [Message(role="user", content="hi")], allow_fallback=False)
        await asyncio.sleep(0)
        await asyncio.sleep(0)

    asyncio.run(go())
    assert len(logged) == 1
    assert "Incorrect API key" in (logged[0]["response"].error or "")


def test_oauth_call_is_logged(monkeypatch):
    from app.services import oauth_model_registry as reg
    from app.services.ai_base import Message

    async def disp(prompt, max_tokens=0, temperature=0):
        return "from oauth"

    monkeypatch.setattr(reg, "get_oauth_dispatcher", lambda mid: disp if mid == "cloud_code" else None)
    mgr, logged = _manager(monkeypatch, _OkService())
    r = _run(mgr.generate("cloud_code", [Message(role="user", content="hi")]))
    assert r.content == "from oauth"
    assert len(logged) == 1 and logged[0]["provider_str"] == "cloud_code"


def test_usage_summary_timestamps_are_explicit_utc():
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from app.api.routes import ai_usage
    from app.core.database import SessionLocal, Base, engine
    from app.models.ai_log import AILog

    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        db.add(AILog(provider="deepseek", model="deepseek-chat", request_type="chat", total_tokens=10,
                     status="success", created_at=datetime.utcnow() - timedelta(minutes=1)))
        db.commit()
    finally:
        db.close()
    app = FastAPI()
    app.include_router(ai_usage.router, prefix="/api")
    d = TestClient(app).get("/api/ai-usage/summary").json()
    assert d["last_request_at"].endswith("Z") and d["first_request_at"].endswith("Z")
    assert d["today"]["count"] >= 1


def test_render_session_has_a_bounded_timeout():
    from app.services.render_service import RenderAPIService as RenderService

    async def go():
        svc = object.__new__(RenderService)
        svc._session = None
        svc.api_key = "dummy"
        s = await svc._get_session()
        try:
            return s.timeout.total
        finally:
            await s.close()

    total = asyncio.run(go())
    assert total is not None and total <= 30
