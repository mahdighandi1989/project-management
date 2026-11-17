"""PM-INS-0020 (۱۳) — one-page summary of «اتاق فرمان» + safe cleanup (preview, confirm, archive — never delete)."""

import asyncio
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from app.services import oversight_service as OS
from app.services import oversight_summary as S

NOW = datetime(2026, 11, 17, 8, 0, tzinfo=timezone.utc)


def _t(i, title, status="suggested", days=1, prio="medium", wid="W"):
    ts = (NOW - timedelta(days=days)).isoformat()
    return OS.OversightTask(id=f"T{i}", watched_id=wid, project_full_name="o/r", title=title, prompt="p",
                            status=status, priority=prio, created_at=ts, updated_at=ts)


def _svc(tasks):
    w = OS.WatchedProject(id="W", repo_full_name="o/r", repo_url="u") if hasattr(OS, "WatchedProject") else None
    svc = SimpleNamespace(tasks=tasks, reports=[], watched=[w], _lock=asyncio.Lock(), saved=0)
    svc._save_tasks = lambda skip_sync=False: setattr(svc, "saved", svc.saved + 1)
    return svc


def test_duplicates_and_stale_preview():
    ts = [_t(1, "افزودن دکمهٔ ذخیره به صفحهٔ تنظیمات کاربر", days=2),
          _t(2, "افزودن دکمهٔ ذخیره به صفحهٔ تنظیمات کاربر جدید", days=1, status="pending"),
          _t(3, "رفعِ خطای ورود با گوگل در موبایل", days=90),
          _t(4, "مستندسازیِ API", days=10, status="done")]
    c = S.cleanup_candidates(_svc(ts), now=NOW)
    assert len(c["duplicate_groups"]) == 1
    g = c["duplicate_groups"][0]
    assert g["keep"]["id"] == "T2" and [a["id"] for a in g["archive"]] == ["T1"]  # approved work kept over a suggestion
    assert [x["id"] for x in c["stale"]] == ["T3"]                                   # done tasks never offered


def test_summary_counts_and_top_tasks():
    ts = [_t(1, "a b c d", prio="low"), _t(2, "e f g h", prio="critical"), _t(3, "i j k l", status="done")]
    s = S.build_summary(_svc(ts), now=NOW)
    assert s["totals"]["tasks_open"] == 2 and s["top_tasks"][0]["id"] == "T2"
    assert s["automation"][0]["off"]  # the defaults: schedule/runner off ⇒ explained


def test_cleanup_archives_only_what_was_confirmed_and_deletes_nothing():
    ts = [_t(1, "x y z w"), _t(2, "x y z w v"), _t(3, "old one here", days=90)]
    svc = _svc(ts)
    res = asyncio.run(S.apply_cleanup(svc, merge=[{"keep": "T2", "archive": ["T1"]}], stale_ids=["T3"]))
    assert res["merged"] == 1 and res["archived_stale"] == 1 and len(svc.tasks) == 3
    t1, t2, t3 = svc.tasks
    assert t1.archived and t1.merged_into == "T2" and t1.archived_reason == "owner_cleanup_duplicate"
    assert "T1" in t2.merged_from and t3.archived_reason == "owner_cleanup_stale"


def test_apply_requires_explicit_confirmation():
    import inspect
    from app.api.routes import oversight as R
    assert "if not body.confirm" in inspect.getsource(R.oversight_cleanup_apply)
