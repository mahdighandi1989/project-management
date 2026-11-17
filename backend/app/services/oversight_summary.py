"""«اتاق فرمان» on one page (PM-INS-0020 بندِ ۱۳, 2026-11-17).

The owner: «۱۳۷۹ تسکِ فعال و ۳۰۵۸ گزارش، همهٔ ۹ پروژه فقط پایش — کنترلش از دستم رفته». This module answers, in Persian, from the
live service state:

* what runs automatically right now, per project, and what is off and WHY (schedule, autonomy, runner, models);
* the 10 most important open tasks;
* cleanup candidates — duplicates (near-identical titles in the same project) and stale ones (untouched suggestions/
  pending tasks) — as a PREVIEW. Nothing is changed until the owner confirms; confirmed items are ARCHIVED with a
  reason (and `merged_into` for duplicates), never deleted, so «بایگانی» shows them and they can be restored.
"""

from __future__ import annotations

import re
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

STALE_DAYS = 45
_PRIO = {"critical": 0, "high": 1, "medium": 2, "low": 3}
_OPEN_EXCLUDE = {"done", "cancelled", "abandoned"}
_WORD = re.compile(r"[\w؀-ۿ]+")
_STOP = {"و", "در", "به", "از", "که", "را", "با", "این", "برای", "یک", "the", "a", "of", "to", "and", "in", "for"}


def _parse(ts: Optional[str]) -> Optional[datetime]:
    try:
        d = datetime.fromisoformat((ts or "").replace("Z", "+00:00"))
        return d if d.tzinfo else d.replace(tzinfo=timezone.utc)
    except Exception:  # noqa: BLE001
        return None


def _is_open(t: Any) -> bool:
    return not getattr(t, "archived", False) and (t.status or "") not in _OPEN_EXCLUDE


def _words(title: str) -> frozenset:
    return frozenset(w.lower() for w in _WORD.findall(title or "") if len(w) > 1 and w.lower() not in _STOP)


def _automation_line(w: Any, models_on: int) -> Dict[str, Any]:
    on, off = [], []
    if not getattr(w, "schedule_enabled", False):
        off.append("همهٔ کارهای دوره‌ای — «زمان‌بندی فعال» خاموش است")
    else:
        sh = float(getattr(w, "scan_interval_hours", 0) or 0)
        vh = float(getattr(w, "verify_interval_hours", 0) or 0)
        if sh > 0:
            fails = int(getattr(w, "scan_fail_count", 0) or 0)
            on.append(f"اسکن هر {sh:g} ساعت" + (f" (⚠️ {fails} شکستِ پیاپی)" if fails else ""))
        else:
            off.append("اسکنِ دوره‌ای — بازه ۰ است")
        if vh > 0:
            on.append(f"verify هر {vh:g} ساعت")
        else:
            off.append("verify ِ دوره‌ای — بازه ۰ است")
        if getattr(w, "autonomy_level", "manual") == "auto" and not getattr(w, "verify_only_mode", False):
            on.append(f"ارزیابیِ خودکارِ تسک‌های auto هر {float(w.interval_hours or 0):g} ساعت")
        else:
            off.append("اجرای خودکارِ تسک‌ها — سطحِ خودمختاری "
                       + ("«فقط verify»" if getattr(w, "verify_only_mode", False) else f"«{w.autonomy_level}» است (فقط پایش)"))
    if getattr(w, "claude_runner_enabled", False):
        on.append("🤖 اجرای کد با Claude در GitHub" + (" (push ِ مستقیم)" if getattr(w, "allow_push", False) else " (شاخه + PR)"))
    else:
        off.append("🤖 تغییرِ خودکارِ کد — «اجرای خودکار» روشن نشده")
    if models_on == 0 and (on and getattr(w, "schedule_enabled", False)):
        off.append("⚠️ هیچ مدلِ روشنی نیست — اسکن و verify با «مدلی نیست» شکست می‌خورند")
    return {"watched_id": w.id, "repo": w.repo_full_name, "on": on, "off": off}


