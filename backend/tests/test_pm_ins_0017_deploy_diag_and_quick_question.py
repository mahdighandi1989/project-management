"""PM-INS-0017 — «🧪 تست Deploy» فقط‌خواندنی با نتیجه، و سؤالِ ساده با وجودِ ساختارمندسازیِ پرامپت."""

import asyncio
import json
import types

from app.api.routes import project_memory as PM
from app.api.routes import render_logs as RL
from app.services import deploy_service as DSV


class _Q:
    def __init__(self, obj):
        self.obj = obj

    def filter(self, *a, **k):
        return self

    def first(self):
        return self.obj


class _DB:
    def __init__(self, project):
        self.project = project

    def query(self, *a, **k):
        return _Q(self.project)


class _FakeRender:
    triggered = []

    def __init__(self, api_key=None):
        self.api_key = api_key

    async def list_services(self):
        return [
            {"service": {"id": "srv-be", "name": "detective-1-backend", "type": "web_service",
                         "suspended": "not_suspended", "serviceDetails": {"url": "https://be.example"}}},
            {"service": {"id": "srv-fe", "name": "detective-1-frontend", "type": "web_service"}},
            {"service": {"id": "srv-x", "name": "something-else", "type": "web_service"}},
        ]

    async def get_deploys(self, service_id, limit=10):
        if service_id == "srv-fe":
            return {"success": False, "error": "HTTP 500: boom"}
        return {"success": True, "deploys": [{"id": "dep-1", "status": "build_failed", "commit_id": "277207c",
                                              "createdAt": "2026-11-16T16:00:00Z", "finishedAt": None}]}

    async def trigger_deploy(self, service_id, clear_cache=False):  # must never be called
        _FakeRender.triggered.append(service_id)
        return {"success": True}

    async def close(self):
        pass


def _project(extra):
    return types.SimpleNamespace(name="Detective-1", extra_data=json.dumps(extra))


def test_diagnose_lists_project_services_with_last_deploy_and_never_deploys(monkeypatch):
    monkeypatch.setenv("RENDER_API_KEY", "dummy")
    monkeypatch.setattr(DSV, "RenderDeployService", _FakeRender)
    _FakeRender.triggered = []
    out = asyncio.run(PM.diagnose_render_deploy("p1", db=_DB(_project({"owner": "o", "repo": "Detective-1"}))))
    assert out["render_api_key_configured"] is True
    assert out["match_method"] == "name"
    ids = {s["id"]: s for s in out["services"]}
    assert set(ids) == {"srv-be", "srv-fe"}
    assert ids["srv-be"]["last_deploy"]["status"] == "build_failed"
    assert ids["srv-fe"]["error"].startswith("HTTP 500")
    assert _FakeRender.triggered == []  # a test is read-only


def test_diagnose_without_key_says_so(monkeypatch):
    monkeypatch.delenv("RENDER_API_KEY", raising=False)
    from app.models import setting as S
    monkeypatch.setattr(S.Setting, "get_value", staticmethod(lambda db, k: None))
    out = asyncio.run(PM.diagnose_render_deploy("p1", db=_DB(_project({}))))
    assert out["success"] is False and out["render_api_key_configured"] is False and out["errors"]


def test_diagnose_prefers_saved_services(monkeypatch):
    monkeypatch.setenv("RENDER_API_KEY", "dummy")
    monkeypatch.setattr(DSV, "RenderDeployService", _FakeRender)
    out = asyncio.run(PM.diagnose_render_deploy("p1", db=_DB(_project({"render_service_ids": ["srv-x"]}))))
    assert out["match_method"] == "saved"
    assert [s["id"] for s in out["services"]] == ["srv-x"]


def _req(message, original=None, reply=None):
    return RL.SmartChatRequest(project_id="p", model_ids=[], message=message, original_message=original,
                               reply_to=reply)


def test_enhanced_prompt_of_a_simple_question_falls_back_to_the_raw_question():
    enhanced = "## هدف\nهش آخرین commit پروژه را از GitHub بخوان و گزارش کن.\n## مراحل\n1. ...\n2. ..."
    r = _req(enhanced, original="هش آخرین commit چیست")
    assert RL._apply_quick_question_override(r) is True
    assert r.message == "هش آخرین commit چیست"


def test_override_leaves_real_requests_and_replies_alone():
    r = _req("## long enhanced", original="این دکمه کار نمیکنه، درستش کن")
    assert RL._apply_quick_question_override(r) is False and r.message == "## long enhanced"
    r = _req("## long enhanced", original=None)
    assert RL._apply_quick_question_override(r) is False
    reply = RL.SmartChatReplyContext(message_id="m", content="x", role="assistant")
    r = _req("## long enhanced", original="هش آخرین commit چیست", reply=reply)
    assert RL._apply_quick_question_override(r) is False
