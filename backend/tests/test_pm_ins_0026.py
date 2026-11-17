"""PM-INS-0026: journal sees the inspector, memory vs. real stack, the honest «last real run» line."""

import json
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool


@pytest.fixture()
def db():
    from app.core.database import Base
    import app.models.project  # noqa: F401
    import app.models.inspector_session  # noqa: F401
    import app.api.routes.project_journal  # noqa: F401  (ActivityLog lives there)
    eng = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(eng)
    s = sessionmaker(bind=eng)()
    yield s
    s.close()


def _project(db, pid="gh_x_quran", **kw):
    from app.models.project import Project
    p = Project(id=pid, name="quran", **kw)
    db.add(p)
    db.commit()
    return p


def test_journal_mirrors_inspector_answers_once(db):
    from app.api.routes.project_journal import ActivityLog, sync_inspector_activity
    from app.models.inspector_session import InspectorMessage, InspectorSession
    _project(db)
    s = InspectorSession(project_id="gh_x_quran")
    db.add(s)
    db.commit()
    db.add_all([InspectorMessage(session_id=s.id, role="user", content="امنیت را بررسی کن"),
                InspectorMessage(session_id=s.id, role="assistant", content="۳ یافته…", model_id="deepseek-chat",
                                 tokens_used=900),
                InspectorMessage(session_id=s.id, role="assistant", content="❌ خطا", model_id="deepseek-chat")])
    db.commit()
    assert sync_inspector_activity(db, "gh_x_quran") == 2
    assert sync_inspector_activity(db, "gh_x_quran") == 0  # idempotent
    rows = db.query(ActivityLog).filter(ActivityLog.project_id == "gh_x_quran").all()
    assert sorted(r.success for r in rows) == [False, True] and sum(r.tokens_used for r in rows) == 900
    assert {r.activity_type for r in rows} == {"inspector_chat"}


def test_stale_framework_memory_is_quarantined_not_deleted(db):
    from app.models.project import ProjectFile
    from app.services.memory_stack_review import review
    fields = [
        {"id": "f1", "name": "دستور پیاده‌سازی مسیریابی Next.js", "value": "App Router Next.js …"},
        {"id": "f2", "name": "لایهٔ API", "value": "axios و NEXT_PUBLIC_API_BASE_URL در .env.local"},
        {"id": "f3", "name": "تست", "value": "برای کامپوننت‌های React تست بنویس"},
    ]
    _project(db, memory_instructions=json.dumps({"content": "اپ قرآنی مبتنی بر React و Next.js"}, ensure_ascii=False),
             dynamic_fields=json.dumps(fields, ensure_ascii=False))
    db.add(ProjectFile(project_id="gh_x_quran", file_path="package.json",
                       content=json.dumps({"dependencies": {"react": "18"}, "devDependencies": {"vite": "5"}})))
    db.commit()
    prev = review(db, "gh_x_quran", apply=False)
    assert {a["id"] for a in prev["archived"]} == {"f1", "f2"} and prev["instructions_corrected"]
    res = review(db, "gh_x_quran")
    assert res["stack"] == ["React", "Vite"]
    from app.models.project import Project
    p = db.query(Project).get("gh_x_quran")
    got = {f["id"]: f for f in json.loads(p.dynamic_fields)}
    assert got["f1"]["archived"] and got["f1"]["archived_reason"] == "stale_stack:Next.js"
    assert not got["f3"].get("archived") and len(got) == 3  # nothing deleted
    mi = json.loads(p.memory_instructions)
    assert mi["content"].startswith("⚠️ اصلاحِ خودکارِ حافظه") and "React و Next.js" in mi["content"]
    again = review(db, "gh_x_quran")
    assert again["archived"] == [] and not again["instructions_corrected"]  # once


def test_a_real_next_project_is_left_alone(db):
    from app.models.project import ProjectFile
    from app.services.memory_stack_review import review
    _project(db, pid="p2", dynamic_fields=json.dumps([{"id": "a", "name": "Next.js routing", "value": "app router"}]))
    db.add(ProjectFile(project_id="p2", file_path="frontend/package.json",
                       content=json.dumps({"dependencies": {"next": "14", "react": "18"}})))
    db.commit()
    assert review(db, "p2")["archived"] == []
    _project(db, pid="p3", dynamic_fields=json.dumps([{"id": "a", "name": "Next.js", "value": "x"}]))
    assert review(db, "p3")["skipped"]  # no manifest ⇒ never guess


def test_summary_states_the_last_real_task_run():
    from app.services.oversight_summary import build_summary
    now = datetime(2026, 11, 17, tzinfo=timezone.utc)
    W = SimpleNamespace
    watched = [W(id="w1", repo_full_name="o/pm", schedule_enabled=True, scan_interval_hours=168, verify_interval_hours=24,
                 autonomy_level="auto", verify_only_mode=True, claude_runner_enabled=False, allow_push=False,
                 interval_hours=6, scan_fail_count=0, last_run_at="2026-06-07T10:00:00+00:00")]
    tasks = [W(id="t1", title="fix x", watched_id="w1", project_full_name="o/pm", status="pending", priority="high",
               archived=False, verification_status="", updated_at="2026-11-10T00:00:00+00:00",
               created_at="2026-05-01T00:00:00+00:00", last_run_at="2026-06-07T09:00:00+00:00", merged_from=[])]
    svc = SimpleNamespace(watched=watched, tasks=tasks, reports=[])
    lr = build_summary(svc, now=now)["last_real_run"]
    assert lr["task_at"].startswith("2026-06-07") and lr["task_days_ago"] == 162
    assert "هیچ پروژه‌ای «اجرای خودکارِ کد»" in lr["line"] and lr["auto_but_verify_only"] == ["o/pm"]
    assert "PR" in lr["safe_path"]