def build_summary(svc: Any, *, now: Optional[datetime] = None) -> Dict[str, Any]:
    now = now or datetime.now(timezone.utc)
    try:
        from .ai_manager import get_ai_manager
        models_on = len(get_ai_manager().get_available_models())
    except Exception:  # noqa: BLE001
        models_on = -1
    watched = list(svc.watched)
    names = {w.id: w.repo_full_name for w in watched}
    tasks = list(svc.tasks)
    open_tasks = [t for t in tasks if _is_open(t)]
    by_status: Dict[str, int] = defaultdict(int)
    for t in open_tasks:
        by_status[t.status or "?"] += 1

    def _rank(t: Any):
        vs = getattr(t, "verification_status", "") or ""
        return (
            _PRIO.get(t.priority or "", 9),
            0 if vs in ("regressed", "partial", "applied_externally_pending_verify") else 1,
            0 if (t.status or "") != "suggested" else 1,  # owner-approved work before scan suggestions
            -(_parse(t.updated_at) or now).timestamp(),
        )

    top = sorted(open_tasks, key=_rank)[:10]
    cand = cleanup_candidates(svc, now=now)
    last_real = last_real_runs(svc, tasks, watched, names, now=now)
    return {
        "generated_at": now.isoformat(),
        "models_on": models_on,
        "totals": {
            "watched": len(watched), "tasks_open": len(open_tasks),
            "tasks_archived": sum(1 for t in tasks if getattr(t, "archived", False)),
            "reports": len(svc.reports), "open_by_status": dict(by_status),
        },
        "automation": [_automation_line(w, models_on) for w in watched],
        "top_tasks": [{
            "id": t.id, "title": t.title, "repo": names.get(t.watched_id, t.project_full_name), "priority": t.priority,
            "status": t.status, "verification_status": getattr(t, "verification_status", ""),
            "updated_at": t.updated_at,
        } for t in top],
        "last_real_run": last_real,
        "cleanup": {"duplicates": len(cand["duplicate_groups"]),
                    "duplicate_tasks": sum(len(g["archive"]) for g in cand["duplicate_groups"]),
                    "stale": len(cand["stale"])},
    }


def last_real_runs(svc: Any, tasks: List[Any], watched: List[Any], names: Dict[str, str], *,
                   now: datetime) -> Dict[str, Any]:
    """(PM-INS-0026 «ب») One honest line: when did a task REALLY run last, and can anything change code right now?
    Scans/verifies run weekly, but «اجرای تسک» (last_run_at) stopped in early June and no project has the Claude runner —
    the summary said nothing about it."""
    def _latest(items, attr):
        best = None
        for x in items:
            d = _parse(getattr(x, attr, None))
            if d and (best is None or d > best[0]):
                best = (d, x)
        return best

    t = _latest(tasks, "last_run_at")
    w = _latest(watched, "last_run_at")
    runner_on = [x.repo_full_name for x in watched if getattr(x, "claude_runner_enabled", False)]
    push_on = [x.repo_full_name for x in watched if getattr(x, "allow_push", False)]
    contradictory = [x.repo_full_name for x in watched
                     if getattr(x, "autonomy_level", "") == "auto" and getattr(x, "verify_only_mode", False)]
    at = t[0] if t else None
    days = (now - at).days if at else None
    line = ("آخرین اجرای واقعیِ یک تسک: " + (f"{at:%Y-%m-%d} ({days} روز پیش) — «{(t[1].title or '')[:60]}» در "
                                           f"{names.get(t[1].watched_id, t[1].project_full_name)}" if at else "هرگز"))
    line += ("؛ هیچ پروژه‌ای «اجرای خودکارِ کد» (Claude runner) ندارد ⇒ هیچ اصلاحِ کدی خودکار انجام نمی‌شود"
             if not runner_on else f"؛ اجرای خودکارِ کد روشن برای: {', '.join(runner_on)}")
    return {
        "task_at": at.isoformat() if at else None, "task_days_ago": days,
        "task_title": (t[1].title if t else None), "task_repo": (names.get(t[1].watched_id, t[1].project_full_name) if t else None),
        "project_run_at": w[0].isoformat() if w else None,
        "runner_on": runner_on, "allow_push_on": push_on,
        "auto_but_verify_only": contradictory,
        "line": line,
        "safe_path": ("برای آزمونِ یک‌خطی: «بازرس ویژه» ِ همان پروژه ⇒ درخواستِ یک‌خطی ⇒ «اعمال» = شاخهٔ تازه "
                      "inspector/smart-fix-… + PR (هرگز main). هیچ تنظیمِ «اتاق فرمان» لازم نیست؛ PR را ادغام نکنید مگر "
                      "پس از بررسی — ادغام = دیپلوی."),
    }


