"""PM-INS-0007 — archive debates (duplicates, stuck status) + inspector (quick classify, list_commits, real model)."""

import inspect
from datetime import datetime, timedelta

from app.api.routes import render_logs as RL
from app.services import cloud_code_executor as CC
from app.services import debate_service as DS
from app.services import inspector_agent as IA
from app.services.inspector_quick_classify import is_simple_info_question


# ── (4) a plain lookup is a QUESTION, a problem/change request is not ─────────
def test_simple_lookup_questions_skip_the_agent():
    for q in ("آخرین commit چیست؟", "آخرین کامیت چیه", "what is the last commit?", "چند فایل در پروژه هست؟"):
        assert is_simple_info_question(q), q
    for q in ("صفحه کار نمیکنه", "این باگ رو درست کن", "چرا خطا میده؟", "TypeError: x is undefined?",
              "دکمه را اضافه کن", "", "آخرین commit چیست؟\nو این خطا"):
        assert not is_simple_info_question(q), q


def test_classifier_uses_the_quick_path_and_names_the_real_agent_model():
    src = inspect.getsource(RL)
    assert "is_simple_info_question(request.message)" in src
    assert "برای این کار از Claude (حالت عامل)" not in src  # was hard-coded even when deepseek answered
    assert "برای این کار از {primary_model} (حالت عامل)" in src


# ── (5) the agent can read commits (and so can the Cloud Code engine) ─────────
def test_list_commits_tool_is_offered_everywhere():
    assert "list_commits" in {t["name"] for t in IA._build_tools()}
    assert "list_commits" in CC.SUPPORTED_TOOLS_PHASE_3
    assert "list_commits" in {t["name"] for t in CC.get_phase_3_tool_schemas()}
    assert 'elif name == "list_commits"' in inspect.getsource(IA.run_inspector_agent)


def test_format_commits_has_hash_date_author_message():
    data = [
        {"sha": "4c59a18deadbeef", "commit": {"message": "fix(x): y\n\nbody", "author": {"name": "A"},
                                              "committer": {"date": "2026-11-15T20:00:00Z"}}},
        {"sha": "2b3626dabc", "commit": {"message": "feat: z", "author": {"name": "B"},
                                         "committer": {"date": "2026-11-14T10:00:00Z"}}},
    ]
    out = IA.format_commits(data, 1, branch="main")
    assert "4c59a18" in out and "fix(x): y" in out and "body" not in out and "2026-11-15" in out
    assert "2b3626d" not in out  # limit honoured
    assert IA.format_commits([], 5) == "هیچ کامیتی پیدا نشد."


# ── (1)(2) archive: one card per double-submitted debate, no stuck status ─────
def _svc(tmp_path, monkeypatch):
    monkeypatch.setattr(DS, "DEBATES_STORAGE_PATH", tmp_path)
    svc = DS.DebateService.__new__(DS.DebateService)
    svc._sessions = {}
    svc._storage_path = tmp_path
    return svc


def _session(sid, prompt, created, status="completed", updated=None, rounds=0):
    return DS.DebateSession(id=sid, prompt=prompt, mode=DS.WorkMode.DEBATE, status=status, models=[],
                            role_assignments={}, rounds=[[] for _ in range(rounds)],
                            created_at=created, updated_at=updated or created)


def test_duplicate_debates_show_once_and_stay_on_disk(tmp_path, monkeypatch):
    svc = _svc(tmp_path, monkeypatch)
    t = datetime(2026, 1, 4, 15, 40, 40)
    svc._sessions = {
        "a": _session("a", "نظرتون راجع به این اکسپرت چیه", t, status="failed"),
        "b": _session("b", "نظرتون راجع به این اکسپرت چیه", t.replace(microsecond=1234), rounds=2),
        "c": _session("c", "نظرتون راجع به این اکسپرت چیه", t + timedelta(days=1)),
    }
    listed = {s.id for s in svc.list_sessions()}
    assert listed == {"b", "c"}          # the further-along twin wins; a genuinely later run stays
    assert svc.get_session("a") is not None  # nothing deleted


def test_stuck_synthesizing_debate_is_settled(tmp_path, monkeypatch):
    svc = _svc(tmp_path, monkeypatch)
    old = datetime.now() - timedelta(days=200)
    fresh = datetime.now() - timedelta(minutes=5)
    svc._sessions = {
        "old": _session("old", "در چه زمینه هایی بهتر میتونید", old, status="synthesizing"),
        "live": _session("live", "در حال اجرا", fresh, status="synthesizing"),
    }
    by_id = {s.id: s for s in svc.list_sessions()}
    assert by_id["old"].status == "failed"
    assert by_id["old"].metadata["stale_reconciled"]["from"] == "synthesizing"
    assert by_id["live"].status == "synthesizing"   # a debate running right now is left alone
    assert (tmp_path / "old.json").exists()          # the correction is persisted
    # with a result it is completed, not failed
    done = _session("d", "x", old, status="judging")
    done.summary = "خلاصه"
    assert svc._reconcile_stale(done) and done.status == "completed"
