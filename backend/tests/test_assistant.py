# -*- coding: utf-8 -*-
"""«دستیار» (app/services/assistant.py + routes/assistant.py) and the live repo reader (repo_docs)."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


@pytest.fixture()
def client(monkeypatch, tmp_path):
    monkeypatch.setenv("ASSISTANT_STORAGE_PATH", str(tmp_path / "assistant"))
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from app.api.routes import assistant as routes
    from app.services import assistant as A

    async def fake_generate(model_id, fallbacks, system, turns):
        # the live context must reach the model
        assert "نقشهٔ صفحه‌های برنامه" in system and "/oversight" in system
        assert "دفترِ کار" in system
        return {"model_id": model_id, "content": f"پاسخ از {model_id}", "latency_ms": 1, "tokens": 3}

    async def fake_counts():
        return "- «اتاق فرمان»: 0 مخزن"

    monkeypatch.setattr(A, "_generate", fake_generate)
    monkeypatch.setattr(A, "_live_counts", fake_counts)
    monkeypatch.setattr(A, "available_models", lambda: [
        {"id": "m-fast", "name": "fast", "provider": "x", "vision": False},
        {"id": "m-strong", "name": "strong", "provider": "y", "vision": False},
    ])
    app = FastAPI()
    app.include_router(routes.router, prefix="/api")
    return TestClient(app)


SITE = [{"href": "/oversight", "label": "اتاق فرمان", "desc": "پایشِ مخازن"}]


def test_worklog_is_read_and_split():
    from app.services import assistant as A, repo_docs

    text, src = repo_docs.read_text("docs/WORKLOG.md")  # offline in tests ⇒ the local checkout
    assert src == "local"
    secs = A.worklog_sections(text)
    assert len(secs) > 10 and secs[0]["title"].startswith("2026-")


def test_ask_single_saves_conversation_and_continues_it(client):
    r = client.post("/api/assistant/ask", json={"message": "اتاق فرمان چه می‌کند؟", "page": {"path": "/"}, "site_map": SITE})
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["answers"][0]["model_id"] == "m-fast"  # the first (cheapest) is the default
    cid = data["conversation_id"]
    r2 = client.post("/api/assistant/ask", json={"message": "و بعد؟", "conversation_id": cid, "site_map": SITE,
                                                 "history": [{"role": "user", "content": "اتاق فرمان چه می‌کند؟"}]})
    assert r2.json()["conversation_id"] == cid
    conv = client.get(f"/api/assistant/conversations/{cid}").json()
    assert len(conv["messages"]) == 4
    assert client.get("/api/assistant/conversations").json()[0]["id"] == cid


def test_multi_model_answers_each(client):
    r = client.post("/api/assistant/ask", json={"message": "مقایسه کن", "model_ids": ["m-fast", "m-strong", "nope"], "site_map": SITE})
    ids = [a["model_id"] for a in r.json()["answers"]]
    assert ids == ["m-fast", "m-strong"]


def test_archiving_a_conversation_keeps_the_file(client, tmp_path):
    cid = client.post("/api/assistant/ask", json={"message": "سلام", "site_map": SITE}).json()["conversation_id"]
    assert client.delete(f"/api/assistant/conversations/{cid}").json() == {"ok": True}
    assert (tmp_path / "assistant" / "deleted" / f"{cid}.json").is_file()
    assert client.get(f"/api/assistant/conversations/{cid}").status_code == 404
    assert client.get("/api/assistant/conversations/../../etc").status_code == 404


def test_empty_message_is_refused(client):
    assert client.post("/api/assistant/ask", json={"message": "  "}).status_code == 400


def test_assistant_router_is_mounted_behind_the_wall():
    from app.core import auth
    from app.main import app

    assert "/api/assistant/ask" in app.openapi()["paths"]
    assert not any(p.startswith("/api/assistant") for p in auth.PUBLIC)