def cleanup_candidates(svc: Any, *, now: Optional[datetime] = None, stale_days: int = STALE_DAYS) -> Dict[str, Any]:
    """Preview only. Duplicates: open tasks of the same project whose title word-sets overlap ≥ 0.8 (Jaccard), grouped;
    the one to keep is the most advanced/most recent. Stale: open «suggested»/«pending» tasks not updated for
    `stale_days` days and never applied/verified-partial."""
    now = now or datetime.now(timezone.utc)
    names = {w.id: w.repo_full_name for w in svc.watched}
    open_tasks = [t for t in svc.tasks if _is_open(t)]
    groups: List[Dict[str, Any]] = []
    by_proj: Dict[str, List[Any]] = defaultdict(list)
    for t in open_tasks:
        by_proj[t.watched_id or t.project_full_name or "?"].append(t)
    seen: set = set()
    for proj, ts in by_proj.items():
        ws = [(t, _words(t.title)) for t in ts]
        # bucket by the rarest-ish first word to avoid O(n²) on 1 000+ tasks
        buckets: Dict[str, List[int]] = defaultdict(list)
        for i, (_t, w) in enumerate(ws):
            for tok in sorted(w)[:3]:
                buckets[tok].append(i)
        for i, (t, w) in enumerate(ws):
            if t.id in seen or len(w) < 3:
                continue
            members = [t]
            near = {j for tok in sorted(w)[:3] for j in buckets[tok] if j != i}
            for j in sorted(near):
                u, wu = ws[j]
                if u.id in seen or len(wu) < 3:
                    continue
                if len(w & wu) / max(1, len(w | wu)) >= 0.8:
                    members.append(u)
            if len(members) < 2:
                continue

            def _keep_rank(x):
                adv = {"applied_externally_pending_verify": 0, "partial": 1, "regressed": 1}.get(
                    getattr(x, "verification_status", ""), 2)
                return (adv, 0 if (x.status or "") != "suggested" else 1, -(_parse(x.updated_at) or now).timestamp())

            members.sort(key=_keep_rank)
            for m in members:
                seen.add(m.id)
            groups.append({
                "repo": names.get(proj, proj),
                "keep": {"id": members[0].id, "title": members[0].title, "status": members[0].status},
                "archive": [{"id": m.id, "title": m.title, "status": m.status} for m in members[1:]],
            })
    cutoff = now - timedelta(days=stale_days)
    stale = []
    for t in open_tasks:
        if t.id in seen or (t.status or "") not in ("suggested", "pending"):
            continue
        if getattr(t, "verification_status", "") in ("partial", "applied_externally_pending_verify", "regressed"):
            continue
        u = _parse(t.updated_at) or _parse(t.created_at)
        if u and u < cutoff:
            stale.append({"id": t.id, "title": t.title, "repo": names.get(t.watched_id, t.project_full_name),
                          "status": t.status, "updated_at": t.updated_at,
                          "days": (now - u).days})
    stale.sort(key=lambda x: -x["days"])
    return {"stale_days": stale_days, "duplicate_groups": groups, "stale": stale}


async def apply_cleanup(svc: Any, *, merge: List[Dict[str, Any]], stale_ids: List[str], by: str = "owner") -> Dict[str, Any]:
    """Archive exactly what the owner confirmed. `merge`: [{"keep": id, "archive": [ids]}]. Never deletes."""
    from .oversight_service import now_iso
    archived = 0
    merged = 0
    async with svc._lock:
        idx = {t.id: t for t in svc.tasks}
        for g in merge or []:
            keep = idx.get(g.get("keep"))
            if keep is None:
                continue
            for tid in g.get("archive") or []:
                t = idx.get(tid)
                if t is None or getattr(t, "archived", False) or tid == keep.id:
                    continue
                t.archived, t.archived_at = True, now_iso()
                t.archived_reason = "owner_cleanup_duplicate"
                t.merged_into = keep.id
                if tid not in (keep.merged_from or []):
                    keep.merged_from = list(keep.merged_from or []) + [tid]
                t.updated_at = now_iso()
                merged += 1
        for tid in stale_ids or []:
            t = idx.get(tid)
            if t is None or getattr(t, "archived", False):
                continue
            t.archived, t.archived_at = True, now_iso()
            t.archived_reason = "owner_cleanup_stale"
            t.updated_at = now_iso()
            archived += 1
        svc._save_tasks(skip_sync=True)
    return {"merged": merged, "archived_stale": archived, "by": by,
            "note": "هیچ چیزی حذف نشد — همه در «آرشیو» با دلیل (owner_cleanup_duplicate / owner_cleanup_stale) قابلِ بازگردانی‌اند"}
